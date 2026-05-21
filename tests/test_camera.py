"""Unit tests for the Camera math (viewport centering and clamping)."""

from engine.camera import Camera


def test_camera_center_and_clamp_middle():
    cam = Camera(800, 600, 1600, 1200)
    # Player in the exact center of the world should produce centered offsets
    offset = cam.get_offset((800, 600))
    assert offset == (400, 300)


def test_camera_clamps_to_left_and_top_edges():
    cam = Camera(800, 600, 1600, 1200)
    # Near world origin should clamp to (0, 0)
    offset = cam.get_offset((100, 100))
    assert offset == (0, 0)


def test_camera_clamps_to_right_and_bottom_edges():
    cam = Camera(800, 600, 1600, 1200)
    # Near world bottom-right should clamp to max offsets
    offset = cam.get_offset((1550, 1150))
    assert offset == (800, 600)
