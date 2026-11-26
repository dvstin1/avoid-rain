# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Phase 2 Playtest Fixes:

1. Enclosed & dressed Scriptorium starting sanctum (maps/the_colophon.json) and sealed 440x440
   macro-world outer perimeter border with guaranteed walkable egress from spawn.
2. Assorted procedural 40x40 standard & anomalous weapon pickup sprites (generate_assets.py + Renderer).
"""
# pylint: disable=no-member,protected-access

from collections import deque
import json
import os

import pygame

import constants
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import LevelLoader, WeaponPickup
from engine.world_generator import WorldGenerator
from generate_assets import generate_weapon_pickup_sprite
from generate_maps import (
    SOLID_PROP_SYMBOLS,
    SYMBOL_BOOKCASE,
    SYMBOL_WALL,
    SYMBOL_WALL_BORDER,
    _get_solid_prop_footprint,
    find_spawn_point,
    generate_colophon_sanctum,
)
from rendering.renderer import Renderer


WEAPON_SPRITE_SPECS = (
    ("weapon_quill_standard.png", "WeaponQuillStandard"),
    ("weapon_quill_refined.png", "WeaponQuillRefined"),
    ("weapon_scriber_blade.png", "WeaponScriberBlade"),
    ("weapon_anomalous_bleed.png", "WeaponAnomalousBleed"),
    ("weapon_anomalous_regen.png", "WeaponAnomalousRegen"),
    ("weapon_anomalous_negation.png", "WeaponAnomalousNegation"),
    ("weapon_anomalous_stout.png", "WeaponAnomalousStout"),
    ("weapon_anomalous_default.png", "WeaponAnomalousDefault"),
)


def test_the_colophon_sanctum_enclosed_dressed_and_walkable():
    """Verify maps/the_colophon.json is enclosed, Scriptorium-dressed, and walkable to all 4 exits."""
    with open("maps/the_colophon.json", "r", encoding="utf-8") as handle:
        data = json.load(handle)

    grid = [list(row) for row in data["grid"]]
    h, w = len(grid), len(grid[0])
    assert (w, h) == (40, 40)

    # Outer edges outside the 6-tile centered cardinal exits are solid '#' walls
    mid_x, mid_y = w // 2, h // 2
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (5, 0), (0, 5)):
        assert grid[corner[1]][corner[0]] == SYMBOL_WALL

    # Scriptorium props present, zero enemies inside the starting sanctum
    all_chars = {ch for row in grid for ch in row}
    for req_prop in ("l", "d", "S", "h", "K", "B", "P"):
        assert req_prop in all_chars, f"Missing expected Scriptorium symbol '{req_prop}' in the_colophon.json"
    for enemy_sym in ("Z", "A", "f", "b", "s", "Y", "w", "E"):
        assert enemy_sym not in all_chars, f"Unexpected enemy '{enemy_sym}' in safe starting sanctum"

    # Every Heavy Bookcase 'h' has unobstructed non-wall/non-prop right half
    for y in range(h):
        for x in range(w):
            if grid[y][x] == SYMBOL_BOOKCASE:
                assert x + 1 < w
                assert grid[y][x + 1] not in (SYMBOL_WALL, SYMBOL_WALL_BORDER)
                assert grid[y][x + 1] not in SOLID_PROP_SYMBOLS

    # BFS over walkable tiles treating solid props ('h' incl. right half) as impassable
    impassable, _ = _get_solid_prop_footprint(grid)
    spawn = find_spawn_point(grid, "P")
    assert spawn == (mid_x, mid_y)
    assert spawn not in impassable

    visited = {spawn}
    queue = deque([spawn])
    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in impassable and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))

    for exit_pt in ((mid_x, 0), (mid_x, h - 1), (0, mid_y), (w - 1, mid_y)):
        assert exit_pt in visited, f"Cardinal exit {exit_pt} unreachable from spawn in the_colophon.json"

    # Smoke-test procedural helper directly
    fresh = generate_colophon_sanctum(seed=777)
    assert (fresh.width, fresh.height) == (40, 40)


def test_stitched_macro_world_seals_outer_perimeter_with_spawn_egress(tmp_path):
    """Verify stitched 440x440 macro-world seals its 1-tile outer border while leaving spawn egress open."""
    gen = WorldGenerator(world_id="perimeter_test", biome="tech_tower")
    gen.generate_layout()
    raw_dict = gen.to_dict()
    assert raw_dict["seal_outer_perimeter"] is True
    assert set(raw_dict["grid"][0]) == {"#"}
    assert set(raw_dict["grid"][-1]) == {"#"}

    out_path = str(tmp_path / "macro_perimeter.json")
    gen.export_world(out_path)
    grid, _, _, player_start, _, _, sockets = LevelLoader.load_json_map(out_path)

    gh, gw = len(grid), len(grid[0])
    assert (gw, gh) == (440, 440)

    # All 4 outer edges must be 100% solid TILE_WALL
    for x in range(gw):
        assert grid[0][x] == constants.TILE_WALL, f"Unsealed North border at x={x}"
        assert grid[gh - 1][x] == constants.TILE_WALL, f"Unsealed South border at x={x}"
    for y in range(gh):
        assert grid[y][0] == constants.TILE_WALL, f"Unsealed West border at y={y}"
        assert grid[y][gw - 1] == constants.TILE_WALL, f"Unsealed East border at y={y}"

    # Verify spawn inside the_colophon.json can walk outside its 40x40 socket bounds into the macro-world
    colophon_sock = next(s for s in sockets if s["active_plug"] == "maps/the_colophon.json")
    b = colophon_sock["bounds"]
    sx = int(player_start[0] // constants.TILE_SIZE)
    sy = int(player_start[1] // constants.TILE_SIZE)
    assert grid[sy][sx] != constants.TILE_WALL

    visited = {(sx, sy)}
    queue = deque([(sx, sy)])
    escaped_sanctum = False
    while queue and len(visited) < 2500:
        cx, cy = queue.popleft()
        if not (b["x"] <= cx < b["x"] + b["width"] and b["y"] <= cy < b["y"] + b["height"]):
            escaped_sanctum = True
            break
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < gw and 0 <= ny < gh and grid[ny][nx] != constants.TILE_WALL and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))

    assert escaped_sanctum is True, "Player could not exit the_colophon starting sanctum into the macro-world"


def test_assorted_weapon_pickup_assets_selection_and_rendering():
    """Verify all 8 weapon pickup PNGs exist, are distinct, load in Renderer, and render for all variants."""
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    fingerprints = {}
    for fname, cache_key in WEAPON_SPRITE_SPECS:
        fpath = os.path.join("assets", "graphics", fname)
        assert os.path.exists(fpath), f"Missing generated weapon sprite: {fpath}"
        assert cache_key in renderer.prop_cache, f"Renderer missing prop_cache[{cache_key!r}]"
        surf = renderer.prop_cache[cache_key]
        assert surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)
        # Ensure non-empty transparent pixel art (not a solid opaque square!)
        raw_bytes = pygame.image.tobytes(surf, "RGBA")
        alpha_vals = raw_bytes[3::4]
        assert any(a > 0 for a in alpha_vals), f"{fname} has no opaque pixels"
        assert any(a == 0 for a in alpha_vals), f"{fname} has no transparent background pixels"
        fingerprints[cache_key] = raw_bytes

    # All 8 sprites must be visually distinct
    assert len(set(fingerprints.values())) == len(WEAPON_SPRITE_SPECS)

    # Verify deterministic sprite selection across standard and anomalous WeaponPickup variants
    cases = [
        ({"name": "Standard Quill", "damage": 10}, "WeaponQuillStandard"),
        ({"name": "Refined Quill", "damage": 15}, "WeaponQuillRefined"),
        ({"name": "Scriber Blade", "damage": 14}, "WeaponScriberBlade"),
        ({"name": "Anomalous Ink-Bleed", "damage": 24, "modifiers": {"bleed": 5.0}}, "WeaponAnomalousBleed"),
        (
            {"name": "Anomalous Life-Thread", "damage": 22, "modifiers": {"slow_hp_regen": 1.0}},
            "WeaponAnomalousRegen",
        ),
        (
            {"name": "Anomalous Iron-Nib", "damage": 25, "modifiers": {"damage_negation_on_hit": 5.0}},
            "WeaponAnomalousNegation",
        ),
        (
            {"name": "Anomalous Stout-Draft", "damage": 26, "modifiers": {"max_hp_boost": 20.0}},
            "WeaponAnomalousStout",
        ),
        ({"name": "Anomalous Relic", "damage": 28, "modifiers": {"mystery": 1.0}}, "WeaponAnomalousDefault"),
    ]
    for wdata, expected_key in cases:
        assert Renderer._select_weapon_pickup_sprite_key(wdata) == expected_key

    # Smoke-test procedural generator directly & full render path (both sprite and procedural fallback)
    gen_surf = generate_weapon_pickup_sprite("weapon_anomalous_bleed", 40, 40)
    assert gen_surf.get_size() == (40, 40)

    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        px, py = state.player.x, state.player.y
        for idx, (wdata, _) in enumerate(cases):
            state.world.interactables.append(WeaponPickup((px + 40 * (idx - 3), py - 40), wdata))
        renderer.render(state)

        # Also exercise procedural fallback path when weapon assets are absent from prop_cache
        for _, cache_key in WEAPON_SPRITE_SPECS:
            renderer.prop_cache.pop(cache_key, None)
        renderer.render(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)
