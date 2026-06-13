
import pytest
from engine.game_state import GameState
from engine.player import PlayerStateEnum
from constants import HIT_STOP_DURATION, SCREEN_SHAKE_DURATION, STAGGER_DURATION

def test_hit_triggers_polish_effects():
    """Verify that hitting an enemy triggers hit-stop, screen shake, and stagger."""
    state = GameState(auto_load=False)
    # Ensure stats exist
    from engine.stats import StatisticsTracker
    state.stats = StatisticsTracker()
    
    # Move away from Sanctuary spawn interactables (which consume 'attack' input)
    state.player.x, state.player.y = 1000, 1000
    state.player.facing = (1, 0) # Facing right
    
    # Mock an enemy in range of the sword hitbox
    from engine.enemy import SlugEnemy
    # Right-facing hitbox is centered at px+50, width 60 (px+20 to px+80)
    enemy = SlugEnemy(state.player.x + 40, state.player.y, hp=100)
    state.enemies = [enemy]
    
    # Update 1: Start attack
    state.update(0.016, {'move': (0, 0), 'attack': True})
    assert state.player.state == PlayerStateEnum.ATTACKING
    
    # Update 2: Resolve hit detection
    state.update(0.016, {'move': (0, 0), 'attack': False})
    
    # Check effects
    assert state.hit_stop_timer > 0
    assert state.shake_timer > 0
    assert enemy.stagger_timer > 0
    assert enemy.is_staggered()

def test_hit_stop_freezes_logic():
    """Verify that while hit_stop_timer > 0, the game logic does not advance."""
    state = GameState(auto_load=False)
    state.hit_stop_timer = 0.1
    
    initial_px = state.player.x
    # Attempt to move
    state.update(0.016, {'move': (1, 0)})
    
    # Player should not have moved because hit_stop was active
    assert state.player.x == initial_px
    assert state.hit_stop_timer < 0.1

def test_player_stagger_blocks_action():
    """Verify that a staggered player cannot move or attack."""
    state = GameState(auto_load=False)
    state.player.state = PlayerStateEnum.STAGGERED
    state.player.stagger_timer = 0.5
    
    initial_x = state.player.x
    # Attempt move and attack
    state.update(0.016, {'move': (1, 0), 'attack': True})
    
    assert state.player.x == initial_x
    assert state.player.state == PlayerStateEnum.STAGGERED
    assert state.player.stagger_timer < 0.5
