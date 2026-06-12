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

def wait_for_condition(condition_func, timeout=5.0):
    start = time.time()
    while time.time() - start < timeout:
        if condition_func():
            return True
        time.sleep(0.05)
    return False

def test_local_network_sync():
    """
    Automated integration test for Local Network Play (Phase 4).
    Verifies Handshake, State Replication, Damage Events, and Prop Synchronization.
    """
    # 1. Initialize Host
    print("\\n[TEST] Initializing Host...")
    host_state = GameState(auto_load=False)
    # Configure custom ports for local test isolation
    host_state.network_manager.port = 50000
    host_state.network_manager.tcp_port = 50001
    host_state.network_manager.host_udp_port = 50002
    host_state.network_manager.local_udp_port = 50002
    host_state.network_manager.identity = "TestHost"
    
    # Enter Macro-world to trigger hosting
    from engine.world import WarpPortal
    WarpPortal("macro_world", 100, 100, (0, 0, 0, 0)).execute_interaction(host_state)
    assert host_state.network_manager.network_mode == "HOST"
    
    # Wait for map generation
    time.sleep(0.5)

    # Find an actual barrel in the generated world
    host_barrels = [obj for obj in host_state.world.interactables if obj.name == "Barrel"]
    assert len(host_barrels) > 0, "Host map must contain at least one barrel for testing."
    target_barrel = host_barrels[0]

    # 2. Initialize Client
    print("[TEST] Initializing Client...")
    client_state = GameState(auto_load=False)
    client_state.network_manager.port = 60000
    client_state.network_manager.tcp_port = 60001
    client_state.network_manager.host_udp_port = 50002 # Needs to know host's port
    client_state.network_manager.local_udp_port = 60002
    client_state.network_manager.identity = "TestClient"
    
    # 3. Perform Handshake
    print("[TEST] Connecting Client to Host...")
    time.sleep(0.5) # Allow host server to bind
    # Directly connect to localhost on host's TCP port
    # Because client_state.network_manager uses tcp_port to connect, we must set it temporarily to host's port
    client_state.network_manager.tcp_port = 50001
    connected = client_state.network_manager.connect_to_host("127.0.0.1")
    assert connected is True, "Client failed to connect to Host."
    assert client_state.network_manager.network_mode == "CLIENT"

    # 4. Map Sync
    print("[TEST] Fetching Host Map...")
    # Emulate Chronicle interaction
    success = client_state.fetch_host_map()
    assert success is True, "Client failed to fetch map payload from Host."
    from engine.maps import create_world
    client_state.world = create_world("generated_world_client")
    
    # Client should now have the exact same interactables
    client_barrels = [obj for obj in client_state.world.interactables if obj.name == "Barrel"]
    assert len(client_barrels) > 0
    assert getattr(client_barrels[0], 'id', None) == getattr(target_barrel, 'id', None), "Map parity failed: Barrel IDs do not match."

    # 5. Position Client near the barrel
    client_state.player.x = target_barrel.x - 20
    client_state.player.y = target_barrel.y
    client_state.player.facing = (1, 0) # Face right

    # Allow UDP loops to sync initial coordinates
    time.sleep(0.2)

    # 6. Combat Phase (Client Attacks)
    print("[TEST] Simulating Client Attack...")
    actions = {'attack': True, 'move': (0, 0), 'ratchet_reset': False}
    
    # Step simulation
    for _ in range(5):
        client_state.update(0.1, actions)
        actions['attack'] = False # Only pressed first frame
        
        # Step Host to process incoming damage queue
        host_state.update(0.1, {'move': (0, 0)})
        time.sleep(0.05)
        
    # 7. Assertions
    # Host should have received the TCP DAMAGE_EVENT and destroyed the barrel
    host_barrel_ids = [getattr(b, 'id', None) for b in host_state.world.interactables if b.name == "Barrel"]
    assert getattr(target_barrel, 'id', None) not in host_barrel_ids, "Host failed to apply damage event to barrel."
    
    # Host should have broadcast the destruction, and Client should have synced it
    # Give UDP a moment to arrive
    time.sleep(0.2)
    client_state.update(0.1, {'move': (0, 0)}) # Process incoming state
    
    client_barrel_ids = [getattr(b, 'id', None) for b in client_state.world.interactables if b.name == "Barrel"]
    assert getattr(target_barrel, 'id', None) not in client_barrel_ids, "Client failed to receive authoritative destruction from Host."

    # Cleanup
    print("[TEST] Cleaning up...")
    host_state.network_manager.stop_network()
    client_state.network_manager.stop_network()
    print("[TEST] Success!")
