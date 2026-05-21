"""Simple camera helper to compute viewport offsets based on player position.

The camera centers on the player when possible, and clamps so the view never
shows pixels outside the world bounds.
"""
from __future__ import annotations

from typing import Tuple


class Camera:
    """Compute a camera offset for rendering a portion of a larger world.

    screen_w/h and world_w/h are in pixels. get_offset takes the player's
    world-space center (x, y) and returns the top-left world-space pixel that
    should be drawn at screen (0, 0).
    """

    def __init__(self, screen_w: int, screen_h: int, world_w: int, world_h: int) -> None:
        self.screen_w = int(screen_w)
        self.screen_h = int(screen_h)
        self.world_w = int(world_w)
        self.world_h = int(world_h)

    def get_offset(self, player_center: Tuple[float, float]) -> Tuple[int, int]:
        cx, cy = player_center
        # Desired top-left such that player is centered on screen
        offset_x = cx - self.screen_w / 2
        offset_y = cy - self.screen_h / 2

        # Clamp so we don't show outside the world
        max_offset_x = max(0, self.world_w - self.screen_w)
        max_offset_y = max(0, self.world_h - self.screen_h)

        offset_x = max(0, min(offset_x, max_offset_x))
        offset_y = max(0, min(offset_y, max_offset_y))

        return int(offset_x), int(offset_y)
