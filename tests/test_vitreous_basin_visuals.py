# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Glass Salt Flats (vitreous_basin) warm palette, 80x80 Fire Chalices, and heat atmosphere."""
# pylint: disable=no-member,protected-access
import glob
import json
import os
from types import SimpleNamespace

import pygame

import constants
from engine.player import Player
from engine.world import LevelLoader, World
from generate_assets import (
    DEFAULT_VITREOUS_FIRE_CHALICE_PATH,
    DEFAULT_VITREOUS_GLASS_FLAT_PATH,
    DEFAULT_VITREOUS_SALT_FLOOR_PATH,
    DEFAULT_VITREOUS_SALT_SPIRE_PATH,
    generate_vitreous_fire_chalice,
)
from generate_maps import SYMBOL_FIRE_CHALICE, SYMBOL_FLOOR
from rendering.renderer import Renderer
from tools.edit_map import MASTER_TOOL_REGISTRY


def _avg_opaque_rgb(surface):
    """Compute average (r, g, b) across all opaque pixels (alpha > 128)."""
    w, h = surface.get_size()
    r_sum = g_sum = b_sum = count = 0
    for y in range(h):
        for x in range(w):
            col = surface.get_at((x, y))
            if col.a > 128:
                r_sum += col.r
                g_sum += col.g
                b_sum += col.b
                count += 1
    assert count > 0
    return (r_sum / count, g_sum / count, b_sum / count)


def test_vitreous_basin_palette_is_warm_amber_terracotta_vs_frozen_peaks():
    """Verify vitreous_basin palette uses warm amber/ochre/terracotta tones unmistakably distinct from frozen_peaks."""
    vit = constants.BIOME_PALETTES["vitreous_basin"]
    frz = constants.BIOME_PALETTES["frozen_peaks"]

    for key in (
        "floor_base",
        "floor_alt",
        "floor_accent",
        "floor_speck",
        "wall_top",
        "wall_hi",
        "wall_face",
        "wall_mortar",
        "wall_glow",
    ):
        r, g, b = vit[key]
        assert r > g > b, f"vitreous_basin[{key}]={vit[key]} should be warm (r > g > b)"
        assert r - b >= 40, f"vitreous_basin[{key}]={vit[key]} lacks warm amber/terracotta separation"

    for idx, (c_lo, c_hi) in enumerate(vit["strata"]):
        for col in (c_lo, c_hi):
            assert col[0] > col[1] > col[2], f"vitreous_basin stratum {idx} {col} must be warm"
            assert col[0] - col[2] >= 75

    # Contrast against frozen_peaks cool snow/ice floor_base
    assert frz["floor_base"][2] >= frz["floor_base"][0]
    assert vit["floor_base"][0] - vit["floor_base"][2] >= 90


def test_vitreous_assets_warm_tiles_and_80x80_fire_chalice_sprite():
    """Verify regenerated vitreous_basin PNG tiles are warm and vitreous_fire_chalice.png is 80x80 blazing."""
    pygame.init()

    for path in (
        DEFAULT_VITREOUS_SALT_FLOOR_PATH,
        DEFAULT_VITREOUS_GLASS_FLAT_PATH,
        DEFAULT_VITREOUS_SALT_SPIRE_PATH,
    ):
        assert os.path.isfile(path), f"Missing asset: {path}"
        surf = pygame.image.load(path)
        assert surf.get_size() == (40, 40)
        avg_r, avg_g, avg_b = _avg_opaque_rgb(surf)
        assert avg_r > avg_g > avg_b, f"{path} should have warm amber/ochre average RGB, got {(avg_r, avg_g, avg_b)}"
        assert avg_r - avg_b >= 50.0, f"{path} too cool/snow-like: {(avg_r, avg_g, avg_b)}"

    # 80x80 Blazing Fire Chalice on disk and procedural generator parity
    assert os.path.isfile(DEFAULT_VITREOUS_FIRE_CHALICE_PATH)
    disk_chalice = pygame.image.load(DEFAULT_VITREOUS_FIRE_CHALICE_PATH)
    proc_chalice = generate_vitreous_fire_chalice(80, 80)
    for chalice in (disk_chalice, proc_chalice):
        assert chalice.get_size() == (constants.VITREOUS_FIRE_CHALICE_SIZE, constants.VITREOUS_FIRE_CHALICE_SIZE)
        assert chalice.get_at((0, 0)).a == 0, "Chalice corners must be transparent"

        flame_pixels = 0
        for y in range(4, 30):
            for x in range(16, 64):
                c = chalice.get_at((x, y))
                if c.a > 180 and c.r >= 220 and c.g >= 60 and c.r > c.b + 60:
                    flame_pixels += 1
        assert flame_pixels >= 120, f"Expected blazing flame plume in upper half, got {flame_pixels} pixels"


def test_fire_chalice_symbol_editor_parity_loader_and_segments():
    """Verify 'V' Fire Chalice is mirrored in edit_map.py, loads as solid 80x80 GameObject, and spawns cleanly."""
    tool_entry = next((t for t in MASTER_TOOL_REGISTRY if t.get("char") == SYMBOL_FIRE_CHALICE), None)
    assert tool_entry is not None, "Palette Divergence Law: 'V' Fire Chalice must exist in MASTER_TOOL_REGISTRY"
    assert "80x80" in tool_entry["size"]

    proto = [
        "######",
        "#....#",
        "#.V..#",
        "#....#",
        "######",
    ]
    _grid, interactables, _warps, _start, _enemies = LevelLoader.parse_map(proto, map_name="chalice_test")
    chalice = next((obj for obj in interactables if obj.name == "Fire Chalice"), None)
    assert chalice is not None
    assert chalice.is_solid is True
    assert (chalice.width, chalice.height) == (constants.TILE_SIZE * 2, constants.TILE_SIZE * 2)

    # All generated vitreous_basin segments should include valid non-clipping 2x2 Fire Chalices
    seg_paths = sorted(glob.glob("maps/segments/vitreous_basin/*.json"))
    assert len(seg_paths) >= 8
    total_chalices = 0
    for path in seg_paths:
        with open(path, "r", encoding="utf-8") as handle:
            grid = json.load(handle)["grid"]
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch == SYMBOL_FIRE_CHALICE:
                    total_chalices += 1
                    assert x + 1 < len(row) - 1 and y + 1 < len(grid) - 1
                    assert grid[y][x + 1] == SYMBOL_FLOOR
                    assert grid[y + 1][x] == SYMBOL_FLOOR
                    assert grid[y + 1][x + 1] == SYMBOL_FLOOR
    assert total_chalices >= 8, "Expected blazing Fire Chalices placed across vitreous_basin segment pools"


def test_renderer_loads_80x80_chalice_and_renders_heat_shimmer_embers():
    """Verify Renderer loads 80x80 VitreousFireChalice, renders it, and draws heat-shimmer/embers on vitreous_basin."""
    pygame.init()
    screen = pygame.Surface((640, 360))
    renderer = Renderer(screen)

    assert "VitreousFireChalice" in renderer.prop_cache
    assert renderer.prop_cache["VitreousFireChalice"].get_size() == (80, 80)

    # 1. Fire Chalice renders warm blazing pixels at its 80x80 location
    proto = [
        "########",
        "#......#",
        "#..V...#",
        "#......#",
        "#......#",
        "########",
    ]
    world = World("vitreous_basin")
    world.load_from_prototype(proto)
    chalice = next(obj for obj in world.interactables if obj.name == "Fire Chalice")
    screen.fill((12, 12, 16))
    renderer._draw_vitreous_fire_chalice(chalice, 120.0, 80.0, 1.25, renderer.prop_cache, True)
    warm_chalice_px = 0
    for y in range(70, 165, 2):
        for x in range(110, 210, 2):
            r, g, b = screen.get_at((x, y))[:3]
            if r > 140 and r > b + 50:
                warm_chalice_px += 1
    assert warm_chalice_px >= 100

    # 2. Heat-shimmer & rising embers draw on vitreous_basin, stay silent on frozen_peaks / DILUTION
    player = Player(160.0, 120.0)
    mock_state = SimpleNamespace(
        world=world,
        player=player,
        bleed_state="GRACE_PERIOD",
        weather_manager=None,
        current_boss_coords=None,
        active_safe_radius=1000000.0,
    )
    bg = (20, 20, 26)
    screen.fill(bg)
    renderer.draw_vitreous_basin_atmosphere(mock_state, 0.0, 0.0, now=3.5)
    warm_atmo_px = 0
    for y in range(0, 360, 3):
        for x in range(0, 640, 3):
            r, g, b = screen.get_at((x, y))[:3]
            if (r, g, b) != bg and r > b:
                warm_atmo_px += 1
    assert warm_atmo_px >= 40, "Expected warm heat-shimmer bands & rising embers on vitreous_basin"

    # Silent during DILUTION
    mock_state.bleed_state = "DILUTION"
    screen.fill(bg)
    renderer.draw_vitreous_basin_atmosphere(mock_state, 0.0, 0.0, now=3.5)
    assert screen.get_at((320, 180))[:3] == bg

    # Silent on frozen_peaks
    frz_world = World("frozen_peaks")
    frz_world.load_from_prototype(proto)
    mock_state.world = frz_world
    mock_state.bleed_state = "GRACE_PERIOD"
    screen.fill(bg)
    renderer.draw_vitreous_basin_atmosphere(mock_state, 0.0, 0.0, now=3.5)
    for y in range(0, 360, 20):
        for x in range(0, 640, 20):
            assert screen.get_at((x, y))[:3] == bg
