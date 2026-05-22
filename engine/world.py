"""
Handles world grid, map sections, and static obstacles.
"""
from constants import (
    GRID_WIDTH, GRID_HEIGHT, TILE_WALL, TILE_EMPTY, TILE_SIZE, TILE_WARP
)

class WarpInteractable:
    """An interactable object that warps the player to another map."""
    def __init__(self, target_name, spawn_x, spawn_y, rect):
        self.target_name = target_name
        self.spawn_x = spawn_x
        self.spawn_y = spawn_y
        self.rect = rect # (x, y, w, h) in pixels

    def execute_interaction(self, game_state):
        """Perform the map transition."""
        try:
            from engine.maps import create_world
            game_state.world = create_world(self.target_name)
            # Position player at spawn coords
            game_state.player.x = float(self.spawn_x)
            game_state.player.y = float(self.spawn_y)
            # Recenter camera instantly
            if hasattr(game_state, 'camera'):
                game_state.camera.instant_center(game_state.player.get_center())
            # Update enemies list from the new world
            game_state.enemies = getattr(game_state.world, 'enemies', []) if hasattr(game_state.world, 'enemies') else []
            # Persist state immediately after warp to avoid progress loss
            if hasattr(game_state, 'save_stats'):
                game_state.save_stats()
        except Exception:
            # If transition fails, ignore to maintain robustness
            pass

class World:
    """Manages the tile-based world map.

    By default this creates the Sanctuary layout. Use create_world(name)
    factory to obtain other world variants (e.g., 'outside').
    """
    # pylint: disable=too-few-public-methods
    def __init__(self, name='sanctuary'):
        self.name = name
        self.grid = [[TILE_EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.warp_tiles = {}  # Mapping (x,y) -> (target_name, spawn_x_px, spawn_y_px)
        self.interactables = []
        self._init_sanctuary_walls()

    def _init_sanctuary_walls(self):
        """Creates a simple border and some internal walls for the Sanctuary.

        Additionally: create a centered island perimeter to separate an inner
        sanctuary area from the outside, while the outer border limits the
        overall outside area.
        """
        # Top and Bottom walls
        for x in range(GRID_WIDTH):
            self.grid[0][x] = TILE_WALL
            self.grid[GRID_HEIGHT - 1][x] = TILE_WALL

        # Left and Right walls
        for y in range(GRID_HEIGHT):
            self.grid[y][0] = TILE_WALL
            self.grid[y][GRID_WIDTH - 1] = TILE_WALL

        # Some random pillars in the sanctuary (keep for interior detail)
        self.grid[5][5] = TILE_WALL
        self.grid[5][GRID_WIDTH - 6] = TILE_WALL
        self.grid[GRID_HEIGHT - 6][5] = TILE_WALL
        self.grid[GRID_HEIGHT - 6][GRID_WIDTH - 6] = TILE_WALL

        # Centered island perimeter (inner wall) to separate inside/outside areas
        island_w = max(5, GRID_WIDTH // 2)
        island_h = max(5, GRID_HEIGHT // 2)
        island_x0 = (GRID_WIDTH - island_w) // 2
        island_y0 = (GRID_HEIGHT - island_h) // 2

        # Horizontal edges of the island
        for x in range(island_x0, island_x0 + island_w):
            self.grid[island_y0][x] = TILE_WALL
            self.grid[island_y0 + island_h - 1][x] = TILE_WALL

        # Vertical edges of the island
        for y in range(island_y0, island_y0 + island_h):
            self.grid[y][island_x0] = TILE_WALL
            self.grid[y][island_x0 + island_w - 1] = TILE_WALL

        # Optionally leave a small doorway on the left side of the island
        door_y = island_y0 + island_h // 2
        door_x = island_x0
        # Replace doorway tile with a warp tile leading to the outside world
        self.grid[door_y][door_x] = TILE_WARP
        # Record warp mapping: spawn player near the left side of outside map
        spawn_px = (GRID_WIDTH - 3) * TILE_SIZE
        spawn_py = (GRID_HEIGHT // 2) * TILE_SIZE
        self.warp_tiles[(door_x, door_y)] = ('outside', spawn_px, spawn_py)

        # Create interactable for the warp
        rect = (door_x * TILE_SIZE, door_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.interactables.append(WarpInteractable('outside', spawn_px, spawn_py, rect))

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

    def get_nearby_interactables(self, player_rect):
        """Returns a list of interactables that overlap with an expanded player rect."""
        px, py, pw, ph = player_rect
        # Expand player rect for interaction detection
        margin = 10
        expanded_rect = (px - margin, py - margin, pw + margin * 2, ph + margin * 2)

        from engine.physics import check_aabb_collision
        nearby = []
        for interactable in self.interactables:
            if check_aabb_collision(expanded_rect, interactable.rect):
                nearby.append(interactable)
        return nearby

    def check_for_warp(self, player_rect):
        """Return (target_name, spawn_x, spawn_y) if player's center is on a warp tile.

        Otherwise return None.
        """
        px, py, pw, ph = player_rect
        cx = int((px + pw / 2) // TILE_SIZE)
        cy = int((py + ph / 2) // TILE_SIZE)
        if (cx, cy) in self.warp_tiles:
            return self.warp_tiles[(cx, cy)]
        return None
