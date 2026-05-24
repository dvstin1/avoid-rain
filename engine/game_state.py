"""
Manages the global game state and coordinates engine components.
"""
from constants import (
    PLAYER_START_X, PLAYER_START_Y, DUMMY_X, DUMMY_Y,
    DUMMY_WIDTH, DUMMY_HEIGHT, DAMAGE_NUMBER_LIFETIME, DAMAGE_NUMBER_SPEED,
    SWORD_DAMAGE, COLOR_YELLOW, RECOVERY_TIME, STAGGER_OUTLINE_TIME,
    PLAYER_MAX_HP, FLASK_MAX_CHARGES,
    SCREEN_SHAKE_DURATION, HIT_STOP_DURATION
)
from engine.player import Player, PlayerStateEnum
from engine.world import World
from engine.combat import get_sword_hitbox
from engine.physics import check_aabb_collision, resolve_enemy_player_collision
from engine.camera import Camera
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, GRID_WIDTH, GRID_HEIGHT, CAMERA_LERP_SPEED
from engine.stats import StatisticsTracker
from typing import Optional

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
        self.world = create_world("sanctuary")
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
                self.world = create_world(world_name)

                # Restore Player
                p_data = run_data.get("player", {})
                self.player.x = float(p_data.get("x", PLAYER_START_X))
                self.player.y = float(p_data.get("y", PLAYER_START_Y))
                self.player.hp = float(p_data.get("hp", PLAYER_MAX_HP))
                self.player.flask_charges = int(p_data.get("flask_charges", FLASK_MAX_CHARGES))

                # Restore Enemies
                # We check "enemies" in run_data; if it is a list (even empty), we use it.
                # If it is missing (None/not present), only then do we fallback to defaults.
                if "enemies" in run_data:
                    from engine.enemy import SlugEnemy
                    self.enemies = []
                    e_data_list = run_data["enemies"]
                    for e_data in e_data_list:
                        if e_data.get("type") == "SlugEnemy":
                            self.enemies.append(SlugEnemy.from_dict(e_data))
                else:
                    # Fallback to world defaults only if enemy data was never saved
                    self.enemies = getattr(self.world, 'enemies', []) if hasattr(self.world, 'enemies') else []
            except Exception:
                # Keep robust: if restoration fails, defaults are already set
                pass
        else:
            # Default enemies for initial world
            self.enemies = getattr(self.world, 'enemies', []) if hasattr(self.world, 'enemies') else []

        # Camera persisted on GameState to avoid recreating each frame
        world_w = GRID_WIDTH * TILE_SIZE
        world_h = GRID_HEIGHT * TILE_SIZE
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, world_w, world_h, lerp_speed=CAMERA_LERP_SPEED)
        self.camera.instant_center(self.player.get_center())

        if self.stats is not None and self.stats.data.get("run_state") is None:
            # Track that a new run has started
            try:
                self.stats.increment("runs_started", 1)
            except KeyError:
                pass

        if self.stats is None:
            self.stats_corrupt = getattr(self, 'stats_corrupt', False)
            self.stats_corrupt_backup = getattr(self, 'stats_corrupt_backup', None)

        self.active_dialogue = None
        self.dialogue_mode = "STANDARD"

        # 4. Dummy Entity State
        self.dummy_rect = (DUMMY_X, DUMMY_Y, DUMMY_WIDTH, DUMMY_HEIGHT)
        self.dummy_stagger_timer = 0.0
        self.dummy_outline_timer = 0.0

        self.damage_numbers = []
        self.loot = [] # Dropped items like Torn Pages
        self.fading_entities = [] # Entities in destruction animation
        self.death_timer = 0.0 # 'Text Bleaching' state timer
        self.shake_timer = 0.0
        self.hit_stop_timer = 0.0

        # Time since last autosave (seconds). Large by default so indicator is hidden.
        self.last_save_elapsed = 1e6

        self.objectives = [] # List of (x, y) world coordinates for minimap indicators

        # Save worker: queue + dedicated thread to serialize all save requests.
        # This avoids spawning many threads and keeps saves off the main thread.
        import queue, threading
        self._save_queue = queue.Queue(maxsize=8)
        self._save_worker_running = True
        self.saving_in_progress = False
        self._save_worker_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._save_worker_thread.start()

    def deallocate(self):
        """Purge all runtime gameplay memory to ensure a clean slate for the title screen."""
        self.player = None
        self.world = None
        self.enemies = []
        self.loot = []
        self.fading_entities = []
        self.active_dialogue = None

    def hydrate_from_disk(self):
        """Reload state exclusively from the persistent disk file and restore the active session."""
        from engine.stats import StatisticsTracker
        from engine.maps import create_world
        from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES

        print("[STATE RECOVERY] Re-hydrating clean player and environment session from disk file.")

        # 1. Reload persistent stats from the absolute source of truth
        try:
            self.stats = StatisticsTracker.load()
        except Exception:
            # Fallback to fresh tracker if load fails
            self.stats = StatisticsTracker()

        # 2. Check for an active session snapshot (run_state)
        run_data = self.stats.data.get("run_state")

        if run_data:
            # Restore specific active session
            world_name = run_data.get("world_name", "sanctuary")
            self.world = create_world(world_name)

            p_data = run_data.get("player", {})
            spawn_x = float(p_data.get("x", self.world.player_start[0]))
            spawn_y = float(p_data.get("y", self.world.player_start[1]))
            hp = float(p_data.get("hp", PLAYER_MAX_HP))
            charges = int(p_data.get("flask_charges", FLASK_MAX_CHARGES))

            self.player = Player(spawn_x, spawn_y)
            self.player.hp = hp
            self.player.flask_charges = charges

            # Restore Enemies
            if "enemies" in run_data:
                from engine.enemy import SlugEnemy
                self.enemies = []
                for e_data in run_data["enemies"]:
                    if e_data.get("type") == "SlugEnemy":
                        self.enemies.append(SlugEnemy.from_dict(e_data))
            else:
                self.enemies = getattr(self.world, 'enemies', []) if hasattr(self.world, 'enemies') else []
        else:
            # Fallback to fresh Sanctuary start if no run is in progress
            self.world = create_world("sanctuary")
            self.player = Player(self.world.player_start[0], self.world.player_start[1])
            self.player.hp = float(PLAYER_MAX_HP)
            self.player.flask_charges = int(FLASK_MAX_CHARGES)
            self.enemies = getattr(self.world, 'enemies', []) if hasattr(self.world, 'enemies') else []

        # 4. Flush all transient scene variables from runtime memory
        self.loot = []
        self.fading_entities = []
        self.active_dialogue = None
        self.death_timer = 0.0
        self.damage_numbers = []

        # 5. Recenter camera on the new player instance
        if hasattr(self, 'camera'):
            self.camera.instant_center(self.player.get_center())

    def reset_to_new_game(self):
        """Reset player and world to start-of-game defaults, and clear run_state."""
        from engine.maps import create_world
        from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES

        self.world = create_world("sanctuary")

        # Instantiate a fresh player at Sanctuary spawn 'P'
        self.player = Player(self.world.player_start[0], self.world.player_start[1])
        self.player.hp = float(PLAYER_MAX_HP)
        self.player.flask_charges = int(FLASK_MAX_CHARGES)

        self.enemies = getattr(self.world, 'enemies', []) if hasattr(self.world, 'enemies') else []

        if self.stats:
            self.stats.data["run_state"] = None
            try:
                self.stats.increment("runs_started", 1)
            except Exception:
                pass

        # Clear other transient state
        self.loot = []
        self.fading_entities = []
        self.active_dialogue = None
        self.damage_numbers = []

        # Recenter camera
        if hasattr(self, 'camera'):
            self.camera.instant_center(self.player.get_center())

    def save_stats(self, path: Optional[str] = None, wait: bool = False) -> None:
        """Persist the attached StatisticsTracker to disk.

        By default, this enqueues the save for a background thread. If wait=True
        is passed, the save is performed synchronously on the main thread.
        """
        if self.stats is None:
            return

        # Collect current run state into StatisticsTracker if a session is active
        if self.player is not None and self.world is not None:
            try:
                self.stats.data["run_state"] = {
                    "world_name": getattr(self.world, 'name', 'sanctuary'),
                    "player": {
                        "x": self.player.x,
                        "y": self.player.y,
                        "hp": self.player.hp,
                        "flask_charges": self.player.flask_charges
                    },
                    "enemies": [e.to_dict() for e in self.enemies]
                }
            except Exception:
                # If state collection fails, we still try to save whatever was there
                pass

        if wait:
            # Synchronous save for critical milestones
            try:
                self.saving_in_progress = True
                self.last_save_elapsed = 0.0
                self.stats.save(path)
            finally:
                self.saving_in_progress = False
            return

        # Enqueue a save request for the worker to process. If the queue is full,
        # drop the request to avoid blocking the main thread.
        try:
            self._save_queue.put_nowait(path)
        except Exception:
            # Queue full or unavailable: ignore (best-effort save)
            pass

    def _save_worker(self):
        import time
        while getattr(self, '_save_worker_running', False):
            try:
                item = self._save_queue.get(timeout=0.5)
            except Exception:
                continue
            # Sentinel to stop
            if item is None:
                break
            try:
                self.saving_in_progress = True
                try:
                    self.last_save_elapsed = 0.0
                except Exception:
                    pass
                # Perform the actual save using the stats object
                if self.stats is not None:
                    try:
                        self.stats.save(item)
                    except Exception:
                        # Save failures are non-fatal; ignore but continue
                        pass
            finally:
                self.saving_in_progress = False
                try:
                    self._save_queue.task_done()
                except Exception:
                    pass
        # Drain any remaining items without blocking
        try:
            while True:
                item = self._save_queue.get_nowait()
                if item is None:
                    break
                try:
                    if self.stats is not None:
                        self.stats.save(item)
                except Exception:
                    pass
                finally:
                    try:
                        self._save_queue.task_done()
                    except Exception:
                        pass
        except Exception:
            pass

    def shutdown_save_worker(self, timeout: float = 2.0) -> None:
        """Stop the save worker thread and wait for it to finish.

        This enqueues a sentinel and joins the thread (with timeout) to ensure
        a clean shutdown during application exit or tests.
        """
        self._save_worker_running = False
        try:
            # enqueue sentinel
            self._save_queue.put_nowait(None)
        except Exception:
            try:
                self._save_queue.put(None, timeout=0.1)
            except Exception:
                pass
        try:
            self._save_worker_thread.join(timeout)
        except Exception:
            pass

    def handle_corrupt_choice(self, start_new: bool) -> None:
        """Handle player's decision after a corrupt save was detected.

        If start_new is True, create a fresh StatisticsTracker and increment
        runs_started. If False, leave stats as None (caller should handle flow).
        """
        if not getattr(self, 'stats_corrupt', False):
            return
        if start_new:
            self.stats = StatisticsTracker()
            try:
                self.stats.increment('runs_started', 1)
            except Exception:
                pass
            # Clear corrupt flags
            self.stats_corrupt = False
            self.stats_corrupt_backup = None
        else:
            # Explicitly keep stats None and leave corrupt flags set for caller
            self.stats = None

    def trigger_choice_of_fates(self):
        """Generate two mutually exclusive stat choices for the player."""
        # Biased Polar Distribution: High-Offense vs High-Defense
        # Values scaled to current "level" (pages collected could be a proxy for level)
        level_scale = 1
        if self.stats:
            try:
                pages = self.stats.data["lifetime_stats"].get("pages_collected", 0)
                level_scale = 1 + (pages // 100)
            except Exception:
                pass

        base_x = 5 * level_scale
        minor_y = int(base_x * 0.25)

        self.active_choice = {
            "title": "The Choice of Fates",
            "options": [
                {
                    "name": "The Quill",
                    "bias": "Offense",
                    "modifiers": {"attack_modifier": base_x, "max_hp_modifier": minor_y},
                    "description": f"+{base_x} Attack, +{minor_y} Max HP"
                },
                {
                    "name": "The Binding",
                    "bias": "Defense",
                    "modifiers": {"max_hp_modifier": base_x, "attack_modifier": minor_y},
                    "description": f"+{base_x} Max HP, +{minor_y} Attack"
                }
            ],
            "selected_index": 0
        }

    def update(self, dt, actions):
        """Update all game logic."""
        # 0. Handle Hit Stop
        if self.hit_stop_timer > 0:
            self.hit_stop_timer -= dt
            return

        # 0. Handle 'Text Bleaching' (Death State)
        if self.death_timer > 0:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.respawn_player()
            return # Freeze logic during bleaching

        move_dir = actions.get('move', (0, 0))
        attack_pressed = actions.get('attack', False)
        flask_pressed = actions.get('flask', False)
        dash_pressed = actions.get('dash', False)
        block_pressed = actions.get('block', False)

        # 0. Handle Dialogue Stasis
        if self.active_dialogue:
            if attack_pressed:
                self.active_dialogue = None
                self.save_stats(wait=True) # Synchronous flush on dialogue close
            return # Block all other updates during dialogue

        # 0b. Handle Choice of Fates
        if getattr(self, 'active_choice', None):
            if move_dir[0] > 0:
                self.active_choice["selected_index"] = 1
            elif move_dir[0] < 0:
                self.active_choice["selected_index"] = 0

            if attack_pressed:
                # Apply selection
                choice = self.active_choice["options"][self.active_choice["selected_index"]]
                for stat, val in choice["modifiers"].items():
                    self.player.stats[stat] = self.player.stats.get(stat, 0) + val
                self.active_choice = None
            return

        # 1. Update Interactables
        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        nearby_interactables = self.world.get_nearby_interactables(player_rect)
        if nearby_interactables:
            self.player.current_interactable = nearby_interactables[0]
        else:
            self.player.current_interactable = None

        # Unified Interaction Filter: If interacting, suppress combat
        if attack_pressed and self.player.current_interactable:
            self.player.current_interactable.execute_interaction(self)
            attack_pressed = False # Suppress combat swing

        # 2. Update Player
        walls = self.world.get_nearby_walls(player_rect)

        # Calculate speed multiplier from hazards
        speed_multiplier = 1.0
        for obj in self.world.interactables:
            if obj.name == "Inkwell Puddle":
                if check_aabb_collision(player_rect, obj.rect):
                    speed_multiplier = 0.5 # 50% slow
                    break

        self.player.update(
            dt, move_dir, walls, actions, attack_pressed, flask_pressed,
            dash_pressed, block_pressed, speed_multiplier
        )

        # Update camera smoothing now that player moved
        self.camera.update(self.player.get_center(), dt)

        # 3. Check for Sword Hits (affect dummy and enemies)
        if self.player.state == PlayerStateEnum.ATTACKING:
            hitbox = get_sword_hitbox(self.player.get_center(), self.player.facing)
            if check_aabb_collision(hitbox, self.dummy_rect):
                if self.dummy_stagger_timer <= 0: # Only hit if not recovering
                    self.trigger_dummy_hit(SWORD_DAMAGE, COLOR_YELLOW)
                    self.dummy_stagger_timer = RECOVERY_TIME
                    self.dummy_outline_timer = STAGGER_OUTLINE_TIME
                    self.hit_stop_timer = HIT_STOP_DURATION
                    self.shake_timer = SCREEN_SHAKE_DURATION

            # Apply hits to enemies
            active_weapon = self.player.get_active_weapon()
            damage = active_weapon.get("damage", SWORD_DAMAGE) + getattr(self.player, 'stats', {}).get('attack_modifier', 0)
            for enemy in list(self.enemies):
                try:
                    if check_aabb_collision(hitbox, enemy.get_rect()):
                        if not enemy.is_staggered():
                            enemy.take_damage(damage)
                            self.hit_stop_timer = HIT_STOP_DURATION
                            self.shake_timer = SCREEN_SHAKE_DURATION
                            # Show damage number above enemy
                            self.damage_numbers.append({
                                'val': damage,
                                'pos': (enemy.x + 10, enemy.y - 20),
                                'time': DAMAGE_NUMBER_LIFETIME,
                                'color': COLOR_YELLOW
                            })
                except Exception:
                    pass

            # Apply hits to destructible props
            for obj in list(self.world.interactables):
                if obj.is_breakable:
                    if check_aabb_collision(hitbox, obj.rect):
                        obj.take_damage(damage)
                        if obj.is_destroyed():
                            try:
                                self.world.interactables.remove(obj)
                                # Add to fading entities for visual cleanup
                                self.fading_entities.append({'obj': obj, 'time': 0.1}) # ~6 frames at 60fps
                                # Trigger Tier 4 Loot Roll
                                from engine.loot import roll_drop
                                roll_drop(4, (obj.x, obj.y), self)
                            except Exception:
                                pass

        # 4. Update Enemies
        for enemy in list(self.enemies):
            if enemy.is_dead():
                try:
                    # Trigger death-specific logic (like the Full-Cradle Rule)
                    if hasattr(enemy, 'on_death'):
                        enemy.on_death(self)
                    
                    self.enemies.remove(enemy)
                    # Trigger Tiered Loot Roll
                    from engine.loot import roll_drop
                    tier = getattr(enemy, 'loot_tier', 3)
                    roll_drop(tier, (enemy.x, enemy.y), self)
                except Exception:
                    pass
                continue

            try:
                enemy.update(dt, self)
            except Exception:
                pass
            try:
                enemy.attempt_damage_player(self)
            except Exception:
                pass

        # Apply soft pushback to separate enemies from the player's bounding box
        resolve_enemy_player_collision(self.player, self.enemies)

        # 5. Update Timers
        if self.dummy_stagger_timer > 0:
            self.dummy_stagger_timer -= dt
        if self.dummy_outline_timer > 0:
            self.dummy_outline_timer -= dt

        if self.shake_timer > 0:
            self.shake_timer -= dt

        # Update fading entities
        for fading in self.fading_entities[:]:
            fading['time'] -= dt
            if fading['time'] <= 0:
                self.fading_entities.remove(fading)

        self.update_damage_numbers(dt)

        # 5b. Update Loot Collection
        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        for item in self.loot[:]:
            try:
                if check_aabb_collision(player_rect, item.get_rect()):
                    item.execute_pickup(self)
                    self.loot.remove(item)
            except Exception:
                pass

        # 6. Check for player death and trigger 'Text Bleaching'
        try:
            if hasattr(self.player, 'hp') and self.player.hp <= 0:
                self.death_timer = 5.0 # 5 second monochrome freeze
        except Exception:
            pass

    def respawn_player(self):
        """Reset player to sanctuary after 'Text Bleaching' completes."""
        from engine.maps import create_world
        from constants import FLASK_MAX_CHARGES

        # Set persistent result for dialogue branching
        if self.stats:
            self.stats.data["last_run_result"] = "DEFEAT"

        self.world = create_world("sanctuary")
        self.player.x = float(self.world.player_start[0])
        self.player.y = float(self.world.player_start[1])
        # Reset camera
        if hasattr(self, 'camera'):
            self.camera.instant_center(self.player.get_center())
        # Reset player HP and Flask
        try:
            self.player.hp = getattr(self.player, 'max_hp', self.player.hp)
            self.player.flask_charges = FLASK_MAX_CHARGES
        except Exception:
            pass
        # Clear transient world state
        self.enemies = []
        self.loot = []

        # [Milestone] Flush state immediately upon returning to sanctuary
        self.save_stats(wait=True)

    def update_damage_numbers(self, dt):
        """Handle fading and movement of damage numbers."""
        for num in self.damage_numbers[:]:
            num['time'] -= dt
            x, y = num['pos']
            num['pos'] = (x, y - DAMAGE_NUMBER_SPEED * dt)
            if num['time'] <= 0:
                self.damage_numbers.remove(num)

    def trigger_dummy_hit(self, damage, color):
        """Simulation of hitting the dummy."""
        self.damage_numbers.append({
            'val': damage,
            'pos': (self.dummy_rect[0] + 10, self.dummy_rect[1] - 20),
            'time': DAMAGE_NUMBER_LIFETIME,
            'color': color
        })
