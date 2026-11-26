# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Venomous Mire (swamp_mire) Pass 1: strata grain, mycelium patterns, soft seams & root cliffs."""
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


def test_swamp_mire_stratum_variants_distinct_low_contrast_and_invariant():
    """Verify 4 distinct <= +/-12 RGB variants per stratum and (1, 1) == s_base invariant."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["swamp_mire"]
    strata_floors = renderer.biome_tiles["swamp_mire"]["strata_floors"]
    assert len(strata_floors) == 3

    for s_idx, (s_base, _s_alt) in enumerate(pal["strata"]):
        variants = strata_floors[s_idx]
        assert len(variants) == 4
        assert variants[0].get_at((1, 1))[:3] == s_base

        variant_bytes = set()
        for surf in variants:
            assert surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)
            variant_bytes.add(pygame.image.tobytes(surf, "RGB"))
            for py in range(0, constants.TILE_SIZE, 2):
                for px in range(0, constants.TILE_SIZE, 2):
                    col = surf.get_at((px, py))[:3]
                    for ch in range(3):
                        assert abs(col[ch] - s_base[ch]) <= 12, (
                            f"Stratum {s_idx} pixel ({px},{py}) drifted >12 RGB from {s_base}: {col}"
                        )
        assert len(variant_bytes) == 4, f"Expected 4 distinct variants for swamp_mire stratum {s_idx}"

    assert strata_floors[1][0].get_at((1, 1))[:3] == pal["floor_base"]


def _render_swamp_patch_colors(renderer, pal, s_idx, grid_n=6):
    """Render a grid_n x grid_n patch of a swamp_mire stratum and return sampled RGB colors."""
    ts = constants.TILE_SIZE
    s_base, s_alt = pal["strata"][s_idx]
    surf = pygame.Surface((ts * grid_n, ts * grid_n))
    surf.fill(s_base)
    for ty in range(grid_n):
        for tx in range(grid_n):
            dr = (tx * ts, ty * ts, ts, ts)
            renderer._draw_connected_floor_patterns(
                surf, ("swamp_mire", pal, s_idx, s_alt), (tx, ty, grid_n, grid_n), dr
            )
    return {
        surf.get_at((px, py))[:3]
        for py in range(0, ts * grid_n, 2)
        for px in range(0, ts * grid_n, 2)
    }


def test_swamp_mire_floor_patterns_remove_white_ring_grid_and_bright_scum_ovals():
    """Verify Stratum 2 replaces white-ring grid with mycelium/fissures, and S0/S1 suppress raw neon ovals."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["swamp_mire"]

    # 1. Stratum 2: no stark wall_hi (216, 202, 226) stamped ring grid, but visible organic detail
    s2_colors = _render_swamp_patch_colors(renderer, pal, 2)
    assert pal["wall_hi"] not in s2_colors, "Stamped stark wall_hi white-ring grid should be removed on Stratum 2"
    assert len(s2_colors) >= 4, "Stratum 2 should render fissures, mycelium veins, and sparse spore pustules"

    # 2. Stratum 0 & 1: no raw neon floor_accent (142, 172, 44) ovals stamped across every block
    for s_idx in (0, 1):
        bog_colors = _render_swamp_patch_colors(renderer, pal, s_idx)
        assert pal["floor_accent"] not in bog_colors, (
            f"Raw neon floor_accent ovals should not stamp across swamp_mire Stratum {s_idx}"
        )
        assert len(bog_colors) >= 3, f"Expected organic ripples and sparse algae patches on Stratum {s_idx}"


def test_swamp_mire_stratum_borders_soft_shoreline_and_chitin_lip():
    """Verify 45-degree organic corner bevels, feathered algae edge (S0), and bruised-lilac chitin lip (S2)."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["swamp_mire"]
    strata_defs = pal["strata"]
    ts = constants.TILE_SIZE

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world.name = "swamp_mire"
        state.world.load_from_prototype(["..." for _ in range(3)])

        # Isolated center tile (1, 1) surrounded by Stratum 1 -> all 4 cardinal edges + all 4 outer corners exposed
        for s_idx, forbidden_col in ((0, pal["floor_accent"]), (2, pal["wall_hi"])):
            renderer._get_tile_stratum = lambda _st, x, y, target=s_idx: target if (x, y) == (1, 1) else 1
            tile_surf = pygame.Surface((ts, ts))
            tile_surf.fill(strata_defs[s_idx][0])
            renderer._draw_stratum_perimeter_borders(
                tile_surf,
                state,
                (1, 1, 3, 3),
                (0, 0, ts, ts),
                ("swamp_mire", pal, s_idx, strata_defs),
            )
            # Outer NW corner must be beveled into surrounding Stratum 1 canvas
            assert tile_surf.get_at((0, 0))[:3] == strata_defs[1][0]
            border_colors = {
                tile_surf.get_at((px, py))[:3]
                for py in range(ts)
                for px in range(ts)
            }
            assert forbidden_col not in border_colors, (
                f"Harsh perimeter color {forbidden_col} should not appear on swamp_mire Stratum {s_idx}"
            )
            assert len(border_colors) >= 3, f"Expected beveled shoreline/chitin border detail on Stratum {s_idx}"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_swamp_mire_walls_organic_root_facades_and_mortar_invariant():
    """Verify swamp_mire wall tops & root-overhang south facades vary organically and keep bottom wall_mortar."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["swamp_mire"]
    ts = constants.TILE_SIZE

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world.name = "swamp_mire"
        state.world.load_from_prototype(["####", "####"])

        top_surf = pygame.Surface((ts, ts))
        renderer._draw_connected_wall_tile(top_surf, state, (0, 0, 4, 2), (0, 0, ts, ts), ("swamp_mire", pal))

        facade_hashes = set()
        for tx in range(4):
            bot_surf = pygame.Surface((ts, ts))
            renderer._draw_connected_wall_tile(bot_surf, state, (tx, 1, 4, 2), (0, 0, ts, ts), ("swamp_mire", pal))
            # Preserve exact pixel (20, TILE_SIZE - 2) == wall_mortar test invariant
            assert bot_surf.get_at((20, ts - 2))[:3] == pal["wall_mortar"]
            assert pygame.image.tobytes(bot_surf, "RGB") != pygame.image.tobytes(top_surf, "RGB")
            facade_hashes.add(pygame.image.tobytes(bot_surf, "RGB"))

        # Adjacent south-facing cliff columns should vary organically (not identical stamped horizontal bars)
        assert len(facade_hashes) >= 3
    finally:
        state.shutdown_save_worker(timeout=1.0)
