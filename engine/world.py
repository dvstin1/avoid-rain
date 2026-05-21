"""
Handles world grid, map sections, and static obstacles.
"""
from constants import (
    GRID_WIDTH, GRID_HEIGHT, TILE_WALL, TILE_EMPTY, TILE_SIZE
)

class World:
    """Manages the tile-based world map."""
    # pylint: disable=too-few-public-methods
    def __init__(self):
        self.grid = [[TILE_EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self._init_sanctuary_walls()

    def _init_sanctuary_walls(self):
        """Creates a simple border and some internal walls for the Sanctuary."""
        # Top and Bottom walls
        for x in range(GRID_WIDTH):
            self.grid[0][x] = TILE_WALL
            self.grid[GRID_HEIGHT - 1][x] = TILE_WALL

        # Left and Right walls
        for y in range(GRID_HEIGHT):
            self.grid[y][0] = TILE_WALL
            self.grid[y][GRID_WIDTH - 1] = TILE_WALL

        # Some random pillars in the sanctuary
        self.grid[5][5] = TILE_WALL
        self.grid[5][GRID_WIDTH - 6] = TILE_WALL
        self.grid[GRID_HEIGHT - 6][5] = TILE_WALL
        self.grid[GRID_HEIGHT - 6][GRID_WIDTH - 6] = TILE_WALL

    def get_nearby_walls(self, player_rect):
        """
        Returns a list of wall rectangles (x, y, w, h) that could collide with the player.
        """
        px, py, pw, ph = player_rect

        # Convert pixel coordinates to grid coordinates
        start_x = max(0, int(px // TILE_SIZE))
        start_y = max(0, int(py // TILE_SIZE))
        end_x = min(GRID_WIDTH, int((px + pw) // TILE_SIZE) + 1)
        end_y = min(GRID_HEIGHT, int((py + ph) // TILE_SIZE) + 1)

        walls = []
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if self.grid[y][x] == TILE_WALL:
                    walls.append((x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        return walls
