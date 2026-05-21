"""
Unit tests for player engine logic.
"""
import math
from engine.player import Player

def test_player_movement_orthogonal():
    """Test that player moves correctly in cardinal directions."""
    p = Player(100, 100)
    p.speed = 100
    # Move right for 1 second, no walls
    p.update(1.0, (1, 0), [], False)
    assert p.x == 200
    assert p.y == 100

def test_player_movement_normalized():
    """Test that diagonal movement is normalized (not faster)."""
    p = Player(100, 100)
    p.speed = 100
    # Move diagonally (1, 1) for 1 second, no walls
    p.update(1.0, (1, 1), [], False)
    
    # Expected distance should be 100, not 141.4
    dist = math.sqrt((p.x - 100)**2 + (p.y - 100)**2)
    assert math.isclose(dist, 100.0, rel_tol=1e-5)

def test_player_boundary_clamping():
    """Test that player cannot move off-screen."""
    from constants import SCREEN_WIDTH, PLAYER_WIDTH
    p = Player(SCREEN_WIDTH - PLAYER_WIDTH, 100)
    p.speed = 100
    # Try to move right off-screen, no walls
    p.update(1.0, (1, 0), [], False)
    assert p.x == SCREEN_WIDTH - PLAYER_WIDTH

def test_player_wall_collision():
    """Test that player is blocked by walls."""
    p = Player(100, 100)
    p.speed = 100
    # Wall is at (120, 100) with size 40x40
    # Player starts at (100, 100) and moves right.
    # With dt=0.1, player would be at x=110.
    # Player right=150, Wall left=120. Overlap=30.
    # Player center=130, Wall center=140. Pushes left.
    p.update(0.1, (1, 0), [(120, 100, 40, 40)], False)
    
    # Player should be pushed back to x=80
    assert p.x == 80
