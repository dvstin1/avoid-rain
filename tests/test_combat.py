"""
Unit tests for combat and hitbox logic.
"""
from engine.combat import get_sword_hitbox
from constants import SWORD_WIDTH, SWORD_HEIGHT, SWORD_OFFSET

def test_sword_hitbox_right():
    """Test hitbox when facing right."""
    center = (100, 100)
    facing = (1, 0)
    hitbox = get_sword_hitbox(center, facing)
    # Expected: x = 100 + 30 = 130, y = 100 - 10 = 90, w = 60, h = 20
    assert hitbox == (130, 90, 60, 20)

def test_sword_hitbox_left():
    """Test hitbox when facing left."""
    center = (100, 100)
    facing = (-1, 0)
    hitbox = get_sword_hitbox(center, facing)
    # Expected: x = 100 - 30 - 60 = 10, y = 90, w = 60, h = 20
    assert hitbox == (10, 90, 60, 20)

def test_sword_hitbox_down():
    """Test hitbox when facing down."""
    center = (100, 100)
    facing = (0, 1)
    hitbox = get_sword_hitbox(center, facing)
    # Expected: x = 100 - 10 = 90, y = 100 + 30 = 130, w = 20, h = 60
    assert hitbox == (90, 130, 20, 60)

def test_sword_hitbox_up():
    """Test hitbox when facing up."""
    center = (100, 100)
    facing = (0, -1)
    hitbox = get_sword_hitbox(center, facing)
    # Expected: x = 90, y = 100 - 30 - 60 = 10, w = 20, h = 60
    assert hitbox == (90, 10, 20, 60)
