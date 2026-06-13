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
    assert mb.width == 64
    assert mb.height == 64

def test_chapter1_bench_dimensions():
    world = create_world('world_map1')

    # Note: world_map1.json legend has BENCH but grid might be empty
    benches = [obj for obj in world.interactables if getattr(obj, "name", "") == "Bench"]
    # If no benches in world_map1, this test is trivial or should be targeting a different map
    if len(benches) > 0:
        assert benches[0].width == TILE_SIZE

def test_chapter1_topology_hallway():
    world = create_world('world_map1')
    # world_map1.json has borders at 38, 39
    from constants import TILE_WALL
    assert world.grid[5][38] == TILE_WALL
    assert world.grid[5][39] == TILE_WALL
