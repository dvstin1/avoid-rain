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
    from engine.stats import StatisticsTracker
    client_state = GameState(auto_load=False, stats=StatisticsTracker())
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
    if client_state.stats:
        client_state.stats.data["active_session_in_progress"] = True
    
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
    assert target_enemy.state in (
        ActorState.CHASE,
        ActorState.WIND_UP,
        ActorState.STRIKE,
        ActorState.RECOVERY,
    ), f"Enemy should be engaging Client, but is in state {target_enemy.state}"
    
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
        
        # Test Case 4.1: Animation/State Sync
        # Force enemy into a visible state on Host
        target_enemy.state = ActorState.WIND_UP
        time.sleep(0.1)
        client_state.update(0.1, {'attack': False, 'move': (0,0)})
        assert client_enemy.state == ActorState.WIND_UP, f"Enemy state failed to sync. Host:{target_enemy.state} Client:{client_enemy.state}"
    else:
        # Verify Host also removed it
        host_enemy_ids = [getattr(e, 'network_id', -1) for e in host_state.enemies]
        assert getattr(target_enemy, 'network_id', -2) not in host_enemy_ids, \
            "Client lost track of enemy while it was still alive on Host."

    # 2. Enemy Damage to Client (New)
    print("[TEST] Case 4.2: Enemy Attack Client...")
    
    # Put client directly on top of a NEW enemy to guarantee contact
    host_state.enemies = [e for e in host_state.enemies if not e.is_dead()]
    assert len(host_state.enemies) > 0
    test_enemy = host_state.enemies[0]
    
    # Reset stagger and disable movement for stability
    test_enemy.stagger_timer = 0
    test_enemy.speed = 0
    
    client_state.player.x, client_state.player.y = test_enemy.x, test_enemy.y
    
    # Allow multiple heartbeats to sync Client position to Host
    client_peer_id = client_state.network_manager.peer_id
    client_found_on_host = False
    for _ in range(20):
        # Force position in EVERY frame to fight physics/walls
        client_state.player.x, client_state.player.y = test_enemy.x, test_enemy.y
        client_state.update(0.1, {'attack': False, 'move': (0,0)})
        host_state.update(0.1, {'attack': False, 'move': (0,0)})
        time.sleep(0.05)
        if client_peer_id in host_state.network_manager.remote_players:
            p = host_state.network_manager.remote_players[client_peer_id]
            # High tolerance for network rounding/sync lag
            if abs(p["x"] - test_enemy.x) < 45: 
                client_found_on_host = True
                break

    assert client_found_on_host is True, "Host failed to see Client near enemy position."

    initial_client_hp = client_state.player.hp
    
    # Force enemy into STRIKE state on Host
    test_enemy.state = ActorState.STRIKE
    test_enemy.combat_timer = 1.0
    test_enemy.has_hit_this_attack = False
    
    # Update Host to deal damage and Client to receive it
    found_host_side_damage = False
    for _ in range(40):
        # Center client on enemy
        client_state.player.x = test_enemy.x + test_enemy.width // 2 - 20
        client_state.player.y = test_enemy.y + test_enemy.height // 2 - 20
        
        host_state.update(0.1, {'attack': False, 'move': (0,0)})
        client_state.update(0.1, {'attack': False, 'move': (0,0)})
        time.sleep(0.05)
        if host_state.network_manager.remote_players[client_peer_id]["hp"] < 100:
            found_host_side_damage = True
        if client_state.player.hp < initial_client_hp:
            break
        
    assert found_host_side_damage is True, "Host failed to apply damage to remote Client."
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
    
    # Client should now be in Sanctuary while keeping the Seamless LAN session alive
    assert client_state.world.name == "sanctuary"
    assert client_state.in_sanctuary is True
    assert client_state.network_manager.network_mode == "CLIENT", \
        f"Client should preserve LAN session on Sanctuary respawn. Mode: {client_state.network_manager.network_mode}"

    # Explicit disconnect from client removes peer from Host connected_peers
    client_state.network_manager.stop_network()
    time.sleep(0.5)
    host_state.update(0.1, {'attack': False, 'move': (0,0)})
    
    # Check connected_peers (more reliable than remote_players which might have ghosts)
    assert client_peer_id not in host_state.network_manager.connected_peers, \
        "Host still thinks Client is connected via connected_peers."
    
    host_state.network_manager.stop_network()
    # Success if it reaches here!
    print("[TEST] Success!")


def test_duplicate_default_player_name_peers_on_localhost():
    """Two clients on 127.0.0.1 sharing DEFAULT_PLAYER_NAME connect and sync without colliding."""
    from constants import DEFAULT_PLAYER_NAME

    host_state = GameState(auto_load=False)
    host_state.network_manager.port = 51100
    host_state.network_manager.tcp_port = 51101
    host_state.network_manager.host_udp_port = 51102
    host_state.network_manager.local_udp_port = 51102
    host_state.network_manager.identity = DEFAULT_PLAYER_NAME
    host_state.network_manager.start_hosting()

    client_1 = GameState(auto_load=False)
    client_1.network_manager.port = 61100
    client_1.network_manager.tcp_port = 51101
    client_1.network_manager.host_udp_port = 51102
    client_1.network_manager.local_udp_port = 61102
    client_1.network_manager.identity = DEFAULT_PLAYER_NAME

    client_2 = GameState(auto_load=False)
    client_2.network_manager.port = 61110
    client_2.network_manager.tcp_port = 51101
    client_2.network_manager.host_udp_port = 51102
    client_2.network_manager.local_udp_port = 61112
    client_2.network_manager.identity = DEFAULT_PLAYER_NAME

    try:
        time.sleep(0.05)
        assert client_1.network_manager.connect_to_host("127.0.0.1") is True
        assert client_2.network_manager.connect_to_host("127.0.0.1") is True

        peer_1 = client_1.network_manager.peer_id
        peer_2 = client_2.network_manager.peer_id
        assert peer_1 != peer_2
        assert peer_1 != host_state.network_manager.peer_id
        assert peer_1 in host_state.network_manager.connected_peers
        assert peer_2 in host_state.network_manager.connected_peers

        client_1.player.x, client_1.player.y = 680.0, 280.0
        client_2.player.x, client_2.player.y = 760.0, 280.0

        for _ in range(15):
            host_state.update(0.016, {"move": (0, 0)})
            client_1.update(0.016, {"move": (0, 0)})
            client_2.update(0.016, {"move": (0, 0)})
            time.sleep(0.03)

        assert peer_1 in host_state.network_manager.remote_players
        assert peer_2 in host_state.network_manager.remote_players
        assert abs(host_state.network_manager.remote_players[peer_1]["x"] - client_1.player.x) < 1.0
        assert abs(host_state.network_manager.remote_players[peer_2]["x"] - client_2.player.x) < 1.0

        # Both clients should also see the Host and each other even though all 3 share DEFAULT_PLAYER_NAME
        assert host_state.network_manager.peer_id in client_1.network_manager.remote_players
        assert peer_2 in client_1.network_manager.remote_players
        assert host_state.network_manager.peer_id in client_2.network_manager.remote_players
        assert peer_1 in client_2.network_manager.remote_players
    finally:
        client_1.network_manager.stop_network()
        client_2.network_manager.stop_network()
        host_state.network_manager.stop_network()


def test_large_framed_tcp_payload_and_map_request():
    """Large TCP payloads (>16KB) transfer cleanly across framed TCP helpers and request_map()."""
    import socket
    from engine.network_manager import _send_framed_json, _recv_framed_json

    left_sock, right_sock = socket.socketpair()
    try:
        large_payload = {
            "type": "MAP_RESPONSE",
            "tiles": ["#" * 256 for _ in range(200)],  # > 50 KB
            "metadata": {"act": 1, "seed": 42},
        }
        _send_framed_json(left_sock, large_payload)
        decoded = _recv_framed_json(right_sock)
        assert decoded == large_payload
    finally:
        left_sock.close()
        right_sock.close()

    host_state = GameState(auto_load=False)
    host_state.network_manager.port = 51200
    host_state.network_manager.tcp_port = 51201
    host_state.network_manager.host_udp_port = 51202
    host_state.network_manager.local_udp_port = 51202
    large_map = {
        "name": "large_test_map",
        "width": 120,
        "height": 120,
        "padding": "X" * 32768,  # > 32 KB payload
    }
    host_state.network_manager.host_map_provider = lambda: large_map
    host_state.network_manager.start_hosting()

    client_state = GameState(auto_load=False)
    client_state.network_manager.port = 61200
    client_state.network_manager.tcp_port = 51201
    client_state.network_manager.host_udp_port = 51202
    client_state.network_manager.local_udp_port = 61202

    try:
        time.sleep(0.05)
        assert client_state.network_manager.connect_to_host("127.0.0.1") is True
        fetched = client_state.network_manager.request_map()
        assert fetched is not None
        assert fetched.get("name") == "large_test_map"
        assert len(fetched.get("padding", "")) == 32768
    finally:
        client_state.network_manager.stop_network()
        host_state.network_manager.stop_network()


def test_main_thread_inbox_drain_and_offline_disconnect_event():
    """Queued UDP snapshots and disconnect events apply on the main thread even after timeout sets OFFLINE."""
    state = GameState(auto_load=False)
    try:
        state.network_manager.network_mode = "CLIENT"
        state.network_manager.server_address = "127.0.0.1"

        # Enqueue a remote state snapshot without calling drain_network_events yet
        remote_peer_id = "peer_abc12345"
        state.network_manager.enqueue_inbound(
            "REMOTE_STATE",
            (
                ("127.0.0.1", 55557),
                {
                    "peer_id": remote_peer_id,
                    "identity": "RemoteHost",
                    "is_host": True,
                    "x": 300.0,
                    "y": 400.0,
                    "hp": 85.0,
                },
            ),
        )
        # Before drain_network_events(), remote_players must NOT be mutated
        assert remote_peer_id not in state.network_manager.remote_players

        state.drain_network_events()
        assert remote_peer_id in state.network_manager.remote_players
        assert state.network_manager.remote_players[remote_peer_id]["hp"] == 85.0

        # Simulate background UDP timeout setting network_mode = "OFFLINE" and queuing HOST_DISCONNECT
        state.world.name = "macro_world"
        state.network_manager.network_mode = "OFFLINE"
        state.network_manager.enqueue_inbound("HOST_DISCONNECT", None)

        # Calling update() while already OFFLINE must still drain HOST_DISCONNECT and return to sanctuary
        state.update(0.016, {"move": (0, 0)})
        assert state.world.name == "sanctuary"
    finally:
        state.network_manager.stop_network()


def test_outbound_reliable_events_enqueue_non_blocking():
    """Outbound reliable TCP events enqueue immediately on the main thread without opening sockets."""
    state = GameState(auto_load=False)
    try:
        state.network_manager.network_mode = "CLIENT"
        state.network_manager.server_address = "127.0.0.1"
        state.network_manager.is_connected = False
        # Do not start worker threads so we can inspect _outbound_queue directly
        state.network_manager.send_damage_event("enemy", 7, 25)
        state.network_manager.send_heal_event(40)
        state.network_manager.send_respite_event("REST", 0, {"max_hp": 100})
        state.network_manager.send_full_state({"hp": 90, "max_hp": 100})

        queued = []
        while not state.network_manager._outbound_queue.empty():
            _host_addr, _tcp_port, payload = state.network_manager._outbound_queue.get_nowait()
            queued.append(payload)

        assert [msg["type"] for msg in queued] == [
            "DAMAGE_EVENT",
            "HEAL_EVENT",
            "RESPITE_ACTION",
            "UPDATE_FULL_STATE",
        ]
        assert all(msg["peer_id"] == state.network_manager.peer_id for msg in queued)
    finally:
        state.network_manager.stop_network()


def test_seamless_lan_auto_host_and_auto_join_sanctuary(tmp_path):
    """Verify Offline/Online mode persistence and start_seamless_lan auto-host + auto-join in Sanctuary."""
    from engine.stats import StatisticsTracker

    save_path = tmp_path / "save_data.json"
    host_state = GameState(stats=None, stats_path=str(save_path), auto_load=True)
    client_state = GameState(auto_load=False)
    try:
        # 1. Offline mode toggle & persistence
        host_state.set_online_mode(False, save=True)
        assert host_state.online_mode is False
        reloaded = StatisticsTracker.load(save_path)
        assert reloaded.data["online_mode"] is False
        assert host_state.start_seamless_lan(probe_duration=0.1) == "OFFLINE"
        assert host_state.network_manager.network_mode == "OFFLINE"

        # 2. Switch back to Online mode and configure isolated test ports
        host_state.set_online_mode(True, save=True)
        host_state.network_manager.port = 51300
        host_state.network_manager.tcp_port = 51301
        host_state.network_manager.host_udp_port = 51302
        host_state.network_manager.local_udp_port = 51302

        client_state.network_manager.port = 51300
        client_state.network_manager.tcp_port = 51301
        client_state.network_manager.host_udp_port = 51302
        client_state.network_manager.local_udp_port = 61302

        # First scholar in Sanctuary probes and promotes to HOST
        role_1 = host_state.start_seamless_lan(probe_duration=0.25)
        assert role_1 == "HOST"
        assert host_state.network_manager.network_mode == "HOST"
        assert host_state.in_sanctuary is True

        # Second scholar in Sanctuary discovers Host broadcast and connects as CLIENT
        role_2 = client_state.start_seamless_lan(probe_duration=1.2)
        assert role_2 == "CLIENT"
        assert client_state.network_manager.network_mode == "CLIENT"
        assert client_state.in_sanctuary is True
        assert client_state.waiting_for_host_run is False
    finally:
        client_state.network_manager.stop_network()
        host_state.network_manager.stop_network()
        host_state.shutdown_save_worker(timeout=1.0)


def test_simultaneous_host_peer_id_tie_breaker():
    """When two Hosts broadcast simultaneously on the same LAN port, the higher peer_id yields to the lower."""
    low_host = GameState(auto_load=False)
    high_host = GameState(auto_load=False)
    try:
        low_host.network_manager.peer_id = "0000_low_host"
        low_host.network_manager.port = 51310
        low_host.network_manager.tcp_port = 51311
        low_host.network_manager.host_udp_port = 51312
        low_host.network_manager.local_udp_port = 51312

        high_host.network_manager.peer_id = "ffff_high_host"
        high_host.network_manager.port = 51310
        high_host.network_manager.tcp_port = 51311
        high_host.network_manager.host_udp_port = 51312
        high_host.network_manager.local_udp_port = 61312

        low_host.network_manager.start_hosting()
        high_host.network_manager.start_hosting()

        settled = False
        for _ in range(30):
            low_host.drain_network_events()
            high_host.drain_network_events()
            if (
                low_host.network_manager.network_mode == "HOST"
                and high_host.network_manager.network_mode == "CLIENT"
                and high_host.network_manager.is_connected
            ):
                settled = True
                break
            time.sleep(0.1)

        assert settled is True, (
            f"Tie-breaker did not converge: low={low_host.network_manager.network_mode}, "
            f"high={high_host.network_manager.network_mode}"
        )
        assert high_host.network_manager.server_peer_id == "0000_low_host"
    finally:
        high_host.network_manager.stop_network()
        low_host.network_manager.stop_network()


def test_sanctuary_group_warp_and_waiting_scholars_regroup():
    """Verify Sanctuary group WarpPortal launch, mid-run Waiting Scholar staging, and Return to Sanctuary regroup."""
    host = GameState(auto_load=False)
    client_party = GameState(auto_load=False)
    client_late = GameState(auto_load=False)
    try:
        host.network_manager.port = 51320
        host.network_manager.tcp_port = 51321
        host.network_manager.host_udp_port = 51322
        host.network_manager.local_udp_port = 51322
        host.network_manager.host_map_provider = lambda: {
            "map_id": "generated_world",
            "dimensions": {"width": 20, "height": 20},
            "grid": ["." * 20 for _ in range(20)],
            "entities": {"player_start": [128, 128]},
            "module_sockets": [],
        }
        host.network_manager.start_hosting()

        client_party.network_manager.port = 61320
        client_party.network_manager.tcp_port = 51321
        client_party.network_manager.host_udp_port = 51322
        client_party.network_manager.local_udp_port = 61322
        assert client_party.network_manager.connect_to_host("127.0.0.1") is True
        assert client_party.waiting_for_host_run is False

        # 1. Host launches a run from Sanctuary; client_party (staged in Sanctuary) warps into the run automatically
        host.world.name = "generated_world"
        host.in_sanctuary = False
        host.host_in_run = True

        warped_with_host = False
        for _ in range(25):
            host.update(0.05, {"move": (0, 0)})
            client_party.update(0.05, {"move": (0, 0)})
            if not client_party.in_sanctuary and client_party.world.name == "generated_world_client":
                warped_with_host = True
                break
            time.sleep(0.05)

        assert warped_with_host is True, "Sanctuary client failed to auto-warp with Host on run launch."

        # 2. A third scholar connects while Host is already in a run -> stays in Sanctuary as Waiting Scholar
        client_late.network_manager.port = 61325
        client_late.network_manager.tcp_port = 51321
        client_late.network_manager.host_udp_port = 51322
        client_late.network_manager.local_udp_port = 61326
        assert client_late.network_manager.connect_to_host("127.0.0.1") is True
        assert client_late.in_sanctuary is True
        assert client_late.waiting_for_host_run is True

        saw_waiting_count = False
        for _ in range(25):
            host.update(0.05, {"move": (0, 0)})
            client_party.update(0.05, {"move": (0, 0)})
            client_late.update(0.05, {"move": (0, 0)})
            if host.waiting_scholars == 1 and client_party.waiting_scholars == 1:
                saw_waiting_count = True
                break
            time.sleep(0.05)

        assert saw_waiting_count is True
        assert client_late.in_sanctuary is True
        assert client_late.waiting_for_host_run is True, (
            f"host_in_run={client_late.host_in_run}, last={client_late._last_host_in_run}, "
            f"seen_sanc={client_late._seen_host_in_sanctuary}, mode={client_late.network_manager.network_mode}, "
            f"host_world={host.world.name}"
        )

        # 3. Active runner triggers Return to Sanctuary -> party regroups in Sanctuary without dropping LAN session
        client_party.return_party_to_sanctuary()
        regrouped = False
        for _ in range(25):
            host.update(0.05, {"move": (0, 0)})
            client_party.update(0.05, {"move": (0, 0)})
            client_late.update(0.05, {"move": (0, 0)})
            if (
                host.in_sanctuary
                and client_party.in_sanctuary
                and client_late.in_sanctuary
                and not client_late.waiting_for_host_run
                and host.waiting_scholars == 0
            ):
                regrouped = True
                break
            time.sleep(0.05)

        assert regrouped is True
        assert host.network_manager.network_mode == "HOST"
        assert client_party.network_manager.network_mode == "CLIENT"
        assert client_late.network_manager.network_mode == "CLIENT"
    finally:
        client_late.network_manager.stop_network()
        client_party.network_manager.stop_network()
        host.network_manager.stop_network()


def test_disruptive_host_promotion_lowest_peer_id():
    """When Host disconnects, all surviving Clients warp to Sanctuary and the lowest peer_id promotes to Host."""
    old_host = GameState(auto_load=False)
    survivor_low = GameState(auto_load=False)
    survivor_high = GameState(auto_load=False)
    try:
        old_host.network_manager.peer_id = "0000_old_host"
        old_host.network_manager.port = 51330
        old_host.network_manager.tcp_port = 51331
        old_host.network_manager.host_udp_port = 51332
        old_host.network_manager.local_udp_port = 51332
        old_host.world.name = "generated_world"
        old_host.in_sanctuary = False
        old_host.host_in_run = True
        old_host.network_manager.start_hosting()

        # survivor_low uses host_udp_port=51332 as its local_udp_port so when it promotes to Host,
        # its UDP receiver binds 51332 cleanly after old_host stops.
        survivor_low.network_manager.peer_id = "aaaa_survivor_low"
        survivor_low.network_manager.port = 51330
        survivor_low.network_manager.tcp_port = 51331
        survivor_low.network_manager.host_udp_port = 51332
        survivor_low.network_manager.local_udp_port = 61332

        survivor_high.network_manager.peer_id = "zzzz_survivor_high"
        survivor_high.network_manager.port = 51330
        survivor_high.network_manager.tcp_port = 51331
        survivor_high.network_manager.host_udp_port = 51332
        survivor_high.network_manager.local_udp_port = 61334

        assert survivor_low.network_manager.connect_to_host("127.0.0.1") is True
        assert survivor_high.network_manager.connect_to_host("127.0.0.1") is True

        survivor_low.world.name = "generated_world_client"
        survivor_low.in_sanctuary = False
        survivor_high.world.name = "generated_world_client"
        survivor_high.in_sanctuary = False

        # Exchange heartbeats so both clients populate remote_players with each other's peer_id
        for _ in range(15):
            old_host.update(0.05, {"move": (0, 0)})
            survivor_low.update(0.05, {"move": (0, 0)})
            survivor_high.update(0.05, {"move": (0, 0)})
            if (
                "zzzz_survivor_high" in survivor_low.network_manager.remote_players
                and "aaaa_survivor_low" in survivor_high.network_manager.remote_players
            ):
                break
            time.sleep(0.05)

        assert "zzzz_survivor_high" in survivor_low.network_manager.remote_players
        assert "aaaa_survivor_low" in survivor_high.network_manager.remote_players

        # Align survivor_low's local_udp_port to 51332 before promotion so survivor_high's UDP packets reach it
        survivor_low.network_manager.local_udp_port = 51332

        # Disconnect old_host abruptly
        old_host.network_manager.stop_network()

        promoted_and_reconnected = False
        for _ in range(35):
            survivor_low.update(0.05, {"move": (0, 0)})
            survivor_high.update(0.05, {"move": (0, 0)})
            if (
                survivor_low.in_sanctuary
                and survivor_high.in_sanctuary
                and survivor_low.network_manager.network_mode == "HOST"
                and survivor_high.network_manager.network_mode == "CLIENT"
                and survivor_high.network_manager.server_peer_id == "aaaa_survivor_low"
            ):
                promoted_and_reconnected = True
                break
            time.sleep(0.1)

        assert promoted_and_reconnected is True, (
            f"Promotion failed: low={survivor_low.network_manager.network_mode}, "
            f"high={survivor_high.network_manager.network_mode} "
            f"(server_peer_id={survivor_high.network_manager.server_peer_id})"
        )
    finally:
        survivor_high.network_manager.stop_network()
        survivor_low.network_manager.stop_network()
        old_host.network_manager.stop_network()
