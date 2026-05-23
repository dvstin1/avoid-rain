
import math
import pytest
from engine.enemy import FlutterEnemy
from engine.game_state import GameState
from constants import TILE_SIZE, FLUTTER_SPEED

class MockPlayer:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40
    def get_center(self):
        return (self.x + self.width / 2, self.y + self.height / 2)

class MockWorld:
    def get_nearby_walls(self, rect):
        return []

class MockState:
    def __init__(self, player_x, player_y):
        self.player = MockPlayer(player_x, player_y)
        self.world = MockWorld()

def test_flutter_flee_behavior():
    """Verify that the Flutter enemy moves away from the player."""
    # Flutter at (100, 100)
    flutter = FlutterEnemy(100, 100)
    # Player at (120, 100) - to the right
    state = MockState(120, 100)
    
    dt = 0.1
    initial_x = flutter.x
    flutter.update(dt, state)
    
    # Flutter should move LEFT (away from player)
    assert flutter.x < initial_x
    assert flutter.vx < 0

def test_flutter_idle_outside_radius():
    """Verify that the Flutter stays idle if the player is far away."""
    # Flutter at (100, 100)
    flutter = FlutterEnemy(100, 100)
    # Player very far away
    state = MockState(1000, 1000)
    
    flutter.update(0.1, state)
    
    assert flutter.vx == 0
    assert flutter.vy == 0

def test_flutter_loot_tier():
    """Verify the Flutter has the correct loot tier."""
    flutter = FlutterEnemy(0, 0)
    assert flutter.loot_tier == 4
