"""Unit tests for Section 13: Map Generation & Corridor Pathing Fixes.

Verifies hallway clearance guards for Heavy Bookcases ('h', 2x1) and Benches ('S'),
post-dressing solid-prop walkable connectivity repair, and unobstructed doorway-to-doorway
connectivity across all generated and on-disk tech_tower (and all 7 biome) segments.
"""

from collections import deque
import json

from constants import BIOME_SEGMENT_POOLS
from generate_maps import (
    SOLID_PROP_SYMBOLS,
    SYMBOL_BOOKCASE,
    SYMBOL_FLOOR,
    SYMBOL_WALL,
    SYMBOL_WALL_BORDER,
    _can_place_architectural_prop,
    _get_solid_prop_footprint,
    find_spawn_point,
    generate_architectural_biome,
    generate_biome_segment,
    validate_prop_walkable_connectivity,
)


def _solid_prop_components(grid):
    """Return connected walkable components treating walls and solid props ('h' incl. right half) as impassable."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    impassable, _ = _get_solid_prop_footprint(grid)
    walkable = {(x, y) for y in range(h) for x in range(w) if (x, y) not in impassable}
    visited = set()
    components = []
    for pt in walkable:
        if pt in visited:
            continue
        comp = set()
        queue = deque([pt])
        visited.add(pt)
        while queue:
            cx, cy = queue.popleft()
            comp.add((cx, cy))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in walkable and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        components.append(comp)
    components.sort(key=len, reverse=True)
    return components, impassable


def test_corridor_clearance_guard_blocks_hallways_and_allows_room_walls():
    """_can_place_architectural_prop rejects narrow 2-tile hallways while allowing wide room perimeter walls."""
    # Build a small map with a 6x6 room on the left connected by a 2-tile horizontal corridor
    # and a 2-tile vertical corridor.
    grid = [list("#" * 16) for _ in range(14)]
    # 6x6 room at x=1..6, y=1..6
    for y in range(1, 7):
        for x in range(1, 7):
            grid[y][x] = SYMBOL_FLOOR
    # 2-tile-high horizontal hallway at y=3..4, x=7..14
    for y in (3, 4):
        for x in range(7, 15):
            grid[y][x] = SYMBOL_FLOOR
    # 2-tile-wide vertical hallway at x=3..4, y=7..12
    for y in range(7, 13):
        for x in (3, 4):
            grid[y][x] = SYMBOL_FLOOR

    occupied, _ = _get_solid_prop_footprint(grid)

    # Inside wide room against North wall (y=1, x=2..3): both Bench and 2x1 Bookcase allowed
    assert _can_place_architectural_prop(grid, [(2, 1)], occupied) is True
    assert _can_place_architectural_prop(grid, [(2, 1), (3, 1)], occupied) is True

    # Inside 2-tile horizontal corridor (y=3, x=9): Bench and Bookcase must be rejected
    assert _can_place_architectural_prop(grid, [(9, 3)], occupied) is False
    assert _can_place_architectural_prop(grid, [(9, 3), (10, 3)], occupied) is False

    # Inside 2-tile vertical corridor (x=3, y=9): Bench and 2x1 Bookcase plugging both lanes must be rejected
    assert _can_place_architectural_prop(grid, [(3, 9)], occupied) is False
    assert _can_place_architectural_prop(grid, [(3, 9), (4, 9)], occupied) is False


def test_post_dressing_connectivity_clears_blocking_bookcase_and_bench():
    """validate_prop_walkable_connectivity strips blocking 'h' (2x1) and 'S' props that sever hallways."""
    raw = [
        "############",
        "#....##....#",
        "#....##....#",
        "#....S.....#",
        "#....##....#",
        "###..#######",
        "###h.#######",
        "###..#######",
        "#....#######",
        "#....#######",
        "############",
    ]
    grid = [list(row) for row in raw]

    # Before repair: 3 disconnected regions (NW room, NE room blocked by 'S', SW room blocked by 'h'+right half)
    comps_before, _ = _solid_prop_components(grid)
    assert len(comps_before) == 3

    cleared = validate_prop_walkable_connectivity(grid, mandatory_coords=[(2, 2), (9, 2), (2, 8)])
    assert cleared == 2
    assert grid[3][5] == SYMBOL_FLOOR
    assert grid[6][3] == SYMBOL_FLOOR

    comps_after, _ = _solid_prop_components(grid)
    assert len(comps_after) == 1
    for pt in ((2, 2), (9, 2), (2, 8)):
        assert pt in comps_after[0]


def test_generated_tech_tower_maps_and_segments_have_unobstructed_paths():
    """Freshly generated tech_tower maps and segments remain 100% walkable with solid props treated as impassable."""
    for seed in (101, 202, 303, 404):
        gmap = generate_architectural_biome(width=40, height=40, biome="tech_tower", seed=seed)
        comps, _ = _solid_prop_components(gmap.grid)
        assert len(comps) == 1, f"Disconnected walkable pockets in tech_tower seed={seed}: {len(comps)} components"

        p_pos = find_spawn_point(gmap.grid, "P")
        w_pos = find_spawn_point(gmap.grid, "W")
        r_pos = find_spawn_point(gmap.grid, "R")
        assert p_pos in comps[0] and w_pos in comps[0] and r_pos in comps[0]

        for y, row in enumerate(gmap.grid):
            for x, ch in enumerate(row):
                if ch == SYMBOL_BOOKCASE:
                    assert x + 1 < len(row) - 1
                    assert gmap.grid[y][x + 1] == SYMBOL_FLOOR

    for dim in (40, 120):
        seg = generate_biome_segment(biome="tech_tower", width=dim, height=dim, variant_index=1, seed=707)
        comps, _ = _solid_prop_components(seg.grid)
        assert len(comps) == 1, f"Disconnected walkable pockets in tech_tower {dim}x{dim} segment"
        mid = dim // 2
        for conn in ((mid, 0), (mid, dim - 1), (0, mid), (dim - 1, mid)):
            assert conn in comps[0], f"Doorway {conn} blocked by solid prop in tech_tower {dim}x{dim} segment"


def test_on_disk_tech_tower_and_all_biome_segments_unobstructed():
    """All on-disk tech_tower (and all 7 biome) segment JSONs have unobstructed doorway paths and intact quotas."""
    assert "tech_tower" in BIOME_SEGMENT_POOLS
    assert set(SOLID_PROP_SYMBOLS) == {"h", "S", "B", "T", "d", "l", "V"}

    for biome, pools in BIOME_SEGMENT_POOLS.items():
        room_minibosses = []
        corridor_minibosses = []
        for kind in ("rooms", "corridors"):
            for path in pools[kind]:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                grid = [list(row) for row in data["grid"]]
                h, w = len(grid), len(grid[0])
                comps, impassable = _solid_prop_components(grid)
                assert len(comps) == 1, f"Disconnected walkable pockets in {path}: {len(comps)} components"

                mid_x, mid_y = w // 2, h // 2
                for conn in ((mid_x, 0), (mid_x, h - 1), (0, mid_y), (w - 1, mid_y)):
                    assert conn not in impassable, f"Connector {conn} obstructed in {path}"
                    assert conn in comps[0], f"Connector {conn} unreachable in {path}"

                # Bookcases must never overlap walls or props on their right half
                for y in range(h):
                    for x in range(w):
                        if grid[y][x] == SYMBOL_BOOKCASE:
                            assert x + 1 < w
                            assert grid[y][x + 1] not in (SYMBOL_WALL, SYMBOL_WALL_BORDER)
                            assert grid[y][x + 1] not in SOLID_PROP_SYMBOLS

                mb_count = sum(row.count("E") for row in data["grid"])
                if kind == "rooms":
                    room_minibosses.append(mb_count)
                else:
                    corridor_minibosses.append(mb_count)

        assert room_minibosses == [1, 0, 1, 0], f"Miniboss room budget regressed for {biome}: {room_minibosses}"
        assert corridor_minibosses == [0, 0, 0, 0], (
            f"Miniboss corridor budget regressed for {biome}: {corridor_minibosses}"
        )
