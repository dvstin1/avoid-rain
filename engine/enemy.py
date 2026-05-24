"""
Enemy classes for simple NPCs and monsters.
"""
import math
from engine.physics import resolve_wall_collision, check_aabb_collision
from constants import TILE_SIZE, STAGGER_DURATION


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
        self.stagger_timer = 0.0

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def is_dead(self):
        return self.hp <= 0

    def take_damage(self, amount):
        try:
            self.hp -= amount
            if self.hp > 0:
                self.stagger_timer = STAGGER_DURATION
                self.vx, self.vy = 0, 0
        except Exception:
            pass

    def is_staggered(self):
        return self.stagger_timer > 0

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
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

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
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

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
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

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

    def on_death(self, state):
        """Implement the Full-Cradle Rule for weapon drops."""
        import random
        from engine.loot import WeaponItem
        
        player_weapons_count = len(state.player.weapons)
        
        if player_weapons_count < 2:
            # Drop Standard Weapon
            weapon_data = {"name": "Refined Quill", "damage": 15}
            state.loot.append(WeaponItem(self.x, self.y, weapon_data))
        else:
            # Full-Cradle Rule: Drop Anomalous Weapon
            anomalies = [
                {"effect": "INK_BLEED", "damage_bonus": 5},
                {"effect": "VOID_STRIKE", "damage_bonus": 3},
                {"effect": "CHRONICLE_ECHO", "damage_bonus": 4}
            ]
            anomaly = random.choice(anomalies)
            weapon_data = {
                "name": f"Anomalous {anomaly['effect'].replace('_', ' ').title()}",
                "damage": 20 + anomaly["damage_bonus"],
                "modifiers": anomaly
            }
            from engine.world import WeaponPickup
            state.world.interactables.append(WeaponPickup((self.x, self.y), weapon_data))


class MinibossM2(Miniboss):
    """Variant M2: Bleeding Scribe - Fast, erratic pursuit miniboss."""
    def __init__(self, x, y, hp=None):
        from constants import MINIBOSS_MAX_HP, MINIBOSS_SPEED
        initial_hp = hp if hp is not None else MINIBOSS_MAX_HP
        super().__init__(x, y, initial_hp)
        self.name = "Bleeding Scribe"
        self.speed = MINIBOSS_SPEED * 1.3
        self._sine_timer = 0.0

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "MinibossM2"
        return d

    def update(self, dt, state):
        """Move toward the player with erratic sine-wave oscillation."""
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

        player_cx, player_cy = state.player.get_center()
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        dx, dy = player_cx - cx, player_cy - cy
        dist_sq = dx * dx + dy * dy

        if dist_sq <= (self.detect_radius * self.detect_radius):
            dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0
            if dist > 0.0:
                nx, ny = dx / dist, dy / dist
                # Erratic oscillation component
                self._sine_timer += dt * 8.0
                osc = math.sin(self._sine_timer) * 120.0
                self.vx = nx * self.speed + (-ny) * osc
                self.vy = ny * self.speed + nx * osc
                self.x += self.vx * dt
                self.y += self.vy * dt
                try:
                    walls = state.world.get_nearby_walls((self.x, self.y, self.width, self.height))
                    self.x, self.y = resolve_wall_collision((self.x, self.y, self.width, self.height), walls)
                except Exception: pass
        else:
            self.vx, self.vy = 0.0, 0.0
        if self._damage_timer > 0.0: self._damage_timer -= dt


class MinibossM3(Miniboss):
    """Variant M3: Forgotten Binder - Area-denial and teleporting miniboss."""
    def __init__(self, x, y, hp=None):
        from constants import MINIBOSS_MAX_HP, MINIBOSS_SPEED
        initial_hp = hp if hp is not None else MINIBOSS_MAX_HP
        super().__init__(x, y, initial_hp)
        self.name = "Forgotten Binder"
        self.speed = MINIBOSS_SPEED * 0.7
        self.teleport_cooldown = 4.0
        self._tele_timer = 0.0

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "MinibossM3"
        return d

    def update(self, dt, state):
        """Standard pursuit + teleporting when player is too close."""
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

        player_cx, player_cy = state.player.get_center()
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        dx, dy = player_cx - cx, player_cy - cy
        dist_sq = dx * dx + dy * dy

        if self._tele_timer > 0: self._tele_timer -= dt

        # Teleport away if player is too close and cooldown is up
        if dist_sq < (120**2) and self._tele_timer <= 0:
            import random
            angle = random.uniform(0, 2 * math.pi)
            self.x = player_cx + math.cos(angle) * 300 - self.width / 2
            self.y = player_cy + math.sin(angle) * 300 - self.height / 2
            self._tele_timer = self.teleport_cooldown
            self.vx, self.vy = 0, 0
            return

        if dist_sq <= (self.detect_radius * self.detect_radius):
            dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0
            if dist > 0.0:
                self.vx, self.vy = (dx / dist) * self.speed, (dy / dist) * self.speed
                self.x += self.vx * dt
                self.y += self.vy * dt
                try:
                    walls = state.world.get_nearby_walls((self.x, self.y, self.width, self.height))
                    self.x, self.y = resolve_wall_collision((self.x, self.y, self.width, self.height), walls)
                except Exception: pass
        else:
            self.vx, self.vy = 0.0, 0.0
        if self._damage_timer > 0.0: self._damage_timer -= dt


class FlutterEnemy(Enemy):
    """A skittish enemy that flees from the player.

    - Detects player within FLUTTER_DETECT_METERS * TILE_SIZE
    - Moves directly away from the player at high speed
    - Low HP, designed to be more of a nuisance than a direct threat
    """
    loot_tier = 4 # Small torn margins
    def __init__(self, x, y, hp=None):
        from constants import (
            FLUTTER_MAX_HP, FLUTTER_SPEED, FLUTTER_DETECT_METERS,
            FLUTTER_DAMAGE, FLUTTER_DAMAGE_COOLDOWN, PLAYER_WIDTH, PLAYER_HEIGHT
        )
        initial_hp = hp if hp is not None else FLUTTER_MAX_HP
        # Flutters are small (16x16)
        super().__init__(x, y, 16, 16, initial_hp)
        self.speed = FLUTTER_SPEED
        self.detect_radius = FLUTTER_DETECT_METERS * TILE_SIZE
        self.damage = FLUTTER_DAMAGE
        self.damage_cooldown = FLUTTER_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "FlutterEnemy"
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(data["x"], data["y"], hp=data["hp"])

    def update(self, dt, state):
        """Move away from the player if within detection radius."""
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

        player_cx, player_cy = state.player.get_center()
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        dx = cx - player_cx # Vector AWAY from player
        dy = cy - player_cy
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
        """Apply damage on contact (rare since they flee)."""
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


class BindlingEnemy(Enemy):
    """A mid-tier harasser enemy that heals when near margins (walls).

    - Moves toward the player at moderate speed.
    - Heals if within BINDLING_HEAL_RADIUS of a TILE_WALL or TILE_LOTUS_FRAME.
    - Attacks apply a "bind" effect that slows the player.
    """
    loot_tier = 2
    def __init__(self, x, y, hp=None):
        from constants import (
            BINDLING_MAX_HP, BINDLING_SPEED, BINDLING_DETECT_METERS,
            BINDLING_DAMAGE, BINDLING_DAMAGE_COOLDOWN, PLAYER_WIDTH, PLAYER_HEIGHT
        )
        initial_hp = hp if hp is not None else BINDLING_MAX_HP
        super().__init__(x, y, PLAYER_WIDTH, PLAYER_HEIGHT, initial_hp)
        self.speed = BINDLING_SPEED
        self.detect_radius = BINDLING_DETECT_METERS * TILE_SIZE
        self.damage = BINDLING_DAMAGE
        self.damage_cooldown = BINDLING_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

    def to_dict(self):
        d = super().to_dict()
        d["type"] = "BindlingEnemy"
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(data["x"], data["y"], hp=data["hp"])

    def _is_near_margin(self, world):
        """Check if any walls are within the healing radius."""
        from constants import BINDLING_HEAL_RADIUS, TILE_WALL, TILE_LOTUS_FRAME
        
        # Check a slightly expanded rect
        margin = BINDLING_HEAL_RADIUS * TILE_SIZE
        check_rect = (self.x - margin, self.y - margin, self.width + margin * 2, self.height + margin * 2)
        
        h = len(world.grid)
        w = len(world.grid[0]) if h > 0 else 0
        start_x = max(0, int(check_rect[0] // TILE_SIZE))
        start_y = max(0, int(check_rect[1] // TILE_SIZE))
        end_x = min(w, int((check_rect[0] + check_rect[2]) // TILE_SIZE) + 1)
        end_y = min(h, int((check_rect[1] + check_rect[3]) // TILE_SIZE) + 1)

        for gy in range(start_y, end_y):
            for gx in range(start_x, end_x):
                if world.grid[gy][gx] in (TILE_WALL, TILE_LOTUS_FRAME):
                    return True
        return False

    def update(self, dt, state):
        """Standard pursuit behavior + healing logic."""
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

        # 1. Healing Logic
        if self.hp < self.max_hp:
            if self._is_near_margin(state.world):
                from constants import BINDLING_HEAL_RATE
                self.hp = min(self.max_hp, self.hp + BINDLING_HEAL_RATE * dt)

        # 2. Movement Logic (Pursuit)
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
        """Apply damage and movement bind on contact."""
        if self._damage_timer > 0.0:
            return False
        if check_aabb_collision(
            self.get_rect(),
            (state.player.x, state.player.y, state.player.width, state.player.height)
        ):
            try:
                state.player.take_damage(self.damage)
                # Apply Bind Effect
                from constants import BINDLING_BIND_DURATION
                if not hasattr(state.player, 'bind_timer'):
                    state.player.bind_timer = 0.0
                state.player.bind_timer = max(state.player.bind_timer, BINDLING_BIND_DURATION)
            except Exception:
                pass
            self._damage_timer = self.damage_cooldown
            return True
        return False
