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

## [ARCHIVED] Auto-Save Hooks & Main Menu Continue Restoration - May 2026

Restored the session persistence pipeline and synchronized the Title Menu with the active run state.

### 1. Mid-Run Auto-Save Integration
- **Lifecycle Injection:** Updated the Pause Menu "Quit" handler in `main.py` to trigger a synchronous `state.save_stats(wait=True)` before returning to the title screen.
- **Session Tracking:** Ensured `active_session_in_progress` is set to `True` for all non-hub saves and cleared to `False` upon return to the Sanctuary or player death.
- **State Capture:** Verified that player coordinates, HP, flasks, and inventory (weapons) are correctly serialized into the `run_state` JSON block.

### 2. Main Menu Logic & Restoration
- **Dynamic Options:** Updated the Title Screen initialization to use the `active_session_in_progress` flag for displaying the "Continue" button.
- **True Hydration:** Verified that selecting "Continue" triggers `GameState.hydrate_from_disk()`, restoring the player exactly where they left off in the hostile zone.
- **Verification:** Added `tests/test_session_persistence.py` to ensure the session lifecycle flag is correctly managed.

## [ARCHIVED] Dynamic Enemy Serialization & Level Restoration - May 2026

Implemented a robust enemy persistence system ensuring that individual entity states are preserved across save sessions.

### 1. Enemy State Capture
- **Dynamic Serialization:** Updated `GameState.save_stats()` to iterate through all active enemies and capture their `type`, `(x, y)` float coordinates, and current `hp`.
- **Loot Integration:** Ensured that dead enemies (removed from the state) are naturally excluded from the save file, preventing respawns on load.

### 2. Level Loading & Override Rule
- **Loader Refactor:** Updated `LevelLoader.parse_map()` and `World.load_from_prototype()` to accept an optional `saved_enemies` list.
- **The Override Rule:** Implemented logic to bypass default grid-symbol spawning when saved entity data is provided. This ensures that reconstruction only occurs from the persistent save state, preventing duplication.
- **Entity Reconstruction:** Added factory logic in the loader to instantiate specific subclasses (`SlugEnemy`, `BatEnemy`, `Miniboss`, etc.) with their exact saved attributes.
- **Stability:** Verified the entire hydration pipeline with existing and new automated tests.

## [ARCHIVED] Physical Save Persistence & Startup Hydration - May 2026

Migrated to a physical `save_data.json` format and ensured session persistence across application restarts.

### 1. Save File Migration
- **Standardization:** Updated `engine/stats.py` to use `save_data.json` as the default save file name, located in the project root for immediate access.
- **Atomic Serialization:** Maintained the atomic write process (temp-file swap) to prevent data corruption during disk writes.

### 2. Startup Logic & Continue Button
- **Immediate Hydration:** Refactored `main.py` to read `save_data.json` instantly upon launch, enabling accurate session detection before the title menu renders.
- **Persistent State:** Verified that the "Continue" option correctly appears after restarting the game window if a non-hub session was in progress.
- **Session Flag Alignment:** Synchronized all menu detection logic to use the `active_session_in_progress` flag for consistent behavior.

## [ARCHIVED] Dialogue Closing Intercept & Input Debounce Fix - May 2026

Resolved the "Spacebar Dialogue Lock" soft-lock and stabilized the modal state machine.

### 1. Dialog State & Input Logic
- **Priority Closure:** Updated `GameState.update()` to handle active dialogue closure at the absolute beginning of the frame.
- **Input Consumption:** Closing a dialogue now consumes the `SPACE` input for that frame, preventing it from leaking into the combat or interaction blocks.
- **Input Debouncing:** Implemented an `input_debounce_timer` that provides a 0.2s window after closing a modal during which new interactions are suppressed. This ensures that textboxes do not instantly re-open.

### 2. Engine Stability & Scope Fixes
- **Refactoring:** Completed a full consolidation of constants in `engine/game_state.py` and `rendering/renderer.py`, resolving all reported `UnboundLocalError` and `NameError` crashes.
- **Verification:** Confirmed fix with the `repro_dummy_crash.py` test suite, ensuring stable combat and UI interactions.

## [ARCHIVED] Combat Rendering Stability Restored - May 2026

Resolved a critical `NameError` that occurred when rendering loot items dropped after combat.

### 1. Renderer Correction
- **Typo Fix:** Corrected a variable reference in `Renderer.draw_loot()` where `draw_rect.width` was used instead of the correctly defined `dr.width`.
- **Stability:** Verified that `HealItem` icons (Red cross on white background) render correctly without crashing the engine.

## [ARCHIVED] Player Dash Mechanic - May 2026
- **Dash Physics:** Implemented a high-speed directional dash burst (3.0x speed) with a 0.2s duration.
- **Cooldown:** Established a 0.5s recovery window to balance combat mobility.

## [ARCHIVED] Player Block Mechanic - May 2026
- **Damage Mitigation:** Added a blocking state (`K`) providing 100% damage reduction and stagger immunity at the cost of 50% movement speed.

## [ARCHIVED] Pause Menu Controls Overlay & Tabbed Layout - May 2026
- **UI Navigation:** Built a tabbed controls interface accessible from both the Title and Pause menus.
