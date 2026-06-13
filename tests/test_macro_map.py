import pytest
import os
import json
from engine.maps import create_world
from constants import TILE_SIZE

def test_macro_map_generation():
    """Verify that 'macro_world' triggers generative logic and returns a valid world."""
    world = create_world("macro_world")
    
    assert "generated_world" in world.name
    # Should be massive
    assert len(world.grid[0]) >= 40
    assert len(world.grid) >= 30

def test_macro_map_player_spawn():
    """Verify player spawn in generated world."""
    world = create_world("macro_world")
    
    # Generated world has spawn logic
    assert world.player_start is not None
    assert len(world.player_start) == 2

def test_macro_map_entities():
    """Verify entities are loaded/spawned in the world."""
    world = create_world("macro_world")
    # Procedural world should have some interactables (Barrels, Lore, etc)
    assert len(world.interactables) > 0
    assert world.name != "sanctuary"
