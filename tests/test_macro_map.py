import pytest
import os
import json
from engine.maps import create_world
from constants import TILE_SIZE

def test_macro_map_json_loading():
    """Verify that 'macro_world' correctly loads from world_map1.json."""
    world = create_world("macro_world")
    
    # Read the JSON directly to verify
    with open(os.path.join("maps", "world_map1.json"), 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    assert world.name == "world_map1"
    assert len(world.grid[0]) == data["dimensions"]["width"]
    assert len(world.grid) == data["dimensions"]["height"]

def test_macro_map_player_spawn():
    """Verify player spawn from world_map1.json layout."""
    world = create_world("macro_world")
    
    # In world_map1.json (formerly chapter1.json), 'P' is at column 17, row 7
    expected_px = 17 * TILE_SIZE
    expected_py = 7 * TILE_SIZE
    
    assert world.player_start == (expected_px, expected_py)

def test_macro_map_entities():
    """Verify entities are loaded into the world."""
    world = create_world("macro_world")
    # Check for lore fragment or warp
    has_warp = any(hasattr(obj, 'target_name') for obj in world.interactables)
    assert has_warp, "Warp portal was not loaded from world_map1.json"
