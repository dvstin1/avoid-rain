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

def test_network_integration_host_and_client_combat():
    """
    TDD Integration Test for Network Combat:
    1. Client Attacks Prop -> Syncs to Host -> Host Destroys -> Syncs back to Client.
    2. Host Attacks Prop -> Host Destroys -> Syncs to Client.
    3. Host/Client Combat with Enemies.
    """
    # --- SETUP HOST ---
    print("\n[TEST] Initializing Host...")
    host_state = GameState(auto_load=False)
    # Disable weather for testing stability
    host_state.weather_manager.damage_enabled = False
    
    host_state.network_manager.port = 51000
    host_state.network_manager.tcp_port = 51001
    host_state.network_manager.host_udp_port = 51002
    host_state.network_manager.local_udp_port = 51002
    host_state.network_manager.identity = "TestHost"
    
    from engine.world import WarpPortal
    WarpPortal("macro_world", 100, 100, (0, 0, 0, 0)).execute_interaction(host_state)
    time.sleep(0.5) # Wait for map generation
    
    # --- SETUP CLIENT ---
    print("[TEST] Initializing Client...")
    client_state = GameState(auto_load=False)
    client_state.network_manager.port = 61000
    client_state.network_manager.tcp_port = 51001 # Point to Host's TCP
    client_state.network_manager.host_udp_port = 51002 # Send UDP to Host
    client_state.network_manager.local_udp_port = 61002 # Receive UDP here
    client_state.network_manager.identity = "TestClient"
    
    print("[TEST] Connecting Client...")
    time.sleep(0.2)
    connected = client_state.network_manager.connect_to_host("127.0.0.1")
    assert connected is True
    
    success = client_state.fetch_host_map()
    assert success is True
    from engine.maps import create_world
    client_state.world = create_world("generated_world_client")
    client_state.enemies = getattr(client_state.world, 'enemies', [])
    
    # --- TEST CASE 1: CLIENT BREAKS BARREL ---
    print("[TEST] Case 1: Client Attacks Barrel...")
    barrels = [b for b in host_state.world.interactables if b.name == "Barrel"]
    assert len(barrels) >= 2, "Test requires at least 2 barrels in macro_world."
    target_1 = barrels[0]
    
    # Position client near barrel 1
    client_state.player.x, client_state.player.y = target_1.x - 20, target_1.y
    client_state.player.facing = (1, 0)
    time.sleep(0.1)
    
    # Client Attacks
    client_state.update(0.1, {'attack': True, 'move': (0,0), 'ratchet_reset': False})
    # Step simulation to process TCP and state loops
    for _ in range(20):
        client_state.update(0.016, {'attack': False, 'move': (0,0)})
        host_state.update(0.016, {'attack': False, 'move': (0,0)})
        time.sleep(0.01)
        
    # Verify Barrel 1 is gone on both
    host_b_ids = [b.id for b in host_state.world.interactables if b.name == "Barrel"]
    client_b_ids = [b.id for b in client_state.world.interactables if b.name == "Barrel"]
    assert target_1.id not in host_b_ids, "Host failed to destroy barrel attacked by Client."
    assert target_1.id not in client_b_ids, "Client failed to hide barrel destroyed by Host (via Client attack)."

    # Allow state to settle
    time.sleep(0.5)

    # --- TEST CASE 2: HOST BREAKS BARREL ---
    print("[TEST] Case 2: Host Attacks Barrel...")
    target_2 = barrels[1]
    host_state.player.x, host_state.player.y = target_2.x - 20, target_2.y
    host_state.player.facing = (1, 0)
    
    # Host Attacks
    host_state.update(0.1, {'attack': True, 'move': (0,0), 'ratchet_reset': False})
    for _ in range(20):
        host_state.update(0.016, {'attack': False, 'move': (0,0)})
        client_state.update(0.016, {'attack': False, 'move': (0,0)})
        time.sleep(0.01)
        
    # Verify Barrel 2 is gone on both
    host_b_ids = [b.id for b in host_state.world.interactables if b.name == "Barrel"]
    client_b_ids = [b.id for b in client_state.world.interactables if b.name == "Barrel"]
    assert target_2.id not in host_b_ids, "Host failed to destroy barrel locally."
    assert target_2.id not in client_b_ids, "Client failed to hide barrel destroyed by Host locally."

    # Allow state to settle
    time.sleep(0.5)

    # --- TEST CASE 3: VISIBILITY AND TARGETING ---
    print("[TEST] Case 3: Visibility and Targeting Sync...")
    
    # 1. Visibility Check: Can Host see Client?
    time.sleep(0.5) # Wait for UDP heartbeat
    assert client_state.network_manager.identity in [p["identity"] for p in host_state.network_manager.remote_players.values()], \
        f"Host failed to see Client '{client_state.network_manager.identity}' in remote_players."
    
    # 2. Visibility Check: Can Client see Host?
    assert host_state.network_manager.identity in [p["identity"] for p in client_state.network_manager.remote_players.values()], \
        f"Client failed to see Host '{host_state.network_manager.identity}' in remote_players."

    # 3. Targeting Check: Enemy should target Client if Client is closer
    assert len(host_state.enemies) > 0, "Test requires at least one enemy."
    target_enemy = host_state.enemies[0]
    initial_hp = target_enemy.hp
    
    # Move Host far away
    host_state.player.x, host_state.player.y = 0, 0
    # Move Client near enemy
    client_state.player.x, client_state.player.y = target_enemy.x + 10, target_enemy.y
    
    # Allow a few frames for AI to update targeting
    for _ in range(5):
        host_state.update(0.1, {'attack': False, 'move': (0,0)})
        client_state.update(0.1, {'attack': False, 'move': (0,0)})
        time.sleep(0.05)
        
    from engine.actor import ActorState
    assert target_enemy.state in (ActorState.CHASE, ActorState.WIND_UP, ActorState.STRIKE), \
        f"Enemy should be engaging Client, but is in state {target_enemy.state}"
    
    # --- TEST CASE 4: COMBAT SYNC ---
    print("[TEST] Case 4: Combat Sync...")
    # cx = x + 20. If x = target_enemy.x - 40, cx = target_enemy.x - 20.
    # hitbox.x = cx + 30 = target_enemy.x + 10.
    # hitbox width 60. Spans target_enemy.x+10 to target_enemy.x+70.
    # Enemy is at target_enemy.x with width 40. Spans target_enemy.x to target_enemy.x+40.
    # OVERLAP: x+10 to x+40. (30 pixels).
    client_state.player.x, client_state.player.y = target_enemy.x - 40, target_enemy.y
    client_state.player.facing = (1, 0)
    client_state.update(0.1, {'attack': True, 'move': (0,0), 'ratchet_reset': False})
    
    for _ in range(20):
        client_state.update(0.016, {'attack': False, 'move': (0,0)})
        host_state.update(0.016, {'attack': False, 'move': (0,0)})
        time.sleep(0.01)
        
    # Verify Client sees position and damage
    print(f"[DEBUG] Target Enemy Network ID: {getattr(target_enemy, 'network_id', -2)}")
    print(f"[DEBUG] Host Enemies: {[getattr(e, 'network_id', -1) for e in host_state.enemies]}")
    print(f"[DEBUG] Client Enemies: {[getattr(e, 'network_id', -1) for e in client_state.enemies]}")
    client_enemy = None
    for e in client_state.enemies:
        if getattr(e, 'network_id', -1) == getattr(target_enemy, 'network_id', -2):
            client_enemy = e; break
    
    assert client_enemy is not None, "Client lost track of synced enemy."
    assert target_enemy.hp < initial_hp, "Host enemy did not take damage from Client attack."
    assert abs(client_enemy.hp - target_enemy.hp) < 1, "Enemy HP out of sync on Client."

    # --- CLEANUP ---
    print("[TEST] Success!")
    host_state.network_manager.stop_network()
    client_state.network_manager.stop_network()
