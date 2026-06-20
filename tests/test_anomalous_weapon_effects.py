"""
Unit tests for anomalous weapon modifiers (bleed, regen, max HP boost, negation).
"""
from engine.player import Player, PlayerStateEnum
from engine.enemy import SlugEnemy
from engine.game_state import GameState

class MockWorld:
    """Mock level world for unit tests."""
    def __init__(self):
        self.player_start = (0, 0)
        self.grid = [[0]]
        self.interactables = []
        self.enemies = []

    def get_nearby_interactables(self, rect):
        """Mock return interactables."""
        _ = rect
        return self.interactables

    def get_nearby_walls(self, rect):
        """Mock return walls."""
        _ = rect
        return []

def test_anomalous_hp_regen():
    """Verify that slow HP regen regenerates the player's HP over time up to max."""
    player = Player(0, 0)
    player.weapons = [{"name": "Regen Quill", "damage": 10, "modifiers": {"slow_hp_regen": 10.0}}]
    player.active_weapon_idx = 0
    player.hp = 50.0

    # Trigger update with dt = 1.0 second
    player.update(1.0, (0, 0), [], {})
    assert player.hp == 60.0

    # Ensure it doesn't exceed max HP
    player.hp = player.max_hp - 5.0
    player.update(1.0, (0, 0), [], {})
    assert player.hp == player.max_hp

def test_anomalous_max_hp_boost():
    """Verify that max HP boost weapon dynamically increases max HP regardless of slot."""
    player = Player(0, 0)
    player.weapons = [
        {"name": "Standard Quill", "damage": 10},
        {"name": "Stout Quill", "damage": 10, "modifiers": {"max_hp_boost": 20.0}}
    ]
    # Max HP boost is active even when Standard Quill is selected
    player.active_weapon_idx = 0
    assert player.max_hp == 120.0

    # Swap to Stout Quill (Max HP boost)
    player.active_weapon_idx = 1
    assert player.max_hp == 120.0

    # Heal to new max HP
    player.hp = 120.0

    # Remove Stout Quill from inventory, max HP should go back to 100.0
    player.weapons = [{"name": "Standard Quill", "damage": 10}]
    player.active_weapon_idx = 0
    assert player.max_hp == 100.0
    player.update(0.1, (0, 0), [], {})  # update ticks clamping
    assert player.hp == 100.0

def test_anomalous_damage_negation():
    """Verify that taking damage with negation weapon triggers temporary negation for next hit."""
    player = Player(0, 0)
    player.weapons = [{"name": "Negation Quill", "damage": 10, "modifiers": {"damage_negation_on_hit": 5.0}}]
    player.active_weapon_idx = 0

    # Set HP to 90.0 so pristine concentration passive (at >95% HP) is not active
    player.hp = 90.0

    # First hit: takes full damage (e.g. 15), but triggers negation. Bypasses stagger to avoid stagger i-frames.
    player.take_damage(15.0, bypass_stagger=True)
    assert player.hp == 75.0
    assert player.negation_timer == 3.0
    assert player.negation_amount == 5.0

    # Second hit: negation reduces damage by 5.0 (takes 10 instead of 15)
    player.take_damage(15.0, bypass_stagger=True)
    assert player.hp == 65.0

    # Tick timer down, negation should expire
    player.update(3.1, (0, 0), [], {})
    assert player.negation_timer == 0.0
    assert player.negation_amount == 0.0

    # Third hit: takes full damage again
    player.take_damage(15.0, bypass_stagger=True)
    assert player.hp == 50.0

def test_anomalous_enemy_bleed():
    """Verify that attacking an enemy with a bleed weapon inflicts ticking bleed damage."""
    state = GameState(auto_load=False)
    state.world = MockWorld()

    # Place player at (0, 0) and configure player weapon with bleed
    state.player.x, state.player.y = 0.0, 0.0
    state.player.facing = (1, 0)
    state.player.weapons = [{"name": "Bleed Quill", "damage": 10, "modifiers": {"bleed": 5.0}}]
    state.player.active_weapon_idx = 0

    # Use real PlayerStateEnum to set ATTACKING state so hit detection runs
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.attack_timer = 0.5

    # Spawn enemy in front of player (overlapping with sword right attack hitbox)
    enemy = SlugEnemy(55.0, 10.0)
    enemy.hp = 100.0
    state.enemies.append(enemy)

    # Trigger game state update to check and register attack hit
    state.update(0.1, {"attack": True})

    # Enemy should have bleed status applied
    assert enemy.bleed_timer == 5.0
    assert enemy.bleed_damage == 5.0

    # Tick update by 1.0 second, enemy should take bleed tick
    prev_hp = enemy.hp
    enemy.update(1.0, state)
    assert enemy.hp == prev_hp - 5.0

def test_inactive_weapon_modifiers():
    """Verify that passive weapon modifiers apply even when they are in an inactive slot."""
    player = Player(0, 0)
    player.weapons = [
        {"name": "Standard Quill", "damage": 10},
        {
            "name": "Stout Regen Quill",
            "damage": 10,
            "modifiers": {"max_hp_boost": 20.0, "slow_hp_regen": 10.0}
        }
    ]
    # Standard Quill is active (slot 0)
    player.active_weapon_idx = 0

    # Max HP boost should still be active
    assert player.max_hp == 120.0

    # HP regen should still be active
    player.hp = 50.0
    player.update(1.0, (0, 0), [], {})
    assert player.hp == 60.0
