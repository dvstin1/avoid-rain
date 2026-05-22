"""
Tests for destructible props and Tier 4 loot drops.
"""
import pytest
import random
from engine.world import World, GameObject, LevelLoader
from engine.game_state import GameState
from engine.loot import TornPage, HealItem, roll_drop
from engine.player import PlayerStateEnum
from constants import SWORD_DAMAGE

def test_barrel_destruction():
    prototype = [
        "...",
        ".B.",
        "..."
    ]
    world = World(name='custom')
    world.load_from_prototype(prototype)
    
    barrel = world.interactables[0]
    assert barrel.name == "Barrel"
    assert barrel.is_breakable is True
    assert barrel.health == 1.0
    
    barrel.take_damage(SWORD_DAMAGE)
    assert barrel.health <= 0
    assert barrel.is_destroyed() is True

def test_game_state_barrel_hit():
    # Setup a game state with a barrel near the player
    prototype = [
        "P.B",
        "...",
        "..."
    ]
    state = GameState(auto_load=False)
    state.world.load_from_prototype(prototype)
    state.player.x, state.player.y = state.world.player_start
    
    # Force player to facing right
    state.player.facing = (1, 0)
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.attack_timer = 0.1
    
    # Initially 1 interactable (the barrel)
    assert len(state.world.interactables) == 1
    
    # Update should detect hit and destroy barrel
    # We pass a small dt
    state.update(0.01, {'move': (0, 0), 'attack': False})
    
    # Barrel should be removed
    assert len(state.world.interactables) == 0

def test_roll_drop_tier4_logic():
    # Mock state to capture loot
    class MockState:
        def __init__(self):
            self.loot = []
    
    state = MockState()
    
    # Test 100% drop (mocking random)
    original_random = random.random
    try:
        # Force 15% drop chance to pass (0.1 < 0.15)
        # And force TornPage (0.4 < 0.5)
        random.random = lambda: 0.1
        roll_drop(4, (100, 100), state)
        assert len(state.loot) == 1
        assert isinstance(state.loot[0], TornPage)
        
        # Force HealItem (0.6 > 0.5)
        state.loot = []
        random.random = lambda: 0.11 # first call for drop, then second for type?
        # Wait, my roll_drop uses random.random() twice.
        # Let's use a sequence
        vals = [0.1, 0.6]
        def mock_rand():
            return vals.pop(0)
        random.random = mock_rand
        roll_drop(4, (100, 100), state)
        assert len(state.loot) == 1
        assert isinstance(state.loot[0], HealItem)
        
        # Force no drop (0.2 > 0.15)
        state.loot = []
        random.random = lambda: 0.2
        roll_drop(4, (100, 100), state)
        assert len(state.loot) == 0
        
    finally:
        random.random = original_random

def test_heal_item_pickup():
    state = GameState(auto_load=False)
    state.player.hp = 50
    state.player.max_hp = 100
    
    heal = HealItem(state.player.x, state.player.y)
    heal.execute_pickup(state)
    
    assert state.player.hp == 60
