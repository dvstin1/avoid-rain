# Application Architecture & Engine Lifecycle

This document outlines the high-level execution flow, data schemas, and environmental systems of *Avoid Rain*.

## 1. Core Lifecycle (main.py)
To ensure clean execution and process management, the main entry point follows a structured `try-finally` pattern:
- **Initialization:** Pygame context, screen setup, and core state objects (`GameState`, `Renderer`).
- **Main Loop:** Delta-time (`dt`) calculation, event handling, polling, engine updates, and rendering.
- **Clean Exit:** Mandated `pygame.quit()` and `sys.exit()` in the `finally` block to prevent orphaned processes on Debian Linux.

### 1.1 Command-Line Arguments
The application supports the following flags:
- `--fullscreen`: Launches the game in fullscreen mode. Uses `pygame.SCALED` to automatically maintain the 1280x720 aspect ratio with black letterboxing or pillarboxing as required by the monitor.

## 2. Decoupled Directory Structure
- `engine/`: **Pure Logic.** No Pygame imports. Contains state management, physics, combat, and world generation.
- `rendering/`: **Visuals.** Handles drawing, camera offsets, and sprite management.
- `ui/`: **Interface logic.** Contains specialized menu components and HUD overlay logic.
- `maps/`: **Assets.** JSON definitions for rooms, corridors, and the macro-world.
- `tools/`: **Utilities.** Includes the native map editor (`edit_map.py`).
- `tests/`: **Verification.** Pytest suite for engine logic and regression testing.
- `constants.py`: **Central Registry.** All magic numbers and configuration must reside here.

## 3. State Schema (The Single Source of Truth)
The `GameState` object manages the following data structures:
- **PlayerState:** Position, velocity, HP, flask charges, active weapon stats, and animation state (IDLE, ATTACKING, etc.).
- **RainState:** Center coordinates, active radius, and shrink rate.
- **WorldState:** Chapter ID, active modular sections, story flags, and respawn anchors.
- **Persistence Snapshot:** Lifetime metrics, discovered bestiary, and serialized `run_state`.

## 4. Climate Engine: The Bleed (The Redacting Circle)
"The Bleed" is a spatial contraction mechanic that shrinks a designated safe perimeter down toward a sequence of Night Boss Arenas.

### 1. Radial Proximity Math
- **The Center Anchor:** Upon map generation, each Act's single-biome world assigns one 40x40 inner socket as its Night Boss Arena (`boss_coords_list`). Across a full two-act run, Act 1 and Act 2 each generate an independent single-biome world with one Night Boss encounter.
- **The Safe Zone Radius:** The engine tracks a float variable: `active_safe_radius`.
- **The Exposure Condition:** During every update frame, the engine calculates the Euclidean distance between the player's position and the active boss center.
  - **Inside Circle:** If `Distance <= active_safe_radius`, the player is safe.
  - **Outside Circle (In The Bleed):** If `Distance > active_safe_radius`, the player is exposed to the ink-storm. They receive damage over time (2 HP/sec) unless standing beneath a protective structure tile (`"T"`).
- **Non-Staggering Damage:** Environmental hazard damage bypasses standard combat hit-reactions. Health is decremented directly without altering the player's state or movement velocity.

### 2. The Contraction Lifecycle (Three-Step Protocol)
The circle contraction does not crawl incrementally. It operates strictly across three distinct milestones:
- **Initialization:** Safe radius starts at maximum scale (**620 tiles**), leaving the entire 440x440 grid clear during the initial 60-second grace period.
- **Step 1 (The First Contraction):** Radius shrinks smoothly down to **300 tiles**, then pauses for 40 seconds.
- **Step 2 (The Second Contraction):** Radius shrinks smoothly down to **120 tiles**, then pauses for 40 seconds.
- **Step 3 (The Final Collapse):** Radius contracts to exactly **40 tiles**, locking over the Night Boss Arena and triggering the boss spawn.

### 3. Act III: The Dilution (Victory Window)
Upon defeating a Night Boss, "The Bleed" enters the **Dilution** phase.
- **Environmental Shift:** Toxic rain turns blue and harmless for 10 seconds.
- **Cycle Reset:** If a second boss is queued, the circle resets to max radius and begins the descent cycle for the new target coordinates.

### 4. Hub Isolation Rules
The weather system state machine, particle calculations, and damage logic are strictly decoupled from the hub map.
- **The Hub Gate:** If the current map identifier equals `"sanctuary"`, the weather update thread exits immediately. The system remains completely dormant while the player is inside the hub.

## 5. Physics & Collision Architecture
- **Order of Operations:** 1. Apply Velocity -> 2. Resolve Wall Collisions (AABB) -> 3. Boundary Clamp -> 4. Finalize Coordinates.
- **Normalization:** Movement vectors are normalized to ensure consistent diagonal speed.
- **Soft-Body Repulsion:** Mobile entities (Player/Enemies) calculate separation vectors upon overlap to prevent graphic clipping.
- **Global Coordinates:** Collision subroutines evaluate position against the master 440x440 grid. Local module boundaries must be passed seamlessly.

## 6. Combat Logic & Hitbox Rules
- **Visual-Aligned Hitbox Geometry:** Calculated based on player center and facing vector using `get_sword_hitbox()`. Generates dynamic bounding boxes covering the full 120-degree crescent sweep arc (`SWORD_ARC_RADIANS = 2.10`, `SWORD_REACH = 64.0` px) for cardinal, diagonal, and arbitrary facing vectors without collapsing diagonal hits into narrow strips.
- **Two-Phase Resolution:** Damage resolution uses `check_sword_hit()` in `GameState.update_combat()`, combining fast AABB bounding box rejection with angular sector and radial reach tests against target rectangles. Point-blank enemies and off-axis enemies sweeping through the slash arc take damage accurately.
- **The Layered SFX Rule:** To maximize tactile feedback, initiating a slash plays `sword_swing.ogg` (with subtle pitch variance), and landing a hit plays `sword_hit.ogg` once per swing (capped to a single layered impact even when cleaving multiple enemies). A "whiff" only triggers `sword_swing.ogg`.

## 7. Map Topography: The Unit Grid Canvas
The world is a massive $440 \times 440$ tile grid assembled from an $11 \times 11$ unit matrix.
- **Room Nodes:** $120 \times 120$ tiles (3x3 units). Reserved for high-density exploration and combat.
- **Corridor Slots:** $40 \times 40$ tiles (1x1 units). Connect Room Nodes.
- **Proximity Route Discovery:** Actors (Enemies/NPCs) automatically anchor to waypoints (`1`-`9`) if detected within a **20-tile radius** at spawn.
- **Stanza Formation:** Markers are grouped by `route_id`. If no ID is provided, the engine recursively builds a spatially connected chain of nearby markers.
- **Perimeter Passability:** Local sub-map modules must not append colliders to their outer frame edges, allowing fluid traversal between adjacent nodes.

## 8. State Hooks: Modular Cleansing
- **Kill-Signal:** Defeating a Miniboss broadcasts a `SIG_CLEANSE_MODULE` event.
- **Cleansing Effect:** Toggles the socket's `is_cleansed` flag, materializes a dormant `RespiteAnchor`, and permanently suppresses enemy respawns in that region.

## 9. Respite Interaction State Machine & Edification Math

To facilitate long-term progression, the engine implements a "Resting" loop and a persistent leveling system (Edification).

### 1. The Resting Loop (engine/world.py)
Interacting with an unlocked `Respite` object triggers the `execute_rest()` sequence:
- **Character Restoration:** Resets `player.hp` to `player.max_hp`, refills `player.flask_charges`, and triggers `respite_rest.ogg`.
- **World Re-population:** Standard enemy spawners (Z, A, f, b, s) are re-instantiated.
- **Elite Exclusion:** Minibosses are never respawned once their unique ID is flagged as defeated in the global session manifest.
- **Progression Unlocking:** Sets `player.has_rested_this_session = True`, enabling the edification menu.

### 2. Edification Leveling (Mark & Finalize Workflow)
Attribute upgrades follow a two-step confirmation process to prevent accidental spending:
- **The Mark Phase:** Player selects an upgrade to "Mark" it for the current session.
- **The Finalize Phase:** Player must navigate to the `[ FINALIZE ]` button to commit the change. 
- **Math Formula:** `Cost = (current_level + 1) * 50` Torn Pages.
- **Stat Categories:** **Edification** (Passive Defense), **Prowess** (+5 Attack), and **Fortification** (+10 Max HP).
- **The State Lock:** Each purchase resets `has_rested_this_session = False`. To edify again, the player must commit to a fresh Rest action.

### 3. Conditional Defensive Parsing (engine/player.py)
- **Pristine Concentration:** If `HP > 95%`, damage reduced by `(Edification / 2)%`.
- **Desperate Synthesis:** If `HP < 30%`, damage reduced by `(Edification)%`.

## 10. UI Overlay Constraints & Input Ratchet Specifications

### 1. Input Ratchet (Debounce State Machine)
- **Latched State:** Maintain `input_ratchet_latched = True` upon processing a discrete action (e.g., purchase).
- **Reset:** The latch is cleared only when receiving a native `KEYUP` or `MOUSEBUTTONUP` signal.

### 2. HUD Scaling Standards
- **Typography Alignment:** Status metrics (`HP`, `Flasks`, `Pages`) must utilize the compact 14pt font assets to match action prompts.

## 11. Boss Lifecycle Sequencing & Spawning Laws

### 1. The Dormant Arena Spawning Rule
The `"night_boss"` entity type is strictly restricted from manifesting during run initialization.
- **The Awakening Phase:** The boss manifests at its arena center the exact frame the safe circle hits its final `CLAMP` boundary.
- **The Lockdown Rule:** Contraction logic is locked in the closed state while the Night Boss is alive. The radius cannot alter until the boss is defeated.

### 2. Two-Act Progression & The Final Boss Arena
- **Act 1 → Act 2 Synchronized Warp & Escalation:** Defeating the Act 1 Night Boss triggers the 10-second **Dilution** victory beat, followed by a synchronized Ink & Fog warp (host & LAN clients) into the pre-generated Act 2 single-biome world (`current_act = 2`, `empowered_act = True`). Entering Act 2 triggers a full-width escalation banner (`ACT2_ESCALATION_BANNER`) and `bleed_start.ogg`, and scales all Act 2 enemies, the Act 2 Night Boss, and The Final Author by `2.0x` max HP and `2.0x` attack damage with empowered visual variants. Player progression (HP, max HP, flasks, stats/level, weapons, torn pages) persists across the transition while weather, debris, and enemies reset.
- **Manifestation (Final Boss Arena):** Defeating the Act 2 Night Boss triggers a synchronized warp into the expanded **Final Boss Arena** (`maps/night_boss_arena.json`, 72x72 size, `The Final Author`).
- **The Extraction Sequence:** Upon defeating The Final Author, a 10-second "Dilution" interlude begins. Once the timer hits zero, the player is automatically warped back to the Sanctuary hub.
- **Conclusion:** True victory (`last_run_result = "VICTORY"`) is achieved only upon successful extraction.

## 12. Hub Persistence Boundaries & State Purification

### 1. The Sanctuary Persistence Rule (The Blank Slate)
The Sanctuary hub world acts as a definitive state purifier. 
- **Purification Pass:** Entering the hub (via victory or death) forces `edification_level` to 1, resets Pages to 0, restores HP/Flasks, and wipes exposure status.
- **Weather Reset:** Resets the weather state machine to `GRACE_PERIOD`.
- **File Persistence:** Session data is written to `~/.config/avoid_rain/save_data.json`. The hub bypasses the `in_progress` restriction, allowing players to Resume directly in the Scriptorium.

## 13. Actor Intelligence: The Stanza System
A unified behavior framework for all mobile entities (Enemies and NPCs).

### 1. Unified State Machine
Actors cycle between logic states based on environmental triggers:
- **IDLE:** Standing at post or wandering.
- **PATROLLING:** Moving between sequential markers in a "Stanza" chain.
- **CHASE:** High-velocity pursuit of the player (Enemies only).
- **ENGAGED:** Movement paused for active interaction/dialogue (NPCs only).

### 2. Caste Filtering
Individual markers can be restricted to specific actor types (e.g., `["Chronicler"]` or `["SlugEnemy"]`). Actors will ignore any markers that do not match their assigned caste.

### 3. Realism Nuance
- **Stanza Speed:** Actors use `0.5x` speed during patrols to simulate walking.
- **Wait Timers:** Upon reaching a marker, actors roll a randomized wait duration (`2s-6s` default) before proceeding to the next waypoint.
- **Dormancy:** Entities flagged with `is_stationary: True` ignore all patrol logic and remain "sleeping" until player detection.

### 2. Minimap Rendering Order
To prevent canvas blackouts, the minimap must adhere to a strict pipeline:
1. **Clear Surface:** `.fill()` with base background tone.
2. **Sub-Surface Blit:** Draw tiles and entities using strict integer casting and boundary clamping.
3. **Primary Blit:** Execute `main_screen.blit(minimap_surface, destination_rect)`.

## 14. Local Area Network (LAN) Architecture
The engine supports local Wi-Fi co-op sessions using an Authoritative Host / Mirror Client structure (`engine/network_manager.py`).

### 1. Implemented Transport & Synchronization Layer
- **Phase 1: Local Presence & Identity [IMPLEMENTED]**
  - Configurable human-readable `player_name` (`identity`) paired with a unique per-session `peer_id` (`uuid.uuid4().hex[:12]`) so multiple scholars sharing `DEFAULT_PLAYER_NAME` or connecting from `127.0.0.1` never collide in `connected_peers`, `remote_players`, or `session_players`.
  - Background UDP broadcast socket loop announcing JSON `{peer_id, identity}` payloads across the LAN subnet without manual IP input (with plain-text fallback and display-name mapping in `found_hosts[ip]`).
- **Phase 2: Lobby Registration & Connection Handshake [IMPLEMENTED]**
  - Visual Lobby Menu discovering hosts; length-prefixed TCP socket handshake verifying connection state and stopping background discovery threads upon connection.
- **Phase 3: Ghost Client State Replication [IMPLEMENTED]**
  - Renders non-local client players as text-tagged coordinate clones with host/client color differentiation driven by peer metadata (`is_host` / `addr`).
- **Phase 4: Authoritative Simulation Sync & Thread-Safe Framing [IMPLEMENTED]**
  - **4-Byte Big-Endian TCP Framing:** All TCP control messages (`HANDSHAKE`, `MAP_REQUEST` / `MAP_RESPONSE`, `UPDATE_FULL_STATE`, `DAMAGE_EVENT`, `HEAL_EVENT`, `RESPITE_ACTION`) use `_send_framed_json()` and `_recv_framed_json()` (`!I` header + exact payload loop, bounded by `MAX_FRAMED_BYTES`) so multi-hundred-kilobyte map payloads never truncate at single-`recv()` boundaries.
  - **Non-Blocking Outbound Reliable Queue:** Client action commands (`send_damage_event`, `send_heal_event`, `send_respite_event`, `send_full_state`) enqueue onto a bounded thread-safe `_outbound_queue` drained by a background TCP worker thread (`_tcp_outbox_loop`) so the 60 FPS main loop never stalls on socket I/O.
  - **Main-Thread Inbox Queue (`drain_network_events`):** Background UDP and TCP listener threads never mutate `GameState`, `World`, `Player`, `WeatherManager`, or entity lists directly. Instead, they push events into a lock-protected `_inbound_queue` drained once per frame at the top of `GameState.update()` via `GameState.drain_network_events()` (including `HOST_DISCONNECT` cleanup after timeout transitions to `OFFLINE`).

### 2. Seamless LAN Co-op Lifecycle (Proposed)
> **STATUS:** Proposed Architecture (See `docs/backlog.md` Section 11). All new state fields and menu transitions below are marked `(proposed)`.

- **Title Screen Online/Offline Mode & Name Editing (`online_mode: bool`, proposed):**
  - Replaces the manual "Join Game" lobby flow (`TitleMenuState.LOBBY` / `ui/lobby_menu.py`) with an **Online / Offline** mode toggle on the Title Screen (defaulting to **Online**), and relocates `[N] Change Name` / `player_name` editing onto the Title Screen when `LOBBY` is removed.
  - **Offline Mode:** Runs purely locally with zero UDP/TCP sockets active.
  - **Online Mode (Single Active LAN Session):** Assumes at most one shared co-op session per local network. Upon entering Sanctuary in Online mode, the client probes `LAN_PORT` (`55555`) for existing host broadcasts (~1.5–2.0s window):
    - If an active Host is discovered on the LAN, automatically connect as a **Client** via framed TCP `HANDSHAKE` and spawn directly into **Sanctuary** alongside connected peers.
    - If no Host is discovered, automatically promote self to **Host** (`start_hosting()`) and begin broadcasting on `LAN_PORT` (`55555`) immediately from Sanctuary.
    - Resuming a saved mid-run via **Continue** (`GameState.hydrate_from_disk()`) in Online mode resumes as **Host** (`host_in_run = True`, `(proposed)`, treating new joiners as Waiting Scholars).
  - **Simultaneous Boot Tie-Breaker (`peer_id` arbitration, proposed):** An active Host keeps a lightweight `LAN_PORT` (`55555`) listener (or periodic probe) active so if two Hosts detect each other's UDP broadcasts on the same LAN, the instance with the lexicographically higher `peer_id` yields, stops hosting, and connects as a Client to the lower-`peer_id` Host.
- **Sanctuary Staging, Group Run Launch & Waiting Scholars (proposed):**
  - **Sanctuary-Only Spawning & Session Persistence:** Newly connecting Clients always spawn into **Sanctuary** (`in_sanctuary: bool`, `(proposed)`), never mid-run into an active macro-world instance. Returning to Sanctuary in Online mode (`GameState.on_enter_sanctuary()`) preserves the active Host/Client LAN session rather than calling `stop_network()`.
  - **Group Run Launch:** When the Host triggers the `WarpPortal` to start a run, all players currently present in Sanctuary warp into the run together (receiving the Host's framed `MAP_RESPONSE` and initial Act 1 world state).
  - **Mid-Run Joiners ("Waiting Scholars"):**
    - Host `HANDSHAKE` responses and 20Hz UDP snapshots replicate `host_in_run: bool` `(proposed)` and `waiting_scholars: int` `(proposed)`.
    - When `host_in_run` is `True`, newly joining Clients remain in Sanctuary (suppressing `fetch_host_map()` until the Host's party returns and starts a new `WarpPortal` run) and display a HUD banner: *"Waiting for current run to finish..."*.
    - Active players out in the run see a live HUD indicator showing the count of waiting players (e.g., *"1 Scholar waiting in Sanctuary"* / *"N Scholars waiting in Sanctuary"*).
    - Whenever `waiting_scholars > 0` `(proposed)`, `PauseMenu` surfaces a **"Return to Sanctuary"** `(proposed)` option so the active party can cleanly abandon the current run (running standard `on_enter_sanctuary()` purification—resetting Torn Pages, run gear, and modifiers—while keeping the Online LAN session alive) and regroup in Sanctuary with the waiting players.
- **Disruptive Host Promotion on Disconnect (proposed):**
  - If the Host disconnects or times out (`HOST_DISCONNECT`), surviving Clients do not get kicked to the title screen:
    - Clients retain the latest `session_players` `peer_id` roster across the disconnect frame so all survivors agree deterministically on promotion order.
    - All surviving Clients warp back to **Sanctuary** (cleaning up active run state).
    - The surviving Client with the lexicographically lowest `peer_id` automatically promotes itself to **Host** (`start_hosting()`), while any other surviving Clients reconnect to the newly promoted Host in Sanctuary within one discovery cycle.

## 15. Layered Visual System (Ghost Indicators)
A decoupled animation architecture that translates internal state flags into composable visual "intents."

### 1. The Visual Packet
Every mobile entity (`Actor`, `Player`) implements `get_visual_packet()`, which returns a schema including:
- **Base:** The primary animation (IDLE, RUN, ATTACK, DASH).
- **Posture:** Physical transformations (WOUNDED squashing, STAGGERED vibration).
- **Overlays:** Status effect indicators (BIND vines, EXPOSED shimmer, PARRY glow).
- **Metadata:** Facing vectors and combat progress timers.

### 2. Composable Rendering
The `Renderer` consumes these packets to draw **"Ghost Indicators"**—abstract representations that provide full tactical feedback without requiring finalized sprite assets.
- **Composition Rule:** Postures (squash/stretch) are applied first, followed by the base body color, then overlays and progress bars are layered on top.
