
import pytest
from engine.game_state import GameState
from engine.player import PlayerStateEnum
from constants import HIT_STOP_DURATION, SCREEN_SHAKE_DURATION, STAGGER_DURATION

def test_hit_triggers_polish_effects():
    """Verify that hitting an enemy triggers hit-stop, screen shake, and stagger."""
    state = GameState()
    # Mock an enemy in range of the sword hitbox
    # Player is at spawn, center is (px+20, py+20)
    # Right-facing hitbox starts at center.x + 30 = px + 50
    from engine.enemy import SlugEnemy
    enemy = SlugEnemy(state.player.x + 40, state.player.y, hp=100)
    state.enemies = [enemy]
    
    # Force player facing
    state.player.facing = (1, 0) # Facing right
    
    # Update state - this should trigger an attack start and then hit detection
    # First update to start attack
    state.update(0.016, {'move': (0, 0), 'attack': True})
    
    # Check effects
    assert state.hit_stop_timer > 0
    assert state.shake_timer > 0
    assert enemy.stagger_timer > 0
    assert enemy.is_staggered()

def test_hit_stop_freezes_logic():
    """Verify that while hit_stop_timer > 0, the game logic does not advance."""
    state = GameState()
    state.hit_stop_timer = 0.1
    
    initial_px = state.player.x
    # Attempt to move
    state.update(0.016, {'move': (1, 0)})
    
    # Player should not have moved because hit_stop was active
    assert state.player.x == initial_px
    assert state.hit_stop_timer < 0.1

def test_player_stagger_blocks_action():
    """Verify that a staggered player cannot move or attack."""
    state = GameState()
    state.player.state = PlayerStateEnum.STAGGERED
    state.player.stagger_timer = 0.5
    
    initial_x = state.player.x
    # Attempt move and attack
    state.update(0.016, {'move': (1, 0), 'attack': True})
    
    assert state.player.x == initial_x
    assert state.player.state == PlayerStateEnum.STAGGERED
    assert state.player.stagger_timer < 0.5
