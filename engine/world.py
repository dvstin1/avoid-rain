"""
Handles world grid, map sections, and static obstacles.
"""
import os
import json
import random
from constants import (
    GRID_WIDTH, GRID_HEIGHT, TILE_WALL, TILE_EMPTY, TILE_SIZE, TILE_WARP,
    PLAYER_START_X, PLAYER_START_Y, POOL_MONTHLY_REPORT, POOL_SPECIAL_EDITION,
    TILE_PATROL
)
from engine.actor import Actor, ActorState

class GameObject:
    """
    Unified base class for all physical props, breakables, doors, and mechanisms.
    Follows the schema defined in docs/architecture.md but without pygame dependency
    to maintain engine decoupling as per docs/file_blueprint.md.
    """
    def __init__(self, position, dimensions):
        self.x, self.y = float(position[0]), float(position[1])
        self.width, self.height = float(dimensions[0]), float(dimensions[1])
        self.rect = (self.x, self.y, self.width, self.height)
        self.is_solid = False
        self.is_interactive = False
        self.is_breakable = False
        self.health = 100.0
        self.name = "Object"

    def update(self, dt, game_state):
        """Standard per-frame logic hook."""
        pass

    def execute_interaction(self, game_state):
        """Hook for when a player interacts with this object."""
        pass

    def take_damage(self, amount):
        """Hook for breakable logic."""
        if self.is_breakable:
            self.health -= amount

    def is_dead(self):
        """Check if object is destroyed."""
        return self.is_breakable and self.health <= 0

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

            # Phase 3 Intercept: If Client entering macro-world, fetch host map
            if game_state.network_manager.network_mode == "CLIENT" and self.target_name in ("macro_world", "outside"):
                if game_state.fetch_host_map():
                    game_state.world = create_world("generated_world_client")
                else:
                    print("[NETWORK] Map fetch failed. Falling back to local generation.")
                    game_state.world = create_world(self.target_name)
            else:
                game_state.world = create_world(self.target_name)

            # Weather Sync Rule: Update boss center coordinates for the safe circle
            new_boss_list = getattr(game_state.world, 'boss_coords_list', None)
            game_state.weather_manager.set_boss_coords_list(new_boss_list)

            # Sanctuary Reset Rule: Enforce absolute state purification
            if self.target_name == "sanctuary":
                game_state.on_enter_sanctuary()
            else:
                # Auto-Host Rule: Start hosting when entering the macro-world (if not already connected)
                if hasattr(game_state, 'network_manager'):
                    if game_state.network_manager.network_mode == "OFFLINE":
                        game_state.network_manager.start_hosting()
                
                # State Reset Rule: When starting a new run through the book, reset result to INIT
                if game_state.stats:
                    game_state.stats.data["last_run_result"] = "INIT"

            # Position player at spawn coords (Priority: World default/player_start, then WarpPortal explicit)
            # Procedural Generation Rule: If create_world returned a world with a valid player_start, use it.
            game_state.player.is_exposed = False
            target_x = float(self.spawn_x)
            target_y = float(self.spawn_y)
            
            # Universal Player Start Override: If target world has a defined spawn, prefer it
            if game_state.world.player_start:
                target_x, target_y = game_state.world.player_start
                print(f"[DEBUG] Using destination player_start override: ({target_x}, {target_y})")

            print(f"[DEBUG] Setting player physical position: ({target_x}, {target_y})")
            game_state.player.x = float(target_x)
            game_state.player.y = float(target_y)
            # Phase 4: Sync camera bounds to new world
            if hasattr(game_state, 'camera'):
                game_state.camera.world_w = len(game_state.world.grid[0]) * TILE_SIZE
                game_state.camera.world_h = len(game_state.world.grid) * TILE_SIZE
                game_state.camera.instant_center(game_state.player.get_center())
            
            # Update enemies list from the new world
            if hasattr(game_state.world, 'enemies'):
                game_state.enemies = getattr(game_state.world, 'enemies', [])
            else:
                game_state.enemies = []

            # Link new world actors to patrol routes
            LevelLoader.link_actors_to_routes(game_state)

            # [Milestone] Flush state immediately upon returning to sanctuary
            is_to_sanctuary = self.target_name == "sanctuary"
            game_state.save_stats(wait=is_to_sanctuary)
            print(f"[DEBUG] Warp to {self.target_name} complete.")
        except Exception as e:
            print(f"[ERROR] Warp failed: {e}")
            import traceback
            traceback.print_exc()

class PatrolPoint(GameObject):
    """Marker symbol for the Stanza system."""
    def __init__(self, position, route_id, symbol_idx, caste_filter=None, wait_min=2.0, wait_max=5.0):
        super().__init__(position, (TILE_SIZE, TILE_SIZE))
        self.route_id = route_id
        self.symbol_idx = symbol_idx
        self.caste_filter = caste_filter or []
        self.wait_min = wait_min
        self.wait_max = wait_max
        self.is_interactive = False
        self.is_solid = False
        self.name = f"PatrolPoint_{route_id}_{symbol_idx}"

class Chronicler(Actor):
    """NPC that provides dialogue and follows a research stanza."""
    def __init__(self, position, dimensions=None, name="The Chronicler"):
        super().__init__(position[0], position[1], 40, 40, 9999, name=name)
        self.is_interactive = True
        self.is_solid = True
        self.current_dialogue = None
        self.patrol_speed_multiplier = 0.4

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
                elif game_state.stats:
                    story_flags = game_state.stats.data.get("story_flags", {})
                    if story_flags.get(key) != value:
                        match = False
                        break

            if match:
                valid_nodes.append(node)

        if not valid_nodes: return
        valid_nodes.sort(key=lambda x: int(x.get("priority", 0)), reverse=True)
        node = valid_nodes[0]

        game_state.active_dialogue = {
            "speaker": self.name,
            "text": node["text"]
        }
        print(f"[NPC] {self.name} triggered dialogue: {node['id']}")

class Wellspring(GameObject):
    """Refill station for flasks."""
    def __init__(self, position, dimensions):
        super().__init__(position, dimensions)
        self.name = "The Wellspring"
        self.is_interactive = True
        self.is_solid = True

    def execute_interaction(self, game_state):
        from constants import FLASK_MAX_CHARGES
        if game_state.player.flask_charges < FLASK_MAX_CHARGES:
            game_state.player.flask_charges = FLASK_MAX_CHARGES
            game_state.trigger_bloom("HYDRATION RESTORED", priority=1)
            print("[WELLSPRING] Flasks refilled.")
        else:
            game_state.trigger_bloom("HYDRATION FULL", priority=1)
            print("[WELLSPRING] Flasks already full.")

class LoreFragment(GameObject):
    """Collectable piece of text that reveals world history."""
    def __init__(self, position, dimensions, fragment_id, name="Lost Page"):
        super().__init__(position, dimensions)
        self.fragment_id = fragment_id
        self.name = name
        self.is_interactive = True
        self.is_solid = False

    def execute_interaction(self, game_state):
        from constants import DIALOGUE_MANIFEST
        lore_text = DIALOGUE_MANIFEST.get("lore_fragments", {}).get(self.fragment_id, "The text has faded into illegibility.")
        
        game_state.active_dialogue = {
            "speaker": self.name,
            "text": lore_text
        }
        print(f"[LORE] Read fragment: {self.fragment_id}")

class WeaponPickup(GameObject):
    """Dropped weapon from miniboss or chest."""
    def __init__(self, position, weapon_data):
        super().__init__(position, (TILE_SIZE, TILE_SIZE))
        self.weapon_data = weapon_data
        self.name = weapon_data.get("name", "Unknown Quill")
        self.is_interactive = True
        self.is_solid = False

    def execute_interaction(self, game_state):
        """Pick up or swap with current active weapon."""
        player = game_state.player
        current_idx = player.active_weapon_idx
        
        if len(player.weapons) < 2:
            # Slot available: simple pickup
            player.weapons.append(self.weapon_data)
            player.active_weapon_idx = len(player.weapons) - 1
            print(f"[PLAYER] Picked up {self.name} into Slot B")
            if self in game_state.world.interactables:
                game_state.world.interactables.remove(self)
        else:
            # Both slots full: perform a swap
            old_weapon = player.weapons[current_idx]
            player.weapons[current_idx] = self.weapon_data
            
            # Put the old weapon into this pickup object
            self.weapon_data = old_weapon
            self.name = old_weapon.get("name", "Unknown Quill")
            print(f"[PLAYER] Swapped {self.name} onto floor, picked up {player.weapons[current_idx]['name']}")
            # NOTE: self is NOT removed from interactables in this case

class Respite(GameObject):
    """Ancient anchor fragment that allows resting and character edification."""
    def __init__(self, position, dimensions):
        super().__init__(position, dimensions)
        self.name = "Respite Anchor"
        self.is_interactive = True
        self.is_solid = True

    def execute_interaction(self, game_state):
        """Trigger the Respite Level-Up UI in GameState."""
        # Only reset and log if first opening
        if getattr(game_state, 'active_respite', None) != self:
            game_state.respite_selection_idx = 0
            game_state.respite_marked_idx = -1
            print("[RESPITE] Interaction engaged.")
        
        game_state.active_dialogue = {
            "speaker": "Respite Anchor",
            "text": "" # Menu will override text rendering
        }
        game_state.active_respite = self

    def execute_rest(self, game_state, audio_manager=None):
        """Restore player and respawn standard enemies."""
        from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES
        
        # 0. Trigger SFX
        if audio_manager:
            audio_manager.play_sfx("respite_rest.ogg")

        # 1. Character Restoration
        game_state.player.hp = float(game_state.player.max_hp)
        game_state.player.flask_charges = int(FLASK_MAX_CHARGES)
        game_state.player.has_rested_this_session = True

        # 2. World Re-population
        print(f"[DEBUG] Respite resting: Re-manifesting threats in {game_state.world.name}")

        from engine.maps import create_world
        temp_world = create_world(game_state.world.name, defeated_ids=game_state.defeated_miniboss_ids)
        
        game_state.enemies = temp_world.enemies
        # Re-link routes after respawn
        LevelLoader.link_actors_to_routes(game_state)
        
        print(f"[DEBUG] Rest complete. {len(game_state.enemies)} threats re-manifested.")
        game_state.save_stats(wait=True)

    def execute_upgrade(self, game_state, marked_idx, audio_manager=None):
        """Finalize the marked upgrade."""
        success = False
        if marked_idx == 1:
            success = game_state._handle_upgrade("attack_modifier", 5)
        elif marked_idx == 2:
            success = game_state._handle_upgrade("max_hp_modifier", 10)

        if success and audio_manager:
            audio_manager.play_sfx("menu_confirm.ogg")
            print(f"[RESPITE] Upgrade {marked_idx} applied.")
        elif not success:
            print("[RESPITE] Upgrade failed (insufficient pages).")

class LevelLoader:
    """
    Dedicated parser for 2D text matrix strings or JSON map definitions.
    Translates symbols into spatial entities and initial layout.
    """
    @staticmethod
    def load_json_map(file_path, saved_enemies=None, defeated_ids=None, destroyed_ids=None):
        """Loads a JSON map file and parses it, supporting modular stitching."""
        import os
        map_name = os.path.basename(file_path).replace(".json", "")
        if "generated_world" in map_name:
            map_name = "avoid_rain_generated_world"

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        grid = [list(row) for row in data["grid"]]
        raw_entities = data.get("entities", {})

        # 1. Modular Assembly Pass
        module_sockets = data.get("module_sockets", [])
        for socket in module_sockets:
            # Override Rule: If the map JSON already defines an active_plug, use it
            active_plug = socket.get("active_plug")
            
            if not active_plug:
                # Independent Anomaly Roll: Each socket has a 10% chance to be Special Edition
                if random.random() < 0.1 and POOL_SPECIAL_EDITION:
                    active_plug = random.choice(POOL_SPECIAL_EDITION)
                else:
                    active_plug = random.choice(POOL_MONTHLY_REPORT)

            # Load and stitch the plug
            try:
                with open(active_plug, 'r', encoding='utf-8') as f_plug:
                    plug_data = json.load(f_plug)
                    
                b = socket["bounds"]
                for y_p, row_p in enumerate(plug_data["grid"]):
                    for x_p, char_p in enumerate(row_p):
                        grid[b["y"] + y_p][b["x"] + x_p] = char_p
                
                # Stitch entities
                for key, e_val in plug_data.get("entities", {}).items():
                    px_p, py_p = map(int, key.split(','))
                    new_key = f"{b['x'] + px_p},{b['y'] + py_p}"
                    raw_entities[new_key] = e_val
            except Exception as e:
                print(f"[ERROR] Modular stitch failed for {active_plug}: {e}")

        # 2. Conversion Pass: Symbols -> Entity Objects
        entity_data = {}
        for key, val in raw_entities.items():
            try:
                kx, ky = map(int, key.split(','))
                entity_data[(kx, ky)] = val
            except ValueError:
                continue

        grid, interactables, warp_tiles, player_start, enemies = LevelLoader.parse_map(
            ["".join(row) for row in grid], 
            entity_data, 
            saved_enemies=saved_enemies,
            map_name=map_name,
            defeated_ids=defeated_ids,
            destroyed_ids=destroyed_ids
        )

        # Apply procedural spawn override if present
        spawn_override = data.get("spawn_coords")
        if spawn_override:
            player_start = (spawn_override["x"] * TILE_SIZE, spawn_override["y"] * TILE_SIZE)
            print(f"[DEBUG] Applied spawn override: {player_start}")

        print(f"[DEBUG] Final player_start for {map_name}: {player_start}")
        boss_coords_list = data.get("boss_coords_list") or []
        module_sockets = data.get("module_sockets", [])

        return grid, interactables, warp_tiles, player_start, enemies, boss_coords_list, module_sockets

    @staticmethod
    def parse_map(prototype_array, entity_data=None, saved_enemies=None, map_name="unknown", defeated_ids=None, destroyed_ids=None):
        """
        Parses a string array and returns (grid, interactables, warp_tiles, player_start, enemies).
        If saved_enemies is provided, default spawner symbols for enemies are bypassed.
        """
        from engine.enemy import SYMBOL_REGISTRY
        
        h = len(prototype_array)
        w = len(prototype_array[0]) if h > 0 else 0
        grid = [[TILE_EMPTY for _ in range(w)] for _ in range(h)]
        interactables = []
        enemies = []
        warp_tiles = {}
        player_start = (PLAYER_START_X, PLAYER_START_Y)
        entity_data = entity_data or {}
        defeated_ids = defeated_ids or set()
        destroyed_ids = destroyed_ids or set()

        # Phase 4 Network Rule: Assign numeric IDs to enemies for synchronization
        # These are used to match Host enemies to Client enemies in the UDP sync.
        next_enemy_id = 0
        def get_next_id():
            nonlocal next_enemy_id
            id_val = next_enemy_id
            next_enemy_id += 1
            return id_val

        # If we have saved enemies, reconstruct them directly (The Override Rule)
        if saved_enemies:
            from engine.enemy import ENEMY_REGISTRY
            for e_data in saved_enemies:
                e_type = e_data.get("type")
                if e_type in ENEMY_REGISTRY:
                    enemy = ENEMY_REGISTRY[e_type].from_dict(e_data)
                    # Phase 4 Network Rule: Assign numeric ID for sync
                    enemy.network_id = get_next_id()
                    enemies.append(enemy)
        
        # Check for Lotus Topography symbols
        has_lotus = any('M' in row or 'X' in row for row in prototype_array)
        if has_lotus:
            print("[DEBUG] LevelLoader actively building Lotus Topography Grid")

        # Check for Chapter 1 specifically for Production Grid verification
        if any('T' in row for row in prototype_array) and not has_lotus:
            print("[DEBUG] Actively rendering Chapter 1 Production Grid")

        for y, row in enumerate(prototype_array):
            for x, char in enumerate(row):

                # 1. Tile Grid Assignment (Static Topography)
                if char in ('#', 'X'):
                    grid[y][x] = TILE_WALL
                elif char == 'M':
                    from constants import TILE_LOTUS_FRAME
                    grid[y][x] = TILE_LOTUS_FRAME
                else:
                    # Every other symbol defaults to empty floor for collision/base grid purposes
                    grid[y][x] = TILE_EMPTY

                pos = (x * TILE_SIZE, y * TILE_SIZE)
                dim = (TILE_SIZE, TILE_SIZE)

                # 2. Entity & Interaction Spawning (Dynamic Overlay)
                # Separated from tile block to prevent character consumption
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
                    respite = Respite(pos, dim)
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
                    prop_id = f"{map_name}:prop:{x},{y}"
                    if prop_id in destroyed_ids:
                        continue # Already redacted

                    prop = GameObject(pos, dim)
                    prop.is_solid = True
                    prop.is_breakable = True
                    prop.health = 1.0
                    prop.name = "Barrel"
                    prop.id = prop_id
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

                elif char == 'K':
                    # Rock
                    rock = GameObject(pos, dim)
                    rock.is_solid = True
                    rock.name = "Rock"
                    interactables.append(rock)

                elif char == 'P':
                    # Player Start hook
                    player_start = (pos[0], pos[1])

                elif char in ('1','2','3','4','5','6','7','8','9'):
                    # Patrol Point
                    data = entity_data.get((x, y), {})
                    rid = data.get("route_id", "default")
                    caste = data.get("caste_filter", [])
                    wmin = data.get("wait_min", 2.0)
                    wmax = data.get("wait_max", 5.0)
                    point = PatrolPoint(pos, rid, int(char), caste, wmin, wmax)
                    interactables.append(point)

                elif char in SYMBOL_REGISTRY:
                    # Generic Enemy Spawner (Bypassed if loading from save)
                    if not saved_enemies:
                        # Generate Unique ID based on position and map
                        enemy_id = f"{map_name}:{x},{y}"
                        
                        # Filter Rule: If it's a miniboss and already defeated, skip spawning
                        enemy_cls = SYMBOL_REGISTRY[char]
                        
                        data = entity_data.get((x, y), {})
                        temp_enemy = enemy_cls(pos[0], pos[1], id=enemy_id)
                        
                        # Phase 4 Network Rule: Assign numeric ID for sync
                        temp_enemy.network_id = get_next_id()
                        
                        # Custom Instance Attributes
                        if data.get("is_stationary"):
                            temp_enemy.is_stationary = True
                        
                        if temp_enemy.is_miniboss and enemy_id in defeated_ids:
                            print(f"[DEBUG] Elite {enemy_id} already redacted; skipping spawn.")
                        else:
                            enemies.append(temp_enemy)


        return grid, interactables, warp_tiles, player_start, enemies

    @staticmethod
    def link_actors_to_routes(game_state):
        """Find and assign patrol routes to nearby actors using proximity discovery."""
        all_actors = list(game_state.enemies)
        # Search for NPCs who are Actors
        for obj in game_state.world.interactables:
            if isinstance(obj, Actor):
                all_actors.append(obj)
        
        markers = [obj for obj in game_state.world.interactables if isinstance(obj, PatrolPoint)]
        
        for actor in all_actors:
            # Rule: Only if actor has no route and is not stationary
            if actor.patrol_route or actor.is_stationary:
                continue
                
            ax, ay = actor.get_center()
            # 1. Find nearest marker (within 20 tiles for robustness)
            nearest = None
            min_dist_sq = (20 * TILE_SIZE)**2
            
            for m in markers:
                # Caste Filter Check
                if m.caste_filter and actor.__class__.__name__ not in m.caste_filter:
                    continue
                    
                mx, my = m.x + m.width/2, m.y + m.height/2
                dist_sq = (ax - mx)**2 + (ay - my)**2
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    nearest = m
            
            if nearest:
                # 2. Gather all markers in the same logical route
                # Rule: Same route_id OR spatially connected chain
                if nearest.route_id != "default":
                    route = [m for m in markers if m.route_id == nearest.route_id]
                else:
                    # Spatially Connected Discovery:
                    # Find all 'default' markers reachable in steps of 10 tiles
                    route = []
                    to_check = [nearest]
                    while to_check:
                        curr = to_check.pop(0)
                        if curr in route: continue
                        route.append(curr)
                        
                        cx, cy = curr.x + curr.width/2, curr.y + curr.height/2
                        for m in markers:
                            if m.route_id == "default" and m not in route:
                                mx, my = m.x + m.width/2, m.y + m.height/2
                                d_sq = (cx - mx)**2 + (cy - my)**2
                                if d_sq <= (10 * TILE_SIZE)**2:
                                    to_check.append(m)

                # Sort by symbol index
                route.sort(key=lambda x: x.symbol_idx)
                actor.patrol_route = route
                # Start at the nearest marker
                actor.patrol_idx = route.index(nearest)
                print(f"[STANZA] Actor {actor.name} anchored to route '{nearest.route_id}' ({len(route)} points)")

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
        self.module_sockets = []
        self.boss_coords_list = []

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
