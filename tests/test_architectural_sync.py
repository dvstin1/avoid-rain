
import math
import pytest
from engine.enemy import MinibossM2, MinibossM3
from engine.game_state import GameState
from engine.world import WarpPortal
from constants import TILE_SIZE, PLAYER_MAX_HP

class MockPlayer:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.width, self.height = 40, 40
        self.hp = PLAYER_MAX_HP
        self.weapons = []
        self.active_weapon_idx = 0
        self.flask_charges = 3
    def get_center(self): return (self.x + self.width/2, self.y + self.height/2)
    def take_damage(self, amount): self.hp -= amount
    def get_active_weapon(self): return {"name": "Test", "damage": 10}

class MockWorld:
    def __init__(self, name="outside"):
        self.name = name
        self.grid = [[0 for _ in range(20)] for _ in range(20)]
        self.player_start = (0, 0)
    def get_nearby_walls(self, rect): return []
    def get_nearby_interactables(self, rect): return []

def test_m2_erratic_movement():
    """Verify MinibossM2 (Bleeding Scribe) has erratic (sine) movement component."""
    from engine.stats import StatisticsTracker
    state = GameState(auto_load=False)
    state.stats = StatisticsTracker()
    state.player = MockPlayer(200, 200) # Within detection (480px)
    m2 = MinibossM2(100, 100) # Pursuit starts
    
    # 1. Update and check velocity
    dt = 0.1
    m2.update(dt, state)
    v1 = (m2.vx, m2.vy)
    
    # 2. Update again and check that velocity changed significantly (erratic)
    m2.update(dt, state)
    v2 = (m2.vx, m2.vy)
    
    # In pursuit-only AI, vx/vy remains constant if distance is large.
    # With sine-wave, it fluctuates every frame.
    assert v1 != v2
    assert v1 != (0, 0)

def test_m3_teleportation():
    """Verify MinibossM3 (Forgotten Binder) teleports when player is too close."""
    from engine.stats import StatisticsTracker
    state = GameState(auto_load=False)
    state.stats = StatisticsTracker()
    # M3 at (0, 0), center (32, 32).
    # Player at (72, 72), center (92, 92).
    # dx=60, dy=60, dist_sq = 7200.
    # 6400 (WIND_UP threshold) < 7200 < 14400 (TELEPORT threshold).
    state.player = MockPlayer(72, 72)
    m3 = MinibossM3(0, 0)

    initial_pos = (m3.x, m3.y)
    m3.update(0.1, state)

    # dist_sq was 7200, should teleport.
    assert (m3.x, m3.y) != initial_pos

    assert m3._tele_timer > 0

def test_lifecycle_session_boundaries():
    """Verify active_session_in_progress toggles correctly."""
    from engine.stats import StatisticsTracker
    state = GameState(auto_load=False)
    state.stats = StatisticsTracker()
    state.world = MockWorld("outside") # Not in sanctuary
    
    # Debug check
    assert state.world.name == "outside"
    assert state.player is not None
    
    # 1. Save state while outside -> session should be in progress
    state.save_stats(wait=True)
    
    print(f"DEBUG: world_name={getattr(state.world, 'name')}")
    print(f"DEBUG: stats_data={state.stats.data}")
    
    assert state.stats.data["active_session_in_progress"] is True
    
    # 2. Return to Sanctuary via Warp -> session should be cleared
    warp = WarpPortal("sanctuary", 0, 0, (0, 0, 10, 10))
    warp.execute_interaction(state)
    assert state.stats.data["active_session_in_progress"] is False
    assert state.stats.data["run_state"] is None

def test_death_clears_session():
    """Verify player death clears the active session."""
    from engine.stats import StatisticsTracker
    state = GameState(auto_load=False)
    state.stats = StatisticsTracker()
    state.world = MockWorld("chapter1")
    state.save_stats(wait=True)
    assert state.stats.data["active_session_in_progress"] is True
    
    # Trigger death
    state.player.hp = 0
    state.respawn_player()
    
    assert state.stats.data["active_session_in_progress"] is False
    assert state.stats.data["run_state"] is None
