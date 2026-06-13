"""
Tests for the Flask healing system.
"""
import pytest
from engine.game_state import GameState
from engine.player import Player, PlayerStateEnum
from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES, FLASK_HEAL_AMOUNT

class MockWorld:
    def __init__(self, name="custom"):
        self.name = name
        self.grid = [[0 for _ in range(10)] for _ in range(10)]
        self.player_start = (0, 0)
        self.interactables = []
    def get_nearby_walls(self, rect): return []
    def get_nearby_interactables(self, rect): return []

def test_flask_healing():
    gs = GameState(auto_load=False)
    gs.world = MockWorld()
    # Ensure stats exist for Edification
    gs.player.stats = {"attack_modifier": 0, "max_hp_modifier": 0, "edification": 1}
    gs.player.hp = 50
    gs.player.flask_charges = 3
    
    # Use flask directly to avoid update loop complexities
    gs.player.use_flask()
    
    assert gs.player.hp == 50 + FLASK_HEAL_AMOUNT
    assert gs.player.flask_charges == 2

def test_flask_clamped_to_max_hp():
    gs = GameState(auto_load=False)
    gs.world = MockWorld()
    gs.player.stats = {"attack_modifier": 0, "max_hp_modifier": 0, "edification": 1}
    gs.player.hp = PLAYER_MAX_HP - 10
    gs.player.flask_charges = 3
    
    gs.player.use_flask()
    
    assert gs.player.hp == PLAYER_MAX_HP
    assert gs.player.flask_charges == 2

def test_flask_no_charges():
    gs = GameState(auto_load=False)
    gs.world = MockWorld()
    gs.player.stats = {"attack_modifier": 0, "max_hp_modifier": 0, "edification": 1}
    gs.player.hp = 50
    gs.player.flask_charges = 0
    
    gs.player.use_flask()
    
    assert gs.player.hp == 50
    assert gs.player.flask_charges == 0

def test_flask_full_hp_no_consumption():
    gs = GameState(auto_load=False)
    gs.world = MockWorld()
    gs.player.stats = {"attack_modifier": 0, "max_hp_modifier": 0, "edification": 1}
    gs.player.hp = PLAYER_MAX_HP
    gs.player.flask_charges = 3
    
    gs.player.use_flask()
    
    assert gs.player.hp == PLAYER_MAX_HP
    assert gs.player.flask_charges == 3

def test_flask_reset_on_death():
    gs = GameState(auto_load=False)
    from engine.stats import StatisticsTracker
    gs.stats = StatisticsTracker()
    # Mock world to avoid wellsprings
    gs.world = MockWorld("not_sanctuary") 
    gs.player.stats = {"attack_modifier": 0, "max_hp_modifier": 0, "edification": 1}
    gs.player.flask_charges = 0
    
    # Kill player
    gs.player.take_damage(PLAYER_MAX_HP + 10)
    # Trigger death sequence initiation
    gs.update(0.016, {'move': (0, 0), 'attack': False, 'flask': False})
    
    # Should be in death state (timer > 0)
    assert gs.death_timer > 0
    # HP should be 0 during the death sequence
    assert gs.player.hp == 0
    
    # Fast forward death sequence (2.0s duration)
    gs.update(2.1, {'move': (0, 0), 'attack': False, 'flask': False})
    
    # Should be back in sanctuary with full health and flasks
    assert gs.world.name == "sanctuary"
    assert gs.player.hp == gs.player.max_hp
    assert gs.player.flask_charges == FLASK_MAX_CHARGES
