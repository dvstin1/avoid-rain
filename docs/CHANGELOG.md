# Changelog

## [Recently Completed]
### Pygame-Based Wall Texture Desaturation
- **Wall Saturation Removal:** Implemented custom color saturation removal on startup using Pygame. The `brown_wall.png` asset is programmatically converted to grayscale (using the standard luminosity method: 0.299R + 0.587G + 0.114B) while keeping the original alpha channel.
- **Grayscale Unit Testing:** Wrote a test suite in `tests/test_wall_desaturation.py` verifying that color surfaces are correctly converted to grayscale while preserving alpha channels.

### High-Density Thicket & Overgrown Vegetation System
- **Pre-loaded and Cached Grass Sizes:** Added startup loading, scaling, and caching of `grass_medium.png` (32x32) and `grass_tall.png` (40x40) alongside `grass_small.png` (16x16).
- **RAM Variants Pool:** Generated horizontal flip and yellow-tinted RAM variants for all grass sizes at initialization.
- **Topography Support for Thickets:** Registered `TILE_THICKET` in engine topo configurations mapped to the uppercase character `G`.
- **Meadow Overgrowth Chance:** Introduced a rare 5% chance per instance on Meadow Tiles (`g`) to select a medium or tall grass variant.
- **High-Density Thicket Clustering:** Implemented the Overgrown Thicket Tile (`G`) which spawns a heavy cluster of 5 to 10 grass instances, heavily weighted (10% small, 45% medium, 45% tall) to prioritize larger variants, rendering on top of the base grass floor tile background.
- **Map and Tool Sync:** Integrated `tile_thicket` into `MASTER_TOOL_REGISTRY` in the map editor, and registered `G` in map legends for `sanctuary.json` and `smallcave.json`.
- **Validation Suite:** Created unit tests verifying parsing, density distributions, scaling, variant pools, and rendering.

### Layered Visuals & Input Refinement: "The Ghost Indicator System"
- **Layered Visual Architecture:** Implemented a decoupled animation system in `Actor` and `Player` that generates 'Visual Packets' containing base actions, physical postures, and status overlays.
- **Renderer "Ghost Indicators":** Overhauled character rendering to draw abstract visual cues:
    - **Postures:** Actors now "squash" (wounded) or vibrate (staggered) based on state.
    - **Overlays:** Added stylized indicators for `BIND` (green vines), `EXPOSED` (shimmer), and `PARRY_WINDOW` (glow).
    - **Progress Bars:** Integrated timing bars above heads for combat telegraphs.
- **Expanded Inspect HUD:**
    - Added a 'Held' inspect action mapped to `TAB` (KB) and `R1` (Gamepad).
    - Holding inspect reveals stylized tooltips with full weapon names, flavor descriptions, and explicit stat modifiers.
    - Supported side-by-side comparison for equipped quills and floor items.
- **Contextual Input Overhaul:**
    - Restored `SPACE / A` interaction for all world objects, including weapons.
    - Implemented **Contextual Swap**: Pressing `Q / L1` while over a weapon immediately collects and equips it.
- **World Balancing & Stability:**
    - **Boss Scaling:** Doubled HP for Minibosses/Night Bosses and tripled HP for the Final Author.
    - **Sanctuary Purification:** Fixed a visual bug where broken barrels persisted in the Hub; the Sanctuary now reset to a pristine state upon entry.
    - **Unit Test Restoration:** Fixed 52+ regression failures and optimized performance by removing high-volume debug logs.
- **Authoritative Map Transfer:** Established a TCP-based world synchronization protocol that transmits the Host's full generated macro-world JSON to clients.
- **Warp Interception:** Modified the Chronicle interaction for Clients to fetch and load the Host's map instead of triggering local procedural generation.
- **Host-Side Profile Caching:** Implemented a persistence layer on the Host that caches connected client states (equipment, stats, HP).
- **Session Restoration:** Configured the TCP handshake to automatically restore a client's profile upon reconnection, preventing progress loss on crash or disconnect.
- **Late Join Support:** Enabled clients to warp into an active Host's run at any time with synchronized geometry.

### Local Network Play (Phase 2): Handshake & State Replication
- **TCP Handshake:** Implemented a reliable session initiation protocol between discovery peers to verify identity and connection readiness.
- **UDP State Sync (30Hz):** Engineered a high-frequency synchronization loop for real-time player coordinates and HP transmission.
- **Auto-Host Mechanism:** Configured the engine to automatically begin hosting when the player warps from the Sanctuary into the macro-world.
- **Visual LAN Lobby:** Built a new UI menu in the Title Screen for automated host discovery and one-click connection.
- **Fault Tolerance:** Implemented a heartbeat/timeout system that warps players back to the Sanctuary Hub upon network connection loss.

### Local Network Play (Phase 1): Discovery Foundation
- **Identity & Config:** Established `PLAYER_NAME` and `LAN_PORT` (55555) in `constants.py` for standardized network identification.
- **Non-Blocking Network Manager:** Created `engine/network_manager.py` using Python's `socket` and `threading` libraries.
- **UDP Discovery Loop:** Implemented background broadcasting of identity payloads ("Dustin's Game") and automated subnet scanning for active host beacons.
- **Terminal Debugging:** Added direct console logging for discovered hosts, allowing connectivity verification without graphic synchronization.

### Telegraphed Enemy Attacks: Combat State Machine & Visual Tells
- **Actor Combat Lifecycle:** Expanded `ActorState` with `WIND_UP`, `STRIKE`, and `RECOVERY`, creating a rhythmic, skill-based combat loop.
- **Visual Stanza Tells:** Implemented pulsing "Margin Red" outlines for wind-ups and solid red flashes for damage frames.
- **Weapon-Specific Indicators:** Added transient white line indicators for 'THRUST' attacks and arc segments for 'SWING' attacks to help player anticipation.
- **Audio Telegraphing:** Hooked `enemy_telegraph.ogg` (shink/glint) into the start of every enemy wind-up.
- **Behavioral Variety:** Balanced unique telegraph and recovery durations for Slugs (slow), Bats (fast), Minibosses (elite), and The Final Author (boss).
- **Non-Weapon Telegraphs:** Ensured that 'Lunge' enemies (Bats, Slugs) have clearly readable attack frames even without held weapons.
- **Combat Stability Fixes:**
    - **Per-Attack Hit Latch:** Implemented `has_hit_this_attack` to prevent enemies from one-shotting players with per-frame damage.
    - **Player i-frames:** Added damage invincibility during the `STAGGERED` and `DASHING` states for fair engagement.

### Frame-Perfect Parry: High-Skill Defensive Combat
- **Active Parry Window:** Implemented a 0.15s (9-frame) window at the start of a `BLOCK` or `DASH`.
- **Damage Negation:** Successful parries reduce incoming damage to 0% and prevent stagger.
- **Enemy Stun:** Parrying an attack triggers a long stagger (0.8s) on the hostile entity.
- **Kinetic Reset:** Instantly resets the player's Dash cooldown upon a successful parry.
- **Visual Feedback:** High-contrast ink spark VFX triggered at the point of impact.
- **Audio Cues:** Integrated `combat_parry.ogg` trigger with OSD logging.
- **Screen Shake:** Brief, intense shake effect to signify a powerful deflection.

### Dynamic Proximity Music & Core SFX Engine
- **Euclidean Engagement Layer:** Overhauled GameState proximity tracking to use 600px Euclidean radius for elite engagement.
- **Temporal Hysteresis:** Implemented a 3.0s temporal cooldown to prevent music jitter when exiting proximity.
- **AudioManager Overhaul:** Refined music transitions to handle intelligent sequential fading for stable track switching.
- **Physical Audio Layer (SFX):** Enhanced AudioManager to support concurrent sound effects with debug tracking and a live OSD.
- **Layered Attack System:** Implemented the 'Layered Attack Rule' where `attack_swing.ogg` triggers on swing and layers with `attack_hit.ogg` on impact.
- **Environmental & System Cues:** Added auditory feedback for acid rain damage (`player_hurt_rain.ogg`), safe circle contraction (`bleed_start.ogg`), and Respite resting (`respite_rest.ogg`).
- **Audio Debug OSD:** Implemented a live on-screen display in the top-left corner to verify music and SFX triggers in real-time.

### The Stanza System: Actor State Machine & Patrols
- **Unified Actor Framework:** Created a base `Actor` class for both Enemies and NPCs, merging movement, state management, and interaction logic.
- **Marker-Based 'Stanza' Patrols:** Implemented an opt-in waypoint system using map symbols '1'-'9'.
- **Grouped Routes:** Supported multiple distinct patrol paths per map via `route_id` grouping.
- **Caste Filtering:** Added type-specific route anchoring, allowing different entities (e.g., Slugs vs. Bats) to follow separate paths.
- **Realism & Nuance:** Implemented randomized wait timers at markers, specialized 'Deep Study' points for NPCs, and 'Dormancy' states for stationary ambushers.
- **Sanctuary Integration:** Coded a research routine for the Chronicler, enabling him to realistically walk between bookcases in the hub world.

### Unified Gamepad Controller Integration & Menu Snapping Logic
- **Joystick Subsystem Initialization:** Initialized `pygame.joystick` and implemented a hardware discovery loop at application startup.
- **Auto Input Mode Switching:** Engineered a seamless transition between Keyboard and Gamepad modes, with real-time HUD feedback.
- **Action Mapping Layer:** Standardized raw controller events into abstract game signals (Attack, Flask, Dash, Swap, Block) for PS5 and SteelSeries profiles.
- **Controller-Driven Menus:** Overhauled the Title, Pause, and Respite menus to support vertical navigation via Analog Sticks and D-pads with precise input ratcheting and temporal debouncing.
- **HUD Indicator:** Added a dynamic input status display to the gameplay interface.

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

## [ARCHIVED] Gated Respite and Rain Close Mechanics - June 2026
- **Gated Respite Loading:** Gated Respite visibility, solidity, and interaction on the `forest` and `ruins` maps so that the Respite anchor does not appear or function until the map's miniboss is defeated.
- **Lore-Accurate Rain Denial:** Prevented Respite interaction if the Respite is being rained on (outside the active safe circle), displaying a lore accurate dialogue message stating that the glyphs are smothered under liquid ink.
- **Instant Weather Closure:** Enforced instant closure of the Respite level-up UI/menu if the active Respite starts getting rained on.
- **Comprehensive Unit Testing:** Implemented custom tests in `tests/test_respite_rain_and_gate.py` verifying correct behavior for gating, other-map immunity, rain interaction blocking, and instant UI closure.

## [ARCHIVED] Proximity-Based Modular Respite Gating - June 2026
- **Proximity-Based Gating:** Refactored Respite gating from static map name filters to dynamic proximity search (5-tile radius) during map parsing, ensuring proper gating of Respite anchors near minibosses in modularly stitched or procedurally generated maps.
- **Dynamic Defeat Syncing:** Stored the gating miniboss ID on the Respite object and updated `GameState.update` to dynamically synchronize Respite active status with the miniboss's entry in `defeated_miniboss_ids`.
- **Modular Test Coverage:** Added unit test `test_respite_gating_modular_proximity` in `tests/test_respite_rain_and_gate.py` to verify correct gating and activation on custom/stitched maps.

## [ARCHIVED] Boss Attack Hitbox Expansion and Visual Cues - June 2026
- **Hitbox Expansion:** Implemented custom attack hitboxes for the `Boss` class (and subclasses like `Miniboss`, `NightBoss`, and `FinalAuthor`), extending the damage reach beyond the boss's physical body during `STRIKE` frames based on facing direction and attack type.
- **Telegraph Warning Zones:** Developed transparent visual overlays on the ground during attacks: a flashing semi-transparent orange zone with an active pulse outline during `WIND_UP` to telegraph the attack, and a bright semi-transparent red zone during `STRIKE` to indicate active damage.
- **Animated Weapon Rendering:** Coded dynamic animated rendering of a giant ink quill weapon held by a limb that thrusts out (for `THRUST` attacks) or swings in a wide arc (for `SWING` attacks), complete with a semi-transparent blue swing trail effect.
- **Hitbox Tests:** Wrote unit tests in `tests/test_boss_hitbox.py` verifying get_attack_hitbox calculations and front-vs-back damage collision logic.

## [ARCHIVED] Map Editor Reference Overlay and Real-Time Brush Details - June 2026
- **Palette Registry Synchronization:** Synchronized the map editor's palette loading dictionary (`MASTER_TOOL_REGISTRY`) to match engine configurations, adding the missing symbols: Lotus Frame (`M`), Wall Boundary (`X`), and The Final Author (`!`).
- **Interactive Multi-Page Help Overlay:** Replaced the static help popup with a larger, tabbed, multi-page reference dialog toggleable via `H` or the sidebar button. Page 1 displays controls, Page 2 lists all tile obstacles and prop sizes/behaviors, and Page 3 lists all enemies, bosses, and patrol waypoint coordinates with collision sizes and behaviors.
- **Tab and Page Navigation:** Implemented page cycling using `A`/`D` or the `Left`/`Right` arrow keys, and mouse-click selection on the tab headers.
- **Real-Time Sidebar Brush Details:** Upgraded the sidebar to fetch the currently selected brush's name, size, and description in real-time, wrapping descriptions cleanly to fit inside the sidebar bounds.

## [ARCHIVED] Active anomalous weapon passives and HUD status indicators - June 2026
- **Global Passive Modifier Accumulation:** Refactored modifier logic to accumulate passives across all owned weapons, allowing effects (HP regen, Max HP boost, damage negation, bleed on hit) to remain active regardless of slot.
- **Player Character Glowing Effect:** Implemented a visual gold shimmer glow overlay and border around the player sprite/ghost when the `NEGATION` (Ward) effect is active.
- **HUD Status Badge Display:** Added dynamic color-coded active status indicators next to status metrics on the HUD panel for `WARD` (damage negation timer/amount), `BOUND` (movement bind status timer), and `REGEN` (passive HP regen rate).
- **Unit Test Coverage:** Updated HP boost unit tests and added `test_inactive_weapon_modifiers` in `tests/test_anomalous_weapon_effects.py` to verify slot-independent passive effect application.

## [ARCHIVED] Sanctuary Level and Stat Reset Restoration - June 2026
- **Level Reset:** Restored the reset of player's Edification level to 1 and attribute stats (`attack_modifier` and `max_hp_modifier` to 0) upon entering the Sanctuary hub.
- **HP Restoration:** Ensured current HP and maximum HP are cleanly reset back to default base stats (`PLAYER_MAX_HP` = 100.0) upon sanctuary entry.
- **Sequence Calibration:** Adjusted the reset order in `on_enter_sanctuary` to reset player stats and weapons *before* setting `self.player.hp` to ensure `self.player.max_hp` matches the default value perfectly.
- **Unit Test Coverage:** Added unit test `test_warp_level_reset` in `tests/test_warp.py` verifying state reset to level 1 and 100 max HP upon warp portal interactions.

## [ARCHIVED] Character Upgrades Inspect View HUD Integration - June 2026
- **Inspect HUD Upgrades Panel:** Upgraded the `inspect_active` view (held `R1` / `TAB`) to render a dedicated "CHARACTER" panel display.
- **Player Stats Display:** Programmed the new panel to detail the player's global `Understanding` (Edification level), `Prowess` level (with raw attack modifier), and `Fortification` level (with raw max HP modifier).
- **Passive Effects & Buffs/Debuffs:** Included tracking of active weapon passive effects (HP regen, Max HP boost, Ward on Hit, Bleed on Hit) and real-time active buff/debuff timers (Ward negation shields, movement binds).
- **Renderer Tests:** Wrote headless unit tests in `tests/test_renderer_inspect_upgrades.py` ensuring correct blit operations and visual labels when inspecting player stats.

## [ARCHIVED] Data-Driven Grass Floor Tile Integration - June 2026
- **Tile Registration:** Registered the new passable "Grass Floor Tile" mapped to tile character "g" and code TILE_GRASS = 12 in constants.py.
- **Pre-Generated Sprites:** Configured the Renderer to load grass_small.png on startup and generate three distinct RAM variants (original, flipped, and programmatically tinted yellow via BLEND_RGBA_MULT).
- **Cluster Spawning Logic:** Implemented randomized cluster generation inside World.generate_grass_decorations() when loading maps, spawning between 2 to 6 grass instances per "g" tile with local offsets of [-12, 12].
- **Map Editor Synchronization:** Registered tile_grass in MASTER_TOOL_REGISTRY inside tools/edit_map.py to maintain synchronization with engine configurations (Palette Divergence Law).
- **Unit Test Coverage:** Wrote tests in tests/test_grass_tile.py verifying grid character mapping, decoration cluster bounds, and rendering safety.

## [ARCHIVED] Procedural Enemy Geometric Graphics - November 2026
- **Procedural Enemy Rendering (`draw_procedural_enemy`):** Replaced placeholder solid rectangles for non-sprite enemies with procedural geometric shapes in `rendering/renderer.py`, matching the Scriptorium Noir enemy design notes.
- **Distinct Enemy Silhouettes & Animations:**
  - **Bat (`BatEnemy`):** Animated flapping wing struts and membrane lobes, round dark body, glowing eyes, and white fangs.
  - **Flutter (`FlutterEnemy`):** Rapidly oscillating cyan paper-wing lobes, parchment scrawl core, and orbiting ink motes.
  - **Bindling (`BindlingEnemy`):** Rounded parchment torso, folded margin hood, diagonal dark ink stitch lines, and a procedural pilcrow (`¶`) sigil.
  - **Smear (`SmearEnemy`):** Amorphous ink blot with four organically wobbling outer lobes and a cyan-ink nucleus tracking the enemy's facing vector.
  - **Bosses & Elites (`Miniboss`, `NightBoss`, `FinalAuthor`):** Hulking armored torso, heavy shoulder pauldrons, dark iron visor plate, and a glowing red eye tracking the facing direction.
- **Combat Telegraph Preservation:** Maintained clear `WIND_UP`, `STRIKE`, and `RECOVERY` color overrides on procedural enemy silhouettes alongside posture and status overlays.
- **Unit Test Coverage:** Added headless unit tests in `tests/test_procedural_enemy_graphics.py` verifying procedural shape generation, telegraph color overrides, and fallback behavior.

## [ARCHIVED] Procedural Scholar Player Character & Tapered Blade Weapons - November 2026
- **Scholar Player Character (`draw_procedural_player`):** Replaced the plain blue rectangle player placeholder with a layered procedural **Scriptorium Scholar** featuring a rounded indigo cloak, azure shoulder mantle with gold stole trim, animated boots during movement, a hood and shadowed cowl with glowing directional eyes, dash speed-streaks, and a raised ward-buckler shield when blocking.
- **Player Sword Attack & Carried Blade (`draw_player_weapon_attack`):** Replaced the 1px green debug attack box with an animated crescent slash trail and a swept tapered sword blade (tinted purple when wielding an Anomalous weapon, or cyan/steel normally), plus a visible sword carried at the Scholar's side when not attacking.
- **Boss Greatblade Upgrade (`draw_boss_weapon`, `_draw_tapered_blade`):** Replaced the paintbrush-like brown shaft and round tip blob on miniboss/boss weapons with a sharp tapered steel greatblade featuring a dark hilt, perpendicular brass crossguard with pommel caps, converging blade edges, and a central fuller groove.

## [ARCHIVED] High-Contrast Procedural Biome Tiles, 2.5D Verticality & Multi-Biome Level Suite - November 2026
- **High-Contrast Procedural Wall & Floor Generation (`_generate_biome_tile_cache`, `_draw_world_tile`):** Implemented procedural multi-variant floor and wall surface generation across five distinct palettes (`BIOME_PALETTES` in `constants.py`: `windy_ridge`, `swamp_mire`, `frozen_peaks`, `tech_tower`, and `sanctuary`) inspired by `docs/reference.md`.
- **2.5D Cliff Verticality & Ambient Occlusion (`docs/level_design_concept.md`):** Added autotiled south-facing cliff/bulkhead wall facades (`wall_front`) vs. rooftop caps (`wall_cap`), paired with north/west ambient occlusion drop-shadows cast onto adjacent floor tiles, animated Lotus-Frame energy conduits (`M`), animated bubbling poison/ink bog pools (`v`), and upgraded environmental props (`Structure`, `Rock`, `Heavy Bookcase`, `Ink Urn`).
- **Four New 120x120 Biome Maps & Two New 40x40 Corridors:** Replaced the `forest`/`ruins` prototype pool in `POOL_MONTHLY_REPORT` and `WorldGenerator` with four macro-shape biome rooms (`maps/windy_ridge.json`, `maps/swamp_mire.json`, `maps/frozen_peaks.json`, `maps/tech_tower.json`) and two new corridors (`maps/gantry_bridge.json`, `maps/mire_causeway.json`), featuring Figure-8 loops, Hourglass choke nodes, Perimeter-and-Core sanctums, safe entrance thresholds, and Typographic Bloom chapter titles.

## [ARCHIVED] Multi-Strata Biome Floors, Environmental Floor Tells & Techno-Sentry Artillery Enemy - November 2026
- **Multi-Strata Non-Uniform Floor Generation (`_generate_biome_tile_cache`, `_decorate_biome_stratum_tile`, `_get_tile_stratum`):** Replaced uniform floor grids with a 3-strata elevation/terrain system per biome (Lowland/Basin/Reactor Trench Grating, Mid-Ground Turf/Deck, and Raised Cobble Path/Timber Boardwalk/Snowdrift/Data-Bus Walkway) driven by a coherent 2D spatial wave field and tile types (`g`/`G`), complete with 2px beveled elevation rims where strata transition.
- **Animated Biome Floor Micro-Effects (`_draw_biome_floor_fx`):** Added live procedural environmental tells to each biome floor: swaying wind-swept grass ribbons on `windy_ridge`, expanding bioluminescent bubble rings in `swamp_mire`, twinkling crystalline frost crosshairs in `frozen_peaks`, and traveling high-voltage reactor pulses in `tech_tower`.
- **Techno-Sentry Enemy (`SentryEnemy`, Symbol `'Y'`):** Implemented a new Anchor/Artillery defense droid (`engine/enemy.py`, `constants.py`, `tools/edit_map.py`, `engine/game_state.py`) that maintains optimal firing spacing, strafes targets, and fires a parryable long-range directional plasma beam (`get_attack_hitbox`, `draw_procedural_enemy`, `draw_boss_weapon`), stationed across tactical choke points and hazard basins in the biome maps.

## [ARCHIVED] Pastoral Valley Biome ("The Scarred Meadow") & Reference 2 Visual Enhancements - November 2026
- **New `pastoral_valley` Biome & 120x120 Map (`maps/pastoral_valley.json`, `BIOME_PALETTES["pastoral_valley"]`):** Preserved `windy_ridge` and added a fifth major biome room (`"THE SCARRED MEADOW"`) to `POOL_MONTHLY_REPORT` inspired by `Reference 2` in `docs/reference.md`.
- **Seamless Lime/Mint Meadow, Warm Tan Pathways & Rounded Contours:** Eliminated square mortar grid borders on `pastoral_valley` floor tiles in favor of solid 2–3 tone horizontal streaks, grouped rounded grass tufts, warm tan earthy pathways, and rounded corner contours that mask tile boundaries without noisy 1px dithering.
- **Stepped Sedimentary Shale Cliffs, Deciduous Tree Crowns & Recessed Tar Swamps:**
  - **Stepped Ridgelines (`wall_front`):** Multi-tiered cliff facades combining flat warm-brown plateau caps, horizontal step ledges, angular slate-gray and brown shale layers, and diagonal sedimentary striations.
  - **Stylized Deciduous Trees (`Structure` / `'T'`):** Short, thick dark-brown trunks with dark outlines, ground cast shadows, overlapping deciduous canopies with bottom-half shadow crescents, and bright lime/mint sunlit crowns.
  - **Recessed Tar / Poison Swamp (`Inkwell Puddle` / `'v'` & `pastoral_valley` Stratum 0):** Visibly recessed near-black inset borders, ragged bruised-purple shorelines, and deep plum toxic pools contrasting against the sunny meadow.

## [ARCHIVED] Procedural Grass Tile Optimization & Pixmap Removal - November 2026
- **Eliminated Per-Tile Grass Pixmap Blitting (`_draw_world_tile`, `_load_grass_assets`):** Removed disk loading and per-frame multi-sprite alpha blitting of `grass_small.png`, `grass_medium.png`, and `grass_tall.png` across `TILE_GRASS` (`g`) and `TILE_THICKET` (`G`) tiles.
- **Pre-Baked Procedural Foliage & Native Display Format Conversion (`_generate_biome_tile_cache`, `_decorate_biome_stratum_tile`):** Baked procedural grass tufts and overgrowth directly into the cached 40x40 `strata_floors` surfaces (and converted cached tile surfaces via `.convert()` when the display is initialized), reducing each `g`/`G` tile from 3–11 alpha blits per frame to a single fast opaque blit.
- **World Load Speedup (`engine/maps.py`):** Removed full-grid `generate_grass_decorations()` passes during `create_world()` on 120x120 and 440x440 maps while retaining prototype compatibility for unit tests.

## [ARCHIVED] Game Engine Revision Save Compatibility System - November 2026
- **Engine Revision Constant (`ENGINE_REVISION = 2` in `constants.py`):** Added a central engine revision identifier to track breaking changes to world layouts, enemy registries, or save schemas.
- **Save Compatibility Gate (`StatisticsTracker.has_compatible_save` & `is_revision_compatible` in `engine/stats.py`):** Configured `StatisticsTracker` to stamp `engine_revision` on new profiles and strip incompatible `run_state` / `active_session_in_progress` data when loading older or unversioned save files.
- **Title Menu & Hydration Enforcement (`main.py`, `engine/game_state.py`, `rendering/renderer.py`):** Updated `TitleMenu` initialization and `New Draft` confirmation in `main.py` to check `StatisticsTracker.has_compatible_save()`, hiding `Continue` (leaving `New Draft` as the starting option) when an older save revision is present, guarding `GameState.hydrate_from_disk()`, displaying the engine revision on the title screen, and stamping `ENGINE_REVISION` once a new draft is started.
- **Unit Test Coverage (`tests/test_engine_revision.py`):** Added unit tests covering fresh tracker revision stamping, legacy/outdated save detection, `TitleMenu` option filtering, and `GameState` revision promotion on starting a new game.

## [ARCHIVED] Chunk-Cached Tilemap Rendering, Spatial Hash Collisions & Pause Menu Debug Text Toggle - November 2026
- **Chunk-Cached World Tilemap & Smooth Panning (`Renderer._get_world_chunk`, `Renderer._draw_static_tile_to_surface` in `rendering/renderer.py`):** Replaced per-frame 627-tile loops (`1,881` trig stratum evaluations and per-tile bevel draws) with lazy `16x16`-tile (`640x640`px) static world chunk surfaces, integer-snapped camera offsets, and smooth wave-based floor strata across `g`/`G` tiles so grass/thicket areas pan with zero 1x1 bevel shimmer and ~6 chunk blits per frame.
- **Viewport Culling, Prop Surface Caching & Weather/Minimap Surface Reuse (`rendering/renderer.py`):** Added camera viewport culling for all `2,046` world interactables, `281` enemies, loot, and debris; pre-baked static `pygame.Surface` sprites (`self.prop_cache`) for trees (`Structure`), tar pools (`Inkwell Puddle`), rocks, bookcases, ink urns, and candelabra glow; cached the static minimap wall layer (`_minimap_walls_surf`); and reused HUD/weather overlay surfaces while skipping full-screen weather blits when no rain particles or barrier arcs intersect the viewport.
- **Spatial Hash Indexing & Idle Network Serialization Guard (`engine/world.py`, `engine/game_state.py`, `engine/network_manager.py`):** Added `160x160`px spatial hash buckets to `World` for O(1) wall, interactable, and hazard puddle queries (eliminating ~570,000 `interactables` iterations per frame during enemy movement) and skipped 20Hz UDP state serialization in `NetworkManager` when no peers are connected.
- **Pause Menu Debug Text Toggle & Save Persistence (`engine/pause_menu.py`, `engine/stats.py`, `engine/game_state.py`, `main.py`, `rendering/renderer.py`, `tests/test_pause_menu.py`):** Added a `Debug Text: OFF/ON` toggle to the Pause Menu (off by default and persisted via `debug_text_enabled` in `save_data.json`), gating in-game and title-screen audio debug announcements (`[ AUDIO_OSD ]`, `SFX:`, `[DEBUG_AUDIO: ...]`), HUD input mode tags (`[ Input: ... ]`), and engine revision debug labels unless enabled.

## [ARCHIVED] Connected Multi-Tile Floor Blending, Perimeter-Only Outlines & Macro-Patterns - November 2026
- **Seamless Connected Floor & Wall Blending (`_generate_biome_tile_cache`, `_draw_connected_wall_tile`, `_get_tile_stratum` in `rendering/renderer.py`):** Removed all 1x1 cell mortar lines and isolated 1x1 inset boxes from floor and wall tiles so adjacent tiles of the same surface merge into continuous, unbroken terrain and cliff plateaus, with 1x1 island suppression in `_get_tile_stratum`.
- **Perimeter-Only Outlines & Rounded Corner Contours (`_draw_stratum_perimeter_borders` in `rendering/renderer.py`):** Added 8-neighbor surface autotiling so transition borders, recessed swamp shorelines, raised pathway bevels, rounded diagonal outer corners, and concave inner corner caps appear strictly along outer edges against different surfaces (`docs/reference.md`).
- **Multi-Tile Connected Shapes & Varied Macro-Patterns (`_draw_connected_floor_patterns` in `rendering/renderer.py`, `tests/test_grass_tile.py`):** Implemented tile-clipped world-space pattern rendering across `4x4`-tile (`160x160`px) macro-contour zones and `2x2`-tile (`80x80`px) connected motifs with 12 pattern combinations per biome and stratum (meadow fairy rings, sweeping turf swells, megalithic sandstone slabs, cart-track ruts, concentric mire vortices, full-span timber boardwalk planks, branching glacial fractures, `80x80`px octagonal techno-hull deck plates, and scriptorium compass/rosette inlays).

## [ARCHIVED] Stylized Combat Particle Effect: Glyph Splatter - November 2026
- **Manuscript Typography Particle System (`engine/particles.py`, `constants.py`):** Created `GlyphSplatterManager` and `GlyphParticle` to spawn bursts of 4 to 7 archaic typographical glyphs (`['†', '‡', '§', '¶', 'ø', '※', '×', '░', '▒']`) on impact instead of generic blood splatters.
- **Physical Trajectory & Clean Evaporation:** Configured initial velocities with random outward angles and slight upward bias (`vx` in `[-2.5, 2.5]`, `vy` in `[-4.0, -1.5]`), gravity (`0.25`/frame), and air friction (`0.94` per frame), with a brief 18–28 frame lifespan (~0.3–0.5s) and linear alpha fade-out across the final 50% of each particle's life.
- **Combat Resolution Integration (`engine/game_state.py`, `engine/player.py`, `engine/enemy.py`, `rendering/renderer.py`):** Wired splatter triggers into damage resolution for enemy impacts (defaulting to dark ink/charcoal or custom entity tints) and player hits (muted parchment white), rendered with a retro monospace manuscript font in `Renderer.draw_glyph_splatter`.
- **Unit Testing Coverage (`tests/test_glyph_splatter.py`):** Added unit tests verifying particle physics, gravity/friction application, linear alpha fade, emission bursts on enemy and player damage, and renderer viewport culling.

## [ARCHIVED] Stylized Layered Title Screen Typography & Ambient Motion - November 2026
- **Layered Composite Typography (`Renderer._get_title_composite` in `rendering/renderer.py`):** Upgraded title screen presentation from flat text to a pre-rendered composite featuring deep drop-shadows (+3/+4 offset doubled blit), 8-direction contrasting edge borders, and two-tone oxidized parchment/gold core lettering.
- **Cinematic Kerning / Letter Tracking:** Added 14px horizontal tracking between characters across "AVOID RAIN" for a wide, deliberate presentation.
- **Ambient Floating Bob & Breathing Pulse (`Renderer.draw_title_screen`):** Implemented gentle sine-wave vertical floating bob (±3px) and subtle breathing pulse (±1.5% scale oscillation) with zero per-frame glyph re-rendering overhead.
- **Unit Testing Coverage (`tests/test_title_rendering.py`):** Added test coverage verifying composite pre-rendering, surface caching, and headless draw loop execution.

## [ARCHIVED] Stylized Transit Sequence: "The Ink & Fog Warp" - November 2026
- **Transition State Controller (`engine/warp_controller.py`, `constants.py`):** Implemented `InkWarpController` with a three-stage non-blocking transition state machine: Stage 1 DEPARTURE (35 frames / ~0.58s), Stage 2 THE VEIL (12 frames / ~0.20s), and Stage 3 ARRIVAL (30 frames / ~0.50s).
- **Dense Fog Cloud & Typographic Manuscript Glyph Swirl:** Created expanding translucent circular/elliptical puffs (`WarpFogPuff`) in soft dark ink `(18, 14, 22)` and muted parchment white `(235, 230, 215)` that rapidly bloom around the player entity during departure, combined with drifting/spiraling typographic manuscript runes (`['†', '‡', '§', '¶', 'ø', '※', '×']`) that scatter upward in departure, and disperse with downward gravity and air friction in arrival while fog patches shrink and evaporate.
- **Player Dissolve & Input Suppression (`engine/game_state.py`, `rendering/renderer.py`):** Fades player sprite alpha linearly from 255 to 0 during departure, maintains invisibility during the veil, restores alpha to 100% during arrival, locks player inputs and movement, and pauses normal enemy/hazard updates across Stages 1 and 2 until the arrival fog clears.
- **Mid-Veil Coordinate Transfer & Camera Snap (`engine/world.py`, `engine/warp_controller.py`):** Fades a full-screen black veil overlay to 100% opacity, executes the physical map/coordinate transfer, snaps the camera instantly to destination player coordinates under the veil, and re-anchors active fog puffs and glyph particles from departure coordinates to arrival coordinates for a seamless reveal.
- **High-Performance Layered Rendering (`rendering/renderer.py`):** Added `Renderer.draw_warp_sequence` drawing fog puffs and runes above the world Y-sort layer with pre-rendered quantized radial gradient puff caching (`_puff_cache`), reusable full-screen veil surfaces (`self.warp_veil_surface`), and offscreen scratch alpha blitting for player dissolves.
- **Unit Testing Coverage (`tests/test_ink_warp.py`, `tests/test_warp.py`):** Added comprehensive unit test coverage testing all 3 transition stages, particle counts/physics, player alpha fades, coordinate re-anchoring, camera snapping, input locking, and renderer caching.

## [ARCHIVED] Procedural PNG Asset Generator Script - November 2026
- **Standalone Offline Procedural Asset Generator (`generate_assets.py`):** Implemented a self-contained, offline PNG asset generator script that procedurally generates grit-textured, dark-fantasy pixel art PNGs without clean geometric primitives.
- **Dirt / Floor Tile Pipeline (`assets/graphics/floor_tile.png` - 40x40):** Generates a desaturated slate-brown/charcoal base tone (`R:45-55, G:40-48, B:35-42`), dense low-contrast per-pixel grit/sand noise (`+/-3` to `+/-8`), 2-5px irregular dark scuffs (`alpha 80-120`), sporadic tiny bright quartz/sand highlights, and subtle 3-pixel perimeter vignette darkening for seamless edge seams.
- **Wall Tile Segment Pipeline (`assets/graphics/wall_tile.png` - 40x40):** Generates heavy slate-blue/grey stone masonry (`R:35-42, G:38-45, B:45-55`) divided into 4 horizontal courses with staggered vertical running bond joints, crumbled 1-2px dark joints (`16, 18, 24`), per-brick facet stone noise and tint variations, 1px top/left warm grey highlights (`66, 72, 82`), and bottom/right recess shadows.
- **Moss / Overgrowth Vegetation Patch Pipeline (`assets/graphics/grass_natural.png` - 40x40 with transparency):** Generates organic foliage patches using multi-seed drifting random-walk silhouettes, dense wobbly scuff clusters, a 3-layer green hierarchy (dark shadow base, rich forest/olive midtone `R:30-48, G:50-70, B:25-45`, and sunlit sage/olive leaf tips), and naturally translucent, rough feathered perimeter pixels for seamless overlapping.
- **Configurable Architecture & Quality Control:** Parameterized all palettes, noise shifts, scuff counts, and output paths at the top of the file; achieved 10.00/10 `pylint` rating and 120-character line length compliance; verified with a dedicated unit test suite in `tests/test_generate_assets.py`.

## [ARCHIVED] Procedural Rock Cluster Asset Pipeline - November 2026
- **Procedural Rock Cluster Generator (`generate_rock_cluster` in `generate_assets.py`):** Implemented a procedural pipeline generating a 40x40 rock cluster asset at `assets/graphics/rock_cluster.png` on a transparent (`pygame.SRCALPHA`) background.
- **Organic Irregular Stone Blobs:** Renders 3–5 rounded stone blobs with randomized polar placement offsets and sinusoidal contour deformation (`1.0 + 0.16*sin(2θ) + 0.12*cos(3θ)`), naturally avoiding geometric circles and ovals.
- **Layered Shading & Directional Lighting:** Renders bottom-edge ground drop shadows (`ROCK_SHADOW_COLOR = (14, 16, 20)`, alpha 140) offset beneath stones, subtle surface grit noise (`±5`), lower-perimeter form shadows, and 1px top-left highlight bevels (`128, 134, 142`) for directional top-down lighting.
- **Pipeline Integration & Testing:** Integrated `rock_cluster` into `generate_all_assets()` and the CLI tool; added unit tests in `tests/test_generate_assets.py` verifying transparency, drop shadow alpha, stone color desaturation, and highlight bevels; confirmed 10.00/10 `pylint` score and green test pass across 199 tests.

## [ARCHIVED] Procedural PNG Tile and Asset Integration - November 2026
- **Procedural Floor Tile RAM Pre-Baking (`Renderer._prebake_floor_variants` in `rendering/renderer.py`):** Pre-bakes 4 subtle variants of `floor_tile.png` into RAM at startup with 90-degree rotations (0°, 90°, 180°, 270°) and brightness shifts (+7%, -6%, +9%) to prevent visual grid tiling and uniform ground patterns.
- **Deterministic Map Floor Variance (`Renderer._draw_static_tile_to_surface`):** Uses a deterministic spatial coordinate hash `((x * 17) ^ (y * 31) ^ (x * y * 7)) % 4` to select from pre-baked floor variants in the static tile rendering pass, replacing procedural geometric shape/flat fill specifically for open floor areas.
- **Wall Tile Masonry Blitting (`Renderer._draw_connected_wall_tile`):** Loads `wall_tile.png` into `Renderer.wall_tile_surf` and blits the textured 4-course slate masonry asset on wall tiles (`TILE_WALL`, `'#'`, `'X'`), replacing procedural geometric rect/line/circle drawing while preserving solid wall collision in `engine/world.py`.
- **Decorative Grass & Rock Layering with Positional Jitter:** Layers `grass_natural.png` on walkable grass and thicket tiles (`TILE_GRASS` `'g'`, `TILE_THICKET` `'G'`) and `rock_cluster.png` on rock tiles (`TILE_OBSTACLE` `'K'`) on top of base floor tiles with deterministic pseudo-random offsets within tile bounds (±4px) to avoid rigid grid alignment.
- **Walkability & Collision Mapping (`engine/world.py`):** Configured `'K'` rock interactables to `is_solid = False` as decorative overlay elements while preserving solid boundary collision on walls (`TILE_WALL`).
- **Comprehensive Test Suite (`tests/test_wired_png_assets.py`):** Added unit test coverage validating startup RAM pre-baking, wall blitting, decorative grass/rock layering, and collision/walkability semantics; verified 100% green pass across all 203 project tests.

## [ARCHIVED] Biome Environment Asset Alignment and Connected Autotiling - November 2026
- **Biome Audit & Scoping (`docs/world_and_lore.md`, `constants.py`, `rendering/renderer.py`):** Audited all defined game biomes (`sanctuary`, `windy_ridge`, `pastoral_valley`, `swamp_mire`, `frozen_peaks`, `tech_tower`). Strictly separated architectural masonry biomes from natural biomes; confirmed and enforced that `swamp_mire` uses organic peat cliff embankments and muddy boundaries rather than stone brick masonry.
- **Generator-Driven Feature Variants (`generate_assets.py`):** Upgraded the offline asset generator to produce generator-driven feature variants baked into 40x40 PNGs:
  - Wall Variants: Standard masonry (`wall_tile.png`), cracked/weathered stone with jagged fissures and chipped edges (`wall_tile_cracked.png`), moss-creeping mortar (`wall_tile_mossy.png`), and corner gossamer spiderwebs with weathered pit pockmarks (`wall_tile_webbed.png`).
  - Biome Natural Surfaces (100% Opaque): Murky swamp water with algae scum patches and emergent reed shoots (`swamp_water.png`), muddy trampled turf with damp silt texture and wet puddles (`mud_turf.png`), fibrous wet peat bank with exposed root filaments (`peat_bank.png`), and organic swamp cliff embankments with sediment strata and overhanging root lips (`swamp_wall.png`).
  - Opaque Base Floors: Ensured all base floor and swamp tiles export with 100% opacity (`alpha=255`), eliminating transparent background checkerboard artifacts.
- **Connected Autotiling & Multi-Tile Footprints (`rendering/renderer.py`):**
  - Continuous Surface Autotiling: Implemented cardinal neighbor-aware autotiling (N, S, E, W, plus diagonals) for continuous surfaces (swamp water, mud turf, peat banks, and cliff embankments) rendering outer rounded corners, cardinal rim transitions, and concave inner corner caps, leaving center fills 100% seamless.
  - Multi-Tile 2x2 Connected Footprints: Added 2x2 connected cluster awareness across matching tiles to apply subtle organic surface variations (duckweed flecks, silt impressions, root threads, and subtle mortar seams) without repeating isolated 1x1 stamps.
  - Biome-Specific Wall Rendering: Replaced global brick blitting with biome-aware wall selection; `swamp_mire` renders organic peat cliff faces (`swamp_wall.png`), masonry biomes deterministically select from feature variants (standard, cracked, mossy, webbed), and `tech_tower` renders dark titanium bulkhead plates.
- **Isolated Render Passes & Geometric Debug Shape Purge (`rendering/renderer.py`):**
  - Render Pass Pipeline: Cleanly isolated tile drawing into 4 sequential passes: Pass 1 (100% opaque base ground fill) -> Pass 2 (Autotiled floor surfaces & multi-tile footprints) -> Pass 3 (Structural walls with collision) -> Pass 4 (Upper decorative grass, rock, and reed overlays with positional jitter).
  - Debug Shape Purge: Fully purged all lingering procedural geometric debug primitives (including the cyan rails `pal["floor_accent"]` in `tech_tower`, 4x4 macro underlay ellipses and polygons, and arbitrary geometric circles/arcs).
  - WIP Biome Fallback: Ensured robust, visually coherent neutral stone fallbacks for undocumented or work-in-progress biomes.
- **Unit Testing Coverage (`tests/test_generate_assets.py`, `tests/test_wired_png_assets.py`, `tests/test_respite_sync.py`):** Added tests verifying wall feature variants, 100% opaque swamp surfaces, swamp wall vs. brick differentiation, and swamp floor pass selection; achieved 100% green pass across all 208 unit tests with 10.00/10 pylint on generator/tests and 9.66/10 on renderer.

## [ARCHIVED] Legacy Biome Floors Restoration & Sanctuary PNG Asset Isolation - November 2026
- **Legacy Procedural Geometric Rendering Restoration (`rendering/renderer.py`):**
  - Restored full legacy procedural geometric floor rendering across all existing biomes (`windy_ridge`, `pastoral_valley`, `tech_tower`, `swamp_mire`, `frozen_peaks`) matching commit `70ed514`.
  - Re-enabled 4x4 macro-zone underlay contours (160x160px continuous contour bands) and 2x2 connected block motifs across matching surfaces for each biome (e.g., pastoral recessed tar/swamp currents and tan sandstone pathways, tech tower reactor trench gratings and data-bus walkways, swamp mire bog shallows and boardwalk planks, frozen peaks mirror-ice fracture networks and snowdrift dunes).
  - Restored 70ed514 legacy connected wall plateaus and 2.5D cliff facades across non-Sanctuary biomes.
- **Sanctuary Biome Asset Isolation (`rendering/renderer.py`, `tests/test_wired_png_assets.py`):**
  - Quarantined newly generated PNG tile assets (`floor_tile.png`, pre-baked variants, `wall_tile.png`, feature variants standard/cracked/mossy/webbed, and autotiling) exclusively to the `sanctuary` biome, serving as the dedicated sandbox/testing grounds.
  - Preserved decorative PNG layering (`grass_natural.png`, `rock_cluster.png`) with positional jitter within Sanctuary.
- **White Background Bleed Elimination:**
  - Diagnosed and resolved the root cause of the white background bleed in Sanctuary: fixed `_prebake_floor_variants` by replacing erroneous `BLEND_RGBA_ADD` of `(255, 255, 255)` with calibrated `BLEND_RGB_ADD` using calculated shift offsets (`add_val = int(255 * brightness_shift)`), ensuring floor variants never clamp to solid white.
  - Forced floor variants to be baked into 100% opaque 24-bit RGB Surfaces (`COLOR_SEPIA_AMBER` base fill) without alpha channels.
  - Guaranteed screen buffer clearing to a solid dark tone every frame (`COLOR_SEPIA_AMBER` for Sanctuary, `COLOR_CHARCOAL` for other biomes) across `render()` and chunk creation.
- **Verification & Testing (`tests/test_wired_png_assets.py`):**
  - Added test coverage verifying legacy procedural rendering preservation in non-Sanctuary biomes, Sanctuary isolation of PNG assets, 100% opacity of floor variants, and zero white bleed on the screen buffer.
  - Verified 100% green pass across all 210 tests in `pytest`; confirmed `pylint` score >= 9.5/10 and 120-character line length compliance.

## [ARCHIVED] Biome Attunement Altar and Expanded Sanctuary Maps - November 2026
- **Procedural Altar Asset (`generate_assets.py`):**
  - Added `generate_attunement_altar()` generating a 40x40 transparent sprite (`assets/graphics/attunement_altar.png`).
  - Features a dark stone stepped pedestal with top-down bevel highlights, ambient bottom drop-shadow, and a glowing
    cyan runic core/dial.
  - Integrated into `generate_all_assets()` and verified with automated test coverage in
    `tests/test_generate_assets.py`.
- **Expanded Sanctuary Variant Maps (`maps/`):**
  - Created four expanded 36x26 Sanctuary map files (`sanctuary_paved.txt`, `sanctuary_geometric.txt`,
    `sanctuary_swamp.txt`, and `sanctuary_ruins.txt`) with 2 tiles of padding buffer around the perimeter.
  - Placed the Attunement Altar entity (`'a'`) at consistent coordinates `(17, 7)` in all four variants, with Player
    Start at `(20, 9)` and other entities cleanly preserved and shifted.
  - Added `'a'` at `(15, 5)` in base `maps/sanctuary.json`.
- **Interactive Altar & Warp Transition (`engine/world.py`, `engine/maps.py`):**
  - Implemented `AttunementAltar(GameObject)` interactable entity that triggers the three-stage cinematic
    `InkWarpController` transit on interaction.
  - Sequentially cycles between the four Sanctuary variants (`sanctuary_paved.txt` -> `sanctuary_geometric.txt` ->
    `sanctuary_swamp.txt` -> `sanctuary_ruins.txt` -> wrap-around).
  - Handles clean world loading, coordinate snapping to player start, camera instant centering, actor route linking,
    and `on_enter_sanctuary()` state purification without state duplication.
- **Biome Tile & Floor Resolution (`rendering/renderer.py`):**
  - Updated `_resolve_tile_biome` so Sanctuary variants dynamically resolve to their matching biome configurations:
    - `sanctuary_geometric` -> `"windy_ridge"` (restores 70ed514 geometric floor rings and patterns)
    - `sanctuary_swamp` -> `"swamp_mire"` (restores organic peat cliffs and bog terrain)
    - `sanctuary_ruins` -> `"tech_tower"` (restores titanium bulkheads and gantry floor plates)
    - `sanctuary_paved` / `sanctuary` -> `"sanctuary"` (PNG tile assets, variants, and autotiling)
  - Loaded `attunement_altar.png` into prop cache and added rendering in `Renderer.render()`.
- **Debug HUD & Room Banner Display (`rendering/renderer.py`):**
  - Rendered `Map: {map_filename}` subtitle directly beneath the Typographic Bloom discovery banner during room entry.
  - Rendered `Map: {map_filename}` indicator on the HUD panel when `debug_text_enabled` is active.
- **Map Editor Synchronization (Palette Divergence Law):**
  - Registered `tile_altar` (`'a'`) in `MASTER_TOOL_REGISTRY` in `tools/edit_map.py` and `TILE_ALTAR = 14` in
    `constants.py`.
- **Comprehensive Testing Suite (`tests/test_attunement_altar.py`):**
  - Added unit tests verifying altar presence in base sanctuary map, expanded dimensions and altar coords in all four
    variants, sequential cycling logic and wrap-around, warp interaction and player transfer, biome resolution, and
    HUD map filename rendering.
  - Maintained 100% green test pass across all 217 tests in `pytest`.

## [ARCHIVED] Map Filename Debug Info Relocated to Persistent Audio/Music HUD - November 2026
- **Room Title Bloom Banner Clean-Up (`rendering/renderer.py`):**
  - Removed map filename subtitle rendering from `draw_bloom_overlay()`, ensuring the typographic discovery banner
    only displays the stylized zone/room name and fades out cleanly according to its standard lifecycle.
- **Persistent Audio / Music HUD Integration (`rendering/renderer.py`):**
  - Relocated the map filename display into `draw_audio_debug()`, rendering directly underneath the music track name
    as the next line (`Map: {map_filename}`).
  - Styled to match the audio OSD font (`hud_font`) and color (`(120, 255, 100)`), centered at the top of the screen.
  - Bound to persistent debug visibility (`debug_text_enabled`), ensuring it stays on screen alongside the music OSD
    rather than fading out with temporary room title banners.
  - Removed previous duplicate map filename rendering from the bottom HUD panel (`draw_hud`).
  - Added surface dimension fallback handling (`hasattr` for `get_width`/`get_rect`) to ensure headless test mocks
    render safely.
- **Testing Verification (`tests/test_attunement_altar.py`):**
  - Updated unit test coverage verifying that `draw_bloom_overlay()` does not contain map filenames, that
    `draw_audio_debug()` renders `Map: {map_filename}` beneath the audio OSD when `debug_text_enabled` is active,
    and that no debug text is rendered when disabled.
  - Maintained 100% green test pass across all 217 tests in `pytest`.



