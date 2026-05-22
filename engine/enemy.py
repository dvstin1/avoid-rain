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

    def to_dict(self):
        """Serialize enemy state to a dictionary."""
        return {
            "type": self.__class__.__name__,
            "x": self.x,
            "y": self.y,
            "hp": self.hp
        }

    @classmethod
    def from_dict(cls, data):
        """Create an enemy instance from a dictionary."""
        # This base implementation might not be enough for specific subclasses
        # but serves as a template.
        return cls(data["x"], data["y"], data.get("width", 40), data.get("height", 40), data["hp"])


class SlugEnemy(Enemy):
    """A low-tier slug enemy that detects the player and slowly approaches.

    - Detects player within SLUG_DETECT_METERS * TILE_SIZE
    - Moves directly toward player (no pathfinding)
    - Deals damage on contact with a cooldown
    """
    loot_tier = 3
    def __init__(self, x, y, hp=None):
        from constants import SLUG_MAX_HP, SLUG_SPEED, SLUG_DETECT_METERS, SLUG_DAMAGE, SLUG_DAMAGE_COOLDOWN, PLAYER_WIDTH, PLAYER_HEIGHT
        initial_hp = hp if hp is not None else SLUG_MAX_HP
        super().__init__(x, y, PLAYER_WIDTH, PLAYER_HEIGHT, initial_hp)
        self.speed = SLUG_SPEED
        self.detect_radius = SLUG_DETECT_METERS * TILE_SIZE
        self.damage = SLUG_DAMAGE
        self.damage_cooldown = SLUG_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "SlugEnemy"
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(data["x"], data["y"], hp=data["hp"])

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


class BatEnemy(Enemy):
    """A fast-pursuit bat enemy that follows the player with slight erratic motion.

    - Detects player within BAT_DETECT_METERS * TILE_SIZE
    - Moves toward player with a faster speed than Slugs
    - Erratic motion: adds a perpendicular sine wave to its movement
    """
    loot_tier = 3
    def __init__(self, x, y, hp=None):
        from constants import (
            BAT_MAX_HP, BAT_SPEED, BAT_DETECT_METERS, BAT_DAMAGE,
            BAT_DAMAGE_COOLDOWN, PLAYER_WIDTH, PLAYER_HEIGHT
        )
        initial_hp = hp if hp is not None else BAT_MAX_HP
        # Bats are smaller (20x20 if player is 40x40)
        super().__init__(x, y, PLAYER_WIDTH // 2, PLAYER_HEIGHT // 2, initial_hp)
        self.speed = BAT_SPEED
        self.detect_radius = BAT_DETECT_METERS * TILE_SIZE
        self.damage = BAT_DAMAGE
        self.damage_cooldown = BAT_DAMAGE_COOLDOWN
        self._damage_timer = 0.0
        self._sine_timer = 0.0

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "BatEnemy"
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(data["x"], data["y"], hp=data["hp"])

    def update(self, dt, state):
        """Move toward the player with a sine-wave oscillation."""
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

                # Base pursuit velocity
                base_vx = nx * self.speed
                base_vy = ny * self.speed

                # Erratic oscillation: add a perpendicular component
                self._sine_timer += dt * 10.0
                oscillation = math.sin(self._sine_timer) * 60.0 # Amplitude

                # Perpendicular vector to (nx, ny) is (-ny, nx)
                self.vx = base_vx + (-ny) * oscillation
                self.vy = base_vy + (nx) * oscillation

                self.x += self.vx * dt
                self.y += self.vy * dt

                # Resolve simple wall collisions
                try:
                    walls = state.world.get_nearby_walls((self.x, self.y, self.width, self.height))
                    self.x, self.y = resolve_wall_collision(
                        (self.x, self.y, self.width, self.height), walls
                    )
                except Exception:
                    pass
        else:
            self.vx = 0.0
            self.vy = 0.0

        if self._damage_timer > 0.0:
            self._damage_timer -= dt

    def attempt_damage_player(self, state):
        """If touching the player and cooldown elapsed, apply damage."""
        if self._damage_timer > 0.0:
            return False
        if check_aabb_collision(
            self.get_rect(),
            (state.player.x, state.player.y, state.player.width, state.player.height)
        ):
            try:
                state.player.take_damage(self.damage)
            except Exception:
                pass
            self._damage_timer = self.damage_cooldown
            return True
        return False


class Miniboss(Enemy):
    """An elite 2x2 miniboss enemy with pursuit behavior."""
    loot_tier = 2
    def __init__(self, x, y, hp=None):
        from constants import (
            MINIBOSS_MAX_HP, MINIBOSS_SPEED, MINIBOSS_DAMAGE,
            MINIBOSS_DAMAGE_COOLDOWN, TILE_SIZE
        )
        initial_hp = hp if hp is not None else MINIBOSS_MAX_HP
        # Miniboss is 2x2 tiles
        super().__init__(x, y, TILE_SIZE * 2, TILE_SIZE * 2, initial_hp)
        self.speed = MINIBOSS_SPEED
        # Large detection radius
        self.detect_radius = 12 * TILE_SIZE
        self.damage = MINIBOSS_DAMAGE
        self.damage_cooldown = MINIBOSS_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "Miniboss"
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(data["x"], data["y"], hp=data["hp"])

    def update(self, dt, state):
        """Move toward the player with a pursuit vector."""
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
                
                # Resolve wall collisions
                try:
                    walls = state.world.get_nearby_walls((self.x, self.y, self.width, self.height))
                    self.x, self.y = resolve_wall_collision(
                        (self.x, self.y, self.width, self.height), walls
                    )
                except Exception:
                    pass
        else:
            self.vx = 0.0
            self.vy = 0.0

        if self._damage_timer > 0.0:
            self._damage_timer -= dt

    def attempt_damage_player(self, state):
        """Apply damage on contact."""
        if self._damage_timer > 0.0:
            return False
        if check_aabb_collision(
            self.get_rect(),
            (state.player.x, state.player.y, state.player.width, state.player.height)
        ):
            try:
                state.player.take_damage(self.damage)
            except Exception:
                pass
            self._damage_timer = self.damage_cooldown
            return True
        return False
