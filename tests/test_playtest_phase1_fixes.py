# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Phase 1 Playtest Fixes:

1. Dash wall-tunneling sub-stepping (1-2 tile distances, dt spikes) & active world-bound clamping.
2. Rain boundary circle gated behind state.debug_text_enabled in Renderer.draw_weather().
3. Rebalanced SCRAPS_REWARD_* constants and PauseMenu 'Reset Margin Scraps' debug option.
"""
# pylint: disable=no-member

from unittest.mock import MagicMock

import pygame

import constants
from engine.binder_scripts import toggle_equip_script, weave_script
from engine.game_state import GameState
from engine.pause_menu import PauseMenu
from engine.player import Player, PlayerStateEnum
from engine.stats import StatisticsTracker
from engine.world import World
from rendering.renderer import Renderer


def _make_walled_test_world(width_tiles=12, height_tiles=8, wall_col=5):
    """Create a simple World with an interior 1-tile-thick (40px) vertical wall column."""
    grid = [[constants.TILE_EMPTY for _ in range(width_tiles)] for _ in range(height_tiles)]
    if wall_col is not None:
        for y in range(height_tiles):
            grid[y][wall_col] = constants.TILE_WALL
    world = World(name="test_arena")
    world.grid = grid
    world.interactables = []
    world.warp_tiles = {}
    world.player_start = (40, 120)
    world.enemies = []
    return world


def test_dash_cannot_tunnel_through_40px_wall_from_various_distances_and_dts():
    """Verify swept wall queries + DASH_SUBSTEP_MAX_PX prevent dashing through a 40px wall."""
    assert constants.DASH_SUBSTEP_MAX_PX <= 10.0

    wall_x = 5 * constants.TILE_SIZE  # 200px (wall spans 200..240)
    # Test starting 0.5, 1.0, 1.5, and 2.0 tiles left of the wall at normal (60 FPS) and hitchy (0.05s / 0.1s) dt
    for start_x in (140.0, 120.0, 100.0, 80.0):
        for dt in (1.0 / 60.0, 0.05, 0.1):
            state = GameState(auto_load=False, stats=StatisticsTracker())
            try:
                state.in_sanctuary = False
                state.world = _make_walled_test_world(width_tiles=12, height_tiles=8, wall_col=5)
                state.enemies = []
                state.player.x = start_x
                state.player.y = 3.0 * constants.TILE_SIZE
                state.player.facing = (1.0, 0.0)
                # Give player max speed script bonus to stress-test worst-case dash velocity
                state.player.script_modifiers["speed"] = 36.0

                # Trigger dash right toward the wall
                state.update(dt, {"move": (1.0, 0.0), "dash": True})
                elapsed = 0.0
                while elapsed < constants.DASH_DURATION + 0.05:
                    state.update(dt, {"move": (1.0, 0.0), "dash": False})
                    elapsed += dt
                    assert state.player.x + state.player.width <= wall_x + 1e-6, (
                        f"Player tunneled past 40px wall at x={wall_x} from start_x={start_x}, "
                        f"dt={dt}: got x={state.player.x}"
                    )
            finally:
                state.shutdown_save_worker(timeout=1.0)


def test_dash_clamps_to_active_world_boundaries():
    """Verify dashing toward any of the 4 outer edges clamps cleanly to the active world dimensions."""
    world_w = 10 * constants.TILE_SIZE  # 400px
    world_h = 8 * constants.TILE_SIZE   # 320px

    cases = [
        # (start_x, start_y, facing, expected_check)
        (20.0, 120.0, (-1.0, 0.0)),   # West edge (x >= 0)
        (340.0, 120.0, (1.0, 0.0)),   # East edge (x <= world_w - width)
        (160.0, 20.0, (0.0, -1.0)),   # North edge (y >= 0)
        (160.0, 260.0, (0.0, 1.0)),   # South edge (y <= world_h - height)
    ]
    for sx, sy, facing in cases:
        player = Player(sx, sy)
        player.facing = facing
        player.state = PlayerStateEnum.DASHING
        player.dash_timer = constants.DASH_DURATION

        for _ in range(15):
            player.update(
                0.02, facing, walls=[], actions={},
                world_width=world_w, world_height=world_h,
            )
            assert 0.0 <= player.x <= world_w - player.width
            assert 0.0 <= player.y <= world_h - player.height


def test_rain_boundary_circle_gated_by_debug_text_enabled(monkeypatch):
    """Verify 5px rain boundary ring in Renderer.draw_weather() renders only when debug_text_enabled is True."""
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        state.world.name = "generated_world"
        state.bleed_state = "SHRINKING"
        state.active_safe_radius = 220.0
        state.current_boss_coords = {"x": 16, "y": 9}
        state.camera.instant_center((16 * constants.TILE_SIZE, 9 * constants.TILE_SIZE))

        circle_calls = []
        orig_circle = pygame.draw.circle

        def spy_circle(surface, color, center, radius, width=0):
            circle_calls.append((color, center, radius, width))
            return orig_circle(surface, color, center, radius, width)

        monkeypatch.setattr(pygame.draw, "circle", spy_circle)

        # Debug text OFF -> rain boundary circle must NOT be drawn
        state.debug_text_enabled = False
        renderer.draw_weather(state)
        assert not circle_calls, f"Expected no rain boundary circle when debug_text_enabled=False, got {circle_calls}"

        # Debug text ON -> 5px black rain boundary circle IS drawn
        state.debug_text_enabled = True
        renderer.draw_weather(state)
        assert len(circle_calls) == 1
        assert circle_calls[0][0] == (0, 0, 0, 255)
        assert circle_calls[0][2] == 220
        assert circle_calls[0][3] == 5
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_margin_scraps_rebalance_and_pause_menu_reset(tmp_path):
    """Verify reduced SCRAPS_REWARD_* constants and PauseMenu 'Reset Margin Scraps' debug reset."""
    assert constants.SCRAPS_REWARD_MARGINALIA_EVENT == 0
    assert constants.SCRAPS_REWARD_NIGHT_BOSS_BASE == 1
    assert constants.SCRAPS_REWARD_NIGHT_BOSS_EMPOWERED == 2
    assert constants.SCRAPS_REWARD_FINAL_AUTHOR == 3

    stats_path = str(tmp_path / "save_data.json")
    state = GameState(auto_load=False, stats=StatisticsTracker(), stats_path=stats_path)
    state.network_manager.stop_network()
    try:
        # Grant scraps, weave & equip +35 Max HP script, and set Binder conflict/story flags
        state.stats.add_margin_scraps(12)
        assert weave_script(state.stats, "hemming_major")[0] is True
        assert toggle_equip_script(state.stats, state.player, "hemming_major", in_sanctuary=True)[0] is True
        assert state.player.max_hp == constants.PLAYER_MAX_HP + 35.0
        assert state.player.hp == constants.PLAYER_MAX_HP + 35.0
        state.stats.data["binder_scripts"]["failed_sequence"] = ["max_hp", "attack"]
        state.stats.data["binder_scripts"]["conflicts_triggered"] = 2
        state.stats.data["story_flags"]["perfect_stitch_completed"] = True
        state.stats.data["story_flags"]["ink_bleed_halted"] = True

        # Mock CLIENT mode to verify send_full_state sync
        state.network_manager.network_mode = "CLIENT"
        mock_send = MagicMock()
        state.network_manager.send_full_state = mock_send

        pm = PauseMenu(
            debug_text_enabled=False,
            on_toggle_debug=lambda val: state.set_debug_text_enabled(val, save=False),
            on_reset_margin_scraps=lambda: state.reset_margin_scraps(save=True),
        )

        # Hidden when debug_text_enabled is False
        assert "Reset Margin Scraps" not in pm.get_options()

        # Enable debug text -> option appears
        pm.set_debug_text_enabled(True)
        assert "Reset Margin Scraps" in pm.get_options()

        # Select and confirm 'Reset Margin Scraps'
        pm.open()
        while pm.get_selected() != "Reset Margin Scraps":
            pm.navigate("down")
        pm.confirm()

        assert state.stats.data["margin_scraps"] == 0
        assert state.stats.data["binder_scripts"] == {
            "unlocked": [],
            "equipped": [],
            "failed_sequence": [],
            "conflicts_triggered": 0,
        }
        assert state.stats.data["story_flags"]["perfect_stitch_completed"] is False
        assert state.stats.data["story_flags"]["ink_bleed_halted"] is False
        assert state.player.max_hp == constants.PLAYER_MAX_HP
        assert state.player.hp == constants.PLAYER_MAX_HP
        mock_send.assert_called_once()

        # Verify reset persisted to disk
        reloaded = StatisticsTracker.load(stats_path)
        assert reloaded.data["margin_scraps"] == 0
        assert reloaded.data["binder_scripts"]["unlocked"] == []
        assert reloaded.data["binder_scripts"]["equipped"] == []
        assert reloaded.data["story_flags"]["perfect_stitch_completed"] is False
    finally:
        state.shutdown_save_worker(timeout=1.0)
