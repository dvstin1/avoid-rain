import pytest
import os
import time
from engine.game_state import GameState
from engine.player import PlayerStateEnum

# Ensure headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame

@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    yield
    pygame.quit()

def test_client_attack_multi_hit_bug():
    """
    Reproduces the bug where a Client attack deals damage every frame.
    """
    # 1. Setup Host
    host_state = GameState(auto_load=False)
    host_state.network_manager.port = 53000
    host_state.network_manager.tcp_port = 53001
    host_state.network_manager.host_udp_port = 53002
    host_state.network_manager.local_udp_port = 53002
    host_state.network_manager.identity = "Host"
    host_state.network_manager.start_hosting()
    
    # 2. Setup Client
    client_state = GameState(auto_load=False)
    client_state.network_manager.port = 63000
    client_state.network_manager.tcp_port = 53001
    client_state.network_manager.host_udp_port = 53002
    client_state.network_manager.local_udp_port = 63002
    client_state.network_manager.identity = "Client"
    
    connected = client_state.network_manager.connect_to_host("127.0.0.1")
    assert connected is True

    # 3. Spawn a high-HP enemy on both
    from engine.enemy import SlugEnemy
    test_enemy = SlugEnemy(100, 100, hp=500)
    test_enemy.network_id = 999
    host_state.enemies = [test_enemy]
    
    client_enemy = SlugEnemy(100, 100, hp=500)
    client_enemy.network_id = 999
    client_state.enemies = [client_enemy]
    
    # 4. Simulate Client Attack
    # Position client near enemy
    client_state.player.x, client_state.player.y = 80, 100
    client_state.player.facing = (1, 0)
    
    # Trigger attack
    actions = {'attack': True, 'move': (0,0)}
    client_state.update(0.1, actions) # Frame 1: Attack starts
    
    assert client_state.player.state == PlayerStateEnum.ATTACKING
    
    # Update for several frames
    for _ in range(10):
        # We must NOT pass 'attack': True again, as GameState resets attack_pressed
        # but the state stays ATTACKING for SWORD_DURATION
        client_state.update(0.016, {'attack': False, 'move': (0,0)})
        host_state.update(0.016, {'attack': False, 'move': (0,0)})
        time.sleep(0.01)
        
    # 5. Verify Enemy HP on Host
    print(f"[TEST] Enemy HP on Host: {test_enemy.hp}")
    
    host_state.network_manager.stop_network()
    client_state.network_manager.stop_network()
    
    # Expected: 490 (1 hit)
    # Bug: much less
    assert test_enemy.hp == 490, f"Enemy should have taken exactly 10 damage. HP: {test_enemy.hp}"
