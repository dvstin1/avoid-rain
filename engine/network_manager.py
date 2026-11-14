"""Local network discovery (LAN) and authoritative host/client synchronization."""
# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments
# pylint: disable=too-many-branches,too-many-statements

from collections import deque
import json
import logging
import queue
import socket
import struct
import threading
import time
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
import uuid

from constants import DEFAULT_PLAYER_NAME, LAN_PORT

logger = logging.getLogger(__name__)

MAX_FRAMED_BYTES = 16 * 1024 * 1024  # 16 MB safety ceiling for framed TCP JSON


def _recv_exact(sock: socket.socket, num_bytes: int) -> Optional[bytes]:
    """Read exactly num_bytes from sock, returning None on clean EOF before completion."""
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def _send_framed_json(sock: socket.socket, payload: Dict[str, Any]) -> None:
    """Serialize payload as UTF-8 JSON prefixed with a 4-byte big-endian unsigned length."""
    raw = json.dumps(payload).encode("utf-8")
    header = struct.pack("!I", len(raw))
    sock.sendall(header + raw)


def _recv_framed_json(sock: socket.socket, max_bytes: int = MAX_FRAMED_BYTES) -> Optional[Dict[str, Any]]:
    """Receive a 4-byte big-endian length-prefixed UTF-8 JSON payload from sock."""
    header = _recv_exact(sock, 4)
    if not header:
        return None
    (length,) = struct.unpack("!I", header)
    if length <= 0 or length > max_bytes:
        raise ValueError(f"Invalid framed JSON length: {length}")
    body = _recv_exact(sock, length)
    if body is None:
        raise ValueError("Truncated framed JSON body")
    return json.loads(body.decode("utf-8"))


class NetworkManager:
    """Handles LAN discovery, framed TCP control messages, and 20Hz UDP state sync."""

    _send_framed_json = staticmethod(_send_framed_json)
    _recv_framed_json = staticmethod(_recv_framed_json)

    def __init__(
        self,
        port: int = LAN_PORT,
        identity: str = DEFAULT_PLAYER_NAME,
        local_udp_port: Optional[int] = None,
        host_tcp_port: Optional[int] = None,
        host_udp_port: Optional[int] = None,
        peer_id: Optional[str] = None,
    ) -> None:
        self.port = port
        self.tcp_port = host_tcp_port if host_tcp_port is not None else port + 1
        self.host_udp_port = host_udp_port if host_udp_port is not None else port + 2
        self.local_udp_port = local_udp_port if local_udp_port is not None else self.host_udp_port

        self.identity = identity
        self.peer_id: str = peer_id or uuid.uuid4().hex[:12]

        self.is_hosting = False
        self.is_searching = False
        self.is_connected = False
        self.network_mode = "OFFLINE"  # "OFFLINE", "HOST", "CLIENT"

        self._lock = threading.Lock()
        self.found_hosts: Dict[str, str] = {}  # {ip_address: display_identity}
        self.found_host_peers: Dict[str, str] = {}  # {ip_address: peer_id}
        self.connected_peers: Dict[str, Dict[str, Any]] = {}  # {peer_id: {...}}
        self.server_address: Optional[str] = None
        self.server_peer_id: Optional[str] = None
        self.server_last_seen = 0.0

        # Keyed by peer_id (with identity fallback for legacy/synthetic tests)
        self.remote_players: Dict[str, Dict[str, Any]] = {}

        # Survivor tracking across HOST_DISCONNECT for Host Promotion
        self.last_survivor_peer_ids: List[str] = []
        self.last_survivor_addrs: Dict[str, str] = {}
        self._ever_connected: bool = False
        self._yielding_host: bool = False

        # Thread-safe inbound event queue (drained on main thread via GameState.drain_network_events)
        self._inbound_queue: Deque[Tuple[str, Any]] = deque()
        # Non-blocking outbound reliable TCP queue for client events
        self._outbound_queue: "queue.Queue[Optional[Tuple[str, int, Dict[str, Any]]]]" = queue.Queue(maxsize=256)
        self._outbox_thread: Optional[threading.Thread] = None

        # Callbacks (Injected by GameState)
        self.local_state_provider: Optional[Callable[..., Any]] = None
        self.remote_state_handler: Optional[Callable[..., Any]] = None
        self.on_disconnect_callback: Optional[Callable[..., Any]] = None
        self.host_status_provider: Optional[Callable[[], Dict[str, Any]]] = None
        self.on_handshake_accepted: Optional[Callable[[Dict[str, Any]], None]] = None

        self.host_map_provider: Optional[Callable[..., Any]] = None
        self.host_client_state_restorer: Optional[Callable[..., Any]] = None
        self.host_client_state_cacher: Optional[Callable[..., Any]] = None
        self.host_damage_handler: Optional[Callable[..., Any]] = None
        self.host_heal_handler: Optional[Callable[..., Any]] = None
        self.host_respite_handler: Optional[Callable[..., Any]] = None
        self.host_return_sanctuary_handler: Optional[Callable[..., Any]] = None
        self.client_restored_state_handler: Optional[Callable[..., Any]] = None

        self.stop_event = threading.Event()
        self._scanner_stop_event = threading.Event()
        self._tcp_ready = threading.Event()
        self._scanner_thread: Optional[threading.Thread] = None
        self.threads: List[threading.Thread] = []

    def enqueue_inbound(self, event_type: str, payload: Any) -> None:
        """Thread-safely enqueue an incoming network event for main-thread processing."""
        with self._lock:
            self._inbound_queue.append((event_type, payload))

    def drain_inbound(self) -> List[Tuple[str, Any]]:
        """Atomically drain and return all queued inbound network events."""
        with self._lock:
            items = list(self._inbound_queue)
            self._inbound_queue.clear()
        return items

    def _dispatch_inbound_event(self, event_type: str, payload: Any) -> None:
        """Dispatch a single inbound event on the calling (main) thread."""
        if event_type == "REMOTE_STATE":
            if self.remote_state_handler:
                self.remote_state_handler(payload[0], payload[1])
        elif event_type == "PEER_JOIN":
            peer_id, identity = payload
            if identity and identity != DEFAULT_PLAYER_NAME:
                for r_key, r_entry in list(self.remote_players.items()):
                    if (
                        r_entry.get("identity") == identity
                        and r_entry.get("peer_id")
                        and r_entry.get("peer_id") != peer_id
                    ):
                        self.remote_players.pop(r_key, None)
        elif event_type == "PEER_DISCONNECT":
            self.remote_players.pop(payload[0], None)
            self.remote_players.pop(payload[1], None)
        elif event_type in ("HOST_DISCONNECT", "DISCONNECT"):
            survivors = {self.peer_id}
            addrs: Dict[str, str] = {}
            for r_key, r_entry in list(self.remote_players.items()):
                if r_entry.get("is_host"):
                    continue
                if self.server_peer_id and r_key == self.server_peer_id:
                    continue
                p_id = str(r_entry.get("peer_id") or r_key)
                if p_id:
                    survivors.add(p_id)
                    if r_entry.get("addr"):
                        addrs[p_id] = str(r_entry["addr"])
            self.last_survivor_peer_ids = sorted(survivors)
            self.last_survivor_addrs = addrs
            self.remote_players.clear()
            if self.on_disconnect_callback:
                self.on_disconnect_callback()
        elif event_type == "CACHE_CLIENT_STATE":
            identity, addr_ip, state_data, peer_id = payload
            if self.host_client_state_cacher:
                try:
                    self.host_client_state_cacher(identity, addr_ip, state_data, peer_id=peer_id)
                except TypeError:
                    self.host_client_state_cacher(identity, addr_ip, state_data)
        elif event_type == "DAMAGE_EVENT":
            if self.host_damage_handler:
                self.host_damage_handler(*payload)
        elif event_type == "HEAL_EVENT":
            if self.host_heal_handler:
                self.host_heal_handler(*payload)
        elif event_type == "RESPITE_ACTION":
            if self.host_respite_handler:
                self.host_respite_handler(*payload)
        elif event_type == "RETURN_TO_SANCTUARY":
            if self.host_return_sanctuary_handler:
                self.host_return_sanctuary_handler()

    def process_inbound_events(self) -> int:
        """Process all queued inbound events on the calling (main) thread."""
        events = self.drain_inbound()
        for event_type, payload in events:
            self._dispatch_inbound_event(event_type, payload)
        return len(events)

    def start_hosting(self) -> None:
        """Start the UDP discovery broadcast, TCP handshake server, and 20Hz UDP sync."""
        if self.is_hosting:
            return
        self.stop_network()

        self.is_hosting = True
        self.is_connected = True
        self._ever_connected = True
        self._yielding_host = False
        self.network_mode = "HOST"
        self.stop_event = threading.Event()
        stop_signal = self.stop_event
        self._scanner_stop_event = threading.Event()
        scanner_stop = self._scanner_stop_event
        self._tcp_ready = threading.Event()

        t_discovery = threading.Thread(
            target=self._broadcast_loop, args=(stop_signal,), name="NetBroadcaster", daemon=True
        )
        t_discovery.start()
        self.threads.append(t_discovery)

        t_scanner = threading.Thread(
            target=self._scanner_loop, args=(scanner_stop,), name="NetHostTieScanner", daemon=True
        )
        t_scanner.start()
        self._scanner_thread = t_scanner
        self.threads.append(t_scanner)

        t_handshake = threading.Thread(
            target=self._tcp_server_loop, args=(stop_signal,), name="NetTCPServer", daemon=True
        )
        t_handshake.start()
        self.threads.append(t_handshake)
        self._tcp_ready.wait(timeout=0.5)

        t_udp_recv = threading.Thread(
            target=self._udp_receive_loop, args=(stop_signal,), name="NetUDPReceiver", daemon=True
        )
        t_udp_recv.start()
        self.threads.append(t_udp_recv)

        t_udp_send = threading.Thread(
            target=self._udp_send_loop, args=(stop_signal,), name="NetUDPSender", daemon=True
        )
        t_udp_send.start()
        self.threads.append(t_udp_send)
        print(
            f"[NETWORK] HOSTING as '{self.identity}' (peer_id={self.peer_id}). "
            f"Discovery:{self.port}, TCP:{self.tcp_port}, UDP:{self.host_udp_port}"
        )

    def stop_searching(self) -> None:
        """Stop the UDP discovery scanner thread without clearing client session state."""
        self.is_searching = False
        if self._scanner_stop_event and not self._scanner_stop_event.is_set():
            self._scanner_stop_event.set()
        if self._scanner_thread is not None and self._scanner_thread.is_alive():
            if threading.current_thread() is not self._scanner_thread:
                self._scanner_thread.join(timeout=0.3)
        self._scanner_thread = None

    def stop_network(self, clear_inbox: bool = True) -> None:
        """Stop all networking threads and reset session state."""
        self.stop_searching()
        if self.stop_event and not self.stop_event.is_set():
            self._send_disconnect_signal()
            self.stop_event.set()

        if self._outbox_thread is not None and self._outbox_thread.is_alive():
            try:
                self._outbound_queue.put_nowait(None)
            except queue.Full:
                pass

        self.is_hosting = False
        self.is_searching = False
        self.is_connected = False
        self.network_mode = "OFFLINE"
        with self._lock:
            self.found_hosts = {}
            self.found_host_peers = {}
            self.connected_peers = {}
            if clear_inbox:
                self._inbound_queue.clear()
        self.remote_players = {}
        self.server_address = None
        self.server_peer_id = None

        current = threading.current_thread()
        for t in self.threads:
            if t is not current and t.is_alive():
                t.join(timeout=0.2)
        self.threads = []
        self._outbox_thread = None
        while not self._outbound_queue.empty():
            try:
                self._outbound_queue.get_nowait()
            except queue.Empty:
                break
        print("[NETWORK] Cleanly stopped all network threads.")

    def _send_disconnect_signal(self) -> None:
        """Send a final DISCONNECT UDP packet to connected peers or host."""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = json.dumps(
                {"type": "DISCONNECT", "peer_id": self.peer_id, "identity": self.identity}
            ).encode("utf-8")
            if self.network_mode == "HOST":
                with self._lock:
                    peers = list(self.connected_peers.values())
                for peer_info in peers:
                    target_addr = peer_info.get("addr")
                    target_port = peer_info.get("udp_port") or self.host_udp_port
                    if target_addr:
                        sock.sendto(payload, (target_addr, int(target_port)))
            elif self.network_mode == "CLIENT" and self.server_address:
                sock.sendto(payload, (self.server_address, self.host_udp_port))
        except OSError as exc:
            logger.debug("Disconnect signal send failed: %s", exc)
        finally:
            if sock is not None:
                sock.close()

    def start_searching(self) -> None:
        """Start the UDP scanner to find active LAN hosts."""
        if self.is_searching:
            return
        self.stop_network()
        with self._lock:
            self.found_hosts = {}
        self.is_searching = True
        self._scanner_stop_event = threading.Event()
        stop_signal = self._scanner_stop_event
        t_scanner = threading.Thread(
            target=self._scanner_loop, args=(stop_signal,), name="NetScanner", daemon=True
        )
        t_scanner.start()
        self._scanner_thread = t_scanner
        self.threads.append(t_scanner)
        print(f"[NETWORK] SEARCHING for hosts on port {self.port}")

    def _ensure_outbox_worker(self) -> None:
        """Ensure the background TCP outbox worker thread is running for client events."""
        if self._outbox_thread is not None and self._outbox_thread.is_alive():
            return
        if self.stop_event.is_set():
            self.stop_event = threading.Event()
        t_out = threading.Thread(
            target=self._tcp_outbox_loop, args=(self.stop_event,), name="NetTCPOutbox", daemon=True
        )
        t_out.start()
        self._outbox_thread = t_out
        self.threads.append(t_out)

    def _enqueue_reliable_tcp(self, payload: Dict[str, Any]) -> None:
        """Enqueue a reliable TCP message for non-blocking background delivery to the Host."""
        if not self.server_address:
            return
        if self.is_connected:
            self._ensure_outbox_worker()
        item = (self.server_address, self.tcp_port, payload)
        try:
            self._outbound_queue.put_nowait(item)
        except queue.Full:
            try:
                self._outbound_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._outbound_queue.put_nowait(item)
            except queue.Full:
                logger.debug("Dropped outbound TCP event due to full queue: %s", payload.get("type"))

    def _tcp_outbox_loop(self, stop_signal: threading.Event) -> None:
        """Background worker that sends framed TCP control events without stalling the main loop."""
        while not stop_signal.is_set():
            try:
                item = self._outbound_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break
            host_addr, tcp_port, payload = item
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.5)
                sock.connect((host_addr, tcp_port))
                _send_framed_json(sock, payload)
            except (OSError, socket.timeout, ValueError) as exc:
                logger.debug("Outbound TCP %s delivery failed: %s", payload.get("type"), exc)
            finally:
                if sock is not None:
                    sock.close()

    def connect_to_host(self, address: str) -> bool:
        """Attempt to connect to a host via framed TCP handshake."""
        self.stop_searching()
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((address, self.tcp_port))

            handshake = {
                "type": "HANDSHAKE",
                "peer_id": self.peer_id,
                "identity": self.identity,
                "udp_port": self.local_udp_port,
            }
            _send_framed_json(sock, handshake)
            response = _recv_framed_json(sock)
            if not response:
                return False

            if response.get("status") == "ACCEPTED":
                self.server_address = address
                self.server_peer_id = response.get("peer_id")
                self.server_last_seen = time.time()
                self.is_connected = True
                self._ever_connected = True
                self.network_mode = "CLIENT"
                self.is_searching = False

                restored = response.get("restored_state")
                if restored and self.client_restored_state_handler:
                    print("[NETWORK] Received RESTORED STATE from host.")
                    self.client_restored_state_handler(restored)

                if self.on_handshake_accepted:
                    try:
                        self.on_handshake_accepted(response)
                    except (TypeError, ValueError, KeyError, RuntimeError):
                        pass

                self.stop_event = threading.Event()
                stop_signal = self.stop_event

                t_udp_recv = threading.Thread(
                    target=self._udp_receive_loop, args=(stop_signal,), name="NetUDPReceiver", daemon=True
                )
                t_udp_recv.start()
                self.threads.append(t_udp_recv)

                t_udp_send = threading.Thread(
                    target=self._udp_send_loop, args=(stop_signal,), name="NetUDPSender", daemon=True
                )
                t_udp_send.start()
                self.threads.append(t_udp_send)

                self._ensure_outbox_worker()
                print(f"[NETWORK] CONNECTED to {address} as CLIENT (peer_id={self.peer_id}).")
                return True
            print(f"[NETWORK] Connection REJECTED by host: {response.get('reason')}")
        except (OSError, socket.timeout, json.JSONDecodeError, ValueError, struct.error) as exc:
            print(f"[NETWORK] Connection FAILED: {exc}")
        finally:
            if sock is not None:
                sock.close()
        return False

    def request_map(self) -> Optional[Dict[str, Any]]:
        """Phase 3: Client requests the full map JSON from the Host via framed TCP."""
        if not self.is_connected or not self.server_address:
            return None

        sock = None
        try:
            print(f"[NETWORK] Requesting authoritative map from host {self.server_address}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.server_address, self.tcp_port))

            req = {"type": "MAP_REQUEST", "peer_id": self.peer_id, "identity": self.identity}
            _send_framed_json(sock, req)
            msg = _recv_framed_json(sock)
            if msg and msg.get("type") == "MAP_RESPONSE":
                map_data = msg.get("map_data")
                print("[NETWORK] Received framed map payload.")
                return map_data
        except (OSError, socket.timeout, json.JSONDecodeError, ValueError, struct.error) as exc:
            print(f"[NETWORK] Map request failed: {exc}")
        finally:
            if sock is not None:
                sock.close()
        return None

    def send_full_state(self, state_dict: Dict[str, Any]) -> None:
        """Phase 3: Enqueue full player profile (weapons, stats) to Host for caching."""
        if (not self.is_connected and self.network_mode != "CLIENT") or not self.server_address:
            return
        payload = {
            "type": "UPDATE_FULL_STATE",
            "peer_id": self.peer_id,
            "identity": self.identity,
            "state": state_dict,
        }
        self._enqueue_reliable_tcp(payload)

    def send_damage_event(self, target_type: str, target_id: Any, amount: float) -> None:
        """Phase 4: Non-blockingly notify Host of damage dealt to shared entities."""
        if self.network_mode != "CLIENT" or not self.server_address:
            return
        payload = {
            "type": "DAMAGE_EVENT",
            "peer_id": self.peer_id,
            "identity": self.identity,
            "target_type": target_type,
            "target_id": target_id,
            "amount": amount,
        }
        self._enqueue_reliable_tcp(payload)

    def send_heal_event(self, amount: float) -> None:
        """Phase 4: Non-blockingly notify Host of healing action."""
        if self.network_mode != "CLIENT" or not self.server_address:
            return
        payload = {
            "type": "HEAL_EVENT",
            "peer_id": self.peer_id,
            "identity": self.identity,
            "amount": amount,
        }
        self._enqueue_reliable_tcp(payload)

    def send_respite_event(
        self, action_type: str, marked_idx: Optional[int] = None, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Phase 4: Non-blockingly notify Host of Respite action (REST, UPGRADE)."""
        if self.network_mode != "CLIENT" or not self.server_address:
            return
        payload = {
            "type": "RESPITE_ACTION",
            "peer_id": self.peer_id,
            "identity": self.identity,
            "action": action_type,
            "marked_idx": marked_idx,
            "data": data or {},
        }
        self._enqueue_reliable_tcp(payload)

    def send_return_to_sanctuary_event(self) -> None:
        """Notify Host that a Client requested a party return to Sanctuary."""
        if self.network_mode != "CLIENT" or not self.server_address:
            return
        payload = {
            "type": "RETURN_TO_SANCTUARY",
            "peer_id": self.peer_id,
            "identity": self.identity,
        }
        self._enqueue_reliable_tcp(payload)

    def _yield_host_to(self, target_ip: str, other_peer_id: str) -> None:
        """Step down from HOST mode and connect as CLIENT to a lower-peer_id Host."""
        with self._lock:
            if self._yielding_host or self.network_mode != "HOST":
                return
            self._yielding_host = True
        print(
            f"[NETWORK] Tie-breaker: yielding HOST (peer_id={self.peer_id}) "
            f"to lower peer_id={other_peer_id} at {target_ip}"
        )
        self.stop_network(clear_inbox=False)
        self.connect_to_host(target_ip)

    # --- Thread Loops ---

    def _broadcast_loop(self, stop_signal: threading.Event) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while not stop_signal.is_set():
                payload = json.dumps({"peer_id": self.peer_id, "identity": self.identity}).encode("utf-8")
                try:
                    sock.sendto(payload, ("<broadcast>", self.port))
                except OSError as exc:
                    logger.debug("UDP broadcast send failed: %s", exc)
                for _ in range(4):
                    lo_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        lo_sock.sendto(payload, ("127.0.0.1", self.port))
                    except OSError:
                        pass
                    finally:
                        lo_sock.close()
                for _ in range(4):
                    if stop_signal.is_set():
                        break
                    time.sleep(0.1)
        finally:
            sock.close()

    def _scanner_loop(self, stop_signal: threading.Event) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass

            try:
                sock.bind(("", self.port))
            except OSError as exc:
                logger.debug("UDP scanner bind failed on port %s: %s", self.port, exc)
                return

            sock.settimeout(0.25)
            while not stop_signal.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                    raw_text = data.decode("utf-8", errors="replace")
                    host_name = raw_text
                    host_peer_id = ""
                    try:
                        parsed = json.loads(raw_text)
                        if isinstance(parsed, dict):
                            if "identity" in parsed:
                                host_name = str(parsed["identity"])
                            if "peer_id" in parsed:
                                host_peer_id = str(parsed["peer_id"])
                    except (json.JSONDecodeError, ValueError):
                        pass

                    if host_peer_id and host_peer_id == self.peer_id:
                        continue

                    if self.network_mode == "HOST" and host_peer_id and host_peer_id != self.peer_id:
                        if self.peer_id > host_peer_id and not self._yielding_host:
                            threading.Thread(
                                target=self._yield_host_to,
                                args=(addr[0], host_peer_id),
                                name="NetHostTieYield",
                                daemon=True,
                            ).start()
                            return
                        continue

                    with self._lock:
                        self.found_hosts[addr[0]] = host_name
                        if host_peer_id:
                            self.found_host_peers[addr[0]] = host_peer_id
                except socket.timeout:
                    continue
                except OSError as exc:
                    logger.debug("UDP scanner recv error: %s", exc)
        finally:
            sock.close()

    def _tcp_server_loop(self, stop_signal: threading.Event) -> None:
        """Accept incoming TCP connections for framed handshakes, map requests, and events."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass

            bound = False
            for _ in range(20):
                if stop_signal.is_set():
                    return
                try:
                    sock.bind(("", self.tcp_port))
                    bound = True
                    break
                except OSError:
                    time.sleep(0.1)

            if not bound:
                print("[NETWORK] TCP Server Bind Error: Address still in use.")
                return

            sock.listen(8)
            sock.settimeout(0.5)
            if hasattr(self, "_tcp_ready") and self._tcp_ready is not None:
                self._tcp_ready.set()

            while not stop_signal.is_set():
                try:
                    conn, addr = sock.accept()
                    t = threading.Thread(target=self._handle_tcp_request, args=(conn, addr), daemon=True)
                    t.start()
                except socket.timeout:
                    continue
                except OSError as exc:
                    if not stop_signal.is_set():
                        print(f"[NETWORK] TCP Accept Error: {exc}")
        finally:
            sock.close()

    def _handle_tcp_request(self, conn: socket.socket, addr: Tuple[str, int]) -> None:
        """Handle a single framed TCP transaction (Handshake, Map Request, or Reliable Event)."""
        try:
            conn.settimeout(5.0)
            msg = _recv_framed_json(conn)
            if not msg:
                return

            m_type = msg.get("type")
            identity = msg.get("identity", "Unknown")
            peer_id = msg.get("peer_id") or f"{identity}@{addr[0]}"

            if m_type == "HANDSHAKE":
                print(f"[NETWORK] HANDSHAKE from {addr[0]} ({identity}, peer_id={peer_id})")
                client_udp_port = msg.get("udp_port", self.host_udp_port)

                with self._lock:
                    self.connected_peers[peer_id] = {
                        "peer_id": peer_id,
                        "identity": identity,
                        "addr": addr[0],
                        "last_seen": time.time(),
                        "udp_port": client_udp_port,
                        "is_host": False,
                    }
                self.enqueue_inbound("PEER_JOIN", (peer_id, identity))

                restored = None
                if self.host_client_state_restorer:
                    try:
                        restored = self.host_client_state_restorer(identity, addr[0], peer_id=peer_id)
                    except TypeError:
                        restored = self.host_client_state_restorer(identity, addr[0])

                response = {
                    "status": "ACCEPTED",
                    "peer_id": self.peer_id,
                    "identity": self.identity,
                    "restored_state": restored,
                }
                if self.host_status_provider:
                    try:
                        status_extra = self.host_status_provider()
                        if isinstance(status_extra, dict):
                            response.update(status_extra)
                    except (TypeError, ValueError, KeyError, RuntimeError):
                        pass
                _send_framed_json(conn, response)

            elif m_type == "MAP_REQUEST":
                print(f"[NETWORK] Map requested by {identity} ({addr[0]}, peer_id={peer_id})")
                if self.host_map_provider:
                    map_data = self.host_map_provider()
                    response = {"type": "MAP_RESPONSE", "map_data": map_data}
                    _send_framed_json(conn, response)
                else:
                    print("[NETWORK] Map provider not ready.")

            elif m_type == "UPDATE_FULL_STATE":
                state_data = msg.get("state")
                self.enqueue_inbound("CACHE_CLIENT_STATE", (identity, addr[0], state_data, peer_id))

            elif m_type == "DAMAGE_EVENT":
                self.enqueue_inbound(
                    "DAMAGE_EVENT", (msg.get("target_type"), msg.get("target_id"), msg.get("amount"))
                )

            elif m_type == "HEAL_EVENT":
                self.enqueue_inbound("HEAL_EVENT", (peer_id, msg.get("amount")))

            elif m_type == "RESPITE_ACTION":
                self.enqueue_inbound(
                    "RESPITE_ACTION", (peer_id, msg.get("action"), msg.get("marked_idx"), msg.get("data"))
                )

            elif m_type == "RETURN_TO_SANCTUARY":
                self.enqueue_inbound("RETURN_TO_SANCTUARY", peer_id)

        except (OSError, socket.timeout, json.JSONDecodeError, ValueError, struct.error) as exc:
            logger.debug("TCP request error from %s: %s", addr, exc)
        finally:
            conn.close()

    def _send_udp_state_packet(self, sock: socket.socket, payload: bytes) -> None:
        """Send an encoded UDP state packet to all connected peers or the server."""
        if self.network_mode == "HOST":
            with self._lock:
                peers = list(self.connected_peers.values())
            for peer_info in peers:
                target_addr = peer_info.get("addr")
                target_port = peer_info.get("udp_port") or self.host_udp_port
                if target_addr:
                    sock.sendto(payload, (target_addr, int(target_port)))
        elif self.network_mode == "CLIENT" and self.server_address:
            sock.sendto(payload, (self.server_address, self.host_udp_port))

    def _udp_send_loop(self, stop_signal: threading.Event) -> None:
        """Continuously send 20Hz local player / host world state via UDP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        try:
            while not stop_signal.is_set():
                if self.network_mode == "HOST":
                    with self._lock:
                        has_peers = bool(self.connected_peers)
                    if not has_peers:
                        time.sleep(1.0 / 20.0)
                        continue

                payload_data: Dict[str, Any] = {
                    "type": "HEARTBEAT",
                    "peer_id": self.peer_id,
                    "identity": self.identity,
                    "is_host": self.network_mode == "HOST",
                    "time": time.time(),
                }
                if self.local_state_provider:
                    try:
                        payload_data.update(self.local_state_provider())
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logger.debug("local_state_provider error: %s", exc)

                try:
                    payload = json.dumps(payload_data).encode("utf-8")
                    self._send_udp_state_packet(sock, payload)
                except OSError as exc:
                    if not stop_signal.is_set():
                        logger.debug("UDP send error: %s", exc)

                time.sleep(1.0 / 20.0)
        finally:
            sock.close()

    def _udp_receive_loop(self, stop_signal: threading.Event) -> None:
        """Continuously receive UDP state packets and enqueue them for the main thread."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass

            bound = False
            for _ in range(20):
                if stop_signal.is_set():
                    return
                try:
                    sock.bind(("", self.local_udp_port))
                    bound = True
                    break
                except OSError:
                    time.sleep(0.1)

            if not bound:
                print("[NETWORK] UDP State Receiver Bind Error: Address still in use.")
                return

            sock.settimeout(1.0)

            while not stop_signal.is_set():
                try:
                    data, addr = sock.recvfrom(65536)
                    if not data:
                        continue
                    msg = json.loads(data.decode("utf-8"))
                    identity = msg.get("identity", "Unknown")
                    msg_peer_id = msg.get("peer_id")
                    peer_key = msg_peer_id or identity

                    if msg.get("type") == "DISCONNECT":
                        print(f"[NETWORK] Peer {addr[0]} ({identity}, peer_id={peer_key}) DISCONNECTED CLEANLY.")
                        if self.network_mode == "HOST":
                            with self._lock:
                                self.connected_peers.pop(peer_key, None)
                                for k, info in list(self.connected_peers.items()):
                                    if info.get("addr") == addr[0] and info.get("identity") == identity:
                                        self.connected_peers.pop(k, None)
                            self.enqueue_inbound("PEER_DISCONNECT", (peer_key, identity))
                        elif self.network_mode == "CLIENT" and addr[0] == self.server_address:
                            self.is_connected = False
                            self.enqueue_inbound("HOST_DISCONNECT", None)
                        continue

                    # Ignore our own packets (by peer_id when present, or identity fallback)
                    if msg_peer_id is not None:
                        if msg_peer_id == self.peer_id:
                            continue
                    elif identity == self.identity:
                        continue

                    now = time.time()
                    if self.network_mode == "HOST":
                        with self._lock:
                            if peer_key in self.connected_peers:
                                self.connected_peers[peer_key]["last_seen"] = now
                    elif self.network_mode == "CLIENT":
                        if addr[0] == self.server_address:
                            self.server_last_seen = now

                    self.enqueue_inbound("REMOTE_STATE", (addr[0], msg))

                except socket.timeout:
                    self._check_timeouts()
                    continue
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    if not stop_signal.is_set():
                        logger.debug("UDP recv error: %s", exc)
        finally:
            sock.close()

    def _check_timeouts(self) -> None:
        now = time.time()
        timeout = 5.0
        if self.network_mode == "HOST":
            expired: List[Tuple[str, str, str]] = []
            with self._lock:
                for peer_key, info in list(self.connected_peers.items()):
                    if now - info.get("last_seen", now) > timeout:
                        expired.append((peer_key, info.get("identity", "Unknown"), info.get("addr", "")))
                        del self.connected_peers[peer_key]
            for peer_key, identity, addr_ip in expired:
                print(f"[NETWORK] Peer {addr_ip} ({identity}, peer_id={peer_key}) timed out.")
                self.enqueue_inbound("PEER_DISCONNECT", (peer_key, identity))

        elif self.network_mode == "CLIENT" and self.server_address:
            if now - self.server_last_seen > timeout:
                print(f"[NETWORK] Host {self.server_address} timed out.")
                if self.is_connected:
                    self.is_connected = False
                    self.enqueue_inbound("HOST_DISCONNECT", None)
                    self.stop_network(clear_inbox=False)
