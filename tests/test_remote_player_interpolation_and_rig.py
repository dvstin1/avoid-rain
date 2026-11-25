# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Item #19: Smooth 60 FPS Remote Player Interpolation & Full Player Model Rendering."""
# pylint: disable=no-member,protected-access,too-many-locals

import os

import pygame
import pytest

import constants
from engine.game_state import GameState, RemotePlayerInterpolator
from engine.player import PlayerStateEnum
from engine.stats import StatisticsTracker
from rendering.renderer import Renderer


def _ensure_pygame():
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def test_snapshot_interpolation_60fps_and_velocity_animation():
    """Verify ~65 ms snapshot interpolation yields smooth 60 FPS movement, walk anim timing, and teleport snap."""
    interp = RemotePlayerInterpolator()

    # Feed 20 Hz (50 ms) snapshots moving east at 300 px/s (15 px per tick)
    for idx in range(5):
        t_snap = idx * 0.050
        interp.push_snapshot(
            timestamp=t_snap,
            x=100.0 + idx * 15.0,
            y=200.0,
            facing=(1.0, 0.0),
            state="RUN",
            weapon_key="WeaponScriberBlade",
            in_sanctuary=False,
        )

    # Sample across 60 FPS frames between t=0.120 and t=0.200 (t_sample = now - 0.065 falls inside [0.055, 0.135])
    xs = []
    anim_times = []
    dt = 1.0 / 60.0
    for step in range(5):
        now = 0.120 + step * dt
        sample = interp.sample(now=now, dt=dt)
        expected_t = now - constants.NET_SNAPSHOT_INTERP_DELAY
        expected_x = 100.0 + (expected_t / 0.050) * 15.0
        assert sample["render_x"] == pytest.approx(expected_x, abs=1e-3)
        assert sample["render_y"] == pytest.approx(200.0, abs=1e-3)
        assert sample["render_vx"] == pytest.approx(300.0, abs=1e-2)
        assert sample["state"] == "RUN"
        assert sample["weapon_key"] == "WeaponScriberBlade"
        xs.append(sample["render_x"])
        anim_times.append(sample["render_anim_time"])

    # Strictly smooth monotonic progression (never stuck on 20 Hz steps)
    assert all(xs[i + 1] > xs[i] for i in range(len(xs) - 1))
    assert all(anim_times[i + 1] > anim_times[i] for i in range(len(anim_times) - 1))

    # Teleport / large jump (> NET_TELEPORT_SNAP_DISTANCE) snaps immediately instead of lerping
    interp.push_snapshot(
        timestamp=0.250,
        x=1200.0,
        y=900.0,
        facing=(0.0, 1.0),
        state="IDLE",
        weapon_key="WeaponScriberBlade",
        in_sanctuary=False,
    )
    snap_sample = interp.sample(now=0.260, dt=dt)
    assert snap_sample["render_x"] == pytest.approx(1200.0, abs=1e-3)
    assert snap_sample["render_y"] == pytest.approx(900.0, abs=1e-3)
    assert snap_sample["state"] == "IDLE"


def test_dead_reckoning_fallback_clamp_and_explicit_stop():
    """Verify dropped UDP packets dead-reckon smoothly up to NET_DEAD_RECKONING_MAX_EXTRAPOLATION then clamp."""
    interp = RemotePlayerInterpolator()
    # Two 20 Hz snapshots moving east at 200 px/s (10 px / 0.05s)
    interp.push_snapshot(timestamp=1.000, x=50.0, y=80.0, facing=(1.0, 0.0), state="RUN")
    interp.push_snapshot(timestamp=1.050, x=60.0, y=80.0, facing=(1.0, 0.0), state="RUN")

    # Packet at 1.100 dropped; at now = 1.165, t_sample = 1.100 => extrap = 0.050s (< max 0.12s)
    mid_extrap = interp.sample(now=1.100 + constants.NET_SNAPSHOT_INTERP_DELAY, dt=1.0 / 60.0)
    assert mid_extrap["render_x"] == pytest.approx(60.0 + 200.0 * 0.050, abs=1e-3)
    assert mid_extrap["render_y"] == pytest.approx(80.0, abs=1e-3)
    assert mid_extrap["state"] == "RUN"

    # Long packet loss (now = 2.000): extrapolation strictly clamped to NET_DEAD_RECKONING_MAX_EXTRAPOLATION
    clamped = interp.sample(now=2.000, dt=1.0 / 60.0)
    max_x = 60.0 + 200.0 * constants.NET_DEAD_RECKONING_MAX_EXTRAPOLATION
    assert clamped["render_x"] == pytest.approx(max_x, abs=1e-3)
    assert clamped["render_vx"] == pytest.approx(0.0, abs=1e-6)
    assert clamped["state"] == "IDLE"

    # Explicit IDLE snapshot does not dead-reckon past the stop coordinate
    stop_interp = RemotePlayerInterpolator()
    stop_interp.push_snapshot(timestamp=1.000, x=10.0, y=20.0, state="RUN")
    stop_interp.push_snapshot(timestamp=1.050, x=25.0, y=20.0, state="IDLE")
    stopped = stop_interp.sample(now=1.150, dt=1.0 / 60.0)
    assert stopped["render_x"] == pytest.approx(25.0, abs=1e-3)
    assert stopped["state"] == "IDLE"


def test_host_and_guest_payload_sync_and_backward_compatibility():
    """Verify facing, state, and weapon_key sync across Host/Guest payloads and legacy omitted fields."""
    host = GameState(auto_load=False, stats=StatisticsTracker())
    client = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        host.network_manager.network_mode = "HOST"
        host.network_manager.peer_id = "host_peer_1"
        host.network_manager.identity = "HostScholar"
        host.in_sanctuary = False
        host.world.name = "generated_world"
        host.player.x, host.player.y = 320.0, 240.0
        host.player.facing = (0.0, -1.0)
        host.player.state = PlayerStateEnum.MOVING
        host.player.weapons = [{"name": "Anomalous Ink-Bleed", "damage": 24, "modifiers": {"bleed": 5.0}}]
        host.player.active_weapon_idx = 0

        client.network_manager.network_mode = "CLIENT"
        client.network_manager.peer_id = "guest_peer_2"
        client.network_manager.identity = "GuestScholar"
        client.network_manager.server_address = "127.0.0.1"
        client.in_sanctuary = False
        client.world.name = "generated_world_client"
        client.player.x, client.player.y = 400.0, 260.0
        client.player.facing = (-1.0, 0.0)
        client.player.state = PlayerStateEnum.BLOCKING
        client.player.weapons = [{"name": "Scriber Blade", "damage": 16}]
        client.player.active_weapon_idx = 0

        # 1. Guest UDP heartbeat includes facing, state, weapon_key -> Host ingests & broadcasts in session_players
        guest_pkt = client.get_local_state()
        assert guest_pkt["facing"] == [-1.0, 0.0]
        assert guest_pkt["state"] == "BLOCK"
        assert guest_pkt["weapon_key"] == "WeaponScriberBlade"

        guest_pkt["peer_id"] = client.network_manager.peer_id
        guest_pkt["identity"] = client.network_manager.identity
        host.apply_remote_state(("127.0.0.1", 60000), guest_pkt, now=10.000)

        host_view_guest = host.network_manager.remote_players["guest_peer_2"]
        assert host_view_guest["facing"] == [-1.0, 0.0]
        assert host_view_guest["state"] == "BLOCK"
        assert host_view_guest["weapon_key"] == "WeaponScriberBlade"

        # 2. Host UDP heartbeat + session_players broadcasts both Host and Guest metadata
        host.local_swing_seq = 1
        host_pkt = host.get_local_state()
        assert host_pkt["facing"] == [0.0, -1.0]
        assert host_pkt["state"] == "RUN"
        assert host_pkt["weapon_key"] == "WeaponAnomalousBleed"
        sp_by_id = {entry["peer_id"]: entry for entry in host_pkt["session_players"]}
        assert sp_by_id["host_peer_1"]["weapon_key"] == "WeaponAnomalousBleed"
        assert sp_by_id["host_peer_1"]["facing"] == [0.0, -1.0]
        assert sp_by_id["host_peer_1"]["state"] == "RUN"
        assert sp_by_id["guest_peer_2"]["weapon_key"] == "WeaponScriberBlade"
        assert sp_by_id["guest_peer_2"]["state"] == "BLOCK"

        # Client applies Host heartbeat -> triggers attack animation via swing_seq increment without duplicate snap
        host_pkt["peer_id"] = host.network_manager.peer_id
        host_pkt["identity"] = host.network_manager.identity
        host_pkt["is_host"] = True
        client.apply_remote_state(("127.0.0.1", 55557), host_pkt, now=10.000)
        assert len(client._remote_interp_buffers["host_peer_1"].snapshots) == 1

        client.update_remote_player_interpolation(dt=0.05, now=10.050)
        client_view_host = client.network_manager.remote_players["host_peer_1"]
        assert client_view_host["weapon_key"] == "WeaponAnomalousBleed"
        assert client_view_host["render_state"] == "ATTACK"
        assert 0.0 < client_view_host["render_attack_progress"] < 1.0

        # 3. Backward compatibility: legacy packet omitting facing, state, and weapon_key
        legacy_pkt_1 = {
            "peer_id": "legacy_peer",
            "identity": "LegacyPeer",
            "x": 100.0,
            "y": 100.0,
            "hp": 90.0,
            "in_sanctuary": False,
        }
        legacy_pkt_2 = {
            "peer_id": "legacy_peer",
            "identity": "LegacyPeer",
            "x": 115.0,
            "y": 100.0,
            "hp": 90.0,
            "in_sanctuary": False,
        }
        host.apply_remote_state(("127.0.0.1", 60001), legacy_pkt_1, now=20.000)
        host.apply_remote_state(("127.0.0.1", 60001), legacy_pkt_2, now=20.050)
        host.update_remote_player_interpolation(dt=1.0 / 60.0, now=20.090)

        legacy_entry = host.network_manager.remote_players["legacy_peer"]
        assert legacy_entry["weapon_key"] == constants.DEFAULT_PLAYER_WEAPON_KEY
        assert legacy_entry["render_state"] == "RUN"
        assert legacy_entry["render_facing"] == pytest.approx((1.0, 0.0), abs=1e-3)
        assert 100.0 < legacy_entry["render_x"] < 115.0
    finally:
        host.shutdown_save_worker(timeout=1.0)
        client.shutdown_save_worker(timeout=1.0)


def test_in_sanctuary_filtering_and_headless_remote_rig_rendering():
    """Verify in_sanctuary filtering, Cyan/Magenta trim, weapon model, nameplate, and world-actor pass order."""
    _ensure_pygame()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        state.network_manager.network_mode = "CLIENT"
        state.network_manager.server_address = "127.0.0.1"
        state.in_sanctuary = False
        state.world.name = "generated_world_client"
        state.player.x, state.player.y = 500.0, 500.0

        # 1. Peer in different in_sanctuary state (Waiting Scholar in Sanctuary) is filtered out
        state.network_manager.remote_players = {
            "waiting_scholar": {
                "peer_id": "waiting_scholar",
                "identity": "WaitingScholar",
                "is_host": False,
                "x": 540.0,
                "y": 500.0,
                "render_x": 540.0,
                "render_y": 500.0,
                "facing": [0.0, 1.0],
                "state": "IDLE",
                "weapon_key": "WeaponQuillStandard",
                "in_sanctuary": True,
            },
            "active_host": {
                "peer_id": "active_host",
                "identity": "ActiveHost",
                "addr": "127.0.0.1",
                "is_host": True,
                "x": 560.0,
                "y": 500.0,
                "render_x": 560.0,
                "render_y": 500.0,
                "facing": [1.0, 0.0],
                "render_facing": (1.0, 0.0),
                "state": "ATTACK",
                "render_state": "ATTACK",
                "render_attack_progress": 0.45,
                "weapon_key": "WeaponAnomalousBleed",
                "in_sanctuary": False,
            },
            "active_guest": {
                "peer_id": "active_guest",
                "identity": "ActiveGuest",
                "addr": "127.0.0.2",
                "is_host": False,
                "x": 640.0,
                "y": 500.0,
                "render_x": 640.0,
                "render_y": 500.0,
                "facing": [-1.0, 0.0],
                "render_facing": (-1.0, 0.0),
                "state": "RUN",
                "render_state": "RUN",
                "render_anim_time": 0.25,
                "weapon_key": "WeaponAnomalousRegen",
                "in_sanctuary": False,
            },
        }

        rig_calls = []
        orig_draw_rig = renderer.draw_player_rig

        def spy_draw_rig(*args, **kwargs):
            rig_calls.append((args, kwargs))
            return orig_draw_rig(*args, **kwargs)

        renderer.draw_player_rig = spy_draw_rig
        try:
            screen.fill((0, 0, 0))
            count = renderer.draw_remote_players(state, 400.0, 400.0)
        finally:
            renderer.draw_player_rig = orig_draw_rig

        assert count == 2
        assert len(rig_calls) == 2
        # Verify Host got Cyan trim + bleed weapon + attack sweep; Guest got Magenta trim + regen weapon
        by_weapon = {kw["weapon_key"]: kw for _args, kw in rig_calls}
        assert by_weapon["WeaponAnomalousBleed"]["trim_color"] == constants.NET_REMOTE_HOST_TRIM_COLOR
        assert by_weapon["WeaponAnomalousBleed"]["base_state"] == "ATTACK"
        assert by_weapon["WeaponAnomalousBleed"]["attack_progress"] == pytest.approx(0.45)
        assert by_weapon["WeaponAnomalousRegen"]["trim_color"] == constants.NET_REMOTE_GUEST_TRIM_COLOR
        assert by_weapon["WeaponAnomalousRegen"]["base_state"] == "RUN"

        # Flip local player into Sanctuary: only waiting_scholar should render now
        state.in_sanctuary = True
        assert renderer.draw_remote_players(state, 400.0, 400.0) == 1

        # 2. Verify full Renderer.render() calls draw_remote_players in world-actor pass
        #    (strictly before roofs, HUD, weather, and bloom)
        state.in_sanctuary = False
        pass_order = []
        hooked = (
            "draw_remote_players",
            "draw_sanctuary_roofs_and_blackout",
            "draw_hud",
            "draw_weather",
            "draw_bloom_overlay",
        )
        originals = {name: getattr(renderer, name) for name in hooked}
        try:
            for name in hooked:
                orig_fn = originals[name]

                def make_spy(fn_name, fn_ref):
                    def _wrapped(*a, **kw):
                        pass_order.append(fn_name)
                        return fn_ref(*a, **kw)

                    return _wrapped

                setattr(renderer, name, make_spy(name, orig_fn))

            renderer.render(state)
        finally:
            for name, orig_fn in originals.items():
                setattr(renderer, name, orig_fn)

        assert "draw_remote_players" in pass_order
        remote_idx = pass_order.index("draw_remote_players")
        for later_pass in (
            "draw_sanctuary_roofs_and_blackout",
            "draw_hud",
            "draw_weather",
            "draw_bloom_overlay",
        ):
            assert remote_idx < pass_order.index(later_pass), (
                f"Expected draw_remote_players before {later_pass}, got order {pass_order}"
            )
    finally:
        state.shutdown_save_worker(timeout=1.0)
