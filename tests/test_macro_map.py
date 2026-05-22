import pytest
from engine.maps import create_world
from engine.world import generate_macro_lotus_world
from constants import MACRO_MAP_SIZE, TILE_WALL, TILE_EMPTY

def test_macro_map_dimensions():
    """Verify that the macro-map is initialized with correct dimensions."""
    world = create_world("macro_world")
    assert len(world.grid) == MACRO_MAP_SIZE
    assert len(world.grid[0]) == MACRO_MAP_SIZE

def test_macro_map_replicated_sectors():
    """Verify that the macro-map contains replicated sectors."""
    prototype = generate_macro_lotus_world()
    
    # Check for presence of 'A' (BatEnemy) or 'S' (Bench) in the sectors
    # Since we know where we placed the sectors, we can check those areas.
    center = MACRO_MAP_SIZE // 2
    
    # Check North Sector roughly
    found_replicated = False
    for y in range(15, 35):
        for x in range(center - 10, center + 10):
            if prototype[y][x] in ['A', 'Z', 'S', 'K', 'B']:
                found_replicated = True
                break
        if found_replicated: break
    
    assert found_replicated, "North sector did not contain replicated elements from chapter1"

def test_macro_map_player_spawn():
    """Verify player spawn is at (60, 50)."""
    world = create_world("macro_world")
    # Player start is returned in pixels
    from constants import TILE_SIZE
    expected_px = 60 * TILE_SIZE
    expected_py = 50 * TILE_SIZE
    
    assert world.player_start == (expected_px, expected_py)
