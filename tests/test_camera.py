"""Unit tests for the Camera math (viewport centering and clamping)."""

from engine.camera import Camera


def test_camera_center_and_clamp_middle():
    cam = Camera(800, 600, 1600, 1200)
    # Player in the exact center of the world should produce centered target offsets
    target = cam.get_target_offset((800, 600))
    assert (int(target[0]), int(target[1])) == (400, 300)


def test_camera_clamps_to_left_and_top_edges():
    cam = Camera(800, 600, 1600, 1200)
    # Near world origin should clamp to (0, 0)
    target = cam.get_target_offset((100, 100))
    assert (int(target[0]), int(target[1])) == (0, 0)


def test_camera_clamps_to_right_and_bottom_edges():
    cam = Camera(800, 600, 1600, 1200)
    # Near world bottom-right should clamp to max offsets
    target = cam.get_target_offset((1550, 1150))
    assert (int(target[0]), int(target[1])) == (800, 600)


def test_camera_smoothing_moves_toward_target():
    cam = Camera(800, 600, 1600, 1200, lerp_speed=2.0)
    cam.instant_center((400, 300))
    # target moves far to the right-bottom
    target = cam.get_target_offset((1200, 900))
    # update with small dt should move offset toward target but not snap
    cam.update((1200, 900), 0.1)
    ox, oy = cam.get_offset()
    assert ox != int(target[0]) or oy != int(target[1])
    # Record distance after small dt
    dist1 = abs(ox - int(target[0])) + abs(oy - int(target[1]))
    # A longer dt should reduce the error
    cam.update((1200, 900), 1.0)
    ox2, oy2 = cam.get_offset()
    dist2 = abs(ox2 - int(target[0])) + abs(oy2 - int(target[1]))
    assert dist2 < dist1
    # After more time the camera should be close to the target
    cam.update((1200, 900), 3.0)
    ox3, oy3 = cam.get_offset()
    assert abs(ox3 - int(target[0])) <= 5
    assert abs(oy3 - int(target[1])) <= 5
