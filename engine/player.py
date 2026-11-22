# pylint: disable=multiple-statements,trailing-whitespace,import-outside-toplevel,no-member,access-member-before-definition,attribute-defined-outside-init,unused-import
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
        self.script_modifiers = {
            "max_hp": 0.0,
            "attack": 0.0,
            "speed": 0.0,
            "damage_mitigation": 0.0,
            "bleed": 0.0,
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
        
        # Anomalous weapon state modifiers
        self.negation_timer = 0.0
        self.negation_amount = 0.0
        self.damage_mitigation = 0.0

        # Marginalia Event Buff / Debuff Timers
        self.storm_immunity_timer = 0.0
        self.pristine_ink_shield_timer = 0.0
        self.attack_speed_buff_timer = 0.0
        self.duel_debuff_timer = 0.0
        
        self.flask_latched = False

        # Frozen Peaks frost exposure & Ice Block encasement state
        self.frost_exposure = 0.0
        self.frozen_hits_remaining = 0
        self.frozen_dash_latched = False
        self.just_cracked_ice = False
        self.just_shattered_ice = False
        self._last_dash_held = False

    def reset_frost_state(self):
        """Clear all frost exposure and Ice Block encasement state."""
        self.frost_exposure = 0.0
        self.frozen_hits_remaining = 0
        self.frozen_dash_latched = False
        self.just_cracked_ice = False
        self.just_shattered_ice = False
        self._last_dash_held = False

    def apply_frost_exposure(self, amount, dash_held=None):
        """Accumulate frost exposure; at >= 1.0 encase the player in a 3-Dash Ice Block."""
        if self.frozen_hits_remaining > 0 or amount <= 0.0:
            return False
        from constants import FROZEN_ICE_BLOCK_HITS
        self.frost_exposure = max(0.0, float(self.frost_exposure) + float(amount))
        if self.frost_exposure >= 1.0:
            self.frost_exposure = 0.0
            self.frozen_hits_remaining = int(FROZEN_ICE_BLOCK_HITS)
            held = self._last_dash_held if dash_held is None else bool(dash_held)
            self.frozen_dash_latched = bool(held)
            self.just_cracked_ice = True
            self.vx = 0.0
            self.vy = 0.0
            self.state = PlayerStateEnum.IDLE
            self.stagger_timer = 0.0
            self.attack_timer = 0.0
            self.dash_timer = 0.0
            return True
        return False

    def swap_weapon(self, audio_manager=None):
        """Toggle the active weapon slot if the player is not currently attacking."""
        if self.state != PlayerStateEnum.ATTACKING and len(self.weapons) > 1:
            self.active_weapon_idx = (self.active_weapon_idx + 1) % len(self.weapons)
            if audio_manager:
                audio_manager.play_sfx("weapon_swap.ogg")

    def get_active_weapon(self):
        """Return the currently selected weapon dictionary."""
        return self.weapons[self.active_weapon_idx]

    def apply_script_modifiers(self, mods: dict | None, refill_in_sanctuary: bool = False) -> None:
        """Apply compiled Binder Script stat modifiers and clamp/refill HP safely."""
        old_max = float(self.max_hp)
        was_full = self.hp >= old_max - 1e-4
        cleaned = {
            "max_hp": 0.0,
            "attack": 0.0,
            "speed": 0.0,
            "damage_mitigation": 0.0,
            "bleed": 0.0,
        }
        if isinstance(mods, dict):
            for k in cleaned:
                if k in mods and isinstance(mods[k], (int, float)):
                    cleaned[k] = float(mods[k])
        self.script_modifiers = cleaned
        new_max = float(self.max_hp)
        if refill_in_sanctuary or (was_full and new_max >= old_max):
            self.hp = new_max
        else:
            self.hp = min(float(self.hp), new_max)

    def get_all_modifiers(self):
        """Accumulates all modifiers from all weapons the player possesses."""
        all_mods = {}
        if hasattr(self, 'weapons') and self.weapons:
            for weapon in self.weapons:
                mods = weapon.get("modifiers", {})
                for k, v in mods.items():
                    if k in ("slow_hp_regen", "max_hp_boost", "damage_negation_on_hit", "bleed"):
                        all_mods[k] = all_mods.get(k, 0.0) + v
        return all_mods

    def is_parry_active(self):
        """Returns True if the player is currently in an active parry window."""
        return self.parry_timer > 0.0

    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches,too-many-statements
    def update(
        self, dt, move_dir, walls, actions, attack_pressed=False, flask_pressed=False,
        dash_pressed=False, block_pressed=False, speed_multiplier=1.0, audio_manager=None,
        world_width=None, world_height=None
    ):
        """
        Update player position and state. Returns True if a heal was performed.
        """
        # Clamp HP to new max HP (handles swapping max_hp_boost weapons)
        self.hp = min(self.hp, self.max_hp)

        # Tick HP regeneration from anomalous weapon
        if self.hp > 0:
            all_mods = self.get_all_modifiers()
            if "slow_hp_regen" in all_mods:
                self.hp = min(self.max_hp, self.hp + all_mods["slow_hp_regen"] * dt)

        # Tick negation buff timer
        if hasattr(self, 'negation_timer') and self.negation_timer > 0:
            self.negation_timer -= dt
            if self.negation_timer <= 0:
                self.negation_timer = 0.0
                self.negation_amount = 0.0

        for attr_t in (
            "storm_immunity_timer",
            "pristine_ink_shield_timer",
            "attack_speed_buff_timer",
            "duel_debuff_timer",
        ):
            val_t = getattr(self, attr_t, 0.0)
            if val_t > 0.0:
                setattr(self, attr_t, max(0.0, val_t - dt))
        from constants import (
            DASH_DURATION,
            DASH_COOLDOWN,
            DASH_SPEED_MULTIPLIER,
            DASH_SUBSTEP_MAX_PX,
            BLOCK_SPEED_MULTIPLIER,
            PARRY_WINDOW,
            FROZEN_EXPOSURE_DECAY_RATE,
        )
        world_pixel_width = world_width if world_width is not None else GRID_WIDTH * TILE_SIZE
        world_pixel_height = world_height if world_height is not None else GRID_HEIGHT * TILE_SIZE

        healed = False
        self.just_cracked_ice = False
        self.just_shattered_ice = False
        self._last_dash_held = bool(dash_pressed)

        # 0. Parry Timer Update
        if self.parry_timer > 0:
            self.parry_timer -= dt

        # 0b. Frozen Ice Block Encasement: lock movement/attacks/block/normal-dash & step 3-Dash breakout
        if self.frozen_hits_remaining > 0:
            self.vx = 0.0
            self.vy = 0.0
            self.state = PlayerStateEnum.IDLE
            self.stagger_timer = 0.0
            self.attack_timer = 0.0
            self.dash_timer = 0.0
            if dash_pressed:
                if not self.frozen_dash_latched:
                    self.frozen_dash_latched = True
                    self.frozen_hits_remaining = max(0, self.frozen_hits_remaining - 1)
                    if self.frozen_hits_remaining > 0:
                        self.just_cracked_ice = True
                    else:
                        self.just_shattered_ice = True
            else:
                self.frozen_dash_latched = False
            return False

        # Decay frost exposure when not encased
        if self.frost_exposure > 0.0:
            self.frost_exposure = max(0.0, self.frost_exposure - FROZEN_EXPOSURE_DECAY_RATE * dt)
        self.frozen_dash_latched = False

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
                # Continue dash movement with sub-stepping to prevent wall/edge tunneling
                eff_speed = self.speed + float(getattr(self, "script_modifiers", {}).get("speed", 0.0))
                current_speed = eff_speed * speed_multiplier * DASH_SPEED_MULTIPLIER
                self.vx = self.facing[0] * current_speed
                self.vy = self.facing[1] * current_speed
                total_dx = self.vx * dt
                total_dy = self.vy * dt
                dist = math.hypot(total_dx, total_dy)
                steps = max(1, int(math.ceil(dist / DASH_SUBSTEP_MAX_PX)))
                step_dx = total_dx / steps
                step_dy = total_dy / steps
                for _ in range(steps):
                    self.x += step_dx
                    self.y += step_dy
                    self.x, self.y = resolve_wall_collision(
                        (self.x, self.y, self.width, self.height),
                        walls
                    )
                    self.x = max(0, min(self.x, world_pixel_width - self.width))
                    self.y = max(0, min(self.y, world_pixel_height - self.height))
            return False

        # Update dash cooldown
        if hasattr(self, 'dash_cooldown_timer') and self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= dt

        # Update bind (slowdown) timer
        if hasattr(self, 'bind_timer') and self.bind_timer > 0:
            self.bind_timer -= dt
            speed_multiplier *= 0.4 # 60% slow while bound
        if getattr(self, 'duel_debuff_timer', 0.0) > 0.0:
            speed_multiplier *= 0.7

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
            return

        # 2. Check for attack start
        if attack_pressed:
            self.state = PlayerStateEnum.ATTACKING
            atk_mult = 0.65 if getattr(self, 'attack_speed_buff_timer', 0.0) > 0.0 else 1.0
            self.attack_timer = SWORD_DURATION * atk_mult
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
            eff_speed = self.speed + float(getattr(self, "script_modifiers", {}).get("speed", 0.0))
            current_speed = eff_speed * speed_multiplier
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

        # 6. World Boundary Clamping (active world dimensions, falling back to macro grid size)
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
        """Dynamic max HP including modifiers and compiled Binder Scripts."""
        base = PLAYER_MAX_HP + self.stats.get("max_hp_modifier", 0)
        base += float(getattr(self, "script_modifiers", {}).get("max_hp", 0.0))
        all_mods = self.get_all_modifiers()
        if "max_hp_boost" in all_mods:
            base += all_mods["max_hp_boost"]
        return base

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
        if getattr(self, 'negation_timer', 0.0) > 0.0: overlays.append("NEGATION")
        
        return {
            "base": base,
            "posture": posture,
            "overlays": overlays,
            "facing": self.facing,
            "timer": self.attack_timer if self.state == PlayerStateEnum.ATTACKING else 0.0,
            "progress": 0.0 
        }

    def use_flask(self, audio_manager=None):
        """Consume a flask charge to restore HP; play flask_empty.ogg if empty or at full HP."""
        if self.flask_charges > 0 and self.hp < self.max_hp:
            self.flask_charges -= 1
            self.hp = min(self.max_hp, self.hp + FLASK_HEAL_AMOUNT)
            if audio_manager:
                audio_manager.play_sfx("flask_use.ogg")
            return True
        if audio_manager:
            from constants import FLASK_EMPTY_SFX
            audio_manager.play_sfx(FLASK_EMPTY_SFX)
        return False

    def take_damage(
        self, amount: float, bypass_stagger: bool = False, audio_manager=None, game_state=None
    ) -> None:
        """Apply damage to the player; clamp at zero.

        Includes conditional defensive parsing based on Edification level.
        If bypass_stagger is True, the player's state is not changed.
        """
        # Pristine Ink Shield (from The Unblotted Margin Act 2) blocks incoming damage
        if getattr(self, 'pristine_ink_shield_timer', 0.0) > 0.0:
            return

        # Apply temporary damage negation from previous discrete hit
        if getattr(self, 'negation_timer', 0) > 0:
            if bypass_stagger:
                from constants import WARD_BUFF_RAIN_REDUCTION
                amount *= (1.0 - WARD_BUFF_RAIN_REDUCTION)
            else:
                amount = max(0.0, amount - self.negation_amount)

        # 0. Damage Immunity (i-frames) during Stagger or Dash (bypassed while encased in Ice Block)
        is_frozen = getattr(self, "frozen_hits_remaining", 0) > 0
        if not is_frozen and self.state in (PlayerStateEnum.STAGGERED, PlayerStateEnum.DASHING):
            if not bypass_stagger: # Hazards like rain still tick
                return

        # 1. Apply active blocking / warding reduction
        was_blocked = False
        if self.state == PlayerStateEnum.BLOCKING:
            if bypass_stagger:
                from constants import WARDING_RAIN_DAMAGE_REDUCTION
                amount *= (1.0 - WARDING_RAIN_DAMAGE_REDUCTION)
            else:
                from constants import BLOCK_DAMAGE_REDUCTION
                amount *= BLOCK_DAMAGE_REDUCTION
                was_blocked = True
                if audio_manager:
                    audio_manager.play_sfx("player_block.ogg")

        # 1b. Apply compiled Binder Script + persistent run damage mitigation (e.g., Unblotted Margin)
        from constants import BINDER_MAX_DAMAGE_MITIGATION
        script_mit = float(getattr(self, "script_modifiers", {}).get("damage_mitigation", 0.0))
        bonus_mit = max(0.0, float(getattr(self, "damage_mitigation", 0.0)))
        total_mit = min(BINDER_MAX_DAMAGE_MITIGATION, max(0.0, script_mit)) + bonus_mit
        if total_mit > 0.0:
            amount *= (1.0 - min(0.85, total_mit))

        # 2. Apply passive Edification parsing (Global Level)
        from constants import PROWESS_ATTACK_STEP, FORTIFICATION_HP_STEP
        prowess = self.stats.get("attack_modifier", 0)
        fort = self.stats.get("max_hp_modifier", 0)
        prowess_lvl = 1 + (prowess // PROWESS_ATTACK_STEP)
        fort_lvl = 1 + (fort // FORTIFICATION_HP_STEP)
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

        # Play quiet combat hurt SFX on unblocked combat hits
        if not bypass_stagger and not was_blocked and amount > 0 and audio_manager:
            from constants import PLAYER_HURT_SFX
            audio_manager.play_sfx(PLAYER_HURT_SFX)

        # Spawn Glyph Splatter on player damage
        if amount > 0 and game_state and hasattr(game_state, 'glyph_particles'):
            from constants import COLOR_PARCHMENT_WHITE
            cx, cy = self.get_center()
            game_state.glyph_particles.spawn_burst(cx, cy, color=COLOR_PARCHMENT_WHITE)

        # Check active weapon for damage negation on hit modifier (discrete combat hits only)
        if not bypass_stagger:
            all_mods = self.get_all_modifiers()
            if "damage_negation_on_hit" in all_mods and amount > 0:
                self.negation_timer = 3.0
                self.negation_amount = all_mods["damage_negation_on_hit"]
        
        # Only stagger if they took actual damage, stagger isn't bypassed, and not encased in Ice Block
        if not bypass_stagger and not is_frozen and self.hp > 0 and amount > 0:
            self.state = PlayerStateEnum.STAGGERED
            self.stagger_timer = STAGGER_DURATION
            self.vx, self.vy = 0, 0
        elif is_frozen and self.hp > 0:
            self.state = PlayerStateEnum.IDLE
            self.vx, self.vy = 0.0, 0.0
