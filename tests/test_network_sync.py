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
    client_state.enemies = client_state.world.enemies
    
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
    # Refresh target enemy to ensure it's still alive and tracked
    host_state.enemies = [e for e in host_state.enemies if not e.is_dead()]
    assert len(host_state.enemies) > 0
    target_enemy = host_state.enemies[0]
    initial_hp = target_enemy.hp
    
    # 1. Client Damage to Enemy
    client_state.player.x, client_state.player.y = target_enemy.x - 40, target_enemy.y
    client_state.player.facing = (1, 0)
    client_state.update(0.1, {'attack': True, 'move': (0,0), 'ratchet_reset': False})
    
    for _ in range(30):
        client_state.update(0.016, {'attack': False, 'move': (0,0)})
        host_state.update(0.016, {'attack': False, 'move': (0,0)})
        time.sleep(0.01)
        
    # Verify Sync
    client_enemy = next((e for e in client_state.enemies if getattr(e, 'network_id', -1) == getattr(target_enemy, 'network_id', -2)), None)
    
    # Rule: If enemy is GONE, it means it died and cleanup worked perfectly.
    # If it is STILL THERE, it must have taken damage.
    if client_enemy:
        assert target_enemy.hp < initial_hp, "Host enemy did not take damage from Client attack."
        assert abs(client_enemy.hp - target_enemy.hp) < 1, "Enemy HP out of sync on Client."
        
        # Test Case 4.1: Animation/State Sync (New)
        # Force enemy into a visible state on Host
        target_enemy.state = ActorState.WIND_UP
        time.sleep(0.1)
        client_state.update(0.1, {'attack': False, 'move': (0,0)})
        assert client_enemy.state == ActorState.WIND_UP, "Enemy state (animations) failed to sync to Client."
    else:
        # Verify Host also removed it
        host_enemy_ids = [getattr(e, 'network_id', -1) for e in host_state.enemies]
        assert getattr(target_enemy, 'network_id', -2) not in host_enemy_ids, \
            "Client lost track of enemy while it was still alive on Host."

    # 2. Enemy Damage to Client (New)
    print("[TEST] Case 4.2: Enemy Attack Client...")
    initial_client_hp = client_state.player.hp
    # Put client directly on top of a NEW enemy to guarantee contact
    host_state.enemies = [e for e in host_state.enemies if not e.is_dead()]
    assert len(host_state.enemies) > 0
    test_enemy = host_state.enemies[0]
    
    client_state.player.x, client_state.player.y = test_enemy.x, test_enemy.y
    
    # Force enemy into STRIKE state on Host
    test_enemy.state = ActorState.STRIKE
    test_enemy.combat_timer = 1.0
    test_enemy.has_hit_this_attack = False
    
    # Update Host and Client
    for _ in range(15):
        host_state.update(0.1, {'attack': False, 'move': (0,0)})
        client_state.update(0.1, {'attack': False, 'move': (0,0)})
        time.sleep(0.05)
        
    # Verify Host recorded the damage and broadcast it back
    assert client_state.player.hp < initial_client_hp, \
        f"Client failed to receive authoritative damage from enemy attack. HP: {client_state.player.hp}"

    # --- TEST CASE 5: WEATHER SYNC ---
    print("[TEST] Case 5: Weather Sync and Damage...")
    # Enable weather damage
    host_state.weather_manager.damage_enabled = True
    client_state.weather_manager.damage_enabled = True
    
    # Move everyone outside the safe zone (Players at 800,800. Safe zone center at 4000,4000)
    host_state.weather_manager.active_safe_radius = 5.0
    host_state.weather_manager.boss_coords_list = [{'x': 100, 'y': 100}]
    host_state.weather_manager.bleed_state = "CLAMPED" # Bypass 60s grace period
    
    client_state.weather_manager.boss_coords_list = [{'x': 100, 'y': 100}] # Sync manually for test
    client_state.weather_manager.bleed_state = "CLAMPED"
    
    host_state.player.x, host_state.player.y = 800, 800
    client_state.player.x, client_state.player.y = 800, 800
    
    # Force tiles to be empty to ensure exposure
    from constants import TILE_EMPTY
    host_state.world.grid[20][20] = TILE_EMPTY
    client_state.world.grid[20][20] = TILE_EMPTY
    
    initial_host_hp = host_state.player.hp
    initial_client_hp = client_state.player.hp
    
    # Step simulation
    for _ in range(10):
        # Force a large delta time to ensure measurable damage
        host_state.update(1.0, {'attack': False, 'move': (0,0)})
        client_state.update(1.0, {'attack': False, 'move': (0,0)})
        time.sleep(0.05)
        
    assert host_state.player.hp < initial_host_hp, f"Host failed to take rain damage. HP: {host_state.player.hp}"
    assert client_state.player.hp < initial_client_hp, f"Client failed to take rain damage locally. HP: {client_state.player.hp}"
    assert host_state.player.is_exposed is True, "Host should be marked as exposed."
    assert client_state.player.is_exposed is True, "Client should be marked as exposed."

    # --- TEST CASE 6: CLIENT DEATH ---
    print("[TEST] Case 6: Client Death and Disconnect...")
    # Force client to 0 HP
    client_state.player.hp = 0
    # Update to trigger death sequence
    client_state.update(0.1, {'attack': False, 'move': (0,0)})
    assert client_state.death_timer > 0, "Client failed to initiate death sequence."
    
    # Fast forward death timer
    client_state.death_timer = 0.01
    client_state.update(0.1, {'attack': False, 'move': (0,0)})
    
    # Client should now be in Sanctuary and OFFLINE
    assert client_state.world.name == "sanctuary"
    assert client_state.network_manager.network_mode == "OFFLINE", \
        f"Client failed to disconnect after death. Mode: {client_state.network_manager.network_mode}"
    
    # Host should eventually see client is gone (after disconnect signal processed)
    time.sleep(0.5)
    host_state.update(0.1, {'attack': False, 'move': (0,0)})
    assert "TestClient" not in [p["identity"] for p in host_state.network_manager.remote_players.values()], \
        "Host failed to remove dead Client from its visibility list."

    # --- CLEANUP ---
    print("[TEST] Cleaning up...")
    host_state.network_manager.stop_network()
    client_state.network_manager.stop_network()
    print("[TEST] Success!")
