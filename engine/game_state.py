"""
Manages the global game state and coordinates engine components.
"""
from constants import (
    PLAYER_START_X, PLAYER_START_Y, DUMMY_X, DUMMY_Y,
    DUMMY_WIDTH, DUMMY_HEIGHT, DAMAGE_NUMBER_LIFETIME, DAMAGE_NUMBER_SPEED,
    SWORD_DAMAGE, COLOR_YELLOW, RECOVERY_TIME, STAGGER_OUTLINE_TIME
)
from engine.player import Player, PlayerStateEnum
from engine.world import World
from engine.combat import get_sword_hitbox
from engine.physics import check_aabb_collision
from engine.camera import Camera
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TILE_SIZE, GRID_WIDTH, GRID_HEIGHT, CAMERA_LERP_SPEED
from engine.stats import StatisticsTracker
from typing import Optional

class GameState:
    """Master state object for the game engine."""
    def __init__(self, stats: Optional[StatisticsTracker] = None, stats_path: Optional[str] = None, auto_load: bool = True):
        self.world = World()
        self.player = Player(PLAYER_START_X, PLAYER_START_Y)

        # Camera persisted on GameState to avoid recreating each frame
        world_w = GRID_WIDTH * TILE_SIZE
        world_h = GRID_HEIGHT * TILE_SIZE
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT, world_w, world_h, lerp_speed=CAMERA_LERP_SPEED)
        # Start camera centered on player instantly
        self.camera.instant_center(self.player.get_center())

        # Statistics tracker: prefer injected tracker; otherwise optionally auto-load
        self.stats = stats
        if self.stats is None and auto_load:
            try:
                if stats_path is not None:
                    self.stats = StatisticsTracker.load(stats_path)
                else:
                    # Load from default location (may be in user's home directory)
                    self.stats = StatisticsTracker.load()
            except Exception as exc:
                # Handle corrupt saves specially so UI can offer a choice to the player
                from engine.stats import CorruptSaveError
                if isinstance(exc, CorruptSaveError):
                    # Record that a corrupt save was detected and where backup was written
                    self.stats = None
                    self.stats_corrupt = True
                    try:
                        self.stats_corrupt_backup = exc.backup_path
                    except Exception:
                        self.stats_corrupt_backup = None
                else:
                    # Other errors: keep integration low-coupled and proceed without stats
                    self.stats = None

        if self.stats is not None:
            # Track that a run has started
            try:
                self.stats.increment("runs_started", 1)
            except KeyError:
                # If the provided tracker doesn't have the key, fail silently to
                # keep this integration low-coupled and non-throwing in tests.
                pass
        else:
            # Ensure flags exist
            self.stats_corrupt = getattr(self, 'stats_corrupt', False)
            self.stats_corrupt_backup = getattr(self, 'stats_corrupt_backup', None)

        # Dummy Entity State
        self.dummy_rect = (DUMMY_X, DUMMY_Y, DUMMY_WIDTH, DUMMY_HEIGHT)
        self.dummy_stagger_timer = 0.0
        self.dummy_outline_timer = 0.0

        self.damage_numbers = []

        # Time since last autosave (seconds). Large by default so indicator is hidden.
        self.last_save_elapsed = 1e6

        # Save worker: queue + dedicated thread to serialize all save requests.
        # This avoids spawning many threads and keeps saves off the main thread.
        import queue, threading
        self._save_queue = queue.Queue(maxsize=8)
        self._save_worker_running = True
        self.saving_in_progress = False
        self._save_worker_thread = threading.Thread(target=self._save_worker, daemon=True)
        self._save_worker_thread.start()

    def save_stats(self, path: Optional[str] = None) -> None:
        """Persist the attached StatisticsTracker to disk in a background thread.

        This spawns a daemon thread to perform the save so that the main loop
        isn't blocked by disk I/O. The GameState.saving_in_progress flag is set
        while the background save is running so UI can display a saving message.
        """
        if self.stats is None:
            return

        # If a save is already in progress, let it continue; do not spawn another
        if getattr(self, 'saving_in_progress', False):
            return

        import threading

        def _worker(p):
            try:
                self.saving_in_progress = True
                # Ensure last_save_elapsed reflects start of save
                try:
                    self.last_save_elapsed = 0.0
                except Exception:
                    pass
                self.stats.save(p)
            finally:
                # Mark as saved; UI will show indicator based on last_save_elapsed
                try:
                    self.saving_in_progress = False
                except Exception:
                    pass

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

    def update(self, dt, actions):
        """Update all game logic."""
        move_dir = actions.get('move', (0, 0))
        attack_pressed = actions.get('attack', False)

        # 1. Update Player
        player_rect = (self.player.x, self.player.y, self.player.width, self.player.height)
        walls = self.world.get_nearby_walls(player_rect)
        self.player.update(dt, move_dir, walls, attack_pressed)

        # Update camera smoothing now that player moved
        self.camera.update(self.player.get_center(), dt)

        # Check for warp tiles and perform a map transition if needed
        warp = self.world.check_for_warp((self.player.x, self.player.y, self.player.width, self.player.height))
        if warp is not None:
            target_name, spawn_x, spawn_y = warp
            try:
                from engine.maps import create_world
                self.world = create_world(target_name)
                # Position player at spawn coords
                self.player.x = float(spawn_x)
                self.player.y = float(spawn_y)
                # Recenter camera instantly
                if hasattr(self, 'camera'):
                    self.camera.instant_center(self.player.get_center())
            except Exception:
                # If transition fails, ignore to maintain robustness
                pass

        # 2. Check for Sword Hits
        if self.player.state == PlayerStateEnum.ATTACKING:
            hitbox = get_sword_hitbox(self.player.get_center(), self.player.facing)
            if check_aabb_collision(hitbox, self.dummy_rect):
                if self.dummy_stagger_timer <= 0: # Only hit if not recovering
                    self.trigger_dummy_hit(SWORD_DAMAGE, COLOR_YELLOW)
                    self.dummy_stagger_timer = RECOVERY_TIME
                    self.dummy_outline_timer = STAGGER_OUTLINE_TIME

        # 3. Update Timers
        if self.dummy_stagger_timer > 0:
            self.dummy_stagger_timer -= dt
        if self.dummy_outline_timer > 0:
            self.dummy_outline_timer -= dt

        self.update_damage_numbers(dt)

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
