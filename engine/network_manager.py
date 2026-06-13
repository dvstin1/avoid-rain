import socket
import threading
import time
import json
import random
from constants import DEFAULT_PLAYER_NAME, LAN_PORT

class NetworkManager:
    """
    Handles local network discovery (LAN) and peer-to-peer synchronization.
    Phase 3: Map Synchronization and Client Persistence.
    """
    
    def __init__(self, port=LAN_PORT, identity=DEFAULT_PLAYER_NAME, local_udp_port=None, host_tcp_port=None, host_udp_port=None):
        self.port = port
        self.tcp_port = host_tcp_port if host_tcp_port is not None else port + 1
        
        # Determine the port to listen on for UDP state payloads
        # If hosting, we listen on our explicit udp_sync_port. If client, we listen on local_udp_port (if provided)
        self.host_udp_port = host_udp_port if host_udp_port is not None else port + 2
        self.local_udp_port = local_udp_port if local_udp_port is not None else self.host_udp_port
        
        self.identity = identity
        
        self.is_hosting = False
        self.is_searching = False
        self.is_connected = False
        self.network_mode = "OFFLINE" # "OFFLINE", "HOST", "CLIENT"
        
        self.found_hosts = {} # {address: identity}
        self.connected_peers = {} # {address: {"identity": str, "last_seen": float}}
        self.server_address = None # For client mode
        self.server_last_seen = 0.0
        
        # State Data
        self.remote_players = {} # {address: {"x": float, "y": float, "hp": int}}
        
        # Callbacks (Injected by GameState)
        self.local_state_provider = None # UDP: returns {"x": f, "y": f, "hp": i}
        self.remote_state_handler = None # UDP: accepts (addr, data)
        self.on_disconnect_callback = None 
        
        self.host_map_provider = None # TCP: returns full map dict
        self.host_client_state_restorer = None # TCP: accepts (identity, ip) returns state dict or None
        self.host_client_state_cacher = None # TCP: accepts (identity, ip, state_dict)
        self.host_damage_handler = None # TCP: accepts (target_type, target_id, amount)
        self.client_restored_state_handler = None # TCP: accepts state_dict
        
        self.stop_event = threading.Event()
        self.threads = []

    def start_hosting(self):
        """Starts the UDP discovery broadcast and TCP handshake server."""
        if self.is_hosting: return
        self.stop_network() # Clean start

        self.is_hosting = True
        self.network_mode = "HOST"
        self.stop_event = threading.Event()
        stop_signal = self.stop_event

        # UDP Discovery Broadcast
        t_discovery = threading.Thread(target=self._broadcast_loop, args=(stop_signal,), name="NetBroadcaster", daemon=True)
        t_discovery.start()
        self.threads.append(t_discovery)

        # TCP Request/Handshake Server
        t_handshake = threading.Thread(target=self._tcp_server_loop, args=(stop_signal,), name="NetTCPServer", daemon=True)
        t_handshake.start()
        self.threads.append(t_handshake)

        # UDP State Sync Receiver
        t_udp_recv = threading.Thread(target=self._udp_receive_loop, args=(stop_signal,), name="NetUDPReceiver", daemon=True)
        t_udp_recv.start()
        self.threads.append(t_udp_recv)

        # UDP State Sync Sender
        t_udp_send = threading.Thread(target=self._udp_send_loop, args=(stop_signal,), name="NetUDPSender", daemon=True)
        t_udp_send.start()
        self.threads.append(t_udp_send)
        print(f"[NETWORK] HOSTING as '{self.identity}'. Discovery:{self.port}, TCP:{self.tcp_port}, UDP:{self.host_udp_port}")

    def stop_network(self):
        """Stops all networking threads and resets state."""
        if self.stop_event and not self.stop_event.is_set():
            self._send_disconnect_signal()
            self.stop_event.set()

        self.is_hosting = False
        self.is_searching = False
        self.is_connected = False
        self.network_mode = "OFFLINE"
        self.found_hosts = {}
        self.connected_peers = {}
        self.remote_players = {} 
        self.server_address = None

        for t in self.threads:
            t.join(timeout=0.2)
        self.threads = []
        print("[NETWORK] Cleanly stopped all network threads.")

    def _send_disconnect_signal(self):
        """Sends a final DISCONNECT packet to peers."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = json.dumps({"type": "DISCONNECT", "identity": self.identity}).encode('utf-8')
            if self.network_mode == "HOST":
                for addr in list(self.connected_peers.keys()):
                    sock.sendto(payload, (addr, self.host_udp_port))
            elif self.network_mode == "CLIENT" and self.server_address:
                sock.sendto(payload, (self.server_address, self.host_udp_port))
            sock.close()
        except: pass

    def start_searching(self):
        """Starts the UDP scanner to find active hosts."""
        if self.is_searching: return
        self.stop_network() # Ensure clean state
        self.found_hosts = {} # Reset list
        self.is_searching = True
        self.stop_event = threading.Event()
        stop_signal = self.stop_event
        t_scanner = threading.Thread(target=self._scanner_loop, args=(stop_signal,), name="NetScanner", daemon=True)
        t_scanner.start()
        self.threads.append(t_scanner)
        print(f"[NETWORK] SEARCHING for hosts on port {self.port}")


    def connect_to_host(self, address):
        """Attempts to connect to a host via TCP handshake."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((address, self.tcp_port))
            
            # Send Handshake (include local_udp_port so Host knows where to send state)
            handshake = {"type": "HANDSHAKE", "identity": self.identity, "udp_port": self.local_udp_port}
            sock.sendall(json.dumps(handshake).encode('utf-8'))
            
            # Receive Acknowledgment & Potential Restored State
            data = sock.recv(4096)
            if not data: return False
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACCEPTED":
                self.server_address = address
                self.server_last_seen = time.time()
                self.is_connected = True
                self.network_mode = "CLIENT"
                self.is_searching = False 
                
                # Check for restored state
                restored = response.get("restored_state")
                if restored and self.client_restored_state_handler:
                    print(f"[NETWORK] Received RESTORED STATE from host.")
                    self.client_restored_state_handler(restored)

                # Start Sync Threads
                self.stop_event = threading.Event()
                stop_signal = self.stop_event

                t_udp_recv = threading.Thread(target=self._udp_receive_loop, args=(stop_signal,), name="NetUDPReceiver", daemon=True)
                t_udp_recv.start()
                self.threads.append(t_udp_recv)

                t_udp_send = threading.Thread(target=self._udp_send_loop, args=(stop_signal,), name="NetUDPSender", daemon=True)
                t_udp_send.start()
                self.threads.append(t_udp_send)

                print(f"[NETWORK] CONNECTED to {address} as CLIENT.")
                return True
            else:
                print(f"[NETWORK] Connection REJECTED by host: {response.get('reason')}")
        except Exception as e:
            print(f"[NETWORK] Connection FAILED: {e}")
        return False

    def request_map(self):
        """Phase 3: Client requests the full map JSON from the Host via TCP."""
        if not self.is_connected or not self.server_address:
            return None
        
        try:
            print(f"[NETWORK] Requesting authoritative map from host {self.server_address}...")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.server_address, self.tcp_port))
            
            req = {"type": "MAP_REQUEST", "identity": self.identity}
            sock.sendall(json.dumps(req).encode('utf-8'))
            
            # Large Buffer for Map JSON
            chunks = []
            while True:
                chunk = sock.recv(16384)
                if not chunk: break
                chunks.append(chunk)
            
            full_data = b"".join(chunks)
            if not full_data: return None
            
            msg = json.loads(full_data.decode('utf-8'))
            if msg.get("type") == "MAP_RESPONSE":
                map_data = msg.get("map_data")
                print(f"[NETWORK] Received map payload ({len(full_data)//1024} KB).")
                return map_data
        except Exception as e:
            print(f"[NETWORK] Map request failed: {e}")
        return None

    def send_full_state(self, state_dict):
        """Phase 3: Client sends full profile (weapons, stats) to Host for caching."""
        if not self.is_connected or not self.server_address:
            return
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((self.server_address, self.tcp_port))
            
            payload = {
                "type": "UPDATE_FULL_STATE",
                "identity": self.identity,
                "state": state_dict
            }
            sock.sendall(json.dumps(payload).encode('utf-8'))
            sock.close()
        except Exception as e:
            print(f"[NETWORK] Full state update failed: {e}")

    def send_damage_event(self, target_type, target_id, amount):
        """Phase 4: Client sends damage events to the Host."""
        if not self.is_connected or not self.server_address: return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((self.server_address, self.tcp_port))
            payload = {
                "type": "DAMAGE_EVENT",
                "identity": self.identity,
                "target_type": target_type,
                "target_id": target_id,
                "amount": amount
            }
            sock.sendall(json.dumps(payload).encode('utf-8'))
            sock.close()
        except: pass

    # --- Thread Loops ---

    def _broadcast_loop(self, stop_signal):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        payload = self.identity.encode('utf-8')
        while not stop_signal.is_set():
            try: sock.sendto(payload, ('<broadcast>', self.port))
            except: pass
            # Sleep in small increments to remain responsive to stop signal
            for _ in range(20):
                if stop_signal.is_set(): break
                time.sleep(0.1)
        sock.close()

    def _scanner_loop(self, stop_signal):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError: pass
        
        try: sock.bind(('', self.port))
        except: return

        sock.settimeout(1.0)
        while not stop_signal.is_set():
            try:
                data, addr = sock.recvfrom(1024)
                self.found_hosts[addr[0]] = data.decode('utf-8')
            except socket.timeout: continue
            except: pass
        sock.close()

    def _tcp_server_loop(self, stop_signal):
        """Accepts incoming TCP connections for handshakes and requests."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError: pass
        
        # Retry binding in case old thread is still shutting down
        bound = False
        for _ in range(20):
            if stop_signal.is_set(): return
            try:
                sock.bind(('', self.tcp_port))
                bound = True
                break
            except Exception as e:
                time.sleep(0.1)
                
        if not bound:
            print("[NETWORK] TCP Server Bind Error: Address still in use.")
            return

        sock.listen(5)
        sock.settimeout(1.0)
        
        while not stop_signal.is_set():
            try:
                conn, addr = sock.accept()
                t = threading.Thread(target=self._handle_tcp_request, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout: continue
            except Exception as e:
                if not stop_signal.is_set():
                    print(f"[NETWORK] TCP Accept Error: {e}")
        sock.close()

    def _handle_tcp_request(self, conn, addr):
        """Handles single TCP transaction (Handshake, Map Request, State Update)."""
        try:
            conn.settimeout(5.0)
            data = conn.recv(8192) # Buff for initial request
            if not data: return
            msg = json.loads(data.decode('utf-8'))
            
            m_type = msg.get("type")
            identity = msg.get("identity", "Unknown")
            
            if m_type == "HANDSHAKE":
                print(f"[NETWORK] HANDSHAKE from {addr[0]} ({identity})")
                client_udp_port = msg.get("udp_port", self.host_udp_port)
                
                # Rule: Purify stale state for this identity to prevent "False Death" upon join
                if identity in self.remote_players:
                    del self.remote_players[identity]

                self.connected_peers[addr[0]] = {
                    "identity": identity, 
                    "last_seen": time.time(),
                    "udp_port": client_udp_port
                }
                
                # Check for restored state from GameState
                restored = None
                if self.host_client_state_restorer:
                    restored = self.host_client_state_restorer(identity, addr[0])
                
                response = {"status": "ACCEPTED", "identity": self.identity, "restored_state": restored}
                conn.sendall(json.dumps(response).encode('utf-8'))
                
            elif m_type == "MAP_REQUEST":
                print(f"[NETWORK] Map requested by {identity} ({addr[0]})")
                if self.host_map_provider:
                    map_data = self.host_map_provider()
                    response = {"type": "MAP_RESPONSE", "map_data": map_data}
                    conn.sendall(json.dumps(response).encode('utf-8'))
                else:
                    print("[NETWORK] Map provider not ready.")

            elif m_type == "UPDATE_FULL_STATE":
                state_data = msg.get("state")
                if self.host_client_state_cacher:
                    self.host_client_state_cacher(identity, addr[0], state_data)

            elif m_type == "DAMAGE_EVENT":
                if self.host_damage_handler:
                    self.host_damage_handler(msg.get("target_type"), msg.get("target_id"), msg.get("amount"))

        except Exception as e:
            print(f"[NETWORK] TCP request error: {e}")
        finally: 
            conn.close()

    def _udp_send_loop(self, stop_signal):
        """Continuously sends local player state via UDP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        
        while not stop_signal.is_set():
            payload_data = {"type": "HEARTBEAT", "identity": self.identity, "time": time.time()}
            if self.local_state_provider:
                try: 
                    payload_data.update(self.local_state_provider())
                except Exception as e: 
                    print(f"[NETWORK] local_state_provider Error: {e}")
            
            try:
                payload = json.dumps(payload_data).encode('utf-8')
                if self.network_mode == "HOST":
                    for addr, peer_info in list(self.connected_peers.items()):
                        target_port = peer_info.get("udp_port", self.host_udp_port)
                        sock.sendto(payload, (addr, target_port))
                elif self.network_mode == "CLIENT" and self.server_address:
                    sock.sendto(payload, (self.server_address, self.host_udp_port))
            except Exception as e:
                if not stop_signal.is_set():
                    print(f"[NETWORK] UDP Send Error: {e} (Payload Size: {len(payload_data.get('enemies', []))} enemies)")
            
            time.sleep(1.0 / 20.0) # 20Hz Sync
        sock.close()

    def _udp_receive_loop(self, stop_signal):
        """Continuously listens for remote player state payloads."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError: pass
        
        # Retry binding in case old thread is still shutting down
        bound = False
        for _ in range(20):
            if stop_signal.is_set(): return
            try:
                sock.bind(('', self.local_udp_port))
                bound = True
                break
            except Exception as e:
                time.sleep(0.1)
                
        if not bound:
            print("[NETWORK] UDP State Receiver Bind Error: Address still in use.")
            sock.close()
            return
            
        sock.settimeout(1.0)
        
        while not stop_signal.is_set():
            try:
                data, addr = sock.recvfrom(65536)
                if not data: continue
                msg = json.loads(data.decode('utf-8'))
                
                if msg.get("type") == "DISCONNECT":
                    identity = msg.get("identity", "Unknown")
                    print(f"[NETWORK] Peer {addr[0]} ({identity}) has DISCONNECTED CLEANLY.")
                    if self.network_mode == "HOST" and addr[0] in self.connected_peers:
                        del self.connected_peers[addr[0]]
                    elif self.network_mode == "CLIENT" and addr[0] == self.server_address:
                        self.is_connected = False
                        if self.on_disconnect_callback: self.on_disconnect_callback()
                    
                    if identity in self.remote_players: del self.remote_players[identity]
                    continue

                identity = msg.get("identity", "Unknown")

                # 1. Identity Check: Never process our own packets
                if identity == self.identity:
                    continue

                # 2. Update peer activity
                if self.network_mode == "HOST":
                    if addr[0] in self.connected_peers:
                        self.connected_peers[addr[0]]["last_seen"] = time.time()
                elif self.network_mode == "CLIENT":
                    if addr[0] == self.server_address:
                        self.server_last_seen = time.time()
                
                # 3. Handle state update
                if self.remote_state_handler:
                    self.remote_state_handler(addr[0], msg)

                    
            except socket.timeout:
                self._check_timeouts()
                continue
            except Exception as e:
                if not stop_signal.is_set():
                    print(f"[NETWORK] UDP Recv Error: {e}")
        sock.close()

    def _check_timeouts(self):
        now = time.time()
        timeout = 5.0
        if self.network_mode == "HOST":
            to_remove = []
            for addr, info in self.connected_peers.items():
                if now - info["last_seen"] > timeout:
                    to_remove.append(addr)
            
            for addr in to_remove:
                identity = self.connected_peers[addr].get("identity", "Unknown")
                print(f"[NETWORK] Peer {addr} ({identity}) timed out.")
                if addr in self.connected_peers: del self.connected_peers[addr]
                if identity in self.remote_players: del self.remote_players[identity]
        
        elif self.network_mode == "CLIENT" and self.server_address:
            if now - self.server_last_seen > timeout:
                print(f"[NETWORK] Host {self.server_address} timed out.")
                if self.is_connected:
                    self.is_connected = False
                    # Clear all ghosts on timeout
                    self.remote_players.clear()
                    if self.on_disconnect_callback: self.on_disconnect_callback()
                    self.stop_network()

if __name__ == "__main__":
    # Minimal standalone test would need significant rewrite for Phase 3, skip for now.
    pass
