"""
Manages the global game state and coordinates engine components.
"""
from typing import Optional
import queue
import threading

from constants import (
    PLAYER_START_X, PLAYER_START_Y, DUMMY_X, DUMMY_Y,
    DUMMY_WIDTH, DUMMY_HEIGHT, DAMAGE_NUMBER_LIFETIME, DAMAGE_NUMBER_SPEED,
    SWORD_DAMAGE, COLOR_YELLOW, COLOR_WHITE, RECOVERY_TIME, STAGGER_OUTLINE_TIME,
    PLAYER_MAX_HP, FLASK_MAX_CHARGES,
    SCREEN_SHAKE_DURATION, HIT_STOP_DURATION,
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_PANEL_H, HUD_SWAP_BTN_RECT, HUD_PICKUP_BTN_RECT,
    TILE_SIZE, GRID_WIDTH, GRID_HEIGHT, CAMERA_LERP_SPEED
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
                saved_enemies = run_data.get("enemies", [])
                self.world = create_world(world_name, saved_enemies=saved_enemies)

                # Restore Player
                p_data = run_data.get("player", {})
                self.player.x = float(p_data.get("x", PLAYER_START_X))
                self.player.y = float(p_data.get("y", PLAYER_START_Y))
                self.player.hp = float(p_data.get("hp", PLAYER_MAX_HP))
                self.player.flask_charges = int(p_data.get("flask_charges", FLASK_MAX_CHARGES))
                self.player.active_weapon_idx = int(p_data.get("active_weapon_idx", 0))
                self.player.weapons = p_data.get("weapons", self.player.weapons)

                # Restore Enemies
                self.enemies = getattr(self.world, 'enemies', [])
            except Exception:
                pass
        else:
            self.enemies = getattr(self.world, 'enemies', [])

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
        self.dummy_rect = (DUMMY_X, DUMMY_Y, DUMMY_WIDTH, DUMMY_HEIGHT)
        self.dummy_stagger_timer = 0.0
        self.dummy_outline_timer = 0.0
        self.damage_numbers = []
        self.loot = []
        self.fading_entities = []
        self.death_timer = 0.0
        self.shake_timer = 0.0
        self.hit_stop_timer = 0.0
        self.last_save_elapsed = 1e6
        self.objectives = []
        self.input_debounce_timer = 0.0

        self._save_queue = queue.Queue(maxsize=8)
        self._save_worker_running = True
        self.saving_in_progress = False
        self._save_worker_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._save_worker_thread.start()

    def deallocate(self):
        """Purge all runtime gameplay memory."""
        self.player = None
        self.world = None
        self.enemies = []
        self.loot = []
        self.fading_entities = []
        self.active_dialogue = None

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
            self.world = create_world(world_name, saved_enemies=saved_enemies)
            p_data = run_data.get("player", {})
            spawn_x = float(p_data.get("x", self.world.player_start[0]))
            spawn_y = float(p_data.get("y", self.world.player_start[1]))
            self.player = Player(spawn_x, spawn_y)
            self.player.hp = float(p_data.get("hp", PLAYER_MAX_HP))
            self.player.flask_charges = int(p_data.get("flask_charges", FLASK_MAX_CHARGES))
            self.player.active_weapon_idx = int(p_data.get("active_weapon_idx", 0))
            self.player.weapons = p_data.get("weapons", self.player.weapons)
            self.enemies = getattr(self.world, 'enemies', [])
        else:
            self.world = create_world("sanctuary")
            self.player = Player(self.world.player_start[0], self.world.player_start[1])
            self.enemies = getattr(self.world, 'enemies', [])

        self.loot = []
        self.fading_entities = []
        self.active_dialogue = None
        self.death_timer = 0.0
        self.damage_numbers = []
        if hasattr(self, 'camera'):
            self.camera.instant_center(self.player.get_center())

    def reset_to_new_game(self):
        """Reset player and world to start-of-game defaults."""
        from engine.maps import create_world
        self.world = create_world("sanctuary")
        self.player = Player(self.world.player_start[0], self.world.player_start[1])
        if self.stats:
            self.stats.data["run_state"] = None
            self.stats.data["active_session_in_progress"] = False
            try:
                self.stats.increment("runs_started", 1)
            except Exception: pass
        self.loot = []
        self.fading_entities = []
        self.active_dialogue = None
        self.damage_numbers = []
        if hasattr(self, 'camera'):
            self.camera.instant_center(self.player.get_center())

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
                        "player": {
                            "x": self.player.x, "y": self.player.y, "hp": self.player.hp,
                            "flask_charges": self.player.flask_charges,
                            "active_weapon_idx": getattr(self.player, 'active_weapon_idx', 0),
                            "weapons": getattr(self.player, 'weapons', [])
                        },
                        "enemies": [e.to_dict() for e in self.enemies]
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

    def update(self, dt, actions):
        """Update all game logic."""
        attack_pressed = actions.get('attack', False)

        if self.input_debounce_timer > 0:
            self.input_debounce_timer -= dt
            attack_pressed = False

        if self.active_dialogue:
            if attack_pressed:
                self.active_dialogue = None
                self.active_respite = None
                self.input_debounce_timer = 0.2
                self.save_stats(wait=True)
                return

            # Respite Menu Logic
            if getattr(self, 'active_respite', None):
                # R - Rest
                if actions.get('key_r'):
                    self.active_respite.execute_rest(self)
                    self.active_respite.execute_interaction(self) # Refresh menu text

                # 1 - Edification
                elif actions.get('key_1'):
                    self._handle_upgrade("edification", 1, 5)
                # 2 - Prowess
                elif actions.get('key_2'):
                    self._handle_upgrade("attack_modifier", 5, 5)
                # 3 - Fortification
                elif actions.get('key_3'):
                    self._handle_upgrade("max_hp_modifier", 10, 5)
            return

        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        nearby_interactables = self.world.get_nearby_interactables(player_rect)
        if nearby_interactables:
            self.player.current_interactable = nearby_interactables[0]
        else:
            self.player.current_interactable = None

        # Unified Interaction Filter: If interacting, suppress combat
        # WeaponPickup is excluded from SPACE bar (now handled via HUD button)
        from engine.world import WeaponPickup
        target = self.player.current_interactable
        if attack_pressed and target and not isinstance(target, WeaponPickup):
            target.execute_interaction(self)
            attack_pressed = False

        if self.hit_stop_timer > 0:
            self.hit_stop_timer -= dt
            return
        if self.death_timer > 0:
            self.death_timer -= dt
            if self.death_timer <= 0: self.respawn_player()
            return

        move_dir = actions.get('move', (0, 0))
        flask_pressed = actions.get('flask', False)
        dash_pressed = actions.get('dash', False)
        block_pressed = actions.get('block', False)

        if getattr(self, 'active_choice', None):
            if move_dir[0] > 0: self.active_choice["selected_index"] = 1
            elif move_dir[0] < 0: self.active_choice["selected_index"] = 0
            if attack_pressed:
                choice = self.active_choice["options"][self.active_choice["selected_index"]]
                for stat, val in choice["modifiers"].items():
                    self.player.stats[stat] = self.player.stats.get(stat, 0) + val
                self.active_choice = None
            return

        mouse_click = actions.get('mouse_click')
        if mouse_click:
            # HUD Button Collision Check
            bx, by = 10, SCREEN_HEIGHT - HUD_PANEL_H - 10
            # [SWAP] Button check
            sb = HUD_SWAP_BTN_RECT
            if (bx + sb[0] <= mouse_click[0] <= bx + sb[0] + sb[2]) and \
               (by + sb[1] <= mouse_click[1] <= by + sb[1] + sb[3]):
                self.player.swap_weapon()
            # [PICK UP] Button check
            pb = HUD_PICKUP_BTN_RECT
            if (bx + pb[0] <= mouse_click[0] <= bx + pb[0] + pb[2]) and \
               (by + pb[1] <= mouse_click[1] <= by + pb[1] + pb[3]):
                target = self.player.current_interactable
                if isinstance(target, WeaponPickup):
                    target.execute_interaction(self)

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
        self.camera.update(self.player.get_center(), dt)

        if self.player.state == PlayerStateEnum.ATTACKING:
            hitbox = get_sword_hitbox(self.player.get_center(), self.player.facing)
            if check_aabb_collision(hitbox, self.dummy_rect):
                if self.dummy_stagger_timer <= 0:
                    self.trigger_dummy_hit(SWORD_DAMAGE, COLOR_WHITE)
                    self.dummy_stagger_timer, self.dummy_outline_timer = RECOVERY_TIME, STAGGER_OUTLINE_TIME
                    self.hit_stop_timer, self.shake_timer = HIT_STOP_DURATION, SCREEN_SHAKE_DURATION

            active_weapon = self.player.get_active_weapon()
            bonus_atk = getattr(self.player, 'stats', {}).get('attack_modifier', 0)
            damage = active_weapon.get("damage", SWORD_DAMAGE) + bonus_atk
            for enemy in list(self.enemies):
                try:
                    if check_aabb_collision(hitbox, enemy.get_rect()):
                        if not enemy.is_staggered():
                            enemy.take_damage(damage)
                            self.hit_stop_timer = HIT_STOP_DURATION
                            self.shake_timer = SCREEN_SHAKE_DURATION
                            self.damage_numbers.append({
                                'val': damage, 'pos': (enemy.x + 10, enemy.y - 20),
                                'time': DAMAGE_NUMBER_LIFETIME, 'color': COLOR_YELLOW
                            })
                except Exception: pass

            for obj in list(self.world.interactables):
                if obj.is_breakable and check_aabb_collision(hitbox, obj.rect):
                    obj.take_damage(damage)
                    if obj.is_destroyed():
                        try:
                            self.world.interactables.remove(obj)
                            self.fading_entities.append({'obj': obj, 'time': 0.1})
                            from engine.loot import roll_drop
                            roll_drop(4, (obj.x, obj.y), self)
                        except Exception: pass

        for enemy in list(self.enemies):
            if enemy.is_dead():
                try:
                    if hasattr(enemy, 'on_death'): enemy.on_death(self)
                    self.enemies.remove(enemy)
                    from engine.loot import roll_drop
                    tier = 2 if getattr(enemy, 'is_miniboss', False) else getattr(enemy, 'loot_tier', 3)
                    roll_drop(tier, (enemy.x, enemy.y), self)
                except Exception: pass
                continue
            try: enemy.update(dt, self)
            except Exception: pass
            try: enemy.attempt_damage_player(self)
            except Exception: pass

        resolve_enemy_player_collision(self.player, self.enemies)
        if self.dummy_stagger_timer > 0: self.dummy_stagger_timer -= dt
        if self.dummy_outline_timer > 0: self.dummy_outline_timer -= dt
        if self.shake_timer > 0: self.shake_timer -= dt
        for fading in self.fading_entities[:]:
            fading['time'] -= dt
            if fading['time'] <= 0: self.fading_entities.remove(fading)
        self.update_damage_numbers(dt)
        for item in self.loot[:]:
            try:
                if check_aabb_collision(player_rect, item.get_rect()):
                    item.execute_pickup(self)
                    self.loot.remove(item)
            except Exception: pass
        try:
            if hasattr(self.player, 'hp') and self.player.hp <= 0: self.death_timer = 5.0
        except Exception: pass

    def _handle_upgrade(self, stat_name, amount, cost_scale):
        """Helper to handle edification upgrades."""
        from constants import EDIFICATION_BASE_COST
        current_val = self.player.stats.get(stat_name, 0)
        level = current_val // amount if amount > 0 else current_val
        cost = EDIFICATION_BASE_COST + (level * cost_scale)
        pages = self.stats.data["lifetime_stats"].get("pages_collected", 0)
        if pages >= cost:
            self.stats.data["lifetime_stats"]["pages_collected"] -= cost
            self.player.stats[stat_name] = current_val + amount
            if getattr(self, 'active_respite', None):
                self.active_respite.execute_interaction(self)
        else:
            print(f"[DEBUG] Not enough pages for {stat_name} upgrade. Need {cost}, have {pages}.")

    def respawn_player(self):
        """Reset player to sanctuary after death."""
        from engine.maps import create_world
        if self.stats:
            self.stats.data["last_run_result"] = "DEFEAT"
            self.stats.data["active_session_in_progress"] = False
            self.stats.data["run_state"] = None
        self.world = create_world("sanctuary")
        self.player.x, self.player.y = float(self.world.player_start[0]), float(self.world.player_start[1])
        if hasattr(self, 'camera'): self.camera.instant_center(self.player.get_center())
        try:
            self.player.hp = getattr(self.player, 'max_hp', self.player.hp)
            self.player.flask_charges = FLASK_MAX_CHARGES
        except Exception: pass
        self.enemies, self.loot = [], []
        self.save_stats(wait=True)

    def update_damage_numbers(self, dt):
        """Handle fading and movement of damage numbers."""
        for num in self.damage_numbers[:]:
            num['time'] -= dt
            x, y = num['pos']
            num['pos'] = (x, y - DAMAGE_NUMBER_SPEED * dt)
            if num['time'] <= 0: self.damage_numbers.remove(num)

    def trigger_dummy_hit(self, damage, color):
        """Simulation of hitting the dummy."""
        self.damage_numbers.append({
            'val': damage,
            'pos': (self.dummy_rect[0] + 10, self.dummy_rect[1] - 20),
            'time': DAMAGE_NUMBER_LIFETIME,
            'color': color
        })
