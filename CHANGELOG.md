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
### Git Asset Recovery & Global Movement Border Correction
- **Asset Recovery:** Restored the original hand-crafted versions of `maps/forest.json` and `maps/ruins.json` from git history, preserving miniboss placements and custom layouts.
- **Global Movement Fix:** Updated `constants.py` and `engine/player.py` to enforce boundary clamping strictly against the global 440x440 world dimensions.
- **Seamless Traversal:** Eliminated local module boundary restrictions, allowing the player to move freely between stitched map modules without collision hitches.

### Grid Logic Refinement & Enriched Asset Population
- **Grid Assembly Correction:** Refactored `engine/world_generator.py` to utilize an 11x11 unit-base grid. Sockets are now strictly defined as 120x120 rooms (when row/col indices align) and 40x40 corridor/junction units for all other slots, eliminating incorrect rectangular shapes.
- **Asset Cleanup:** Purged the redundant and invalid `maps/night_boss.json` file to maintain a clean and reliable asset pool.
- **Interactive Asset Enrichment:**
    - **The Colophon:** Injected a player spawn token (`P`) and decorative bookcases (`h`) into the starting room.
    - **Smallcave:** Populated corridor modules with test Bats (`A`) and Barrels (`B`) to verify entity instantiation across the macro-world.
- **Structural Verification:** Confirmed the 440x440 symmetric assembly logic via terminal debug traces.

### World Generator Refinement & Robust Anomaly Logic
- **Hard Size Filtering:** Implemented a strict validation pass in `WorldGenerator` that automatically rejects any map file not matching exactly 120x120 or 40x40, purging the pool of legacy 7x7 assets.
- **Graceful Anomaly Fallback:** Fixed the 10% "Special Edition" roll logic to detect empty anomaly pools and automatically fallback to standard map selections, preventing crashes and dimension mismatch warnings.
- **Open-Floor Initialization:** Switched the 440x440 macro-world canvas to initialize using open floor space (" ") for immediate playability and improved exploration flow.

### Asset Expansion & Generation Pipeline Finalization
- **Open-Floor Canvas:** Updated `WorldGenerator` to initialize the 440x440 macro-world using open floor space (" ") instead of solid walls, ensuring a more open exploration experience.
- **Strict Size Mapping:** Refined the generator to strictly map 120x120 assets to large sockets and 40x40 assets to corridors/junctions.
- **Passable Asset Pool:** Generated new placeholder maps for `Forest`, `Ruins`, `The Colophon`, and `Night Boss Arena` with guaranteed traversable boundaries.
- **Night Boss Implementation:** Registered the `NightBoss` elite enemy class with high HP and unique identification, and integrated it into the procedural generation via the `night_boss_arena.json` module.

### Emergency Fix: World Generator Regression & Sanctuary Restoration
- **Sanctuary Restoration:** Restored `maps/sanctuary.json` as an independent hub world, removing it from the macro-generation pool.
- **Symmetric Layout Correction:** Fixed the world generator to implement the true **120-40-120-40-120** symmetric grid (440x440).
- **The Colophon (New Spawn Room):** Created a dedicated 40x40 starting room at `maps/the_colophon.json`.
- **Logic Refinement:** Updated the allocation pipeline to place the player in a random outer corridor and the boss in an inner junction.

### Data-Driven Macro-World Layout Generator & Theme Integration
- **The Colophon (Spawn):** Renamed the `sanctuary` area to "The Colophon" for theme integration and updated `docs/modular_system.md`.
- **Macro-World Framework:** Built `engine/world_generator.py` to support a symmetric 440x440 layout matrix (11x11 grid of 40x40 sockets).
- **Rule-Based Allocation:** Implemented a generation pipeline that randomly selects one outer socket for the spawn area and one inner socket (within the "Crown Ring") for the night boss.
- **Random Backfill:** Automated the backfilling of all remaining 119 sockets with randomized selections from the 40x40 asset pool (`Forest`, `Ruins`, `Cave`).
- **Generation:** Successfully generated a sample world layout at `maps/generated_world.json`.

### Refining Editor UI and Input Handling
- **Help Dialog Modal:** Replaced the sidebar help text with a dedicated modal (H key) and added a dimming overlay when modals are active.
- **Input Bleed-Through Fix:** Implemented a robust mouse-release blocker to prevent map clicks from occurring immediately after closing a modal dialog.
- **Sidebar Cleanup:** Reorganized sidebar info and improved layout consistency for high-resolution editing.

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
- **Lifecycle Injection:** Updated the Pause Menu "Quit" handler in `main.py` to trigger a synchronous `state.save_stats(wait=True)` before returning to the title screen.
- **Session Tracking:** Ensured `active_session_in_progress` is set to `True` for all non-hub saves and cleared to `False` upon return to the Sanctuary or player death.
- **State Capture:** Verified that player coordinates, HP, flasks, and inventory (weapons) are correctly serialized into the `run_state` JSON block.

## [ARCHIVED] Hard Persistent Save File Serialization & Startup Boot Hook - May 2026
- **Physical Persistence:** Updated the session saving module to write directly to `save_data.json` in the project root.
- **Data Integrity:** Implemented atomic write operations (using temporary files and `os.replace`) to prevent data corruption during unexpected exits.
- **Payload Coverage:** Ensured that player coordinates, HP, flasks, weapons, and all living enemy states (position, health, type) are serialized.

## [ARCHIVED] Dynamic Enemy Serialization & Level Restoration - May 2026
- **Dynamic Serialization:** Updated `GameState.save_stats()` to iterate through all active enemies and capture their `type`, `(x, y)` float coordinates, and current `hp`.
- **Loot Integration:** Ensured that dead enemies (removed from the state) are naturally excluded from the save file, preventing respawns on load.

## [ARCHIVED] Physical Save Persistence & Startup Hydration - May 2026
- **Immediate Hydration:** Refactored `main.py` to read `save_data.json` instantly upon launch, enabling accurate session detection before the title menu renders.
- **Persistent State:** Verified that the "Continue" option correctly appears after restarting the game window if a non-hub session was in progress.
- **Session Flag Alignment:** Synchronized all menu detection logic to use the `active_session_in_progress` flag for consistent behavior.

## [ARCHIVED] Config-Dir Save Persistence & Exit Safety - May 2026
- **Dedicated Dotfile Directory:** Updated `engine/stats.py` to store `save_data.json` inside `~/.config/avoid_rain/`, ensuring proper isolation from project source files.
- **Path Expansion:** Implemented `Path.expanduser()` to correctly resolve the home directory across different system environments.

## [ARCHIVED] Map Editor Overhaul & Interaction Prompt Refinement - May 2026
- **Visual Map Picker (Ctrl+O):** Replaced text-buffer loading with a scrollable overlay containing all discovered `.json` map files. Added Arrow key navigation and `Enter` selection.
- **Palette Divergence Law:** Refactored the palette to dynamically include all engine-supported enemy variants, including the new `M2` (Bleeding Scribe) and `M3` (Forgotten Binder) elites.
- **Palette Coloring:** Updated editor rendering to correctly color-code all specialized spawners and structural tiles.

## [ARCHIVED] Dialogue Closing Intercept & Input Debounce Fix - May 2026
- **Priority Closure:** Updated `GameState.update()` to handle active dialogue closure at the absolute beginning of the frame.
- **Input Consumption:** Closing a dialogue now consumes the `SPACE` input for that frame, preventing it from leaking into the combat or interaction blocks.
- **Input Debouncing:** Implemented an `input_debounce_timer` that provides a 0.2s window after closing a modal during which new interactions are suppressed. This ensures that textboxes do not instantly re-open.

## [ARCHIVED] Combat Rendering Stability Restored - May 2026
- **Typo Fix:** Corrected a variable reference in `Renderer.draw_loot()` where `draw_rect.width` was used instead of the correctly defined `dr.width`.
- **Stability:** Verified that `HealItem` icons (Red cross on white background) render correctly without crashing the engine.

## [ARCHIVED] HUD Proximity Pickup Button & Spacebar De-confliction - May 2026
- **Spacebar De-confliction:** Removed the ability to pick up or swap weapons via the `SPACE` key. Spacebar is now exclusively reserved for attacks and non-item interactions (NPCs, Lore Lecterns).
- **HUD [PICK UP] Button:** Implemented a new clickable HUD button that appears only when the player is standing within proximity of a `WeaponPickup` object.
- **Contextual Visuals:** The button outline dynamically matches the weapon's tier color (White for Common, Purple for Anomalous).

## [ARCHIVED] XDG Config Home Save Redirection & Persistent Flush Fix - May 2026
- **Dynamic Path Resolution (~/.config/avoid_rain/):** Updated `engine/stats.py` to store `save_data.json` within a dedicated `~/.config/avoid_rain/` directory.
- **Path Expansion:** Implemented `os.path.expanduser` to ensure the absolute save destination is dynamically resolved regardless of the system environment.
- **Directory Management:** Enforced explicit directory construction on boot to guarantee the configuration tree exists before any write operations occur.

## [ARCHIVED] Map Editor Sub-Palette Component Cycling Layout - May 2026
- **Monster Brush Array:** Consolidated all active enemy types (`Bat`, `M1`, `M2`, `M3`, `Flutter`, `Bindling`) into a sequential internal array.
- **Single Widget Interface:** Replaced multiple redundant entity buttons with a single interactive button: `[ Monster: <Type> ]`.
- **Cyclic Selection:** Clicking the monster button while it is active now increments an internal index, rotating through every available elite strain.
- **Hover Metadata:** Implemented a contextual hover block that displays the full descriptive name (e.g., "M2 - Bleeding Scribe") when the mouse is over the cyclic widget.

## [ARCHIVED] Interaction Prompt Scope Fix - May 2026
- **Logic Consolidation:** Refactored `Renderer.draw_interaction_prompt()` to ensure `prompt_surf` is always initialized before use.
- **Stability:** Fixed the crash reported when talking to the Chronicler or reading the Chronicle book in the Sanctuary.

## [ARCHIVED] Player Dash Mechanic - May 2026
- **Dash Physics:** Implemented a high-speed directional dash burst (3.0x speed) with a 0.2s duration.
- **Cooldown:** Established a 0.5s recovery window to balance combat mobility.

## [ARCHIVED] Player Block Mechanic - May 2026
- **Damage Mitigation:** Added a blocking state (`K`) providing 100% damage reduction and stagger immunity at the cost of 50% movement speed.

## [ARCHIVED] Pause Menu Controls Overlay & Tabbed Layout - May 2026
- **UI Navigation:** Built a tabbed controls interface accessible from both the Title and Pause menus.

## [ARCHIVED] Save Path Verification & Title Menu Alignment Audit - May 2026
- **Unified Absolute Path Constancy:** Audited and resolved the regression preventing the 'Continue' option from appearing on the Main Menu, ensuring save writes and boot reads target the exact same absolute path.
- **Defensive Folder Initialization:** Implemented explicit folder generation (`os.makedirs`) right before serialization to ensure the configuration directory exists.
- **Hard Disk Save Detection Override for Title Menu Initialization:** Corrected the cold-boot title menu state logic to evaluate the physical presence of `save_data.json` on disk.
- **Runtime Flag Synchronization:** Ensured that if a valid save is detected, the `active_session_in_progress` runtime flag is synchronized immediately.

## [ARCHIVED] Map Editor Socket Drawing Tool & Dimensions HUD - May 2026
- **Canvas Dimensions Readout:** Added a permanent `Size: WxH` indicator in the editor sidebar for real-time feedback during resizing.
- **The Module Socket Brush Tool ([J] Key):** Implemented a specialized `SOCKET` tool with a dedicated click-and-drag interaction loop.
- **Naming Protocol:** Added an interactive banner prompt that triggers upon bounding box completion, allowing users to name the socket (e.g., `M1`, `M2`).
- **Data Integrity:** Ensured sockets are serialized into a root-level `module_sockets` array in the map JSON, fully compliant with the updated format specification.
- **Visual Overlay Rendering:** Implemented persistent rendering for all registered sockets as cyan outlines on the map grid.

## [ARCHIVED] Modular Map Stitching & Socket Injection - May 2026
- **Modular Assembly Logic:** Refactored `LevelLoader.load_json_map` to perform a pre-parsing assembly pass.
- **Tile Overwriting:** The system now overlays sub-map grid matrices onto the master macro-grid using socket bounds.
- **Absolute Entity Blitting:** Implemented logic to transpose sub-map entity coordinates into absolute world-space coordinates during the stitching phase.
- **Macro-World Integration:** Updated `world_map1.json` with `active_plug` references for the `M1` and `M2` sockets.
- **Dimensions Alignment:** Enforced a dimensions validation rule to ensure sub-maps perfectly fit their designated sockets.

## [ARCHIVED] Tiered Module Pools & Rare "Special Edition" Runway Logic - May 2026
- **Pool Definitions:** Established `POOL_MONTHLY_REPORT` and `POOL_SPECIAL_EDITION` in `constants.py` as central registries for modular sub-maps.
- **Monthly Report (Standard):** Contains `maps/test_m1.json`.
- **Special Edition (Rare):** Contains `maps/test_m2.json`.
- **Chronicle Randomization Loop:** Updated "The Chronicle" interaction to perform a 1 in 10 (10%) probability roll when starting a new run.
- **Persistence:** Integrated `active_module_pool` into the `GameState` and persistent `run_state` JSON, ensuring the chosen run variant survives application restarts and manual saves.

## [ARCHIVED] Granular Per-Socket Anomaly Rolls for Module Selection - May 2026
- **Per-Socket Rolls:** Moved the 10% "Special Edition" probability check inside the `LevelLoader.load_json_map` socket iteration loop.
- **Independent Calculations:** Each socket now performs its own unique roll, meaning a single run can contain both standard Monthly Report modules and rare Special Edition challenges simultaneously.
- **HUD & Logging Updates:** Implemented specific terminal logs to distinguish between standard generation and anomaly injection.

## [ARCHIVED] Implementation of the "Smear" Menagerie Anomaly - May 2026
- **Thematic Stats:** Established slow, viscous movement profiles and high HP for Smear entities in `constants.py`.
- **Lore Integration:** Added the `smear_viscosity` lore fragment to the Bestiary Reflection manifest, detailing the origin of these "crawling scrawls."
- **Symbol Mapping:** Assigned the `s` symbol for modular map integration.
- **Amorphous Behavior Logic:** Implemented dynamic spawning of "Inkwell Puddle" hazards during Smear movement.
- **The Splitting Rule:** Engineered a self-replication mechanic where large Smear entities split into two smaller, faster "blots" upon death.

## [ARCHIVED] Map Editor Expansion — Visual Sockets Management, Resizing, & Safe Canvas Creation - May 2026
- **In-Editor Socket Inspector:** Implemented enhanced HUD labels that display socket names and dimensions (`Width x Height`) directly on the canvas.
- **Socket Selection:** Enabled clicking on a socket to select it, highlighting its boundaries in yellow and displaying detailed metadata in the sidebar.
- **Editing & Deletion:** Added `[E]` key to rename the selected socket and `[DEL]` key to remove it from the map's `module_sockets` array.
- **Canvas Resizing ([Ctrl+R]):** Implemented a dedicated input menu that allows users to type specific numerical dimensions for the map grid.
- **Safe Blank Map Canvas ([Ctrl+N]):** Added a `Ctrl+N` shortcut that flushes the grid, clears all entities/sockets, and resets the camera/zoom to defaults.

## [ARCHIVED] Respite Progression UI Overlay & Fresh View Enemy Reset Loops - May 2026
- **Respite Resting Interaction:** Implemented the `execute_rest()` sequence which resets `player.hp` to max and refills `player.flask_charges`.
- **The Fresh View Call:** Integrated a world re-population pass that re-instantiates standard enemy spawners (Slugs, Bats, etc.) while explicitly preserving the death state of Miniboss elites.
- **Level Up Interactive Menu:** Built an expanded UI menu modal triggered by Respite interaction.
- **Attribute Upgrades:** Players can now trade "Torn Pages" to edify their character profile across three categories: **Edification** (Passive Defense), **Prowess** (Attack), and **Fortification** (Max HP).

## [ARCHIVED] Miniboss Polymorphic Refactoring & Drop Pipeline Standardization - May 2026
- **Attribute Injection & Inheritance:** Injected `self.is_miniboss = False` into the baseline `Enemy` constructor.
- **Elite Toggling:** Explicitly set `self.is_miniboss = True` in the `Miniboss` base class.
- **Respite Reset Filter:** Updated the `Respite.execute_rest` logic in `engine/world.py` to filter entities using `getattr(enemy, 'is_miniboss', False)`.
- **Loot Drop Module:** Refactored `GameState.update` to dynamically assign Tier 2 loot rewards based on the `is_miniboss` flag.
- **Save State Reconstruction:** Implemented `ENEMY_REGISTRY` and `SYMBOL_REGISTRY` in `engine/enemy.py`, allowing the `LevelLoader` to reconstruct enemies without hardcoded type branches.

## [ARCHIVED] Respite Level-Up Lock, Input Ratchet Debounce, & HUD Font Scaling Alignment - May 2026
- **Resting Mandate:** Implemented `player.has_rested_this_session` to track the single-use level-up restriction.
- **Transaction Lock:** Completing an edification upgrade or closing the menu instantly clears the flag.
- **UI Input Ratchet:** Implemented a debounce safeguard in `engine/game_state.py` to prevent rapid menu selections.
- **HUD Status Metric Font Realignment:** Scaled down the font size for the top-level HUD parameters (`HP`, `Flasks`, `Pages`) to match the compact 14pt assets.

## [ARCHIVED] HUD Level Display, Notification Spam Silencing, & Sanctuary Save Preservation - May 2026
- **Notification Event Gate:** Silenced Respite notification spam by gating "Not enough pages!" messages behind the input ratchet.
- **Universal Player Level HUD Integration:** Added the player's current Edification level to the main gameplay HUD (e.g., `LVL: 1`).
- **Sanctuary Save Preservation:** Enforced a strict reset rule that clamps the player's Edification level to 1 whenever they are within the Sanctuary hub.
- **Title Menu Logic:** Updated the boot sequence to allow the "Continue" option whenever `save_data.json` exists on disk.

## [ARCHIVED] Closed Volume Lore Integration - May 2026
- **Lore Integration:** Formally defined the **Closed Volume Paradox** in `docs/world_and_lore.md`.
- **The Book Metaphor:** Established that returning to the Sanctuary represents closing a specific manuscript.
- **Run Reset Logic:** Justified the clean-slate return to "Page One" (Level 1) for every fresh run, aligning gameplay balance with thematic consistency.

## [ARCHIVED] Audio System Architecture Mockup & On-Screen Debug Display - May 2026
- **Audio Track Manager Mockup State:** Added `active_track_name` to the `Player` state to store the currently playing OST.
- **Miniboss Proximity Combat Triggers:** Implemented continuous Euclidean distance calculations between the player and any entity with `.is_miniboss == True`.
- **Engagement Persistence:** Added a 3.0-second cooldown timer before the combat track fades back into the exploration theme.
- **Debug HUD OSD Overlay:** Rendered a compact `[DEBUG_AUDIO: Playing <track_name>]` string at the top of the viewport.

## [ARCHIVED] Macro-World Blockout & Modular "Whitebox" Generation - May 2026
- **Macro Canvas Assembly:** Open and structurally expand `maps/world_map1.json` in the Map Editor.
- **Simplified Module Blueprint Files:** Constructed the base 2D character arrays for independent 7x7 socket plugs matching our layout guide.
- **The Cave (`maps/test_m1.json`):** Simple labyrinth of tight, serpentine wall blocks and blind turns.
- **The Pond (`maps/test_m2.json`):** Massive square bounding perimeter outlining a wide, empty center hazard pool.
- **Verification of Granular Randomization:** Verified that crossing through the Chronicle gateway seamlessly loads `world_map1.json` and stitches modules dynamically.

## [ARCHIVED] High-Priority Fix: Miniboss Live-Check Respite Respawn Filter - May 2026

Resolved a regression in the Respite world-reset logic to ensure undefeated minibosses correctly re-manifest during resting loops.

### 1. Persistent Defeat Tracking
- **Miniboss ID Log:** Implemented `defeated_miniboss_ids` in `GameState` to uniquely track sector-level threats that have been officially "redacted" from the world's text.
- **Coordinate-Based Identity:** Injected unique IDs (`map_name:x,y`) into all enemies, ensuring spawner identities are consistent across session reloads and rests.

### 2. Respite Loop Filter Overhaul
- **Polymorphic Evaluation:** Refactored the `execute_rest()` sequence to check the `.is_miniboss` property of all room entities.
- **Precision Respawning:** Updated the spawner logic to only skip instantiation if an elite's unique ID is present in the `defeated_miniboss_ids` manifest. Undefeated minibosses now correctly respawn alongside common enemies.
- **State Synchronization:** Ensured the defeat log is perfectly serialized into the persistent save state.

## [ARCHIVED] Map Editor Multi-Tool Palette Overhaul & Enemy Brush Restoration - May 2026
- **Interactive Resize:** Converted the Map Size display into a clickable button that opens a clean text input dialog.
- **Enhanced Tool Selection:** Added mouse wheel scrolling and click-to-select support to the tool picker dialog.
- **Input Dialog Refactor:** Replaced the problematic `draw_input_banner` with a stable `draw_input_dialog` method.
- **Stability Fix:** Restored the missing `draw_file_picker` method that caused a crash when opening the map selection dialog.

- **Full Tool Registry Consolidation:** Implemented a centralized `MASTER_TOOL_REGISTRY` in `tools/edit_map.py` containing all tiles, enemies, and utilities.
- **Dynamic 10-Slot Hotbar:** Built a new UI sidebar with 10 remappable tool slots.
- **Split Interaction Mechanics:** Slots support left-click for selection and a "SET" button for remapping.
- **Scrollable Tool Picker:** Implemented an overlay modal to assign tools from the registry to hotbar slots with scroll support.
- **Remap Exclusion Logic:** Ensured that assigning a tool to a new slot automatically unassigns it from any previous slot.
- **Enemy Restoration:** Restored selection for Bats, Slugs, Flutters, Bindlings, Smears, and all Miniboss variants (M1, M2, M3).
- **Quality Standards:** Verified code quality with pylint (Rating: 9.44/10).

## [ARCHIVED] 440x440 Generator Correction, Dynamic Sub-Map Generation, & Night Boss Creation - May 2026
- **Generator Refactor:** Overhauled `engine/world_generator.py` to initialize canvases with open floor space (" ") and strictly map 120x120 and 40x40 assets.
- **Placeholder Generation:** Automatically provisioned traversable JSON templates for missing maps (Forest, Ruins, Colophon, Night Boss Arena).
- **Night Boss Integration:** Registered the high-tier "Night Boss" enemy entity and placed it within its dedicated arena module.

## [ARCHIVED] Automated Symmetrical 440x440 World Assembly Compiler - May 2026
- **Procedural Generation Pipeline:** Fully implemented the symmetric sizing array `[120, 40, 120, 40, 120]`.
- **World Assembly:** Automated the stitching of sub-maps (Forest, Ruins, Colophon, Night Boss) into a massive 440x440 macro-world layout.
- **Warp Integration:** Hooked the `WorldGenerator` into the Chronicle interaction script, ensuring a fresh world is compiled and exported whenever the player enters a new run.
- **Spawn Re-Targeting:** Implemented procedural spawn coordinate overrides to ensure the player always starts in the center of the Colophon module.

## [Recently Completed]
### Spatial Overhaul: The Redacting Circle (The Bleed)
- **Shrinking Safe Circle:** Replaced temporal storm phases with a spatial "Safe Zone" that contracts toward the Night Boss Arena.
- **State Machine Lifecycle:** Implemented a cyclic "Wait -> Contract -> Pause" state machine for the safe circle, ending in a final clamp around the boss lair.
- **Asynchronous Rendering Fix:** Resolved the movement freezing bug by implementing a persistent, time-scaled particle system that updates independently of the physics thread.
- **Shelter-Aware Hazard:** Integrated radial distance checks with tile-based shelter detection; players only take damage if outside the safe circle AND not under a structure ("T").
- **Asset Integration:** Updated `WorldGenerator` to export boss center coordinates for real-time safe zone anchoring.

### The Bleed: Core Weather System & Shelter Mechanics
- **Weather Lifecycle:** Implemented a global state machine cycling between "Clearance" (90s) and "Downpour" (45s) phases.
- **Exposure Detection:** Integrated real-time tile-based logic to check if the player is standing under open sky or protected by a structure ("T") or Respite ("R").
- **Damage Over Time:** Exposed players now accumulate 2.0 HP/sec corrosive damage during active storm phases.
- **Visual Rain Layer:** Developed a performant screen-space particle overlay featuring translucent "Toxic Lime" vertical rain falling across the viewport.
- **Documentation:** Codified the system rules and shelter vectors in `docs/architecture.md`.

## [Recently Completed]
### Minimap Overhaul & Weather Damage Fix
- **Minimap Visualization:** Overhauled the minimap to feature a higher zoom scale and updated radar color rules (White for player, Red for enemies).
- **Safe Circle Indicator:** Added real-time rendering of the shrinking safe circle boundary directly onto the minimap radar.
- **Hub Exclusion:** Gated the minimap to be completely hidden while the player is in the Sanctuary hub, ensuring a cleaner interface for non-combat zones.
- **Damage Precision:** Fixed the acid rain damage tracking to accurately subtract 2 HP per second when exposed outside the safe circle.
- **Boss Encounter Gating:** Implemented logic to gate the Night Boss spawn until the safe circle has fully closed, locking the perimeter until the encounter is resolved.

## [Recently Completed]
### Damage Stagger Bypass & 3-Step Radius Contraction Sequence
- **Stagger Bypass:** Refactored environmental damage logic to completely bypass hit-reactions, allowing uninterrupted player movement while exposed to acid rain.
- **3-Step Contraction:** Overhauled the safe circle state machine to contract in three distinct, major steps (300, 120, and 40 units) rather than a continuous slow crawl.
- **Interval Management:** Established a 40-second pause between contraction phases to allow for tactical traversal and exploration.
- **Grace Period Preservation:** Maintained the strict 60-second wide-open initial grace period before the first contraction begins.

## [Recently Completed]
### State & UI Refinement: Exposure Logic & Minimap Stability
- **Exposure State Fix:** Implemented explicit `is_exposed` tracking in `Player` and `WeatherManager`. Damage now correctly halts the moment a player enters the safe zone or shelter.
- **Sanctuary Damage Wipe:** Enforced a hard reset of the exposure state upon returning to the Sanctuary hub.
- **Minimap Stability:** Resolved the "black screen" minimap bug by enforcing strict integer casting and boundary clamping across the 440x440 grid.
- **Improved Radar Visuals:** Updated radar colors to high-contrast White (player) and Red (enemies), and integrated the safe circle perimeter line into the minimap display.
- **Hub UI Logic:** Gated the minimap to automatically hide while in the Sanctuary hub.

## [Recently Completed]
### Minimap Blit & Render Order Finalization
- **Corrected Render Order:** Relocated the surface clearance method (`.fill()`) to the absolute beginning of the minimap draw loop, preventing the accidental erasure of rendered dots and boundaries.
- **Main Canvas Blitting:** Verified and enforced the final `screen.blit` call to ensure the local minimap surface is correctly painted onto the main gameplay window.
- **Surface Stability:** Implemented a dedicated local surface for the minimap to ensure clean alpha blending and prevent coordinate bleeding.
- **Exposure Fail-Safe:** Explicitly synchronized `player.is_exposed` reset logic to halt environmental damage instantly upon entering safe zones.

## [Recently Completed]
### Polish & Bugfix Pass: Economy & Feedback
- **Economy Reset:** Implemented an absolute Page count reset upon returning to the Sanctuary hub, ensuring a fresh start for every run.
- **Dynamic Respite Menu:** Refactored the level-up menu to recalculate player stats and page costs in real-time, eliminating stale data blits.
- **Cinematic Weather Alerts:** Integrated the "Typographic Bloom" system with weather milestones; the game now flashes "THE INK BEGINS TO RUN" and "THE FINAL PARAGRAPH LOCKS" to signal critical safe-zone shifts.
- **Health Restoration:** Confirmed full HP restoration when entering the Sanctuary hub to facilitate run preparation.

## [Recently Completed]
### Respite UI Polish & Legacy Entity Purge
- **Training Dummy Elimination:** Completely purged the hardcoded training dummy entity and its associated logic from the engine and renderer, finalizing the transition to data-driven content.
- **Dedicated UI Layer:** Created the `ui/menu.py` module to handle specialized interface components, improving code modularity.
- **Dynamic Respite Menu:** Refactored the Respite level-up system to accept the live `state` object. The interface now recalculates player stats and upgrade costs every frame for zero-latency feedback.
- **Visual Lockout Feedback:** Implemented a visual "gray-out" state for unaffordable upgrades and added an on-screen "[ Insufficient Pages ]" warning to improve player economy awareness.

## [Recently Completed]
### Typographic Bloom: Zone Discovery Overlays
- **Discovery Detection:** Implemented real-time zone tracking in `GameState` that triggers title events when entering any of the nine major 120x120 room nodes.
- **Stylized Overlays:** Developed an alpha-blended rendering layer that displays large, stylized "noir" title cards (e.g., "THE SCORCHED MARGIN") across the camera viewport.
- **Smooth Animation:** Coded a three-stage animation lifecycle (Fade-In, Hold, Fade-Out) using dedicated timing constants for a professional aesthetic lift.
- **Discovery Cooldown:** Integrated a boundary cooldown to prevent title spamming when crossing corridor/room thresholds.

### Macro Safe Zone Initialization Repair & Initial Grace Period Lock
- **Massive Starting Radius:** Enforced a 620.0 unit initial `active_safe_radius` to ensure the entire 440x440 world is safe upon run start.
- **Initial Grace Period:** Implemented a strict 60-second grace period during which all rain visuals and environmental hazards are suppressed.
- **Initialization Fix:** Resolved the game thread freeze by delegating weather logic to a dedicated `WeatherManager` and using time-based particle updates.
- **Dynamic Contraction:** Integrated the warning event and smooth contraction sequence centered on the Night Boss Arena.

## [ARCHIVED] Fix Sanctuary State Isolation, Force Page Resets, and Repair Respite Font Rendering - May 2026
- **Hub Isolation:** Implemented a definitive gate in `engine/weather.py` and `rendering/renderer.py` that freezes all rain logic, timers, and particle rendering while the player is in the Sanctuary hub.
- **Robust Page Reset:** Enforced an absolute clear of the player's Page count at the map-load level whenever they enter the Sanctuary, ensuring a clean economic state for every new run regardless of how the transition was triggered.
- **Real-Time Respite UI:** Refactored the Respite menu to explicitly call `font.render()` every frame using live player statistics, ensuring that understanding levels and page costs update visually the instant an upgrade occurs.
- **Indentation Fix:** Resolved a crash caused by a missing return statement in the Renderer's weather logic during the hub isolation pass.

## [Recently Completed]
### Multi-Boss Run Lifecycle & Victory Sequence
- **Dual Night Boss Support:** Overhauled `engine/world_generator.py` and `engine/weather.py` to support two distinct Night Boss arenas per run, targeted sequentially by the safe circle.
- **The Dilution Interlude:** Implemented a safe-weather "Dilution" phase triggered by the defeat of the first Night Boss, featuring safe blue rain and a 10-second breather before the second contraction begins.
- **Dynamic Arena Spawning:** Resolved boss duplication by implementing "Dormant Arenas." Night Bosses now only manifest dynamically when the safe circle reaches its final closed state.
- **The Appendix (Final Boss):** Developed a 50x50 `final_boss.json` arena and implemented a warp portal that manifests after the second Night Boss falls, leading to the ultimate encounter.
- **True Victory Loop:** Integrated run-victory logic; defeating The Final Author triggers a permanent Dilution effect, records a Chapter Clear statistic, and extracts the player to the Sanctuary.
- **Cinematic Feedback:** Linked all major lifecycle transitions (Appendix Reveal, Dilution, Second Draft) to the Typographic Bloom system for high-impact cinematic alerts.
- **State Persistence:** Verified and enforced full weather and run-progress serialization, ensuring mid-run storm states survive application restarts.
