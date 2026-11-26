# copyright 2026 Dustin Massop, License: GPLv2
"""Regression tests ensuring 80x40 Benches ('S') and Bookcases ('h') never clip tiles or Bookmarks/Respites."""
import glob
import json
import os

import constants
from engine.world import LevelLoader
from generate_maps import (
    RESPITE_WIDE_PROP_CLEARANCE,
    SYMBOL_BENCH,
    SYMBOL_BOOKCASE,
    SYMBOL_FLOOR,
    SYMBOL_RESPITE,
    WIDE_SOLID_PROP_SYMBOLS,
    generate_biome_segment,
    generate_colophon_sanctum,
    generate_sanctuary,
    validate_wide_prop_clearances,
)


def _assert_grid_wide_props_clean(grid, label, entities=None):
    """Assert every multi-tile prop ('S' N/S 2x1 or E/W 1x2, 'h' 2x1) has clean open footprint and clears 'R'."""
    respites = [
        (rx, ry)
        for ry, row in enumerate(grid)
        for rx, ch in enumerate(row)
        if ch == SYMBOL_RESPITE
    ]
    h_grid = len(grid)
    claimed = set()
    for y, row in enumerate(grid):
        row_w = len(row)
        for x, ch in enumerate(row):
            if ch not in WIDE_SOLID_PROP_SYMBOLS:
                continue
            if ch == SYMBOL_BENCH:
                meta = (entities or {}).get(f"{x},{y}")
                b_facing = constants.normalize_bench_facing(meta.get("facing") if isinstance(meta, dict) else None)
                cells = constants.get_bench_footprint_tiles(x, y, b_facing)
            else:
                cells = ((x, y), (x + 1, y))
            for px, py in cells:
                assert 0 < px < row_w - 1 and 0 < py < h_grid - 1, (
                    f"{label}: {ch}@({x},{y}) cell ({px},{py}) touches or exceeds border ({row_w}x{h_grid})"
                )
                assert (px, py) not in claimed, f"{label}: {ch}@({x},{y}) overlaps another wide prop at ({px},{py})"
            for px, py in cells[1:]:
                assert grid[py][px] == SYMBOL_FLOOR, (
                    f"{label}: {ch}@({x},{y}) secondary tile ({px},{py}) is {grid[py][px]!r}, expected '.'"
                )
            for rx, ry in respites:
                for px, py in cells:
                    assert max(abs(px - rx), abs(py - ry)) > RESPITE_WIDE_PROP_CLEARANCE, (
                        f"{label}: {ch}@({x},{y}) clips or crowds Bookmark/Respite 'R'@({rx},{ry})"
                    )
            claimed.update(cells)


def _rects_overlap(rect_a, rect_b):
    """Return True if two (x, y, w, h) AABB rectangles overlap."""
    ax, ay, aw, ah = rect_a
    bx, by, bw, bh = rect_b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def _assert_loaded_map_wide_props_non_overlapping(path):
    """Assert instantiated directional Bench and Heavy Bookcase AABBs never overlap walls or other interactables."""
    grid, interactables, *_rest = LevelLoader.load_json_map(path)
    ts = constants.TILE_SIZE
    for w_obj in interactables:
        if getattr(w_obj, "name", "") not in ("Bench", "Heavy Bookcase"):
            continue
        wx, wy, ww, wh = w_obj.rect
        if w_obj.name == "Bench":
            exp_w, exp_h = constants.get_bench_dimensions(getattr(w_obj, "facing", "south"))
            assert (ww, wh) == (float(exp_w), float(exp_h)), f"{path}: unexpected bench size {(ww, wh)}"
        else:
            assert (ww, wh) == (float(ts * 2), float(ts)), f"{path}: unexpected wide prop size {(ww, wh)}"
        x0, y0 = int(wx // ts), int(wy // ts)
        for ty in range(y0, int((wy + wh - 1) // ts) + 1):
            for tx in range(x0, int((wx + ww - 1) // ts) + 1):
                assert grid[ty][tx] == constants.TILE_EMPTY, (
                    f"{path}: {w_obj.name}@({x0},{y0}) overlaps non-empty tile {grid[ty][tx]} at ({tx},{ty})"
                )
        for other in interactables:
            if other is not w_obj:
                assert not _rects_overlap(w_obj.rect, other.rect), (
                    f"{path}: {w_obj.name}@({x0},{y0}) overlaps {other.name}"
                )


def test_static_maps_and_segments_have_zero_bench_or_bookcase_clipping():
    """Every static map and generated biome segment must be free of Bench/Bookcase overlaps."""
    static_paths = sorted(p for p in glob.glob("maps/*.json") if not p.endswith("world_map1.json"))
    segment_paths = sorted(glob.glob("maps/segments/**/*.json", recursive=True))
    assert static_paths, "Expected static maps in maps/"
    assert segment_paths, "Expected biome segments in maps/segments/"

    for path in static_paths + segment_paths:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        _assert_grid_wide_props_clean(data["grid"], path, entities=data.get("entities"))

    aabb_paths = [
        "maps/the_colophon.json",
        "maps/sanctuary.json",
        "maps/final_boss.json",
        "maps/forest.json",
    ] + sorted(glob.glob("maps/segments/tech_tower/*.json")) + sorted(
        glob.glob("maps/segments/sunlit_aqueducts/*.json")
    )
    for path in aabb_paths:
        _assert_loaded_map_wide_props_non_overlapping(path)


def test_validate_wide_prop_clearances_removes_clipping_benches_and_respite_crowding():
    """validate_wide_prop_clearances removes invalid 80x40 benches/bookcases while preserving valid ones."""
    raw = [
        "##############",
        "#..S..#...Sh.#",  # valid S@(3,1); clipping S@(10,1) into h@(11,1)
        "#.....#......#",
        "#....R.......#",  # Respite at (5,3)
        "#...S........#",  # S@(4,4) adjacent to R@(5,3) -> must clear
        "#.....SR.....#",  # S@(6,5) right tile clips R@(7,5) -> must clear
        "#...........S#",  # S@(12,6) right tile hits border '#' -> must clear
        "#..S#........#",  # S@(3,7) right tile hits interior '#' -> must clear
        "#.....h......#",  # valid h@(6,8)
        "##############",
    ]
    grid = [list(row) for row in raw]
    cleared = validate_wide_prop_clearances(grid)

    assert cleared == 5
    assert grid[1][3] == SYMBOL_BENCH
    assert grid[8][6] == SYMBOL_BOOKCASE
    assert grid[1][11] == SYMBOL_BOOKCASE
    assert grid[1][10] == SYMBOL_FLOOR
    assert grid[4][4] == SYMBOL_FLOOR
    assert grid[5][6] == SYMBOL_FLOOR
    assert grid[6][12] == SYMBOL_FLOOR
    assert grid[7][3] == SYMBOL_FLOOR
    assert grid[3][5] == SYMBOL_RESPITE
    assert grid[5][7] == SYMBOL_RESPITE
    _assert_grid_wide_props_clean(grid, "synthetic_clearance_test")


def test_generated_sanctuary_colophon_and_segments_preserve_bench_clearances():
    """Freshly generated Sanctuary, Colophon, and architectural segments never clip 80x40 benches."""
    for seed in (101, 105, 108, 124):
        sanctuary = generate_sanctuary(seed=seed)
        _assert_grid_wide_props_clean(
            sanctuary.grid, f"generate_sanctuary(seed={seed})", entities=sanctuary.entities
        )
        # Courtyard bench at (15, 32) faces north toward the lake and retains open right-half floor at (16, 32)
        assert sanctuary.grid[32][15] == SYMBOL_BENCH
        assert sanctuary.grid[32][16] == SYMBOL_FLOOR
        assert sanctuary.entities["15,32"]["facing"] == "north"

    for seed in (404, 405, 410, 420):
        colophon = generate_colophon_sanctum(seed=seed)
        _assert_grid_wide_props_clean(
            colophon.grid, f"generate_colophon_sanctum(seed={seed})", entities=colophon.entities
        )

    for biome in ("tech_tower", "ruins", "sunlit_aqueducts"):
        for seed in (11, 22, 33):
            seg = generate_biome_segment(biome=biome, width=40, height=40, variant_index=1, seed=seed)
            _assert_grid_wide_props_clean(seg.grid, f"segment({biome}, seed={seed})", entities=seg.entities)


def test_perimeter_sealing_clears_bench_at_right_border(tmp_path):
    """LevelLoader.load_json_map clears 'S' at x=width-2 when sealing the outer perimeter wall."""
    map_data = {
        "map_id": "seal_bench_test",
        "dimensions": {"width": 8, "height": 5},
        "grid": [
            "........",
            "......S.",
            "..S.....",
            "......h.",
            "........",
        ],
        "entities": {},
        "module_sockets": [],
        "seal_outer_perimeter": True,
    }
    map_path = os.path.join(tmp_path, "seal_bench_test.json")
    with open(map_path, "w", encoding="utf-8") as handle:
        json.dump(map_data, handle)

    grid, interactables, *_rest = LevelLoader.load_json_map(map_path)
    benches = [obj for obj in interactables if getattr(obj, "name", "") == "Bench"]
    bookcases = [obj for obj in interactables if getattr(obj, "name", "") == "Heavy Bookcase"]

    assert len(benches) == 1
    assert (int(benches[0].x // constants.TILE_SIZE), int(benches[0].y // constants.TILE_SIZE)) == (2, 2)
    assert len(bookcases) == 0
    assert grid[1][7] == constants.TILE_WALL
    assert grid[3][7] == constants.TILE_WALL
