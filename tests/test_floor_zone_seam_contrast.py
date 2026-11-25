# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests verifying softened flat floor-to-floor seam contrast vs crisp wall/cliff edges across all biomes."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from generate_assets import (
    DEFAULT_AQUEDUCT_TERRACOTTA_FLOOR_PATH,
    DEFAULT_VITREOUS_GLASS_FLAT_PATH,
    DEFAULT_VITREOUS_SALT_FLOOR_PATH,
)
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def _luminance(rgb) -> float:
    """Compute Rec. 601 perceived luminance for an RGB tuple."""
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _make_state(biome_name: str, prototype: list[str]) -> GameState:
    """Create a headless offline GameState populated with the given prototype grid."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    state.world.name = biome_name
    state.world.load_from_prototype(prototype)
    return state


def test_compute_floor_seam_colors_softer_than_wall_cliff_edges_all_biomes():
    """Verify every biome's computed flat floor seam avoids wall_mortar/wall_hi and has softer contrast than walls."""
    for biome, pal in constants.BIOME_PALETTES.items():
        wall_mortar = pal["wall_mortar"]
        wall_hi = pal["wall_hi"]
        wall_contrast = abs(_luminance(wall_hi) - _luminance(wall_mortar))
        wm_lum = _luminance(wall_mortar)

        for s_idx in (0, 2):
            seam = constants.compute_floor_seam_colors(biome, pal, s_idx)
            rim_hi = seam["rim_hi"]
            rim_lo = seam["rim_lo"]
            inner_lip = seam["inner_lip"]

            assert rim_hi != wall_mortar, f"{biome} S{s_idx} rim_hi reused wall_mortar"
            assert rim_lo != wall_mortar, f"{biome} S{s_idx} rim_lo reused wall_mortar"
            assert rim_hi != wall_hi, f"{biome} S{s_idx} rim_hi reused stark wall_hi"

            # Flat floor seam edges must stay strictly lighter than deep cliff wall_mortar
            assert _luminance(rim_hi) > wm_lum, f"{biome} S{s_idx} rim_hi is darker than wall_mortar"
            assert _luminance(rim_lo) > wm_lum, f"{biome} S{s_idx} rim_lo is darker than wall_mortar"

            # N-vs-S bevel span and inner-lip span must be substantially softer than wall highlight-to-mortar contrast
            seam_span = max(
                abs(_luminance(rim_hi) - _luminance(rim_lo)),
                abs(_luminance(rim_hi) - _luminance(inner_lip)),
                abs(_luminance(rim_lo) - _luminance(inner_lip)),
            )
            assert seam_span < wall_contrast * 0.45, (
                f"{biome} S{s_idx} seam contrast {seam_span:.1f} too sharp vs wall contrast {wall_contrast:.1f}"
            )


def _measure_wall_edge_contrast(renderer, state, biome: str, pal: dict) -> float:
    """Render a south-facing wall tile bordering floor and return its vertical luminance contrast."""
    ts = constants.TILE_SIZE
    wall_surf = pygame.Surface((ts, ts))
    renderer._draw_connected_wall_tile(wall_surf, state, (2, 0, 5, 5), (0, 0, ts, ts), (biome, pal))
    wall_lums = [_luminance(wall_surf.get_at((ts // 2, py))[:3]) for py in range(ts)]
    if biome != "sanctuary":
        assert wall_surf.get_at((ts // 2, ts - 2))[:3] == pal["wall_mortar"], (
            f"{biome} wall south cliff edge lost its crisp wall_mortar undercut"
        )
    return max(wall_lums) - min(wall_lums)


def test_rendered_floor_seams_softer_than_wall_edges_across_all_biomes(monkeypatch):
    """Verify rendered flat floor-to-floor seams have lower contrast than rendered wall/cliff edges in every biome."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    ts = constants.TILE_SIZE

    for biome, pal in constants.BIOME_PALETTES.items():
        strata_defs = pal["strata"]
        state = _make_state(biome, ["#####", "#...#", "#...#", "#...#", "#####"])
        try:
            wall_edge_contrast = _measure_wall_edge_contrast(renderer, state, biome, pal)

            for s_idx in (0, 2):
                monkeypatch.setattr(
                    renderer,
                    "_get_tile_stratum",
                    lambda _st, tx, ty, target=s_idx: target if (tx, ty) == (2, 2) else 1,
                )
                seam_surf = pygame.Surface((ts, ts))
                s_base = strata_defs[s_idx][0]
                seam_surf.fill(s_base)
                renderer._draw_stratum_perimeter_borders(
                    seam_surf, state, (2, 2, 5, 5), (0, 0, ts, ts), (biome, pal, s_idx, strata_defs)
                )

                cardinal_cols = [seam_surf.get_at((ts // 2, py))[:3] for py in (0, 1, ts - 2, ts - 1)]
                assert pal["wall_mortar"] not in cardinal_cols, (
                    f"{biome} S{s_idx} cardinal flat floor seam drew dark wall_mortar"
                )
                assert pal["wall_hi"] not in cardinal_cols, (
                    f"{biome} S{s_idx} cardinal flat floor seam drew stark wall_hi"
                )
                assert seam_surf.get_at((ts // 2, 3))[:3] == s_base, (
                    f"{biome} S{s_idx} flat floor seam intruded past 2px into tile interior"
                )

                seam_lums = [_luminance(col) for col in cardinal_cols] + [_luminance(s_base)]
                floor_seam_contrast = max(seam_lums) - min(seam_lums)
                assert floor_seam_contrast < wall_edge_contrast, (
                    f"{biome} S{s_idx} floor seam contrast ({floor_seam_contrast:.1f}) "
                    f"must be softer than wall/cliff contrast ({wall_edge_contrast:.1f})"
                )
        finally:
            state.shutdown_save_worker(timeout=1.0)


def test_wall_ambient_occlusion_shadows_remain_distinct():
    """Verify wall-to-floor ambient occlusion drop-shadows remain active on floors bordering walls."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    ts = constants.TILE_SIZE

    state = _make_state("frozen_peaks", ["#####", "#...#", "#...#", "#####"])
    try:
        # Compare floor tile directly south of a wall (2, 1) vs open floor tile (2, 2)
        surf_wall_adj = pygame.Surface((ts, ts))
        surf_open = pygame.Surface((ts, ts))
        renderer._get_tile_stratum = lambda _st, _tx, _ty: 1
        renderer._draw_static_tile_to_surface(surf_wall_adj, state, (2, 1, 5, 4), (0, 0, ts, ts))
        renderer._draw_static_tile_to_surface(surf_open, state, (2, 2, 5, 4), (0, 0, ts, ts))

        top_wall_adj_lum = _luminance(surf_wall_adj.get_at((ts // 2, 1))[:3])
        top_open_lum = _luminance(surf_open.get_at((ts // 2, 1))[:3])
        assert top_wall_adj_lum < top_open_lum - 15.0, (
            "Wall north AO drop-shadow must remain crisp and darker than open floor"
        )
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sanctuary_textured_floor_zones_skip_phantom_stratum_cliff_rims(monkeypatch):
    """Verify Sanctuary flagstone/dirt/wood tiles do not draw phantom dark stratum rims across flat floors."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    ts = constants.TILE_SIZE
    pal = constants.BIOME_PALETTES["sanctuary"]

    state = _make_state("sanctuary", [".....", ".....", "....."])
    try:
        monkeypatch.setattr(
            renderer,
            "_get_tile_stratum",
            lambda _st, tx, ty: 2 if (tx, ty) == (2, 1) else 1,
        )
        tile_surf = pygame.Surface((ts, ts))
        renderer._draw_static_tile_to_surface(tile_surf, state, (2, 1, 5, 3), (0, 0, ts, ts))
        edge_colors = {
            tile_surf.get_at((px, py))[:3]
            for px in range(ts)
            for py in (0, 1, ts - 2, ts - 1)
        }
        assert pal["wall_mortar"] not in edge_colors
        assert pal["wall_hi"] not in edge_colors
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_generated_biome_floor_pngs_keep_edges_softer_than_wall_mortar():
    """Verify generated aqueduct & vitreous floor PNGs keep edge/seam pixels lighter than biome wall_mortar."""
    checks = (
        (DEFAULT_AQUEDUCT_TERRACOTTA_FLOOR_PATH, constants.BIOME_PALETTES["sunlit_aqueducts"]["wall_mortar"]),
        (DEFAULT_VITREOUS_SALT_FLOOR_PATH, constants.BIOME_PALETTES["vitreous_basin"]["wall_mortar"]),
        (DEFAULT_VITREOUS_GLASS_FLAT_PATH, constants.BIOME_PALETTES["vitreous_basin"]["wall_mortar"]),
    )
    for asset_path, wall_mortar in checks:
        assert os.path.isfile(asset_path), f"Missing floor tile PNG: {asset_path}"
        surf = pygame.image.load(asset_path)
        w, h = surf.get_size()
        wm_lum = _luminance(wall_mortar)
        min_px_lum = min(_luminance(surf.get_at((x, y))[:3]) for y in range(h) for x in range(w))
        assert min_px_lum > wm_lum + 15.0, (
            f"{asset_path} min luminance ({min_px_lum:.1f}) is too close to wall_mortar ({wm_lum:.1f})"
        )
