"""
Handles world grid, map sections, and static obstacles.
"""
import os
import json
import random
from constants import (
    GRID_WIDTH, GRID_HEIGHT, TILE_WALL, TILE_EMPTY, TILE_SIZE, TILE_WARP,
    PLAYER_START_X, PLAYER_START_Y, POOL_MONTHLY_REPORT, POOL_SPECIAL_EDITION
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
            print(f"[DEBUG] WarpPortal targeting: {self.target_name}")
            
            game_state.world = create_world(self.target_name)

            # Sanctuary Reset Rule: Enforce automatic item and health reset
            if self.target_name == "sanctuary":
                from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES, SWORD_DAMAGE
                game_state.player.hp = float(PLAYER_MAX_HP)
                game_state.player.flask_charges = int(FLASK_MAX_CHARGES)
                game_state.player.weapons = [{"name": "Initial Quill", "damage": SWORD_DAMAGE}]
                game_state.player.active_weapon_idx = 0
                # Lifecycle Boundary: Permanent Sanctuary return clears session
                if game_state.stats:
                    game_state.stats.data["active_session_in_progress"] = False
                    game_state.stats.data["run_state"] = None
            else:
                # State Reset Rule: When starting a new run through the book, reset result to INIT
                if game_state.stats:
                    game_state.stats.data["last_run_result"] = "INIT"

            # Position player at spawn coords
            print(f"[DEBUG] Setting player spawn: ({self.spawn_x}, {self.spawn_y})")
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
            print(f"[DEBUG] Warp to {self.target_name} complete.")
        except Exception as e:
            print(f"[ERROR] Warp failed: {e}")
            import traceback
            traceback.print_exc()

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

class WeaponPickup(GameObject):
    """An interactable weapon drop that can be swapped with the player's current weapon."""
    def __init__(self, position, weapon_data):
        super().__init__(position, (24, 24))
        self.weapon_data = weapon_data
        self.name = weapon_data.get("name", "Unknown Weapon")
        self.is_interactive = True
        self.is_solid = False

    def execute_interaction(self, game_state):
        """Perform the swap/pickup logic."""
        player = game_state.player
        if len(player.weapons) < 2:
            player.weapons.append(self.weapon_data)
            # Remove from world
            if self in game_state.world.interactables:
                game_state.world.interactables.remove(self)
        else:
            # Swap: Replace active weapon and drop the old one
            old_weapon = player.get_active_weapon()
            player.weapons[player.active_weapon_idx] = self.weapon_data
            # Drop old weapon at current position
            game_state.world.interactables.append(WeaponPickup((player.x, player.y), old_weapon))
            # Remove this pickup from world
            if self in game_state.world.interactables:
                game_state.world.interactables.remove(self)

class LevelLoader:
    """
    Dedicated parser for 2D text matrix strings or JSON map definitions.
    Translates symbols into spatial entities and initial layout.
    """
    @staticmethod
    def load_json_map(file_path, saved_enemies=None):
        """Loads a JSON map file and parses it, supporting modular stitching."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        grid = [list(row) for row in data["grid"]]
        raw_entities = data.get("entities", {})
        
        # 1. Modular Assembly Pass
        module_sockets = data.get("module_sockets", [])
        for socket in module_sockets:
            # Independent Anomaly Roll: Each socket has a 10% chance to be Special Edition
            if random.random() < 0.1:
                active_plug = random.choice(POOL_SPECIAL_EDITION)
                print(f"[ANOMALY INJECTION] Socket {socket['name']} rolled a rare Special Edition!")
            else:
                active_plug = random.choice(POOL_MONTHLY_REPORT)
                print(f"[Generation] Socket {socket['name']} compiled as Standard Monthly Report.")

            if not active_plug:
                continue
            
            # Resolve path relative to project root or maps dir
            if not os.path.exists(active_plug):
                alt_path = os.path.join("maps", os.path.basename(active_plug))
                if os.path.exists(alt_path):
                    active_plug = alt_path
                else:
                    print(f"[WARNING] Sub-map {active_plug} not found for socket {socket['name']}")
                    continue

            try:
                with open(active_plug, 'r', encoding='utf-8') as f:
                    sub_data = json.load(f)
                
                b = socket["bounds"]
                sw = sub_data["dimensions"]["width"]
                sh = sub_data["dimensions"]["height"]

                # Dimensions Alignment Rule
                if sw != b["width"] or sh != b["height"]:
                    print(f"[WARNING] Dimension mismatch for socket {socket['name']}: "
                          f"Expected {b['width']}x{b['height']}, got {sw}x{sh}")
                    continue

                # Tile Overwriting
                sub_grid = sub_data["grid"]
                for sy in range(sh):
                    for sx in range(sw):
                        grid[b["y"] + sy][b["x"] + sx] = sub_grid[sy][sx]

                # Entity Blitting (Absolute World Coordinates)
                sub_entities = sub_data.get("entities", {})
                for k, v in sub_entities.items():
                    try:
                        ex, ey = map(int, k.split(','))
                        abs_x = b["x"] + ex
                        abs_y = b["y"] + ey
                        raw_entities[f"{abs_x},{abs_y}"] = v
                    except ValueError:
                        continue
                
                print(f"[DEBUG] Stitched sub-map {active_plug} into socket {socket['name']}")
            except Exception as e:
                print(f"[ERROR] Failed to stitch sub-map {active_plug}: {e}")

        # Convert "x,y" string keys back to (x, y) tuples for LevelLoader
        entity_data = {}
        for k, v in raw_entities.items():
            try:
                x, y = map(int, k.split(','))
                entity_data[(x, y)] = v
            except ValueError:
                continue

        return LevelLoader.parse_map(["".join(row) for row in grid], entity_data, saved_enemies=saved_enemies)

    @staticmethod
    def parse_map(prototype_array, entity_data=None, saved_enemies=None):
        """
        Parses a string array and returns (grid, interactables, warp_tiles, player_start, enemies).
        If saved_enemies is provided, default spawner symbols for enemies are bypassed.
        """
        h = len(prototype_array)
        w = len(prototype_array[0]) if h > 0 else 0
        grid = [[TILE_EMPTY for _ in range(w)] for _ in range(h)]
        interactables = []
        enemies = []
        warp_tiles = {}
        player_start = (PLAYER_START_X, PLAYER_START_Y)
        entity_data = entity_data or {}

        # If we have saved enemies, reconstruct them directly (The Override Rule)
        if saved_enemies:
            for e_data in saved_enemies:
                e_type = e_data.get("type")
                if e_type == "SlugEnemy":
                    from engine.enemy import SlugEnemy
                    enemies.append(SlugEnemy.from_dict(e_data))
                elif e_type == "BatEnemy":
                    from engine.enemy import BatEnemy
                    enemies.append(BatEnemy.from_dict(e_data))
                elif e_type == "FlutterEnemy":
                    from engine.enemy import FlutterEnemy
                    enemies.append(FlutterEnemy.from_dict(e_data))
                elif e_type == "BindlingEnemy":
                    from engine.enemy import BindlingEnemy
                    enemies.append(BindlingEnemy.from_dict(e_data))
                elif e_type == "Miniboss":
                    from engine.enemy import Miniboss
                    enemies.append(Miniboss.from_dict(e_data))
                elif e_type == "MinibossM2":
                    from engine.enemy import MinibossM2
                    enemies.append(MinibossM2.from_dict(e_data))
                elif e_type == "MinibossM3":
                    from engine.enemy import MinibossM3
                    enemies.append(MinibossM3.from_dict(e_data))

        # Check for Lotus Topography symbols
        has_lotus = any('M' in row or 'X' in row for row in prototype_array)
        if has_lotus:
            print("[DEBUG] LevelLoader actively building Lotus Topography Grid")

        # Check for Chapter 1 specifically for Production Grid verification
        if any('T' in row for row in prototype_array) and not has_lotus:
            print("[DEBUG] Actively rendering Chapter 1 Production Grid")

        for y, row in enumerate(prototype_array):
            for x, char in enumerate(row):

                # Only static walls, frame, and empty space go into the grid
                if char in ('#', 'X'):
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
                    # Miniboss Spawn (Bypassed if loading from save)
                    if not saved_enemies:
                        from engine.enemy import Miniboss
                        enemies.append(Miniboss(pos[0], pos[1]))

                elif char == '2':
                    # Miniboss M2 Spawn (Bypassed if loading from save)
                    if not saved_enemies:
                        from engine.enemy import MinibossM2
                        enemies.append(MinibossM2(pos[0], pos[1]))

                elif char == '3':
                    # Miniboss M3 Spawn (Bypassed if loading from save)
                    if not saved_enemies:
                        from engine.enemy import MinibossM3
                        enemies.append(MinibossM3(pos[0], pos[1]))

                elif char == 'K':
                    # Rock
                    rock = GameObject(pos, dim)
                    rock.is_solid = True
                    rock.name = "Rock"
                    interactables.append(rock)

                elif char == 'Z':
                    # SlugEnemy Spawn (Bypassed if loading from save)
                    if not saved_enemies:
                        from engine.enemy import SlugEnemy
                        enemies.append(SlugEnemy(pos[0], pos[1]))

                elif char == 'A':
                    # BatEnemy Spawn (Bypassed if loading from save)
                    if not saved_enemies:
                        from engine.enemy import BatEnemy
                        enemies.append(BatEnemy(pos[0], pos[1]))

                elif char == 'f':
                    # FlutterEnemy Spawn (Bypassed if loading from save)
                    if not saved_enemies:
                        from engine.enemy import FlutterEnemy
                        enemies.append(FlutterEnemy(pos[0], pos[1]))

                elif char == 'b':
                    # BindlingEnemy Spawn (Bypassed if loading from save)
                    if not saved_enemies:
                        from engine.enemy import BindlingEnemy
                        enemies.append(BindlingEnemy(pos[0], pos[1]))

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

    def load_from_prototype(self, prototype_array, entity_data=None, saved_enemies=None):
        """
        Populates the world from a string array using LevelLoader.
        """
        self.grid, self.interactables, self.warp_tiles, self.player_start, self.enemies = \
            LevelLoader.parse_map(prototype_array, entity_data, saved_enemies)

    def get_nearby_walls(self, player_rect):
        """Returns wall rectangles (grid or solid GameObjects) near the player."""
        px, py, pw, ph = player_rect
        h = len(self.grid)
        w = len(self.grid[0]) if h > 0 else 0
        start_x = max(0, int(px // TILE_SIZE))
        start_y = max(0, int(py // TILE_SIZE))
        end_x = min(w, int((px + pw) // TILE_SIZE) + 1)
        end_y = min(h, int((py + ph) // TILE_SIZE) + 1)

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
