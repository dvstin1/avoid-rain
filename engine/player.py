"""
Core player logic and state management.
"""
import math
from enum import Enum
from constants import (
    PLAYER_SPEED, SCREEN_WIDTH, SCREEN_HEIGHT,
    PLAYER_WIDTH, PLAYER_HEIGHT, SWORD_DURATION,
    GRID_WIDTH, GRID_HEIGHT, TILE_SIZE,
    PLAYER_MAX_HP, FLASK_MAX_CHARGES, FLASK_HEAL_AMOUNT,
    STAGGER_DURATION, SWORD_DAMAGE
)
from engine.physics import resolve_wall_collision

class PlayerStateEnum(Enum):
    """Possible states for the player."""
    IDLE = "idle"
    MOVING = "moving"
    ATTACKING = "attacking"
    DASHING = "dashing"
    STAGGERED = "staggered"
    BLOCKING = "blocking"

class Player:
    """Represents the player in the game engine."""
    # pylint: disable=too-many-instance-attributes
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.name = "Player"
        self.vx = 0.0
        self.vy = 0.0
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.speed = PLAYER_SPEED
        self.state = PlayerStateEnum.IDLE
        self.facing = (1, 0) # Direction vector
        self.attack_timer = 0.0
        self.stagger_timer = 0.0
        self.current_interactable = None
        self.stats = {
            "attack_modifier": 0,
            "max_hp_modifier": 0
        }
        self.hp = PLAYER_MAX_HP
        self.flask_charges = FLASK_MAX_CHARGES
        # Dual-Weapon Inventory Management
        self.weapons = [{"name": "Initial Quill", "damage": SWORD_DAMAGE}]
        self.active_weapon_idx = 0
        self.has_rested_this_session = False
        self.active_track_name = "sanctuary_hub.ogg"
        self.miniboss_cooldown_accumulator = 0.0
        self.is_exposed = False
        
        # Parry Mechanics
        self.parry_timer = 0.0
        self.was_blocking = False
        
        # Attack Latching (Prevent multi-hit per swing)
        self.hit_entities_this_attack = set()
        self.hit_props_this_attack = set()
        
        self.flask_latched = False

    def swap_weapon(self, audio_manager=None):
        """Toggle the active weapon slot if the player is not currently attacking."""
        if self.state != PlayerStateEnum.ATTACKING and len(self.weapons) > 1:
            self.active_weapon_idx = (self.active_weapon_idx + 1) % len(self.weapons)
            if audio_manager:
                audio_manager.play_sfx("weapon_swap.ogg")

    def get_active_weapon(self):
        """Return the currently selected weapon dictionary."""
        return self.weapons[self.active_weapon_idx]

    def is_parry_active(self):
        """Returns True if the player is currently in an active parry window."""
        return self.parry_timer > 0.0

    def update(
        self, dt, move_dir, walls, actions, attack_pressed=False, flask_pressed=False,
        dash_pressed=False, block_pressed=False, speed_multiplier=1.0, audio_manager=None
    ):
        """
        Update player position and state. Returns True if a heal was performed.
        """
        from constants import DASH_DURATION, DASH_COOLDOWN, DASH_SPEED_MULTIPLIER, BLOCK_SPEED_MULTIPLIER, PARRY_WINDOW

        healed = False
        
        # 0. Parry Timer Update
        if self.parry_timer > 0:
            self.parry_timer -= dt

        if self.state == PlayerStateEnum.STAGGERED:
            self.stagger_timer -= dt
            if self.stagger_timer <= 0:
                self.state = PlayerStateEnum.IDLE
            return False

        if self.state == PlayerStateEnum.ATTACKING:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.state = PlayerStateEnum.IDLE
            return False

        if self.state == PlayerStateEnum.DASHING:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.state = PlayerStateEnum.IDLE
            else:
                # Continue dash movement
                current_speed = self.speed * speed_multiplier * DASH_SPEED_MULTIPLIER
                self.vx = self.facing[0] * current_speed
                self.vy = self.facing[1] * current_speed
                self.x += self.vx * dt
                self.y += self.vy * dt
                self.x, self.y = resolve_wall_collision(
                    (self.x, self.y, self.width, self.height),
                    walls
                )
            return False

        # Update dash cooldown
        if hasattr(self, 'dash_cooldown_timer') and self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= dt

        # Update bind (slowdown) timer
        if hasattr(self, 'bind_timer') and self.bind_timer > 0:
            self.bind_timer -= dt
            speed_multiplier *= 0.4 # 60% slow while bound

        # 0. Handle Flask
        if flask_pressed:
            if not self.flask_latched:
                if self.use_flask(audio_manager=audio_manager):
                    healed = True
                self.flask_latched = True
        else:
            self.flask_latched = False

        dx, dy = move_dir

        # 1. Update facing direction
        if dx != 0 or dy != 0:
            # Normalize for facing
            mag = math.sqrt(dx*dx + dy*dy)
            self.facing = (dx/mag, dy/mag)

        # Handle Dash Initialization
        if dash_pressed and getattr(self, 'dash_cooldown_timer', 0) <= 0:
            self.state = PlayerStateEnum.DASHING
            self.dash_timer = DASH_DURATION
            self.dash_cooldown_timer = DASH_COOLDOWN
            self.parry_timer = PARRY_WINDOW # Trigger Parry Window
            if audio_manager:
                audio_manager.play_sfx("player_dash.ogg")
            return

        # 2. Check for attack start
        if attack_pressed:
            self.state = PlayerStateEnum.ATTACKING
            self.attack_timer = SWORD_DURATION
            self.vx, self.vy = 0, 0
            self.hit_entities_this_attack.clear()
            self.hit_props_this_attack.clear()
            return

        # Apply blocking state
        if block_pressed:
            if not self.was_blocking:
                self.parry_timer = PARRY_WINDOW # Trigger Parry Window
            self.state = PlayerStateEnum.BLOCKING
            speed_multiplier *= BLOCK_SPEED_MULTIPLIER
        
        self.was_blocking = block_pressed

        # 3. Normalize movement
        magnitude = math.sqrt(dx*dx + dy*dy)
        if magnitude > 0:
            current_speed = self.speed * speed_multiplier
            self.vx = (dx / magnitude) * current_speed
            self.vy = (dy / magnitude) * current_speed
            if not block_pressed:
                self.state = PlayerStateEnum.MOVING
        else:
            self.vx = 0.0
            self.vy = 0.0
            if not block_pressed:
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
        
        return healed

    def get_pos(self):
        """Returns the current position as a tuple."""
        return (self.x, self.y)

    def get_center(self):
        """Returns the center point of the player."""
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def rect(self):
        """Standard rect tuple (x, y, w, h) for collision logic."""
        return (self.x, self.y, self.width, self.height)

    @property
    def max_hp(self):
        """Dynamic max HP including modifiers."""
        return PLAYER_MAX_HP + self.stats.get("max_hp_modifier", 0)

    def get_visual_packet(self):
        """Returns a composable packet of visual intents for the renderer."""
        # 1. Base Layer
        base = "IDLE"
        if self.state == PlayerStateEnum.MOVING: base = "RUN"
        if self.state == PlayerStateEnum.ATTACKING: base = "ATTACK"
        if self.state == PlayerStateEnum.DASHING: base = "DASH"
        if self.state == PlayerStateEnum.BLOCKING: base = "BLOCK"
        
        # 2. Posture Layer
        posture = "READY"
        if self.hp / self.max_hp < 0.3: posture = "WOUNDED"
        if self.state == PlayerStateEnum.STAGGERED: posture = "STAGGERED"
        
        # 3. Overlays
        overlays = []
        if getattr(self, 'bind_timer', 0) > 0: overlays.append("BIND")
        if self.is_exposed: overlays.append("EXPOSED")
        if self.parry_timer > 0: overlays.append("PARRY_WINDOW")
        
        return {
            "base": base,
            "posture": posture,
            "overlays": overlays,
            "facing": self.facing,
            "timer": self.attack_timer if self.state == PlayerStateEnum.ATTACKING else 0.0,
            "progress": 0.0 
        }

    def use_flask(self, audio_manager=None):
        """Consume a flask charge to restore HP. Returns True if heal performed."""
        if self.flask_charges > 0 and self.hp < self.max_hp:
            self.flask_charges -= 1
            self.hp = min(self.max_hp, self.hp + FLASK_HEAL_AMOUNT)
            if audio_manager:
                audio_manager.play_sfx("flask_use.ogg")
            return True
        return False

    def take_damage(self, amount: float, bypass_stagger: bool = False, audio_manager=None) -> None:
        """Apply damage to the player; clamp at zero.

        Includes conditional defensive parsing based on Edification level.
        If bypass_stagger is True, the player's state is not changed.
        """
        # 0. Damage Immunity (i-frames) during Stagger or Dash
        if self.state in (PlayerStateEnum.STAGGERED, PlayerStateEnum.DASHING):
            if not bypass_stagger: # Hazards like rain still tick
                return

        # 1. Apply active blocking reduction
        if self.state == PlayerStateEnum.BLOCKING:
            from constants import BLOCK_DAMAGE_REDUCTION
            amount *= BLOCK_DAMAGE_REDUCTION
            if audio_manager:
                audio_manager.play_sfx("player_block.ogg")

        # 2. Apply passive Edification parsing (Global Level)
        prowess = self.stats.get("attack_modifier", 0)
        fort = self.stats.get("max_hp_modifier", 0)
        prowess_lvl = 1 + (prowess // 5)
        fort_lvl = 1 + (fort // 10)
        edif = prowess_lvl + fort_lvl - 1
        
        hp_ratio = self.hp / self.max_hp if self.max_hp > 0 else 0

        # Rule 1: Pristine Concentration (> 95% HP)
        if hp_ratio > 0.95:
            # reduce by (Edification / 2)%
            reduction = (edif / 2.0) / 100.0
            amount *= (1.0 - reduction)
        # Rule 2: Desperate Synthesis (< 30% HP)
        elif hp_ratio < 0.30:
            # reduce by (Edification)%
            reduction = edif / 100.0
            amount *= (1.0 - reduction)

        self.hp = max(0.0, self.hp - amount)
        
        # Only stagger if they took actual damage and stagger isn't bypassed
        if not bypass_stagger and self.hp > 0 and amount > 0:
            self.state = PlayerStateEnum.STAGGERED
            self.stagger_timer = STAGGER_DURATION
            self.vx, self.vy = 0, 0
