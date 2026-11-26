# copyright 2026 Dustin Massop, License: GPLv2
"""Regression tests for Multi-Directional 80px Benches (N/S 80x40, E/W 40x80) and Map Orientation Pass."""
# pylint: disable=no-member,too-many-locals

import glob
import json
import os
from types import SimpleNamespace

import pygame

import constants
from engine.camera import Camera
from engine.player import Player
from engine.world import LevelLoader, World
from generate_assets import generate_bench
from generate_maps import (
    SYMBOL_BENCH,
    SYMBOL_FLOOR,
    SYMBOL_WALL,
    validate_wide_prop_clearances,
)
from rendering.renderer import Renderer
from tools.edit_map import MASTER_TOOL_REGISTRY, MapEditor


def _ensure_pygame():
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def test_directional_bench_sprites_generation_and_renderer_preload():
    """Verify all 4 directional bench PNGs exist with exact sizes, distinct visuals, and preload into prop_cache."""
    _ensure_pygame()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    expected_sizes = {
        "south": (80, 40),
        "north": (80, 40),
        "east": (40, 80),
        "west": (40, 80),
    }
    raw_by_facing = {}
    for facing, exp_size in expected_sizes.items():
        fname = constants.BENCH_SPRITE_FILENAMES[facing]
        cache_key = constants.BENCH_PROP_CACHE_KEYS[facing]
        fpath = os.path.join("assets", "graphics", fname)
        assert os.path.exists(fpath), f"Missing generated directional bench asset: {fpath}"

        disk_surf = pygame.image.load(fpath)
        assert disk_surf.get_size() == exp_size
        assert disk_surf.get_at((0, 0)).a == 0

        gen_surf = generate_bench(facing=facing)
        assert gen_surf.get_size() == exp_size
        assert gen_surf.get_at((0, 0)).a == 0

        assert cache_key in renderer.prop_cache
        assert fname in renderer.image_cache
        assert renderer.prop_cache[cache_key].get_size() == exp_size
        raw_by_facing[facing] = pygame.image.tobytes(gen_surf, "RGBA")

    # All 4 directional bench sprites must be visually distinct
    assert raw_by_facing["south"] != raw_by_facing["north"]
    assert raw_by_facing["east"] != raw_by_facing["west"]
    assert len(set(raw_by_facing.values())) == 4


def test_directional_bench_loading_footprints_perimeter_sealing_and_rendering(tmp_path):
    """Verify LevelLoader footprints (80x40 N/S, 40x80 E/W), vertical perimeter sealing, and directional rendering."""
    _ensure_pygame()
    ts = constants.TILE_SIZE
    map_data = {
        "map_id": "directional_benches_test",
        "dimensions": {"width": 12, "height": 10},
        "grid": [
            "............",
            "..S...S.....",
            "............",
            "..S.....S...",
            "............",
            "............",
            "............",
            "..........S.",  # horizontal south bench at x=w-2 -> must clear on perimeter seal
            "....S.......",  # vertical east bench at y=h-2 -> must clear on perimeter seal
            "............",
        ],
        "entities": {
            "2,1": {"facing": "south"},
            "6,1": {"facing": "north"},
            "2,3": {"facing": "east"},
            "8,3": {"facing": "west"},
            "10,7": {"facing": "south"},
            "4,8": {"facing": "east"},
        },
        "module_sockets": [],
        "seal_outer_perimeter": True,
    }
    map_path = tmp_path / "directional_benches_test.json"
    map_path.write_text(json.dumps(map_data), encoding="utf-8")

    _grid, interactables, *_rest = LevelLoader.load_json_map(str(map_path))
    benches = [obj for obj in interactables if getattr(obj, "name", "") == "Bench"]
    assert len(benches) == 4

    by_tile = {(int(b.x // ts), int(b.y // ts)): b for b in benches}
    assert by_tile[(2, 1)].facing == "south"
    assert (by_tile[(2, 1)].width, by_tile[(2, 1)].height) == (80, 40)
    assert by_tile[(6, 1)].facing == "north"
    assert (by_tile[(6, 1)].width, by_tile[(6, 1)].height) == (80, 40)
    assert by_tile[(2, 3)].facing == "east"
    assert (by_tile[(2, 3)].width, by_tile[(2, 3)].height) == (40, 80)
    assert by_tile[(8, 3)].facing == "west"
    assert (by_tile[(8, 3)].width, by_tile[(8, 3)].height) == (40, 80)

    # Headless render pass exercises all 4 directional sprites and directional fallback without errors
    world = World("sanctuary")
    world.grid = _grid
    world.interactables = interactables
    screen = pygame.Surface((640, 480))
    renderer = Renderer(screen)
    player = Player(200.0, 200.0)
    state = SimpleNamespace(
        world=world,
        player=player,
        camera=Camera(640, 480, len(_grid[0]) * ts, len(_grid) * ts),
        enemies=[],
        loot=[],
        fading_entities=[],
        damage_numbers=[],
        parry_effects=[],
        slash_effects=[],
        impact_sparks=[],
        glyph_particles=None,
        network_manager=SimpleNamespace(remote_players={}),
        stats=None,
        debug_text_enabled=False,
        in_sanctuary=True,
    )
    renderer.render(state)
    # Also verify fallback rendering when directional keys are absent from prop_cache
    for key in constants.BENCH_PROP_CACHE_KEYS.values():
        renderer.prop_cache.pop(key, None)
    renderer.render(state)


def test_sanctuary_and_procedural_bench_orientations_face_focal_features():
    """Verify Sanctuary lakeside/Scriptorium benches and procedural segment benches orient logically."""
    # 1. Sanctuary Hub orientation checks
    with open("maps/sanctuary.json", "r", encoding="utf-8") as handle:
        sanc = json.load(handle)
    sanc_entities = sanc.get("entities", {})
    sanc_benches = {
        (x, y): constants.normalize_bench_facing((sanc_entities.get(f"{x},{y}") or {}).get("facing"))
        for y, row in enumerate(sanc["grid"])
        for x, ch in enumerate(row)
        if ch == SYMBOL_BENCH
    }
    # All 4 cardinal directions are present in Sanctuary
    assert set(sanc_benches.values()) == {"north", "south", "east", "west"}
    # Lakeside benches face the Sanctuary pond (x=6..19, y=19..29): south->north, east->west, west->east
    assert sanc_benches[(15, 32)] == "north"
    assert sanc_benches[(23, 21)] == "west"
    assert sanc_benches[(4, 23)] == "east"
    # Scriptorium interior reading benches near south wall (y=19) face north into the hall
    assert sanc_benches[(31, 19)] == "north"
    assert sanc_benches[(45, 19)] == "north"
    # South courtyard garden bench outside Scriptorium south facade faces south
    assert sanc_benches[(43, 24)] == "south"

    # 2. Colophon & all runtime biome segments: every bench has its backing wall behind it and open floor in front
    back_offsets = {"south": (0, -1), "north": (0, 1), "east": (-1, 0), "west": (1, 0)}
    front_offsets = {"south": (0, 1), "north": (0, -1), "east": (1, 0), "west": (-1, 0)}
    paths = ["maps/the_colophon.json"] + sorted(glob.glob("maps/segments/**/*.json", recursive=True))
    orientations_seen = set()
    for path in paths:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        grid = data["grid"]
        ents = data.get("entities", {})
        h_g = len(grid)
        w_g = len(grid[0]) if h_g else 0
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if ch != SYMBOL_BENCH:
                    continue
                facing = constants.normalize_bench_facing((ents.get(f"{x},{y}") or {}).get("facing"))
                orientations_seen.add(facing)
                bdx, bdy = back_offsets[facing]
                fdx, fdy = front_offsets[facing]
                for px, py in constants.get_bench_footprint_tiles(x, y, facing):
                    assert 0 <= py + bdy < h_g and 0 <= px + bdx < w_g
                    assert grid[py + bdy][px + bdx] == SYMBOL_WALL, (
                        f"{path}: bench@({x},{y}) facing={facing} lacks backing wall at ({px + bdx},{py + bdy})"
                    )
                    assert grid[py + fdy][px + fdx] != SYMBOL_WALL, (
                        f"{path}: bench@({x},{y}) facing={facing} faces directly into wall at ({px + fdx},{py + fdy})"
                    )
    assert orientations_seen == {"north", "south", "east", "west"}


def test_validate_wide_prop_clearances_handles_vertical_and_cross_orientation_benches():
    """validate_wide_prop_clearances catches vertical E/W bench collisions, border hits, and cross overlaps."""
    grid = [
        list("############"),
        list("#..S.......#"),  # (3,1) east vertical -> valid: occupies (3,1),(3,2)
        list("#..S.......#"),  # (3,2) north horiz -> invalid: anchor overlaps (3,1)'s bottom cell (makes (3,1) invalid)
        list("#......S...#"),  # (7,3) west vertical -> valid: occupies (7,3),(7,4)
        list("#......#...#"),  # (7,4) is wall -> makes (7,3) invalid!
        list("#..S.......#"),  # (3,5) east vertical -> valid: occupies (3,5),(3,6)
        list("#.S........#"),  # (2,6) south horiz -> overlaps (3,6) claimed by (3,5) -> must clear!
        list("#.......S..#"),  # (8,7) west vertical at y=h-2 -> hits bottom wall -> must clear!
        list("############"),
    ]
    entities = {
        "3,1": {"facing": "east"},
        "3,2": {"facing": "north"},
        "7,3": {"facing": "west"},
        "3,5": {"facing": "east"},
        "2,6": {"facing": "south"},
        "8,7": {"facing": "west"},
    }
    cleared = validate_wide_prop_clearances(grid, entities=entities)
    # (3,1) cleared because (3,2) wasn't floor; (3,2) stays valid; (7,3) cleared (wall below);
    # (3,5) stays valid; (2,6) cleared (overlaps (3,6)); (8,7) cleared (border below)
    assert cleared == 4
    assert grid[2][3] == SYMBOL_BENCH
    assert grid[5][3] == SYMBOL_BENCH
    assert grid[1][3] == SYMBOL_FLOOR
    assert grid[3][7] == SYMBOL_FLOOR
    assert grid[6][2] == SYMBOL_FLOOR
    assert grid[7][8] == SYMBOL_FLOOR
    assert "8,7" not in entities
    assert "2,6" not in entities


def test_map_editor_palette_parity_and_directional_bench_painting():
    """Verify MapEditor MASTER_TOOL_REGISTRY has all 4 directional bench brushes and paint_tile writes entities."""
    _ensure_pygame()
    bench_tools = {t.get("facing"): t for t in MASTER_TOOL_REGISTRY if t.get("char") == "S"}
    assert set(bench_tools.keys()) == {"south", "north", "east", "west"}
    assert "80x40" in bench_tools["south"]["size"] and "2x1" in bench_tools["south"]["size"]
    assert "80x40" in bench_tools["north"]["size"] and "2x1" in bench_tools["north"]["size"]
    assert "40x80" in bench_tools["east"]["size"] and "1x2" in bench_tools["east"]["size"]
    assert "40x80" in bench_tools["west"]["size"] and "1x2" in bench_tools["west"]["size"]

    editor = MapEditor(width=10, height=10)
    editor.hotbar[7] = "tile_bench_west"
    editor.select_hotbar_slot(7)
    assert editor.current_brush_char == "S"
    assert editor.current_brush_facing == "west"

    editor.paint_tile(4, 3)
    assert editor.grid[3][4] == "S"
    assert editor.entities["4,3"] == {"facing": "west"}

    # Painting floor over it clears the stale facing-only entity metadata
    editor.select_hotbar_slot(1)  # tile_floor
    editor.paint_tile(4, 3)
    assert editor.grid[3][4] == "."
    assert "4,3" not in editor.entities
