# World Expansion: The Macro-Grid Topology

## Purpose
To facilitate a sustained 10-minute exploration experience before the environmental shift (The Devouring Storm) triggers, the world is constructed as a massive macro-layout rather than isolated rooms.

## Implementation: The Modular Component Matrix
The world utilizes a $120 \times 120$ tile minimum grid, divided into:
- **Core Framework:** Immutable safe walkways.
- **Modular Holes:** $20 \times 20$ tile cavities populated with specific layouts (e.g., `chapter1`).

## Why it exists
- **Sustained Exploration:** Allows the player to traverse a large, connected space during Act I.
- **State Management:** Enables the "Closing Collapse" (Act II) to operate on a single large coordinate space, shrinking the safe zone toward a center point.
- **Prototyping Stability:** During Phase 1, modular holes are populated with copies of established layouts to ensure reliable testing.

## Technical Notes
- **Constants:** `WORLD_WIDTH` and `WORLD_HEIGHT` (or equivalent extra tile constants) should define the $120 \times 120$ scale.
- **Clamping:** The player remains clamped to the global world bounds; the camera and renderer handle scrolling across the macro-grid.
- **Reference:** See `docs/architecture.md` Section 9 for full topology details.
