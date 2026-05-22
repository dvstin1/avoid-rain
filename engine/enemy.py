"""
Enemy classes for simple NPCs and monsters.
"""
import math
from engine.physics import resolve_wall_collision, check_aabb_collision
from constants import TILE_SIZE


class Enemy:
    """Base enemy class."""
    def __init__(self, x, y, width, height, hp):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.vx = 0.0
        self.vy = 0.0
        self.hp = hp
        self.max_hp = hp

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def is_dead(self):
        return self.hp <= 0

    def take_damage(self, amount):
        try:
            self.hp -= amount
        except Exception:
            pass


class SlugEnemy(Enemy):
    """A low-tier slug enemy that detects the player and slowly approaches.

    - Detects player within SLUG_DETECT_METERS * TILE_SIZE
    - Moves directly toward player (no pathfinding)
    - Deals damage on contact with a cooldown
    """
    def __init__(self, x, y):
        from constants import SLUG_MAX_HP, SLUG_SPEED, SLUG_DETECT_METERS, SLUG_DAMAGE, SLUG_DAMAGE_COOLDOWN, PLAYER_WIDTH, PLAYER_HEIGHT
        super().__init__(x, y, PLAYER_WIDTH, PLAYER_HEIGHT, SLUG_MAX_HP)
        self.speed = SLUG_SPEED
        self.detect_radius = SLUG_DETECT_METERS * TILE_SIZE
        self.damage = SLUG_DAMAGE
        self.damage_cooldown = SLUG_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

    def update(self, dt, state):
        """Move toward the player when within detection radius and handle internal timers."""
        player_cx, player_cy = state.player.get_center()
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        dx = player_cx - cx
        dy = player_cy - cy
        dist_sq = dx * dx + dy * dy
        if dist_sq <= (self.detect_radius * self.detect_radius):
            dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0
            if dist > 0.0:
                nx = dx / dist
                ny = dy / dist
                self.vx = nx * self.speed
                self.vy = ny * self.speed
                self.x += self.vx * dt
                self.y += self.vy * dt
                # Resolve simple wall collisions using same helper as Player
                try:
                    walls = state.world.get_nearby_walls((self.x, self.y, self.width, self.height))
                    self.x, self.y = resolve_wall_collision((self.x, self.y, self.width, self.height), walls)
                except Exception:
                    pass
        else:
            # Idle
            self.vx = 0.0
            self.vy = 0.0

        if self._damage_timer > 0.0:
            self._damage_timer -= dt

    def attempt_damage_player(self, state):
        """If touching the player and cooldown elapsed, apply damage to player."""
        if self._damage_timer > 0.0:
            return False
        if check_aabb_collision(self.get_rect(), (state.player.x, state.player.y, state.player.width, state.player.height)):
            try:
                state.player.take_damage(self.damage)
            except Exception:
                pass
            self._damage_timer = self.damage_cooldown
            return True
        return False
