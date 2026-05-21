"""Simple camera helper to compute viewport offsets based on player position.

The camera centers on the player when possible, and clamps so the view never
shows pixels outside the world bounds.
"""
from __future__ import annotations

from typing import Tuple


class Camera:
    """Stateful camera with optional smoothing/lerp behaviour.

    Use update(player_center, dt) each frame to move the camera's internal
    offset toward the desired target. Call get_offset() to retrieve the
    current integer pixel offset for rendering.
    """

    def __init__(self, screen_w: int, screen_h: int, world_w: int, world_h: int, lerp_speed: float = 8.0) -> None:
        self.screen_w = int(screen_w)
        self.screen_h = int(screen_h)
        self.world_w = int(world_w)
        self.world_h = int(world_h)
        self.lerp_speed = float(lerp_speed)

        # Current offset (top-left world pixel drawn at screen 0,0)
        self.offset_x = 0.0
        self.offset_y = 0.0

    def get_target_offset(self, player_center: Tuple[float, float]) -> Tuple[float, float]:
        cx, cy = player_center
        target_x = cx - self.screen_w / 2
        target_y = cy - self.screen_h / 2

        # Clamp so we don't show outside the world
        max_offset_x = max(0, self.world_w - self.screen_w)
        max_offset_y = max(0, self.world_h - self.screen_h)

        target_x = max(0, min(target_x, max_offset_x))
        target_y = max(0, min(target_y, max_offset_y))

        return target_x, target_y

    def update(self, player_center: Tuple[float, float], dt: float) -> None:
        """Move the internal offset toward the target using exponential/lerp.

        Uses simple linear interpolation factor derived from lerp_speed*dt but
        clamped to [0,1] to avoid overshooting on large dt.
        """
        target_x, target_y = self.get_target_offset(player_center)
        t = max(0.0, min(1.0, self.lerp_speed * dt))
        # Move fraction t toward target
        self.offset_x += (target_x - self.offset_x) * t
        self.offset_y += (target_y - self.offset_y) * t

    def instant_center(self, player_center: Tuple[float, float]) -> None:
        """Immediately snap the camera to center on player (no smoothing)."""
        tx, ty = self.get_target_offset(player_center)
        self.offset_x = tx
        self.offset_y = ty

    def get_offset(self) -> Tuple[int, int]:
        return int(self.offset_x), int(self.offset_y)
