import pytest
import os
import time
from engine.game_state import GameState
from engine.enemy import SlugEnemy, NightBoss
from engine.world import WarpPortal, World

# Ensure headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame

@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()

def test_host_dynamic_spawns_visible_to_client():
    """
    Verifies that enemies and interactables spawned by Host mid-session are synced to Client.
    """
    # 1. Setup Host
    host_state = GameState(auto_load=False)
    host_state.network_manager.port = 56000
    host_state.network_manager.tcp_port = 56001
    host_state.network_manager.host_udp_port = 56002
    host_state.network_manager.local_udp_port = 56002
    host_state.network_manager.identity = "Host"
    host_state.network_manager.start_hosting()
    
    # Use empty worlds to avoid default spawns
    host_state.world = World(name="custom_host")
    host_state.world.grid = [['.' for _ in range(10)] for _ in range(10)]
    host_state.enemies = []
    host_state.world.interactables = []

    # 2. Setup Client (Using VALID ports < 65535)
    client_state = GameState(auto_load=False)
    client_state.network_manager.port = 57000
    client_state.network_manager.tcp_port = 56001
    client_state.network_manager.host_udp_port = 56002
    client_state.network_manager.local_udp_port = 57002
    client_state.network_manager.identity = "Client"
    
    # Use empty worlds
    client_state.world = World(name="custom_client")
    client_state.world.grid = [['.' for _ in range(10)] for _ in range(10)]
    client_state.enemies = []
    client_state.world.interactables = []

    connected = client_state.network_manager.connect_to_host("127.0.0.1")
    assert connected is True
    
    # Wait for initial handshake/sync to settle
    time.sleep(0.5)

    # 3. Host spawns Night Boss
    boss = NightBoss(200, 200)
    boss.network_id = 777
    host_state.enemies.append(boss)
    
    # 4. Host spawns Appendix Warp
    portal = WarpPortal("final_boss", 25, 25, (300, 300, 40, 40), name="Appendix Warp")
    portal.id = "appendix_portal_1"
    host_state.world.interactables.append(portal)
    
    # 5. Step simulation for sync
    # We need enough steps for UDP broadcast to trigger and be processed
    for _ in range(30):
        host_state.update(0.1, {'move': (0,0)})
        client_state.update(0.1, {'move': (0,0)})
        time.sleep(0.05)
        
    # 6. Verify Client sees them
    client_boss = next((e for e in client_state.enemies if getattr(e, 'network_id', -1) == 777), None)
    assert client_boss is not None, "Client failed to spawn Night Boss dynamically."
    assert isinstance(client_boss, NightBoss), f"Client spawned wrong enemy type: {type(client_boss)}"
    
    client_portal = next((obj for obj in client_state.world.interactables if obj.name == "Appendix Warp"), None)
    assert client_portal is not None, "Client failed to spawn Appendix Warp dynamically."
    assert client_portal.target_name == "final_boss", "Client portal has wrong destination."
    
    host_state.network_manager.stop_network()
    client_state.network_manager.stop_network()
