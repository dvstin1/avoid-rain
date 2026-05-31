"""
Enemy AI and behavior definitions.
"""
import math
import random
import pygame
from constants import TILE_SIZE
from engine.physics import check_aabb_collision, resolve_wall_collision

class Enemy:
    """Base class for all enemy types."""
    def __init__(self, x, y, width, height, hp, id=None):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.hp = hp
        self.max_hp = hp
        self.id = id
        self.vx = 0.0
        self.vy = 0.0
        self.stagger_timer = 0.0
        self.is_miniboss = False
        self.loot_tier = 3 # Standard
        self.name = "Enemy"
        self._damage_timer = 0.0
        self.damage_cooldown = 1.0

    def take_damage(self, amount):
        """Standard damage logic with stagger."""
        self.hp -= amount
        if amount >= 10:
            self.stagger_timer = 0.2

    def is_staggered(self):
        return self.stagger_timer > 0

    def is_dead(self):
        return self.hp <= 0

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def to_dict(self):
        """Serialize enemy for saving."""
        return {
            "type": self.__class__.__name__,
            "x": self.x,
            "y": self.y,
            "hp": self.hp,
            "id": self.id
        }

    @classmethod
    def from_dict(cls, data):
        """Reconstruct enemy from dict."""
        return cls(data["x"], data["y"], hp=data["hp"], id=data.get("id"))

    def update(self, dt, state):
        """Standard pursuit logic."""
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
                self.vx, self.vy = (dx / dist) * self.speed, (dy / dist) * self.speed
                self.x += self.vx * dt
                self.y += self.vy * dt
                try:
                    walls = state.world.get_nearby_walls((self.x, self.y, self.width, self.height))
                    self.x, self.y = resolve_wall_collision((self.x, self.y, self.width, self.height), walls)
                except Exception:
                    pass
        else:
            self.vx, self.vy = 0.0, 0.0

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

class SlugEnemy(Enemy):
    """A slow, low-tier enemy."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            SLUG_MAX_HP, SLUG_SPEED, SLUG_DETECT_METERS,
            SLUG_DAMAGE, SLUG_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else SLUG_MAX_HP
        super().__init__(x, y, 32, 32, initial_hp, id=id)
        self.speed = SLUG_SPEED
        self.detect_radius = SLUG_DETECT_METERS * TILE_SIZE
        self.damage = SLUG_DAMAGE
        self.damage_cooldown = SLUG_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

class BatEnemy(Enemy):
    """A fast, erratic enemy."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            BAT_MAX_HP, BAT_SPEED, BAT_DETECT_METERS,
            BAT_DAMAGE, BAT_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else BAT_MAX_HP
        super().__init__(x, y, 24, 24, initial_hp, id=id)
        self.speed = BAT_SPEED
        self.detect_radius = BAT_DETECT_METERS * TILE_SIZE
        self.damage = BAT_DAMAGE
        self.damage_cooldown = BAT_DAMAGE_COOLDOWN
        self._damage_timer = 0.0
        self._angle = random.uniform(0, 2 * math.pi)

    def update(self, dt, state):
        """Move toward the player with a sine-wave oscillation."""
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
                # Pursuit vector
                self.vx, self.vy = (dx / dist) * self.speed, (dy / dist) * self.speed
                
                # Erratic sine wave perpendicular to movement
                self._angle += dt * 10.0
                perp_x, perp_y = -self.vy, self.vx
                
                self.x += (self.vx + perp_x * math.sin(self._angle)) * dt
                self.y += (self.vy + perp_y * math.sin(self._angle)) * dt
        else:
            self.vx, self.vy = 0.0, 0.0

class BindlingEnemy(Enemy):
    """A harasser enemy that binds the player."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            BINDLING_MAX_HP, BINDLING_SPEED, BINDLING_DETECT_METERS,
            BINDLING_DAMAGE, BINDLING_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else BINDLING_MAX_HP
        super().__init__(x, y, 40, 40, initial_hp, id=id)
        self.speed = BINDLING_SPEED
        self.detect_radius = BINDLING_DETECT_METERS * TILE_SIZE
        self.damage = BINDLING_DAMAGE
        self.damage_cooldown = BINDLING_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

class Miniboss(Enemy):
    """Heavy elite enemy."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            MINIBOSS_MAX_HP, MINIBOSS_SPEED, MINIBOSS_DAMAGE, MINIBOSS_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else MINIBOSS_MAX_HP
        super().__init__(x, y, 64, 64, initial_hp, id=id)
        self.is_miniboss = True
        self.name = "Miniboss"
        self.loot_tier = 2
        self.speed = MINIBOSS_SPEED
        self.detect_radius = 10 * TILE_SIZE
        self.damage = MINIBOSS_DAMAGE
        self.damage_cooldown = MINIBOSS_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

    def on_death(self, state):
        """Rule: Full-Cradle Manifestation. 
        Drop Refined Quill normally, or Anomalous Weapon if player is full.
        """
        from engine.world import WeaponPickup
        player = state.player
        
        if len(player.weapons) < 2:
            # Standard Upgrade: Refined Quill
            weapon_data = {"name": "Refined Quill", "damage": 15}
        else:
            # Anomalous Upgrade: Random powerful variant
            names = ["Anomalous Ink-Bleed", "Anomalous Void-Strike", "Anomalous Cleft-Nib"]
            name = random.choice(names)
            weapon_data = {
                "name": name, 
                "damage": 20 + random.randint(0, 10),
                "modifiers": {"bleed": 5.0} # Placeholder for now
            }
        
        state.world.interactables.append(WeaponPickup((self.x, self.y), weapon_data))
        print(f"[LOOT] Miniboss dropped {weapon_data['name']}")

class MinibossM2(Miniboss):
    """Fast pursuit elite."""
    def __init__(self, x, y, hp=None, id=None):
        super().__init__(x, y, hp, id=id)
        self.name = "Bleeding Scribe"
        self.speed *= 1.4

class MinibossM3(Miniboss):
    """Teleporting elite."""
    def __init__(self, x, y, hp=None, id=None):
        super().__init__(x, y, hp, id=id)
        self.name = "Forgotten Binder"
        self.speed *= 0.7
        self.teleport_cooldown = 4.0
        self._tele_timer = 0.0

    def update(self, dt, state):
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

        player_cx, player_cy = state.player.get_center()
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        dx, dy = player_cx - cx, player_cy - cy
        dist_sq = dx * dx + dy * dy

        if self._tele_timer > 0: self._tele_timer -= dt

        if dist_sq < (120**2) and self._tele_timer <= 0:
            angle = random.uniform(0, 2 * math.pi)
            self.x = player_cx + math.cos(angle) * 300 - self.width / 2
            self.y = player_cy + math.sin(angle) * 300 - self.height / 2
            self._tele_timer = self.teleport_cooldown
            self.vx, self.vy = 0, 0
            return

        super().update(dt, state)

class FlutterEnemy(Enemy):
    """Skittish fleeing enemy."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            FLUTTER_MAX_HP, FLUTTER_SPEED, FLUTTER_DETECT_METERS,
            FLUTTER_DAMAGE, FLUTTER_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else FLUTTER_MAX_HP
        super().__init__(x, y, 16, 16, initial_hp, id=id)
        self.speed = FLUTTER_SPEED
        self.detect_radius = FLUTTER_DETECT_METERS * TILE_SIZE
        self.damage = FLUTTER_DAMAGE
        self.damage_cooldown = FLUTTER_DAMAGE_COOLDOWN
        self._damage_timer = 0.0

    def update(self, dt, state):
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return
        player_cx, player_cy = state.player.get_center()
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        dx, dy = cx - player_cx, cy - player_cy
        dist_sq = dx * dx + dy * dy
        if dist_sq <= (self.detect_radius * self.detect_radius):
            dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0
            if dist > 0.0:
                self.vx, self.vy = (dx / dist) * self.speed, (dy / dist) * self.speed
                self.x += self.vx * dt
                self.y += self.vy * dt
        else:
            self.vx, self.vy = 0, 0

class SmearEnemy(Enemy):
    """Splitting puddle enemy."""
    def __init__(self, x, y, hp=None, id=None, size_multiplier=1.0):
        from constants import (
            SMEAR_MAX_HP, SMEAR_SPEED, SMEAR_DETECT_METERS,
            SMEAR_DAMAGE, SMEAR_DAMAGE_COOLDOWN
        )
        self.size_multiplier = size_multiplier
        initial_hp = hp if hp is not None else SMEAR_MAX_HP * size_multiplier
        w, h = 48 * size_multiplier, 48 * size_multiplier
        super().__init__(x, y, w, h, initial_hp, id=id)
        self.speed = SMEAR_SPEED
        self.detect_radius = SMEAR_DETECT_METERS * TILE_SIZE
        self.damage = SMEAR_DAMAGE
        self.damage_cooldown = SMEAR_DAMAGE_COOLDOWN
        self._damage_timer = 0.0
        self._puddle_timer = 0.0

    def update(self, dt, state):
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return
        self._puddle_timer += dt
        from constants import SMEAR_PUDDLE_CHANCE
        if self._puddle_timer >= 1.0:
            self._puddle_timer = 0.0
            if random.random() < SMEAR_PUDDLE_CHANCE:
                from engine.world import GameObject
                puddle = GameObject((self.x, self.y), (TILE_SIZE, TILE_SIZE))
                puddle.is_solid = False
                puddle.name = "Inkwell Puddle"
                state.world.interactables.append(puddle)
        super().update(dt, state)

    def on_death(self, state):
        if self.size_multiplier >= 1.0:
            s1 = SmearEnemy(self.x - 10, self.y, size_multiplier=0.5)
            s2 = SmearEnemy(self.x + 10, self.y, size_multiplier=0.5)
            state.enemies.append(s1)
            state.enemies.append(s2)

class NightBoss(Miniboss):
    """Dual-encounter boss."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import MINIBOSS_MAX_HP, MINIBOSS_SPEED
        initial_hp = hp if hp is not None else MINIBOSS_MAX_HP * 2
        super().__init__(x, y, initial_hp, id=id)
        self.name = "Night Boss"
        self.speed = MINIBOSS_SPEED * 0.9
        self.loot_tier = 1

class FinalAuthor(Miniboss):
    """The Final Author."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import MINIBOSS_MAX_HP, MINIBOSS_SPEED
        initial_hp = hp if hp is not None else MINIBOSS_MAX_HP * 5
        super().__init__(x, y, initial_hp, id=id)
        self.name = "The Final Author"
        self.width, self.height = 80, 80
        self.speed = MINIBOSS_SPEED * 0.8
        self.detect_radius = 2000.0
        self.loot_tier = 1

ENEMY_REGISTRY = {
    "SlugEnemy": SlugEnemy, "BatEnemy": BatEnemy, "FlutterEnemy": FlutterEnemy,
    "BindlingEnemy": BindlingEnemy, "Miniboss": Miniboss, "MinibossM2": MinibossM2,
    "MinibossM3": MinibossM3, "SmearEnemy": SmearEnemy, "NightBoss": NightBoss,
    "FinalAuthor": FinalAuthor
}

SYMBOL_REGISTRY = {
    'Z': SlugEnemy, 'A': BatEnemy, 'f': FlutterEnemy, 'b': BindlingEnemy,
    'E': Miniboss, '2': MinibossM2, '3': MinibossM3, 's': SmearEnemy, '!': FinalAuthor
}
