"""
Handles world grid, map sections, and static obstacles.
"""
from constants import (
    GRID_WIDTH, GRID_HEIGHT, TILE_WALL, TILE_EMPTY, TILE_SIZE, TILE_WARP, TILE_KEY
)

class GameObject:
    """
    Unified base class for all physical props, breakables, doors, and mechanisms.
    Follows the schema defined in docs/architecture.md but without pygame dependency
    to maintain engine decoupling as per docs/file_blueprint.md.
    """
    def __init__(self, position, dimensions):
        self.x, self.y = position
        self.width, self.height = dimensions
        
        # Core Architectural Trait Flags
        self.is_solid = True         # Blocks player/enemy kinematics
        self.is_breakable = False     # Listens to damage vectors; links to LootManager
        self.is_interactive = False   # Listens to player input triggers
        self.is_kinematic = False     # Modifies passenger velocity vectors (platforms)
        
        self.name = "Object"
        self.data = {}

    @property
    def rect(self):
        """Returns the rectangle as a (x, y, w, h) tuple."""
        return (self.x, self.y, self.width, self.height)

    def execute_interaction(self, game_state):
        """Standard interaction callback to be overridden or assigned."""
        pass

class WarpPortal(GameObject):
    """An interactable object that warps the player to another map."""
    def __init__(self, target_name, spawn_x, spawn_y, rect, name="Warp"):
        super().__init__((rect[0], rect[1]), (rect[2], rect[3]))
        self.target_name = target_name
        self.spawn_x = spawn_x
        self.spawn_y = spawn_y
        self.name = name
        self.is_interactive = True
        self.is_solid = False # Usually can stand on warp tiles

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

    Supports loading from string-based prototypes for rapid level design.
    """
    def __init__(self, name='sanctuary'):
        self.name = name
        self.grid = [[TILE_EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.warp_tiles = {}  # Legacy mapping (x,y) -> (target_name, spawn_x_px, spawn_y_px)
        self.interactables = []
        
        # Default to legacy hardcoded sanctuary if no prototype is used
        if name == 'sanctuary':
            self._init_sanctuary_walls()

    def _init_sanctuary_walls(self):
        """Creates a simple border and some internal walls for the Sanctuary.
        
        Maintains legacy behavior for the default hub.
        """
        # Top and Bottom walls
        for x in range(GRID_WIDTH):
            self.grid[0][x] = TILE_WALL
            self.grid[GRID_HEIGHT - 1][x] = TILE_WALL

        # Left and Right walls
        for y in range(GRID_HEIGHT):
            self.grid[y][0] = TILE_WALL
            self.grid[y][GRID_WIDTH - 1] = TILE_WALL

        # Centered island perimeter (inner wall)
        island_w = max(5, GRID_WIDTH // 2)
        island_h = max(5, GRID_HEIGHT // 2)
        island_x0 = (GRID_WIDTH - island_w) // 2
        island_y0 = (GRID_HEIGHT - island_h) // 2

        for x in range(island_x0, island_x0 + island_w):
            self.grid[island_y0][x] = TILE_WALL
            self.grid[island_y0 + island_h - 1][x] = TILE_WALL

        for y in range(island_y0, island_y0 + island_h):
            self.grid[y][island_x0] = TILE_WALL
            self.grid[y][island_x0 + island_w - 1] = TILE_WALL

        # Warp portal to outside
        door_y = island_y0 + island_h // 2
        door_x = island_x0
        self.grid[door_y][door_x] = TILE_WARP
        
        spawn_px = (GRID_WIDTH - 3) * TILE_SIZE
        spawn_py = (GRID_HEIGHT // 2) * TILE_SIZE
        self.warp_tiles[(door_x, door_y)] = ('outside', spawn_px, spawn_py)
        
        rect = (door_x * TILE_SIZE, door_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.interactables.append(WarpPortal('outside', spawn_px, spawn_py, rect, name="The Chronicle"))

    def load_from_prototype(self, prototype_array, entity_data=None):
        """
        Populates the grid and spawns GameObjects from a string array.
        
        Args:
            prototype_array: List of strings representing the map layout.
            entity_data: Dictionary mapping (x, y) to custom entity properties.
        """
        self.grid = [[TILE_EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.interactables = []
        self.warp_tiles = {}
        entity_data = entity_data or {}

        for y, row in enumerate(prototype_array):
            if y >= GRID_HEIGHT: break
            for x, char in enumerate(row):
                if x >= GRID_WIDTH: break
                
                tile_type = TILE_KEY.get(char, TILE_EMPTY)
                self.grid[y][x] = tile_type
                
                pos = (x * TILE_SIZE, y * TILE_SIZE)
                dim = (TILE_SIZE, TILE_SIZE)
                
                if char == 'W':
                    # Warp Portal
                    data = entity_data.get((x, y), {})
                    target = data.get('target', 'sanctuary')
                    from constants import PLAYER_START_X, PLAYER_START_Y
                    sx = data.get('spawn_x', PLAYER_START_X)
                    sy = data.get('spawn_y', PLAYER_START_Y)
                    
                    self.warp_tiles[(x, y)] = (target, sx, sy)
                    self.interactables.append(WarpPortal(target, sx, sy, (pos[0], pos[1], dim[0], dim[1]), name=data.get('name', "The Chronicle")))
                
                elif char == 'R':
                    # Respite
                    respite = GameObject(pos, dim)
                    respite.is_interactive = True
                    respite.is_solid = True
                    respite.name = "Respite"
                    self.interactables.append(respite)
                
                elif char == 'T':
                    # Static Obstacle
                    tree = GameObject(pos, dim)
                    tree.is_solid = True
                    tree.name = "Structure"
                    self.interactables.append(tree)
                
                elif char == 'B':
                    # Placeholder Prop
                    prop = GameObject(pos, dim)
                    prop.is_solid = True
                    prop.is_breakable = True
                    prop.name = "Prop"
                    self.interactables.append(prop)

    def get_nearby_walls(self, player_rect):
        """Returns wall rectangles (grid or solid GameObjects) near the player."""
        px, py, pw, ph = player_rect
        start_x = max(0, int(px // TILE_SIZE))
        start_y = max(0, int(py // TILE_SIZE))
        end_x = min(GRID_WIDTH, int((px + pw) // TILE_SIZE) + 1)
        end_y = min(GRID_HEIGHT, int((py + ph) // TILE_SIZE) + 1)

        walls = []
        # Grid-based walls
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if self.grid[y][x] == TILE_WALL:
                    walls.append((x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
        
        # Solid GameObjects
        from engine.physics import check_aabb_collision
        for obj in self.interactables:
            if obj.is_solid and check_aabb_collision(player_rect, obj.rect):
                walls.append((obj.rect[0], obj.rect[1], obj.rect[2], obj.rect[3]))
                
        return walls

    def get_nearby_interactables(self, player_rect):
        """Returns interactables that overlap with an expanded player rect."""
        px, py, pw, ph = player_rect
        margin = 10
        expanded_rect = (px - margin, py - margin, pw + margin * 2, ph + margin * 2)

        from engine.physics import check_aabb_collision
        nearby = []
        for obj in self.interactables:
            if obj.is_interactive and check_aabb_collision(expanded_rect, obj.rect):
                nearby.append(obj)
        return nearby

    def check_for_warp(self, player_rect):
        """Legacy warp check for grid-based warp tiles."""
        px, py, pw, ph = player_rect
        cx = int((px + pw / 2) // TILE_SIZE)
        cy = int((py + ph / 2) // TILE_SIZE)
        if (cx, cy) in self.warp_tiles:
            return self.warp_tiles[(cx, cy)]
        return None
