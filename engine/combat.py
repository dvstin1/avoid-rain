"""
Handles combat logic, hitboxes, and damage resolution.
"""
from constants import SWORD_WIDTH, SWORD_HEIGHT, SWORD_OFFSET

def get_sword_hitbox(player_center, facing):
    """
    Calculates the sword hitbox based on player position and facing direction.
    Returns (x, y, w, h)
    """
    cx, cy = player_center
    fx, fy = facing

    # Calculate orientation
    if abs(fx) > abs(fy): # Horizontal attack
        w, h = SWORD_WIDTH, SWORD_HEIGHT
        if fx > 0: # Right
            x = cx + SWORD_OFFSET
            y = cy - h / 2
        else: # Left
            x = cx - SWORD_OFFSET - w
            y = cy - h / 2
    else: # Vertical attack
        w, h = SWORD_HEIGHT, SWORD_WIDTH
        if fy > 0: # Down
            x = cx - w / 2
            y = cy + SWORD_OFFSET
        else: # Up
            x = cx - w / 2
            y = cy - SWORD_OFFSET - h

    return (x, y, w, h)
