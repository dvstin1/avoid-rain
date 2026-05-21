# Physics & Collision Rules

To ensure consistent gameplay and prevent out-of-bounds errors, the following physics rules must be enforced by the `engine/`.

## 1. Screen Boundary Clamping
Even in the absence of wall tiles or modular obstacles, the Player object must be strictly contained within the active screen dimensions.

- **Rule:** After calculating the new position based on velocity and `dt`, the engine must clamp the `x` and `y` coordinates.
- **Math:**
    - `pos.x = max(0, min(pos.x, SCREEN_WIDTH - PLAYER_WIDTH))`
    - `pos.y = max(0, min(pos.y, SCREEN_HEIGHT - PLAYER_HEIGHT))`
- **Implementation Note:** Clamping should occur *after* wall collision resolution but *before* the state is finalized for rendering. This prevents the player from "shivering" at the edge when moving diagonally against a boundary.

## 2. Collision Order of Operations
1. **Apply Velocity:** `temp_pos = pos + vel * dt`
2. **Wall Collision:** Resolve AABB intersections with static grid.
3. **Boundary Clamp:** Force `temp_pos` into screen bounds.
4. **Finalize:** `pos = temp_pos`
