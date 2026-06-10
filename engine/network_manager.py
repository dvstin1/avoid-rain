import socket
import threading
import time
import json
import random
from constants import PLAYER_NAME, LAN_PORT

class NetworkManager:
    """
    Handles local network discovery (LAN) and peer-to-peer synchronization.
    Phase 2: Handshake (TCP) and State Replication (UDP).
    """
    
    def __init__(self, port=LAN_PORT, identity=PLAYER_NAME):
        self.port = port
        self.tcp_port = port + 1
        self.udp_sync_port = port + 2
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
        self.local_state_provider = None # Callback returning {"x": f, "y": f, "hp": i}
        self.remote_state_handler = None # Callback accepting (addr, data)
        self.on_disconnect_callback = None # Callback for handling connection loss
        
        self.stop_event = threading.Event()
        self.threads = []

    def start_hosting(self):
        """Starts the UDP discovery broadcast and TCP handshake server."""
        if self.is_hosting: return
        self.stop_network() # Clean start
        
        self.is_hosting = True
        self.network_mode = "HOST"
        self.stop_event.clear()
        
        # UDP Discovery Broadcast
        t_discovery = threading.Thread(target=self._broadcast_loop, name="NetBroadcaster", daemon=True)
        t_discovery.start()
        self.threads.append(t_discovery)
        
        # TCP Handshake Server
        t_handshake = threading.Thread(target=self._tcp_server_loop, name="NetTCPServer", daemon=True)
        t_handshake.start()
        self.threads.append(t_handshake)
        
        # UDP State Sync Receiver
        t_udp_recv = threading.Thread(target=self._udp_receive_loop, name="NetUDPReceiver", daemon=True)
        t_udp_recv.start()
        self.threads.append(t_udp_recv)

        # UDP State Sync Sender
        t_udp_send = threading.Thread(target=self._udp_send_loop, name="NetUDPSender", daemon=True)
        t_udp_send.start()
        self.threads.append(t_udp_send)

        print(f"[NETWORK] HOSTING as '{self.identity}'. Discovery:{self.port}, TCP:{self.tcp_port}, UDP:{self.udp_sync_port}")

    def stop_network(self):
        """Stops all networking threads and resets state."""
        if not self.stop_event.is_set():
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
        
        # Threads are daemon, but we join for cleanliness
        for t in self.threads:
            t.join(timeout=0.1)
        self.threads = []
        print("[NETWORK] Cleanly stopped all network threads.")

    def _send_disconnect_signal(self):
        """Sends a final DISCONNECT packet to peers."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = json.dumps({"type": "DISCONNECT", "identity": self.identity}).encode('utf-8')
            if self.network_mode == "HOST":
                for addr in self.connected_peers:
                    sock.sendto(payload, (addr, self.udp_sync_port))
            elif self.network_mode == "CLIENT" and self.server_address:
                sock.sendto(payload, (self.server_address, self.udp_sync_port))
            sock.close()
        except: pass

    def start_searching(self):
        """Starts the UDP scanner to find active hosts."""
        if self.is_searching: return
        self.is_searching = True
        self.stop_event.clear()
        t_scanner = threading.Thread(target=self._scanner_loop, name="NetScanner", daemon=True)
        t_scanner.start()
        self.threads.append(t_scanner)
        print(f"[NETWORK] SEARCHING for hosts on port {self.port}")

    def connect_to_host(self, address):
        """Attempts to connect to a host via TCP handshake."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((address, self.tcp_port))
            
            # Send Handshake
            handshake = {"type": "HANDSHAKE", "identity": self.identity}
            sock.sendall(json.dumps(handshake).encode('utf-8'))
            
            # Receive Acknowledgment
            data = sock.recv(1024)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACCEPTED":
                self.server_address = address
                self.server_last_seen = time.time()
                self.is_connected = True
                self.network_mode = "CLIENT"
                self.is_searching = False # Stop searching once connected
                
                # Start Sync Threads
                t_udp_recv = threading.Thread(target=self._udp_receive_loop, name="NetUDPReceiver", daemon=True)
                t_udp_recv.start()
                self.threads.append(t_udp_recv)

                t_udp_send = threading.Thread(target=self._udp_send_loop, name="NetUDPSender", daemon=True)
                t_udp_send.start()
                self.threads.append(t_udp_send)
                
                print(f"[NETWORK] CONNECTED to {address} as CLIENT.")
                return True
            else:
                print(f"[NETWORK] Connection REJECTED by host: {response.get('reason')}")
        except Exception as e:
            print(f"[NETWORK] Connection FAILED: {e}")
        return False

    # --- Thread Loops ---

    def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        payload = self.identity.encode('utf-8')
        while self.is_hosting and not self.stop_event.is_set():
            try: 
                sock.sendto(payload, ('<broadcast>', self.port))
            except Exception as e: 
                if not self.stop_event.is_set():
                    print(f"[NETWORK] Broadcast error: {e}")
            time.sleep(2.0)
        sock.close()

    def _scanner_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError: pass
        
        try:
            sock.bind(('', self.port))
        except Exception as e:
            print(f"[NETWORK] Scanner bind error: {e}")
            sock.close()
            return

        sock.settimeout(1.0)
        while self.is_searching and not self.stop_event.is_set():
            try:
                data, addr = sock.recvfrom(1024)
                self.found_hosts[addr[0]] = data.decode('utf-8')
            except socket.timeout: continue
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"[NETWORK] Scanner recv error: {e}")
        sock.close()

    def _tcp_server_loop(self):
        """Accepts incoming TCP connections for handshakes."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('', self.tcp_port))
            sock.listen(5)
            sock.settimeout(1.0)
        except Exception as e:
            print(f"[NETWORK] TCP server bind error: {e}")
            sock.close()
            return
        
        while self.is_hosting and not self.stop_event.is_set():
            try:
                conn, addr = sock.accept()
                t = threading.Thread(target=self._handle_handshake, args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout: continue
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"[NETWORK] TCP accept error: {e}")
        sock.close()

    def _handle_handshake(self, conn, addr):
        try:
            data = conn.recv(1024)
            if not data: return
            msg = json.loads(data.decode('utf-8'))
            if msg.get("type") == "HANDSHAKE":
                identity = msg.get("identity", "Unknown")
                print(f"[NETWORK] HANDSHAKE from {addr[0]} ({identity})")
                
                self.connected_peers[addr[0]] = {"identity": identity, "last_seen": time.time()}
                response = {"status": "ACCEPTED", "identity": self.identity}
                conn.sendall(json.dumps(response).encode('utf-8'))
        except Exception as e:
            print(f"[NETWORK] Handshake handler error: {e}")
        finally: 
            conn.close()

    def _udp_send_loop(self):
        """Continuously sends local player state via UDP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        
        while (self.is_hosting or self.is_connected) and not self.stop_event.is_set():
            payload_data = {"type": "HEARTBEAT", "identity": self.identity, "time": time.time()}
            
            # Phase 2: Add actual gameplay data if available
            if self.local_state_provider:
                try:
                    game_data = self.local_state_provider()
                    payload_data.update(game_data)
                except: pass
            
            try:
                payload = json.dumps(payload_data).encode('utf-8')
                if self.network_mode == "HOST":
                    peers = list(self.connected_peers.keys())
                    for addr in peers:
                        sock.sendto(payload, (addr, self.udp_sync_port))
                        if random.random() < 0.01: # 1% Log
                            print(f"[NETWORK] Sent sync to client {addr}")
                elif self.network_mode == "CLIENT" and self.server_address:
                    sock.sendto(payload, (self.server_address, self.udp_sync_port))
                    if random.random() < 0.01: # 1% Log
                        print(f"[NETWORK] Sent sync to host {self.server_address}")
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"[NETWORK] UDP Send Error: {e}")
            
            time.sleep(1.0 / 10.0) # Lower frequency (10Hz) for debugging
        sock.close()

    def _udp_receive_loop(self):
        """Continuously listens for remote player state payloads."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError: pass
        
        try:
            sock.bind(('', self.udp_sync_port))
            sock.settimeout(1.0)
            print(f"[NETWORK] UDP Receiver Active on port {self.udp_sync_port}")
        except Exception as e:
            print(f"[NETWORK] UDP bind error: {e}")
            sock.close()
            return
        
        while (self.is_hosting or self.is_connected) and not self.stop_event.is_set():
            try:
                data, addr = sock.recvfrom(4096)
                if not data: continue
                
                msg = json.loads(data.decode('utf-8'))
                
                if msg.get("type") == "DISCONNECT":
                    identity = msg.get("identity", "Unknown")
                    print(f"[NETWORK] Peer {addr[0]} ({identity}) has DISCONNECTED CLEANLY.")
                    if self.network_mode == "HOST" and addr[0] in self.connected_peers:
                        del self.connected_peers[addr[0]]
                        if addr[0] in self.remote_players: del self.remote_players[addr[0]]
                    elif self.network_mode == "CLIENT" and addr[0] == self.server_address:
                        self.is_connected = False
                        if self.on_disconnect_callback: self.on_disconnect_callback()
                        self.stop_network()
                    continue

                if random.random() < 0.05: # 5% Log
                    print(f"[NETWORK] RECV from {addr[0]}: {msg.get('identity')} (Type: {msg.get('type')})")
                
                # Update peer tracking
                if addr[0] in self.connected_peers:
                    self.connected_peers[addr[0]]["last_seen"] = time.time()
                elif addr[0] == self.server_address:
                    self.server_last_seen = time.time()
                
                # Update remote player state
                self.remote_players[addr[0]] = msg
                
                if self.remote_state_handler:
                    self.remote_state_handler(addr[0], msg)
                    
            except socket.timeout:
                self._check_timeouts()
                continue
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"[NETWORK] UDP Recv Error: {e}")
        sock.close()

    def _check_timeouts(self):
        """Checks for timed out peers and handles disconnection."""
        now = time.time()
        timeout = 5.0 # Increased timeout for debugging stability
        
        if self.network_mode == "HOST":
            to_remove = []
            for addr, info in list(self.connected_peers.items()):
                if now - info["last_seen"] > timeout:
                    print(f"[NETWORK] Peer {addr} ({info['identity']}) timed out.")
                    to_remove.append(addr)
            for addr in to_remove:
                if addr in self.connected_peers: del self.connected_peers[addr]
                if addr in self.remote_players: del self.remote_players[addr]
                    
        elif self.network_mode == "CLIENT" and self.server_address:
            if now - self.server_last_seen > timeout:
                print(f"[NETWORK] Host {self.server_address} timed out.")
                # Use a flag to avoid recursive calls if stop_network is called within callback
                if self.is_connected:
                    self.is_connected = False 
                    if self.on_disconnect_callback:
                        self.on_disconnect_callback()
                    self.stop_network()

if __name__ == "__main__":
    import sys
    nm = NetworkManager()
    nm.local_state_provider = lambda: {"x": 100, "y": 200, "hp": 100}
    nm.remote_state_handler = lambda addr, data: print(f"Update from {addr}: {data}")

    if len(sys.argv) > 1:
        if sys.argv[1] == "host":
            nm.start_hosting()
            try:
                while True: time.sleep(1)
            except KeyboardInterrupt: nm.stop_network()
        elif sys.argv[1] == "search":
            nm.start_searching()
            try:
                while True:
                    if nm.found_hosts:
                        print(f"Found: {nm.found_hosts}")
                        target = list(nm.found_hosts.keys())[0]
                        if nm.connect_to_host(target):
                            while True: time.sleep(1)
                    time.sleep(1)
            except KeyboardInterrupt: nm.stop_network()
    else:
        print("Usage: python engine/network_manager.py [host|search]")
