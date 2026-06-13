import pytest
from engine.world import World
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, GRID_WIDTH, GRID_HEIGHT

def test_world_is_larger_than_screen():
    screen_tiles_w = SCREEN_WIDTH // TILE_SIZE
    assert GRID_WIDTH > screen_tiles_w

    world = World()
    # Check default grid size
    assert len(world.grid[0]) == GRID_WIDTH
    assert len(world.grid) == GRID_HEIGHT
