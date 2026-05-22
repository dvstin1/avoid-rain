"""
Tests for the Flask healing system.
"""
from engine.game_state import GameState
from engine.player import Player
from constants import PLAYER_MAX_HP, FLASK_MAX_CHARGES, FLASK_HEAL_AMOUNT

def test_flask_healing():
    gs = GameState(auto_load=False)
    gs.player.hp = 50
    gs.player.flask_charges = 3
    
    # Use flask
    gs.update(0.1, {'move': (0, 0), 'attack': False, 'flask': True})
    
    assert gs.player.hp == 50 + FLASK_HEAL_AMOUNT
    assert gs.player.flask_charges == 2

def test_flask_clamped_to_max_hp():
    gs = GameState(auto_load=False)
    gs.player.hp = PLAYER_MAX_HP - 10
    gs.player.flask_charges = 3
    
    # Use flask
    gs.update(0.1, {'move': (0, 0), 'attack': False, 'flask': True})
    
    assert gs.player.hp == PLAYER_MAX_HP
    assert gs.player.flask_charges == 2

def test_flask_no_charges():
    gs = GameState(auto_load=False)
    gs.player.hp = 50
    gs.player.flask_charges = 0
    
    # Use flask
    gs.update(0.1, {'move': (0, 0), 'attack': False, 'flask': True})
    
    assert gs.player.hp == 50
    assert gs.player.flask_charges == 0

def test_flask_full_hp_no_consumption():
    gs = GameState(auto_load=False)
    gs.player.hp = PLAYER_MAX_HP
    gs.player.flask_charges = 3
    
    # Use flask
    gs.update(0.1, {'move': (0, 0), 'attack': False, 'flask': True})
    
    assert gs.player.hp == PLAYER_MAX_HP
    assert gs.player.flask_charges == 3

def test_flask_reset_on_death():
    gs = GameState(auto_load=False)
    gs.player.flask_charges = 0
    
    # Kill player
    gs.player.take_damage(PLAYER_MAX_HP + 10)
    gs.update(0.1, {'move': (0, 0), 'attack': False, 'flask': False})
    
    # Should be in bleaching state, not yet respawned
    assert gs.death_timer > 0
    assert gs.player.hp == 0
    
    # Advance time past 5 seconds
    gs.update(5.0, {'move': (0, 0), 'attack': False, 'flask': False})
    
    assert gs.player.hp == PLAYER_MAX_HP
    assert gs.player.flask_charges == FLASK_MAX_CHARGES
