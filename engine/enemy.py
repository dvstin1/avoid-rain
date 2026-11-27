# copyright 2026 Dustin Massop, License: GPLv2
"""
Enemy AI and behavior definitions.
Inherits from Actor for the Stanza patrol system.
"""
# pylint: disable=too-many-arguments,too-many-positional-arguments,redefined-builtin
# pylint: disable=import-outside-toplevel,too-many-instance-attributes,arguments-renamed
# pylint: disable=broad-exception-caught,multiple-statements,unused-import

import math
import random
from constants import TILE_SIZE
from engine.physics import check_aabb_collision, resolve_wall_collision
from engine.actor import Actor, ActorState

class Enemy(Actor):
    """Base class for all enemy types."""
    def __init__(self, x, y, width, height, hp, id=None, name="Enemy"):
        super().__init__(x, y, width, height, hp, id=id, name=name)
        self.attack_type = "LUNGE" # Default for non-weapon enemies
        self.is_parryable = False
        self.damage = 0
        self.is_empowered = False
        self.network_id = -1
        self.persistent_pursuit = False
        self._stall_timer = 0.0
        self._phase_timer = 0.0
        self.dormant_boss_summon = False
        self.summoning_emerge_timer = 0.0

    def is_summoning_or_dormant(self) -> bool:
        """Return True while this enemy is awaiting proximity summon or emerging from a ritual seal."""
        return bool(getattr(self, "dormant_boss_summon", False)) or (
            float(getattr(self, "summoning_emerge_timer", 0.0) or 0.0) > 0.0
        )

    def take_damage(self, amount, bypass_stagger=False):
        """Ignore damage while dormant or emerging from the Ink-Unsealing ritual."""
        if self.is_summoning_or_dormant():
            return
        super().take_damage(amount, bypass_stagger=bypass_stagger)

    def update(self, dt, state):
        """Freeze AI while dormant or emerging from the summoning seal, otherwise run Actor AI."""
        if self.is_summoning_or_dormant():
            self.vx = 0.0
            self.vy = 0.0
            return
        super().update(dt, state)

    def apply_act_scaling(
        self,
        hp_multiplier=1.0,
        damage_multiplier=1.0,
        empowered=None,
        speed_multiplier=1.0,
        cooldown_multiplier=1.0,
    ):
        """Scale enemy HP, damage, movement speed, and attack cooldown/cadence for Act escalation."""
        if hp_multiplier != 1.0:
            self.max_hp = float(self.max_hp) * float(hp_multiplier)
            self.hp = float(self.hp) * float(hp_multiplier)
        if damage_multiplier != 1.0:
            self.damage = float(self.damage) * float(damage_multiplier)
        if speed_multiplier != 1.0:
            self.speed = float(self.speed) * float(speed_multiplier)
            if hasattr(self, "pounce_speed"):
                self.pounce_speed = float(self.pounce_speed) * float(speed_multiplier)
        if cooldown_multiplier != 1.0:
            cd_mult = float(cooldown_multiplier)
            self.attack_cooldown = max(0.2, float(self.attack_cooldown) * cd_mult)
            cadence_mult = 1.0 - (1.0 - cd_mult) * 0.5
            self.wind_up_duration = max(0.18, float(self.wind_up_duration) * cadence_mult)
            self.recovery_duration = max(0.22, float(self.recovery_duration) * cadence_mult)
        if empowered is None:
            self.is_empowered = (hp_multiplier > 1.0 or damage_multiplier > 1.0)
        else:
            self.is_empowered = bool(empowered)

    def attempt_damage_player(self, state):
        """Apply damage on contact during STRIKE frames, handling parries for all players."""
        if self.is_summoning_or_dormant():
            return False
        # 1. Identify all potential victims (Local + Remote); skip resting local player in Respite UI
        potential_victims = []
        if state.player and getattr(state, "active_respite", None) is None:
            potential_victims.append(("local", None, state.player))
        
        remote_data = getattr(state.network_manager, 'remote_players', {})
        for addr, p_data in remote_data.items():
            victim_rect = (p_data["x"], p_data["y"], 40, 40) # Standard Player size
            potential_victims.append(("remote", addr, victim_rect))

        body_rect = self.get_rect()
        if hasattr(self, 'get_attack_hitbox'):
            source_rect = self.get_attack_hitbox()
        else:
            source_rect = body_rect

        for v_type, v_id, v_obj in potential_victims:
            v_rect = v_obj if v_type == "remote" else v_obj.rect

            if check_aabb_collision(source_rect, v_rect) or check_aabb_collision(body_rect, v_rect):
                if v_type == "local":
                    # Local Player Parry Check
                    if self.is_parryable and v_obj.is_parry_active():
                        self._handle_parry(state)
                        return True
                    
                    # Local Damage
                    try:
                        try:
                            v_obj.take_damage(
                                self.damage,
                                audio_manager=getattr(state, 'audio_manager', None),
                                game_state=state,
                            )
                        except TypeError:
                            v_obj.take_damage(
                                self.damage,
                                audio_manager=getattr(state, 'audio_manager', None),
                            )
                        
                        # Phase 4: Status Effects (BIND)
                        if self.attack_type == "BIND" and hasattr(v_obj, 'bind_timer'):
                            from constants import BIND_DURATION
                            v_obj.bind_timer = BIND_DURATION

                        return True
                    except Exception:  # pylint: disable=broad-exception-caught
                        pass
                else:
                    # Remote Player Damage (Host authoritative view)
                    if v_id in state.network_manager.remote_players:
                        from constants import BINDER_MAX_DAMAGE_MITIGATION
                        p_data = state.network_manager.remote_players[v_id]
                        get_cached = getattr(state, "_get_cached_client_state", None)
                        cached = (
                            get_cached(v_id, p_data.get("identity"))
                            if callable(get_cached)
                            else {}
                        )
                        s_mods = cached.get("script_modifiers") if isinstance(cached, dict) else None
                        if not isinstance(s_mods, dict):
                            s_mods = p_data.get("script_modifiers", {})
                        mit = 0.0
                        if isinstance(s_mods, dict):
                            mit = min(
                                BINDER_MAX_DAMAGE_MITIGATION,
                                max(0.0, float(s_mods.get("damage_mitigation", 0.0))),
                            )
                        p_data["hp"] = max(0.0, p_data["hp"] - self.damage * (1.0 - mit))
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
        if hasattr(state, "trigger_shake"):
            state.trigger_shake(SCREEN_SHAKE_DURATION)
        elif getattr(state, "screen_shake_enabled", True):
            state.shake_timer = SCREEN_SHAKE_DURATION  # Intense feedback
        if hasattr(state, "trigger_rumble"):
            state.trigger_rumble("parry")
        
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

    def get_visual_packet(self):
        packet = super().get_visual_packet()
        packet["color_hint"] = (100, 100, 120) # Deep Slug Grey
        return packet

    def get_attack_hitbox(self):
        """Return a 38x38 forward bite hitbox during STRIKE (body rect otherwise)."""
        if self.state != ActorState.STRIKE:
            return self.get_rect()
        from constants import SLUG_ATTACK_HITBOX_OFFSET, SLUG_ATTACK_HITBOX_SIZE
        cx, cy = self.get_center()
        dx, dy = self.facing
        if self.active_target:
            tx, ty = self.active_target
            tdx, tdy = tx - cx, ty - cy
            if math.hypot(tdx, tdy) > 0.001:
                dx, dy = tdx, tdy
        mag = math.hypot(dx, dy)
        if mag > 0.001:
            ux, uy = dx / mag, dy / mag
        else:
            ux, uy = 1.0, 0.0
        size = float(SLUG_ATTACK_HITBOX_SIZE)
        offset = float(SLUG_ATTACK_HITBOX_OFFSET)
        hx = cx + ux * offset - size / 2.0
        hy = cy + uy * offset - size / 2.0
        return (hx, hy, size, size)

class BatEnemy(Enemy):
    """A fast, erratic enemy."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            BAT_MAX_HP, BAT_SPEED, BAT_DETECT_METERS,
            BAT_DAMAGE, BAT_DAMAGE_COOLDOWN,
            BAT_SINE_AMPLITUDE, BAT_SWOOP_SPEED_MULTIPLIER,
        )
        initial_hp = hp if hp is not None else BAT_MAX_HP
        super().__init__(x, y, 24, 24, initial_hp, id=id, name="Bat")
        self.speed = BAT_SPEED
        self.detect_radius = BAT_DETECT_METERS * TILE_SIZE
        self.damage = BAT_DAMAGE
        self.attack_cooldown = BAT_DAMAGE_COOLDOWN
        self.sine_amplitude = BAT_SINE_AMPLITUDE
        self.swoop_speed_multiplier = BAT_SWOOP_SPEED_MULTIPLIER
        self.swoop_dir = (1.0, 0.0)
        self._swoop_locked = False

        # Fast telegraphs
        self.wind_up_duration = 0.3
        self.strike_duration = 0.2
        self.recovery_duration = 0.4
        self._angle = random.uniform(0, 2 * math.pi)

    def get_visual_packet(self):
        packet = super().get_visual_packet()
        packet["color_hint"] = (150, 50, 150) # Bat Purple
        return packet

    def _lock_swoop_vector(self):
        """Lock a normalized swoop direction toward the active target or current facing."""
        if self.active_target:
            tx, ty = self.active_target
            cx, cy = self.get_center()
            dx, dy = tx - cx, ty - cy
            mag = math.hypot(dx, dy)
            if mag > 0.001:
                self.swoop_dir = (dx / mag, dy / mag)
                self.facing = self.swoop_dir
                self._swoop_locked = True
                return
        fx, fy = self.facing
        mag = math.hypot(fx, fy)
        if mag > 0.001:
            self.swoop_dir = (fx / mag, fy / mag)
        else:
            self.swoop_dir = (1.0, 0.0)
        self.facing = self.swoop_dir
        self._swoop_locked = True

    def get_attack_hitbox(self):
        """Return a 28x28 tight swoop hitbox shifted forward along the bat's swoop vector."""
        from constants import BAT_SWOOP_HITBOX_SIZE, BAT_SWOOP_HITBOX_OFFSET
        cx, cy = self.get_center()
        dx, dy = self.swoop_dir if self._swoop_locked else self.facing
        mag = math.hypot(dx, dy)
        if mag > 0.001:
            ux, uy = dx / mag, dy / mag
        else:
            ux, uy = 1.0, 0.0
        size = float(BAT_SWOOP_HITBOX_SIZE)
        offset = float(BAT_SWOOP_HITBOX_OFFSET)
        hx = cx + ux * offset - size / 2.0
        hy = cy + uy * offset - size / 2.0
        return (hx, hy, size, size)

    def _update_wind_up(self, dt, game_state):
        """Lock the swoop direction vector on wind-up before lunging."""
        if not self._swoop_locked:
            self._lock_swoop_vector()
        super()._update_wind_up(dt, game_state)
        self.facing = self.swoop_dir

    def _on_start_strike(self, game_state):
        """Launch high-speed swoop lunge (~2.4x speed) along the locked swoop vector."""
        if not self._swoop_locked:
            self._lock_swoop_vector()
        sx, sy = self.swoop_dir
        swoop_speed = self.speed * self.swoop_speed_multiplier
        self.vx = sx * swoop_speed
        self.vy = sy * swoop_speed
        self.facing = self.swoop_dir

    def _update_strike(self, dt, game_state):
        """Surge forward during STRIKE frames and check swoop hitbox collision."""
        if not self.has_hit_this_attack and self.attempt_damage_player(game_state):
            self.has_hit_this_attack = True
            self.vx, self.vy = 0.0, 0.0
        if not self.has_hit_this_attack:
            self.x += self.vx * dt
            self.y += self.vy * dt
            if getattr(game_state, "world", None):
                walls = game_state.world.get_nearby_walls(self.get_rect())
                self.x, self.y = resolve_wall_collision(self.get_rect(), walls)
        super()._update_strike(dt, game_state)
        self.facing = self.swoop_dir
        if self.state != ActorState.STRIKE:
            self._swoop_locked = False

    def _update_chase(self, dt, state):
        """Move toward the active target via A* waypoints with a tightened sine-wave oscillation."""
        self._swoop_locked = False
        if not self.active_target:
            self.state = ActorState.IDLE
            return

        target_cx, target_cy = self.active_target
        nav_x, nav_y = self._get_navigation_waypoint(dt, state, target_cx, target_cy)
        cx, cy = self.get_center()
        dx, dy = nav_x - cx, nav_y - cy
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0.0:
            # Pursuit vector
            vx, vy = (dx / dist) * self.speed, (dy / dist) * self.speed

            # Tightened sine wave perpendicular to movement so bat tracks reliably onto target
            self._angle += dt * 10.0
            perp_x, perp_y = -vy, vx
            dist_scale = min(1.0, dist / (TILE_SIZE * 2.5))
            amp = self.sine_amplitude * dist_scale

            self.vx = vx + perp_x * math.sin(self._angle) * amp
            self.vy = vy + perp_y * math.sin(self._angle) * amp

            self.x += self.vx * dt
            self.y += self.vy * dt

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

    def update(self, dt, state):
        """Rule: Ink-Affinity. Heals if touching a Margin wall."""
        from constants import BINDLING_HEAL_RATE, BINDLING_MAX_HP
        
        if self.hp < BINDLING_MAX_HP:
            # Check nearby walls only when damaged
            my_rect = self.get_rect()
            walls = state.world.get_nearby_walls(my_rect)
            near_wall = False
            for wall in walls:
                if check_aabb_collision(my_rect, wall):
                    near_wall = True
                    break
            
            if near_wall:
                self.hp = min(BINDLING_MAX_HP, self.hp + BINDLING_HEAL_RATE * dt)

        super().update(dt, state)

class Boss(Enemy):
    """Base class for all Elites and Bosses. Implements weapon telegraphs, parrying, and anti-cheese attacks."""
    def __init__(self, x, y, width, height, hp, id=None, name="Boss"):
        from constants import (
            BOSS_WIND_UP_DURATION, BOSS_STRIKE_DURATION, BOSS_RECOVERY_DURATION
        )
        super().__init__(x, y, width, height, hp, id=id, name=name)
        self.is_miniboss = True # Music/Spawn trigger flag
        self.is_parryable = True

        # Elite Telegraphs
        self.wind_up_duration = BOSS_WIND_UP_DURATION
        self.strike_duration = BOSS_STRIKE_DURATION
        self.recovery_duration = BOSS_RECOVERY_DURATION
        self.attack_type = "THRUST"

        # Anti-cheese ranged ink-bolt and cover-flanking state
        self.ranged_cooldown_timer = 0.0
        self._boss_stall_timer = 0.0
        self._flank_dir = random.choice((-1.0, 1.0))
        self.ink_bolts = []

    def get_display_name(self) -> str:
        """Return the player-facing HUD display name for this boss."""
        explicit = getattr(self, "display_name", None)
        if explicit:
            return str(explicit)
        from constants import BOSS_HUD_DISPLAY_NAMES
        cls_name = self.__class__.__name__
        if cls_name in BOSS_HUD_DISPLAY_NAMES:
            return BOSS_HUD_DISPLAY_NAMES[cls_name]
        return str(getattr(self, "name", "Boss") or "Boss")

    def update(self, dt, state):
        """Advance boss ranged cooldown and active ink-bolt projectiles alongside base AI."""
        if self.is_summoning_or_dormant():
            self.vx = 0.0
            self.vy = 0.0
            return
        if self.ranged_cooldown_timer > 0.0:
            self.ranged_cooldown_timer = max(0.0, self.ranged_cooldown_timer - dt)
        if self.ink_bolts:
            self._update_ink_bolts(dt, state)
        super().update(dt, state)

    def _fire_ink_bolt(self, start_x, start_y, target_x, target_y, state):
        """Spawn a Host-authoritative arcing ink-bolt aimed at the target to counter pillar cheese."""
        from constants import (
            BOSS_BOLT_SPEED, BOSS_BOLT_DAMAGE, BOSS_BOLT_RADIUS,
            BOSS_BOLT_MAX_LIFETIME, BOSS_RANGED_COOLDOWN
        )
        net = getattr(state, "network_manager", None)
        if getattr(net, "network_mode", "OFFLINE") == "CLIENT":
            return False

        dx = target_x - start_x
        dy = target_y - start_y
        mag = math.hypot(dx, dy)
        ux, uy = (dx / mag, dy / mag) if mag > 0.001 else (1.0, 0.0)
        self.facing = (ux, uy)
        self.ink_bolts.append({
            "x": float(start_x),
            "y": float(start_y),
            "vx": ux * BOSS_BOLT_SPEED,
            "vy": uy * BOSS_BOLT_SPEED,
            "damage": float(BOSS_BOLT_DAMAGE),
            "life": float(BOSS_BOLT_MAX_LIFETIME),
            "radius": int(BOSS_BOLT_RADIUS),
        })
        self.ranged_cooldown_timer = BOSS_RANGED_COOLDOWN
        self._boss_stall_timer = 0.0
        audio = getattr(state, "audio_manager", None)
        if audio:
            try:
                audio.play_sfx("enemy_telegraph.ogg")
            except Exception:
                pass
        return True

    def _update_ink_bolts(self, dt, state):
        """Advance active ink-bolts and resolve hits against the player."""
        net = getattr(state, "network_manager", None)
        is_client = getattr(net, "network_mode", "OFFLINE") == "CLIENT"
        player = getattr(state, "player", None)
        player_rect = getattr(player, "rect", None) if player is not None else None
        if player is not None and player_rect is None and hasattr(player, "x") and hasattr(player, "y"):
            player_rect = (player.x, player.y, getattr(player, "width", 40), getattr(player, "height", 40))
        can_hit_local = (
            not is_client
            and player is not None
            and player_rect is not None
            and hasattr(player, "take_damage")
            and getattr(state, "active_respite", None) is None
            and getattr(player, "hp", 0.0) > 0.0
        )
        audio = getattr(state, "audio_manager", None)

        remaining = []
        for bolt in self.ink_bolts:
            bolt["x"] += bolt["vx"] * dt
            bolt["y"] += bolt["vy"] * dt
            bolt["life"] -= dt
            if bolt["life"] <= 0.0:
                continue

            r = bolt["radius"]
            bolt_rect = (bolt["x"] - r, bolt["y"] - r, r * 2, r * 2)
            if can_hit_local and check_aabb_collision(bolt_rect, player_rect):
                try:
                    player.take_damage(bolt["damage"], audio_manager=audio, game_state=state)
                except TypeError:
                    player.take_damage(bolt["damage"])
                continue

            remaining.append(bolt)
        self.ink_bolts = remaining

    def _update_chase(self, dt, state):
        """Chase with obstacle flanking and anti-cheese ranged ink-bolts when cover blocks LOS or stalls pursuit."""
        from constants import (
            BOSS_ANTI_CHEESE_RANGE, BOSS_ANTI_CHEESE_STALL_TIME,
            BOSS_FLANK_WEIGHT, BOSS_STALL_MOVE_RATIO
        )
        from engine.pathfinding import has_line_of_sight

        if not self.active_target:
            self.state = ActorState.IDLE
            return

        target_cx, target_cy = self.active_target
        cx, cy = self.get_center()
        dx, dy = target_cx - cx, target_cy - cy
        dist = math.hypot(dx, dy)
        world = getattr(state, "world", None)
        los_clear = has_line_of_sight(world, (cx, cy), (target_cx, target_cy)) if world is not None else True

        prev_x, prev_y = self.x, self.y
        super()._update_chase(dt, state)
        moved = math.hypot(self.x - prev_x, self.y - prev_y)

        stalled = dist > 1.0 and dt > 0.0 and moved < self.speed * dt * BOSS_STALL_MOVE_RATIO
        if stalled:
            self._boss_stall_timer += dt
            ux, uy = dx / dist, dy / dist
            px, py = -uy * self._flank_dir, ux * self._flank_dir
            steer_x = ux * (1.0 - BOSS_FLANK_WEIGHT) + px * BOSS_FLANK_WEIGHT
            steer_y = uy * (1.0 - BOSS_FLANK_WEIGHT) + py * BOSS_FLANK_WEIGHT
            steer_mag = math.hypot(steer_x, steer_y) or 1.0
            flank_prev_x, flank_prev_y = self.x, self.y
            self.vx = (steer_x / steer_mag) * self.speed
            self.vy = (steer_y / steer_mag) * self.speed
            self.x += self.vx * dt
            self.y += self.vy * dt
            if world is not None:
                walls = world.get_nearby_walls(self.get_rect())
                self.x, self.y = resolve_wall_collision(self.get_rect(), walls)
            if math.hypot(self.x - flank_prev_x, self.y - flank_prev_y) < self.speed * dt * BOSS_STALL_MOVE_RATIO * 0.5:
                self._flank_dir = -self._flank_dir
        elif los_clear:
            self._boss_stall_timer = 0.0

        if (
            dist <= BOSS_ANTI_CHEESE_RANGE
            and self.ranged_cooldown_timer <= 0.0
            and (not los_clear or self._boss_stall_timer >= BOSS_ANTI_CHEESE_STALL_TIME)
        ):
            new_cx, new_cy = self.get_center()
            self._fire_ink_bolt(new_cx, new_cy, target_cx, target_cy, state)

    def get_attack_hitbox(self):
        """Calculate the boss's current strike hitbox based on position, size, facing direction, and attack type."""
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        fx, fy = self.facing
        
        # Base offset is proportional to size
        base_offset = max(self.width, self.height) / 2
        
        if self.attack_type == "THRUST":
            # Long, narrow thrust
            length = 100.0
            thickness = 30.0
            offset = base_offset + 10.0
            
            if abs(fx) > abs(fy): # Horizontal
                w, h = length, thickness
                x = cx + offset if fx > 0 else cx - offset - w
                y = cy - h / 2
            else: # Vertical
                w, h = thickness, length
                x = cx - w / 2
                y = cy + offset if fy > 0 else cy - offset - h
        else: # SWING or default
            # Wide, shorter swing
            length = 50.0
            thickness = 120.0
            offset = base_offset + 5.0
            
            if abs(fx) > abs(fy): # Horizontal swing (covers height)
                w, h = length, thickness
                x = cx + offset if fx > 0 else cx - offset - w
                y = cy - h / 2
            else: # Vertical swing (covers width)
                w, h = thickness, length
                x = cx - w / 2
                y = cy + offset if fy > 0 else cy - offset - h
                
        return (x, y, w, h)

    def _update_wind_up(self, dt, state):
        """Randomize attack type at the start of a wind-up."""
        if self.combat_timer == self.wind_up_duration:
            from constants import BOSS_SWING_EXTRA_WIND_UP
            self.attack_type = random.choice(["THRUST", "SWING"])
            print(f"[COMBAT] {self.name} preparing {self.attack_type}!")
            
            # Balancing: Swings take slightly longer to wind up
            if self.attack_type == "SWING":
                self.combat_timer += BOSS_SWING_EXTRA_WIND_UP
        
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
            variants = [
                {
                    "name": "Anomalous Ink-Bleed",
                    "modifiers": {"bleed": 5.0},
                    "description": "Inflicts ink-bleed, dealing 5 damage per second on hit."
                },
                {
                    "name": "Anomalous Life-Thread",
                    "modifiers": {"slow_hp_regen": 1.0},
                    "description": "Slowly mends the Reader, regenerating 1 HP per second."
                },
                {
                    "name": "Anomalous Iron-Nib",
                    "modifiers": {"damage_negation_on_hit": 5.0},
                    "description": "Taking damage temporarily reduces next damage taken by 5."
                },
                {
                    "name": "Anomalous Stout-Draft",
                    "modifiers": {"max_hp_boost": 20.0},
                    "description": "Gives the Reader a small boost of +20 Max HP."
                }
            ]
            chosen = random.choice(variants)
            weapon_data = {
                "name": chosen["name"],
                "damage": 20 + random.randint(0, 10),
                "modifiers": chosen["modifiers"],
                "description": chosen["description"]
            }
        
        state.world.interactables.append(WeaponPickup((self.x, self.y), weapon_data))
        print(f"[LOOT] Miniboss dropped {weapon_data['name']}")

class MinibossM2(Miniboss):
    """Fast pursuit elite."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import MINIBOSS_M2_SPEED
        super().__init__(x, y, hp, id=id)
        self.name = "Bleeding Scribe"
        self.speed = MINIBOSS_M2_SPEED

class MinibossM3(Miniboss):
    """Teleporting elite."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import MINIBOSS_M3_SPEED
        super().__init__(x, y, hp, id=id)
        self.name = "Forgotten Binder"
        self.speed = MINIBOSS_M3_SPEED
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

        if self._tele_timer > 0:
            self._tele_timer -= dt

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

    def _update_state_logic(self, dt, state):
        """Override to always CHASE (flee) when player detected."""
        targets = self.get_active_runner_positions(state)

        cx, cy = self.get_center()
        best_dist_sq = float('inf')
        self.active_target = None
        for tx, ty in targets:
            d_sq = (tx - cx)**2 + (ty - cy)**2
            if d_sq < best_dist_sq:
                best_dist_sq = d_sq
                self.active_target = (tx, ty)

        prev_state = self.state
        if self.active_target and best_dist_sq <= self.detect_radius**2:
            if prev_state != ActorState.CHASE:
                self._clear_nav_path()
            self.state = ActorState.CHASE
        elif self.patrol_route and not self.is_stationary:
            if prev_state != ActorState.PATROLLING:
                nearest_idx = min(
                    range(len(self.patrol_route)),
                    key=lambda idx: (
                        (self.patrol_route[idx].x + self.patrol_route[idx].width / 2 - cx) ** 2
                        + (self.patrol_route[idx].y + self.patrol_route[idx].height / 2 - cy) ** 2
                    ),
                )
                self.patrol_idx = nearest_idx
                if prev_state == ActorState.CHASE:
                    self._returning_to_patrol = True
                    self.wait_timer = 0.0
                self._clear_nav_path()
            self.state = ActorState.PATROLLING
        else:
            self.state = ActorState.IDLE

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
        """Custom update to handle periodic puddle drops when within active simulation."""
        if not self.is_within_active_simulation(state):
            self.vx = 0.0
            self.vy = 0.0
            return

        # Process puddle timer regardless of stagger
        self._puddle_timer += dt
        from constants import SMEAR_PUDDLE_CHANCE, SMEAR_TRAIL_PUDDLE_LIFETIME
        if self._puddle_timer >= 1.0:
            self._puddle_timer = 0.0
            if random.random() < SMEAR_PUDDLE_CHANCE:
                from engine.world import GameObject
                puddle = GameObject((self.x, self.y), (TILE_SIZE, TILE_SIZE))
                puddle.is_solid = False
                puddle.name = "Inkwell Puddle"
                puddle.lifetime = float(SMEAR_TRAIL_PUDDLE_LIFETIME)
                puddle.max_lifetime = float(SMEAR_TRAIL_PUDDLE_LIFETIME)
                state.world.interactables.append(puddle)

        # Then call standard actor update (handles stagger and movement)
        super().update(dt, state)

    def on_death(self, state):
        """Splits the Smear enemy into two smaller blots on death."""
        if self.size_multiplier >= 1.0:
            s1 = SmearEnemy(self.x - 10, self.y, size_multiplier=0.5)
            s2 = SmearEnemy(self.x + 10, self.y, size_multiplier=0.5)
            state.enemies.append(s1)
            state.enemies.append(s2)

class SentryEnemy(Enemy):
    """Anchor/Artillery defense droid that maintains spacing and fires a directional plasma beam."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            SENTRY_MAX_HP, SENTRY_SPEED, SENTRY_DETECT_METERS,
            SENTRY_DAMAGE, SENTRY_DAMAGE_COOLDOWN, SENTRY_BEAM_RANGE, SENTRY_BEAM_WIDTH
        )
        initial_hp = hp if hp is not None else SENTRY_MAX_HP
        super().__init__(x, y, 36, 36, initial_hp, id=id, name="Techno-Sentry")
        self.speed = SENTRY_SPEED
        self.detect_radius = SENTRY_DETECT_METERS * TILE_SIZE
        self.damage = SENTRY_DAMAGE
        self.attack_cooldown = SENTRY_DAMAGE_COOLDOWN
        self.beam_range = SENTRY_BEAM_RANGE
        self.beam_width = SENTRY_BEAM_WIDTH
        self.attack_type = "BEAM"
        self.is_sentry = True
        self.is_parryable = True

        self.wind_up_duration = 0.65
        self.strike_duration = 0.25
        self.recovery_duration = 0.6
        self._orbit_dir = 1.0 if (int(x + y) % 2 == 0) else -1.0

    def get_visual_packet(self):
        packet = super().get_visual_packet()
        packet["color_hint"] = (48, 62, 88)
        return packet

    def get_beam_segment(self):
        """Return ((sx, sy), (ex, ey)) for the true omnidirectional plasma beam along self.facing."""
        cx = self.x + self.width / 2.0
        cy = self.y + self.height / 2.0
        fx, fy = self.facing
        mag = math.hypot(fx, fy)
        if mag < 1e-6:
            ux, uy = 1.0, 0.0
        else:
            ux, uy = fx / mag, fy / mag
        start_off = 14.0
        sx, sy = cx + ux * start_off, cy + uy * start_off
        ex, ey = cx + ux * (start_off + self.beam_range), cy + uy * (start_off + self.beam_range)
        return (sx, sy), (ex, ey)

    def _point_hits_beam(self, px, py, pad_radius):
        """Return True if point (px, py) lies within beam_width/2 + pad_radius of the oriented beam segment."""
        (sx, sy), (ex, ey) = self.get_beam_segment()
        vx, vy = ex - sx, ey - sy
        seg_len_sq = vx * vx + vy * vy
        if seg_len_sq < 1e-6:
            return False
        t = max(0.0, min(1.0, ((px - sx) * vx + (py - sy) * vy) / seg_len_sq))
        closest_x = sx + vx * t
        closest_y = sy + vy * t
        half_w = self.beam_width * 0.5 + pad_radius
        return (px - closest_x) ** 2 + (py - closest_y) ** 2 <= half_w * half_w

    def get_attack_hitbox(self):
        """Return tight bounding AABB around the oriented plasma beam corridor."""
        (sx, sy), (ex, ey) = self.get_beam_segment()
        vx, vy = ex - sx, ey - sy
        seg_len = math.hypot(vx, vy)
        if seg_len < 1e-6:
            return (sx, sy, 1.0, 1.0)
        half_w = self.beam_width * 0.5
        nx, ny = (-vy / seg_len) * half_w, (vx / seg_len) * half_w
        xs = (sx + nx, sx - nx, ex + nx, ex - nx)
        ys = (sy + ny, sy - ny, ey + ny, ey - ny)
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return (min_x, min_y, max(1.0, max_x - min_x), max(1.0, max_y - min_y))

    def attempt_damage_player(self, state):
        """Perform true 360-degree point-to-segment plasma beam collision against active runners."""
        if self.cooldown_timer > 0 or self.stagger_timer > 0:
            return False
        if hasattr(state, 'warp_controller') and state.warp_controller.blocks_enemy_updates():
            return False

        potential_victims = []
        if (
            not getattr(state, "in_sanctuary", False)
            and getattr(state, "active_respite", None) is None
            and state.player.hp > 0
        ):
            potential_victims.append(("local", "LOCAL", state.player))
        remote_data = getattr(state.network_manager, 'remote_players', {})
        for addr, p_data in remote_data.items():
            if not p_data.get("in_sanctuary", False) and p_data.get("hp", 100) > 0:
                potential_victims.append(("remote", addr, (p_data["x"], p_data["y"], 40, 40)))

        body_rect = self.get_rect()
        for v_type, v_id, v_obj in potential_victims:
            v_rect = v_obj if v_type == "remote" else v_obj.rect
            vcx = v_rect[0] + v_rect[2] * 0.5
            vcy = v_rect[1] + v_rect[3] * 0.5
            v_rad = min(v_rect[2], v_rect[3]) * 0.42
            hit = self._point_hits_beam(vcx, vcy, v_rad) or check_aabb_collision(body_rect, v_rect)
            if not hit:
                continue
            if v_type == "local":
                if self.is_parryable and v_obj.is_parry_active():
                    self._handle_parry(state)
                    return True
                try:
                    v_obj.take_damage(
                        self.damage,
                        audio_manager=getattr(state, 'audio_manager', None),
                        game_state=state,
                    )
                except TypeError:
                    v_obj.take_damage(self.damage, audio_manager=getattr(state, 'audio_manager', None))
                return True
            if v_id in state.network_manager.remote_players:
                p_data = state.network_manager.remote_players[v_id]
                p_data["hp"] = max(0.0, p_data.get("hp", 100.0) - self.damage)
                return True
        return False

    def _update_chase(self, dt, state):
        """Maintain artillery spacing, route around obstacles, and fire beam when in range & sight."""
        if not self.active_target:
            self.state = ActorState.IDLE
            return

        from engine.pathfinding import has_line_of_sight

        target_cx, target_cy = self.active_target
        cx, cy = self.get_center()
        dx, dy = target_cx - cx, target_cy - cy
        dist = math.sqrt(dx * dx + dy * dy)
        world = getattr(state, "world", None)
        clear_shot = world is None or not getattr(world, "grid", None) or has_line_of_sight(
            world, (cx, cy), (target_cx, target_cy)
        )

        if dist <= self.beam_range and self.cooldown_timer <= 0 and clear_shot:
            self.state = ActorState.WIND_UP
            self.combat_timer = self.wind_up_duration
            self.vx, self.vy = 0.0, 0.0
            self.has_hit_this_attack = False
            self._clear_nav_path()
            if dist > 0.1:
                self.facing = (dx / dist, dy / dist)
            if hasattr(state, "audio_manager") and state.audio_manager:
                state.audio_manager.play_sfx("enemy_telegraph.ogg")
            return

        if dist > 0.1:
            if not clear_shot or dist > self.beam_range * 0.9:
                nav_x, nav_y = self._get_navigation_waypoint(dt, state, target_cx, target_cy)
                ndx, ndy = nav_x - cx, nav_y - cy
                ndist = math.hypot(ndx, ndy) or 1.0
                ux, uy = ndx / ndist, ndy / ndist
                if not clear_shot:
                    self.vx = ux * self.speed
                    self.vy = uy * self.speed
                else:
                    px, py = -uy * self._orbit_dir, ux * self._orbit_dir
                    self.vx = (ux * 0.8 + px * 0.4) * self.speed
                    self.vy = (uy * 0.8 + py * 0.4) * self.speed
            else:
                ux, uy = dx / dist, dy / dist
                px, py = -uy * self._orbit_dir, ux * self._orbit_dir
                if dist < 110.0:
                    self.vx = (-ux * 0.75 + px * 0.65) * self.speed
                    self.vy = (-uy * 0.75 + py * 0.65) * self.speed
                else:
                    self.vx = px * self.speed * 0.8
                    self.vy = py * self.speed * 0.8

            self.x += self.vx * dt
            self.y += self.vy * dt
            walls = state.world.get_nearby_walls(self.get_rect())
            self.x, self.y = resolve_wall_collision(self.get_rect(), walls)
            self.facing = (dx / dist, dy / dist)


class PunctuationWolfEnemy(Enemy):
    """Pack predator shaped from glyphs that stalks targets and pounces from margins."""

    def __init__(self, x, y, hp=None, id=None):
        from constants import (
            WOLF_MAX_HP, WOLF_SPEED, WOLF_POUNCE_SPEED,
            WOLF_DETECT_METERS, WOLF_POUNCE_RANGE, WOLF_DAMAGE, WOLF_DAMAGE_COOLDOWN,
        )
        initial_hp = hp if hp is not None else WOLF_MAX_HP
        super().__init__(x, y, 36, 36, initial_hp, id=id, name="Punctuation Wolf")
        self.speed = WOLF_SPEED
        self.pounce_speed = WOLF_POUNCE_SPEED
        self.detect_radius = WOLF_DETECT_METERS * TILE_SIZE
        self.pounce_range = WOLF_POUNCE_RANGE
        self.damage = WOLF_DAMAGE
        self.attack_cooldown = WOLF_DAMAGE_COOLDOWN
        self.attack_type = "POUNCE"
        self.is_parryable = True

        self.wind_up_duration = 0.45
        self.strike_duration = 0.25
        self.recovery_duration = 0.55
        self._flank_dir = 1.0 if (int(x + y) % 2 == 0) else -1.0

    def get_visual_packet(self):
        packet = super().get_visual_packet()
        packet["color_hint"] = (255, 215, 166)
        return packet

    def _emit_wolf_sfx(self, state, sfx_name):
        """Play spatialized wolf SFX locally."""
        cx, cy = self.get_center()
        if hasattr(state, "audio_manager") and state.audio_manager:
            vol = 1.0
            if getattr(state, "player", None):
                px, py = state.player.get_center()
                dist = math.hypot(cx - px, cy - py)
                calc_vol = getattr(state.audio_manager, "calculate_spatial_volume", lambda _d: 1.0)
                vol = calc_vol(dist)
            state.audio_manager.play_sfx(sfx_name, volume=vol, pitch_jitter=0.06)

    def _on_start_strike(self, game_state):
        """Launch high-speed pounce in the locked facing direction."""
        fx, fy = self.facing
        mag = math.hypot(fx, fy)
        if mag > 0.001:
            fx, fy = fx / mag, fy / mag
        else:
            fx, fy = 1.0, 0.0
        self.vx = fx * self.pounce_speed
        self.vy = fy * self.pounce_speed
        self._emit_wolf_sfx(game_state, "wolf_attack.ogg")

    def _update_strike(self, dt, game_state):
        """Advance pounce lunge with wall collision and apply contact bite damage."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        if getattr(game_state, "world", None):
            walls = game_state.world.get_nearby_walls(self.get_rect())
            self.x, self.y = resolve_wall_collision(self.get_rect(), walls)
        super()._update_strike(dt, game_state)

    def _update_chase(self, dt, state):
        """Stalk target with subtle pack-flanking offset, then telegraph a pounce."""
        if not self.active_target:
            self.state = ActorState.IDLE
            return

        target_cx, target_cy = self.active_target
        cx, cy = self.get_center()
        dx, dy = target_cx - cx, target_cy - cy
        dist = math.hypot(dx, dy)

        if dist <= self.pounce_range and self.cooldown_timer <= 0:
            self.state = ActorState.WIND_UP
            self.combat_timer = self.wind_up_duration
            self.vx, self.vy = 0.0, 0.0
            self.has_hit_this_attack = False
            if dist > 0.1:
                self.facing = (dx / dist, dy / dist)
            self._emit_wolf_sfx(state, "wolf_telegraph.ogg")
            return

        if dist > 0.1:
            nav_x, nav_y = self._get_navigation_waypoint(dt, state, target_cx, target_cy)
            ndx, ndy = nav_x - cx, nav_y - cy
            ndist = math.hypot(ndx, ndy) or 1.0
            ux, uy = ndx / ndist, ndy / ndist
            # Pack AI: flank laterally if another wolf is nearby and target is directly ahead
            has_packmate = any(
                other is not self and getattr(other, "name", "") == "Punctuation Wolf"
                and math.hypot(other.x - self.x, other.y - self.y) < 140.0
                for other in getattr(state, "enemies", [])
            )
            direct_approach = (nav_x == target_cx and nav_y == target_cy)
            flank = 0.45 * self._flank_dir if has_packmate and direct_approach and dist > 75.0 else 0.0
            px, py = -uy * flank, ux * flank
            move_x, move_y = ux + px, uy + py
            move_mag = math.hypot(move_x, move_y) or 1.0
            self.vx = (move_x / move_mag) * self.speed
            self.vy = (move_y / move_mag) * self.speed

            self.x += self.vx * dt
            self.y += self.vy * dt
            if getattr(state, "world", None):
                walls = state.world.get_nearby_walls(self.get_rect())
                self.x, self.y = resolve_wall_collision(self.get_rect(), walls)
            self.facing = (dx / dist, dy / dist)

class NightBoss(Miniboss):
    """Dual-encounter boss."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import NIGHT_BOSS_MAX_HP, MINIBOSS_SPEED
        initial_hp = hp if hp is not None else NIGHT_BOSS_MAX_HP
        super().__init__(x, y, initial_hp, id=id)
        self.name = "Night Boss"
        self.speed = MINIBOSS_SPEED * 0.9
        self.loot_tier = 1


class SlugBoss(NightBoss):
    """Swamp biome Night Boss: crowned yellow/pink sword-pierced sovereign with charge & slime-pool attacks."""

    def __init__(self, x, y, hp=None, id=None):
        from constants import SLUG_BOSS_SIZE, SLUG_BOSS_SPEED
        super().__init__(x, y, hp=hp, id=id)
        self.width = SLUG_BOSS_SIZE
        self.height = SLUG_BOSS_SIZE
        self.name = "Night Boss"
        self.display_name = "The Crowned Slug"
        self.is_slug_boss = True
        self.speed = SLUG_BOSS_SPEED
        self.attack_type = "LUNGE"
        self.attack_mode = "CHARGE"  # Alternates "CHARGE" <-> "SLIME"
        self.phase = 1
        self.minions_summoned = False
        self.wind_up_duration = 0.65
        self.strike_duration = 0.45
        self.recovery_duration = 0.85
        self._charge_dir = (1.0, 0.0)
        self._charge_locked = False
        self._slime_released = False

    def get_visual_packet(self):
        packet = super().get_visual_packet()
        packet["color_hint"] = (212, 174, 52)
        packet["attack_mode"] = self.attack_mode
        packet["phase"] = self.phase
        return packet

    def _summon_phase2_minions(self, state):
        """Play slug_boss_slime.ogg and summon 10 walkable, Act-scaled SlugEnemy minions around SlugBoss."""
        from constants import (
            ACT2_DAMAGE_MULTIPLIER,
            ACT2_HP_MULTIPLIER,
            SLUG_BOSS_MINION_COUNT,
            SLUG_BOSS_SLIME_SFX,
            get_act_saturation,
        )

        audio = getattr(state, "audio_manager", None)
        if audio is not None:
            try:
                audio.play_sfx(SLUG_BOSS_SLIME_SFX)
            except Exception:
                pass

        enemies = getattr(state, "enemies", None)
        if enemies is None:
            return
        world = getattr(state, "world", None)

        current_act = int(getattr(state, "current_act", 0) or 0)
        empowered_act = bool(getattr(state, "empowered_act", False))
        hp_mult = 1.0
        dmg_mult = 1.0
        spd_mult = 1.0
        cd_mult = 1.0
        emp_flag = None
        if current_act >= 1 or empowered_act:
            sat = get_act_saturation(max(1, current_act if current_act >= 1 else 2))
            spd_mult = float(sat.get("speed_multiplier", 1.0))
            cd_mult = float(sat.get("cooldown_multiplier", 1.0))
            if empowered_act and current_act <= 2:
                hp_mult = float(max(ACT2_HP_MULTIPLIER, float(sat["hp_multiplier"])))
                dmg_mult = float(max(ACT2_DAMAGE_MULTIPLIER, float(sat["damage_multiplier"])))
                emp_flag = True
            else:
                hp_mult = float(sat["hp_multiplier"])
                dmg_mult = float(sat["damage_multiplier"])
                emp_flag = bool(sat["empowered"])

        next_net_id = max((getattr(e, "network_id", -1) for e in enemies), default=0) + 1
        cx, cy = self.get_center()
        count = int(SLUG_BOSS_MINION_COUNT)
        active_runners = Actor.get_active_runner_positions(state)

        for idx in range(count):
            angle = (2.0 * math.pi * idx) / max(1, count)
            ring_r = 96.0 if (idx % 2 == 0) else 124.0
            minion = SlugEnemy(cx + math.cos(angle) * ring_r - 16.0, cy + math.sin(angle) * ring_r - 16.0)
            if world is not None and hasattr(world, "find_nearest_walkable_spawn"):
                wx, wy = world.find_nearest_walkable_spawn(minion.x, minion.y, minion.width, minion.height)
                minion.x, minion.y = float(wx), float(wy)
                minion.origin_x, minion.origin_y = float(wx), float(wy)
            if (
                hp_mult != 1.0
                or dmg_mult != 1.0
                or emp_flag is not None
                or spd_mult != 1.0
                or cd_mult != 1.0
            ):
                minion.apply_act_scaling(
                    hp_mult,
                    dmg_mult,
                    empowered=emp_flag,
                    speed_multiplier=spd_mult,
                    cooldown_multiplier=cd_mult,
                )
            minion.persistent_pursuit = True
            if active_runners:
                mcx, mcy = minion.get_center()
                minion.active_target = min(
                    active_runners,
                    key=lambda pos, mx=mcx, my=mcy: (pos[0] - mx) ** 2 + (pos[1] - my) ** 2,
                )
                minion.state = ActorState.CHASE
            minion.network_id = next_net_id
            next_net_id += 1
            enemies.append(minion)

        if world is not None:
            world._enemies = list(enemies)

    def update(self, dt, state):
        """Advance SlugBoss AI and trigger Phase 2 + 10-Slug minion summon at <= 50% HP."""
        super().update(dt, state)
        if self.is_summoning_or_dormant():
            return
        from constants import SLUG_BOSS_PHASE2_HP_RATIO
        if (
            not self.minions_summoned
            and self.hp > 0
            and self.max_hp > 0
            and self.hp <= self.max_hp * SLUG_BOSS_PHASE2_HP_RATIO
        ):
            self.phase = 2
            self.minions_summoned = True
            net_mode = getattr(getattr(state, "network_manager", None), "network_mode", "OFFLINE")
            if net_mode != "CLIENT":
                self._summon_phase2_minions(state)

    def _lock_charge_vector(self):
        """Lock a normalized charge vector toward active_target or current facing."""
        if self.active_target:
            tx, ty = self.active_target
            cx, cy = self.get_center()
            dx, dy = tx - cx, ty - cy
            mag = math.hypot(dx, dy)
            if mag > 0.001:
                self._charge_dir = (dx / mag, dy / mag)
                self.facing = self._charge_dir
                self._charge_locked = True
                return
        fx, fy = self.facing
        mag = math.hypot(fx, fy)
        self._charge_dir = (fx / mag, fy / mag) if mag > 0.001 else (1.0, 0.0)
        self.facing = self._charge_dir
        self._charge_locked = True

    def get_attack_hitbox(self):
        """Return a 92x92 forward charge hitbox during CHARGE STRIKE (112x112 body rect otherwise)."""
        if self.state == ActorState.STRIKE and self.attack_mode == "CHARGE":
            from constants import SLUG_BOSS_CHARGE_HITBOX_OFFSET, SLUG_BOSS_CHARGE_HITBOX_SIZE
            cx, cy = self.get_center()
            dx, dy = self._charge_dir if self._charge_locked else self.facing
            mag = math.hypot(dx, dy)
            ux, uy = (dx / mag, dy / mag) if mag > 0.001 else (1.0, 0.0)
            size = float(SLUG_BOSS_CHARGE_HITBOX_SIZE)
            off = float(SLUG_BOSS_CHARGE_HITBOX_OFFSET)
            return (cx + ux * off - size / 2.0, cy + uy * off - size / 2.0, size, size)
        return self.get_rect()

    def _release_slime_pools(self, game_state):
        """Play slug_boss_slime.ogg once and secrete damaging slime pools onto the ground."""
        if self._slime_released:
            return
        self._slime_released = True
        from constants import (
            SLUG_BOSS_SLIME_POOL_COUNT,
            SLUG_BOSS_SLIME_POOL_DAMAGE,
            SLUG_BOSS_SLIME_POOL_DURATION,
            SLUG_BOSS_SLIME_POOL_RADIUS,
            SLUG_BOSS_SLIME_SFX,
        )
        audio = getattr(game_state, "audio_manager", None)
        if audio is not None:
            try:
                audio.play_sfx(SLUG_BOSS_SLIME_SFX)
            except Exception:
                pass
        spawn_fn = getattr(game_state, "spawn_slime_pool", None)
        if not callable(spawn_fn):
            return
        cx, cy = self.get_center()
        fx, fy = self.facing
        mag = math.hypot(fx, fy)
        ux, uy = (fx / mag, fy / mag) if mag > 0.001 else (1.0, 0.0)
        px, py = -uy, ux
        # Forward center pool + two flanking pools around the bloated slug
        offsets = (
            (ux * 68.0, uy * 68.0),
            (ux * 34.0 + px * 58.0, uy * 34.0 + py * 58.0),
            (ux * 34.0 - px * 58.0, uy * 34.0 - py * 58.0),
        )
        for ox_p, oy_p in offsets[:SLUG_BOSS_SLIME_POOL_COUNT]:
            spawn_fn(
                cx + ox_p,
                cy + oy_p,
                radius=SLUG_BOSS_SLIME_POOL_RADIUS,
                duration=SLUG_BOSS_SLIME_POOL_DURATION,
                damage=SLUG_BOSS_SLIME_POOL_DAMAGE,
            )

    def _update_chase(self, dt, state):
        """Pursue target and initiate CHARGE or stationary SLIME attack within boss spacing."""
        if self.active_target and self.cooldown_timer <= 0:
            cx, cy = self.get_center()
            tx, ty = self.active_target
            dist = math.hypot(tx - cx, ty - cy)
            if dist <= TILE_SIZE * 4.5:
                self.state = ActorState.WIND_UP
                self.combat_timer = self.wind_up_duration
                self.vx, self.vy = 0.0, 0.0
                self.has_hit_this_attack = False
                self._charge_locked = False
                self._slime_released = False
                if dist > 0.1:
                    self.facing = ((tx - cx) / dist, (ty - cy) / dist)
                self._clear_nav_path()
                audio = getattr(state, "audio_manager", None)
                if audio is not None:
                    try:
                        audio.play_sfx("enemy_telegraph.ogg")
                    except Exception:
                        pass
                return
        super()._update_chase(dt, state)

    def _update_wind_up(self, dt, game_state):
        """Halt during wind-up, locking charge direction if in CHARGE mode."""
        self.vx, self.vy = 0.0, 0.0
        if self.attack_mode == "CHARGE" and not self._charge_locked:
            self._lock_charge_vector()
        super()._update_wind_up(dt, game_state)

    def _on_start_strike(self, game_state):
        """Launch a fast charging lunge or halt and secrete damaging slime pools."""
        if self.attack_mode == "CHARGE":
            from constants import SLUG_BOSS_CHARGE_SPEED_MULTIPLIER
            if not self._charge_locked:
                self._lock_charge_vector()
            ux, uy = self._charge_dir
            charge_spd = self.speed * SLUG_BOSS_CHARGE_SPEED_MULTIPLIER
            self.vx = ux * charge_spd
            self.vy = uy * charge_spd
        else:
            self.vx, self.vy = 0.0, 0.0
            self._release_slime_pools(game_state)

    def _update_strike(self, dt, game_state):
        """Execute charging lunge movement or stationary slime secretion, then alternate mode."""
        if self.attack_mode == "CHARGE":
            self.x += self.vx * dt
            self.y += self.vy * dt
            if getattr(game_state, "world", None):
                walls = game_state.world.get_nearby_walls(self.get_rect())
                self.x, self.y = resolve_wall_collision(self.get_rect(), walls)
            if not self.has_hit_this_attack and self.attempt_damage_player(game_state):
                self.has_hit_this_attack = True
        else:
            self.vx, self.vy = 0.0, 0.0
            self._release_slime_pools(game_state)

        super()._update_strike(dt, game_state)
        if self.state != ActorState.STRIKE:
            self.vx, self.vy = 0.0, 0.0
            self._charge_locked = False
            self._slime_released = False
            self.attack_mode = "SLIME" if self.attack_mode == "CHARGE" else "CHARGE"

    def on_death(self, state):
        """Leave a persistent non-interactive SlugBossCrown and scatter two distinct weapon pickups."""
        from constants import SLUG_BOSS_CROWN_HEIGHT, SLUG_BOSS_CROWN_WIDTH
        from engine.world import SlugBossCrown, WeaponPickup

        world = getattr(state, "world", None)
        if world is None:
            return

        cx, cy = self.get_center()
        crown_x = cx - SLUG_BOSS_CROWN_WIDTH / 2.0
        crown_y = cy - SLUG_BOSS_CROWN_HEIGHT / 2.0
        if hasattr(world, "find_nearest_walkable_spawn"):
            crown_x, crown_y = world.find_nearest_walkable_spawn(
                crown_x, crown_y, SLUG_BOSS_CROWN_WIDTH, SLUG_BOSS_CROWN_HEIGHT
            )
        world.interactables.append(SlugBossCrown((crown_x, crown_y)))

        weapon_pool = [
            {
                "name": "Anomalous Ink-Bleed",
                "damage": 24,
                "modifiers": {"bleed": 5.0},
                "description": "Inflicts ink-bleed, dealing 5 damage per second on hit.",
            },
            {
                "name": "Anomalous Life-Thread",
                "damage": 22,
                "modifiers": {"slow_hp_regen": 1.0},
                "description": "Slowly mends the Reader, regenerating 1 HP per second.",
            },
            {
                "name": "Anomalous Iron-Nib",
                "damage": 23,
                "modifiers": {"damage_negation_on_hit": 5.0},
                "description": "Taking damage temporarily reduces next damage taken by 5.",
            },
            {
                "name": "Anomalous Stout-Draft",
                "damage": 25,
                "modifiers": {"max_hp_boost": 20.0},
                "description": "Gives the Reader a small boost of +20 Max HP.",
            },
        ]
        chosen_pair = random.sample(weapon_pool, 2)
        scatter_offsets = ((-48.0, 12.0), (48.0, -12.0))
        for weapon_template, (ox_w, oy_w) in zip(chosen_pair, scatter_offsets):
            wx, wy = cx + ox_w - TILE_SIZE / 2.0, cy + oy_w - TILE_SIZE / 2.0
            if hasattr(world, "find_nearest_walkable_spawn"):
                wx, wy = world.find_nearest_walkable_spawn(wx, wy, TILE_SIZE, TILE_SIZE)
            weapon_copy = {
                "name": weapon_template["name"],
                "damage": weapon_template["damage"],
                "modifiers": dict(weapon_template["modifiers"]),
                "description": weapon_template["description"],
            }
            world.interactables.append(WeaponPickup((wx, wy), weapon_copy))
        print("[LOOT] SlugBoss dropped tarnished crown and 2 scattered weapons.")


class MeadowCensorBoss(NightBoss):
    """Pastoral Valley Night Boss (The Meadow Censor): hooked scythe pull-cleave, boiling tar geysers & wolves."""

    def __init__(self, x, y, hp=None, id=None):
        from constants import MEADOW_CENSOR_HP, MEADOW_CENSOR_SIZE, MEADOW_CENSOR_SPEED
        initial_hp = hp if hp is not None else MEADOW_CENSOR_HP
        super().__init__(x, y, hp=initial_hp, id=id)
        self.width = MEADOW_CENSOR_SIZE
        self.height = MEADOW_CENSOR_SIZE
        self.name = "Night Boss"
        self.display_name = "The Meadow Censor"
        self.is_meadow_censor = True
        self.speed = MEADOW_CENSOR_SPEED
        self.loot_tier = 2
        self.attack_type = "SWING"
        self.attack_mode = "SCYTHE"  # Alternates "SCYTHE" <-> "TAR_GEYSER"
        self.phase = 1
        self.minions_summoned = False
        self.wind_up_duration = 0.62
        self.strike_duration = 0.42
        self.recovery_duration = 0.80
        self._tar_released = False
        self._pull_applied = False

    def get_visual_packet(self):
        packet = super().get_visual_packet()
        packet["color_hint"] = (176, 86, 212)
        packet["attack_mode"] = self.attack_mode
        packet["phase"] = self.phase
        return packet

    def get_attack_hitbox(self):
        """Return a wide hooked crescent scythe cleave hitbox during SCYTHE STRIKE."""
        if self.state == ActorState.STRIKE and self.attack_mode == "SCYTHE":
            cx, cy = self.get_center()
            fx, fy = self.facing
            mag = math.hypot(fx, fy)
            ux, uy = (fx / mag, fy / mag) if mag > 0.001 else (1.0, 0.0)
            cleave_size = 144.0
            offset = 32.0
            return (
                cx + ux * offset - cleave_size / 2.0,
                cy + uy * offset - cleave_size / 2.0,
                cleave_size,
                cleave_size,
            )
        return self.get_rect()

    def _apply_scythe_pull(self, game_state):
        """Pull local player inward toward MeadowCensorBoss while respecting wall collisions."""
        if self._pull_applied:
            return
        player = getattr(game_state, "player", None)
        if player is None or getattr(game_state, "active_respite", None) is not None:
            return
        from constants import MEADOW_CENSOR_PULL_DISTANCE

        self._pull_applied = True
        bcx, bcy = self.get_center()
        pcx, pcy = player.get_center()
        dx = bcx - pcx
        dy = bcy - pcy
        dist = math.hypot(dx, dy)
        min_gap = (self.width + player.width) * 0.52
        pull_dist = min(float(MEADOW_CENSOR_PULL_DISTANCE), max(0.0, dist - min_gap))
        if dist <= 1e-3 or pull_dist <= 0.5:
            return
        ux, uy = dx / dist, dy / dist
        world = getattr(game_state, "world", None)
        steps = max(1, int(math.ceil(pull_dist / 12.0)))
        step_px = pull_dist / float(steps)
        for _ in range(steps):
            player.x += ux * step_px
            player.y += uy * step_px
            if world is not None and hasattr(world, "get_nearby_walls"):
                walls = world.get_nearby_walls(player.rect)
                player.x, player.y = resolve_wall_collision(player.rect, walls)

    def _release_tar_geysers(self, game_state):
        """Play shepherd's culling whistle and erupt boiling plum tar-ink pools onto the ground."""
        if self._tar_released:
            return
        self._tar_released = True
        from constants import (
            MEADOW_CENSOR_TAR_POOL_COUNT,
            MEADOW_CENSOR_WHISTLE_SFX,
            SLUG_BOSS_SLIME_POOL_DAMAGE,
            SLUG_BOSS_SLIME_POOL_DURATION,
            SLUG_BOSS_SLIME_POOL_RADIUS,
        )
        audio = getattr(game_state, "audio_manager", None)
        if audio is not None:
            try:
                audio.play_sfx(MEADOW_CENSOR_WHISTLE_SFX)
            except Exception:
                pass
        spawn_fn = getattr(game_state, "spawn_slime_pool", None)
        if not callable(spawn_fn):
            return
        cx, cy = self.get_center()
        fx, fy = self.facing
        mag = math.hypot(fx, fy)
        ux, uy = (fx / mag, fy / mag) if mag > 0.001 else (1.0, 0.0)
        px, py = -uy, ux
        offsets = (
            (ux * 78.0, uy * 78.0),
            (ux * 42.0 + px * 68.0, uy * 42.0 + py * 68.0),
            (ux * 42.0 - px * 68.0, uy * 42.0 - py * 68.0),
        )
        for ox_p, oy_p in offsets[:MEADOW_CENSOR_TAR_POOL_COUNT]:
            try:
                spawn_fn(
                    cx + ox_p,
                    cy + oy_p,
                    radius=SLUG_BOSS_SLIME_POOL_RADIUS,
                    duration=SLUG_BOSS_SLIME_POOL_DURATION,
                    damage=SLUG_BOSS_SLIME_POOL_DAMAGE,
                    style="tar",
                )
            except TypeError:
                pool = spawn_fn(
                    cx + ox_p,
                    cy + oy_p,
                    radius=SLUG_BOSS_SLIME_POOL_RADIUS,
                    duration=SLUG_BOSS_SLIME_POOL_DURATION,
                    damage=SLUG_BOSS_SLIME_POOL_DAMAGE,
                )
                if isinstance(pool, dict):
                    pool["style"] = "tar"

    def _summon_phase2_wolves(self, state):
        """Summon 4 walkable, Act-scaled PunctuationWolfEnemy minions around MeadowCensorBoss."""
        from constants import (
            ACT2_DAMAGE_MULTIPLIER,
            ACT2_HP_MULTIPLIER,
            MEADOW_CENSOR_MINION_COUNT,
            get_act_saturation,
        )

        enemies = getattr(state, "enemies", None)
        if enemies is None:
            return
        world = getattr(state, "world", None)

        current_act = int(getattr(state, "current_act", 0) or 0)
        empowered_act = bool(getattr(state, "empowered_act", False))
        hp_mult = 1.0
        dmg_mult = 1.0
        spd_mult = 1.0
        cd_mult = 1.0
        emp_flag = None
        if current_act >= 1 or empowered_act:
            sat = get_act_saturation(max(1, current_act if current_act >= 1 else 2))
            spd_mult = float(sat.get("speed_multiplier", 1.0))
            cd_mult = float(sat.get("cooldown_multiplier", 1.0))
            if empowered_act and current_act <= 2:
                hp_mult = float(max(ACT2_HP_MULTIPLIER, float(sat["hp_multiplier"])))
                dmg_mult = float(max(ACT2_DAMAGE_MULTIPLIER, float(sat["damage_multiplier"])))
                emp_flag = True
            else:
                hp_mult = float(sat["hp_multiplier"])
                dmg_mult = float(sat["damage_multiplier"])
                emp_flag = bool(sat["empowered"])

        next_net_id = max((getattr(e, "network_id", -1) for e in enemies), default=0) + 1
        cx, cy = self.get_center()
        count = int(MEADOW_CENSOR_MINION_COUNT)

        for idx in range(count):
            angle = (2.0 * math.pi * idx) / max(1, count) + (math.pi / 4.0)
            ring_r = 108.0
            wolf = PunctuationWolfEnemy(cx + math.cos(angle) * ring_r - 18.0, cy + math.sin(angle) * ring_r - 18.0)
            if world is not None and hasattr(world, "find_nearest_walkable_spawn"):
                wx, wy = world.find_nearest_walkable_spawn(wolf.x, wolf.y, wolf.width, wolf.height)
                wolf.x, wolf.y = float(wx), float(wy)
                wolf.origin_x, wolf.origin_y = float(wx), float(wy)
            if (
                hp_mult != 1.0
                or dmg_mult != 1.0
                or emp_flag is not None
                or spd_mult != 1.0
                or cd_mult != 1.0
            ):
                wolf.apply_act_scaling(
                    hp_mult,
                    dmg_mult,
                    empowered=emp_flag,
                    speed_multiplier=spd_mult,
                    cooldown_multiplier=cd_mult,
                )
            wolf.network_id = next_net_id
            next_net_id += 1
            enemies.append(wolf)

        if world is not None:
            world._enemies = list(enemies)

    def update(self, dt, state):
        """Advance MeadowCensorBoss AI and trigger Phase 2 culling whistle + 4-wolf pack summon at <= 50% HP."""
        super().update(dt, state)
        if self.is_summoning_or_dormant():
            return
        from constants import MEADOW_CENSOR_PHASE2_HP_RATIO, MEADOW_CENSOR_WHISTLE_SFX
        if (
            not self.minions_summoned
            and self.hp > 0
            and self.max_hp > 0
            and self.hp <= self.max_hp * MEADOW_CENSOR_PHASE2_HP_RATIO
        ):
            self.phase = 2
            self.minions_summoned = True
            audio = getattr(state, "audio_manager", None)
            if audio is not None:
                try:
                    audio.play_sfx(MEADOW_CENSOR_WHISTLE_SFX)
                except Exception:
                    pass
            net_mode = getattr(getattr(state, "network_manager", None), "network_mode", "OFFLINE")
            if net_mode != "CLIENT":
                self._summon_phase2_wolves(state)

    def _update_chase(self, dt, state):
        """Pursue target and initiate hooked SCYTHE cleave or TAR_GEYSER eruption within spacing."""
        if self.active_target and self.cooldown_timer <= 0:
            cx, cy = self.get_center()
            tx, ty = self.active_target
            dist = math.hypot(tx - cx, ty - cy)
            if dist <= TILE_SIZE * 4.5:
                self.state = ActorState.WIND_UP
                self.combat_timer = self.wind_up_duration
                self.vx, self.vy = 0.0, 0.0
                self.has_hit_this_attack = False
                self._tar_released = False
                self._pull_applied = False
                if dist > 0.1:
                    self.facing = ((tx - cx) / dist, (ty - cy) / dist)
                self._clear_nav_path()
                audio = getattr(state, "audio_manager", None)
                if audio is not None:
                    try:
                        audio.play_sfx("enemy_telegraph.ogg")
                    except Exception:
                        pass
                return
        super()._update_chase(dt, state)

    def _update_wind_up(self, dt, game_state):
        """Halt cleanly during wind-up."""
        self.vx, self.vy = 0.0, 0.0
        super()._update_wind_up(dt, game_state)

    def _on_start_strike(self, game_state):
        """Launch hooked scythe sweep or halt and erupt boiling plum tar geysers."""
        self.vx, self.vy = 0.0, 0.0
        if self.attack_mode == "TAR_GEYSER":
            self._release_tar_geysers(game_state)

    def _update_strike(self, dt, game_state):
        """Execute hooked scythe pull-cleave or stationary tar geyser eruption, then alternate mode."""
        self.vx, self.vy = 0.0, 0.0
        if self.attack_mode == "SCYTHE":
            if not self.has_hit_this_attack and self.attempt_damage_player(game_state):
                self.has_hit_this_attack = True
                if self.stagger_timer <= 0.0:
                    self._apply_scythe_pull(game_state)
        else:
            self._release_tar_geysers(game_state)

        super()._update_strike(dt, game_state)
        if self.state != ActorState.STRIKE:
            self.vx, self.vy = 0.0, 0.0
            self._tar_released = False
            self._pull_applied = False
            self.attack_mode = "TAR_GEYSER" if self.attack_mode == "SCYTHE" else "SCYTHE"

    def on_death(self, state):
        """Plant persistent non-interactive MeadowCensorScythe, scatter 2 weapons, and drop ChoiceOfFates."""
        from constants import MEADOW_CENSOR_SCYTHE_HEIGHT, MEADOW_CENSOR_SCYTHE_WIDTH
        from engine.loot import ChoiceOfFates
        from engine.world import MeadowCensorScythe, WeaponPickup

        world = getattr(state, "world", None)
        if world is None:
            return

        cx, cy = self.get_center()
        scythe_x = cx - MEADOW_CENSOR_SCYTHE_WIDTH / 2.0
        scythe_y = cy - MEADOW_CENSOR_SCYTHE_HEIGHT / 2.0
        if hasattr(world, "find_nearest_walkable_spawn"):
            scythe_x, scythe_y = world.find_nearest_walkable_spawn(
                scythe_x, scythe_y, MEADOW_CENSOR_SCYTHE_WIDTH, MEADOW_CENSOR_SCYTHE_HEIGHT
            )
        world.interactables.append(MeadowCensorScythe((scythe_x, scythe_y)))

        weapon_pool = [
            {
                "name": "Anomalous Redaction Sickle",
                "damage": 25,
                "modifiers": {"bleed": 5.5},
                "description": "Hooked ink-reaping edge inflicting 5.5 bleed damage per second.",
            },
            {
                "name": "Anomalous Shepherd's Crook",
                "damage": 22,
                "modifiers": {"slow_hp_regen": 1.2},
                "description": "Steadies the Reader's pulse, regenerating 1.2 HP per second.",
            },
            {
                "name": "Anomalous Ledger Ward",
                "damage": 23,
                "modifiers": {"damage_negation_on_hit": 5.0},
                "description": "Taking damage temporarily reduces next damage taken by 5.",
            },
            {
                "name": "Anomalous Stout-Draft",
                "damage": 25,
                "modifiers": {"max_hp_boost": 20.0},
                "description": "Gives the Reader a small boost of +20 Max HP.",
            },
        ]
        chosen_pair = random.sample(weapon_pool, 2)
        scatter_offsets = ((-48.0, 12.0), (48.0, -12.0))
        for weapon_template, (ox_w, oy_w) in zip(chosen_pair, scatter_offsets):
            wx, wy = cx + ox_w - TILE_SIZE / 2.0, cy + oy_w - TILE_SIZE / 2.0
            if hasattr(world, "find_nearest_walkable_spawn"):
                wx, wy = world.find_nearest_walkable_spawn(wx, wy, TILE_SIZE, TILE_SIZE)
            weapon_copy = {
                "name": weapon_template["name"],
                "damage": weapon_template["damage"],
                "modifiers": dict(weapon_template["modifiers"]),
                "description": weapon_template["description"],
            }
            world.interactables.append(WeaponPickup((wx, wy), weapon_copy))

        loot_list = getattr(state, "loot", None)
        if isinstance(loot_list, list) and not any(isinstance(i, ChoiceOfFates) for i in loot_list):
            loot_list.append(ChoiceOfFates(cx, cy))
        print("[LOOT] MeadowCensorBoss planted hooked scythe, 2 scattered weapons, and Choice of Fates.")


class RimecrestArbiterBoss(NightBoss):
    """Frozen Peaks Night Boss: mirror-ice sentinel with frost halberd sweep & freezing Frost Breath cone."""

    def __init__(self, x, y, hp=None, id=None):
        from constants import RIMECREST_ARBITER_HP, RIMECREST_ARBITER_SIZE, RIMECREST_ARBITER_SPEED
        initial_hp = hp if hp is not None else RIMECREST_ARBITER_HP
        super().__init__(x, y, hp=initial_hp, id=id)
        self.width = RIMECREST_ARBITER_SIZE
        self.height = RIMECREST_ARBITER_SIZE
        self.name = "Night Boss"
        self.display_name = "The Rimecrest Arbiter"
        self.is_rimecrest_arbiter = True
        self.speed = RIMECREST_ARBITER_SPEED
        self.damage = 28.0
        self.wind_up_duration = 0.72
        self.strike_duration = 0.85
        self.recovery_duration = 0.72
        self.attack_mode = "HALBERD"  # Alternates between "HALBERD" and "FROST_BREATH"
        self.phase = 1
        self.minions_summoned = False
        self._breath_sfx_played = False
        self._breath_hit_applied = False

    def get_visual_packet(self):
        """Include RimecrestArbiterBoss attack mode & phase so renderer draws halberd arcs, frost cone, and aura."""
        packet = super().get_visual_packet()
        packet["attack_mode"] = self.attack_mode
        packet["phase"] = self.phase
        return packet

    def get_attack_hitbox(self):
        """Return wide frost-halberd cleave hitbox during HALBERD strike; zero-size rect during FROST_BREATH."""
        if self.attack_mode == "FROST_BREATH":
            return (self.x, self.y, 0.0, 0.0)
        cx, cy = self.get_center()
        fx, fy = self.facing
        reach = self.width * 0.62
        box_w = self.width * 1.12
        box_h = self.height * 1.12
        return (cx + fx * reach - box_w / 2.0, cy + fy * reach - box_h / 2.0, box_w, box_h)

    def _is_point_in_frost_cone(self, px, py):
        """Return True if world point (px, py) lies within the active Frost Breath directional cone."""
        from constants import RIMECREST_ARBITER_BREATH_HALF_ANGLE, RIMECREST_ARBITER_BREATH_RANGE
        cx, cy = self.get_center()
        dx, dy = px - cx, py - cy
        dist = math.hypot(dx, dy)
        if dist > float(RIMECREST_ARBITER_BREATH_RANGE) + 18.0:
            return False
        if dist < 1e-3:
            return True
        fx, fy = self.facing
        f_mag = math.hypot(fx, fy)
        if f_mag < 1e-3:
            fx, fy = 1.0, 0.0
        else:
            fx, fy = fx / f_mag, fy / f_mag
        dot = max(-1.0, min(1.0, (dx / dist) * fx + (dy / dist) * fy))
        return math.acos(dot) <= float(RIMECREST_ARBITER_BREATH_HALF_ANGLE)

    def _apply_frost_breath_tick(self, dt, game_state):
        """Project Frost Breath cone: apply one 0.5 chill hit per breath attack and deal light chill damage."""
        from constants import RIMECREST_ARBITER_BREATH_DPS, RIMECREST_CHILL_HIT_AMOUNT
        player = getattr(game_state, "player", None)
        if player is None or getattr(player, "hp", 0) <= 0:
            return
        if getattr(game_state, "in_sanctuary", False) or getattr(game_state, "active_respite", None):
            return
        px, py = player.get_center()
        if not self._is_point_in_frost_cone(px, py):
            return
        if not self._breath_hit_applied and hasattr(player, "apply_frost_exposure"):
            self._breath_hit_applied = True
            player.apply_frost_exposure(float(RIMECREST_CHILL_HIT_AMOUNT))
        chill_dmg = float(RIMECREST_ARBITER_BREATH_DPS) * dt
        if chill_dmg > 0.0:
            player.take_damage(
                chill_dmg,
                bypass_stagger=True,
                audio_manager=getattr(game_state, "audio_manager", None),
                game_state=game_state,
            )

    def _summon_phase2_vanguard(self, state):
        """Summon 3 walkable, Act-scaled SmearEnemy / FlutterEnemy glacial vanguard minions."""
        from constants import (
            ACT2_DAMAGE_MULTIPLIER,
            ACT2_HP_MULTIPLIER,
            RIMECREST_ARBITER_MINION_COUNT,
            get_act_saturation,
        )

        enemies = getattr(state, "enemies", None)
        if enemies is None:
            return
        world = getattr(state, "world", None)

        current_act = int(getattr(state, "current_act", 0) or 0)
        empowered_act = bool(getattr(state, "empowered_act", False))
        hp_mult = 1.0
        dmg_mult = 1.0
        spd_mult = 1.0
        cd_mult = 1.0
        emp_flag = None
        if current_act >= 1 or empowered_act:
            sat = get_act_saturation(max(1, current_act if current_act >= 1 else 2))
            spd_mult = float(sat.get("speed_multiplier", 1.0))
            cd_mult = float(sat.get("cooldown_multiplier", 1.0))
            if empowered_act and current_act <= 2:
                hp_mult = float(max(ACT2_HP_MULTIPLIER, float(sat["hp_multiplier"])))
                dmg_mult = float(max(ACT2_DAMAGE_MULTIPLIER, float(sat["damage_multiplier"])))
                emp_flag = True
            else:
                hp_mult = float(sat["hp_multiplier"])
                dmg_mult = float(sat["damage_multiplier"])
                emp_flag = bool(sat["empowered"])

        next_net_id = max((getattr(e, "network_id", -1) for e in enemies), default=0) + 1
        cx, cy = self.get_center()
        count = int(RIMECREST_ARBITER_MINION_COUNT)
        minion_classes = (SmearEnemy, FlutterEnemy, SmearEnemy)

        for idx in range(count):
            angle = (2.0 * math.pi * idx) / max(1, count) + (math.pi / 6.0)
            ring_r = 104.0
            cls_m = minion_classes[idx % len(minion_classes)]
            minion = cls_m(cx + math.cos(angle) * ring_r - 20.0, cy + math.sin(angle) * ring_r - 20.0)
            if world is not None and hasattr(world, "find_nearest_walkable_spawn"):
                wx, wy = world.find_nearest_walkable_spawn(minion.x, minion.y, minion.width, minion.height)
                minion.x, minion.y = float(wx), float(wy)
                minion.origin_x, minion.origin_y = float(wx), float(wy)
            if (
                hp_mult != 1.0
                or dmg_mult != 1.0
                or emp_flag is not None
                or spd_mult != 1.0
                or cd_mult != 1.0
            ):
                minion.apply_act_scaling(
                    hp_mult,
                    dmg_mult,
                    empowered=emp_flag,
                    speed_multiplier=spd_mult,
                    cooldown_multiplier=cd_mult,
                )
            minion.network_id = next_net_id
            next_net_id += 1
            enemies.append(minion)

        if world is not None:
            world._enemies = list(enemies)

    def update(self, dt, state):
        """Advance RimecrestArbiterBoss AI and trigger Phase 2 gale + 3-minion glacial vanguard at <= 50% HP."""
        super().update(dt, state)
        if self.is_summoning_or_dormant():
            return
        from constants import FROST_BREATH_SFX, RIMECREST_ARBITER_PHASE2_HP_RATIO
        if (
            not self.minions_summoned
            and self.hp > 0
            and self.max_hp > 0
            and self.hp <= self.max_hp * RIMECREST_ARBITER_PHASE2_HP_RATIO
        ):
            self.phase = 2
            self.minions_summoned = True
            audio = getattr(state, "audio_manager", None)
            if audio is not None:
                try:
                    audio.play_sfx(FROST_BREATH_SFX)
                except Exception:
                    pass
            net_mode = getattr(getattr(state, "network_manager", None), "network_mode", "OFFLINE")
            if net_mode != "CLIENT":
                self._summon_phase2_vanguard(state)

    def _update_chase(self, dt, state):
        """Pursue target and initiate HALBERD sweep or FROST_BREATH cone within engagement range."""
        if self.active_target and self.cooldown_timer <= 0:
            cx, cy = self.get_center()
            tx, ty = self.active_target
            dist = math.hypot(tx - cx, ty - cy)
            if dist <= TILE_SIZE * 4.8:
                self.state = ActorState.WIND_UP
                self.combat_timer = self.wind_up_duration
                self.vx, self.vy = 0.0, 0.0
                self.has_hit_this_attack = False
                self._breath_sfx_played = False
                if dist > 0.1:
                    self.facing = ((tx - cx) / dist, (ty - cy) / dist)
                self._clear_nav_path()
                audio = getattr(state, "audio_manager", None)
                if audio is not None:
                    try:
                        audio.play_sfx("enemy_telegraph.ogg")
                    except Exception:
                        pass
                return
        super()._update_chase(dt, state)

    def _update_wind_up(self, dt, game_state):
        """Hold stance cleanly during telegraph wind-up."""
        self.vx, self.vy = 0.0, 0.0
        super()._update_wind_up(dt, game_state)

    def _on_start_strike(self, game_state):
        """Play Frost Breath gale SFX when entering FROST_BREATH strike."""
        self.vx, self.vy = 0.0, 0.0
        if self.attack_mode == "FROST_BREATH" and not self._breath_sfx_played:
            self._breath_sfx_played = True
            from constants import FROST_BREATH_SFX
            audio = getattr(game_state, "audio_manager", None)
            if audio is not None:
                try:
                    audio.play_sfx(FROST_BREATH_SFX)
                except Exception:
                    pass

    def _update_strike(self, dt, game_state):
        """Execute HALBERD cleave (+0.5 chill) or FROST_BREATH cone (+0.5 chill once per breath), then alternate."""
        self.vx, self.vy = 0.0, 0.0
        if self.attack_mode == "HALBERD":
            if not self.has_hit_this_attack and self.attempt_damage_player(game_state):
                self.has_hit_this_attack = True
                if self.stagger_timer <= 0.0:
                    from constants import RIMECREST_CHILL_HIT_AMOUNT
                    player = getattr(game_state, "player", None)
                    if player is not None and hasattr(player, "apply_frost_exposure"):
                        player.apply_frost_exposure(float(RIMECREST_CHILL_HIT_AMOUNT))
        else:
            if not self._breath_sfx_played:
                self._on_start_strike(game_state)
            self._apply_frost_breath_tick(dt, game_state)
            self.has_hit_this_attack = True

        super()._update_strike(dt, game_state)
        if self.state != ActorState.STRIKE:
            self.vx, self.vy = 0.0, 0.0
            self._breath_sfx_played = False
            self._breath_hit_applied = False
            self.attack_mode = "FROST_BREATH" if self.attack_mode == "HALBERD" else "HALBERD"

    def on_death(self, state):
        """Plant persistent non-interactive RimecrestHalberd, scatter 2 glacial weapons, and drop ChoiceOfFates."""
        from constants import RIMECREST_ARBITER_HALBERD_HEIGHT, RIMECREST_ARBITER_HALBERD_WIDTH
        from engine.loot import ChoiceOfFates
        from engine.world import RimecrestHalberd, WeaponPickup

        world = getattr(state, "world", None)
        if world is None:
            return

        cx, cy = self.get_center()
        hx = cx - RIMECREST_ARBITER_HALBERD_WIDTH / 2.0
        hy = cy - RIMECREST_ARBITER_HALBERD_HEIGHT / 2.0
        if hasattr(world, "find_nearest_walkable_spawn"):
            hx, hy = world.find_nearest_walkable_spawn(
                hx, hy, RIMECREST_ARBITER_HALBERD_WIDTH, RIMECREST_ARBITER_HALBERD_HEIGHT
            )
        world.interactables.append(RimecrestHalberd((hx, hy)))

        weapon_pool = [
            {
                "name": "Anomalous Rimecrest Glaive",
                "damage": 26,
                "modifiers": {"bleed": 5.5},
                "description": "Mirror-ice halberd edge inflicting 5.5 frost-bleed damage per second.",
            },
            {
                "name": "Anomalous Glacier Ward",
                "damage": 23,
                "modifiers": {"damage_negation_on_hit": 5.5},
                "description": "Taking damage temporarily reduces next damage taken by 5.5.",
            },
            {
                "name": "Anomalous Thaw-Quill",
                "damage": 22,
                "modifiers": {"slow_hp_regen": 1.3},
                "description": "Warms the Reader's inkflow, regenerating 1.3 HP per second.",
            },
            {
                "name": "Anomalous Permafrost Plate",
                "damage": 25,
                "modifiers": {"max_hp_boost": 25.0},
                "description": "Fortifies the Reader with +25 Max HP.",
            },
        ]
        chosen_pair = random.sample(weapon_pool, 2)
        scatter_offsets = ((-48.0, 12.0), (48.0, -12.0))
        for weapon_template, (ox_w, oy_w) in zip(chosen_pair, scatter_offsets):
            wx, wy = cx + ox_w - TILE_SIZE / 2.0, cy + oy_w - TILE_SIZE / 2.0
            if hasattr(world, "find_nearest_walkable_spawn"):
                wx, wy = world.find_nearest_walkable_spawn(wx, wy, TILE_SIZE, TILE_SIZE)
            weapon_copy = {
                "name": weapon_template["name"],
                "damage": weapon_template["damage"],
                "modifiers": dict(weapon_template["modifiers"]),
                "description": weapon_template["description"],
            }
            world.interactables.append(WeaponPickup((wx, wy), weapon_copy))

        loot_list = getattr(state, "loot", None)
        if isinstance(loot_list, list) and not any(isinstance(i, ChoiceOfFates) for i in loot_list):
            loot_list.append(ChoiceOfFates(cx, cy))
        print("[LOOT] RimecrestArbiterBoss planted mirror-ice halberd, 2 scattered weapons, and Choice of Fates.")


class FinalAuthor(Boss):
    """The Final Author."""
    def __init__(self, x, y, hp=None, id=None):
        from constants import FINAL_AUTHOR_MAX_HP, FINAL_AUTHOR_WIND_UP_DURATION, MINIBOSS_SPEED
        initial_hp = hp if hp is not None else FINAL_AUTHOR_MAX_HP
        super().__init__(x, y, 80, 80, initial_hp, id=id, name="The Final Author")
        self.speed = MINIBOSS_SPEED * 0.8
        self.detect_radius = 2000.0
        self.loot_tier = 0 # No rewards for the final redaction

        self.wind_up_duration = FINAL_AUTHOR_WIND_UP_DURATION
        self.strike_duration = 0.4
        self.recovery_duration = 1.0

ENEMY_REGISTRY = {
    "SlugEnemy": SlugEnemy, "BatEnemy": BatEnemy, "FlutterEnemy": FlutterEnemy,
    "BindlingEnemy": BindlingEnemy, "Miniboss": Miniboss, "MinibossM2": MinibossM2,
    "MinibossM3": MinibossM3, "SmearEnemy": SmearEnemy, "SentryEnemy": SentryEnemy,
    "PunctuationWolfEnemy": PunctuationWolfEnemy,
    "NightBoss": NightBoss, "SlugBoss": SlugBoss, "MeadowCensorBoss": MeadowCensorBoss,
    "RimecrestArbiterBoss": RimecrestArbiterBoss,
    "FinalAuthor": FinalAuthor,
}

SYMBOL_REGISTRY = {
    'Z': SlugEnemy, 'A': BatEnemy, 'f': FlutterEnemy, 'b': BindlingEnemy,
    'E': Miniboss, '2': MinibossM2, '3': MinibossM3, 's': SmearEnemy,
    'Y': SentryEnemy, 'w': PunctuationWolfEnemy, '!': FinalAuthor
}
