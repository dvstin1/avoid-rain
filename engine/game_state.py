"""
Manages the global game state and coordinates engine components.
"""
from typing import Optional
import queue
import threading

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
        # 1. Initialize core components with defaults
        from engine.maps import create_world
        from engine.world import LevelLoader
        self.destroyed_prop_ids = set()
        self.world = create_world("sanctuary", destroyed_ids=self.destroyed_prop_ids)
        self.player = Player(self.world.player_start[0], self.world.player_start[1])
        self.enemies = []

        # 2. Statistics tracker: prefer injected tracker; otherwise optionally auto-load
        self.stats = stats
        if self.stats is None and auto_load:
            try:
                if stats_path is not None:
                    self.stats = StatisticsTracker.load(stats_path)
                else:
                    self.stats = StatisticsTracker.load()
            except Exception as exc:
                from engine.stats import CorruptSaveError
                if isinstance(exc, CorruptSaveError):
                    self.stats = None
                    self.stats_corrupt = True
                    try:
                        self.stats_corrupt_backup = exc.backup_path
                    except Exception:
                        self.stats_corrupt_backup = None
                else:
                    self.stats = None

        # 3. Apply persistent run state if available
        if self.stats is not None and self.stats.data.get("run_state"):
            run_data = self.stats.data["run_state"]
            try:
                # Restore World
                from engine.maps import create_world
                world_name = run_data.get("world_name", "sanctuary")
                saved_enemies = run_data.get("enemies", [])
                self.world_debris = run_data.get("world_debris", [])
                self.defeated_miniboss_ids = set(run_data.get("defeated_miniboss_ids", []))
                self.destroyed_prop_ids = set(run_data.get("destroyed_prop_ids", []))
                self.world = create_world(world_name, saved_enemies=saved_enemies, 
                                          defeated_ids=self.defeated_miniboss_ids,
                                          destroyed_ids=self.destroyed_prop_ids)

                # Restore Player
                p_data = run_data.get("player", {})
                self.player.x = float(p_data.get("x", PLAYER_START_X))
                self.player.y = float(p_data.get("y", PLAYER_START_Y))
                self.player.hp = float(p_data.get("hp", PLAYER_MAX_HP))
                self.player.flask_charges = int(p_data.get("flask_charges", FLASK_MAX_CHARGES))
                self.player.active_weapon_idx = int(p_data.get("active_weapon_idx", 0))
                self.player.weapons = p_data.get("weapons", self.player.weapons)
                self.player.stats = p_data.get("stats", {})
                self.defeated_miniboss_ids = set(run_data.get("defeated_miniboss_ids", []))

                # Restore Enemies
                self.enemies = getattr(self.world, 'enemies', [])
                
                # Weather System Restoration
                from engine.weather import WeatherManager
                boss_list = getattr(self.world, 'boss_coords_list', None)
                self.weather_manager = WeatherManager(boss_coords_list=boss_list)
                self.weather_manager.from_dict(run_data.get("weather"))
            except Exception:
                pass
        else:
            self.enemies = getattr(self.world, 'enemies', [])
            from engine.weather import WeatherManager
            boss_list = getattr(self.world, 'boss_coords_list', None)
            self.weather_manager = WeatherManager(boss_coords_list=boss_list)

        world_w = GRID_WIDTH * TILE_SIZE
        world_h = GRID_HEIGHT * TILE_SIZE
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, world_w, world_h, lerp_speed=CAMERA_LERP_SPEED)
        self.camera.instant_center(self.player.get_center())

        if self.stats is not None and self.stats.data.get("run_state") is None:
            try:
                self.stats.increment("runs_started", 1)
            except KeyError:
                pass

        self.active_dialogue = None
        self.dialogue_mode = "STANDARD"
        self.damage_numbers = []
        self.parry_effects = [] # List of {'pos': (x,y), 'time': float}
        self.world_debris = [] # List of {'name': str, 'pos': (x,y)} - Persistent, no collision
        self.loot = []
        self.fading_entities = []
        self.death_timer = 0.0
        self.shake_timer = 0.0
        self.hit_stop_timer = 0.0
        self.last_save_elapsed = 1e6
        self.objectives = []
        self.input_debounce_timer = 0.0
        self.input_ratchet_latched = False
        self.menu_nav_cooldown = 0.0
        self.defeated_miniboss_ids = set()
        self.destroyed_prop_ids = set() # Track destroyed barrels/breakables
        self.sanctuary_reset_complete = False

        # Typographic Bloom State
        self.bloom_timer = 0.0
        self.bloom_text = ""
        self.bloom_priority = 0 # 0=None, 1=Discovery, 2=Milestone/Alert
        self.last_zone_id = None
        self.zone_cooldown_timer = 0.0

        # Input Mode State (Keyboard/Gamepad)
        from constants import INPUT_MODE_KEYBOARD
        self.input_mode = INPUT_MODE_KEYBOARD
        self.respite_selection_idx = 0 # 0=Rest, 1-3=Edify, 4=Finalize, 5=Close
        self.respite_marked_idx = -1 # Which one is staged for upgrade

        self._save_queue = queue.Queue(maxsize=8)
        self._save_worker_running = True
        self.saving_in_progress = False
        self._save_worker_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._save_worker_thread.start()

        # Link actors to routes after everything is loaded
        LevelLoader.link_actors_to_routes(self)

        # Network Phase 2: Manager Initialization
        from engine.network_manager import NetworkManager
        self.network_manager = NetworkManager()
        self.network_manager.local_state_provider = self.get_local_state
        self.network_manager.remote_state_handler = self.apply_remote_state
        self.network_manager.on_disconnect_callback = self.on_network_disconnect
        
        # Start searching for hosts if in Sanctuary
        if getattr(self.world, 'name', '') == "sanctuary":
            self.network_manager.start_searching()

    def get_local_state(self):
        """Phase 2: Returns the local player state for network sync."""
        if not self.player: return {"x": 0, "y": 0, "hp": 0}
        return {
            "x": self.player.x,
            "y": self.player.y,
            "hp": self.player.hp
        }

    def apply_remote_state(self, addr, data):
        """Phase 2: Handles incoming remote player state data."""
        # For Phase 2, the NetworkManager already stores this in self.remote_players.
        pass

    def on_network_disconnect(self):
        """Handles connection loss by warping to Sanctuary."""
        print("[NETWORK] Connection lost. Warping to Sanctuary.")
        self.trigger_bloom("CONNECTION LOST", priority=2)
        # Execute emergency Sanctuary warp
        from engine.maps import create_world
        self.world = create_world("sanctuary")
        self.on_enter_sanctuary()
        self.respawn_player()

    def deallocate(self):
        """Purge all runtime gameplay memory."""
        self.player = None
        self.world = None
        self.enemies = []
        self.loot = []
        self.fading_entities = []
        self.world_debris = []
        self.destroyed_prop_ids = set()
        self.active_dialogue = None

    def trigger_bloom(self, text, priority=1):
        """Display a cinematic typographic alert if priority allows."""
        if priority >= self.bloom_priority or self.bloom_timer <= 0:
            from constants import BLOOM_TOTAL_DURATION
            self.bloom_text = text
            self.bloom_timer = BLOOM_TOTAL_DURATION
            self.bloom_priority = priority

    def hydrate_from_disk(self):
        """Reload state exclusively from the persistent disk file."""
        from engine.stats import StatisticsTracker
        from engine.maps import create_world
        try:
            self.stats = StatisticsTracker.load()
        except Exception:
            self.stats = StatisticsTracker()

        run_data = self.stats.data.get("run_state")
        if run_data:
            world_name = run_data.get("world_name", "sanctuary")
            saved_enemies = run_data.get("enemies", [])
            self.world_debris = run_data.get("world_debris", [])
            self.defeated_miniboss_ids = set(run_data.get("defeated_miniboss_ids", []))
            self.destroyed_prop_ids = set(run_data.get("destroyed_prop_ids", []))
            
            self.world = create_world(world_name, saved_enemies=saved_enemies, 
                                      defeated_ids=self.defeated_miniboss_ids,
                                      destroyed_ids=self.destroyed_prop_ids)
            
            p_data = run_data.get("player", {})
            spawn_x = float(p_data.get("x", self.world.player_start[0]))
            spawn_y = float(p_data.get("y", self.world.player_start[1]))
            self.player = Player(spawn_x, spawn_y)
            self.player.hp = float(p_data.get("hp", PLAYER_MAX_HP))
            self.player.flask_charges = int(p_data.get("flask_charges", FLASK_MAX_CHARGES))
            self.player.active_weapon_idx = int(p_data.get("active_weapon_idx", 0))
            self.player.weapons = p_data.get("weapons", self.player.weapons)
            self.player.stats = p_data.get("stats", {})
            self.defeated_miniboss_ids = set(run_data.get("defeated_miniboss_ids", []))
            self.enemies = getattr(self.world, 'enemies', [])

            # Restore Weather
            from engine.weather import WeatherManager
            boss_list = getattr(self.world, 'boss_coords_list', None)
            self.weather_manager = WeatherManager(boss_coords_list=boss_list)
            self.weather_manager.from_dict(run_data.get("weather"))
            
            # Finalization Pass: Link Actors to Routes
            from engine.world import LevelLoader
            LevelLoader.link_actors_to_routes(self)
        else:
            self.world = create_world("sanctuary")
            self.player = Player(self.world.player_start[0], self.world.player_start[1])
            self.enemies = getattr(self.world, 'enemies', [])
            from engine.weather import WeatherManager
            self.weather_manager = WeatherManager(boss_coords_list=None)
            
            from engine.world import LevelLoader
            LevelLoader.link_actors_to_routes(self)

        self.loot = []
        self.fading_entities = []
        self.active_dialogue = None
        self.death_timer = 0.0
        self.damage_numbers = []
        if hasattr(self, 'camera'):
            self.camera.instant_center(self.player.get_center())

    def reset_to_new_game(self):
        """Reset gameplay-affecting state to start-of-game defaults, preserving meta-statistics."""
        from engine.maps import create_world
        
        # 1. Reset Statistics (Only gameplay-affecting fields)
        if self.stats:
            # KEEP: runs_started, wins_chapters_cleared, bestiary, etc.
            # RESET: Banked pages and active run state
            self.stats.data["lifetime_stats"]["pages_collected"] = 0
            self.stats.data["run_state"] = None
            self.stats.data["active_session_in_progress"] = False
            self.stats.data["last_run_result"] = "INIT"
            try:
                self.stats.increment("runs_started", 1)
            except Exception: pass

        # 2. Reset World & Player
        self.defeated_miniboss_ids = set()
        self.world = create_world("sanctuary", defeated_ids=self.defeated_miniboss_ids)
        
        # Fresh player with default starting stats (Edification resets to 1)
        self.player = Player(self.world.player_start[0], self.world.player_start[1])
        self.world_debris = []
        self.player.stats = {
            "edification": 1,
            "attack_modifier": 0,
            "max_hp_modifier": 0
        }
        
        # 3. Weather Reset: Re-initialize to default state
        from engine.weather import WeatherManager
        self.weather_manager = WeatherManager(boss_coords_list=None)
        
        self.loot = []
        self.fading_entities = []
        self.active_dialogue = None
        self.damage_numbers = []
        if hasattr(self, 'camera'):
            self.camera.instant_center(self.player.get_center())
            
        # Ensure actors in Sanctuary are linked
        from engine.world import LevelLoader
        LevelLoader.link_actors_to_routes(self)

    def save_stats(self, path: Optional[str] = None, wait: bool = False) -> None:
        """Persist the attached StatisticsTracker to disk."""
        if self.stats is None:
            return
        if self.player is not None and self.world is not None:
            world_name = getattr(self.world, 'name', 'sanctuary')
            try:
                if world_name == "sanctuary":
                    self.stats.data["run_state"] = None
                    self.stats.data["active_session_in_progress"] = False
                else:
                    self.stats.data["run_state"] = {
                        "world_name": world_name,
                        "world_debris": self.world_debris,
                        "defeated_miniboss_ids": list(self.defeated_miniboss_ids),
                        "destroyed_prop_ids": list(self.destroyed_prop_ids),
                        "player": {
                            "x": self.player.x, "y": self.player.y, "hp": self.player.hp,
                            "flask_charges": self.player.flask_charges,
                            "active_weapon_idx": getattr(self.player, 'active_weapon_idx', 0),
                            "weapons": getattr(self.player, 'weapons', []),
                            "stats": getattr(self.player, 'stats', {})
                        },
                        "defeated_miniboss_ids": list(self.defeated_miniboss_ids),
                        "enemies": [e.to_dict() for e in self.enemies],
                        "weather": self.weather_manager.to_dict()
                    }
                    self.stats.data["active_session_in_progress"] = True
            except Exception: pass
        if wait:
            try:
                self.saving_in_progress = True
                self.last_save_elapsed = 0.0
                self.stats.save(path)
            finally: self.saving_in_progress = False
            return
        try: self._save_queue.put_nowait(path)
        except Exception: pass

    def _save_worker(self):
        while getattr(self, '_save_worker_running', False):
            try:
                item = self._save_queue.get(timeout=0.5)
            except Exception: continue
            if item is None: break
            try:
                self.saving_in_progress = True
                self.last_save_elapsed = 0.0
                if self.stats is not None:
                    try: self.stats.save(item)
                    except Exception: pass
            finally:
                self.saving_in_progress = False
                try: self._save_queue.task_done()
                except Exception: pass

    def shutdown_save_worker(self, timeout: float = 2.0) -> None:
        """Stop the save worker thread."""
        self._save_worker_running = False
        try:
            self._save_queue.put_nowait(None)
            self._save_worker_thread.join(timeout)
        except Exception: pass

    def trigger_choice_of_fates(self):
        """Generate two mutually exclusive stat choices for the player."""
        level_scale = 1
        if self.stats:
            try:
                pages = self.stats.data["lifetime_stats"].get("pages_collected", 0)
                level_scale = 1 + (pages // 100)
            except Exception: pass
        base_x = 5 * level_scale
        minor_y = int(base_x * 0.25)
        self.active_choice = {
            "title": "The Choice of Fates",
            "options": [
                {
                    "name": "The Quill", "bias": "Offense",
                    "modifiers": {"attack_modifier": base_x, "max_hp_modifier": minor_y},
                    "description": f"+{base_x} Attack, +{minor_y} Max HP"
                },
                {
                    "name": "The Binding", "bias": "Defense",
                    "modifiers": {"max_hp_modifier": base_x, "attack_modifier": minor_y},
                    "description": f"+{base_x} Max HP, +{minor_y} Attack"
                }
            ],
            "selected_index": 0
        }
        # Prevent instant-confirm on the same frame as kill
        self.input_debounce_timer = 0.3
        print(f"[FATE] Choice of Fates menu opened (Scale: {level_scale}).")

    def on_enter_sanctuary(self):
        """Rule: Absolute state purification upon entering the Sanctuary hub."""
        from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES, SWORD_DAMAGE

        self.player.is_exposed = False
        self.player.hp = float(self.player.max_hp)
        self.player.flask_charges = int(FLASK_MAX_CHARGES)

        # Network Reset: Stop active sessions and resume discovery
        if hasattr(self, 'network_manager'):
            self.network_manager.stop_network()
            self.network_manager.start_searching()

        # Weapon Reset: Back to standard starting gear

        self.player.weapons = [{"name": "Initial Quill", "damage": SWORD_DAMAGE}]
        self.player.active_weapon_idx = 0
        
        # Weather Reset: Ensure next run starts from Grace Period
        if hasattr(self, 'weather_manager'):
            self.weather_manager.reset(boss_coords_list=None)
        
        # Economy Reset: Clear current Pages collected for the next run
        if self.stats:
            self.stats.data["lifetime_stats"]["pages_collected"] = 0
            self.stats.data["run_state"] = None
            self.stats.data["active_session_in_progress"] = False

        # Sanctuary-specific stat locks
        if self.player.stats.get("edification", 0) != 1:
            self.player.stats["edification"] = 1

        self.world_debris = []
        self.destroyed_prop_ids = set()

        # Ensure actors in Sanctuary (Chronicler) are linked to routes
        from engine.world import LevelLoader
        LevelLoader.link_actors_to_routes(self)

    def update(self, dt, actions, audio_manager=None):
        """Update all game logic."""
        self.audio_manager = audio_manager
        attack_pressed = actions.get('attack', False)
        ratchet_reset = actions.get('ratchet_reset', False)

        if ratchet_reset:
            self.input_ratchet_latched = False

        if self.input_debounce_timer > 0:
            self.input_debounce_timer -= dt
            attack_pressed = False

        # 1. Capture attack start for SFX
        if attack_pressed and self.player.state != PlayerStateEnum.ATTACKING:
            if audio_manager:
                audio_manager.play_sfx("attack_swing.ogg")

        # --- Weather System: The Redacting Circle ---
        self.weather_manager.update(dt, self.player, self.world, audio_manager=audio_manager)
        # Sync attributes for legacy renderer access if needed
        self.active_safe_radius = self.weather_manager.active_safe_radius
        self.bleed_state = self.weather_manager.bleed_state
        self.current_boss_coords = self.weather_manager.get_current_boss_coords()

        # Milestone Bloom Trigger (Priority 2)
        if self.weather_manager.pending_milestone_text:
            self.trigger_bloom(self.weather_manager.pending_milestone_text, priority=2)
            self.weather_manager.pending_milestone_text = None

        # --- Typographic Bloom: Zone Discovery (Priority 1) ---
        if getattr(self.world, 'name', '') != "sanctuary":
            px, py = self.player.get_center()
            # Unit logic: 11x11 units of 40x40 tiles
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
                    
                    # Room naming logic
                    name = "THE UNKNOWN MARGIN"
                    for s in getattr(self.world, 'module_sockets', []):
                        if s.get('name') == current_room_id:
                            plug = s.get('active_plug', '').lower()
                            if 'forest' in plug: name = "THE VERDANT SILENCE"
                            elif 'ruins' in plug: name = "THE SCORCHED MARGIN"
                            elif 'colophon' in plug: name = "THE COLOPHON"
                            elif 'boss' in plug: name = "THE CROWN RING"
                            break
                    self.trigger_bloom(name, priority=1)

        if self.zone_cooldown_timer > 0: self.zone_cooldown_timer -= dt
        if self.bloom_timer > 0:
            self.bloom_timer -= dt
        else:
            self.bloom_priority = 0

        # Boss Spawn Rule: Only if circle is closed (CLAMPED) and not already spawned
        if self.weather_manager.is_boss_spawn_ready():
            boss_alive = any(getattr(e, 'name', '') == "Night Boss" for e in self.enemies)
            
            # Active Spawning Pass: If clamped and no boss, manifest the threat
            if not boss_alive and self.bleed_state == "CLAMPED":
                from engine.enemy import NightBoss
                idx = self.weather_manager.current_boss_idx
                boss_list = getattr(self.world, 'boss_coords_list', [])
                if idx < len(boss_list):
                    coords = boss_list[idx]
                    bx, by = coords['x'] * TILE_SIZE, coords['y'] * TILE_SIZE
                    new_boss = NightBoss(bx, by)
                    self.enemies.append(new_boss)
                    print(f"[THE BLEED] Night Boss {idx + 1} has manifested at ({bx}, {by}).")
                    boss_alive = True

            self.weather_manager.lock_circle_for_boss(boss_alive)
            
        # Appendix Rule: After Night 2 defeat, spawn the portal
        if self.bleed_state == "APPENDIX" and not any(e.name == "Appendix Warp" for e in self.world.interactables):
            idx = self.weather_manager.current_boss_idx
            boss_list = getattr(self.world, 'boss_coords_list', []) or []
            if idx < len(boss_list):
                coords = boss_list[idx]
                from engine.world import WarpPortal
                portal_rect = (coords['x'] * TILE_SIZE - 20, coords['y'] * TILE_SIZE - 20, 40, 40)
                portal = WarpPortal("final_boss", 25, 25, portal_rect, name="Appendix Warp")
                self.world.interactables.append(portal)
                self.trigger_bloom("THE APPENDIX REVEALED", priority=2)
                print("[THE BLEED] The portal to the Appendix has manifested.")

        # Final Boss Victory Rule
        if getattr(self.world, 'name', '') == "final_boss":
            final_boss_dead = not any(getattr(e, 'name', '') == "The Final Author" for e in self.enemies)
            if final_boss_dead and getattr(self.stats, 'data', {}).get("last_run_result") != "VICTORY":
                if self.stats:
                    self.stats.data["last_run_result"] = "VICTORY"
                    self.stats.increment("wins_chapters_cleared", 1)
                    self.weather_manager.trigger_dilution()
                    self.trigger_bloom("CHAPTER COMPLETE", priority=2)
                    print("[SYSTEM] Final Boss defeated. Victory achieved.")

        # Victory Extraction sequence
        if getattr(self.stats, 'data', {}).get("last_run_result") == "VICTORY":
            # Rule: If the dilution interlude ends (or has graduated to APPENDIX) while in the final arena
            if (self.bleed_state in ("DILUTION", "APPENDIX")) and self.weather_manager.timer <= 0:
                print("[SYSTEM] Victory sequence complete. Extracting to Sanctuary...")
                from engine.world import WarpPortal
                # Automatic extraction warp
                extraction_warp = WarpPortal("sanctuary", 0, 0, (0, 0, 0, 0))
                extraction_warp.execute_interaction(self)

        # Sanctuary Level Reset Rule: Transition logic
        if getattr(self.world, 'name', '') == "sanctuary":
            if not self.sanctuary_reset_complete:
                self.on_enter_sanctuary()
                self.sanctuary_reset_complete = True
        else:
            # Clear flag when in the macro-world to allow reset on next return
            self.sanctuary_reset_complete = False

        if self.active_dialogue:
            active_respite = getattr(self, 'active_respite', None)
            
            # Standard Dialogue Rule: Close on any confirmation if NOT a menu
            if attack_pressed and not active_respite:
                self.active_dialogue = None
                self.input_debounce_timer = 0.2
                self.save_stats(wait=True)
                return

            # Respite Menu Logic
            if active_respite:
                move_dir = actions.get('move', (0, 0))
                
                # 1. Navigation focus (Vertical)
                if not self.input_ratchet_latched and self.menu_nav_cooldown <= 0:
                    if move_dir[1] > 0.6: # Down
                        self.respite_selection_idx = (self.respite_selection_idx + 1) % 6
                        self.input_ratchet_latched = True
                        self.menu_nav_cooldown = 0.2
                        if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")
                    elif move_dir[1] < -0.6: # Up
                        self.respite_selection_idx = (self.respite_selection_idx - 1) % 6
                        self.input_ratchet_latched = True
                        self.menu_nav_cooldown = 0.2
                        if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")

                # 2. Handle Confirm/Select Actions (Independent of Ratchet)
                if attack_pressed and not self.input_ratchet_latched:
                    self.input_ratchet_latched = True
                    if audio_manager: audio_manager.play_sfx("menu_confirm.ogg")
                    
                    # Index 0: Immediate REST
                    if self.respite_selection_idx == 0:
                        active_respite.execute_rest(self, audio_manager=audio_manager)
                        self.respite_marked_idx = -1 # Clear markings on rest
                    
                    # Index 1-3: MARK for upgrade
                    elif 1 <= self.respite_selection_idx <= 3:
                        if self.player.has_rested_this_session:
                            self.respite_marked_idx = self.respite_selection_idx
                        else:
                            print("[UI] Must rest before marking upgrades.")

                    # Index 4: FINALIZE (Apply marked)
                    elif self.respite_selection_idx == 4:
                        if self.respite_marked_idx == 1: self._handle_upgrade("edification", 1, 50)
                        elif self.respite_marked_idx == 2: self._handle_upgrade("attack_modifier", 5, 50)
                        elif self.respite_marked_idx == 3: self._handle_upgrade("max_hp_modifier", 10, 50)
                        
                        if not self.player.has_rested_this_session:
                            # Upgrade successful (auto-locks rest)
                            self.respite_marked_idx = -1
                            self.respite_selection_idx = 5 # Shift focus to Close

                    # Index 5: CLOSE
                    elif self.respite_selection_idx == 5:
                        self.active_dialogue = None
                        self.active_respite = None
                        self.input_debounce_timer = 0.2
                        self.player.has_rested_this_session = False
                        self.save_stats(wait=True)
                        return
                    
                    attack_pressed = False

                # 3. Handle Keyboard Shortcuts (Independent of Ratchet)
                # R - Rest is ALWAYS allowed to trigger the unblock
                if actions.get('key_r'):
                    active_respite.execute_rest(self, audio_manager=audio_manager)
                    self.respite_marked_idx = -1
                
                # Upgrades are only allowed AFTER resting
                elif self.player.has_rested_this_session:
                    if actions.get('key_1'): self.respite_marked_idx = 1
                    elif actions.get('key_2'): self.respite_marked_idx = 2
                    elif actions.get('key_3'): self.respite_marked_idx = 3

            return

        # Choice of Fates Rule: Priority Input
        active_choice = getattr(self, 'active_choice', None)
        if active_choice:
            move_dir = actions.get('move', (0, 0))
            
            if not self.input_ratchet_latched and self.menu_nav_cooldown <= 0:
                if move_dir[0] > 0.5:
                    active_choice["selected_index"] = 1
                    self.input_ratchet_latched = True
                    self.menu_nav_cooldown = 0.2
                elif move_dir[0] < -0.5:
                    active_choice["selected_index"] = 0
                    self.input_ratchet_latched = True
                    self.menu_nav_cooldown = 0.2
                
            if attack_pressed:
                choice_node = active_choice["options"][active_choice["selected_index"]]
                print(f"[DEBUG] Choice Confirm Attempt: {choice_node['name']}")
                for stat, val in choice_node["modifiers"].items():
                    self.player.stats[stat] = self.player.stats.get(stat, 0) + val
                self.active_choice = None
                print(f"[FATE] Player chose {choice_node['name']}. Stats updated.")
            return

        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        nearby_interactables = self.world.get_nearby_interactables(player_rect)
        if nearby_interactables:
            self.player.current_interactable = nearby_interactables[0]
        else:
            self.player.current_interactable = None

        # Unified Interaction Filter: If interacting, suppress combat
        target = self.player.current_interactable
        if attack_pressed and target:
            target.execute_interaction(self)
            attack_pressed = False

        if self.hit_stop_timer > 0:
            self.hit_stop_timer -= dt
            return
        if self.death_timer > 0:
            self.death_timer -= dt
            self._update_audio_track(dt) # Allow death music to trigger
            if self.death_timer <= 0:
                self.respawn_player()
            return

        move_dir = actions.get('move', (0, 0))
        flask_pressed = actions.get('flask', False)
        dash_pressed = actions.get('dash', False)
        block_pressed = actions.get('block', False)
        swap_pressed = actions.get('swap', False)

        if swap_pressed:
            self.player.swap_weapon()

        walls = self.world.get_nearby_walls(player_rect)
        speed_multiplier = 1.0
        for obj in self.world.interactables:
            if obj.name == "Inkwell Puddle":
                if check_aabb_collision(player_rect, obj.rect):
                    speed_multiplier = 0.5
                    break
        self.player.update(
            dt, move_dir, walls, actions, attack_pressed,
            flask_pressed, dash_pressed, block_pressed, speed_multiplier
        )
        # Audio Track Manager logic
        self._update_audio_track(dt)

        self.camera.update(self.player.get_center(), dt)

        if self.player.state == PlayerStateEnum.ATTACKING:
            hitbox = get_sword_hitbox(self.player.get_center(), self.player.facing)

            active_weapon = self.player.get_active_weapon()
            bonus_atk = getattr(self.player, 'stats', {}).get('attack_modifier', 0)
            damage = active_weapon.get("damage", SWORD_DAMAGE) + bonus_atk
            hit_landed = False
            for enemy in list(self.enemies):
                try:
                    if check_aabb_collision(hitbox, enemy.get_rect()):
                        if not enemy.is_staggered():
                            enemy.take_damage(damage)
                            hit_landed = True
                            self.hit_stop_timer = HIT_STOP_DURATION
                            self.shake_timer = SCREEN_SHAKE_DURATION
                            self.damage_numbers.append({
                                'val': damage, 'pos': (enemy.x + 10, enemy.y - 20),
                                'time': DAMAGE_NUMBER_LIFETIME, 'color': COLOR_SELECTION
                            })
                except Exception: pass

            for obj in list(self.world.interactables):
                if obj.is_breakable and check_aabb_collision(hitbox, obj.rect):
                    obj.take_damage(damage)
                    hit_landed = True
                    if obj.is_dead():
                        try:
                            # Record Destruction if it has a unique ID
                            if hasattr(obj, 'id') and obj.id:
                                self.destroyed_prop_ids.add(obj.id)
                            
                            self.world.interactables.remove(obj)
                            # Rule: Barrels get 0.16s for breaking animation (80ms x 2), others 0.1s
                            fade_time = 0.16 if obj.name == "Barrel" else 0.1
                            self.fading_entities.append({'obj': obj, 'time': fade_time})
                            if audio_manager:
                                audio_manager.play_sfx("prop_break.ogg")
                            from engine.loot import roll_drop
                            roll_drop(4, (obj.x, obj.y), self)
                        except Exception: pass
            
            if hit_landed and audio_manager:
                audio_manager.play_sfx("attack_hit.ogg")

        # Environmental SFX
        if self.player.is_exposed and audio_manager:
            audio_manager.play_sfx("player_hurt_rain.ogg")

        for enemy in list(self.enemies):
            if enemy.is_dead():
                try:
                    if getattr(enemy, 'is_miniboss', False) and enemy.id:
                        self.defeated_miniboss_ids.add(enemy.id)
                    
                    if hasattr(enemy, 'on_death'): enemy.on_death(self)
                    self.enemies.remove(enemy)
                    if audio_manager:
                        audio_manager.play_sfx("enemy_death.ogg")
                    from engine.loot import roll_drop
                    tier = getattr(enemy, 'loot_tier', 3)
                    roll_drop(tier, (enemy.x, enemy.y), self)
                except Exception: pass
                continue
            try: enemy.update(dt, self)
            except Exception: pass

        resolve_enemy_player_collision(self.player, self.enemies)
        if self.shake_timer > 0: self.shake_timer -= dt
        for fading in self.fading_entities[:]:
            fading['time'] -= dt
            if fading['time'] <= 0:
                # Rule: Barrels transition to persistent debris
                if fading['obj'].name == "Barrel":
                    self.world_debris.append({
                        'name': 'BarrelRubble',
                        'pos': (fading['obj'].x, fading['obj'].y)
                    })
                self.fading_entities.remove(fading)
        self.update_damage_numbers(dt)
        
        # Age out parry sparks
        for effect in self.parry_effects[:]:
            effect['time'] -= dt
            if effect['time'] <= 0:
                self.parry_effects.remove(effect)

        for item in self.loot[:]:
            try:
                if check_aabb_collision(player_rect, item.get_rect()):
                    item.execute_pickup(self)
                    self.loot.remove(item)
                    if audio_manager:
                        audio_manager.play_sfx("page_pickup.ogg")
            except Exception: pass
        try:
            if hasattr(self.player, 'hp') and self.player.hp <= 0:
                self.death_timer = 5.0
        except Exception:
            pass

    def _update_audio_track(self, dt):
        """Update active_track_name based on zone, boss proximity, and temporal hysteresis."""
        world_name = getattr(self.world, 'name', 'sanctuary')

        # 1. Base Selection Rule (Zone & Result Priority)
        target_track = "world_exploration.ogg"
        if world_name == "sanctuary":
            target_track = "sanctuary_hub.ogg"
        
        # Victory Exception: Chapter complete theme
        if getattr(self.stats, 'data', {}).get("last_run_result") == "VICTORY" and world_name == "final_boss":
            self.player.active_track_name = "victory_theme.ogg"
            return

        if self.player.hp <= 0:
            self.player.active_track_name = "death_theme.ogg"
            return

        # 2. Dynamic Engagement Rule (15m = 600px Euclidean Radius)
        proximity_threshold = 15 * TILE_SIZE # 600px
        cooldown_limit = 3.0 # Hysteresis window

        near_miniboss = False
        near_night_boss = False
        near_final_author = False
        
        px, py = self.player.get_center()
        for enemy in self.enemies:
            if getattr(enemy, 'is_miniboss', False):
                ex, ey = enemy.get_center()
                dist_sq = (px - ex)**2 + (py - ey)**2
                if dist_sq <= proximity_threshold**2:
                    ename = getattr(enemy, 'name', '')
                    if ename == "The Final Author": near_final_author = True
                    elif ename == "Night Boss": near_night_boss = True
                    else: near_miniboss = True
                    break

        # 3. Hierarchy Stack with Hysteresis
        # Rule: Combat themes share a common 'Engagement Cooldown'
        current_active = self.player.active_track_name
        combat_tracks = ("miniboss_combat.ogg", "night_boss.ogg", "final_reckoning.ogg")

        if near_final_author:
            self.player.active_track_name = "final_reckoning.ogg"
            self.player.miniboss_cooldown_accumulator = 0.0
        elif near_night_boss:
            self.player.active_track_name = "night_boss.ogg"
            self.player.miniboss_cooldown_accumulator = 0.0
        elif near_miniboss:
            self.player.active_track_name = "miniboss_combat.ogg"
            self.player.miniboss_cooldown_accumulator = 0.0
        elif current_active in combat_tracks:
            # Player has left the radius; start ticking the hysteresis cooldown
            self.player.miniboss_cooldown_accumulator += dt
            if self.player.miniboss_cooldown_accumulator >= cooldown_limit:
                self.player.active_track_name = target_track
        else:
            # Passive Exploration
            self.player.active_track_name = target_track

    def _handle_upgrade(self, stat_name, amount, cost_scale):
        """Helper to handle edification upgrades. Returns True on success."""
        current_val = self.player.stats.get(stat_name, 0)

        # Calculate level based on amount steps
        level = current_val // amount if amount > 0 else current_val
        cost = (level + 1) * cost_scale

        pages = self.stats.data["lifetime_stats"].get("pages_collected", 0)
        if pages >= cost:
            self.stats.data["lifetime_stats"]["pages_collected"] -= cost
            self.player.stats[stat_name] = current_val + amount
            self.player.has_rested_this_session = False # Lock until next rest

            if getattr(self, 'active_respite', None):
                self.active_respite.execute_interaction(self)
            return True
        else:
            print(f"[DEBUG] Not enough pages for {stat_name} upgrade. Need {cost}, have {pages}.")
            return False

    def respawn_player(self):
        """Reset player to sanctuary after death."""
        from engine.maps import create_world
        if self.stats:
            self.stats.data["last_run_result"] = "DEFEAT"
            self.stats.data["active_session_in_progress"] = False
            self.stats.data["run_state"] = None
        
        self.world = create_world("sanctuary", defeated_ids=self.defeated_miniboss_ids)
        self.player.x, self.player.y = float(self.world.player_start[0]), float(self.world.player_start[1])
        if hasattr(self, 'camera'): self.camera.instant_center(self.player.get_center())
        
        # Centralized Reset (HP, Flasks, Pages, Weapons)
        self.on_enter_sanctuary()
        
        self.enemies, self.loot = [], []
        self.save_stats(wait=True)

    def update_damage_numbers(self, dt):
        """Handle fading and movement of damage numbers."""
        from constants import DAMAGE_NUMBER_SPEED
        for num in self.damage_numbers[:]:
            num['time'] -= dt
            x, y = num['pos']
            num['pos'] = (x, y - DAMAGE_NUMBER_SPEED * dt)
            if num['time'] <= 0: self.damage_numbers.remove(num)
