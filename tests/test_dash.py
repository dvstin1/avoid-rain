import pytest
from engine.player import Player, PlayerStateEnum
from engine.game_state import GameState
from constants import DASH_DURATION, DASH_COOLDOWN, DASH_SPEED_MULTIPLIER

def test_player_dash_state_transition():
    player = Player(100, 100)
    walls = []
    
    # Trigger dash
    player.update(0.016, (1, 0), walls, dash_pressed=True)
    assert player.state == PlayerStateEnum.DASHING
    assert player.dash_timer == DASH_DURATION
    assert player.dash_cooldown_timer == DASH_COOLDOWN

def test_player_dash_movement_speed():
    player = Player(100, 100)
    walls = []
    
    # Establish facing direction
    player.update(0.016, (1, 0), walls)
    
    # Trigger dash
    player.update(0.016, (0, 0), walls, dash_pressed=True)
    
    # Run one frame of dash
    dt = 0.1
    start_x = player.x
    player.update(dt, (0, 0), walls)
    
    expected_speed = player.speed * DASH_SPEED_MULTIPLIER
    expected_distance = expected_speed * dt
    
    # Due to floating point math, check if we are very close
    assert abs((player.x - start_x) - expected_distance) < 0.1

def test_player_dash_cooldown():
    player = Player(100, 100)
    walls = []
    
    # Trigger dash
    player.update(0.016, (1, 0), walls, dash_pressed=True)
    assert player.state == PlayerStateEnum.DASHING
    
    # Fast forward through dash duration
    player.update(DASH_DURATION + 0.01, (0, 0), walls)
    assert player.state == PlayerStateEnum.IDLE
    
    # Attempt to dash again immediately (should fail due to cooldown)
    player.update(0.016, (1, 0), walls, dash_pressed=True)
    assert player.state != PlayerStateEnum.DASHING
    
    # Fast forward through cooldown
    player.update(DASH_COOLDOWN, (0, 0), walls)
    
    # Attempt to dash again (should succeed)
    player.update(0.016, (1, 0), walls, dash_pressed=True)
    assert player.state == PlayerStateEnum.DASHING
