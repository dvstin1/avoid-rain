"""
Handles world grid, map sections, and static obstacles.
"""
import math
from constants import (
    GRID_WIDTH, GRID_HEIGHT, TILE_WALL, TILE_EMPTY, TILE_SIZE, TILE_WARP,
    PLAYER_START_X, PLAYER_START_Y, MACRO_MAP_SIZE
)

def generate_macro_lotus_world():
    """
    Refactors the macro-level generation to a distance-based radial algorithm.
    Creates a central courtyard, an outer ring, and 6 connecting spokes.
    Nests replicated chapter1 modules within the radial sectors.
    """
    from engine.room_definitions import ROOM_PROTOTYPES
    chapter1 = ROOM_PROTOTYPES.get("chapter1", ["#"])
    
    # Initialize 120x120 with '#' (Walls)
    world_grid = [['#' for _ in range(MACRO_MAP_SIZE)] for _ in range(MACRO_MAP_SIZE)]
    center_x, center_y = MACRO_MAP_SIZE // 2, MACRO_MAP_SIZE // 2
    
    for y in range(MACRO_MAP_SIZE):
        for x in range(MACRO_MAP_SIZE):
            dx = x - center_x
            dy = y - center_y
            dist = math.sqrt(dx*dx + dy*dy)

            # 1. Central Courtyard
            if dist < 15:
                world_grid[y][x] = '.'

            # 2. Outer Rim Ring
            if 50 < dist < 55:
                world_grid[y][x] = '.'

            # 3. 6 Radial Spoke Hallways
            # Angles: 0, 60, 120, 180, 240, 300 degrees
            if 15 <= dist <= 50:
                angle = math.degrees(math.atan2(dy, dx))
                # Normalize angle to [0, 360)
                if angle < 0:
                    angle += 360

                # Check proximity to 6 target angles
                for target in [0, 60, 120, 180, 240, 300]:
                    # Handle wrap-around for 0/360
                    diff = abs(angle - target)
                    if diff > 180:
                        diff = 360 - diff

                    # Hallway width threshold (approx 2-3 tiles wide at dist 15-50)
                    # angle_threshold = width / dist * (180 / pi)
                    # Let's use a simpler fixed angle width for now, or scale it.
                    if diff < (120 / max(1, dist)):
                        world_grid[y][x] = '.'

    # 4. Nest Replicated Modules
    # We place 4 modules in the larger gaps between spokes
    # Positions roughly at 30, 90, 210, 270 degrees
    module_angles = [30, 105, 210, 285] # Adjusted to miss spokes better
    for m_angle in module_angles:
        rad = math.radians(m_angle)
        # Place module center at distance ~35
        mx = int(center_x + math.cos(rad) * 35) - 10
        my = int(center_y + math.sin(rad) * 35) - 10

        for y_offset in range(20):
            if y_offset >= len(chapter1):
                break
            for x_offset in range(20):
                if x_offset >= len(chapter1[y_offset]):
                    break
                char = chapter1[y_offset][x_offset]
                if char == 'P':
                    char = '.'

                # Only overwrite if it's within map bounds
                if 0 <= my + y_offset < MACRO_MAP_SIZE and 0 <= mx + x_offset < MACRO_MAP_SIZE:
                    # Carve into walls
                    if char != '#':
                        world_grid[my + y_offset][mx + x_offset] = char

    # 5. Anchor player spawn point
    # LAND at (60, 50) as requested
    world_grid[50][60] = 'P'

    print("[WORLD MATRIX] Initialized 120x120 Radial Lotus-Wheel with 6 spokes and 4 modules.")

    return ["".join(row) for row in world_grid]

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

        self.health = 1.0            # Default health for breakables
        self.name = "Object"
        self.data = {}

    @property
    def rect(self):
        """Returns the rectangle as a (x, y, w, h) tuple."""
        return (self.x, self.y, self.width, self.height)

    def take_damage(self, amount):
        """Decrement health if the object is breakable."""
        if self.is_breakable:
            self.health -= amount

    def is_destroyed(self):
        """Check if the object has been destroyed."""
        return self.is_breakable and self.health <= 0

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

            # State Reset Rule: When starting a new run through the book, reset result to INIT
            if self.target_name != "sanctuary" and game_state.stats:
                game_state.stats.data["last_run_result"] = "INIT"

            # Position player at spawn coords
            game_state.player.x = float(self.spawn_x)
            game_state.player.y = float(self.spawn_y)
            # Recenter camera instantly
            if hasattr(game_state, 'camera'):
                game_state.camera.instant_center(game_state.player.get_center())
            # Update enemies list from the new world
            if hasattr(game_state.world, 'enemies'):
                game_state.enemies = getattr(game_state.world, 'enemies', [])
            else:
                game_state.enemies = []

            # [Milestone] Flush state immediately upon returning to sanctuary
            is_to_sanctuary = self.target_name == "sanctuary"
            game_state.save_stats(wait=is_to_sanctuary)
        except Exception:
            # If transition fails, ignore to maintain robustness
            pass

class Chronicler(GameObject):
    """NPC that provides dialogue based on the player's last run result."""
    def __init__(self, position, dimensions, name="The Chronicler"):
        super().__init__(position, dimensions)
        self.name = name
        self.is_interactive = True
        self.is_solid = True
        self.current_dialogue = None

    def execute_interaction(self, game_state):
        """Select dialogue based on state and display it."""
        from constants import DIALOGUE_MANIFEST
        manifest = DIALOGUE_MANIFEST.get("chronicler", [])

        # Get current state from stats
        last_result = "INIT"
        if game_state.stats:
            last_result = game_state.stats.data.get("last_run_result", "INIT")

        # Filter and sort by priority
        valid_nodes = []
        for node in manifest:
            conditions = node.get("conditions", {})
            match = True
            for key, value in conditions.items():
                if key == "last_run_result":
                    if value != last_result:
                        match = False
                        break
                # Other story flags could be checked here
                elif game_state.stats:
                    story_flags = game_state.stats.data.get("story_flags", {})
                    if story_flags.get(key) != value:
                        match = False
                        break

            if match:
                valid_nodes.append(node)

        # Sort by priority (descending)
        valid_nodes.sort(key=lambda x: int(x.get("priority", 0)), reverse=True)

        if valid_nodes:
            self.current_dialogue = valid_nodes[0]["text"]
            # Trigger dialogue box in GameState
            game_state.dialogue_mode = "STANDARD"
            game_state.active_dialogue = {
                "speaker": self.name,
                "text": self.current_dialogue
            }

class Wellspring(GameObject):
    """Environmental Hub Asset that projects statistics and bestiary."""
    def __init__(self, position, dimensions, name="The Wellspring"):
        super().__init__(position, dimensions)
        self.name = name
        self.is_interactive = True
        self.is_solid = True

    def execute_interaction(self, game_state):
        """Open the Statistics menu via dialogue box."""
        if not game_state.stats:
            # Fallback if no stats available
            game_state.active_dialogue = {
                "speaker": self.name,
                "text": "The water is still. No memories are reflected here yet."
            }
            return

        stats = game_state.stats.data.get("lifetime_stats", {})
        bestiary = game_state.stats.data.get("discovered_bestiary", {})

        # Build multiline text
        text = "Timeline Reflection:\n"
        text += f"Chapters Cleared: {stats.get('wins_chapters_cleared', 0)}\n"
        text += f"Bleed Wipes: {stats.get('losses_bleed_wipes', 0)}\n"
        text += f"Standard Respawns: {stats.get('deaths_standard_respawns', 0)}\n"
        text += f"Torn Pages: {stats.get('pages_collected', 0)}\n"

        discovered_count = sum(1 for v in bestiary.values() if v)
        text += f"Syntax Blocks: {discovered_count}"

        game_state.dialogue_mode = "EXPANDED"
        game_state.active_dialogue = {
            "speaker": self.name,
            "text": text
        }

class LoreFragment(GameObject):
    """An interactable object that displays a lore snippet from the manifest."""
    def __init__(self, position, dimensions, fragment_id, name="Lost Passage"):
        super().__init__(position, dimensions)
        self.fragment_id = fragment_id
        self.name = name
        self.is_interactive = True
        self.is_solid = False # Can walk over it, like a page on the ground

    def execute_interaction(self, game_state):
        from constants import DIALOGUE_MANIFEST
        manifest = DIALOGUE_MANIFEST.get("lore_fragments", {})
        snippet = manifest.get(self.fragment_id, "The text is faded beyond recognition.")

        game_state.dialogue_mode = "STANDARD"
        game_state.active_dialogue = {
            "speaker": self.name,
            "text": snippet
        }

class LevelLoader:
    """
    Dedicated parser for 2D text matrix strings.
    Translates symbols into spatial entities and initial layout.
    """
    @staticmethod
    def parse_map(prototype_array, entity_data=None):
        """
        Parses a string array and returns (grid, interactables, warp_tiles, player_start, enemies).
        """
        grid = [[TILE_EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        interactables = []
        enemies = []
        warp_tiles = {}
        player_start = (PLAYER_START_X, PLAYER_START_Y)
        entity_data = entity_data or {}

        # Check for Lotus Topography symbols
        has_lotus = any('M' in row or 'X' in row for row in prototype_array)
        if has_lotus:
            print("[DEBUG] LevelLoader actively building Lotus Topography Grid")

        # Check for Chapter 1 specifically for Production Grid verification
        # For simplicity, we can pass the room_id or just check a unique pattern.
        # Let's check for 'T' (trees) which are prominent in Chapter 1.
        if any('T' in row for row in prototype_array) and not has_lotus:
            print("[DEBUG] Actively rendering Chapter 1 Production Grid")

        for y, row in enumerate(prototype_array):
            if y >= GRID_HEIGHT: break
            for x, char in enumerate(row):
                if x >= GRID_WIDTH: break

                # Only static walls, frame, and empty space go into the grid
                if char == '#' or char == 'X':
                    grid[y][x] = TILE_WALL
                elif char == 'M':
                    from constants import TILE_LOTUS_FRAME
                    grid[y][x] = TILE_LOTUS_FRAME
                else:
                    grid[y][x] = TILE_EMPTY

                pos = (x * TILE_SIZE, y * TILE_SIZE)
                dim = (TILE_SIZE, TILE_SIZE)

                if char == 'W':
                    # Warp Portal
                    data = entity_data.get((x, y), {})
                    target = data.get('target', 'sanctuary')
                    sx = data.get('spawn_x', PLAYER_START_X)
                    sy = data.get('spawn_y', PLAYER_START_Y)

                    warp_tiles[(x, y)] = (target, sx, sy)
                    interactables.append(WarpPortal(
                        target, sx, sy, (pos[0], pos[1], dim[0], dim[1]),
                        name=data.get('name', "The Chronicle")
                    ))

                elif char == 'R':
                    # Respite
                    respite = GameObject(pos, dim)
                    respite.is_interactive = True
                    respite.is_solid = True
                    respite.name = "Respite"
                    interactables.append(respite)

                elif char == 'T':
                    # Static Obstacle / Tree
                    tree = GameObject(pos, dim)
                    tree.is_solid = True
                    tree.name = "Structure"
                    interactables.append(tree)

                elif char == 'C':
                    # The Chronicler NPC
                    chronicler = Chronicler(pos, dim)
                    interactables.append(chronicler)

                elif char == 'F':
                    # The Wellspring (Fountain)
                    wellspring = Wellspring(pos, dim)
                    interactables.append(wellspring)

                elif char == 'L':
                    # Lore Fragment
                    data = entity_data.get((x, y), {})
                    frag_id = data.get('fragment_id', 'unknown')
                    frag_name = data.get('name', 'Lost Passage')
                    fragment = LoreFragment(pos, dim, frag_id, name=frag_name)
                    interactables.append(fragment)

                elif char == 'B':
                    # Placeholder Prop / Barrel
                    prop = GameObject(pos, dim)
                    prop.is_solid = True
                    prop.is_breakable = True
                    prop.health = 1.0
                    prop.name = "Barrel"
                    interactables.append(prop)

                elif char == 'h':
                    # Heavy Bookcase - Horizontal 2x1
                    bookcase_dim = (TILE_SIZE * 2, TILE_SIZE)
                    bookcase = GameObject(pos, bookcase_dim)
                    bookcase.is_solid = True
                    bookcase.name = "Heavy Bookcase"
                    interactables.append(bookcase)

                elif char == 'd':
                    # Ink-Drip Urn - 1x1
                    urn = GameObject(pos, dim)
                    urn.is_solid = True
                    urn.name = "Ink Urn"
                    interactables.append(urn)

                elif char == 'v':
                    # Spilled Inkwell Puddle - 1x1 Hazard
                    puddle = GameObject(pos, dim)
                    puddle.is_solid = False
                    puddle.name = "Inkwell Puddle"
                    interactables.append(puddle)

                elif char == 'l':
                    # Iron Candelabra - 1x1 Light Source
                    candelabra = GameObject(pos, dim)
                    candelabra.is_solid = True
                    candelabra.name = "Candelabra"
                    interactables.append(candelabra)

                elif char == 'S':                    # Seat / Bench - Vertical 1x2
                    bench_dim = (TILE_SIZE, TILE_SIZE * 2)
                    bench = GameObject(pos, bench_dim)
                    bench.is_solid = True
                    bench.name = "Bench"
                    interactables.append(bench)

                elif char == 'E':
                    # Miniboss Spawn
                    from engine.enemy import Miniboss
                    enemies.append(Miniboss(pos[0], pos[1]))

                elif char == 'K':
                    # Rock
                    rock = GameObject(pos, dim)
                    rock.is_solid = True
                    rock.name = "Rock"
                    interactables.append(rock)

                elif char == 'Z':
                    # SlugEnemy Spawn
                    from engine.enemy import SlugEnemy
                    enemies.append(SlugEnemy(pos[0], pos[1]))

                elif char == 'A':
                    # BatEnemy Spawn
                    from engine.enemy import BatEnemy
                    enemies.append(BatEnemy(pos[0], pos[1]))

                elif char == 'P':
                    # Player Start hook
                    player_start = (pos[0], pos[1])

        return grid, interactables, warp_tiles, player_start, enemies

class World:
    """Manages the tile-based world map.

    Supports loading from string-based prototypes for rapid level design.
    """
    def __init__(self, name='sanctuary'):
        self.name = name
        self.grid = [[TILE_EMPTY for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.warp_tiles = {}  # Legacy mapping (x,y) -> (target_name, spawn_x_px, spawn_y_px)
        self.interactables = []
        self.enemies = []
        self.player_start = (PLAYER_START_X, PLAYER_START_Y)

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
        Populates the world from a string array using LevelLoader.
        """
        self.grid, self.interactables, self.warp_tiles, self.player_start, self.enemies = \
            LevelLoader.parse_map(prototype_array, entity_data)

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
