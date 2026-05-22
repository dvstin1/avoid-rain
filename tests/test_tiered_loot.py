import pytest
import random
from engine.game_state import GameState
from engine.enemy import SlugEnemy, Miniboss
from engine.loot import roll_drop, TornPage, HealItem, ChoiceOfFates

def test_roll_drop_tier4_barrel():
    """Verify Tier 4 (Barrel) loot rolls."""
    state = GameState(auto_load=False)
    # Set seed for deterministic testing if possible, but roll_drop uses random.random()
    # Let's monkeypatch random.random to control outcomes
    
    # Test 15% drop chance - Success
    with pytest.MonkeyPatch.context() as m:
        m.setattr(random, "random", lambda: 0.1) # < 0.15
        m.setattr(random, "randint", lambda a, b: a)
        roll_drop(4, (100, 100), state)
        assert len(state.loot) == 1
        assert isinstance(state.loot[0], (TornPage, HealItem))

    # Test 15% drop chance - Failure
    state.loot = []
    with pytest.MonkeyPatch.context() as m:
        m.setattr(random, "random", lambda: 0.2) # > 0.15
        roll_drop(4, (100, 100), state)
        assert len(state.loot) == 0

def test_roll_drop_tier3_minor_enemy():
    """Verify Tier 3 (Minor Enemy) loot rolls."""
    state = GameState(auto_load=False)
    
    # Test 5% drop chance - Success
    with pytest.MonkeyPatch.context() as m:
        m.setattr(random, "random", lambda: 0.01) # < 0.05
        m.setattr(random, "randint", lambda a, b: 7)
        roll_drop(3, (100, 100), state)
        assert len(state.loot) == 1
        assert isinstance(state.loot[0], TornPage)
        assert state.loot[0].amount == 7

def test_roll_drop_tier2_miniboss():
    """Verify Tier 2 (Miniboss) loot rolls."""
    state = GameState(auto_load=False)
    
    # Guaranteed drop
    with pytest.MonkeyPatch.context() as m:
        m.setattr(random, "randint", lambda a, b: 35)
        roll_drop(2, (100, 100), state)
        assert len(state.loot) == 1
        assert isinstance(state.loot[0], TornPage)
        assert state.loot[0].amount == 35

def test_roll_drop_tier1_boss():
    """Verify Tier 1 (Boss) loot rolls."""
    state = GameState(auto_load=False)
    
    # Guaranteed Choice of Fates
    roll_drop(1, (100, 100), state)
    assert len(state.loot) == 1
    assert isinstance(state.loot[0], ChoiceOfFates)

def test_enemy_death_triggers_correct_tier(monkeypatch):
    """Verify that enemy death in GameState triggers the correct loot tier."""
    state = GameState(auto_load=False)
    
    # Add a Slug (Tier 3)
    slug = SlugEnemy(100, 100)
    slug.hp = 0
    state.enemies.append(slug)
    
    # Add a Miniboss (Tier 2)
    boss = Miniboss(200, 200)
    boss.hp = 0
    state.enemies.append(boss)
    
    # Mock roll_drop to track calls
    calls = []
    def mock_roll_drop(tier, pos, st):
        calls.append((tier, pos))
    
    monkeypatch.setattr("engine.loot.roll_drop", mock_roll_drop)
    
    state.update(0.1, {'move': (0,0), 'attack': False, 'flask': False})
    
    assert (3, (slug.x, slug.y)) in calls
    assert (2, (boss.x, boss.y)) in calls
    assert len(state.enemies) == 0

def test_choice_of_fates_application():
    """Verify that selecting an option in Choice of Fates applies stat modifiers."""
    state = GameState(auto_load=False)
    state.trigger_choice_of_fates()
    
    assert state.active_choice is not None
    assert state.active_choice["selected_index"] == 0
    
    # Option 0 is usually "The Quill" (Offense)
    # Move right to select Option 1 ("The Binding" - Defense)
    actions = {'move': (1, 0), 'attack': False, 'flask': False}
    state.update(0.1, actions)
    assert state.active_choice["selected_index"] == 1
    
    # Press attack to confirm
    actions = {'move': (0, 0), 'attack': True, 'flask': False}
    initial_hp_mod = state.player.stats.get("max_hp_modifier", 0)
    
    state.update(0.1, actions)
    
    assert state.active_choice is None
    # Level 1 scale should give +5 to main stat
    assert state.player.stats["max_hp_modifier"] == initial_hp_mod + 5
    assert state.player.max_hp == 100 + initial_hp_mod + 5
