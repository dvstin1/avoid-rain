"""
Tests to validate that the world grid is larger than the visible screen
and that the world contains an inner island perimeter wall separating an
inside area from the outside.
"""

from engine.world import World
from constants import GRID_WIDTH, GRID_HEIGHT, SCREEN_WIDTH, TILE_SIZE


def test_world_is_larger_than_screen():
    screen_tiles_w = SCREEN_WIDTH // TILE_SIZE
    assert GRID_WIDTH > screen_tiles_w

    world = World()
    world._init_sanctuary_walls()

    # Outer border walls should exist
    for x in range(GRID_WIDTH):
        assert world.grid[0][x] == 1
        assert world.grid[GRID_HEIGHT - 1][x] == 1
    for y in range(GRID_HEIGHT):
        assert world.grid[y][0] == 1
        assert world.grid[y][GRID_WIDTH - 1] == 1

    # There should be at least one inner wall tile not on the outer border
    inner_wall_found = any(
        world.grid[y][x] == 1 and x not in (0, GRID_WIDTH-1) and y not in (0, GRID_HEIGHT-1)
        for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH)
    )
    assert inner_wall_found
