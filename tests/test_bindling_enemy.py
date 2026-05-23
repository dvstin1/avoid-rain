
import pytest
from engine.enemy import BindlingEnemy
from constants import TILE_SIZE, BINDLING_MAX_HP, BINDLING_HEAL_RATE

class MockPlayer:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
        self.bind_timer = 0.0
    def get_center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)
    def take_damage(self, amount):
        pass

class MockWorld:
    def __init__(self, wall_near=False):
        # 10x10 empty grid
        self.grid = [[0 for _ in range(10)] for _ in range(10)]
        if wall_near:
            # Place a wall at (1,1)
            self.grid[1][1] = 1 # TILE_WALL
    def get_nearby_walls(self, rect):
        return []

class MockState:
    def __init__(self, player_x, player_y, wall_near=False):
        self.player = MockPlayer(player_x, player_y)
        self.world = MockWorld(wall_near)

def test_bindling_healing_near_margin():
    """Verify that Bindling heals when near a wall."""
    # Bindling near (1,1) wall. Grid coords (1,1) is (40,40) pixels.
    # Bindling at (45, 45)
    bindling = BindlingEnemy(45, 45)
    bindling.hp = 10 # Heavily damaged
    
    state = MockState(500, 500, wall_near=True)
    dt = 1.0
    bindling.update(dt, state)
    
    assert bindling.hp > 10
    assert bindling.hp == 10 + BINDLING_HEAL_RATE

def test_bindling_no_healing_far_from_margin():
    """Verify that Bindling does not heal when far from walls."""
    bindling = BindlingEnemy(200, 200) # Far from (1,1) wall
    bindling.hp = 10
    
    state = MockState(500, 500, wall_near=True)
    bindling.update(1.0, state)
    
    assert bindling.hp == 10

def test_bindling_apply_bind_effect():
    """Verify that Bindling hit applies bind_timer to player."""
    bindling = BindlingEnemy(100, 100)
    state = MockState(100, 100) # Directly touching player
    
    bindling.attempt_damage_player(state)
    
    assert state.player.bind_timer > 0
