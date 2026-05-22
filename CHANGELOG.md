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
### Active Session Snapshot & True Continue Hydration
- Refactored `GameState.hydrate_from_disk()` to restore the player's exact health, coordinates, and active zone from the persistent `run_state`.
- Hardened `GameState.save_stats()` to guard against overwriting session data when in a deallocated (Title Screen) state.
- Integrated synchronous save flushes (`wait=True`) for the Pause Menu "Quit" action and application exit.
- Ensured the Title Screen "Continue" button accurately reflects the presence of a resume-able run state.
- Verified restoration accuracy with comprehensive unit tests in `tests/test_hydration.py`.

### State Hydration & Scene Deallocation Lifecycle
- Implemented `GameState.deallocate()` to purge runtime memory (Player, World, enemies) when exiting to the Title Screen.
- Implemented `GameState.hydrate_from_disk()` to ensure "Continue" loads exclusively from persistent disk storage.
- Enforced a "Fresh Hub Start" policy on Continue: resets player to full health in a clean Sanctuary layout.
- Added terminal trace logs for state recovery verification.
- Updated `main.py` and `GameState.reset_to_new_game()` to support the new deallocation-safe lifecycle.

### Atomic Save-Flush & Milestone Persistence
- Implemented synchronous, atomic save flushing for critical game milestones.
- Forced immediate directory creation and disk write during New Game initialization.
- Added synchronous save hooks after warping back to the Sanctuary and closing NPC dialogue.
- Integrated diagnostic trace logs: `[DISK WRITE] Target path resolved to: {path}`.
- Ensured physical disk write compliance using `os.fsync()`.

### Persistent Save-Path Migration & XDG Compliance
- Migrated save data storage to an XDG-compliant directory (`~/.local/state/avoid_rain/`).
- Implemented environment variable check for `XDG_STATE_HOME` with fallback logic.
- Added debug logging to verify state hydration upon application startup.
- Robustly handles loading from older save formats by populating missing baseline flags.

### The Chronicler NPC & Dialogue System
- Implemented The Chronicler NPC in `ZONE_SANCTUARY` using the `GameObject` architecture.
- Built a state-driven dialogue engine that branches based on the persistent `last_run_result` flag.
- Integrated a Unified Interaction Filter to suppress combat during conversation.
- Added a dedicated dialogue UI layer with word-wrapping and speaker identification.
- Established a persistent state reset rule when initiating new runs through The Chronicle.

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
