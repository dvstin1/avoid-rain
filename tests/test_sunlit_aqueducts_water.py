# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Section 20 Sunlit Aqueducts Continuous Channel Water Overhaul."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def _make_aqueduct_state(prototype: list[str], biome: str = "sunlit_aqueducts") -> GameState:
    """Build a headless offline GameState populated with the given grid and biome name."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    state.world.name = biome
    state.world.load_from_prototype(prototype)
    return state


def test_continuous_channel_fill_and_no_pill_seams(monkeypatch):
    """Verify adjacent sunlit_aqueducts water tiles fill continuously with zero boxy 2x2 pill seams."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    ts = constants.TILE_SIZE
    state = _make_aqueduct_state(
        [
            "#####",
            "#...#",
            "#...#",
            "#...#",
            "#####",
        ]
    )
    try:
        water_coords = {(1, 1), (2, 1), (3, 1), (1, 2), (2, 2), (3, 2), (1, 3), (2, 3), (3, 3)}
        monkeypatch.setattr(
            renderer,
            "_get_tile_stratum",
            lambda _st, tx, ty: 0 if (tx, ty) in water_coords else 1,
        )

        canvas = pygame.Surface((5 * ts, 5 * ts))
        for ty in range(1, 4):
            for tx in range(1, 4):
                renderer._draw_static_tile_to_surface(
                    canvas, state, (tx, ty, 5, 5), (tx * ts, ty * ts, ts, ts)
                )

        # Center water tile (2, 2) has water on all 4 sides -> continuous base fill across all borders
        cx0, cy0 = 2 * ts, 2 * ts
        base_col = constants.AQUEDUCT_WATER_BASE_COLOR
        assert canvas.get_at((cx0, cy0 + ts // 2))[:3] == base_col
        assert canvas.get_at((cx0 - 1, cy0 + ts // 2))[:3] == base_col
        assert canvas.get_at((cx0 + ts - 1, cy0 + ts // 2))[:3] == base_col
        assert canvas.get_at((cx0 + ts, cy0 + ts // 2))[:3] == base_col
        assert canvas.get_at((cx0 + ts // 2, cy0))[:3] == base_col
        assert canvas.get_at((cx0 + ts // 2, cy0 + ts - 1))[:3] == base_col

        # Scan center tile pixels: must contain base fill + staggered 1px shimmers, never old pill colors
        seen_colors = {
            canvas.get_at((cx0 + px, cy0 + py))[:3]
            for px in range(ts)
            for py in range(ts)
        }
        assert base_col in seen_colors
        assert constants.AQUEDUCT_WATER_SHIMMER_HI in seen_colors
        assert constants.AQUEDUCT_WATER_SHIMMER_LO in seen_colors
        assert (64, 144, 158) not in seen_colors
        assert (132, 224, 236) not in seen_colors
        assert constants.AQUEDUCT_TROUGH_RIM_NORTH not in seen_colors
        assert constants.AQUEDUCT_TROUGH_RIM_SOUTH not in seen_colors
        assert constants.AQUEDUCT_TROUGH_RIM_SIDE not in seen_colors
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_neighbor_aware_three_px_trough_rims(monkeypatch):
    """Verify 3px carved terracotta/wet-stone trough rims appear strictly on non-water cardinal edges."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    ts = constants.TILE_SIZE
    rim = constants.AQUEDUCT_TROUGH_RIM_PX
    assert rim == 3

    state = _make_aqueduct_state(
        [
            "#####",
            "#...#",
            "#...#",
            "#...#",
            "#####",
        ]
    )
    try:
        # 1. Isolated 1x1 water tile surrounded by terracotta -> all 4 cardinal 3px rims + N/W waterline
        monkeypatch.setattr(
            renderer,
            "_get_tile_stratum",
            lambda _st, tx, ty: 0 if (tx, ty) == (2, 2) else 1,
        )
        iso_surf = pygame.Surface((ts, ts))
        renderer._draw_static_tile_to_surface(iso_surf, state, (2, 2, 5, 5), (0, 0, ts, ts))

        for off in range(rim):
            assert iso_surf.get_at((ts // 2, off))[:3] == constants.AQUEDUCT_TROUGH_RIM_NORTH
            assert iso_surf.get_at((ts // 2, ts - 1 - off))[:3] == constants.AQUEDUCT_TROUGH_RIM_SOUTH
            assert iso_surf.get_at((off, ts // 2))[:3] == constants.AQUEDUCT_TROUGH_RIM_SIDE
            assert iso_surf.get_at((ts - 1 - off, ts // 2))[:3] == constants.AQUEDUCT_TROUGH_RIM_SIDE
        assert iso_surf.get_at((ts // 2, rim))[:3] == constants.AQUEDUCT_TROUGH_WATERLINE
        assert iso_surf.get_at((rim, ts // 2))[:3] == constants.AQUEDUCT_TROUGH_WATERLINE

        # 2. Horizontal channel: (1,2), (2,2), (3,2) are water -> N & S get 3px rims; W & E stay open water
        horiz = {(1, 2), (2, 2), (3, 2)}
        monkeypatch.setattr(renderer, "_get_tile_stratum", lambda _st, tx, ty: 0 if (tx, ty) in horiz else 1)
        h_surf = pygame.Surface((ts, ts))
        renderer._draw_static_tile_to_surface(h_surf, state, (2, 2, 5, 5), (0, 0, ts, ts))
        assert h_surf.get_at((ts // 2, 0))[:3] == constants.AQUEDUCT_TROUGH_RIM_NORTH
        assert h_surf.get_at((ts // 2, ts - 1))[:3] == constants.AQUEDUCT_TROUGH_RIM_SOUTH
        assert h_surf.get_at((0, ts // 2))[:3] == constants.AQUEDUCT_WATER_BASE_COLOR
        assert h_surf.get_at((ts - 1, ts // 2))[:3] == constants.AQUEDUCT_WATER_BASE_COLOR

        # 3. Vertical channel: (2,1), (2,2), (2,3) are water -> W & E get 3px rims; N & S stay open water
        vert = {(2, 1), (2, 2), (2, 3)}
        monkeypatch.setattr(renderer, "_get_tile_stratum", lambda _st, tx, ty: 0 if (tx, ty) in vert else 1)
        v_surf = pygame.Surface((ts, ts))
        renderer._draw_static_tile_to_surface(v_surf, state, (2, 2, 5, 5), (0, 0, ts, ts))
        assert v_surf.get_at((0, ts // 2))[:3] == constants.AQUEDUCT_TROUGH_RIM_SIDE
        assert v_surf.get_at((ts - 1, ts // 2))[:3] == constants.AQUEDUCT_TROUGH_RIM_SIDE
        assert v_surf.get_at((ts // 2, 0))[:3] == constants.AQUEDUCT_WATER_BASE_COLOR
        assert v_surf.get_at((ts // 2, ts - 1))[:3] == constants.AQUEDUCT_WATER_BASE_COLOR
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sunlit_aqueducts_atmosphere_headless_and_non_duplicating(monkeypatch):
    """Verify ambient water ripples/glints/motes draw on sunlit_aqueducts without duplicating wading ripples."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    ts = constants.TILE_SIZE

    state = _make_aqueduct_state(
        [
            "#########",
            "#.......#",
            "#.......#",
            "#.......#",
            "#.......#",
            "#########",
        ],
        biome="sunlit_aqueducts",
    )
    try:
        # Place player on dry terracotta (1, 1) while (3..6, 2..3) is a visible water channel
        state.player.x = float(1 * ts + 4)
        state.player.y = float(1 * ts + 4)
        water_tiles = {(tx, ty) for tx in range(3, 7) for ty in range(2, 4)}
        monkeypatch.setattr(renderer, "_get_tile_stratum", lambda _st, tx, ty: 0 if (tx, ty) in water_tiles else 1)

        wade_calls = []
        orig_wade = renderer._draw_player_water_ripples
        monkeypatch.setattr(
            renderer,
            "_draw_player_water_ripples",
            lambda *a, **kw: (wade_calls.append(True), orig_wade(*a, **kw))[1],
        )

        # 1. Direct atmosphere call draws ambient ripples, glints, and motes without calling wading ripples
        screen.fill((0, 0, 0))
        renderer._fx_surface_cache.clear()
        renderer.draw_sunlit_aqueducts_atmosphere(state, 0.0, 0.0, now=4.25)

        assert not wade_calls
        cache_tags = {key[0] for key in renderer._fx_surface_cache}
        assert "aqueduct_ripple" in cache_tags
        assert "aqueduct_glint" in cache_tags
        assert "aqueduct_sunlit_mote" in cache_tags

        # Verify pixels were actually drawn onto the screen
        nonzero_pixels = sum(
            1
            for py in range(0, 6 * ts, 2)
            for px in range(0, 9 * ts, 2)
            if screen.get_at((px, py))[:3] != (0, 0, 0)
        )
        assert nonzero_pixels > 0

        # 2. Full Renderer.render() calls draw_sunlit_aqueducts_atmosphere and wading ripples once each
        atmo_calls = []
        orig_atmo = renderer.draw_sunlit_aqueducts_atmosphere
        monkeypatch.setattr(
            renderer,
            "draw_sunlit_aqueducts_atmosphere",
            lambda *a, **kw: (atmo_calls.append(True), orig_atmo(*a, **kw))[1],
        )
        wade_calls.clear()
        renderer.render(state)
        assert len(atmo_calls) == 1
        assert len(wade_calls) == 1

        # 3. Different biome is a strict no-op
        other_state = _make_aqueduct_state(["#####", "#...#", "#...#", "#####"], biome="windy_ridge")
        try:
            other_state.player.x = float(2 * ts)
            other_state.player.y = float(2 * ts)
            screen.fill((0, 0, 0))
            orig_atmo(other_state, 0.0, 0.0, now=4.25)
            assert screen.get_at((2 * ts, 2 * ts))[:3] == (0, 0, 0)
        finally:
            other_state.shutdown_save_worker(timeout=1.0)
    finally:
        state.shutdown_save_worker(timeout=1.0)
