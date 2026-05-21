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
            except Exception:
                # Keep integration low-coupled: if load fails, leave stats None
                self.stats = None

        if self.stats is not None:
            # Track that a run has started
            try:
                self.stats.increment("runs_started", 1)
            except KeyError:
                # If the provided tracker doesn't have the key, fail silently to
                # keep this integration low-coupled and non-throwing in tests.
                pass

        # Dummy Entity State
        self.dummy_rect = (DUMMY_X, DUMMY_Y, DUMMY_WIDTH, DUMMY_HEIGHT)
        self.dummy_stagger_timer = 0.0
        self.dummy_outline_timer = 0.0

        self.damage_numbers = []

    def save_stats(self, path: Optional[str] = None) -> None:
        """Persist the attached StatisticsTracker to disk, if present."""
        if self.stats is not None:
            self.stats.save(path)

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
