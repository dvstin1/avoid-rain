import pytest
from engine.maps import create_world
from engine.enemy import Miniboss
from constants import TILE_SIZE, MINIBOSS_MAX_HP

def test_chapter1_miniboss_spawn():
    world = create_world('world_map1')
    
    # Find miniboss in world.enemies
    minibosses = [e for e in world.enemies if isinstance(e, Miniboss)]
    assert len(minibosses) == 1
    mb = minibosses[0]
    
    # Check attributes
    assert mb.hp == MINIBOSS_MAX_HP
    assert mb.width == TILE_SIZE * 2
    assert mb.height == TILE_SIZE * 2

def test_chapter1_bench_dimensions():
    world = create_world('world_map1')
    
    # Find benches in world.interactables
    benches = [obj for obj in world.interactables if getattr(obj, "name", "") == "Bench"]
    # The new layout puts separate 'S' tiles.
    assert len(benches) >= 1

def test_chapter1_topology_hallway():
    world = create_world('world_map1')
    # Row 13-22 should be mostly walls with a hole at index 39
    # In json: "#######################################.########################################"
    for y in range(13, 23):
        # 39 * TILE_SIZE is the open space
        # Tile 38 is wall, 39 is empty, 40 is wall
        from constants import TILE_WALL, TILE_EMPTY
        assert world.grid[y][38] == TILE_WALL
        assert world.grid[y][39] == TILE_EMPTY
        assert world.grid[y][40] == TILE_WALL

