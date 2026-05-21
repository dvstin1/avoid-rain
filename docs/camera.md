Camera (engine/camera.py)

Purpose:
Provide a stateful, frame-rate independent viewport controller that centers on the player and clamps to world bounds. Supports instantaneous centering and smooth following via an exponential damping (configurable via constants.CAMERA_LERP_SPEED).

Why it exists:
Keeps rendering decoupled from camera math, avoids per-frame allocation of camera objects, and enables configurable smoothing without touching rendering or player logic.

Notes:
- Camera.get_target_offset(player_center) returns the unclamped target.
- Camera.update(player_center, dt) applies smoothing.
- Camera.instant_center(...) snaps immediately.
