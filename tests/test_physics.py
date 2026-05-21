"""
Unit tests for pure physics and collision logic.
"""
from engine.physics import check_aabb_collision, resolve_wall_collision

def test_aabb_overlap():
    """Test that overlapping rectangles are detected."""
    rect1 = (0, 0, 50, 50)
    rect2 = (25, 25, 50, 50)
    assert check_aabb_collision(rect1, rect2) is True

def test_aabb_no_overlap():
    """Test that non-overlapping rectangles are detected."""
    rect1 = (0, 0, 50, 50)
    rect2 = (100, 100, 50, 50)
    assert check_aabb_collision(rect1, rect2) is False

def test_resolve_horizontal_collision():
    """Test that horizontal collision pushes player back correctly."""
    player = (130, 100, 40, 40) # Overlapping wall by 10px on right
    wall = (160, 100, 40, 40)
    # player_right = 170, wall_left = 160. Overlap = 10.
    new_x, new_y = resolve_wall_collision(player, [wall])
    assert new_x == 120
    assert new_y == 100

def test_resolve_vertical_collision():
    """Test that vertical collision pushes player back correctly."""
    player = (100, 130, 40, 40) # Overlapping wall by 10px on bottom
    wall = (100, 160, 40, 40)
    # player_bottom = 170, wall_top = 160. Overlap = 10.
    new_x, new_y = resolve_wall_collision(player, [wall])
    assert new_x == 100
    assert new_y == 120
