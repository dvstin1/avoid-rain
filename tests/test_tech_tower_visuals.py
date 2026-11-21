"""Unit tests for Tech Tower Pass 1: Recessed Grating, Titanium Deck, Chamfered Seams & Bulkhead Walls."""
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
    """Initialize and cleanly tear down pygame in headless dummy video/audio mode."""
    pygame.init()
    yield
    pygame.quit()


def test_tech_tower_strata_variants_low_contrast_and_pixel_invariant():
    """Verify tech_tower generates 4 distinct low-contrast (<= +/-12 RGB) variants per stratum with (1,1) intact."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    pal = constants.BIOME_PALETTES["tech_tower"]
    pack = renderer.biome_tiles["tech_tower"]
    strata_floors = pack["strata_floors"]
    assert len(strata_floors) == 3

    for s_idx, tier in enumerate(strata_floors):
        s_base = pal["strata"][s_idx][0]
        assert len(tier) == 4
        sigs = {pygame.image.tobytes(surf, "RGB") for surf in tier}
        assert len(sigs) == 4, f"Expected 4 distinct variants for tech_tower stratum {s_idx}"
        assert tier[0].get_at((1, 1))[:3] == s_base

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


def test_tech_tower_floor_patterns_mute_conduits_and_ban_bright_ovals():
    """Verify tech_tower floor patterns eliminate bright (0,145,185) ovals and neon cyan/magenta spikes."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["tech_tower"]
    ts = constants.TILE_SIZE

    banned_glare = {
        pal["strata"][0][1],  # (0, 145, 185) bright teal-cyan macro oval underlay
        pal["floor_accent"],  # (0, 230, 255) blazing #00E6FF
        pal["wall_glow"],     # (0, 245, 255) blazing cyan
        pal["floor_speck"],   # (255, 65, 185) blazing neon magenta
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
                    surf, ("tech_tower", pal, s_idx, s_alt), (tx, ty, grid_n, grid_n), dr
                )

        sampled = {
            surf.get_at((px, py))[:3]
            for py in range(0, grid_n * ts, 2)
            for px in range(0, grid_n * ts, 2)
        }
        assert len(sampled) >= 3, f"Stratum {s_idx} should render metallic/conduit variation"
        assert not (sampled & banned_glare), f"Stratum {s_idx} drew glaring legacy color(s): {sampled & banned_glare}"


def test_tech_tower_chamfered_stratum_borders_no_neon_outline(monkeypatch):
    """Verify tech_tower stratum seams draw 25%-darker steel bevels with zero #00E6FF perimeter lines."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["tech_tower"]
    strata_defs = pal["strata"]
    ts = constants.TILE_SIZE

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    state.world.name = "tech_tower"
    state.world.load_from_prototype([".....", ".....", ".....", ".....", "....."])

    expected_shadow = tuple(max(0, int(c * 0.75)) for c in strata_defs[1][0])
    banned_neon = {pal["floor_accent"], pal["wall_glow"]}

    for center_stratum in (0, 2):
        monkeypatch.setattr(
            renderer,
            "_get_tile_stratum",
            lambda _st, tx, ty, cs=center_stratum: cs if (tx, ty) == (2, 2) else 1,
        )

        surf = pygame.Surface((ts, ts))
        surf.fill(strata_defs[center_stratum][0])
        renderer._draw_stratum_perimeter_borders(
            surf, state, (2, 2, 5, 5), (0, 0, ts, ts), ("tech_tower", pal, center_stratum, strata_defs)
        )

        all_colors = {surf.get_at((px, py))[:3] for py in range(ts) for px in range(ts)}
        assert expected_shadow in all_colors, (
            f"Expected 25%-darker steel bevel {expected_shadow} on stratum {center_stratum}"
        )
        assert not (all_colors & banned_neon), (
            f"Found neon cyan contour spike {all_colors & banned_neon} on stratum {center_stratum}"
        )


def test_tech_tower_engineered_wall_bulkheads_vary_across_tiles():
    """Verify tech_tower wall tops and south bulkhead facades render varied engineered titanium plates."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["tech_tower"]
    ts = constants.TILE_SIZE

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    state.world.name = "tech_tower"
    state.world.load_from_prototype([
        "########",
        "########",
        "########",
        "........",
    ])

    top_sigs = set()
    facade_sigs = set()
    for tx in range(1, 7):
        top_surf = pygame.Surface((ts, ts))
        renderer._draw_connected_wall_tile(top_surf, state, (tx, 1, 8, 4), (0, 0, ts, ts), ("tech_tower", pal))
        top_sigs.add(pygame.image.tobytes(top_surf, "RGB"))
        top_colors = {top_surf.get_at((px, py))[:3] for py in range(0, ts, 2) for px in range(0, ts, 2)}
        assert pal["wall_glow"] not in top_colors

        fac_surf = pygame.Surface((ts, ts))
        renderer._draw_connected_wall_tile(fac_surf, state, (tx, 2, 8, 4), (0, 0, ts, ts), ("tech_tower", pal))
        facade_sigs.add(pygame.image.tobytes(fac_surf, "RGB"))
        fac_colors = {fac_surf.get_at((px, py))[:3] for py in range(0, ts, 2) for px in range(0, ts, 2)}
        assert pal["wall_glow"] not in fac_colors

    assert len(top_sigs) >= 3, f"Expected varied engineered wall tops, got {len(top_sigs)} unique tiles"
    assert len(facade_sigs) >= 2, f"Expected varied south bulkhead facades, got {len(facade_sigs)} unique tiles"
