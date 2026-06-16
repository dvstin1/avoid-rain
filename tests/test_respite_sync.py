import pytest
import os
import time
from engine.game_state import GameState
from engine.world import Respite
from engine.stats import StatisticsTracker
from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES

# Ensure headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame

@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()

def test_client_respite_rest_sync():
    """
    Reproduces the bug where Client resting fails to sync HP and respawn enemies on Host.
    """
    # 1. Setup Host
    host_state = GameState(auto_load=False)
    host_state.network_manager.port = 55000
    host_state.network_manager.tcp_port = 55001
    host_state.network_manager.host_udp_port = 55002
    host_state.network_manager.local_udp_port = 55002
    host_state.network_manager.identity = "Host"
    host_state.network_manager.start_hosting()
    
    # 2. Setup Client
    client_state = GameState(auto_load=False, stats=StatisticsTracker())
    client_state.network_manager.port = 65000
    client_state.network_manager.tcp_port = 55001
    client_state.network_manager.host_udp_port = 55002
    client_state.network_manager.local_udp_port = 65002
    client_state.network_manager.identity = "Client"
    
    connected = client_state.network_manager.connect_to_host("127.0.0.1")
    assert connected is True
    
    # Set identical world for both
    host_state.world.name = "outside"
    client_state.world.name = "outside" 
    
    client_state.player.hp = 10.0
    client_state.player.flask_charges = 0
    
    host_state.network_manager.remote_players["Client"] = {
        "identity": "Client", "x": 0, "y": 0, "hp": 10.0, "flask_charges": 0
    }
    
    # Kill some enemies on Host
    from engine.enemy import SlugEnemy
    enemy = SlugEnemy(100, 100)
    host_state.enemies = [enemy]
    host_state.enemies[0].hp = 0 # Dead
    
    # Ensure there's a Respite anchor in the Host's world for the handler to find
    respite = Respite((0,0), (40,40))
    host_state.world.interactables.append(respite)
    
    # 3. Client Rests at Respite
    respite.execute_rest(client_state)
    
    assert client_state.player.hp == client_state.player.max_hp
    
    # 4. Step simulation to allow sync
    for _ in range(20):
        host_state.update(0.1, {'move': (0,0)})
        client_state.update(0.1, {'move': (0,0)})
        time.sleep(0.02)
        
    host_hp_on_host_authoritative = host_state.network_manager.remote_players["Client"]["hp"]
    host_enemies_alive = any(e.hp > 0 for e in host_state.enemies)

    host_state.network_manager.stop_network()
    client_state.network_manager.stop_network()
    
    assert host_hp_on_host_authoritative == 100.0
    assert host_enemies_alive, "Enemies did not respawn on Host after Client rest."

def test_client_respite_upgrade_sync():
    """
    Reproduces the bug where Client upgrades fail to sync to Host.
    """
    host_state = GameState(auto_load=False)
    host_state.network_manager.port = 55005
    host_state.network_manager.tcp_port = 55006
    host_state.network_manager.host_udp_port = 55007
    host_state.network_manager.local_udp_port = 55007
    host_state.network_manager.identity = "Host"
    host_state.network_manager.start_hosting()
    
    client_state = GameState(auto_load=False, stats=StatisticsTracker())
    client_state.network_manager.port = 65005
    client_state.network_manager.tcp_port = 55006
    client_state.network_manager.host_udp_port = 55007
    client_state.network_manager.local_udp_port = 65007
    client_state.network_manager.identity = "Client"
    
    connected = client_state.network_manager.connect_to_host("127.0.0.1")
    assert connected is True
    
    # Give client some pages
    client_state.stats.data["lifetime_stats"]["pages_collected"] = 1000
    
    # Initial sync
    host_state.network_manager.remote_players["Client"] = {
        "identity": "Client", "x": 0, "y": 0, "hp": 100.0
    }
    
    # Pre-cache client state on Host so Host knows max_hp
    host_state.cached_client_states["Client"] = client_state.get_full_player_state()
    
    # 3. Client Upgrades Fortification (+10 Max HP)
    respite = Respite((0,0), (40,40))
    # Add respite to Host so it can execute logic
    host_state.world.interactables.append(respite)

    # execute_upgrade(state, marked_idx) -> 2 = max_hp_modifier
    respite.execute_upgrade(client_state, 2)
    
    # 4. Step simulation
    for _ in range(20):
        # We need to make sure the Host receives the updated full state eventually,
        # but for this test we want to see if the UPGRADE event triggers an immediate fix.
        host_state.update(0.1, {'move': (0,0)})
        client_state.update(0.1, {'move': (0,0)})
        time.sleep(0.02)
        
    host_hp_on_host = host_state.network_manager.remote_players["Client"]["hp"]

    host_state.network_manager.stop_network()
    client_state.network_manager.stop_network()
    
    # Expected: Host authoritative HP should be 110.0
    # Current Bug: It will be 100.0 because Host doesn't know about the upgrade yet.
    assert host_hp_on_host == 110.0
