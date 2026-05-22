# Changelog

## [2026-05-21] - Documentation Cleanup & Consolidation
- Audited `AGENTS.md` and `docs/` to remove contradictions.
- Moved permanent technical architectures into `docs/architecture.md`.
- Archived completed features into this Changelog.
- Streamlined `AGENTS.md` to focus on core rules and active tasks.

### Initial Foundation (Sanctuary)
- Established core engine loop with frame-rate independence (dt-scaling).
- Implemented Title Screen with basic menu functionality.
- Created the Sanctuary (Hub World) as a playable sandbox.
- Implemented Player Controller with WASD movement and normalized vectors.
- Established Constants system for centralized configuration.
- Integrated training dummy entities for combat testing.

## [Recently Completed]
### Grid-Based Level Parser
- Implemented a clean, data-driven map parsing engine that reads 2D text matrix strings.
- Mapped symbols (`#`, `T`, `B`, `.`) to basic structural elements.
- Integrated `LevelLoader` with the physics engine's collision detection.

### Destructible Prop Layer & Loot System
- Implemented destruction state engine for placeholder Barrel (`B`) props.
- Integrated baseline `LootManager` probability engine for Tier 4 drops.
- Added support for breakable entity clean-up and brief fading animations.

### Map Data Layout Population
- Populated `ROOM_PROTOTYPES` with distinct structural layouts for the Sanctuary and Chapter 1.
- Established structural test layouts to verify physical distribution of objects.

### Lotus Layout Instantiation
- Implemented the "Lotus Pod" blueprint in `map_data.py`.
- Established correct spawn orientations and boundary logic for the macro Lotus grid.

### Level Hook & Main Loop Verification
- Audited and verified file import paths for level layouts.
- Explicitly bound the `World` initialization to the new Lotus topography grid.
- Added debug logging for map initialization.

### Chapter 1 Realignment & Arena Expansion
- Realigned the Chronicle warp trigger to point directly to the `chapter1` production layout.
- Expanded the arena with clusters of breakable barrels and enemy spawn points.
