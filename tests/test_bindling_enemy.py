
import pytest
import math
from engine.enemy import BindlingEnemy
from constants import TILE_SIZE, BINDLING_MAX_HP, BINDLING_HEAL_RATE, BIND_DURATION

class MockPlayer:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
        self.bind_timer = 0.0
    def get_center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)
    def take_damage(self, amount, bypass_stagger=False, audio_manager=None):
        pass
    @property
    def rect(self):
        return (self.x, self.y, self.width, self.height)
    def is_parry_active(self):
        return False

class MockWorld:
    def __init__(self, wall_near=False):
        self.name = "test_world"
        self.grid = [[0 for _ in range(10)] for _ in range(10)]
        self.wall_near = wall_near
        
    def get_nearby_walls(self, rect):
        if self.wall_near:
            # Return a wall rect that overlaps with (45, 45, 40, 40)
            return [(40, 40, 40, 40)]
        return []

class MockNetworkManager:
    def __init__(self):
        self.remote_players = {}
        self.identity = "LocalScholar"

class MockState:
    def __init__(self, player_x, player_y, wall_near=False):
        self.player = MockPlayer(player_x, player_y)
        self.world = MockWorld(wall_near)
        self.network_manager = MockNetworkManager()

def test_bindling_healing_near_margin():
    """Verify that Bindling heals when near a wall."""
    bindling = BindlingEnemy(45, 45)
    bindling.hp = 10 
    
    state = MockState(500, 500, wall_near=True)
    dt = 1.0
    bindling.update(dt, state)
    
    assert bindling.hp > 10
    assert math.isclose(bindling.hp, 10 + BINDLING_HEAL_RATE)

def test_bindling_no_healing_far_from_margin():
    """Verify that Bindling does not heal when far from walls."""
    bindling = BindlingEnemy(200, 200)
    bindling.hp = 10
    
    state = MockState(500, 500, wall_near=True)
    bindling.update(1.0, state)
    
    assert bindling.hp == 10

def test_bindling_apply_bind_effect():
    """Verify that Bindling hit applies bind_timer to player."""
    from constants import BIND_DURATION
    bindling = BindlingEnemy(100, 100)
    state = MockState(100, 100) # Directly touching player
    
    # We call attempt_damage_player manually
    hit = bindling.attempt_damage_player(state)
    
    assert hit is True
    assert state.player.bind_timer == BIND_DURATION
