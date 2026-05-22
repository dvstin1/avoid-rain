"""Map factory and an OutsideWorld variant.

This provides a minimal OutsideWorld for the warp to transition into. The
outside world uses the same grid dimensions for now (to keep renderer and
physics simple) but populates different tiles.
"""
from engine.world import World
from constants import TILE_WALL, TILE_EMPTY, TILE_SIZE, GRID_WIDTH, GRID_HEIGHT


class OutsideWorld(World):
    """A simple outside map with some open space and perimeter walls."""
    def _init_sanctuary_walls(self):
        # wipe existing grid
        self.grid = [[TILE_EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        # Outer border walls
        for x in range(GRID_WIDTH):
            self.grid[0][x] = TILE_WALL
            self.grid[GRID_HEIGHT - 1][x] = TILE_WALL
        for y in range(GRID_HEIGHT):
            self.grid[y][0] = TILE_WALL
            self.grid[y][GRID_WIDTH - 1] = TILE_WALL

        # Add a few clusters of walls to suggest obstacles
        for x in range(3, min(10, GRID_WIDTH - 3)):
            self.grid[3][x] = TILE_WALL
        for y in range(6, min(12, GRID_HEIGHT - 3)):
            self.grid[y][6] = TILE_WALL


def create_world(name: str) -> World:
    if name == 'outside':
        return OutsideWorld()
    # default
    return World()
