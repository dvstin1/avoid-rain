"""
Manages the global game state and coordinates engine components.
"""
from typing import Optional
import queue
import threading
import random
import time
import pygame

from constants import (
    PLAYER_START_X, PLAYER_START_Y,
    DAMAGE_NUMBER_LIFETIME, DAMAGE_NUMBER_SPEED,
    SWORD_DAMAGE, COLOR_SELECTION, COLOR_WHITE, RECOVERY_TIME, STAGGER_OUTLINE_TIME,
    PLAYER_MAX_HP, FLASK_MAX_CHARGES,
    SCREEN_SHAKE_DURATION, HIT_STOP_DURATION,
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_PANEL_H, HUD_SWAP_BTN_RECT, HUD_PICKUP_BTN_RECT,
    TILE_SIZE, GRID_WIDTH, GRID_HEIGHT, CAMERA_LERP_SPEED,
    SCREEN_SHAKE_INTENSITY, AUTOSAVE_INDICATOR_DURATION,
    WEATHER_MAX_RADIUS, WEATHER_MIN_RADIUS, WEATHER_WAIT_DURATION,
    WEATHER_SHRINK_DURATION, WEATHER_DAMAGE_PER_SECOND,
    TILE_STRUCTURE, TILE_RESPITE,
    BLOOM_TOTAL_DURATION, BLOOM_COOLDOWN,
    INPUT_MODE_KEYBOARD, INPUT_MODE_GAMEPAD
)
from engine.player import Player, PlayerStateEnum
from engine.combat import get_sword_hitbox
from engine.physics import check_aabb_collision, resolve_enemy_player_collision
from engine.camera import Camera
from engine.stats import StatisticsTracker

class GameState:
    """Master state object for the game engine."""
    def __init__(
        self,
        stats: Optional[StatisticsTracker] = None,
        stats_path: Optional[str] = None,
        auto_load: bool = True
    ):
        from engine.maps import create_world
        from engine.world import LevelLoader
        self.world = create_world("sanctuary")
        self.player = Player(self.world.player_start[0], self.world.player_start[1])
        self.enemies = []
        self.loot = []
        self.fading_entities = []
        self.world_debris = []
        self.damage_numbers = []
        self.defeated_miniboss_ids = set()
        self.destroyed_prop_ids = set()
        self.respite_upgrades = {1: 0, 2: 0}

        # 2. Statistics tracker: prefer injected tracker; otherwise optionally auto-load
        self.stats = stats
        if self.stats is None and auto_load:
            try:
                if stats_path is not None:
                    self.stats = StatisticsTracker.load(stats_path)
                else:
                    self.stats = StatisticsTracker.load()
            except Exception:
                self.stats = StatisticsTracker()
        
        # Hydration Rule: If we have a suspended run, restore it now
        if self.stats and self.stats.data.get("run_state"):
            self.hydrate_from_disk()

        # 3. Environment and Camera
        from engine.weather import WeatherManager
        world_w = len(self.world.grid[0]) * TILE_SIZE
        world_h = len(self.world.grid) * TILE_SIZE
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, world_w, world_h, lerp_speed=CAMERA_LERP_SPEED)
        self.weather_manager = WeatherManager(boss_coords_list=getattr(self.world, 'boss_coords_list', None))
        
        # Environmental Sync State (Legacy access for Renderer)
        self.active_safe_radius = self.weather_manager.active_safe_radius
        self.bleed_state = self.weather_manager.bleed_state
        self.current_boss_coords = self.weather_manager.get_current_boss_coords()
        
        # UI and Visual State
        self.bloom_text = ""
        self.bloom_timer = 0.0
        self.bloom_priority = 0
        self.last_zone_id = None
        self.zone_cooldown_timer = 0.0
        self.sanctuary_reset_complete = False
        
        self.active_choice = None
        self.active_dialogue = None
        self.active_respite = None
        
        self.hit_stop_timer = 0.0
        self.shake_timer = 0.0
        self.death_timer = 0.0
        self.last_save_elapsed = 9999.0 # Start large to trigger early if needed
        self.inspect_active = False
        self.parry_effects = [] # Transient VFX sparks

        # 4. Input and Navigation State
        self.input_mode = INPUT_MODE_KEYBOARD
        self.input_debounce_timer = 0.0
        self.input_ratchet_latched = False
        self.menu_nav_cooldown = 0.0
        self.lobby_selection_idx = 0
        self.lobby_editing_name = False
        
        # Menu indices
        self.respite_selection_idx = 0 # 0=Rest, 1-3=Edify, 4=Finalize, 5=Close
        self.respite_marked_idx = -1 # Which one is staged for upgrade

        self._save_queue = queue.Queue(maxsize=8)
        self._save_worker_running = True
        self.saving_in_progress = False
        self._save_worker_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._save_worker_thread.start()

        # Link actors to routes after everything is loaded
        LevelLoader.link_actors_to_routes(self)

        # Network Phase 2, 3 & 4: Manager Initialization
        from engine.network_manager import NetworkManager
        from constants import DEFAULT_PLAYER_NAME
        
        p_name = DEFAULT_PLAYER_NAME
        if self.stats:
            p_name = self.stats.data.get("player_name", DEFAULT_PLAYER_NAME)
            
        self.network_manager = NetworkManager(identity=p_name)
        self.network_manager.local_state_provider = self.get_local_state
        self.network_manager.remote_state_handler = self.apply_remote_state
        self.network_manager.on_disconnect_callback = self.on_network_disconnect
        
        # Phase 3 Callbacks
        self.network_manager.host_map_provider = self.get_host_map_payload
        self.network_manager.host_client_state_restorer = self.host_restorer_callback
        self.network_manager.host_client_state_cacher = self.host_cacher_callback
        self.network_manager.client_restored_state_handler = self.apply_restored_state
        self.network_manager.host_damage_handler = self.handle_remote_damage
        self.network_manager.host_heal_handler = self.handle_remote_heal
        self.network_manager.host_respite_handler = self.handle_remote_respite
        
        self.cached_client_states = {} # {identity: state_dict}
        self.full_state_sync_timer = 0.0
        self.pending_remote_damage = [] # Thread-safe queue for TCP damage events
        self.pending_remote_heals = [] # Thread-safe queue for TCP heal events
        self.pending_remote_respite_actions = [] # Thread-safe queue for TCP respite events
        
        # Start searching for hosts if in Sanctuary
        if getattr(self.world, 'name', '') == "sanctuary":
            self.network_manager.start_searching()

    def get_local_state(self):
        """Phase 2 & 4: Returns the local player state for network sync."""
        if not self.player: return {"x": 0, "y": 0, "hp": 0}
        
        state = {
            "x": round(self.player.x, 1),
            "y": round(self.player.y, 1),
            "hp": round(self.player.hp, 1)
        }
        
        # Phase 4: Host Authority Sync
        if self.network_manager.network_mode == "HOST":
            state["weather"] = {
                "radius": round(self.weather_manager.active_safe_radius, 1),
                "state": self.weather_manager.bleed_state,
                "boss_idx": self.weather_manager.current_boss_idx
            }
            
            state["enemies"] = [
                {
                    "id": getattr(e, "network_id", -1),
                    "name": getattr(e, "name", "Enemy"),
                    "x": round(e.x, 1), "y": round(e.y, 1), "hp": round(e.hp, 1),
                    "state": e.state.value if hasattr(e, 'state') else 0
                }
                for e in self.enemies
            ]
            
            # Optimization: Only broadcast dynamic/crucial interactables in high-frequency heartbeat
            state["interactables"] = [obj.to_dict() for obj in self.world.interactables if obj.name == "Appendix Warp"]
            state["destroyed_props"] = list(self.destroyed_prop_ids)
            state["defeated_miniboss_ids"] = list(self.defeated_miniboss_ids)
            
            # Broadcast the Host's view of all remote players AND themselves (authoritative HP)
            state["session_players"] = [
                {"identity": self.network_manager.identity, "hp": self.player.hp, "x": self.player.x, "y": self.player.y}
            ]
            for p in self.network_manager.remote_players.values():
                state["session_players"].append(
                    {"identity": p["identity"], "hp": p["hp"], "x": p["x"], "y": p["y"]}
                )
            
        return state

    def apply_remote_state(self, addr, data):
        """Phase 2 & 4: Handles incoming remote player state data."""
        # Record remote player state for ghost rendering
        identity = data.get("identity", "Unknown")
        if identity == self.network_manager.identity:
            # This is our own data bouncing back
            pass
        else:
            # Rule: Host is authoritative for HP. 
            # If we are the Host, we only update remote player coordinates, not their HP.
            if self.network_manager.network_mode == "HOST":
                current = self.network_manager.remote_players.get(identity, {"hp": float(data.get("hp", 0))})
                self.network_manager.remote_players[identity] = {
                    "identity": identity,
                    "x": float(data.get("x", 0)),
                    "y": float(data.get("y", 0)),
                    "hp": current["hp"], # Authoritative Host-side HP
                    "time": time.time()
                }
            else:
                self.network_manager.remote_players[identity] = {
                    "identity": identity,
                    "x": float(data.get("x", 0)),
                    "y": float(data.get("y", 0)),
                    "hp": float(data.get("hp", 0)),
                    "time": time.time()
                }

        # Phase 4: Host-Authoritative Overrides (Client only)
        if self.network_manager.network_mode == "CLIENT":
            # 1. Weather
            w_data = data.get("weather")
            if w_data:
                self.weather_manager.active_safe_radius = float(w_data.get("radius", self.weather_manager.active_safe_radius))
                self.weather_manager.bleed_state = w_data.get("state", self.weather_manager.bleed_state)
                self.weather_manager.current_boss_idx = int(w_data.get("boss_idx", self.weather_manager.current_boss_idx))
            
            # 2. Session Players (Authoritative HP from Host)
            session_players = data.get("session_players", [])
            for p_info in session_players:
                p_identity = p_info.get("identity")
                # Update our own health if the host sent it
                if p_identity == self.network_manager.identity:
                    self.player.hp = float(p_info.get("hp", self.player.hp))
                else:
                    # Update other scholars for ghost rendering
                    self.network_manager.remote_players[p_identity] = {
                        "identity": p_identity,
                        "x": float(p_info.get("x", 0)),
                        "y": float(p_info.get("y", 0)),
                        "hp": float(p_info.get("hp", 0)),
                        "time": time.time()
                    }
            
            # 3. Enemies
            e_data_list = data.get("enemies", [])
            if e_data_list: self._sync_enemies_from_host(e_data_list)

            # 4. Interactables
            i_data_list = data.get("interactables", [])
            if i_data_list: self._sync_interactables_from_host(i_data_list)

            # 5. Props
            p_data = data.get("destroyed_props")
            if p_data: self._sync_props_from_host(p_data)

            # 6. Defeated Minibosses
            def_bosses = data.get("defeated_miniboss_ids")
            if def_bosses is not None:
                self.defeated_miniboss_ids = set(def_bosses)


    def _sync_enemies_from_host(self, enemy_data_list):
        remote_enemies = {int(e_data["id"]): e_data for e_data in enemy_data_list if "id" in e_data}
        local_net_ids = [getattr(e, 'network_id', -1) for e in self.enemies]
        
        # 1. Update/Remove existing
        for enemy in self.enemies[:]:
            net_id = getattr(enemy, "network_id", -1)
            if net_id in remote_enemies:
                e_data = remote_enemies[net_id]
                enemy.x = float(e_data.get("x", enemy.x))
                enemy.y = float(e_data.get("y", enemy.y))
                enemy.hp = float(e_data.get("hp", enemy.hp))
                
                # Sync visual state for animations
                if "state" in e_data:
                    from engine.actor import ActorState
                    try: enemy.state = ActorState(e_data["state"])
                    except ValueError: pass
            else:
                if enemy in self.enemies: self.enemies.remove(enemy)

        # 2. Spawn new ones
        for net_id, e_data in remote_enemies.items():
            if net_id not in local_net_ids:
                # We need to map Name back to Class.
                from engine.enemy import SlugEnemy, BatEnemy, NightBoss, MinibossM2, MinibossM3
                mapping = {
                    "Slug": SlugEnemy, "Bat": BatEnemy, "Night Boss": NightBoss,
                    "Ink-Stained": MinibossM2, "Forgotten Binder": MinibossM3
                }
                cls = mapping.get(e_data.get("name"), SlugEnemy)
                new_e = cls(e_data["x"], e_data["y"], hp=e_data["hp"])
                new_e.network_id = net_id
                self.enemies.append(new_e)

    def _sync_interactables_from_host(self, interactable_data_list):
        """Syncs dynamically spawned objects (Warp Portals, Chests)."""
        remote_objs = {obj_data["id"]: obj_data for obj_data in interactable_data_list}
        local_ids = [getattr(obj, 'id', id(obj)) for obj in self.world.interactables]
        
        # 1. Update/Remove
        for obj in self.world.interactables[:]:
            oid = getattr(obj, 'id', id(obj))
            if oid in remote_objs:
                o_data = remote_objs[oid]
                obj.x, obj.y = o_data["x"], o_data["y"]
                obj.health = o_data.get("hp", 100.0)
            else:
                # Rule: Only remove if it was likely a dynamic object or destroyed
                if obj.name in ("Appendix Warp", "Loot"):
                    self.world.interactables.remove(obj)

        # 2. Spawn New (Appendix Warp is the main one needed)
        for oid, o_data in remote_objs.items():
            if oid not in local_ids:
                if o_data["name"] == "Appendix Warp":
                    from engine.world import WarpPortal
                    new_obj = WarpPortal("final_boss", 25, 25, (o_data["x"], o_data["y"], 40, 40), name="Appendix Warp")
                    new_obj.id = oid
                    self.world.interactables.append(new_obj)

    def _sync_props_from_host(self, destroyed_ids_list):
        incoming_ids = set(destroyed_ids_list)
        # 1. Update our local set of destroyed IDs
        self.destroyed_prop_ids.update(incoming_ids)
        
        # 2. Reconcile world interactables: remove anything that is in the destroyed set
        for obj in self.world.interactables[:]:
            prop_id = getattr(obj, 'id', None)
            if prop_id and prop_id in self.destroyed_prop_ids:
                try:
                    self.world.interactables.remove(obj)
                    # Trigger a small fade VFX if it was just found
                    self.fading_entities.append({'obj': obj, 'time': 0.1})
                except ValueError: pass

    def fetch_host_map(self):
        if not self.network_manager.is_connected: return False
        map_json = self.network_manager.request_map()
        if map_json:
            import json
            from constants import get_generated_world_path
            path = get_generated_world_path().replace(".json", "_client.json")
            with open(path, 'w', encoding='utf-8') as f: json.dump(map_json, f)
            print(f"[NETWORK] Received map payload ({len(json.dumps(map_json)) // 1024} KB).")
            
            # Immediately load to set state.enemies etc
            from engine.world import World, LevelLoader
            # Rule: We bypass create_world("generated_world_client") to avoid recursive generative triggers in some contexts
            self.world = World("generated_world_client")
            grid, interactables, warp_tiles, player_start, enemies, boss_coords, module_sockets = LevelLoader.load_json_map(
                path,
                defeated_ids=self.defeated_miniboss_ids
            )
            self.world.grid = grid
            self.world.interactables = interactables
            self.world.warp_tiles = warp_tiles
            self.world.player_start = player_start
            self.world.enemies = enemies
            self.world.boss_coords_list = boss_coords
            self.world.module_sockets = module_sockets
            
            self.enemies = self.world.enemies
            return True
        return False

    def get_host_map_payload(self):
        from constants import get_generated_world_path
        import os, json
        path = get_generated_world_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        return None

    def host_restorer_callback(self, identity, ip): return self.cached_client_states.get(identity)
    def host_cacher_callback(self, identity, ip, data): self.cached_client_states[identity] = data

    def apply_restored_state(self, data):
        if not self.player or not data: return
        self.player.x = float(data.get("x", self.player.x))
        self.player.y = float(data.get("y", self.player.y))
        self.player.hp = float(data.get("hp", self.player.hp))
        self.player.flask_charges = int(data.get("flask_charges", self.player.flask_charges))
        self.player.active_weapon_idx = int(data.get("active_weapon_idx", self.player.active_weapon_idx))
        self.player.weapons = data.get("weapons", self.player.weapons)
        self.player.stats = data.get("stats", self.player.stats)
        if hasattr(self, 'camera'): self.camera.instant_center(self.player.get_center())

    def handle_remote_damage(self, target_type, target_id, amount):
        """Phase 4: Queues damage events sent by remote clients."""
        self.pending_remote_damage.append((target_type, target_id, amount))

    def handle_remote_heal(self, identity, amount):
        """Phase 4: Queues heal events sent by remote clients."""
        self.pending_remote_heals.append((identity, amount))

    def handle_remote_respite(self, identity, action_type, marked_idx, data):
        """Phase 4: Queues respite events (REST, UPGRADE) sent by remote clients."""
        self.pending_remote_respite_actions.append((identity, action_type, marked_idx, data))

    def get_full_player_state(self):
        if not self.player: return {}
        return {
            "x": self.player.x, "y": self.player.y, "hp": self.player.hp,
            "max_hp": self.player.max_hp, "flask_charges": self.player.flask_charges,
            "active_weapon_idx": self.player.active_weapon_idx,
            "weapons": self.player.weapons, "stats": self.player.stats
        }

    def update(self, dt, actions, audio_manager=None):
        """Update all game logic."""
        if self.player is None: return
        
        self.audio_manager = audio_manager
        attack_pressed = actions.get('attack', False)
        ratchet_reset = actions.get('ratchet_reset', False)
        self.inspect_active = actions.get('inspect', False)
        is_client = (self.network_manager.network_mode == "CLIENT")

        if is_client:
            self.full_state_sync_timer += dt
            if self.full_state_sync_timer >= 10.0:
                self.full_state_sync_timer = 0.0
                full_state = self.get_full_player_state()
                import threading
                threading.Thread(target=self.network_manager.send_full_state, args=(full_state,), daemon=True).start()

        if ratchet_reset: self.input_ratchet_latched = False
        if self.input_debounce_timer > 0: self.input_debounce_timer -= dt
        if self.menu_nav_cooldown > 0: self.menu_nav_cooldown -= dt

        # Dynamically update the is_active status of any gated respites in the world
        if self.world:
            for obj in self.world.interactables:
                if type(obj).__name__ == "Respite" and getattr(obj, 'gated_by_miniboss_id', None):
                    is_defeated = (obj.gated_by_miniboss_id in self.defeated_miniboss_ids)
                    if obj.is_active != is_defeated:
                        obj.is_active = is_defeated

        # 1. PRE-SYNC: Detection and State Management
        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        nearby = self.world.get_nearby_interactables(player_rect)
        self.player.current_interactable = nearby[0] if nearby else None

        # 2. INTERACTION PHASE
        target = self.player.current_interactable
        if attack_pressed and target and getattr(target, 'is_interactive', False) and not self.active_dialogue and not self.active_choice:
            target.execute_interaction(self)
            attack_pressed = False # Consume input
        
        # HUD Click Interactions
        self._handle_hud_interactions(actions)

        # 3. AI & COMBAT
        if not is_client:
            for enemy in self.enemies: enemy.update(dt, self)
            
            # --- Phase 1 & 4: Host World Events ---
            self._update_world_events(dt)
            
        self.weather_manager.update(dt, self.player, self.world, audio_manager=audio_manager)

        # Close Respite instantly if it is getting rained on
        if getattr(self, 'active_respite', None):
            rx = self.active_respite.x + self.active_respite.width / 2
            ry = self.active_respite.y + self.active_respite.height / 2
            if not self.weather_manager.is_pos_safe(rx, ry):
                self.active_respite = None
                self.active_dialogue = None
                self.respite_upgrades = {1: 0, 2: 0}
                self.respite_selection_idx = 0
                self.respite_marked_idx = -1
                self.player.has_rested_this_session = False
                print("[RESPITE] Closed instantly due to rain exposure.")

        self.update_combat(dt, attack_pressed, actions, audio_manager)

        # 4. SHARED SYSTEMS (Visuals, Movement, UI)
        self._update_shared_world(dt)
        
        # Rule: Movement is suppressed if a menu or dialogue is active
        if not self.active_dialogue and not getattr(self, 'active_choice', None):
            self._update_player_lifecycle(dt, actions, attack_pressed, audio_manager)
        else:
            # Freeze momentum while in menus
            self.player.vx = 0
            self.player.vy = 0
            self._update_audio_track(dt)
            
        self._update_ui_and_menus(dt, actions, attack_pressed, audio_manager)

        # 5. CAMERA & VIEWPORT
        if hasattr(self, 'camera') and self.player:
            self.camera.update(self.player.get_center(), dt)
        
        # 6. VFX DECAY
        if self.shake_timer > 0:
            self.shake_timer -= dt
            if self.shake_timer < 0: self.shake_timer = 0.0

    def _update_world_events(self, dt):
        """Host-only logic for boss spawns and environmental transitions."""
        from constants import TILE_SIZE, TILE_STRUCTURE, TILE_RESPITE
        # 0. Weather Damage to Remote Players
        if self.weather_manager.damage_enabled:
            for identity, p_data in self.network_manager.remote_players.items():
                # Estimate center
                px, py = p_data["x"] + 20, p_data["y"] + 20
                if not self.weather_manager.is_pos_safe(px, py):
                    # Check for shelter
                    tx, ty = int(px // TILE_SIZE), int(py // TILE_SIZE)
                    is_sheltered = False
                    if 0 <= ty < len(self.world.grid) and 0 <= tx < len(self.world.grid[0]):
                        if self.world.grid[ty][tx] in (TILE_STRUCTURE, TILE_RESPITE):
                            is_sheltered = True
                    
                    if not is_sheltered:
                        # Apply authoritative damage
                        p_data["hp"] = max(0.0, p_data["hp"] - (2.0 * dt))

        # 1. Boss Spawn Rule: Only if circle is closed (CLAMPED) and not already spawned
        if self.weather_manager.is_boss_spawn_ready():
            boss_alive = any(getattr(e, 'name', '') == "Night Boss" for e in self.enemies)
            if not boss_alive and self.weather_manager.bleed_state == "CLAMPED":
                from engine.enemy import NightBoss
                idx = self.weather_manager.current_boss_idx
                boss_list = getattr(self.world, 'boss_coords_list', [])
                if idx < len(boss_list):
                    coords = boss_list[idx]
                    from constants import TILE_SIZE
                    bx, by = coords['x'] * TILE_SIZE, coords['y'] * TILE_SIZE
                    new_boss = NightBoss(bx, by)
                    new_boss.network_id = 9000 + idx
                    self.enemies.append(new_boss)
                    print(f"[THE BLEED] Night Boss manifested at ({bx}, {by}).")
                    boss_alive = True
            self.weather_manager.lock_circle_for_boss(boss_alive)

        # Appendix Rule: Spawn portal after Night 2 defeat
        if self.weather_manager.bleed_state == "APPENDIX" and not any(e.name == "Appendix Warp" for e in self.world.interactables):
            idx = self.weather_manager.current_boss_idx
            boss_list = getattr(self.world, 'boss_coords_list', []) or []
            if idx < len(boss_list):
                coords = boss_list[idx]
                from engine.world import WarpPortal
                from constants import TILE_SIZE
                portal_rect = (coords['x'] * TILE_SIZE - 20, coords['y'] * TILE_SIZE - 20, 40, 40)
                portal = WarpPortal("final_boss", 25, 25, portal_rect, name="Appendix Warp")
                self.world.interactables.append(portal)
                self.trigger_bloom("THE APPENDIX REVEALED", priority=2)

    def update_combat(self, dt, attack_pressed, actions, audio_manager):
        """Phase 1: Handles player attacks and damage resolution."""
        if not self.player: return
        
        is_client = (self.network_manager.network_mode == "CLIENT")
        
        # 0. Process queued remote damage (Host Only)
        if not is_client and self.pending_remote_damage:
            for target_type, target_id, amount in self.pending_remote_damage:
                if target_type == "enemy":
                    for e in self.enemies:
                        if getattr(e, 'network_id', -1) == target_id:
                            e.take_damage(amount)
                            self.damage_numbers.append({'val': amount, 'pos': (e.x + 10, e.y - 20), 'time': 1.0, 'color': (255, 255, 0)})
                            break
                elif target_type == "prop":
                    for obj in list(self.world.interactables):
                        if getattr(obj, 'id', None) == target_id:
                            obj.take_damage(amount)
                            if obj.is_dead():
                                try:
                                    if hasattr(obj, 'id') and obj.id:
                                        self.destroyed_prop_ids.add(obj.id)
                                    self.world.interactables.remove(obj)
                                    self.fading_entities.append({'obj': obj, 'time': 0.16 if obj.name == "Barrel" else 0.1})
                                    from engine.loot import roll_drop
                                    roll_drop(4, (obj.x, obj.y), self)
                                except Exception: pass
                            break
            self.pending_remote_damage.clear()
            
        if not is_client and self.pending_remote_heals:
            for identity, amount in self.pending_remote_heals:
                if identity in self.network_manager.remote_players:
                    p_data = self.network_manager.remote_players[identity]
                    # Attempt to find max_hp in cached states
                    cached = self.cached_client_states.get(identity, {})
                    m_hp = float(cached.get("max_hp", 100.0))
                    p_data["hp"] = min(m_hp, p_data["hp"] + amount)
            self.pending_remote_heals.clear()
            
        if not is_client and self.pending_remote_respite_actions:
            for identity, action_type, marked_idx, data in self.pending_remote_respite_actions:
                from engine.world import Respite
                anchor = next((obj for obj in self.world.interactables if isinstance(obj, Respite)), None)
                
                if identity in self.network_manager.remote_players:
                    p_data = self.network_manager.remote_players[identity]
                    cached = self.cached_client_states.get(identity, {})
                    m_hp = float(data.get("max_hp", cached.get("max_hp", 100.0)))
                    
                    if action_type == "REST":
                        p_data["hp"] = m_hp
                        if anchor: anchor.execute_rest(self)
                    elif action_type == "UPGRADE":
                        p_data["hp"] = m_hp 
            self.pending_remote_respite_actions.clear()

        # 1. Local Attacks
        if self.player.state == PlayerStateEnum.ATTACKING:
            from engine.combat import get_sword_hitbox
            from engine.physics import check_aabb_collision
            hitbox = get_sword_hitbox(self.player.get_center(), self.player.facing)
            active_weapon = self.player.get_active_weapon()
            bonus_atk = getattr(self.player, 'stats', {}).get('attack_modifier', 0)
            from constants import SWORD_DAMAGE, HIT_STOP_DURATION, SCREEN_SHAKE_DURATION, DAMAGE_NUMBER_LIFETIME, COLOR_SELECTION
            damage = active_weapon.get("damage", SWORD_DAMAGE) + bonus_atk
            hit_landed = False

            # Enemies
            for enemy in list(self.enemies):
                try:
                    e_rect = enemy.get_rect()
                    net_id = getattr(enemy, 'network_id', id(enemy))
                    
                    if check_aabb_collision(hitbox, e_rect) and net_id not in self.player.hit_entities_this_attack:
                        # Rule: Hit once per attack swing
                        self.player.hit_entities_this_attack.add(net_id)
                        
                        enemy.take_damage(damage, bypass_stagger=is_client)
                        
                        # Apply anomalous weapon modifiers on hit
                        all_mods = self.player.get_all_modifiers()
                        if "bleed" in all_mods and enemy.hp > 0:
                            enemy.bleed_timer = 5.0
                            enemy.bleed_damage = all_mods["bleed"]
                            enemy.bleed_tick_timer = 1.0

                        hit_landed = True
                        if is_client:
                            self.network_manager.send_damage_event("enemy", net_id, damage)
                        self.hit_stop_timer = HIT_STOP_DURATION
                        self.shake_timer = SCREEN_SHAKE_DURATION
                        self.damage_numbers.append({
                            'val': damage, 'pos': (enemy.x + 10, enemy.y - 20),
                            'time': DAMAGE_NUMBER_LIFETIME, 'color': COLOR_SELECTION
                        })
                except Exception: pass

            # Props
            for obj in list(self.world.interactables):
                p_id = getattr(obj, 'id', id(obj))
                if getattr(obj, 'is_breakable', False) and check_aabb_collision(hitbox, obj.rect) and p_id not in self.player.hit_props_this_attack:
                    self.player.hit_props_this_attack.add(p_id)
                    
                    obj.take_damage(damage)
                    hit_landed = True
                    if is_client:
                        self.network_manager.send_damage_event("prop", p_id, damage)
                    
                    # Only the Host officially kills props and spawns loot. Clients wait for the UDP state sync to hide them.
                    if obj.is_dead() and not is_client:
                        try:
                            if hasattr(obj, 'id') and obj.id:
                                self.destroyed_prop_ids.add(obj.id)
                            self.world.interactables.remove(obj)
                            fade_time = 0.16 if obj.name == "Barrel" else 0.1
                            self.fading_entities.append({'obj': obj, 'time': fade_time})
                            if audio_manager: audio_manager.play_sfx("prop_break.ogg")
                            from engine.loot import roll_drop
                            roll_drop(4, (obj.x, obj.y), self)
                        except Exception: pass
            
            if hit_landed and audio_manager:
                audio_manager.play_sfx("attack_hit.ogg")

        # 2. Enemy Lifecycle (Death/Cleanup) - Host Only handles death logic
        if not is_client:
            for enemy in list(self.enemies):
                if enemy.is_dead():
                    try:
                        if getattr(enemy, 'is_miniboss', False) and getattr(enemy, 'id', None):
                            self.defeated_miniboss_ids.add(enemy.id)
                        if hasattr(enemy, 'on_death'): enemy.on_death(self)
                        self.enemies.remove(enemy)
                        if audio_manager: audio_manager.play_sfx("enemy_death.ogg")
                        from engine.loot import roll_drop
                        tier = getattr(enemy, 'loot_tier', 3)
                        roll_drop(tier, (enemy.x, enemy.y), self)
                    except Exception: pass

        from engine.physics import resolve_enemy_player_collision
        # Rule: Everyone resolves collision locally to prevent clipping.
        # But if we are a client, we don't push the enemies (we trust Host position).
        resolve_enemy_player_collision(self.player, self.enemies, allow_push_enemies=(not is_client))


    def _update_shared_world(self, dt):
        """Logic that runs on both Host and Client for visuals/vfx."""
        self.active_safe_radius = self.weather_manager.active_safe_radius
        self.bleed_state = self.weather_manager.bleed_state
        self.current_boss_coords = self.weather_manager.get_current_boss_coords()

        if self.weather_manager.pending_milestone_text:
            self.trigger_bloom(self.weather_manager.pending_milestone_text, priority=2)
            self.weather_manager.pending_milestone_text = None

        self.update_damage_numbers(dt)
        for fading in self.fading_entities[:]:
            fading['time'] -= dt
            if fading['time'] <= 0:
                if fading['obj'].name == "Barrel":
                    self.world_debris.append({'name': 'BarrelRubble', 'pos': (fading['obj'].x, fading['obj'].y)})
                self.fading_entities.remove(fading)

        for effect in self.parry_effects[:]:
            effect['time'] -= dt
            if effect['time'] <= 0: self.parry_effects.remove(effect)

    def _update_player_lifecycle(self, dt, actions, attack_pressed, audio_manager):
        if self.hit_stop_timer > 0:
            self.hit_stop_timer -= dt
            return
        
        # Check for death initiation
        if self.player.hp <= 0 and self.death_timer <= 0:
            self.death_timer = 2.0 # 2 seconds of death theme
            self.player.vx = 0
            self.player.vy = 0
            print("[GAME] Scholar has been redacted.")

        if self.death_timer > 0:
            self.death_timer -= dt
            self._update_audio_track(dt)
            if self.death_timer <= 0: self.respawn_player()
            return

        # Player Movement (Local)
        move_dir = actions.get('move', (0, 0))
        flask_pressed = actions.get('flask', False)
        dash_pressed = actions.get('dash', False)
        block_pressed = actions.get('block', False)
        swap_pressed = actions.get('swap', False)

        if swap_pressed:
            # Rule: Contextual Swap. If standing on a weapon, 'Swap' picks it up.
            target = self.player.current_interactable
            from engine.world import WeaponPickup
            if isinstance(target, WeaponPickup):
                target.execute_interaction(self)
            else:
                self.player.swap_weapon()
                
            if self.network_manager.network_mode == "CLIENT":
                full_state = self.get_full_player_state()
                threading.Thread(target=self.network_manager.send_full_state, args=(full_state,), daemon=True).start()

        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        walls = self.world.get_nearby_walls(player_rect)
        speed_multiplier = 1.0
        for obj in self.world.interactables:
            if obj.name == "Inkwell Puddle":
                if check_aabb_collision(player_rect, obj.rect):
                    speed_multiplier = 0.5
                    break
        
        healed = self.player.update(dt, move_dir, walls, actions, attack_pressed, flask_pressed, dash_pressed, block_pressed, speed_multiplier)
        if healed and self.network_manager.network_mode == "CLIENT":
            from constants import FLASK_HEAL_AMOUNT
            self.network_manager.send_heal_event(FLASK_HEAL_AMOUNT)

        self._update_audio_track(dt)
        self._handle_victory_conditions(dt)

    def _handle_hud_interactions(self, actions):
        """Phase 4: Handles mouse clicks on HUD elements."""
        click_pos = actions.get('mouse_click')
        if not click_pos: return
        
        from constants import (
            SCREEN_HEIGHT, HUD_PANEL_H, HUD_SWAP_BTN_RECT, HUD_PICKUP_BTN_RECT
        )
        
        # Calculate HUD base position (matches renderer.py)
        hx = 10
        hy = SCREEN_HEIGHT - HUD_PANEL_H - 10
        
        mx, my = click_pos
        
        # 1. Swap Button
        swr = HUD_SWAP_BTN_RECT
        if hx + swr[0] <= mx <= hx + swr[0] + swr[2] and hy + swr[1] <= my <= hy + swr[1] + swr[3]:
             self.player.swap_weapons()
             return
             
        # 2. Pickup Button
        pkr = HUD_PICKUP_BTN_RECT
        if hx + pkr[0] <= mx <= hx + pkr[0] + pkr[2] and hy + pkr[1] <= my <= hy + pkr[1] + pkr[3]:
             target = self.player.current_interactable
             if target and getattr(target, 'is_interactive', False):
                 target.execute_interaction(self)
             return

    def _update_ui_and_menus(self, dt, actions, attack_pressed, audio_manager):
        # Zone Discovery Bloom
        if getattr(self.world, 'name', '') not in ("", "sanctuary"):
            px, py = self.player.get_center()
            from constants import TILE_SIZE, BLOOM_COOLDOWN
            # Unit logic: 11x11 units of 40x40 tiles. Sub-rooms are indexed by (0, 4, 8)
            cur_unit_x, cur_unit_y = int(px // (TILE_SIZE * 40)), int(py // (TILE_SIZE * 40))
            
            current_room_id = None
            for ru_y in (0, 4, 8):
                for ru_x in (0, 4, 8):
                    if ru_x <= cur_unit_x < ru_x + 3 and ru_y <= cur_unit_y < ru_y + 3:
                        current_room_id = f"Room_{ru_x}_{ru_y}"
                        break
            
            if current_room_id and current_room_id != self.last_zone_id:
                if self.zone_cooldown_timer <= 0:
                    self.last_zone_id = current_room_id
                    self.zone_cooldown_timer = BLOOM_COOLDOWN
                    
                    # Search for a meaningful room name
                    zone_name = "THE UNKNOWN MARGIN"
                    for s in getattr(self.world, 'module_sockets', []):
                        # Fix: Check both 'name' and 'id' (world_generator uses 'name')
                        s_id = s.get('id') or s.get('name')
                        if s_id == current_room_id:
                            plug = s.get('active_plug', '').lower()
                            if 'forest' in plug: zone_name = "THE VERDANT SILENCE"
                            elif 'ruins' in plug: zone_name = "THE SCORCHED MARGIN"
                            elif 'colophon' in plug: zone_name = "THE COLOPHON"
                            elif 'boss' in plug: zone_name = "THE CROWN RING"
                            break
                    self.trigger_bloom(zone_name, priority=1)
        
        if self.zone_cooldown_timer > 0: self.zone_cooldown_timer -= dt
        if self.bloom_timer > 0: self.bloom_timer -= dt
        else: self.bloom_priority = 0

        # Sanctuary Management
        if getattr(self.world, 'name', '') == "sanctuary":
            if not self.sanctuary_reset_complete:
                self.on_enter_sanctuary()
                self.sanctuary_reset_complete = True
        else: self.sanctuary_reset_complete = False

        if self.active_dialogue: self._handle_dialogue_ui(actions, attack_pressed, audio_manager)
        elif getattr(self, 'active_choice', None): self._handle_choice_ui(actions, attack_pressed)
        
        # Pickup Logic
        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        nearby = self.world.get_nearby_interactables(player_rect)
        self.player.current_interactable = nearby[0] if nearby else None
        
        for item in self.loot[:]:
            if check_aabb_collision(player_rect, item.get_rect()):
                item.execute_pickup(self)
                self.loot.remove(item)
                if audio_manager: audio_manager.play_sfx("page_pickup.ogg")

    def _handle_dialogue_ui(self, actions, attack_pressed, audio_manager):
        active_respite = getattr(self, 'active_respite', None)
        if attack_pressed and not active_respite:
            self.active_dialogue = None
            self.input_debounce_timer = 0.2
            self.save_stats(wait=True)
            return
        if active_respite:
            move_dir = actions.get('move', (0, 0))
            if not self.input_ratchet_latched and self.menu_nav_cooldown <= 0:
                if move_dir[1] > 0.6:
                    self.respite_selection_idx = self._get_next_respite_idx(self.respite_selection_idx)
                    self.input_ratchet_latched = True
                    self.menu_nav_cooldown = 0.2
                elif move_dir[1] < -0.6:
                    self.respite_selection_idx = self._get_prev_respite_idx(self.respite_selection_idx)
                    self.input_ratchet_latched = True
                    self.menu_nav_cooldown = 0.2
            if attack_pressed and not self.input_ratchet_latched:
                self.input_ratchet_latched = True
                if self.respite_selection_idx == 0:
                    active_respite.execute_rest(self, audio_manager=audio_manager)
                elif 1 <= self.respite_selection_idx <= 2 and self.player.has_rested_this_session:
                    info = self.get_staged_respite_info()
                    pages = self.stats.data["lifetime_stats"].get("pages_collected", 0) if self.stats else 0
                    available = pages - info["total_staged_cost"]
                    if self.respite_selection_idx == 1:
                        if available >= info["next_prowess_cost"]:
                            self.respite_upgrades[1] += 1
                            if audio_manager:
                                audio_manager.play_sfx("menu_confirm.ogg")
                    elif self.respite_selection_idx == 2:
                        if available >= info["next_fort_cost"]:
                            self.respite_upgrades[2] += 1
                            if audio_manager:
                                audio_manager.play_sfx("menu_confirm.ogg")
                elif self.respite_selection_idx == 4:
                    success = active_respite.execute_finalize_upgrades(self, audio_manager=audio_manager)
                    if success:
                        self.player.has_rested_this_session = False
                        self.respite_selection_idx = 5
                elif self.respite_selection_idx == 5:
                    self.active_dialogue = self.active_respite = None
                    self.player.has_rested_this_session = False
                    self.respite_upgrades = {1: 0, 2: 0}
                    if self.network_manager.network_mode == "CLIENT":
                        threading.Thread(target=self.network_manager.send_full_state, args=(self.get_full_player_state(),), daemon=True).start()
                    self.save_stats(wait=True)

    def _get_next_respite_idx(self, current_idx):
        """Helper to find the next valid Respite menu index."""
        idx = (current_idx + 1) % 6
        has_rested = self.player.has_rested_this_session
        # Skip rules:
        # 1. Skip 1, 2, 3 if not rested
        # 2. Always skip 3 (unused)
        while True:
            if idx == 3: idx = (idx + 1) % 6; continue
            if not has_rested and (1 <= idx <= 3): idx = (idx + 1) % 6; continue
            break
        return idx

    def _get_prev_respite_idx(self, current_idx):
        """Helper to find the previous valid Respite menu index."""
        idx = (current_idx - 1) % 6
        has_rested = self.player.has_rested_this_session
        while True:
            if idx == 3: idx = (idx - 1) % 6; continue
            if not has_rested and (1 <= idx <= 3): idx = (idx - 1) % 6; continue
            break
        return idx

    def _handle_choice_ui(self, actions, attack_pressed):
        move_dir = actions.get('move', (0, 0))
        if not self.input_ratchet_latched and self.menu_nav_cooldown <= 0:
            if move_dir[0] > 0.5: self.active_choice["selected_index"] = 1; self.input_ratchet_latched = True; self.menu_nav_cooldown = 0.2
            elif move_dir[0] < -0.5: self.active_choice["selected_index"] = 0; self.input_ratchet_latched = True; self.menu_nav_cooldown = 0.2
        if attack_pressed:
            choice = self.active_choice["options"][self.active_choice["selected_index"]]
            for s, v in choice["modifiers"].items(): self.player.stats[s] = self.player.stats.get(s, 0) + v
            self.active_choice = None
            if self.network_manager.network_mode == "CLIENT":
                threading.Thread(target=self.network_manager.send_full_state, args=(self.get_full_player_state(),), daemon=True).start()

    def _handle_victory_conditions(self, dt):
        if getattr(self.world, 'name', '') != "final_boss":
            return

        final_boss_dead = not any(getattr(e, 'name', '') == "The Final Author" for e in self.enemies)
        if final_boss_dead and getattr(self.stats, 'data', {}).get("last_run_result") != "VICTORY":
            if self.stats:
                self.stats.data["last_run_result"] = "VICTORY"
                self.stats.increment("wins_chapters_cleared", 1)
                self.weather_manager.trigger_dilution()
                self.trigger_bloom("CHAPTER COMPLETE", priority=2)
        if getattr(self.stats, 'data', {}).get("last_run_result") == "VICTORY":
            if (self.bleed_state in ("DILUTION", "APPENDIX")) and self.weather_manager.timer <= 0:
                from engine.world import WarpPortal
                WarpPortal("sanctuary", 0, 0, (0, 0, 0, 0)).execute_interaction(self)

    def on_enter_sanctuary(self):
        """Rule: Absolute state purification upon entering the Sanctuary hub."""
        from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES, SWORD_DAMAGE
        self.player.is_exposed = False
        self.player.hp = float(self.player.max_hp)
        self.player.flask_charges = int(FLASK_MAX_CHARGES)
        
        # Network Rule: If we just returned from a draft (world), clear session.
        # But if we just joined from the lobby (is_connected), keep it!
        if hasattr(self, 'network_manager'):
            mode = self.network_manager.network_mode
            if mode in ("HOST", "CLIENT"):
                # Only stop if we weren't already in the hub or just connected
                # Check active_session_in_progress as a proxy for "was in a run"
                if self.stats and self.stats.data.get("active_session_in_progress"):
                    self.network_manager.stop_network()
                    self.network_manager.start_searching()
            elif mode == "OFFLINE":
                self.network_manager.start_searching()
        
        self.player.weapons = [{"name": "Initial Quill", "damage": SWORD_DAMAGE}]
        self.player.active_weapon_idx = 0
        
        # Purification: Clear run state and persistent world changes when entering Hub
        self.world_debris = []
        self.destroyed_prop_ids.clear()

        if self.stats:
            self.stats.data["run_state"] = None
            self.stats.data["active_session_in_progress"] = False

        # Weather Reset: Full system restore for hub safety
        if hasattr(self, 'weather_manager'):
            self.weather_manager.reset(boss_coords_list=None)
            
        self.sanctuary_reset_complete = True
        self.save_stats(wait=True)

    def on_network_disconnect(self):
        print("[NETWORK] Connection lost. Warping to Sanctuary.")
        self.trigger_bloom("CONNECTION LOST", priority=2)
        from engine.maps import create_world
        self.world = create_world("sanctuary")
        # Phase 4: Sync camera bounds
        if hasattr(self, 'camera'):
            self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
            self.camera.world_h = len(self.world.grid) * TILE_SIZE
            self.camera.instant_center(self.player.get_center())
        
        self.on_enter_sanctuary()
        self.respawn_player()

    def deallocate(self):
        self.player = self.world = None
        self.enemies = self.loot = self.world_debris = []
        self.destroyed_prop_ids = set()
        self.active_dialogue = self.active_choice = self.active_respite = None

    def trigger_bloom(self, text, priority=1):
        if priority >= self.bloom_priority or self.bloom_timer <= 0:
            from constants import BLOOM_TOTAL_DURATION
            self.bloom_text = text
            self.bloom_timer = BLOOM_TOTAL_DURATION
            self.bloom_priority = priority

    def hydrate_from_disk(self):
        """Phase 2: Hydrate runtime objects from StatisticsTracker.data['run_state']."""
        from engine.stats import StatisticsTracker
        from engine.maps import create_world
        
        # Priority: If we already have stats with a run, use it. Otherwise load from disk.
        if not self.stats or not self.stats.data.get("run_state"):
            try: self.stats = StatisticsTracker.load()
            except Exception: self.stats = StatisticsTracker()
        
        # Update Network Identity from loaded stats
        if self.stats and hasattr(self, 'network_manager'):
            self.network_manager.identity = self.stats.data.get("player_name", self.network_manager.identity)

        run_data = self.stats.data.get("run_state")
        if run_data:
            world_name = run_data.get("world_name", "sanctuary")
            self.world_debris = run_data.get("world_debris", [])
            self.defeated_miniboss_ids = set(run_data.get("defeated_miniboss_ids", []))
            self.destroyed_prop_ids = set(run_data.get("destroyed_prop_ids", []))
            self.world = create_world(world_name, saved_enemies=run_data.get("enemies", []), defeated_ids=self.defeated_miniboss_ids, destroyed_ids=self.destroyed_prop_ids)
            
            p_data = run_data.get("player", {})
            self.player = Player(float(p_data.get("x", self.world.player_start[0])), float(p_data.get("y", self.world.player_start[1])))
            
            # Phase 4: Sync camera bounds
            if hasattr(self, 'camera'):
                self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
                self.camera.world_h = len(self.world.grid) * TILE_SIZE
                self.camera.instant_center(self.player.get_center())
            
            self.player.hp = float(p_data.get("hp", PLAYER_MAX_HP))
            self.player.flask_charges = int(p_data.get("flask_charges", FLASK_MAX_CHARGES))
            self.player.active_weapon_idx = int(p_data.get("active_weapon_idx", 0))
            self.player.weapons = p_data.get("weapons", self.player.weapons)
            self.player.stats = p_data.get("stats", {})
            self.enemies = getattr(self.world, 'enemies', [])
            from engine.weather import WeatherManager
            self.weather_manager = WeatherManager(boss_coords_list=getattr(self.world, 'boss_coords_list', None))
            self.weather_manager.from_dict(run_data.get("weather"))
            
            self.input_ratchet_latched = False
            self.menu_nav_cooldown = 0.0
            
            self.active_dialogue = None
            self.active_choice = None
            self.active_respite = None
            
            # Auto-Host Rule: Start hosting if resuming outside Sanctuary
            if world_name not in ("sanctuary", ""):
                if hasattr(self, 'network_manager'):
                    if self.network_manager.network_mode == "OFFLINE":
                        self.network_manager.start_hosting()
        else:
            # Fallback for empty run_state: reset to sanctuary
            self.reset_to_new_game()

    def reset_to_new_game(self):
        from engine.maps import create_world
        if self.stats:
            self.stats.data["lifetime_stats"]["pages_collected"] = 0
            self.stats.data["run_state"] = None
            self.stats.data["active_session_in_progress"] = False
            self.stats.data["last_run_result"] = "INIT"
            try: self.stats.increment("runs_started", 1)
            except Exception: pass
        self.defeated_miniboss_ids = set()
        self.world = create_world("sanctuary", defeated_ids=self.defeated_miniboss_ids)
        
        self.player = Player(self.world.player_start[0], self.world.player_start[1])
        
        # Phase 4: Sync camera bounds
        if hasattr(self, 'camera'):
            self.camera.world_w = len(self.world.grid[0]) * TILE_SIZE
            self.camera.world_h = len(self.world.grid) * TILE_SIZE
            self.camera.instant_center(self.player.get_center())
        
        self.world_debris = []
        self.player.stats = {"attack_modifier": 0, "max_hp_modifier": 0, "edification": 1}
        self.input_ratchet_latched = False
        self.menu_nav_cooldown = 0.0
        from engine.weather import WeatherManager
        self.weather_manager = WeatherManager(boss_coords_list=getattr(self.world, 'boss_coords_list', None))
        self.loot = []
        self.damage_numbers = []
        self.active_dialogue = None
        self.active_choice = None
        self.active_respite = None
        from engine.world import LevelLoader
        LevelLoader.link_actors_to_routes(self)

    def get_full_run_state(self):
        """Serializes the complete current world and player state for persistence."""
        if not self.world or not self.player: return None
        return {
            "world_name": getattr(self.world, 'name', 'macro_world'),
            "world_debris": self.world_debris,
            "defeated_miniboss_ids": list(self.defeated_miniboss_ids),
            "destroyed_prop_ids": list(self.destroyed_prop_ids),
            "enemies": [e.to_dict() for e in self.enemies],
            "player": self.get_full_player_state(),
            "weather": self.weather_manager.to_dict() if hasattr(self, 'weather_manager') else None
        }

    def save_stats(self, path: Optional[str] = None, wait: bool = False) -> None:
        if self.stats is None or not getattr(self, '_save_worker_running', False): return
        if self.player is None or self.world is None: return # Guard against deallocated state
        
        # --- Persistence: Sanctuary is the hub; runs are completed/redacted here ---
        world_name = getattr(self.world, 'name', 'sanctuary')
        if world_name not in ("sanctuary", "") and self.player:
            self.stats.data["run_state"] = self.get_full_run_state()
            self.stats.data["active_session_in_progress"] = True
        else:
            self.stats.data["run_state"] = None
            self.stats.data["active_session_in_progress"] = False

        try: self._save_queue.put_nowait({"stats": self.stats.data, "path": path})
        except queue.Full: pass
        if wait: self._save_queue.join()

    def _save_worker(self):
        while self._save_worker_running:
            item = self._save_queue.get()
            if item is None: self._save_queue.task_done(); break
            try:
                self.saving_in_progress = True
                from engine.stats import StatisticsTracker
                temp_stats = StatisticsTracker()
                temp_stats.data = item["stats"]
                temp_stats.save(item["path"])
                self.saving_in_progress = False
            except Exception: pass
            finally: self._save_queue.task_done()

    def shutdown_save_worker(self, timeout: float = 2.0) -> None:
        self._save_worker_running = False
        try: self._save_queue.put_nowait(None); self._save_worker_thread.join(timeout)
        except Exception: pass

    def trigger_choice_of_fates(self):
        level_scale = 1
        if self.stats:
            try: level_scale = 1 + (self.stats.data["lifetime_stats"].get("pages_collected", 0) // 100)
            except Exception: pass
        base_x = 5 * level_scale
        minor_y = int(base_x * 0.25)
        self.active_choice = {
            "title": "The Choice of Fates",
            "options": [
                {"name": "The Quill", "bias": "Offense", "modifiers": {"attack_modifier": base_x, "max_hp_modifier": minor_y}, "description": f"+{base_x} Attack, +{minor_y} Max HP"},
                {"name": "The Binding", "bias": "Defense", "modifiers": {"max_hp_modifier": base_x, "attack_modifier": minor_y}, "description": f"+{base_x} Max HP, +{minor_y} Attack"}
            ],
            "selected_index": 0
        }
        self.input_debounce_timer = 0.3

    def update_damage_numbers(self, dt):
        from constants import DAMAGE_NUMBER_SPEED
        for num in self.damage_numbers[:]:
            num['time'] -= dt
            x, y = num['pos']
            num['pos'] = (x, y - DAMAGE_NUMBER_SPEED * dt)
            if num['time'] <= 0: self.damage_numbers.remove(num)

    def _update_audio_track(self, dt):
        world_name = getattr(self.world, 'name', 'sanctuary')
        target_track = "world_exploration.ogg"
        if world_name == "sanctuary": target_track = "sanctuary_hub.ogg"
        if getattr(self.stats, 'data', {}).get("last_run_result") == "VICTORY" and world_name == "final_boss": self.player.active_track_name = "victory_theme.ogg"; return
        if self.player.hp <= 0: self.player.active_track_name = "death_theme.ogg"; return
        proximity_threshold = 15 * TILE_SIZE
        cooldown_limit = 3.0
        near_miniboss = near_night_boss = near_final_author = False
        px, py = self.player.get_center()
        for enemy in self.enemies:
            if getattr(enemy, 'is_miniboss', False):
                ex, ey = enemy.get_center()
                if (px - ex)**2 + (py - ey)**2 <= proximity_threshold**2:
                    ename = getattr(enemy, 'name', '')
                    if ename == "The Final Author": near_final_author = True
                    elif ename == "Night Boss": near_night_boss = True
                    else: near_miniboss = True
                    break
        current_active = self.player.active_track_name
        combat_tracks = ("miniboss_combat.ogg", "night_boss.ogg", "final_reckoning.ogg")
        if near_final_author: self.player.active_track_name = "final_reckoning.ogg"; self.player.miniboss_cooldown_accumulator = 0.0
        elif near_night_boss: self.player.active_track_name = "night_boss.ogg"; self.player.miniboss_cooldown_accumulator = 0.0
        elif near_miniboss: self.player.active_track_name = "miniboss_combat.ogg"; self.player.miniboss_cooldown_accumulator = 0.0
        elif current_active in combat_tracks:
            self.player.miniboss_cooldown_accumulator += dt
            if self.player.miniboss_cooldown_accumulator >= cooldown_limit: self.player.active_track_name = target_track
        else: self.player.active_track_name = target_track

    def get_staged_respite_info(self):
        """Calculate levels, staged counts, next costs, and total costs for respite upgrades."""
        from constants import EDIFICATION_BASE_COST, EDIFICATION_COST_SCALE
        
        # 1. Prowess (Attack modifier, steps of 5)
        prowess = self.player.stats.get("attack_modifier", 0)
        prowess_lvl = 1 + (prowess // 5)
        staged_prowess = self.respite_upgrades.get(1, 0)
        
        prowess_staged_cost = 0
        for i in range(staged_prowess):
            lvl = prowess_lvl + i
            prowess_staged_cost += EDIFICATION_BASE_COST + ((lvl - 1) * EDIFICATION_COST_SCALE)
            
        next_prowess_lvl = prowess_lvl + staged_prowess
        next_prowess_cost = EDIFICATION_BASE_COST + ((next_prowess_lvl - 1) * EDIFICATION_COST_SCALE)
        
        # 2. Fortification (HP modifier, steps of 10)
        fort = self.player.stats.get("max_hp_modifier", 0)
        fort_lvl = 1 + (fort // 10)
        staged_fort = self.respite_upgrades.get(2, 0)
        
        fort_staged_cost = 0
        for i in range(staged_fort):
            lvl = fort_lvl + i
            fort_staged_cost += EDIFICATION_BASE_COST + ((lvl - 1) * EDIFICATION_COST_SCALE)
            
        next_fort_lvl = fort_lvl + staged_fort
        next_fort_cost = EDIFICATION_BASE_COST + ((next_fort_lvl - 1) * EDIFICATION_COST_SCALE)
        
        total_staged_cost = prowess_staged_cost + fort_staged_cost
        
        return {
            "prowess_lvl": prowess_lvl,
            "staged_prowess": staged_prowess,
            "next_prowess_cost": next_prowess_cost,
            "fort_lvl": fort_lvl,
            "staged_fort": staged_fort,
            "next_fort_cost": next_fort_cost,
            "total_staged_cost": total_staged_cost
        }

    def _handle_upgrade(self, stat_name, amount):
        from constants import EDIFICATION_BASE_COST, EDIFICATION_COST_SCALE
        current_val = self.player.stats.get(stat_name, 0)
        
        # Calculate current 1-based level
        current_level = 1 + (current_val // amount) if amount > 0 else 1
        
        # Correct Formula: Base + ((Level - 1) * Scale)
        cost = EDIFICATION_BASE_COST + ((current_level - 1) * EDIFICATION_COST_SCALE)
        
        pages = self.stats.data["lifetime_stats"].get("pages_collected", 0)
        if pages >= cost:
            self.stats.data["lifetime_stats"]["pages_collected"] -= cost
            self.player.stats[stat_name] = current_val + amount
            
            if stat_name == "max_hp_modifier":
                self.player.hp = self.player.max_hp
            
            # Recalculate Global Edification Level
            prowess = self.player.stats.get("attack_modifier", 0)
            fort = self.player.stats.get("max_hp_modifier", 0)
            self.player.stats["edification"] = (prowess // 5) + (fort // 10) + 1

            # Sync to persistent stats for UI parity
            if self.stats:
                if "run_state" in self.stats.data and self.stats.data["run_state"]:
                    self.stats.data["run_state"]["player"]["stats"] = self.player.stats

            self.player.has_rested_this_session = False
            if getattr(self, 'active_respite', None): self.active_respite.execute_interaction(self)
            return True
        return False

    def respawn_player(self):
        from engine.maps import create_world
        if self.stats: self.stats.data["last_run_result"] = "DEFEAT"
        self.world = create_world("sanctuary", defeated_ids=self.defeated_miniboss_ids)
        
        # Reset local player fully
        self.player.x, self.player.y = float(self.world.player_start[0]), float(self.world.player_start[1])
        self.player.hp = self.player.max_hp
        self.player.state = PlayerStateEnum.IDLE
        self.death_timer = 0.0
        
        if hasattr(self, 'camera'): self.camera.instant_center(self.player.get_center())
        self.on_enter_sanctuary()
        self.enemies, self.loot = [], []
        self.save_stats(wait=True)
