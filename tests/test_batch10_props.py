# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Batch 10: Environment & Prop Sprite Overhaul.

Covers procedural barrel_0..3.png + biome-matched break/rubble colors (tech_tower cyan/slate),
swamp_barrel.png vs. non-interactive swamp_spore_pod.png mire accents, non-religious
highland_monolith.png, common pastoral_rock.png + rare pastoral_shepherd_cairn.png ratio,
80x40 Bench dimensions & 2x1 map footprint, 4 tree_structure variants, and uneven Sanctuary
roof moss distribution.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.world import GameObject, LevelLoader, World
from generate_assets import (
    generate_barrel_frame,
    generate_bench,
    generate_highland_monolith,
    generate_pastoral_rock,
    generate_sanctuary_roof_tile,
    generate_swamp_barrel,
    generate_tree_structure,
)
from generate_maps import SYMBOL_BENCH, _get_solid_prop_footprint
from rendering.renderer import Renderer
from tools.edit_map import MASTER_TOOL_REGISTRY


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_procedural_barrels_and_tech_tower_biome_rubble():
    """Verify barrel_0..3.png generate uniquely and tech_tower break/rubble uses metallic cyan/slate debris."""
    frames = [generate_barrel_frame(stage) for stage in range(4)]
    raw_bytes = set()
    for stage, surf in enumerate(frames):
        fpath = os.path.join("assets", "graphics", f"barrel_{stage}.png")
        assert os.path.exists(fpath)
        assert surf.get_size() == (40, 40)
        assert surf.get_flags() & pygame.SRCALPHA != 0
        assert surf.get_at((0, 0)).a == 0
        raw_bytes.add(pygame.image.tobytes(surf, "RGBA"))
    assert len(raw_bytes) == 4, "All 4 barrel stages must be visually distinct"

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("tech_tower")
        state.world.load_from_prototype(["." * 8 for _ in range(8)])
        barrel = GameObject((160, 160), (40, 40))
        barrel.name = "Barrel"
        barrel.is_solid = True
        barrel.is_breakable = True
        barrel.health = 1.0
        state.world.interactables = [barrel]

        # Simulate barrel break carrying biome tag into fading_entities -> world_debris
        biome_tag = state._resolve_prop_biome(barrel)
        assert biome_tag == "tech_tower"
        state.fading_entities.append({"obj": barrel, "time": 0.05, "biome": biome_tag})
        state._update_shared_world(0.1)
        assert any(
            d.get("name") == "BarrelRubble" and d.get("biome") == "tech_tower"
            for d in state.world_debris
        )

        # Verify tech_tower rubble surface contains bright cyan coolant pixels (not brown oak wood)
        tech_rubble = renderer._get_biome_barrel_debris_surface("tech_tower", 3)
        default_rubble = renderer._get_biome_barrel_debris_surface("windy_ridge", 3)
        assert tech_rubble is not None and default_rubble is not None
        assert pygame.image.tobytes(tech_rubble, "RGBA") != pygame.image.tobytes(default_rubble, "RGBA")

        cyan_pixels = sum(
            1
            for y in range(40)
            for x in range(40)
            if tech_rubble.get_at((x, y)).a > 128
            and tech_rubble.get_at((x, y)).b > 190
            and tech_rubble.get_at((x, y)).g > 170
            and tech_rubble.get_at((x, y)).r < 160
        )
        assert cyan_pixels >= 20, f"Expected cyan coolant pixels in tech_tower rubble, got {cyan_pixels}"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_swamp_barrel_vs_non_interactive_spore_pod_accent():
    """Verify swamp_barrel.png preloads for swamp_mire barrels while swamp_spore_pod accents Stratum 0/1 floor."""
    swamp_barrel_path = os.path.join("assets", "graphics", "swamp_barrel.png")
    assert os.path.exists(swamp_barrel_path)
    gen_sb = generate_swamp_barrel()
    assert gen_sb.get_size() == (40, 40) and gen_sb.get_at((0, 0)).a == 0

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "SwampBarrel" in renderer.prop_cache
    assert "SwampSporePod" in renderer.prop_cache

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world = World("swamp_mire")
        state.world.load_from_prototype(["." * 28 for _ in range(12)])

        # Pick a deterministic swamp_mire tile that lands on Stratum 0/1 and matches the % 23 accent hash
        accent_tile = next(
            (tx, ty)
            for ty in range(1, 11)
            for tx in range(1, 27)
            if constants.get_tile_stratum(tx, ty) in (0, 1)
            and (((tx * 73856093) ^ (ty * 19349663)) & 0x7FFFFFFF) % 23 == 0
        )
        sentinel = pygame.Surface((ts, ts), pygame.SRCALPHA)
        sentinel.fill((250, 20, 230, 255))
        renderer.prop_cache["SwampSporePod"] = sentinel

        tile_surf = pygame.Surface((ts, ts))
        renderer._draw_static_tile_to_surface(
            tile_surf, state, (accent_tile[0], accent_tile[1], 0, 0), (0, 0, ts, ts)
        )
        assert tile_surf.get_at((ts // 2, ts // 2))[:3] == (250, 20, 230)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_highland_monolith_non_religious_glyphs():
    """Verify highland_monolith.png preserves 40x60 SRCALPHA and uses geometric wind-spiral glyphs, not a cross."""
    mono_path = os.path.join("assets", "graphics", "highland_monolith.png")
    assert os.path.exists(mono_path)
    mono = generate_highland_monolith(40, 60)
    assert mono.get_size() == (40, 60)
    assert mono.get_flags() & pygame.SRCALPHA != 0
    assert mono.get_at((0, 0)).a == 0

    # Ensure there is no solid vertical+horizontal seafoam cross intersection at the old (19, 17) glyph center
    def _is_rune(px, py):
        c = mono.get_at((px, py))
        return c.g > 180 and c.b > 150 and c.r < 170

    cross_arm_vertical = all(_is_rune(19, y) for y in range(14, 24))
    cross_arm_horizontal = all(_is_rune(x, 17) for x in range(16, 23))
    assert not (cross_arm_vertical and cross_arm_horizontal), "Monolith must not carve a cross shape"

    # Verify seafoam geometric spiral & chevron rune pixels are present on the shaft
    rune_pixels = sum(1 for y in range(12, 46) for x in range(13, 27) if _is_rune(x, y))
    assert rune_pixels >= 20


def test_pastoral_rock_common_vs_rare_shepherd_cairn_distribution():
    """Verify pastoral_rock.png is ~85% of pastoral_valley structures and Shepherd Cairn is ~15%."""
    rock_path = os.path.join("assets", "graphics", "pastoral_rock.png")
    assert os.path.exists(rock_path)
    rock = generate_pastoral_rock(40, 60)
    assert rock.get_size() == (40, 60) and rock.get_at((0, 0)).a == 0

    rare_count = sum(
        1 for ty in range(20) for tx in range(20) if Renderer._is_pastoral_rare_cairn(tx, ty)
    )
    ratio = rare_count / 400.0
    assert 0.10 <= ratio <= 0.22, f"Expected ~15% rare cairns, got {ratio:.2%}"


def test_bench_80x40_sprite_and_2x1_map_footprint():
    """Verify bench.png is 80x40, LevelLoader spawns 80x40 Bench, map footprint reserves (x+1, y), and editor agrees."""
    bench_surf = generate_bench()
    assert bench_surf.get_size() == (80, 40)
    assert bench_surf.get_at((0, 0)).a == 0
    assert pygame.image.load(os.path.join("assets", "graphics", "bench.png")).get_size() == (80, 40)

    proto = ["######", "#....#", "#.S..#", "#....#", "######"]
    bench = next(obj for obj in LevelLoader.parse_map(proto)[1] if obj.name == "Bench")
    assert (bench.width, bench.height) == (80, 40)

    grid = [list(row) for row in proto]
    impassable, owners = _get_solid_prop_footprint(grid)
    assert grid[2][2] == SYMBOL_BENCH
    assert (2, 2) in impassable and (3, 2) in impassable
    assert owners[(2, 2)] == (2, 2) and owners[(3, 2)] == (2, 2)

    bench_tool = next(t for t in MASTER_TOOL_REGISTRY if t["char"] == "S")
    assert "80x40" in bench_tool["size"] and "2x1" in bench_tool["size"]


def test_tree_structure_four_variants_preloaded_and_selected():
    """Verify tree_structure variants 0..3 are distinct, preloaded, and deterministically selected in render."""
    variant_bytes = set()
    for v_idx in range(4):
        fname = "tree_structure.png" if v_idx == 0 else f"tree_structure_{v_idx}.png"
        fpath = os.path.join("assets", "graphics", fname)
        assert os.path.exists(fpath), f"Missing tree variant: {fpath}"
        surf = generate_tree_structure(40, 40, variant=v_idx)
        assert surf.get_size() == (40, 40) and surf.get_at((0, 0)).a == 0
        variant_bytes.add(pygame.image.tobytes(surf, "RGBA"))
    assert len(variant_bytes) == 4, "All 4 tree variants must be visually distinct"

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    for key in ("Structure", "Structure_1", "Structure_2", "Structure_3"):
        assert key in renderer.prop_cache
        assert renderer.prop_cache[key].get_size() == (40, 40)

    # Confirm Renderer.render selects multiple distinct tree variants across coordinates using color sentinels
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        ts = constants.TILE_SIZE
        state.world = World("sanctuary")
        state.world.load_from_prototype(["." * 14 for _ in range(10)])
        sentinel_colors = {
            "Structure": (240, 20, 20),
            "Structure_1": (20, 240, 20),
            "Structure_2": (20, 20, 240),
            "Structure_3": (240, 220, 20),
        }
        for key, rgb in sentinel_colors.items():
            s = pygame.Surface((ts, ts), pygame.SRCALPHA)
            s.fill((*rgb, 255))
            renderer.prop_cache[key] = s

        trees = []
        for tx in range(2, 12):
            t_obj = GameObject((tx * ts, 4 * ts), (ts, ts))
            t_obj.name = "Structure"
            t_obj.is_solid = True
            trees.append(t_obj)
        state.world.interactables = trees
        state.player.x, state.player.y = 6 * ts, 7 * ts
        state.camera.instant_center((6 * ts, 4 * ts))

        renderer.render(state)
        ox, oy = state.camera.get_offset()
        seen_colors = set()
        for t_obj in trees:
            sx = int(t_obj.x - ox + ts // 2)
            sy = int(t_obj.y - oy + ts // 2)
            if 0 <= sx < screen.get_width() and 0 <= sy < screen.get_height():
                px = screen.get_at((sx, sy))[:3]
                if px in sentinel_colors.values():
                    seen_colors.add(px)
        assert len(seen_colors) >= 3, f"Expected multiple tree variants rendered, got {seen_colors}"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sanctuary_roof_moss_is_uneven_across_tiles():
    """Verify clean roof tile variants 0..3 exist and composited Sanctuary roof moss varies organically per tile."""
    base_tile = generate_sanctuary_roof_tile(40, 40, variant=0)
    assert base_tile.get_size() == (40, 40)
    # Clean base roof tile should not stamp bright green moss circles at the old fixed spots
    green_moss_px = sum(
        1
        for y in range(40)
        for x in range(40)
        if base_tile.get_at((x, y)).g > base_tile.get_at((x, y)).b + 8
    )
    assert green_moss_px == 0, f"Base roof tile should be clean slate without uniform moss, got {green_moss_px} px"

    for v_idx in range(1, 4):
        fpath = os.path.join("assets", "graphics", f"sanctuary_roof_tile_{v_idx}.png")
        assert os.path.exists(fpath)

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    for key in ("SanctuaryRoofTile", "SanctuaryRoofTile_1", "SanctuaryRoofTile_2", "SanctuaryRoofTile_3"):
        assert key in renderer.prop_cache

    roof_surf = renderer._get_sanctuary_roof_surface({"name": "scriptorium_roof", "w": 12, "h": 8})
    # Count moss pixels per 40x40 roof tile and verify strong non-uniformity (some clean tiles, some mossy clusters)
    ts = constants.TILE_SIZE
    per_tile_moss = []
    for ty in range(8):
        for tx in range(12):
            m_px = 0
            for py in range(ty * ts, (ty + 1) * ts, 2):
                for px in range(tx * ts, (tx + 1) * ts, 2):
                    col = roof_surf.get_at((px, py))
                    if col.g > col.b + 6 and col.g > col.r + 6:
                        m_px += 1
            per_tile_moss.append(m_px)

    assert any(c == 0 for c in per_tile_moss), "Expected clean moss-free slate tiles on Sanctuary roof"
    assert any(c >= 12 for c in per_tile_moss), "Expected organic moss clusters on some Sanctuary roof tiles"
    assert len(set(per_tile_moss)) >= 4, "Moss distribution across roof tiles must not be uniform"
