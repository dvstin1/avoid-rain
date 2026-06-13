import math
import pytest
from engine.enemy import BatEnemy
from constants import BAT_MAX_HP, PLAYER_MAX_HP

class MockPlayer:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.width, self.height = 40, 40
        self.hp = PLAYER_MAX_HP
        self.stats = {"attack_modifier": 0, "max_hp_modifier": 0}
    def get_center(self): return (self.x + self.width/2, self.y + self.height/2)
    def take_damage(self, amount, bypass_stagger=False, audio_manager=None): 
        self.hp -= amount
    @property
    def rect(self): return (self.x, self.y, self.width, self.height)
    def is_parry_active(self): return False

class MockWorld:
    def __init__(self):
        self.name = "test_world"
        self.grid = [[0 for _ in range(20)] for _ in range(20)]
    def get_nearby_walls(self, rect): return []

class MockNetworkManager:
    def __init__(self):
        self.remote_players = {}
        self.identity = "LocalScholar"

class MockState:
    def __init__(self, x, y):
        self.player = MockPlayer(x, y)
        self.world = MockWorld()
        self.network_manager = MockNetworkManager()

def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def test_bat_enemy_movement():
    state = MockState(0, 0)
    bat = BatEnemy(100, 100) # Within detection (200px)
    
    before = distance((bat.x, bat.y), state.player.get_center())
    # Update
    bat.update(0.1, state)
    after = distance((bat.x, bat.y), state.player.get_center())
    
    assert after < before
    assert bat.vx != 0 or bat.vy != 0

def test_bat_enemy_damage():
    state = MockState(0, 0)
    bat = BatEnemy(0, 0) # On top
    
    state.player.hp = PLAYER_MAX_HP
    
    # Run multiple updates to cycle from IDLE -> WIND_UP -> STRIKE
    found_damage = False
    for _ in range(30):
        bat.update(0.1, state)
        if state.player.hp < PLAYER_MAX_HP:
            found_damage = True
            break
            
    assert found_damage is True

def test_bat_enemy_death():
    bat = BatEnemy(100, 100)
    bat.take_damage(BAT_MAX_HP)
    assert bat.is_dead()
