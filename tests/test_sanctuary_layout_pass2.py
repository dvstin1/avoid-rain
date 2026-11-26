# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Pass 2: Expanded Sanctuary Layout & Courtyard Composition.

Verifies the expanded 56x40 maps/sanctuary.json layout, preserved NPC/spawn invariants,
sanctuary_zones metadata loading, non-duplicated prop_type entity spawning, interactive
flavor dialogue on the locked shed door and mossy gravestone, and error-free rendering
across all courtyard and Scriptorium interior zones.
"""
# pylint: disable=no-member,protected-access

from collections import Counter, deque
import json

import pygame

import constants
from engine.game_state import GameState
from engine.maps import create_world
from engine.stats import StatisticsTracker
from engine.world import (
    Binder,
    Chronicler,
    FlavorProp,
    LevelLoader,
    LoreFragment,
    PatrolPoint,
    WarpPortal,
    Wellspring,
)
from generate_maps import (
    SYMBOL_BOOKCASE,
    SYMBOL_WALL,
    _get_solid_prop_footprint,
    find_spawn_point,
    generate_sanctuary,
)
from rendering.renderer import Renderer


def test_expanded_sanctuary_layout_and_invariants():
    """Verify expanded 56x40 maps/sanctuary.json preserves all core NPCs, spawn clearance, and walkability."""
    with open("maps/sanctuary.json", "r", encoding="utf-8") as handle:
        data = json.load(handle)

    assert data["dimensions"] == {"width": 56, "height": 40}
    grid = [list(row) for row in data["grid"]]
    assert len(grid) == 40 and all(len(row) == 56 for row in grid)
    assert grid[0][0] == SYMBOL_WALL

    # Solid outer perimeter border
    for x in range(56):
        assert grid[0][x] == SYMBOL_WALL and grid[39][x] == SYMBOL_WALL
    for y in range(40):
        assert grid[y][0] == SYMBOL_WALL and grid[y][55] == SYMBOL_WALL

    # Player start has unobstructed open floor immediately west (test_chronicler invariant)
    spawn = find_spawn_point(grid, "P")
    assert spawn is not None
    impassable, _ = _get_solid_prop_footprint(grid)
    assert spawn not in impassable
    assert (spawn[0] - 1, spawn[1]) not in impassable

    # Bookcases reserve open right half
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == SYMBOL_BOOKCASE:
                assert x + 1 < 55 and grid[y][x + 1] == "."

    # Single-component solid-prop walkable connectivity across entire Sanctuary
    walkable = {(x, y) for y in range(40) for x in range(56) if (x, y) not in impassable}
    visited = {spawn}
    queue = deque([spawn])
    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in walkable and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))
    assert visited == walkable, f"Disconnected walkable tiles in Sanctuary: {len(walkable - visited)}"

    # Core entities & zero enemies via create_world("sanctuary")
    world = create_world("sanctuary")
    assert world.enemies == []
    assert len([o for o in world.interactables if isinstance(o, Binder)]) == 1
    assert len([o for o in world.interactables if isinstance(o, Chronicler)]) == 1
    assert any(isinstance(o, PatrolPoint) and o.route_id == "chron_research" for o in world.interactables)
    warps = [o for o in world.interactables if isinstance(o, WarpPortal) and o.target_name == "macro_world"]
    assert len(warps) == 1 and warps[0].name == "The Chronicle"
    assert len([o for o in world.interactables if isinstance(o, Wellspring)]) >= 1
    lores = [o for o in world.interactables if isinstance(o, LoreFragment)]
    assert len(lores) >= 1
    assert lores[0].fragment_id == "chronicler_nature"
    assert lores[0].name == "Faded Note"
    candelabras = [o for o in world.interactables if o.name == "Candelabra"]
    assert 4 <= len(candelabras) <= 8

    # Direct helper smoke test
    fresh = generate_sanctuary(seed=108)
    assert (fresh.width, fresh.height) == (56, 40)


def test_sanctuary_zones_metadata_and_load_json_map_tuple_compat():
    """Verify LevelLoader.load_json_map() stays a 7-tuple and create_world populates sanctuary_zones."""
    loaded_tuple = LevelLoader.load_json_map("maps/sanctuary.json")
    assert len(loaded_tuple) == 7

    world = create_world("sanctuary")
    zones = world.sanctuary_zones
    for key in ("wood_floor", "dirt_path", "pond_water", "roof_zones"):
        assert key in zones and len(zones[key]) > 0

    roof_names = {r["name"] for r in zones["roof_zones"]}
    assert {"scriptorium_roof", "shed_roof"}.issubset(roof_names)

    # Verify zone lookups across oak Scriptorium, dirt garden paths, pond water, and flagstone courtyard
    assert world.get_sanctuary_zone_type(38, 14) == "wood_floor"
    assert world.get_sanctuary_zone_type(21, 24) == "dirt_path"
    assert world.get_sanctuary_zone_type(12, 24) == "pond_water"
    assert world.get_sanctuary_zone_type(1, 1) is None


def test_prop_type_no_duplicates_and_flavor_prop_interactions():
    """Verify prop_type overrides spawn strictly one object per tile and flavor props show dialogue only."""
    world = create_world("sanctuary")

    # No two interactables share the exact same tile origin (no duplicate spawning)
    pos_counts = Counter((int(o.x), int(o.y)) for o in world.interactables)
    duplicates = {pos: cnt for pos, cnt in pos_counts.items() if cnt > 1}
    assert not duplicates, f"Duplicate overlapping interactables spawned: {duplicates}"

    # Verify all 5 Sanctuary prop_type categories spawned cleanly
    ptypes = {getattr(o, "prop_type", None) for o in world.interactables}
    for req in ("sanctuary_tree", "garden_flora", "pond_lily_reeds", "locked_shed_door", "mossy_gravestone"):
        assert req in ptypes, f"Missing Sanctuary prop_type '{req}'"

    # Pond lily reeds are decorative non-solid and must NOT trigger Inkwell Puddle slowdown
    lily = next(o for o in world.interactables if getattr(o, "prop_type", None) == "pond_lily_reeds")
    assert lily.is_solid is False
    assert world.has_puddle_collision(lily.rect) is False

    # Test interactive flavor dialogue with zero mechanical reward on locked shed door & mossy gravestone
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        state.player.hp = 60.0
        state.player.flask_charges = 1
        state.stats.data["lifetime_stats"]["pages_collected"] = 0
        state.stats.data["margin_scraps"] = 0

        for ptype in ("locked_shed_door", "mossy_gravestone"):
            prop = next(o for o in state.world.interactables if getattr(o, "prop_type", None) == ptype)
            assert isinstance(prop, FlavorProp)
            assert prop.is_solid is True and prop.is_interactive is True

            state.active_dialogue = None
            prop.execute_interaction(state)
            assert isinstance(state.active_dialogue, dict)
            assert state.active_dialogue["speaker"] == prop.name
            assert len(state.active_dialogue["text"]) > 15
            # Zero mechanical reward
            assert state.player.hp == 60.0
            assert state.player.flask_charges == 1
            assert state.stats.data["lifetime_stats"]["pages_collected"] == 0
            assert state.stats.data["margin_scraps"] == 0
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sanctuary_courtyard_and_interior_zone_rendering():
    """Verify Renderer renders Scriptorium oak hall, dirt paths, pond, shed, gravestone, and tree canopies."""
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        # Render across Northwest (shed + gravestone), West (pond + garden), and East (oak Scriptorium)
        focus_tiles = ((8, 8), (12, 24), (38, 14))
        for tx, ty in focus_tiles:
            state.camera.instant_center((tx * constants.TILE_SIZE, ty * constants.TILE_SIZE))
            renderer.render(state)

        # Also exercise procedural fallbacks when Pass 1 Sanctuary sprites are absent
        for key in ("SanctuaryTreeCanopy", "PondLilyReeds", "GardenFlora", "LockedShedDoor", "MossyGravestone"):
            renderer.prop_cache.pop(key, None)
        renderer.sanctuary_wood_floor_variants = []
        renderer.sanctuary_dirt_path_variants = []
        renderer._chunk_cache.clear()
        for tx, ty in focus_tiles:
            state.camera.instant_center((tx * constants.TILE_SIZE, ty * constants.TILE_SIZE))
            renderer.render(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)
