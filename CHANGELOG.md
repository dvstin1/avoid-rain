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
### Minimap Entity Markers
- Implemented markers for enemies and loot on the minimap.
- Added `MINIMAP_ENEMY_COLOR` and `MINIMAP_LOOT_COLOR` constants.
- Updated `Renderer.draw_minimap` to render small markers for entities within the minimap viewport.
- Added unit tests to verify markers appear correctly on the minimap.

### Arena Sprawl Expansion, Multi-Tile Props, & 2x2 Miniboss
- **Corridor Sprawl:** Expanded the `chapter1` map layout to include a starting room, a narrow corridor, and a grand final chamber.
- **Bench Refactor:** Updated `LevelLoader` to support vertical 1x2 multi-tile Benches (`S`).
- **Miniboss Entity:** Implemented a 2x2 elite enemy with pursuit behavior and an expanded health pool.
- **Entity Population:** Integrated the Miniboss into the `chapter1` layout.

### Bat Visibility Patch & Test Area Asset Population
- **Visibility Fix:** Added missing `COLOR_PURPLE` constant to `constants.py`, resolving a rendering pipeline `ImportError`.
- **Exhibition Layout:** Rearranged the `chapter1` map to cluster a Rock, Bench, Barrel, Tree, and Bat enemy directly in front of the player's spawn point for immediate testing.
- **Bat Rendering:** Verified purple primitive rendering with wing indicators for the `BatEnemy`.

### New Game Confirmation Prompt Rendering
- Fixed the rendering sequence for the New Game "Y/N" confirmation overlay.
- Ensured text assets are drawn as the absolute top layer on the viewport buffer.
- Anchored confirmation text to the viewport center for dynamic scaling.
- Verified that 'N' reverts to the Title Menu and 'Y' correctly resets the game profile and state.

### Fast-Pursuit Enemy & Environmental Objects
- **BatEnemy:** A new fast-pursuit enemy type with erratic sine-wave movement patterns.
- **Environmental Objects:** Added Benches ('S') and Rocks ('K') as solid obstacles to enrich map topography.
- **Engine Refactor (Enemy Cleanup):** Centralized dead enemy removal in `GameState.update`, ensuring cleanup and loot spawning occur regardless of the player's attack state.
- **Enemy Population Reset Lifecycle Fix:** Transitioned to a fully data-driven re-population system using map symbols ('Z', 'A'). Enemies now correctly reset to full health and original positions upon map entry or run restart, resolving the issue of persistent death states.
- **Visuals:** Added custom rendering for Bats (purple with wings), Benches (dark wood), and Rocks (grey with highlights).

### Compass Indicator for Minimap
- Implemented the "Compass Indicator" feature to show markers for off-screen objectives at the minimap edge.
- Added an `objectives` list to `GameState` for world-space coordinates.
- Developed projection logic in `Renderer.draw_minimap` to handle edge-clamping and vector intersection.
- Added comprehensive unit tests in `tests/test_minimap.py`.

### Wellspring Visual Mapping & Expanded UI Overhaul
- Implemented animated water primitive for the Wellspring fountain using shifting horizontal cyan lines.
- Refactored the dialogue engine to support a `display_mode="EXPANDED"` flag for large, centralized modals.
- Optimized the Wellspring interaction to display high-density player statistics using the expanded UI mode.
- Ensured player movement and combat are suppressed during expanded UI states.

### Active Session Snapshot & True Continue Hydration
- Refactored `GameState.hydrate_from_disk()` to restore the player's exact health, coordinates, and active zone from the persistent `run_state`.
- Hardened `GameState.save_stats()` to guard against overwriting session data when in a deallocated (Title Screen) state.
- Integrated synchronous save flushes (`wait=True`) for the Pause Menu "Quit" action and application exit.
- Ensured the Title Screen "Continue" button accurately reflects the presence of a resume-able run state.
- Verified restoration accuracy with comprehensive unit tests in `tests/test_hydration.py`.

### [ARCHIVED] Dual-Weapon Inventory Management & Full-Cradle Manifestation Loop - May 2026
- **Inventory Expansion:** Refactored the player to hold exactly two weapons with a swap mechanic.
- **Full-Cradle Rule:** Minibosses now drop randomized "Anomalous" weapons only when both player slots are full.
- **Loot Engine:** Integrated ground-item spawning for discarded weapons during swaps.

### [ARCHIVED] HUD Weapon Swap Button, Sanctuary Purge, & Triple Elite Deployment - May 2026
- **HUD Upgrades:** Implemented a visible dual-slot weapon HUD with Slot A/B labels, tier coloring, and a clickable [SWAP] button.
- **Sanctuary Reset:** Enforced automatic item/health purge upon hub entry: resets to "Initial Quill" and max health/flasks.
- **Triple Elite Deployment:** Added `MinibossM2` and `MinibossM3` symbols to map data for drop testing.
- **Visible Drops:** Rendered weapon pickups as glowing book icons with interactive prompts.

### [ARCHIVED] Input Unification & Interaction Handler Fix - May 2026
- **Key Unification:** Consolidated all interactions (NPCs, Items, Warps) under the `SPACE` key.
- **Cleanup:** Removed all `E` key logic and updated all UI prompts to consistently display `SPACE`.
- **UI Alignment:** Updated the controls overlay to reflect the streamlined input layout.

### [ARCHIVED] Level Design & Lifecycle Sync - May 2026
- **Elite AI (Bleeding Scribe M2):** Implemented fast, erratic pursuit logic using sine-wave velocity oscillation.
- **Elite AI (Forgotten Binder M3):** Implemented teleportation escape logic triggered by player proximity.
- **Map Refinement:** Separated M2 and M3 into independent large chambers within `world_map1.json`.
- **Session Lifecycle:** Enforced `active_session_in_progress` boundaries; non-hub states flush to disk, while hub returns clear the session.
- **Verification:** Added `tests/test_architectural_sync.py` to ensure AI and lifecycle stability.

## [ARCHIVED] Emergency Logic Reordering & Scope Crash Resolution - May 2026
- **Interaction Priority:** Moved interaction logic to the top of the `update()` loop to prioritize world transitions.
- **Scope Fix:** Consolidated imports in `engine/game_state.py` and `rendering/renderer.py` to resolve `COLOR_WHITE` shadowing errors.

## [ARCHIVED] Lore Fragment Documentation & Scriptorium Placement - May 2026
- **Lore Archive:** Created `docs/lore_fragments.md` and registered the "Half-Cleft Manuscript".
- **Map Integration:** Placed a Lore Lectern ('L') at the start of `world_map1.json`.
- **Interaction:** Verified Lectern triggers UI text with Spacebar interaction.

## [ARCHIVED] Player Dash Mechanic - May 2026
- **Dash Physics:** Implemented a high-speed directional dash burst (3.0x speed) with a 0.2s duration.
- **Cooldown:** Established a 0.5s recovery window to balance combat mobility.

## [ARCHIVED] Player Block Mechanic - May 2026
- **Damage Mitigation:** Added a blocking state (`K`) providing 100% damage reduction and stagger immunity at the cost of 50% movement speed.

## [ARCHIVED] Pause Menu Controls Overlay & Tabbed Layout - May 2026
- **UI Navigation:** Built a tabbed controls interface accessible from both the Title and Pause menus.
