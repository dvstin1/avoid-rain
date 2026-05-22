
import pytest
from engine.world import World, LevelLoader
from engine.room_definitions import ROOM_PROTOTYPES, ENTITY_MANIFEST
from engine.enemy import Miniboss
from constants import TILE_SIZE, MINIBOSS_MAX_HP

def test_chapter1_miniboss_spawn():
    world = World(name='chapter1')
    world.load_from_prototype(ROOM_PROTOTYPES["chapter1"], ENTITY_MANIFEST.get("chapter1", {}))
    
    # Find miniboss in world.enemies
    minibosses = [e for e in world.enemies if isinstance(e, Miniboss)]
    assert len(minibosses) == 1
    mb = minibosses[0]
    
    # Check attributes
    assert mb.hp == MINIBOSS_MAX_HP
    assert mb.width == TILE_SIZE * 2
    assert mb.height == TILE_SIZE * 2

def test_chapter1_bench_dimensions():
    world = World(name='chapter1')
    world.load_from_prototype(ROOM_PROTOTYPES["chapter1"], ENTITY_MANIFEST.get("chapter1", {}))
    
    # Find benches in world.interactables
    benches = [obj for obj in world.interactables if obj.name == "Bench"]
    # In my chapter1 layout I added 2 benches (each spanning 2 rows 'S' was twice)
    # Wait, 'S' was twice but LevelLoader creates one GameObject per 'S'.
    # In my layout I have:
    # "#...S..........................................................................#" (row 3)
    # "#...S..........................................................................#" (row 10)
    # So there are 2 benches.
    assert len(benches) == 2
    for bench in benches:
        assert bench.width == TILE_SIZE
        assert bench.height == TILE_SIZE * 2

def test_chapter1_topology_hallway():
    # Verify the hallway exists at x=39 (middle of 80)
    prototype = ROOM_PROTOTYPES["chapter1"]
    
    # Row 13-22 should be mostly walls with a hole at index 39
    for y in range(13, 23):
        row = prototype[y]
        assert row[38] == '#'
        assert row[39] == '.'
        assert row[40] == '#'
