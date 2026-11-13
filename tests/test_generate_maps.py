"""
Unit tests for standalone procedural offline map generator (generate_maps.py).
Verifies algorithmic generation across biomes, connectivity validation,
smart prop scattering, serialization, and preview generation.
"""
# pylint: disable=redefined-outer-name,no-member,too-many-locals

import json
import os
import tempfile
import pytest

from engine.world import LevelLoader
from generate_maps import (
    generate_organic_biome,
    generate_architectural_biome,
    generate_procedural_map,
    render_map_preview,
    find_spawn_point,
    apply_verticality_post_pass,
    GeneratedMap,
    MAP_LEGEND,
    ORGANIC_BIOMES,
    ARCHITECTURAL_BIOMES,
    ELEVATION_PIT,
    ELEVATION_LOWER,
    ELEVATION_TERRACE,
)


@pytest.fixture
def temp_dir():
    """Provides a temporary directory for map and preview generation."""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


def test_symbol_registry_coverage():
    """Verifies that all canonical map symbols are defined in the generator legend."""
    expected_symbols = {
        '#', 'X', '.', 'g', 'G', 'v', 'T', 'P', 'W', 'R', 'L', 'F',
        'a', 'S', 's', 'A', 'b', 'Y', 'E', 'Z', 'M', '2', '3',
        'B', 'h', 'K', 'd', 'l', 'C', 'f', '!'
    }
    legend_keys = set(MAP_LEGEND.keys())
    assert expected_symbols.issubset(legend_keys), f"Missing symbols: {expected_symbols - legend_keys}"


def test_organic_biome_generation():
    """Verifies organic biome generation creates properly bounded, feature-rich maps."""
    gen_map = generate_organic_biome(width=40, height=40, biome="swamp_mire", seed=42)

    assert gen_map.width == 40
    assert gen_map.height == 40
    assert len(gen_map.grid) == 40
    assert all(len(row) == 40 for row in gen_map.grid)

    # Perimeter walls check
    for x in range(40):
        assert gen_map.grid[0][x] == "#"
        assert gen_map.grid[39][x] == "#"
    for y in range(40):
        assert gen_map.grid[y][0] == "#"
        assert gen_map.grid[y][39] == "#"

    all_symbols = {char for row in gen_map.grid for char in row}
    # Player start and warp exit must exist
    assert "P" in all_symbols, "Player start 'P' must exist"
    assert "W" in all_symbols, "Warp exit 'W' must exist"
    # Natural organic features
    assert any(sym in all_symbols for sym in ("g", "v", "G")), "Organic terrain features must exist"


def test_architectural_biome_generation():
    """Verifies architectural biome generation creates chambers, corridors, dais, and tactical props."""
    gen_map = generate_architectural_biome(width=40, height=40, biome="ruins", seed=101)

    assert gen_map.width == 40
    assert gen_map.height == 40
    assert len(gen_map.grid) == 40

    all_symbols = {char for row in gen_map.grid for char in row}
    assert "P" in all_symbols, "Player start 'P' must exist"
    assert "W" in all_symbols, "Warp exit 'W' must exist"
    # Architectural elements: central dais/altar 'a', lanterns 'L'/'F', or books 'B'
    assert any(sym in all_symbols for sym in ("a", "R", "L", "F", "B", "7")), "Architectural props must exist"


def test_connectivity_and_flood_fill():
    """Verifies that all walkable tiles in generated maps are reachable from player start."""
    for biome in ("swamp", "ruins", "crypt", "pastoral_valley"):
        gen_map = generate_procedural_map(biome=biome, width=35, height=35, seed=777)
        player_pos = find_spawn_point(gen_map.grid, "P")
        assert player_pos is not None, f"Player start not found for biome {biome}"

        warp_pos = find_spawn_point(gen_map.grid, "W")
        assert warp_pos is not None, f"Warp exit not found for biome {biome}"

        # Collect all non-wall tiles
        walkable_tiles = {
            (x, y)
            for y in range(gen_map.height)
            for x in range(gen_map.width)
            if gen_map.grid[y][x] != "#"
        }

        # BFS from player start
        visited = set()
        queue = [player_pos]
        visited.add(player_pos)

        while queue:
            cx, cy = queue.pop(0)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) in walkable_tiles and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

        # Check connectivity: 100% of walkable tiles must be connected
        assert visited == walkable_tiles, (
            f"Unreachable tiles detected in {biome}: {len(walkable_tiles - visited)} disconnected tiles"
        )
        assert warp_pos in visited, f"Warp point {warp_pos} must be reachable from player {player_pos}"


def test_smart_prop_clustering():
    """Verifies that smart prop placement preferentially clusters near walls."""
    gen_map = generate_architectural_biome(width=40, height=40, biome="ruins", seed=888)

    prop_symbols = {'K', 'B', 'h', 'S', 'd', 'l'}
    prop_coords = [
        (x, y)
        for y in range(gen_map.height)
        for x in range(gen_map.width)
        if gen_map.grid[y][x] in prop_symbols
    ]

    if prop_coords:
        # Check that the vast majority of props have at least one wall in their 3x3 neighborhood
        adjacent_to_wall_count = 0
        for px, py in prop_coords:
            has_wall_neighbor = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = px + dx, py + dy
                    if 0 <= nx < gen_map.width and 0 <= ny < gen_map.height:
                        if gen_map.grid[ny][nx] == '#':
                            has_wall_neighbor = True
                            break
                if has_wall_neighbor:
                    break
            if has_wall_neighbor:
                adjacent_to_wall_count += 1

        ratio = adjacent_to_wall_count / len(prop_coords)
        assert ratio >= 0.70, f"Expected >= 70% of props near walls, got {ratio:.2%}"


def test_map_serialization_and_level_loader(temp_dir):
    """Verifies that generated maps serialize properly to JSON and TXT and load into LevelLoader."""
    gen_map = generate_organic_biome(width=40, height=40, biome="swamp_mire", seed=321)

    json_path = os.path.join(temp_dir, "test_map.json")
    txt_path = os.path.join(temp_dir, "test_map.txt")

    gen_map.save(json_path, format_type="json")
    gen_map.save(txt_path, format_type="txt")

    assert os.path.exists(json_path)
    assert os.path.exists(txt_path)

    # Validate JSON structure
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["map_id"] == "swamp_mire_321"
    assert data["dimensions"] == {"width": 40, "height": 40}
    assert len(data["grid"]) == 40
    assert len(data["grid"][0]) == 40

    # Validate LevelLoader parses the generated JSON map successfully
    grid, interactables, _, player_start, enemies, _, _ = LevelLoader.load_json_map(json_path)
    assert len(grid) == 40
    assert len(grid[0]) == 40
    assert player_start is not None
    assert len(player_start) == 2
    assert len(enemies) > 0
    assert len(interactables) > 0

    # Validate LevelLoader parses the generated TXT map successfully
    t_grid, t_interactables, _, t_start, t_enemies, _, _ = LevelLoader.load_json_map(txt_path)
    assert len(t_grid) == 40
    assert t_start is not None
    assert len(t_enemies) > 0
    assert len(t_interactables) > 0


def test_preview_rendering(temp_dir):
    """Verifies that headless preview rendering generates valid PNG images."""
    gen_map = generate_architectural_biome(width=30, height=30, biome="sanctuary", seed=55)
    preview_path = os.path.join(temp_dir, "preview.png")

    result_path = render_map_preview(gen_map, preview_path, scale=8)
    assert os.path.exists(result_path)
    assert os.path.getsize(result_path) > 100, "Preview PNG file should have non-trivial size"


def test_all_biomes_generation():
    """Verifies that all registered organic and architectural biomes generate without error."""
    for biome in ORGANIC_BIOMES:
        m = generate_procedural_map(biome=biome, width=30, height=30, seed=12)
        assert isinstance(m, GeneratedMap)
        assert m.biome == biome

    for biome in ARCHITECTURAL_BIOMES:
        m = generate_procedural_map(biome=biome, width=30, height=30, seed=34)
        assert isinstance(m, GeneratedMap)
        assert m.biome == biome


def test_cli_integration(temp_dir):
    """Verifies CLI execution with flags produces expected files."""
    out_map = os.path.join(temp_dir, "cli_map.json")
    cmd = (
        f"python3 generate_maps.py --biome ruins --seed 999 "
        f"--width 32 --height 32 --output {out_map} --preview"
    )
    exit_code = os.system(cmd)
    assert exit_code == 0
    assert os.path.exists(out_map)

    # Check that preview was generated in maps/previews/
    expected_preview = os.path.join("maps", "previews", "ruins_999_preview.png")
    assert os.path.exists(expected_preview)
    # Clean up preview created during test
    if os.path.exists(expected_preview):
        os.remove(expected_preview)


def test_elevation_tiers_and_staircases():
    """Verifies elevation tiers (Pit, Lower, Terrace) and connecting staircase placement."""
    for biome, seed in (("swamp_mire", 42), ("ruins", 101)):
        gen_map = generate_procedural_map(biome=biome, width=40, height=40, seed=seed)
        elev_values = {val for row in gen_map.elevation_grid for val in row}
        assert ELEVATION_PIT in elev_values, f"Expected Pit tier in {biome}"
        assert ELEVATION_LOWER in elev_values, f"Expected Lower tier in {biome}"
        assert ELEVATION_TERRACE in elev_values, f"Expected Terrace tier in {biome}"

        stairs = gen_map.verticality_layers.get("stairs", [])
        assert len(stairs) > 0, f"Expected connecting staircases in {biome}"
        for sx, sy in stairs:
            assert gen_map.elevation_grid[sy][sx] == ELEVATION_TERRACE
            assert any(
                gen_map.elevation_grid[sy + dy][sx + dx] == ELEVATION_LOWER
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
            )


def test_auto_shading_and_wall_facing_post_pass():
    """Verifies auto-facing walls, floor drop shadows, cliff edges, and pit rims."""
    grid = [
        list("#####"),
        list("#...#"),
        list("#.B.#"),
        list("#...#"),
        list("#####"),
    ]
    elev = [
        [ELEVATION_PIT, ELEVATION_PIT, ELEVATION_PIT, ELEVATION_PIT, ELEVATION_PIT],
        [ELEVATION_LOWER, ELEVATION_TERRACE, ELEVATION_TERRACE, ELEVATION_TERRACE, ELEVATION_LOWER],
        [ELEVATION_LOWER, ELEVATION_LOWER, ELEVATION_LOWER, ELEVATION_LOWER, ELEVATION_LOWER],
        [ELEVATION_LOWER, ELEVATION_LOWER, ELEVATION_LOWER, ELEVATION_LOWER, ELEVATION_LOWER],
        [ELEVATION_PIT, ELEVATION_PIT, ELEVATION_PIT, ELEVATION_PIT, ELEVATION_PIT],
    ]
    layers = apply_verticality_post_pass(grid, elev, stairs_coords=[[2, 1]])

    # Row 0 walls border walkable row 1 -> front_face
    assert [1, 0] in layers["wall_faces"]["front_face"]
    assert [2, 0] in layers["wall_faces"]["front_face"]
    # Row 4 walls have nothing south -> top_cap
    assert [1, 4] in layers["wall_faces"]["top_cap"]

    # Walkable tile (2, 3) immediately south of Barrel 'B' at (2, 2) gets south shadow
    assert [2, 3] in layers["floor_shadows"]["south"]
    # Walkable tile (3, 2) immediately east of Barrel 'B' at (2, 2) gets east shadow
    assert [3, 2] in layers["floor_shadows"]["east"]
    # Walkable tile (3, 3) SE of Barrel 'B' gets inner corner shadow
    assert [3, 3] in layers["floor_shadows"]["corner"]

    # Terrace tiles (1, 1) and (3, 1) border lower floor to south without stairs -> cliff_edges
    assert [1, 1] in layers["cliff_edges"]
    assert [3, 1] in layers["cliff_edges"]
    assert [2, 1] not in layers["cliff_edges"]  # Has stair

    # Pit tiles bordering non-pit tiles get pit_rims
    assert [1, 0] in layers["pit_rims"]
    assert [2, 4] in layers["pit_rims"]


def test_verticality_serialization_and_engine_compatibility(temp_dir):
    """Verifies verticality layers serialize cleanly to JSON without breaking LevelLoader."""
    gen_map = generate_procedural_map(biome="ruins", width=36, height=36, seed=202)
    out_path = os.path.join(temp_dir, "vertical_ruins.json")
    gen_map.save(out_path, file_format="json")

    with open(out_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "elevation_grid" in data
    assert "verticality_layers" in data
    assert "wall_faces" in data["verticality_layers"]
    assert "floor_shadows" in data["verticality_layers"]
    assert "pit_rims" in data["verticality_layers"]

    grid, _, _, player_start, _, _, _ = LevelLoader.load_json_map(out_path)
    assert len(grid) == 36
    assert player_start is not None
