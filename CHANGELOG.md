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

## [ARCHIVED] Hard Persistent Save File Serialization & Startup Boot Hook - May 2026

Migrated from internal in-memory session tracking to absolute, physical JSON disk persistence to ensure game state survival across application restarts.

### 1. Hard Disk Serialization on Exit
- **Physical Persistence:** Updated the session saving module to write directly to `save_data.json` in the project root.
- **Data Integrity:** Implemented atomic write operations (using temporary files and `os.replace`) to prevent data corruption during unexpected exits.
- **Payload Coverage:** Ensured that player coordinates, HP, flasks, weapons, and all living enemy states (position, health, type) are serialized.

### 2. Main Boot Initialization Check
- **Launch Hydration:** Refactored the main application entry point to perform an explicit `json.load()` check on `~/.config/avoid_rain/save_data.json` immediately upon startup.
- **Physical Detection:** The "Continue" button now relies on an absolute physical disk check instead of volatile runtime memory, ensuring accurate session detection after cold boots.
- **Resilience:** Implemented exception handling for `json.JSONDecodeError` to gracefully manage malformed save files without crashing the application.

### 3. Session Cleanup Rules
- **Death Clearance:** Verified that player death or a clean warp-out to the Sanctuary correctly clears the `active_session_in_progress` flag and resets the `run_state` on disk.
- **Verification:** Confirmed fix with comprehensive unit tests ensuring sessions are correctly set, cleared, and restored.

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

## [ARCHIVED] Config-Dir Save Persistence & Exit Safety - May 2026

Updated the save system to use XDG-compliant configuration paths and guaranteed data integrity during shutdowns.

### 1. Dedicated Dotfile Directory
- **Path Migration:** Updated `engine/stats.py` to store `save_data.json` inside `~/.config/avoid_rain/`, ensuring proper isolation from project source files.
- **Path Expansion:** Implemented `Path.expanduser()` to correctly resolve the home directory across different system environments.

### 2. Exit Safety & Flush Guarantee
- **Atexit Integration:** Registered a shutdown handler using Python's `atexit` module in `main.py`.
- **Hard Persistence:** The shutdown handler performs a final synchronous `save_stats(wait=True)` call, ensuring that session data is perfectly flushed to the hard drive even if the game window is abruptly closed.
- **Verification:** Verified path resolution and session flag persistence with automated tests.

## [ARCHIVED] Map Editor Overhaul & Interaction Prompt Refinement - May 2026

Enhanced the developer toolset with a visual file picker and dynamic palette synchronization, while refining player-facing interaction strings.

### 1. Map Editor Visual Overhaul
- **Visual Map Picker (Ctrl+O):** Replaced text-buffer loading with a scrollable overlay containing all discovered `.json` map files. Added Arrow key navigation and `Enter` selection.
- **Palette Divergence Law:** Refactored the palette to dynamically include all engine-supported enemy variants, including the new `M2` (Bleeding Scribe) and `M3` (Forgotten Binder) elites.
- **Palette Coloring:** Updated editor rendering to correctly color-code all specialized spawners and structural tiles.

### 2. UI & Interaction Strings
- **Prompt Refinement:** Updated `Renderer.draw_interaction_prompt()` to remove weapon collection from the `SPACE` key instruction.
- **HUD Guidance:** The ground weapon prompt now explicitly reads: `"[Click [PICK UP] on HUD to claim weapon]"`, aligning with the recently decoupled input scheme.
- **Stability:** Verified that interaction modals and prompt layers correctly prioritize player focus without overlapping instructions.

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

## [ARCHIVED] HUD Proximity Pickup Button & Spacebar De-confliction - May 2026

Decoupled weapon collection from the keyboard combat input layer, replacing it with an interactive HUD element.

### 1. Interaction Refactor
- **Spacebar De-confliction:** Removed the ability to pick up or swap weapons via the `SPACE` key. Spacebar is now exclusively reserved for attacks and non-item interactions (NPCs, Lore Lecterns).
- **HUD [PICK UP] Button:** Implemented a new clickable HUD button that appears only when the player is standing within proximity of a `WeaponPickup` object.
- **Contextual Visuals:** The button outline dynamically matches the weapon's tier color (White for Common, Purple for Anomalous).

### 2. Click Handling & Inventory Logic
- **UI Interaction:** Added mouse click detection for the new button region. 
- **Inventory Integration:** Clicking `[PICK UP]` correctly handles adding the weapon to an empty slot or swapping/dropping the currently active weapon if the Cradle is full.
- **Verification:** Added `tests/test_pickup_button.py` to confirm input suppression and button functionality.

## [ARCHIVED] XDG Config Home Save Redirection & Persistent Flush Fix - May 2026

Redirected all game session save states to a platform-native dotfile configuration folder and ensured absolute disk synchronization before application exit.

### 1. Dynamic Path Resolution (~/.config/avoid_rain/)
- **XDG Compliance:** Updated `engine/stats.py` to store `save_data.json` within a dedicated `~/.config/avoid_rain/` directory.
- **Path Expansion:** Implemented `os.path.expanduser` to ensure the absolute save destination is dynamically resolved regardless of the system environment.
- **Directory Management:** Enforced explicit directory construction on boot to guarantee the configuration tree exists before any write operations occur.

### 2. Guaranteed Disk Serialization
- **Atexit Integration:** Registered a formal shutdown function using Python's `atexit` module in `main.py`.
- **Absolute Persistence:** The shutdown hook forces a final synchronous save flush (`os.fsync`) whenever the game window is closed or the process terminates.
- **Verification:** Confirmed that the "Continue" option accurately persists across application reboots by reading directly from the absolute configuration path.

## [ARCHIVED] Map Editor Sub-Palette Component Cycling Layout - May 2026

Refactored the map editor sidebar UI to use a compact, cyclic toggle for all enemy entities.

### 1. Cyclic Interaction Logic
- **Monster Brush Array:** Consolidated all active enemy types (`Bat`, `M1`, `M2`, `M3`, `Flutter`, `Bindling`) into a sequential internal array.
- **Single Widget Interface:** Replaced multiple redundant entity buttons with a single interactive button: `[ Monster: <Type> ]`.
- **Cyclic Selection:** Clicking the monster button while it is active now increments an internal index, rotating through every available elite strain.
- **Hover Metadata:** Implemented a contextual hover block that displays the full descriptive name (e.g., "M2 - Bleeding Scribe") when the mouse is over the cyclic widget.

### 2. UI Synchronization
- **Palette Divergence Law:** Ensured that all current engine enemy symbols are automatically registered in the editor palette.
- **Rendering Alignment:** Updated the editor's grid and sidebar drawing code to correctly color-code all specialized spawner symbols.

## [ARCHIVED] Interaction Prompt Scope Fix - May 2026

Resolved a critical `UnboundLocalError` that occurred when interacting with NPCs and world objects.

### 1. Renderer Correction
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

Upgraded the map editor utility to support the new modular map nesting protocol and enhanced the HUD with real-time canvas dimensions.

### 1. Canvas Dimensions Readout
- Added a permanent `Size: WxH` indicator in the editor sidebar for real-time feedback during resizing.
- Integrated `Cursor Grid: (X, Y)` tracking into the editor HUD.

### 2. The Module Socket Brush Tool ([J] Key)
- Implemented a specialized `SOCKET` tool with a dedicated click-and-drag interaction loop.
- **Naming Protocol:** Added an interactive banner prompt that triggers upon bounding box completion, allowing users to name the socket (e.g., `M1`, `M2`).
- **Data Integrity:** Ensured sockets are serialized into a root-level `module_sockets` array in the map JSON, fully compliant with the updated format specification.

### 3. Visual Overlay Rendering
- Implemented persistent rendering for all registered sockets as cyan outlines on the map grid.
- Added dynamic label rendering to display socket identifiers directly on the canvas for better spatial orientation.
- Verified that socket visualization persists through save/load cycles.

## [ARCHIVED] Modular Map Stitching & Socket Injection - May 2026

Implemented the "Master Loom" modular assembly system, allowing for seamless injection of sub-maps into macro-world environments.

### 1. LevelLoader Refactor (Stitching Pass)
- **Modular Assembly Logic:** Refactored `LevelLoader.load_json_map` to perform a pre-parsing assembly pass.
- **Tile Overwriting:** The system now overlays sub-map grid matrices onto the master macro-grid using socket bounds.
- **Absolute Entity Blitting:** Implemented logic to transpose sub-map entity coordinates into absolute world-space coordinates during the stitching phase.

### 2. Macro-World Integration
- **Socket Configuration:** Updated `world_map1.json` with `active_plug` references for the `M1` and `M2` sockets.
- **Dimensions Alignment:** Enforced a dimensions validation rule to ensure sub-maps perfectly fit their designated sockets.
- **Verification:** Confirmed successful runtime assembly through prototype instantiation tests, verifying both tile layout and entity population.

## [ARCHIVED] Tiered Module Pools & Rare "Special Edition" Runway Logic - May 2026

Implemented a tiered randomization system for level modules, introducing rare "Special Edition" run variants.

### 1. Dual-Pool Registration
- **Pool Definitions:** Established `POOL_MONTHLY_REPORT` and `POOL_SPECIAL_EDITION` in `constants.py` as central registries for modular sub-maps.
- **Monthly Report (Standard):** Contains `maps/test_m1.json`.
- **Special Edition (Rare):** Contains `maps/test_m2.json`.

### 2. Chronicle Randomization Loop
- **Trigger Event:** Updated "The Chronicle" interaction to perform a 1 in 10 (10%) probability roll when starting a new run.
- **Pool Selection:** Successfully rolled runs now pull modules exclusively from the `POOL_SPECIAL_EDITION`, while standard runs default to the `POOL_MONTHLY_REPORT`.
- **Persistence:** Integrated `active_module_pool` into the `GameState` and persistent `run_state` JSON, ensuring the chosen run variant survives application restarts and manual saves.

### 3. LevelLoader Pool Overrides
- **Stitching Pass:** Updated the `LevelLoader` to support dynamic pool-based overrides. When a pool is specified, the system ignores hardcoded `active_plug` values and selects random modules from the active pool for every available socket.

## [ARCHIVED] Granular Per-Socket Anomaly Rolls for Module Selection - May 2026

Refactored the modular generation pipeline to execute anomaly rolls independently for every available socket, enabling mixed-pool environments.

### 1. Decentralized Random Selection
- **Per-Socket Rolls:** Moved the 10% "Special Edition" probability check inside the `LevelLoader.load_json_map` socket iteration loop.
- **Independent Calculations:** Each socket now performs its own unique roll, meaning a single run can contain both standard Monthly Report modules and rare Special Edition challenges simultaneously.

### 2. HUD & Logging Updates
- **Diagnostic Tracing:** Implemented specific terminal logs to distinguish between standard generation and anomaly injection:
    - `[Generation] Socket <Name> compiled as Standard Monthly Report.`
    - `[ANOMALY INJECTION] Socket <Name> rolled a rare Special Edition!`

### 3. State Simplification
- **Persistence Refactor:** Removed `active_module_pool` from the global `GameState` and persistence layers. Since selection is now a generative property of the world load pass, it no longer requires run-wide tracking.

## [ARCHIVED] Map Editor Expansion — Visual Sockets Management, Resizing, & Safe Canvas Creation - May 2026

Overhauled the map editor utility with robust socket management, precise canvas resizing, and a safe workflow for new map creation.

### 1. In-Editor Socket Inspector & Modification
- **Visual Feedback:** Implemented enhanced HUD labels that display socket names and dimensions (`Width x Height`) directly on the canvas.
- **Socket Selection:** Enabled clicking on a socket to select it, highlighting its boundaries in yellow and displaying detailed metadata in the sidebar.
- **Editing & Deletion:** Added `[E]` key to rename the selected socket and `[DEL]` key to remove it from the map's `module_sockets` array.

### 2. Canvas Resizing Control Interface
- **Sidebar Integration:** Integrated a permanent `Size: WxH` readout in the sidebar for real-time monitoring.
- **Precise Resizing ([Ctrl+R]):** Implemented a dedicated input menu that allows users to type specific numerical dimensions for the map grid.
- **Data Preservation:** Ensured the resizing logic correctly pads with empty tiles (`.`) when expanding and safely truncates when shrinking.

### 3. Safe Blank Map Canvas Sequence ([Ctrl+N])
- **Clean Slate:** Added a `Ctrl+N` shortcut that flushes the grid, clears all entities/sockets, and resets the camera/zoom to defaults.
- **The Overwrite Guard:** Implemented an explicit file path reset to `None` upon creating a new map. This prevents `Ctrl+S` from overwriting the previously loaded file, forcing a naming prompt for the new asset.

## [ARCHIVED] Expanding world_map1.json into a Large-Scale Modular Testing Layout - May 2026

Scaled up the macro-world testing grounds to verify the performance and aesthetic consistency of the "Master Loom" modular assembly system at scale.

### 1. Macro-World Scaling
- **Canvas Expansion:** Resized `maps/world_map1.json` to a significantly larger footprint ($100 \times 100$) using the new editor resizing tools.
- **Topology Design:** Developed a high-quality "Lotus Topography" frame that links multiple disparate regions via intentional corridors and pathways.

### 2. Socket Population & Anomaly Testing
- **Dense Sockets:** Placed 8-10 independent module sockets throughout the expanded map layout.
- **Content Variety:** Assigned a diverse range of `active_plug` targets, including combat arenas, lore-heavy respite zones, and hazard corridors.
- **Generative Verification:** Verified that the per-socket 10% Special Edition roll correctly populates the large-scale world with a mix of standard and rare modules.

### 3. Stress Test & Performance
- **Load Optimization:** Verified that the "Master Loom" assembly pass executes efficiently even with double-digit socket counts.
- **Viewport Stability:** Ensured that the camera damping and minimap panning handle the expanded $100 \times 100$ grid without artifacting or lag.

## [ARCHIVED] Implementation of the "Smear" Menagerie Anomaly - May 2026

Introduced the Smear enemy type, a viscous ink-based threat that reinforces the Scriptorium Noir aesthetic and implements unique splitting and hazard-dropping mechanics.

### 1. Mechanical Definition
- **Thematic Stats:** Established slow, viscous movement profiles and high HP for Smear entities in `constants.py`.
- **Lore Integration:** Added the `smear_viscosity` lore fragment to the Bestiary Reflection manifest, detailing the origin of these "crawling scrawls."
- **Symbol Mapping:** Assigned the `s` symbol for modular map integration.

### 2. Amorphous Behavior Logic
- **The Trail Rule:** Implemented dynamic spawning of "Inkwell Puddle" hazards during Smear movement, creating persistent area-denial zones that slow the player.
- **The Splitting Rule:** Engineered a self-replication mechanic where large Smear entities split into two smaller, faster "blots" upon death.

### 3. Tooling Synchronization
- **Map Editor:** Updated `tools/edit_map.py` to include the Smear in the palette and enemy cycle list, ensuring designers can place these anomalies in future modules.
- **Level Loader:** Enhanced the `LevelLoader` to support Smear spawning and state reconstruction.

## [ARCHIVED] Respite Progression UI Overlay & Fresh View Enemy Reset Loops - May 2026

Implemented the functional state architecture for Respite resting, itemized page level-ups, and conditional HP-bracket defensive stat modifications.

### 1. Respite Resting Interaction & World Reset
- **Character Restoration:** Implemented the `execute_rest()` sequence which resets `player.hp` to max and refills `player.flask_charges`.
- **The Fresh View Call:** Integrated a world re-population pass that re-instantiates standard enemy spawners (Slugs, Bats, etc.) while explicitly preserving the death state of Miniboss elites.
- **State Persistence:** Ensured that resting triggers a synchronous save flush to prevent progress loss.

### 2. Level Up Interactive Overlay Menu
- **Edification Interface:** Built an expanded UI menu modal triggered by Respite interaction.
- **Attribute Upgrades:** Players can now trade "Torn Pages" to edify their character profile across three categories: **Edification** (Passive Defense), **Prowess** (Attack), and **Fortification** (Max HP).
- **Linear Scaling Curve:** Implemented a strictly linear cost formula: `Cost = 10 + (Level * 5)`.

### 3. Bracketed Stat Defensive Scaling Hooks
- **Conditional Parsing:** Added passive defensive buffs that activate based on the player's current health threshold relative to their Edification level.
- **Pristine Concentration:** Grants `(Edification / 2)%` damage reduction when health is above 95%.
- **Desperate Synthesis:** Grants `(Edification)%` damage reduction when health is below 30%.
- **Architecture:** Synchronized `docs/world_and_lore.md` and `docs/architecture.md` with the new Edification definitions and technical specs.

## [ARCHIVED] Miniboss Polymorphic Refactoring & Drop Pipeline Standardization - May 2026

Refactored the enemy architecture to eliminate hardcoded string checks for specific miniboss types, transitioning to a scalable boolean-flag-driven system.

### 1. Attribute Injection & Inheritance
- **Base Property:** Injected `self.is_miniboss = False` into the baseline `Enemy` constructor.
- **Elite Toggling:** Explicitly set `self.is_miniboss = True` in the `Miniboss` base class, ensuring all current (`M1`, `M2`, `M3`) and future elites inherit the trait automatically.

### 2. Core System Decoupling
- **Respite Reset Filter:** Updated the `Respite.execute_rest` logic in `engine/world.py` to filter entities using `getattr(enemy, 'is_miniboss', False)`, ensuring all elite types are preserved across rests without manual string lookups.
- **Loot Drop Module:** Refactored `GameState.update` to dynamically assign Tier 2 loot rewards based on the `is_miniboss` flag, standardizing the reward pipeline for all high-value targets.
- **Save State Reconstruction:** Implemented `ENEMY_REGISTRY` and `SYMBOL_REGISTRY` in `engine/enemy.py`, allowing the `LevelLoader` to reconstruct enemies from persistent data or map symbols without hardcoded type branches.

## [ARCHIVED] Respite Level-Up Lock, Input Ratchet Debounce, & HUD Font Scaling Alignment - May 2026

Resolved input spamming inside menu overlays, enforced the single-use level-up restriction per rest cycle, and aligned HUD layout text fonts.

### 1. Level-Up Lock State Integration
- **Resting Mandate:** Implemented `player.has_rested_this_session` to track the single-use level-up restriction.
- **Unlock Trigger:** The flag is toggled to `True` strictly upon triggering a "Rest" action at a Respite.
- **Transaction Lock:** Completing an edification upgrade or closing the menu instantly clears the flag, preventing repeated level-ups without accepting the risk of a world reset.
- **Visual Feedback:** Added an interactive message block reading `"[Must Rest to Unblock Level Up]"` when the edification menu is locked.

### 2. UI Input Ratchet (Debounce Safeguard)
- **Transaction Security:** Implemented an input ratchet in `engine/game_state.py` to prevent rapid menu selections and accidental double-purchases.
- **Event-Driven Latching:** UI actions now require a distinct `KEYUP` or `MOUSEBUTTONUP` signal from the OS to reset the input latch, blocking continuous held-input triggers.

### 3. HUD Status Metric Font Realignment
- **Typography Standardization:** Scaled down the font size for the top-level HUD parameters (`HP`, `Flasks`, `Pages`) to match the compact 14pt assets used for action prompts.
- **Visual Alignment:** Improved vertical padding and boundary containment within the HUD panel for a cleaner, professional interface.

## [ARCHIVED] Closed Volume Lore Integration - May 2026

Anchored the Sanctuary level-1 reset mechanic within the master narrative source-of-truth documentation.

### 1. Narrative Justification
- **Lore Integration:** Formally defined the **Closed Volume Paradox** in `docs/world_and_lore.md`.
- **The Book Metaphor:** Established that returning to the Sanctuary represents closing a specific manuscript. Because comprehension is tied to an active reading of a text, the traveler's Edification level collapses when the volume is shelved.
- **Run Reset Logic:** Justified the clean-slate return to "Page One" (Level 1) for every fresh run, aligning gameplay balance with thematic consistency.

## [ARCHIVED] Audio System Architecture Mockup & On-Screen Debug Display - May 2026

Implemented an engine track manager mockup and a visual HUD overlay to track soundtrack assignments, including distance-based combat triggers.

### 1. Audio Track Manager Mockup State
- **Active Tracking:** Added `active_track_name` to the `Player` state to store the currently playing OST.
- **Zone Dynamics:** Implemented logic to automatically shift track assignments based on the active zone (e.g., `title_theme.ogg`, `sanctuary_hub.ogg`, `world_exploration.ogg`).
- **Death Feedback:** Set the soundtrack to `death_screen.ogg` upon player HP depletion.

### 2. Miniboss Proximity Combat Triggers
- **15-Meter Detection:** Implemented continuous Euclidean distance calculations between the player and any entity with `.is_miniboss == True`.
- **Combat Hysteresis:** Entering a 15-meter (600px) radius instantly triggers `miniboss_combat.ogg`.
- **Engagement Persistence:** Added a 3.0-second cooldown timer that must expire before the combat track fades back into the exploration theme, preventing audio flicker during repositioning.

### 3. Debug HUD OSD Overlay
- **Audit Tool:** Rendered a compact `[DEBUG_AUDIO: Playing <track_name>]` string at the top of the viewport.
- **Universal Visibility:** Integrated the OSD into both the main game renderer and the Title Screen interface for perfect logic auditing.

## [ARCHIVED] HUD Level Display, Notification Spam Silencing, & Sanctuary Save Preservation - May 2026

Fixed UI message duplication during level-ups, integrated player level readouts across the HUD, and ensured the Main Menu displays 'Continue' for hub-world saves.

### 1. Notification Event Gate
- **Spam Prevention:** Silenced Respite notification spam by gating "Not enough pages!" messages behind the input ratchet.
- **Initial Trigger Only:** Alert messages now only fire on the initial down-press frame, preventing text buffer flooding during held inputs.

### 2. Universal Player Level HUD Integration
- **HUD Update:** Added the player's current Edification level to the main gameplay HUD (e.g., `LVL: 1`) using standardized compact fonts.
- **Menu Visibility:** Ensured the level metric is also clearly visible inside the Respite menu overlay text strings.

### 3. Sanctuary Save Preservation & Level Reset Hooks
- **Level Clamping:** Enforced a strict reset rule that clamps the player's Edification level to 1 whenever they are within the Sanctuary hub.
- **Persistence Fix:** Resolved a bug where `player.stats` were not being correctly serialized into the `run_state`.
- **Title Menu Logic:** Updated the boot sequence to allow the "Continue" option whenever `save_data.json` exists on disk, supporting resumption from Sanctuary saves.
