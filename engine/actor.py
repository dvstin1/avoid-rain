# copyright 2026 Dustin Massop, License: GPLv2
# pylint: disable=trailing-whitespace,missing-class-docstring,missing-function-docstring,too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,redefined-builtin,multiple-statements,no-value-for-parameter,too-many-branches,unused-argument,unnecessary-pass,redefined-outer-name,reimported,import-outside-toplevel,unused-import
"""
Unified Actor base class for mobile entities (Enemies, NPCs).
Implements the Stanza System for marker-based patrols.
"""
import math
import random
from enum import Enum, auto
from engine.physics import check_aabb_collision, resolve_wall_collision
from engine.pathfinding import find_path, has_line_of_sight
from constants import (
    ACTOR_ACTIVE_SIMULATION_RADIUS_TILES,
    DAMAGE_NUMBER_LIFETIME,
    PATHFINDING_LOS_CACHE_INTERVAL,
    PATHFINDING_MAX_RADIUS_TILES,
    PATHFINDING_PATROL_REPATH_INTERVAL,
    PATHFINDING_REPATH_INTERVAL,
    PATHFINDING_WAYPOINT_REACH_PX,
    PATROL_RETURN_SPEED_MULTIPLIER,
    PATROL_STALL_SKIP_TIME,
    TILE_SIZE,
)

class ActorState(Enum):
    IDLE = auto()        # Waiting or wandering
    PATROLLING = auto()   # Moving between markers
    CHASE = auto()       # Aggressive pursuit
    WIND_UP = auto()     # Preparing an attack (Telegraph)
    STRIKE = auto()      # Damage-dealing frames
    RECOVERY = auto()    # Post-attack vulnerability
    ENGAGED = auto()     # Interaction/Dialogue pause

class VisualLayer(Enum):
    """Layers for animation composition."""
    BASE = auto()      # The main action (IDLE, RUN, ATTACK)
    POSTURE = auto()   # Physical state (READY, WOUNDED, STAGGERED)
    OVERLAY = auto()   # Magical/Status effects (POISON, BIND, PARRY_GLOW)

class Actor:
    """Base class for all mobile entities following the 'Stanza' movement system."""
    def __init__(self, x, y, width, height, hp, id=None, name="Actor"):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.hp = hp
        self.max_hp = hp
        self.id = id
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 100.0
        self.facing = (1, 0)
        
        self.state = ActorState.IDLE
        self.patrol_route = [] # List of entity objects (PatrolPoints)
        self.patrol_idx = 0
        self.wait_timer = 0.0
        self.patrol_speed_multiplier = 0.5
        
        # Combat Stanzas (Timers in seconds)
        self.wind_up_duration = 0.4
        self.strike_duration = 0.2
        self.recovery_duration = 0.5
        self.combat_timer = 0.0
        self.attack_cooldown = 1.5
        self.cooldown_timer = 0.0
        self.has_hit_this_attack = False
        
        self.stagger_timer = 0.0
        self.name = name
        self.animation_timer = 0.0
        
        # Bleed status tracking
        self.bleed_timer = 0.0
        self.bleed_tick_timer = 0.0
        self.bleed_damage = 0.0
        self.frame_index = 0
        self.detect_radius = 5.0 * TILE_SIZE
        self.is_miniboss = False
        self.is_stationary = False
        self.is_breakable = False    # Required for breakable test in GameState
        self.is_interactive = False  # NPCs override this
        self.is_solid = False
        self.loot_tier = 3
        self.active_target = None # (x, y) target for chasing/attacking
        self._nav_path = []
        self._nav_goal_tile = None
        jitter_seed = (int(abs(x) * 17 + abs(y) * 31) % 37) / 37.0
        self._nav_jitter = jitter_seed * 0.35
        self._nav_repath_timer = self._nav_jitter
        self._nav_los_clear = False
        self._nav_los_timer = 0.0
        self._nav_solid_sig = None
        self._returning_to_patrol = False
        self._patrol_stall_timer = 0.0

    @staticmethod
    def get_active_runner_positions(game_state):
        """Return world-space centers of active runners (excluding Waiting Scholars & resting local player)."""
        cached = getattr(game_state, "_frame_runner_positions", None)
        if cached is not None:
            return cached
        runners = []
        player = getattr(game_state, "player", None)
        if (
            player is not None
            and hasattr(player, "get_center")
            and getattr(game_state, "active_respite", None) is None
            and getattr(player, "hp", 1) > 0
            and float(getattr(game_state, "death_timer", 0.0) or 0.0) <= 0.0
        ):
            runners.append(player.get_center())
        in_sanctuary = bool(getattr(game_state, "in_sanctuary", False))
        net = getattr(game_state, "network_manager", None)
        for p_data in getattr(net, "remote_players", {}).values():
            if not in_sanctuary and p_data.get("in_sanctuary", False):
                continue
            runners.append((float(p_data.get("x", 0.0)) + 20.0, float(p_data.get("y", 0.0)) + 20.0))
        return runners

    def is_within_active_simulation(self, game_state):
        """Return True if actor should run full AI/pathfinding this frame."""
        if getattr(self, "persistent_pursuit", False):
            return True
        if self.name in ("Night Boss", "The Final Author", "The Chronicler") or self.__class__.__name__ in (
            "NightBoss",
            "SlugBoss",
            "MeadowCensorBoss",
            "RimecrestArbiterBoss",
            "GaleVaneRaptorBoss",
            "TypesetterAutomatonBoss",
            "GlassKilnBasiliskBoss",
            "FinalAuthor",
        ):
            return True
        if self.bleed_timer > 0 or self.stagger_timer > 0:
            return True
        if self.state in (ActorState.WIND_UP, ActorState.STRIKE, ActorState.RECOVERY, ActorState.CHASE):
            return True

        runners = self.get_active_runner_positions(game_state)
        if not runners:
            return False
        cx, cy = self.get_center()
        sim_rad_sq = (ACTOR_ACTIVE_SIMULATION_RADIUS_TILES * TILE_SIZE) ** 2
        for rx, ry in runners:
            if (cx - rx) ** 2 + (cy - ry) ** 2 <= sim_rad_sq:
                return True
        return False

    def _clear_nav_path(self):
        """Reset cached A* waypoints and repath timer."""
        self._nav_path = []
        self._nav_goal_tile = None
        self._nav_repath_timer = 0.0
        self._nav_los_clear = False
        self._nav_los_timer = 0.0

    def _get_navigation_waypoint(self, dt, game_state, target_x, target_y, repath_interval=PATHFINDING_REPATH_INTERVAL):
        """Return next world-space steering point toward (target_x, target_y) using A* when blocked."""
        self._nav_repath_timer = max(0.0, self._nav_repath_timer - dt)
        self._nav_los_timer = max(0.0, self._nav_los_timer - dt)
        world = getattr(game_state, "world", None)
        if world is None or not getattr(world, "grid", None):
            return (target_x, target_y)

        cx, cy = self.get_center()
        goal_tile = (int(target_x // TILE_SIZE), int(target_y // TILE_SIZE))
        goal_moved = (
            self._nav_goal_tile is None
            or abs(goal_tile[0] - self._nav_goal_tile[0]) > 1
            or abs(goal_tile[1] - self._nav_goal_tile[1]) > 1
        )
        solid_sig = getattr(world, "_nav_solid_sig", None)
        if solid_sig is not None and solid_sig != self._nav_solid_sig:
            self._nav_solid_sig = solid_sig
            self._nav_los_timer = 0.0

        # Fast path 1: Cached clear line-of-sight on current leg
        if not goal_moved and self._nav_los_clear and self._nav_los_timer > 0.0:
            return (target_x, target_y)

        # Fast path 2: Active A* waypoint list still valid before repath timer expires
        while self._nav_path:
            wx, wy = self._nav_path[0]
            if (wx - cx) ** 2 + (wy - cy) ** 2 <= PATHFINDING_WAYPOINT_REACH_PX ** 2:
                self._nav_path.pop(0)
            else:
                break
        if self._nav_path and not goal_moved and self._nav_repath_timer > 0.0:
            return self._nav_path[0]

        # Re-evaluate LOS / A* only when timer expires or target tile moved
        if goal_moved or self._nav_los_timer <= 0.0 or self._nav_repath_timer <= 0.0:
            los_interval = max(PATHFINDING_LOS_CACHE_INTERVAL, repath_interval * 0.5) + self._nav_jitter
            if has_line_of_sight(world, (cx, cy), (target_x, target_y)):
                self._nav_solid_sig = getattr(world, "_nav_solid_sig", None)
                self._nav_goal_tile = goal_tile
                self._nav_path = []
                self._nav_los_clear = True
                self._nav_los_timer = los_interval
                return (target_x, target_y)

            self._nav_solid_sig = getattr(world, "_nav_solid_sig", None)
            self._nav_los_clear = False
            self._nav_los_timer = los_interval
            if goal_moved or self._nav_repath_timer <= 0.0:
                self._nav_path = find_path(world, (cx, cy), (target_x, target_y))
                self._nav_goal_tile = goal_tile
                self._nav_repath_timer = repath_interval + self._nav_jitter
                while self._nav_path:
                    wx, wy = self._nav_path[0]
                    if (wx - cx) ** 2 + (wy - cy) ** 2 <= PATHFINDING_WAYPOINT_REACH_PX ** 2:
                        self._nav_path.pop(0)
                    else:
                        break

        if self._nav_path:
            return self._nav_path[0]
        return (target_x, target_y)

    def get_visual_packet(self):
        """Returns a composable packet of visual intents for the renderer."""
        # 1. Base Layer
        base = "IDLE"
        if abs(self.vx) > 1.0 or abs(self.vy) > 1.0: base = "RUN"
        if self.state == ActorState.WIND_UP: base = "WIND_UP"
        if self.state == ActorState.STRIKE: base = "STRIKE"
        if self.state == ActorState.RECOVERY: base = "RECOVERY"
        
        # 2. Posture Layer
        posture = "READY"
        if self.hp / self.max_hp < 0.3: posture = "WOUNDED"
        if self.stagger_timer > 0: posture = "STAGGERED"
        
        # 3. Overlays
        overlays = []
        if getattr(self, 'bind_timer', 0) > 0: overlays.append("BIND")
        
        return {
            "base": base,
            "posture": posture,
            "overlays": overlays,
            "facing": self.facing,
            "timer": self.combat_timer if self.combat_timer > 0 else 0.0,
            "anim_timer": self.animation_timer,
            "progress": 0.0 # To be calculated if needed
        }

    @property
    def rect(self):
        """Standard rect tuple (x, y, w, h) for collision logic."""
        return (self.x, self.y, self.width, self.height)

    def get_center(self):
        return self.x + self.width / 2, self.y + self.height / 2

    def get_rect(self):
        return self.rect

    def take_damage(self, amount, bypass_stagger=False):
        """Standard damage logic."""
        self.hp -= amount
        if not bypass_stagger and amount >= 10:
            self.stagger_timer = 0.2

    def is_staggered(self):
        return self.stagger_timer > 0

    def is_dead(self):
        return self.hp <= 0

    def to_dict(self):
        return {
            "type": self.__class__.__name__,
            "x": self.x,
            "y": self.y,
            "hp": self.hp,
            "id": self.id,
            "is_stationary": self.is_stationary
        }

    @classmethod
    def from_dict(cls, data):
        inst = cls(data["x"], data["y"], hp=data["hp"], id=data.get("id"))
        inst.is_stationary = data.get("is_stationary", False)
        return inst

    def update(self, dt, state):
        """Unified state machine update."""
        if not self.is_within_active_simulation(state):
            self.vx = 0.0
            self.vy = 0.0
            return

        self.animation_timer += dt

        # Bleed ticking (applied even if staggered)
        if self.bleed_timer > 0 and self.hp > 0:
            self.bleed_timer -= dt
            self.bleed_tick_timer -= dt
            if self.bleed_tick_timer <= 0:
                self.take_damage(self.bleed_damage, bypass_stagger=True)
                # Spawning damage number
                if hasattr(state, 'damage_numbers'):
                    state.damage_numbers.append({
                        'val': self.bleed_damage, 'pos': (self.x + 10, self.y - 20),
                        'time': DAMAGE_NUMBER_LIFETIME, 'color': (180, 0, 0)
                    })
                self.bleed_tick_timer = 1.0

        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

        # 0. Global Timers
        if self.cooldown_timer > 0:
            self.cooldown_timer -= dt

        # 1. State Transition Check
        self._update_state_logic(dt, state)

        # 2. Movement & Combat Logic
        if self.state == ActorState.PATROLLING:
            self._update_patrol(dt, state)
        elif self.state == ActorState.CHASE:
            self._update_chase(dt, state)
        elif self.state == ActorState.IDLE:
            self._update_idle(dt, state)
        elif self.state == ActorState.WIND_UP:
            self._update_wind_up(dt, state)
        elif self.state == ActorState.STRIKE:
            self._update_strike(dt, state)
        elif self.state == ActorState.RECOVERY:
            self._update_recovery(dt, state)
        # ENGAGED: No movement

        # 3. Update Facing (Unified Rule)
        # Priority 1: If attacking, face the target
        if self.state in (ActorState.WIND_UP, ActorState.STRIKE) and self.active_target:
            tx, ty = self.active_target
            cx, cy = self.get_center()
            dx, dy = tx - cx, ty - cy
            mag = math.sqrt(dx*dx + dy*dy)
            if mag > 0.1:
                self.facing = (dx/mag, dy/mag)
        # Priority 2: If moving, face the direction of travel
        elif abs(self.vx) > 0.1 or abs(self.vy) > 0.1:
            mag = math.sqrt(self.vx**2 + self.vy**2)
            if mag > 0.1:
                self.facing = (self.vx/mag, self.vy/mag)

    def _update_state_logic(self, dt, game_state):
        """Determine current behavior state."""
        # NPCs (Chronicler, The Binder) never CHASE. They only ENGAGE or PATROL/IDLE.
        if "Chronicler" in self.name or self.name == "The Binder":
            if (
                game_state.active_dialogue and game_state.active_dialogue.get("speaker") == self.name
            ) or (
                self.name == "The Binder" and getattr(game_state, "binder_dialog", None)
            ):
                self.state = ActorState.ENGAGED
                self.vx, self.vy = 0, 0
                return
            if self.patrol_route and not self.is_stationary:
                self.state = ActorState.PATROLLING
            else:
                self.state = ActorState.IDLE
            return
        
        # Combat State Lock: If in a combat state, don't transition until timer ends
        if self.state in (ActorState.WIND_UP, ActorState.STRIKE, ActorState.RECOVERY):
            return

        # 1. Identify all potential targets (Local + Remote active runners)
        targets = self.get_active_runner_positions(game_state)

        # 2. Find Nearest Target
        cx, cy = self.get_center()
        best_dist_sq = float('inf')
        self.active_target = None

        for tx, ty in targets:
            d_sq = (tx - cx)**2 + (ty - cy)**2
            if d_sq < best_dist_sq:
                best_dist_sq = d_sq
                self.active_target = (tx, ty)

        # 3. State Transitions based on Target
        prev_state = self.state
        in_pursuit = bool(getattr(self, "persistent_pursuit", False))
        if self.active_target and (in_pursuit or best_dist_sq <= self.detect_radius**2):
            # If close enough and off cooldown, trigger attack sequence
            if best_dist_sq <= (TILE_SIZE * 2)**2 and self.cooldown_timer <= 0:
                self.state = ActorState.WIND_UP
                self.combat_timer = self.wind_up_duration
                self.vx, self.vy = 0, 0 # Stop movement to wind up
                self.has_hit_this_attack = False # Reset damage latch
                self._clear_nav_path()

                # Auditory Trigger (Telegraph)
                if hasattr(game_state, 'audio_manager') and game_state.audio_manager:
                    sfx_name = None
                    if self.name == "Slug":
                        sfx_name = "slug_attack.ogg"
                    elif self.name == "Bat":
                        sfx_name = "bat_attack.ogg"
                    
                    if sfx_name:
                        d = math.sqrt(best_dist_sq)
                        calculate_vol = getattr(game_state.audio_manager, 'calculate_spatial_volume', lambda dist: 1.0)
                        vol = calculate_vol(d)
                        game_state.audio_manager.play_sfx(sfx_name, volume=vol)
                    else:
                        game_state.audio_manager.play_sfx("enemy_telegraph.ogg")
            else:
                if prev_state != ActorState.CHASE:
                    self._clear_nav_path()
                    self._patrol_stall_timer = 0.0
                self.state = ActorState.CHASE
            return

        # If not chasing/engaged, and has route + not stationary, patrol (or return to patrol)
        if self.patrol_route and not self.is_stationary:
            if prev_state != ActorState.PATROLLING:
                # Re-anchor to the nearest waypoint on our patrol route when returning from chase/combat
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
                self._patrol_stall_timer = 0.0
                self._clear_nav_path()
            self.state = ActorState.PATROLLING
        else:
            self.state = ActorState.IDLE

    def _update_wind_up(self, dt, game_state):
        """Telegraphing the attack."""
        self.combat_timer -= dt
        if self.combat_timer <= 0:
            self.state = ActorState.STRIKE
            self.combat_timer = self.strike_duration
            self.has_hit_this_attack = False # Reset latch for new strike
            # One-time trigger at start of strike
            self._on_start_strike(game_state)

    def _update_strike(self, dt, game_state):
        """Active damage frames (Continuous check w/ latch)."""
        self.combat_timer -= dt
        
        # Per-frame damage attempt ONLY if we haven't hit yet this swing
        if not self.has_hit_this_attack and hasattr(self, 'attempt_damage_player'):
            if self.attempt_damage_player(game_state):
                self.has_hit_this_attack = True # Lock further damage for this animation

        if self.combat_timer <= 0:
            self.state = ActorState.RECOVERY
            self.combat_timer = self.recovery_duration

    def _on_start_strike(self, game_state):
        """Hook for one-time effects at the moment of impact."""
        pass

    def _update_recovery(self, dt, game_state):
        """Post-attack vulnerability."""
        self.combat_timer -= dt
        if self.combat_timer <= 0:
            self.state = ActorState.IDLE # Reset to check for chase
            self.cooldown_timer = self.attack_cooldown

    def _update_patrol(self, dt, game_state):
        """Move toward the current patrol point using A* pathfinding around obstacles."""
        if self.wait_timer > 0:
            self.wait_timer -= dt
            self.vx, self.vy = 0, 0
            return

        if not self.patrol_route:
            self.state = ActorState.IDLE
            return

        target = self.patrol_route[self.patrol_idx]
        tx = target.x + target.width / 2
        ty = target.y + target.height / 2

        cx, cy = self.get_center()
        dx_goal, dy_goal = tx - cx, ty - cy
        dist_sq_goal = dx_goal * dx_goal + dy_goal * dy_goal

        if dist_sq_goal < 100:  # Reached marker (within 10 pixels)
            self._on_reach_marker(target)
            return

        nav_x, nav_y = self._get_navigation_waypoint(
            dt, game_state, tx, ty, repath_interval=PATHFINDING_PATROL_REPATH_INTERVAL
        )
        dx, dy = nav_x - cx, nav_y - cy
        dist = math.hypot(dx, dy)
        if dist <= 0.001:
            dx, dy = dx_goal, dy_goal
            dist = math.sqrt(dist_sq_goal)

        speed_mult = (
            max(self.patrol_speed_multiplier, PATROL_RETURN_SPEED_MULTIPLIER)
            if self._returning_to_patrol
            else self.patrol_speed_multiplier
        )
        move_speed = self.speed * speed_mult
        prev_x, prev_y = self.x, self.y
        self.vx, self.vy = (dx / dist) * move_speed, (dy / dist) * move_speed

        self.x += self.vx * dt
        self.y += self.vy * dt

        # Resolve collisions (exclude self for solid NPCs stored in world.interactables)
        try:
            walls = game_state.world.get_nearby_walls(self.get_rect(), exclude_obj=self)
        except TypeError:
            walls = game_state.world.get_nearby_walls(self.get_rect())
        self.x, self.y = resolve_wall_collision(self.get_rect(), walls)

        moved = math.hypot(self.x - prev_x, self.y - prev_y)
        if move_speed > 0 and moved < move_speed * dt * 0.1:
            self._patrol_stall_timer += dt
            if self._patrol_stall_timer >= PATROL_STALL_SKIP_TIME:
                self._patrol_stall_timer = 0.0
                self._clear_nav_path()
                self.patrol_idx = (self.patrol_idx + 1) % len(self.patrol_route)
        else:
            self._patrol_stall_timer = 0.0

    def _on_reach_marker(self, marker):
        """Handle reaching a patrol point."""
        import random
        wait_min = getattr(marker, 'wait_min', 2.0)
        wait_max = getattr(marker, 'wait_max', 5.0)
        self.wait_timer = random.uniform(wait_min, wait_max)
        self._returning_to_patrol = False
        self._patrol_stall_timer = 0.0
        self._clear_nav_path()

        # Advance index
        self.patrol_idx = (self.patrol_idx + 1) % len(self.patrol_route)

    def _update_chase(self, dt, game_state):
        """Aggressive pursuit logic with A* pathfinding, breadcrumb pursuit, and wall-phase fallback."""
        if not self.active_target:
            self.state = ActorState.IDLE
            return

        target_cx, target_cy = self.active_target
        cx, cy = self.get_center()
        in_pursuit = bool(getattr(self, "persistent_pursuit", False))
        if in_pursuit:
            max_astar_px = PATHFINDING_MAX_RADIUS_TILES * TILE_SIZE
            if abs(target_cx - cx) <= max_astar_px and abs(target_cy - cy) <= max_astar_px:
                nav_x, nav_y = self._get_navigation_waypoint(
                    dt, game_state, target_cx, target_cy, repath_interval=PATHFINDING_REPATH_INTERVAL
                )
                target_cx, target_cy = nav_x, nav_y
            else:
                breadcrumbs = getattr(game_state, "player_breadcrumbs", None) or []
                if breadcrumbs and (target_cx - cx) ** 2 + (target_cy - cy) ** 2 > (TILE_SIZE * 3) ** 2:
                    # Choose the furthest breadcrumb along the trail within 6 tiles of the hunter
                    reach_sq = (TILE_SIZE * 6) ** 2
                    for bx, by in reversed(breadcrumbs):
                        if (bx - cx) ** 2 + (by - cy) ** 2 <= reach_sq:
                            target_cx, target_cy = bx, by
                            break
        else:
            target_cx, target_cy = self._get_navigation_waypoint(
                dt, game_state, target_cx, target_cy, repath_interval=PATHFINDING_REPATH_INTERVAL
            )

        dx, dy = target_cx - cx, target_cy - cy
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist > 0:
            prev_x, prev_y = self.x, self.y
            self.vx, self.vy = (dx / dist) * self.speed, (dy / dist) * self.speed
            self.x += self.vx * dt
            self.y += self.vy * dt
            
            phase_timer = getattr(self, "_phase_timer", 0.0)
            if in_pursuit and phase_timer > 0.0:
                self._phase_timer = max(0.0, phase_timer - dt)
            else:
                walls = game_state.world.get_nearby_walls(self.get_rect())
                self.x, self.y = resolve_wall_collision(self.get_rect(), walls)
                if in_pursuit:
                    from constants import MARGINALIA_HUNTER_STALL_TIME, MARGINALIA_HUNTER_PHASE_TIME
                    moved = math.hypot(self.x - prev_x, self.y - prev_y)
                    if moved < self.speed * dt * 0.15:
                        self._stall_timer = getattr(self, "_stall_timer", 0.0) + dt
                        if self._stall_timer >= MARGINALIA_HUNTER_STALL_TIME:
                            self._phase_timer = MARGINALIA_HUNTER_PHASE_TIME
                            self._stall_timer = 0.0
                    else:
                        self._stall_timer = 0.0

    def _update_idle(self, dt, game_state):
        """Generic idle/wander behavior."""
        self.vx, self.vy = 0, 0
