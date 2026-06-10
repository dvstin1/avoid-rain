import socket
import threading
import time
from constants import PLAYER_NAME, LAN_PORT

class NetworkManager:
    """
    Handles local network discovery (LAN) using UDP broadcasting.
    Phase 1: Background discovery and host identification.
    """
    
    def __init__(self, port=LAN_PORT, identity=PLAYER_NAME):
        self.port = port
        self.identity = identity
        self.is_hosting = False
        self.is_searching = False
        self.found_hosts = {} # {address: identity}
        
        self.stop_event = threading.Event()
        self.broadcast_thread = None
        self.scanner_thread = None

    def start_hosting(self):
        """Starts the UDP broadcast loop to announce this host on the network."""
        if self.is_hosting:
            return
        
        self.is_hosting = True
        self.stop_event.clear()
        self.broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.broadcast_thread.start()
        print(f"[NETWORK] Started hosting as '{self.identity}' on port {self.port}")

    def stop_hosting(self):
        self.is_hosting = False
        self.stop_event.set()
        if self.broadcast_thread:
            self.broadcast_thread.join(timeout=1.0)
        print("[NETWORK] Stopped hosting.")

    def start_searching(self):
        """Starts the UDP scanner loop to find hosts on the network."""
        if self.is_searching:
            return
        
        self.is_searching = True
        self.stop_event.clear()
        self.scanner_thread = threading.Thread(target=self._scanner_loop, daemon=True)
        self.scanner_thread.start()
        print(f"[NETWORK] Started searching for hosts on port {self.port}")

    def stop_searching(self):
        self.is_searching = False
        self.stop_event.set()
        if self.scanner_thread:
            self.scanner_thread.join(timeout=1.0)
        print("[NETWORK] Stopped searching.")

    def _broadcast_loop(self):
        """UDP Broadcast loop: sends identity payload periodically."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        payload = self.identity.encode('utf-8')
        
        while self.is_hosting and not self.stop_event.is_set():
            try:
                # Broadcast to the subnet
                sock.sendto(payload, ('<broadcast>', self.port))
            except Exception as e:
                print(f"[NETWORK] Broadcast error: {e}")
            
            time.sleep(2.0) # Broadcast every 2 seconds
        
        sock.close()

    def _scanner_loop(self):
        """UDP Scanner loop: listens for broadcast identity payloads."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Handle potential platform differences for REUSEADDR/REUSEPORT
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
            
        sock.bind(('', self.port))
        sock.settimeout(1.0) # Check stop_event periodically
        
        while self.is_searching and not self.stop_event.is_set():
            try:
                data, addr = sock.recvfrom(1024)
                identity = data.decode('utf-8')
                
                if addr[0] not in self.found_hosts:
                    self.found_hosts[addr[0]] = identity
                    print(f"[NETWORK] Found Host: {identity} at {addr[0]}")
                else:
                    # Update identity if changed
                    self.found_hosts[addr[0]] = identity
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[NETWORK] Scanner error: {e}")
        
        sock.close()

if __name__ == "__main__":
    # Test block for standalone verification
    import sys
    
    nm = NetworkManager()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "host":
            nm.start_hosting()
            try:
                while True: time.sleep(1)
            except KeyboardInterrupt:
                nm.stop_hosting()
        elif sys.argv[1] == "search":
            nm.start_searching()
            try:
                while True: time.sleep(1)
            except KeyboardInterrupt:
                nm.stop_searching()
    else:
        print("Usage: python engine/network_manager.py [host|search]")
