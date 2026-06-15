import pytest
import os
import time
from engine.game_state import GameState
from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES, FLASK_HEAL_AMOUNT

# Ensure headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame

@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()

def test_client_healing_bug():
    """
    Reproduces the bug where Client healing consumes all charges and fails to sync HP.
    """
    # 1. Setup Host
    host_state = GameState(auto_load=False)
    host_state.network_manager.port = 54000
    host_state.network_manager.tcp_port = 54001
    host_state.network_manager.host_udp_port = 54002
    host_state.network_manager.local_udp_port = 54002
    host_state.network_manager.identity = "Host"
    host_state.network_manager.start_hosting()
    
    # 2. Setup Client
    client_state = GameState(auto_load=False)
    client_state.network_manager.port = 64000
    client_state.network_manager.tcp_port = 54001
    client_state.network_manager.host_udp_port = 54002
    client_state.network_manager.local_udp_port = 64002
    client_state.network_manager.identity = "Client"
    
    connected = client_state.network_manager.connect_to_host("127.0.0.1")
    assert connected is True
    
    # Damage client locally and on host (initial sync)
    client_state.world.name = "outside" # Avoid sanctuary auto-heal
    client_state.player.hp = 50
    client_state.player.flask_charges = 3
    
    # Force sync to Host
    # In real game, Host is authoritative for HP.
    # We need to make sure Host knows Client's initial state if it doesn't already.
    host_state.network_manager.remote_players["Client"] = {
        "identity": "Client", "x": 0, "y": 0, "hp": 50.0, "flask_charges": 3
    }
    
    # 3. Simulate Multi-frame Heal Input (Gamepad holding button)
    # If the bug exists, this will drain all 3 charges.
    actions = {'flask': True, 'move': (0,0)}
    
    # Frame 1
    client_state.update(0.1, actions)
    # Frame 2
    client_state.update(0.1, actions)
    # Frame 3
    client_state.update(0.1, actions)
    
    # 4. Check Local State
    print(f"[TEST] Client HP locally: {client_state.player.hp}")
    print(f"[TEST] Client Flasks locally: {client_state.player.flask_charges}")
    
    # If bug exists, flasks will be 0.
    # If fixed, flasks should be 2.
    assert client_state.player.flask_charges == 2, f"Client consumed too many flasks! Count: {client_state.player.flask_charges}"
    
    # 5. Check Authoritative Sync
    # Update Host and Client for a few frames to allow UDP state sync
    for _ in range(10):
        host_state.update(0.1, {'move': (0,0)})
        client_state.update(0.1, {'move': (0,0)})
        time.sleep(0.02)
        
    print(f"[TEST] Host view of Client HP: {host_state.network_manager.remote_players['Client']['hp']}")
    print(f"[TEST] Client HP after sync: {client_state.player.hp}")
    
    # Verify exact values
    assert host_state.network_manager.remote_players["Client"]["hp"] == 90.0, "Host failed to update authoritative HP for Client heal."
    assert client_state.player.hp == 90.0, "Client HP was overwritten by stale Host data."

    host_state.network_manager.stop_network()
    client_state.network_manager.stop_network()
