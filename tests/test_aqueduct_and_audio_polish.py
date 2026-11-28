# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Locked Shed Door SFX, Candelabra Volume, and Sunlit Aqueducts Organic Textures."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from types import SimpleNamespace

import pygame
import pytest

import constants
import generate_sfx
from engine.audio import AudioManager
from engine.game_state import GameState
from engine.world import FlavorProp, GameObject, World
from rendering.renderer import Renderer


def test_locked_shed_door_rattle_sfx_and_interaction():
    """Verify locked_door_rattle.ogg exists, decodes cleanly, and plays on locked_shed_door interaction."""
    assert constants.LOCKED_DOOR_RATTLE_SFX == "locked_door_rattle.ogg"
    sfx_path = os.path.join("assets", "audio", "sfx", constants.LOCKED_DOOR_RATTLE_SFX)
    assert os.path.exists(sfx_path), f"Missing generated SFX: {sfx_path}"
    duration = generate_sfx.verify_ogg(sfx_path)
    assert 0.10 <= duration <= 0.60
    assert generate_sfx.find_missing_sfx(".") == {}

    played = []
    state = SimpleNamespace(
        active_dialogue=None,
        audio_manager=SimpleNamespace(play_sfx=lambda name, **kw: played.append(name)),
    )

    locked_door = FlavorProp(
        (120.0, 120.0),
        (40, 40),
        "Locked Shed Door",
        "The brass padlock won't budge.",
        prop_type="locked_shed_door",
    )
    locked_door.execute_interaction(state)
    assert played == [constants.LOCKED_DOOR_RATTLE_SFX]
    assert state.active_dialogue == {
        "speaker": "Locked Shed Door",
        "text": "The brass padlock won't budge.",
    }

    # Other FlavorProps do not trigger the padlock rattle SFX
    played.clear()
    other_prop = FlavorProp((200.0, 120.0), (40, 40), "Stone Plaque", "Faded ink.", prop_type="plaque")
    other_prop.execute_interaction(state)
    assert not played


def test_candelabra_ambient_volume_scaled_to_0_2_while_chalice_stays_1_25():
    """Verify AudioManager._compute_environment_targets() scales Candelabra to 0.2x and Fire Chalice to 1.25x."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init()

    assert constants.ENV_AUDIO_CANDELABRA_VOL_MULT == pytest.approx(0.2)
    assert constants.ENV_AUDIO_CHALICE_VOL_MULT == pytest.approx(1.25)

    am = AudioManager()
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("sanctuary")
        state.world.load_from_prototype(["." * 12 for _ in range(12)])
        state.world.sanctuary_zones = {}
        state.in_sanctuary = True
        state.player.x = 200.0
        state.player.y = 200.0

        # Centered Candelabra within full_dist yields exact ENV_AUDIO_FLAME_BASE_VOL * 0.2 (0.068)
        candle = GameObject((200.0, 200.0), (40, 40))
        candle.name = "Candelabra"
        state.world.interactables = [candle]
        targets_candle = am._compute_environment_targets(state)
        expected_candle = constants.ENV_AUDIO_FLAME_BASE_VOL * constants.ENV_AUDIO_CANDELABRA_VOL_MULT
        assert expected_candle == pytest.approx(0.068)
        assert targets_candle["flame"][0] == pytest.approx(expected_candle)
        assert targets_candle["flame"][1] == pytest.approx(expected_candle)

        # Centered Fire Chalice within full_dist yields exact ENV_AUDIO_FLAME_BASE_VOL * 1.25 (0.425)
        chalice = GameObject((180.0, 180.0), (80, 80))
        chalice.name = "Fire Chalice"
        state.world.interactables = [chalice]
        targets_chalice = am._compute_environment_targets(state)
        expected_chalice = min(1.0, constants.ENV_AUDIO_FLAME_BASE_VOL * constants.ENV_AUDIO_CHALICE_VOL_MULT)
        assert targets_chalice["flame"][0] == pytest.approx(expected_chalice)
        assert targets_chalice["flame"][1] == pytest.approx(expected_chalice)
    finally:
        am.stop_environment_audio()
        state.shutdown_save_worker(timeout=1.0)


def test_sunlit_aqueducts_organic_grass_and_plateau_rooftop_rendering():
    """Verify Sunlit Aqueducts grass (s_idx==2), plateau rooftop (wall_s), and south cliff facade render cleanly."""
    if not pygame.get_init():
        pygame.init()
    screen = pygame.Surface((240, 240))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["sunlit_aqueducts"]
    ts = constants.TILE_SIZE

    # 1. Organic Grass Terrace tiles (s_idx == 2): multi-tone variation & no solid wall_glow ellipse flood
    grass_surf = pygame.Surface((ts * 3, ts * 3))
    base_grass_col, alt_grass_col = pal["strata"][2]
    for gy in range(3):
        for gx in range(3):
            sx, sy = gx * ts, gy * ts
            grass_surf.fill(base_grass_col, (sx, sy, ts, ts))
            renderer._draw_connected_floor_patterns(
                grass_surf,
                ("sunlit_aqueducts", pal, 2, alt_grass_col),
                (gx, gy, 3, 3),
                (sx, sy, ts, ts),
            )

    grass_colors = {
        tuple(grass_surf.get_at((px, py))[:3])
        for px in range(0, ts * 3, 2)
        for py in range(0, ts * 3, 2)
    }
    assert len(grass_colors) >= 4
    # Giant wall_glow ellipse flood must no longer dominate the grass tiles
    glow_rgb = pal["wall_glow"]
    glow_count = sum(
        1
        for px in range(0, ts * 3, 2)
        for py in range(0, ts * 3, 2)
        if tuple(grass_surf.get_at((px, py))[:3]) == glow_rgb
    )
    assert glow_count == 0

    # 2. Elevated Rocky / Terracotta Plateau Rooftop (wall_s=True)
    grid_roof = [
        [constants.TILE_EMPTY, constants.TILE_EMPTY, constants.TILE_EMPTY, constants.TILE_EMPTY],
        [constants.TILE_EMPTY, constants.TILE_WALL, constants.TILE_WALL, constants.TILE_EMPTY],
        [constants.TILE_EMPTY, constants.TILE_WALL, constants.TILE_WALL, constants.TILE_EMPTY],
        [constants.TILE_EMPTY, constants.TILE_EMPTY, constants.TILE_EMPTY, constants.TILE_EMPTY],
    ]
    dummy_state = SimpleNamespace(world=SimpleNamespace(grid=grid_roof, name="sunlit_aqueducts"))
    roof_surf = pygame.Surface((ts * 4, ts * 4))
    roof_surf.fill((0, 0, 0))
    # Row 1 wall tiles have wall_s=True -> plateau rooftop branch
    renderer._draw_connected_wall_tile(
        roof_surf, dummy_state, (1, 1, 4, 4), (ts, ts, ts, ts), ("sunlit_aqueducts", pal)
    )
    renderer._draw_connected_wall_tile(
        roof_surf, dummy_state, (2, 1, 4, 4), (ts * 2, ts, ts, ts), ("sunlit_aqueducts", pal)
    )
    roof_colors = {
        tuple(roof_surf.get_at((px, py))[:3])
        for px in range(ts, ts * 3, 2)
        for py in range(ts, ts * 2, 2)
    }
    assert len(roof_colors) >= 4
    # Exposed north edge has mortar border line at top
    assert tuple(roof_surf.get_at((ts + 10, ts))[:3]) == pal["wall_mortar"]

    # 3. South-facing cliff facade (wall_s=False) continues using AqueductMossWall path cleanly
    renderer._draw_connected_wall_tile(
        roof_surf, dummy_state, (1, 2, 4, 4), (ts, ts * 2, ts, ts), ("sunlit_aqueducts", pal)
    )
    south_colors = {
        tuple(roof_surf.get_at((px, py))[:3])
        for px in range(ts, ts * 2, 2)
        for py in range(ts * 2, ts * 3, 2)
    }
    assert len(south_colors) >= 2
