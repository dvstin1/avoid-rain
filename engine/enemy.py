"""
Enemy AI and behavior definitions.
Inherits from Actor for the Stanza patrol system.
"""
import math
import random
import pygame
from constants import TILE_SIZE
from engine.physics import check_aabb_collision, resolve_wall_collision
from engine.actor import Actor, ActorState

class Enemy(Actor):
    """Base class for all enemy types."""
    def __init__(self, x, y, width, height, hp, id=None, name="Enemy"):
        super().__init__(x, y, width, height, hp, id=id, name=name)
        self.attack_type = "LUNGE" # Default for non-weapon enemies
        self.is_parryable = False

    def attempt_damage_player(self, state):
        """Apply damage on contact during STRIKE frames, handling parries for all players."""
        # 1. Identify all potential victims (Local + Remote)
        potential_victims = []
        if state.player:
            potential_victims.append(("local", None, state.player))
        
        remote_data = getattr(state.network_manager, 'remote_players', {})
        for addr, p_data in remote_data.items():
            victim_rect = (p_data["x"], p_data["y"], 40, 40) # Standard Player size
            potential_victims.append(("remote", addr, victim_rect))

        for v_type, v_id, v_obj in potential_victims:
            v_rect = v_obj if v_type == "remote" else v_obj.rect
            
            if check_aabb_collision(self.get_rect(), v_rect):
                if v_type == "local":
                    # print(f"[DEBUG] Enemy {getattr(self, 'network_id', -1)} hit LOCAL player")
                    # Local Player Parry Check
                    if self.is_parryable and v_obj.is_parry_active():
                        self._handle_parry(state)
                        return True
                    
                    # Local Damage
                    try:
                        v_obj.take_damage(self.damage, audio_manager=getattr(state, 'audio_manager', None))
                        return True
                    except Exception: pass
                else:
                    # Remote Player Damage (Host authoritative view)
                    if v_id in state.network_manager.remote_players:
                        state.network_manager.remote_players[v_id]["hp"] -= self.damage
                        return True
        return False

    def _handle_parry(self, state):
        """Rule: High-Skill Reward. Stagger enemy and reset dash."""
        from constants import PARRY_STUN_DURATION, SCREEN_SHAKE_DURATION
        
        # Enemy Stun
        self.state = ActorState.RECOVERY
        self.combat_timer = PARRY_STUN_DURATION
        self.stagger_timer = PARRY_STUN_DURATION
        
        # Player Reward
        state.player.dash_cooldown_timer = 0.0 # Kinetic Reset
        state.shake_timer = SCREEN_SHAKE_DURATION # Intense feedback
        
        # Signal Feedback
        if hasattr(state, 'audio_manager') and state.audio_manager:
            state.audio_manager.play_sfx("combat_parry.ogg")
        
        # Spawn Ink Spark
        if hasattr(state, 'parry_effects'):
            state.parry_effects.append({'pos': state.player.get_center(), 'time': 0.3})
        
        print(f"[COMBAT] Parry Success against {self.name}!")

class SlugEnemy(Enemy):
    """A slow, low-tier enemy."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            SLUG_MAX_HP, SLUG_SPEED, SLUG_DETECT_METERS,
            SLUG_DAMAGE, SLUG_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else SLUG_MAX_HP
        super().__init__(x, y, 32, 32, initial_hp, id=id, name="Slug")
        self.speed = SLUG_SPEED
        self.detect_radius = SLUG_DETECT_METERS * TILE_SIZE
        self.damage = SLUG_DAMAGE
        self.attack_cooldown = SLUG_DAMAGE_COOLDOWN
        
        # Slow, predictable telegraphs
        self.wind_up_duration = 0.6
        self.strike_duration = 0.3
        self.recovery_duration = 0.8
        self.patrol_speed_multiplier = 0.3

class BatEnemy(Enemy):
    """A fast, erratic enemy."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            BAT_MAX_HP, BAT_SPEED, BAT_DETECT_METERS,
            BAT_DAMAGE, BAT_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else BAT_MAX_HP
        super().__init__(x, y, 24, 24, initial_hp, id=id, name="Bat")
        self.speed = BAT_SPEED
        self.detect_radius = BAT_DETECT_METERS * TILE_SIZE
        self.damage = BAT_DAMAGE
        self.attack_cooldown = BAT_DAMAGE_COOLDOWN
        
        # Fast telegraphs
        self.wind_up_duration = 0.3
        self.strike_duration = 0.2
        self.recovery_duration = 0.4
        self._angle = random.uniform(0, 2 * math.pi)

    def _update_chase(self, dt, state):
        """Move toward the active target with a sine-wave oscillation."""
        if not self.active_target:
            self.state = ActorState.IDLE
            return

        target_cx, target_cy = self.active_target
        cx, cy = self.get_center()
        dx, dy = target_cx - cx, target_cy - cy
        dist = math.sqrt(dx*dx + dy*dy)

        if dist > 0.0:
            # Pursuit vector
            vx, vy = (dx / dist) * self.speed, (dy / dist) * self.speed
            
            # Erratic sine wave perpendicular to movement
            self._angle += dt * 10.0
            perp_x, perp_y = -vy, vx
            
            self.x += (vx + perp_x * math.sin(self._angle)) * dt
            self.y += (vy + perp_y * math.sin(self._angle)) * dt
            
            walls = state.world.get_nearby_walls(self.get_rect())
            self.x, self.y = resolve_wall_collision(self.get_rect(), walls)

class BindlingEnemy(Enemy):
    """A harasser enemy that binds the player."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            BINDLING_MAX_HP, BINDLING_SPEED, BINDLING_DETECT_METERS,
            BINDLING_DAMAGE, BINDLING_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else BINDLING_MAX_HP
        super().__init__(x, y, 40, 40, initial_hp, id=id, name="Bindling")
        self.speed = BINDLING_SPEED
        self.detect_radius = BINDLING_DETECT_METERS * TILE_SIZE
        self.damage = BINDLING_DAMAGE
        self.attack_cooldown = BINDLING_DAMAGE_COOLDOWN
        self.attack_type = "BIND"

        self.wind_up_duration = 0.4
        self.strike_duration = 0.2
        self.recovery_duration = 0.5


class Boss(Enemy):
    """Base class for all Elites and Bosses. Implements weapon telegraphs and parrying."""
    def __init__(self, x, y, width, height, hp, id=None, name="Boss"):
        super().__init__(x, y, width, height, hp, id=id, name=name)
        self.is_miniboss = True # Music/Spawn trigger flag
        self.is_parryable = True
        
        # Elite Telegraphs
        self.wind_up_duration = 0.5
        self.strike_duration = 0.25
        self.recovery_duration = 0.6
        self.attack_type = "THRUST"

    def _update_wind_up(self, dt, state):
        """Randomize attack type at the start of a wind-up."""
        if self.combat_timer == self.wind_up_duration:
            self.attack_type = random.choice(["THRUST", "SWING"])
            print(f"[COMBAT] {self.name} preparing {self.attack_type}!")
            
            # Balancing: Swings take slightly longer to wind up
            if self.attack_type == "SWING":
                self.combat_timer += 0.2 
        
        super()._update_wind_up(dt, state)

class Miniboss(Boss):
    """Loot-dropping elite enemy."""
    def __init__(self, x, y, hp=None, id=None, name="Miniboss"):
        from constants import (
            MINIBOSS_MAX_HP, MINIBOSS_SPEED, MINIBOSS_DAMAGE, MINIBOSS_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else MINIBOSS_MAX_HP
        super().__init__(x, y, 64, 64, initial_hp, id=id, name=name)
        self.loot_tier = 2
        self.speed = MINIBOSS_SPEED
        self.detect_radius = 10 * TILE_SIZE
        self.damage = MINIBOSS_DAMAGE
        self.attack_cooldown = MINIBOSS_DAMAGE_COOLDOWN

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

    def _update_chase(self, dt, state):
        if not self.active_target:
            self.state = ActorState.IDLE
            return

        target_cx, target_cy = self.active_target
        cx, cy = self.x + self.width / 2, self.y + self.height / 2
        dx, dy = target_cx - cx, target_cy - cy
        dist_sq = dx * dx + dy * dy

        if self._tele_timer > 0: self._tele_timer -= dt

        if dist_sq < (120**2) and self._tele_timer <= 0:
            angle = random.uniform(0, 2 * math.pi)
            self.x = target_cx + math.cos(angle) * 300 - self.width / 2
            self.y = target_cy + math.sin(angle) * 300 - self.height / 2
            self._tele_timer = self.teleport_cooldown
            self.vx, self.vy = 0, 0
            return

        super()._update_chase(dt, state)

class FlutterEnemy(Enemy):
    """Skittish fleeing enemy."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            FLUTTER_MAX_HP, FLUTTER_SPEED, FLUTTER_DETECT_METERS,
            FLUTTER_DAMAGE, FLUTTER_DAMAGE_COOLDOWN
        )
        initial_hp = hp if hp is not None else FLUTTER_MAX_HP
        super().__init__(x, y, 16, 16, initial_hp, id=id, name="Flutter")
        self.speed = FLUTTER_SPEED
        self.detect_radius = FLUTTER_DETECT_METERS * TILE_SIZE
        self.damage = FLUTTER_DAMAGE
        self.attack_cooldown = FLUTTER_DAMAGE_COOLDOWN
        
        self.wind_up_duration = 0.2
        self.strike_duration = 0.2
        self.recovery_duration = 0.3

    def _update_chase(self, dt, state):
        """Fleeing behavior."""
        if not self.active_target:
            self.state = ActorState.IDLE
            return

        target_cx, target_cy = self.active_target
        cx, cy = self.get_center()
        dx, dy = cx - target_cx, cy - target_cy
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0.0:
            self.vx, self.vy = (dx / dist) * self.speed, (dy / dist) * self.speed
            self.x += self.vx * dt
            self.y += self.vy * dt
            walls = state.world.get_nearby_walls(self.get_rect())
            self.x, self.y = resolve_wall_collision(self.get_rect(), walls)

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
        super().__init__(x, y, w, h, initial_hp, id=id, name="Smear")
        self.speed = SMEAR_SPEED
        self.detect_radius = SMEAR_DETECT_METERS * TILE_SIZE
        self.damage = SMEAR_DAMAGE
        self.attack_cooldown = SMEAR_DAMAGE_COOLDOWN
        self._puddle_timer = 0.0

        self.wind_up_duration = 0.5
        self.strike_duration = 0.3
        self.recovery_duration = 0.6

        self._puddle_timer = 0.0

    def update(self, dt, state):
        """Custom update to handle periodic puddle drops."""
        # Process puddle timer regardless of stagger
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
        
        # Then call standard actor update (handles stagger and movement)
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

class FinalAuthor(Boss):
    """The Final Author."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import MINIBOSS_MAX_HP, MINIBOSS_SPEED
        initial_hp = hp if hp is not None else MINIBOSS_MAX_HP * 5
        super().__init__(x, y, 80, 80, initial_hp, id=id, name="The Final Author")
        self.speed = MINIBOSS_SPEED * 0.8
        self.detect_radius = 2000.0
        self.loot_tier = 0 # No rewards for the final redaction
        
        self.wind_up_duration = 0.7
        self.strike_duration = 0.4
        self.recovery_duration = 1.0

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
