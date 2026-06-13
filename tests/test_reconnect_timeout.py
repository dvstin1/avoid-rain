import pytest
import os
import time
from engine.game_state import GameState

# Ensure headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame

@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()

def test_rapid_restart_hosting_timeout():
    """
    Reproduces the connection timeout by rapidly stopping and starting hosting.
    This simulates moving Sanctuary -> World -> Sanctuary -> World.
    """
    host_state = GameState(auto_load=False)
    host_state.network_manager.port = 52000
    host_state.network_manager.tcp_port = 52001
    host_state.network_manager.host_udp_port = 52002
    host_state.network_manager.local_udp_port = 52002
    host_state.network_manager.identity = "RapidHost"

    for i in range(10):
        print(f"\n[TEST] Cycle {i+1}")
        # 1. Start Hosting
        host_state.network_manager.start_hosting()
        time.sleep(0.05)
        
        # 2. Stop Hosting (Sanctuary)
        host_state.network_manager.stop_network()
        time.sleep(0.05)
    
    # 3. Final Start
    host_state.network_manager.start_hosting()
    
    # 4. Attempt to connect from Client
    client_state = GameState(auto_load=False)
    client_state.network_manager.port = 62000
    client_state.network_manager.tcp_port = 52001
    client_state.network_manager.host_udp_port = 52002
    client_state.network_manager.local_udp_port = 62002
    
    print("[TEST] Attempting connection...")
    connected = client_state.network_manager.connect_to_host("127.0.0.1")
    
    assert connected is True, "Client failed to connect after rapid host restarts."
