"""
Core player logic and state management.
"""
import math
from enum import Enum
from constants import (
    PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT,
    PLAYER_WIDTH, PLAYER_HEIGHT, SWORD_DURATION,
    GRID_WIDTH, GRID_HEIGHT, TILE_SIZE
)
from engine.physics import resolve_wall_collision

class PlayerStateEnum(Enum):
    """Possible states for the player."""
    IDLE = "idle"
    MOVING = "moving"
    ATTACKING = "attacking"
    DASHING = "dashing"
    STAGGERED = "staggered"

class Player:
    """Represents the player in the game engine."""
    # pylint: disable=too-many-instance-attributes
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.speed = PLAYER_SPEED
        self.state = PlayerStateEnum.IDLE
        self.facing = (1, 0) # Direction vector
        self.attack_timer = 0.0
        self.current_interactable = None

    def update(self, dt, move_dir, walls, attack_pressed=False):
        """
        Update player position and state.
        """
        if self.state == PlayerStateEnum.ATTACKING:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.state = PlayerStateEnum.IDLE
            return

        dx, dy = move_dir

        # 1. Update facing direction
        if dx != 0 or dy != 0:
            # Normalize for facing
            mag = math.sqrt(dx*dx + dy*dy)
            self.facing = (dx/mag, dy/mag)

        # 2. Check for attack start
        if attack_pressed:
            self.state = PlayerStateEnum.ATTACKING
            self.attack_timer = SWORD_DURATION
            self.vx, self.vy = 0, 0
            return

        # 3. Normalize movement
        magnitude = math.sqrt(dx*dx + dy*dy)
        if magnitude > 0:
            self.vx = (dx / magnitude) * self.speed
            self.vy = (dy / magnitude) * self.speed
            self.state = PlayerStateEnum.MOVING
        else:
            self.vx = 0.0
            self.vy = 0.0
            self.state = PlayerStateEnum.IDLE

        # 4. Apply velocity with dt scaling
        self.x += self.vx * dt
        self.y += self.vy * dt

        # 5. Wall Collision
        self.x, self.y = resolve_wall_collision(
            (self.x, self.y, self.width, self.height),
            walls
        )

        # 6. World Boundary Clamping (use world grid size instead of screen)
        world_pixel_width = GRID_WIDTH * TILE_SIZE
        world_pixel_height = GRID_HEIGHT * TILE_SIZE
        self.x = max(0, min(self.x, world_pixel_width - self.width))
        self.y = max(0, min(self.y, world_pixel_height - self.height))

    def get_pos(self):
        """Returns the current position as a tuple."""
        return (self.x, self.y)

    def get_center(self):
        """Returns the center point of the player."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    def take_damage(self, amount: float) -> None:
        """Apply damage to the player; clamp at zero.

        This method is intentionally simple; death/respawn handling is
        managed by GameState to keep responsibilities decoupled.
        """
        try:
            if not hasattr(self, 'hp'):
                from constants import PLAYER_MAX_HP
                self.hp = PLAYER_MAX_HP
                self.max_hp = PLAYER_MAX_HP
            self.hp -= amount
            if self.hp < 0:
                self.hp = 0
        except Exception:
            pass
