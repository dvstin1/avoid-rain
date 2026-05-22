Minimap (rendering/renderer.py)

Purpose:
Provide a small in-game minimap showing a viewport around the player rather than the entire world. This demonstrates panning and gives a small spatial overview without revealing everything.

Configuration:
- MINIMAP_WIDTH, MINIMAP_HEIGHT, MINIMAP_PADDING: pixel size and offset in the UI
- MINIMAP_VIEWPORT_FRAC: fraction (0..1) of the world to show in the minimap viewport; less than 1 shows a window around the player and enables panning behavior
- MINIMAP_WALL_COLOR, MINIMAP_PLAYER_COLOR: marker colors

Behavior:
- The minimap renders in the top-left corner.
- It computes a world-space viewport centered on the player's center, clamped to the world bounds.
- Only walls inside the viewport are drawn; the player is shown relative to the viewport center to indicate position and movement.
- Useful for early prototyping; future work could add toggles, minimap markers for entities, or a zoom control.

Implementation notes:
- Low-coupled: functionality lives in Renderer.draw_minimap and relies only on state.player and state.world for read-only data.
- The minimap is purely visual; game logic is unaffected.

References:
- rendering/renderer.py: draw_minimap implementation
- constants.py: MINIMAP_* configuration
