# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Windy Ridge Pass 1: Organic Highland Ground Textures & Natural Stratum Seams."""
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
    """Initialize and cleanly tear down pygame in dummy video/audio mode."""
    pygame.init()
    yield
    pygame.quit()


def test_windy_ridge_strata_variants_low_contrast_and_pixel_invariant():
    """Verify windy_ridge generates 4 distinct low-contrast (<= +/-12 RGB) variants per stratum with (1,1) intact."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    pal = constants.BIOME_PALETTES["windy_ridge"]
    pack = renderer.biome_tiles["windy_ridge"]
    strata_floors = pack["strata_floors"]
    assert len(strata_floors) == 3

    for s_idx, tier in enumerate(strata_floors):
        s_base = pal["strata"][s_idx][0]
        assert len(tier) == 4
        # All 4 variants must be distinct textured surfaces
        sigs = {pygame.image.tobytes(surf, "RGB") for surf in tier}
        assert len(sigs) == 4, f"Expected 4 distinct variants for windy_ridge stratum {s_idx}"
        # Pixel (1, 1) of variant 0 preserves test_procedural_enemy_graphics invariant
        assert tier[0].get_at((1, 1))[:3] == s_base

        # Every pixel across all variants stays within <= +/-12 RGB of s_base
        for surf in tier:
            assert surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)
            for py in range(0, constants.TILE_SIZE, 2):
                for px in range(0, constants.TILE_SIZE, 2):
                    col = surf.get_at((px, py))[:3]
                    for ch in range(3):
                        assert abs(col[ch] - s_base[ch]) <= 12, (
                            f"Stratum {s_idx} pixel ({px},{py})={col} exceeded +/-12 RGB of {s_base}"
                        )

    assert strata_floors[1][0].get_at((1, 1))[:3] == pal["floor_base"]


def test_windy_ridge_organic_floor_patterns_avoid_neon_polka_dots():
    """Verify windy_ridge floor patterns produce organic accents without bright mint/cyan stamped shapes."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["windy_ridge"]
    ts = constants.TILE_SIZE

    banned_neon = {
        pal["floor_accent"],  # (110, 215, 130) bright mint
        pal["wall_glow"],     # (90, 235, 180) neon seafoam
        pal["wall_hi"],       # (150, 215, 240) bright cyan-blue
        pal["wall_top"],      # (75, 105, 138) stark slate rectangle fill
    }

    for s_idx in (0, 1, 2):
        s_base, s_alt = pal["strata"][s_idx]
        grid_n = 10
        surf = pygame.Surface((grid_n * ts, grid_n * ts))
        surf.fill(s_base)
        for ty in range(grid_n):
            for tx in range(grid_n):
                dr = (tx * ts, ty * ts, ts, ts)
                renderer._draw_connected_floor_patterns(
                    surf, ("windy_ridge", pal, s_idx, s_alt), (tx, ty, grid_n, grid_n), dr
                )

        sampled = {
            surf.get_at((px, py))[:3]
            for py in range(0, grid_n * ts, 4)
            for px in range(0, grid_n * ts, 4)
        }
        assert len(sampled) >= 3, f"Stratum {s_idx} should contain organic texture accents"
        assert not (sampled & banned_neon), f"Stratum {s_idx} drew legacy neon color(s): {sampled & banned_neon}"


def test_windy_ridge_soft_stratum_borders_without_neon_contours(monkeypatch):
    """Verify windy_ridge stratum transitions draw soft blended seams with zero neon-mint or sky-blue contours."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["windy_ridge"]
    strata_defs = pal["strata"]
    ts = constants.TILE_SIZE

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    state.world.name = "windy_ridge"
    state.world.load_from_prototype([".....", ".....", ".....", ".....", "....."])

    banned_contour = {pal["floor_accent"], pal["wall_hi"], pal["wall_mortar"]}

    for center_stratum in (0, 2):
        # Place a 1-tile island of center_stratum at (2, 2) surrounded by stratum 1 meadow
        monkeypatch.setattr(
            renderer,
            "_get_tile_stratum",
            lambda _st, tx, ty, cs=center_stratum: cs if (tx, ty) == (2, 2) else 1,
        )

        surf = pygame.Surface((ts, ts))
        s_base = strata_defs[center_stratum][0]
        surf.fill(s_base)
        renderer._draw_stratum_perimeter_borders(
            surf, state, (2, 2, 5, 5), (0, 0, ts, ts), ("windy_ridge", pal, center_stratum, strata_defs)
        )

        seam = constants.compute_floor_seam_colors("windy_ridge", pal, center_stratum)
        all_colors = {surf.get_at((px, py))[:3] for py in range(ts) for px in range(ts)}
        assert seam["rim_hi"] in all_colors and seam["rim_lo"] in all_colors, (
            f"Expected soft blended seam {seam['rim_hi']}/{seam['rim_lo']} for stratum {center_stratum}"
        )
        assert not (all_colors & banned_contour), (
            f"Found harsh contour spike {all_colors & banned_contour} on stratum {center_stratum} seam"
        )
