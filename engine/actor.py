"""
Unified Actor base class for mobile entities (Enemies, NPCs).
Implements the Stanza System for marker-based patrols.
"""
import math
import random
from enum import Enum, auto
from engine.physics import check_aabb_collision, resolve_wall_collision
from constants import TILE_SIZE

class ActorState(Enum):
    IDLE = auto()        # Waiting or wandering
    PATROLLING = auto()   # Moving between markers
    CHASE = auto()       # Aggressive pursuit
    ENGAGED = auto()     # Interaction/Dialogue pause

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
        
        self.state = ActorState.IDLE
        self.patrol_route = [] # List of entity objects (PatrolPoints)
        self.patrol_idx = 0
        self.wait_timer = 0.0
        self.patrol_speed_multiplier = 0.5
        
        self.stagger_timer = 0.0
        self.name = name
        self.detect_radius = 5.0 * TILE_SIZE
        self.is_miniboss = False
        self.is_stationary = False
        self.loot_tier = 3

    @property
    def rect(self):
        """Standard rect tuple (x, y, w, h) for collision logic."""
        return (self.x, self.y, self.width, self.height)

    def get_center(self):
        return self.x + self.width / 2, self.y + self.height / 2

    def get_rect(self):
        return self.rect

    def take_damage(self, amount):
        """Standard damage logic."""
        self.hp -= amount
        if amount >= 10:
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
        if self.stagger_timer > 0:
            self.stagger_timer -= dt
            return

        # 1. State Transition Check
        # NPCs: Shift to ENGAGED if dialogue is active
        # Enemies: Shift to CHASE if player in radius
        self._update_state_logic(dt, state)

        # 2. Movement Logic
        if self.state == ActorState.PATROLLING:
            self._update_patrol(dt, state)
        elif self.state == ActorState.CHASE:
            self._update_chase(dt, state)
        elif self.state == ActorState.IDLE:
            self._update_idle(dt, state)
        # ENGAGED: No movement

    def _update_state_logic(self, dt, game_state):
        """Determine current behavior state."""
        # NPCs (Chronicler) never CHASE. They only ENGAGE or PATROL.
        if "Chronicler" in self.name:
            if game_state.active_dialogue and game_state.active_dialogue.get("speaker") == self.name:
                self.state = ActorState.ENGAGED
                self.vx, self.vy = 0, 0
                return
        else:
            # Enemies CHASE if player is detected
            player_cx, player_cy = game_state.player.get_center()
            cx, cy = self.get_center()
            dist_sq = (player_cx - cx)**2 + (player_cy - cy)**2
            
            if dist_sq <= self.detect_radius**2:
                self.state = ActorState.CHASE
                return

        # If not chasing/engaged, and has route + not stationary, patrol
        if self.patrol_route and not self.is_stationary:
            self.state = ActorState.PATROLLING
        else:
            self.state = ActorState.IDLE

    def _update_patrol(self, dt, game_state):
        """Move toward the current patrol point."""
        if self.wait_timer > 0:
            self.wait_timer -= dt
            self.vx, self.vy = 0, 0
            return

        if not self.patrol_route:
            self.state = ActorState.IDLE
            return

        target = self.patrol_route[self.patrol_idx]
        # Target center calculation
        tx = target.x + target.width / 2
        ty = target.y + target.height / 2
        
        cx, cy = self.get_center()
        dx, dy = tx - cx, ty - cy
        dist_sq = dx*dx + dy*dy
        
        if dist_sq < 100: # Reached marker (within 10 pixels)
            self._on_reach_marker(target)
            return

        dist = math.sqrt(dist_sq)
        move_speed = self.speed * self.patrol_speed_multiplier
        self.vx, self.vy = (dx / dist) * move_speed, (dy / dist) * move_speed
        
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Resolve collisions
        walls = game_state.world.get_nearby_walls(self.get_rect())
        self.x, self.y = resolve_wall_collision(self.get_rect(), walls)

    def _on_reach_marker(self, marker):
        """Handle reaching a patrol point."""
        import random
        wait_min = getattr(marker, 'wait_min', 2.0)
        wait_max = getattr(marker, 'wait_max', 5.0)
        self.wait_timer = random.uniform(wait_min, wait_max)
        
        # Advance index
        self.patrol_idx = (self.patrol_idx + 1) % len(self.patrol_route)
        print(f"[ACTOR] {self.name} reached marker. Waiting {self.wait_timer:.1f}s")

    def _update_chase(self, dt, game_state):
        """Aggressive pursuit logic."""
        player_cx, player_cy = game_state.player.get_center()
        cx, cy = self.get_center()
        dx, dy = player_cx - cx, player_cy - cy
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > 0:
            self.vx, self.vy = (dx / dist) * self.speed, (dy / dist) * self.speed
            self.x += self.vx * dt
            self.y += self.vy * dt
            
            walls = game_state.world.get_nearby_walls(self.get_rect())
            self.x, self.y = resolve_wall_collision(self.get_rect(), walls)

    def _update_idle(self, dt, game_state):
        """Generic idle/wander behavior."""
        self.vx, self.vy = 0, 0
