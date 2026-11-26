# Application Architecture & Engine Lifecycle

This document outlines the high-level execution flow, data schemas, and environmental systems of *Avoid Rain*.

## 1. Core Lifecycle (main.py)
To ensure clean execution and process management, the main entry point follows a structured `try-finally` pattern:
- **Initialization:** Pygame context, screen setup, and core state objects (`GameState`, `Renderer`).
- **Main Loop:** Delta-time (`dt`) calculation, event handling, polling, engine updates, and rendering.
- **Clean Exit:** Mandated `pygame.quit()` and `sys.exit()` in the `finally` block to prevent orphaned processes on Debian Linux.

### 1.1 Command-Line Arguments
The application supports the following flags (`main.py:parse_args()`):
- `--fullscreen`: Launches the game in fullscreen mode. Uses `pygame.SCALED` to automatically maintain the 1280x720 aspect ratio with black letterboxing or pillarboxing as required by the monitor.
- `--offline`: Enforces a strict socket-free `offline_only` lockout across `NetworkManager`, `GameState`, `WarpPortal`, and `TitleMenu` so zero UDP/TCP sockets are opened (avoiding OS firewall prompts).
- Linux desktop launchers (windowed and fullscreen `.desktop` entries) can be generated via `install-linux.py`.

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
- **The Center Anchor:** Upon map generation, each Act's single-biome world assigns one 40x40 inner socket as its Night Boss Arena (`boss_coords_list`). Across a full five-act run (`MAX_ACTS = 5`), Acts 1 through 5 each generate an independent single-biome world with one Night Boss encounter.
- **The Safe Zone Radius:** The engine tracks a float variable: `active_safe_radius`.
- **The Exposure Condition:** During every update frame, the engine calculates the Euclidean distance between the player's position and the active boss center.
  - **Inside Circle:** If `Distance <= active_safe_radius`, the player is safe.
  - **Outside Circle (In The Bleed):** If `Distance > active_safe_radius`, the player is exposed to the ink-storm. They receive damage over time (`2.0`–`4.0` HP/sec scaling per Act via `ACT_SATURATION_MATRIX`) unless standing beneath a protective structure tile (`"T"`).
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

## 5. Physics, Collision & A* Pathfinding Architecture
- **Order of Operations:** 1. Apply Velocity -> 2. Resolve Wall Collisions (AABB) -> 3. Boundary Clamp -> 4. Finalize Coordinates.
- **Normalization:** Movement vectors are normalized to ensure consistent diagonal speed.
- **A* Pathfinding & Stanza Patrols (`engine/pathfinding.py`, `engine/actor.py`):** Corner-safe 8-way A* (`find_path`, `has_line_of_sight`) with bounded search radius (`PATHFINDING_MAX_RADIUS_TILES`), node budget (`PATHFINDING_MAX_NODES`), per-actor repath intervals, and cached solid `GameObject` tile footprints (`get_solid_obstacle_tiles`). Enemies navigate around walls and furniture during `PATROLLING`, `CHASE`, and return-to-patrol transitions (re-anchoring to the nearest `PatrolPoint` on their socket-scoped route after breaking aggro).
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
- **Interaction & Lifecycle Locks:** `Respite.execute_interaction()` blocks opening whenever any alive enemy is within `RESPITE_HOSTILE_BLOCK_RADIUS` (`320.0` px) or actively aggroed, and locks out entirely once a Night Boss spawns (`GameState.night_boss_spawned` or `bleed_state` in `("BOSS_PHASE", "DILUTION", "APPENDIX")`). Opening the Respite menu defers enemy aggro against the resting local player until the menu closes (`GameState.close_respite_menu()`), and warps or storm rain auto-close the menu.
- **Character Restoration:** Resets `player.hp` to `player.max_hp`, refills `player.flask_charges`, triggers `respite_rest.ogg`, and emits a localized `RespiteActivationPulse` typographic bloom around the Respite anchor (plus an unobstructed replay on modal close).
- **World Re-population:** Standard enemy spawners (Z, A, f, b, s, Y, w) are re-instantiated.
- **Elite Exclusion:** Minibosses are never respawned once their unique ID is flagged as defeated in the global session manifest.
- **Progression Unlocking:** Sets `player.has_rested_this_session = True`, enabling the edification menu.

### 2. Edification Leveling (Mark & Finalize Workflow)
Attribute upgrades follow a two-step confirmation process to prevent accidental spending:
- **The Mark Phase:** Player selects an upgrade to "Mark" it for the current session.
- **The Finalize Phase:** Player must navigate to the `[ FINALIZE ]` button to commit the change. 
- **Math Formula:** `Cost = (current_level + 1) * 50` Torn Pages.
- **Stat Categories:** **Edification** (Passive Defense), **Prowess** (`+3 Attack`, `PROWESS_ATTACK_STEP = 3`), and **Fortification** (`+10 Max HP`, `FORTIFICATION_HP_STEP = 10`).
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

### 1. The Dormant Arena Spawning Rule & Proximity Summon Ritual
The `"night_boss"` entity type is strictly restricted from manifesting during run initialization.
- **The Awakening Phase (Proximity-Triggered Summon Eruption):** When the safe circle hits its final `CLAMP` boundary (or for dormant map-placed `Miniboss` / `FinalAuthor` encounters), the engine arms a grey vellum ground ritual circle (`BossSummonManager`). The rising typographic glyph-squares eruption, `boss_summon.ogg` SFX, gamepad rumble (`boss_summon`), delayed boss music drop, and boss emergence hold until an active runner approaches within `BOSS_SUMMON_ERUPTION_RADIUS` (`140.0` px).
- **Biome-Specific Night Bosses (`engine/enemy.py`):** Depending on the Act's biome, the Night Boss manifests as `SlugBoss` (`swamp_mire`), `MeadowCensorBoss` (`pastoral_valley`), `RimecrestArbiterBoss` (`frozen_peaks`), or the canonical `NightBoss`, each featuring multi-phase mechanics and bottom-center Boss HUD tracking (`GameState.get_active_boss_hud_info()`).
- **The Lockdown Rule:** Contraction logic is locked in the closed state while the Night Boss is alive. The radius cannot alter until the boss is defeated.

### 2. 5-Act Unbound Chronicle Progression & The Final Boss Arena
- **Pre-Run 5-of-7 Biome Draft (`open_chronicle_biome_dialog`):** Before launching a run via `WarpPortal`, the player (or Host in Seamless LAN Co-op) selects and orders **5 distinct biomes** out of the 7-biome `CHRONICLE_BIOME_ROSTER` (`windy_ridge`, `pastoral_valley`, `swamp_mire`, `frozen_peaks`, `tech_tower`, `vitreous_basin`, `sunlit_aqueducts`) across `Acts 1..5` (`MAX_ACTS = 5`, `run_biomes = {"act1": ..., ..., "act5": ...}`, `act_worlds: dict[int, dict]`).
- **Act-Keyed Segment Resolution (`resolve_segment_pool`):** `WorldGenerator` resolves `(biome_id, act_number)` via `BIOME_ACT_SEGMENT_POOLS[(biome_id, k)]` walking `k` from `act_number` down to `1`, then `BIOME_SEGMENT_POOLS[biome_id]` across all 7 first-class biomes (with `BIOME_FALLBACK_MAP` retained for unknown aliases) and enforces a normalized `ACT_MINIBOSS_BUDGET = 4` minibosses per Act.
- **Act 1 → Act 5 Synchronized Warp & Saturation Matrix (`ACT_SATURATION_MATRIX`):** Defeating each Act's Night Boss triggers the 10-second **Dilution** interlude, followed by a synchronized Ink & Fog warp (`transition_to_act(next_act)`) into the next Act (`Act 1 -> 2 -> 3 -> 4 -> 5`) with automatic post-Night-Boss full HP restoration (`restore_post_night_boss_hp()`). Acts 1–2 spawn base-tier enemies (`empowered = False`, HP `1.0x`/`1.4x`, Damage `1.0x`/`1.35x`), while Acts 3–5 escalate into empowered/saturated variants (`empowered = True`, HP `2.0x`/`2.8x`/`3.8x`, Damage `1.8x`/`2.35x`/`3.0x`, Speed `1.15x..1.28x`), increasing storm exposure `rain_dps` (`2.0..4.0`) and Torn Page yield multipliers (`1.0x`/`1.25x`/`1.5x`/`1.75x`/`2.0x`). Player progression persists across Act transitions while weather, debris, and enemies reset.
- **Manifestation (Final Boss Arena):** Defeating the Act 5 Night Boss triggers a synchronized warp (with post-Night-Boss full heal) into the expanded **Final Boss Arena** (`maps/night_boss_arena.json`, 72x72 size, `The Final Author`, `FINAL_AUTHOR_MAX_HP = 1600`).
- **The Extraction Sequence:** Upon defeating The Final Author, a 10-second "Dilution" interlude begins. Once the timer hits zero, the player is automatically warped back to the Sanctuary hub.
- **Conclusion:** True victory (`last_run_result = "VICTORY"`, or `"STITCH_VICTORY"` when `story_flags["perfect_stitch_completed"]` is `True`) is achieved only upon successful extraction.

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

## 14. Local Area Network (LAN) Architecture
The engine supports local Wi-Fi co-op sessions using an Authoritative Host / Mirror Client structure (`engine/network_manager.py`).

### 1. Implemented Transport & Synchronization Layer
- **Phase 1: Local Presence & Identity [IMPLEMENTED]**
  - Configurable human-readable `player_name` (`identity`) paired with a unique per-session `peer_id` (`uuid.uuid4().hex[:12]`) so multiple scholars sharing `DEFAULT_PLAYER_NAME` or connecting from `127.0.0.1` never collide in `connected_peers`, `remote_players`, or `session_players`.
  - Background UDP broadcast socket loop announcing JSON `{peer_id, identity}` payloads across the LAN subnet without manual IP input (with plain-text fallback and display-name mapping in `found_hosts[ip]`).
- **Phase 2: Lobby Registration & Connection Handshake [IMPLEMENTED]**
  - Visual Lobby Menu discovering hosts; length-prefixed TCP socket handshake verifying connection state and stopping background discovery threads upon connection.
- **Phase 3: 60 FPS Remote Player Interpolation & Full Rig Rendering [IMPLEMENTED]**
  - Syncs `facing`, player action `state`, equipped `weapon_key`, `swing_seq`, and `in_sanctuary` in the 20 Hz UDP heartbeat and Host `session_players` payload (backward-compatible when omitted).
  - Buffers remote snapshots via `RemotePlayerInterpolator` (~65 ms interpolation delay with bounded `NET_DEAD_RECKONING_MAX_EXTRAPOLATION = 0.12` fallback and teleport/scene snapping) to produce smooth 60 FPS remote movement and velocity-driven walk/attack animations.
  - Filters out peers in a different `in_sanctuary` state (both world rendering and minimap) and renders remote players in the world-actor pass using `Renderer.draw_player_rig()` with their equipped weapon, subtle Cyan (Host) / Magenta (Guest) trim, and nameplate.
- **Phase 4: Authoritative Simulation Sync & Thread-Safe Framing [IMPLEMENTED]**
  - **4-Byte Big-Endian TCP Framing:** All TCP control messages (`HANDSHAKE`, `MAP_REQUEST` / `MAP_RESPONSE`, `UPDATE_FULL_STATE`, `DAMAGE_EVENT`, `HEAL_EVENT`, `RESPITE_ACTION`) use `_send_framed_json()` and `_recv_framed_json()` (`!I` header + exact payload loop, bounded by `MAX_FRAMED_BYTES`) so multi-hundred-kilobyte map payloads never truncate at single-`recv()` boundaries.
  - **Non-Blocking Outbound Reliable Queue:** Client action commands (`send_damage_event`, `send_heal_event`, `send_respite_event`, `send_full_state`) enqueue onto a bounded thread-safe `_outbound_queue` drained by a background TCP worker thread (`_tcp_outbox_loop`) so the 60 FPS main loop never stalls on socket I/O.
  - **Main-Thread Inbox Queue (`drain_network_events`):** Background UDP and TCP listener threads never mutate `GameState`, `World`, `Player`, `WeatherManager`, or entity lists directly. Instead, they push events into a lock-protected `_inbound_queue` drained once per frame at the top of `GameState.update()` via `GameState.drain_network_events()` (including `HOST_DISCONNECT` cleanup after timeout transitions to `OFFLINE`).

### 2. Seamless LAN Co-op Lifecycle [IMPLEMENTED]
- **Title Screen Online/Offline Mode & Name Editing (`online_mode: bool`):**
  - Replaces the manual "Join Game" lobby flow with an **Online / Offline** mode toggle on the Title Screen (`"Mode: Online"` / `"Mode: Offline"`, defaulting to **Online** and persisted in `save_data.json`), and relocates `[N] Change Name` / `player_name` editing onto the Title Screen.
  - **Offline Mode:** Runs purely locally with zero UDP/TCP sockets active.
  - **Online Mode (Single Active LAN Session):** Assumes at most one shared co-op session per local network. Upon entering Sanctuary in Online mode (`GameState.start_seamless_lan()`), the client probes `LAN_PORT` (`55555`) for existing host broadcasts (~1.6s window):
    - If an active Host is discovered on the LAN, automatically connects as a **Client** via framed TCP `HANDSHAKE` and spawns directly into **Sanctuary** alongside connected peers.
    - If no Host is discovered, automatically promotes self to **Host** (`start_hosting()`) and begins broadcasting on `LAN_PORT` (`55555`) immediately from Sanctuary.
    - Resuming a saved mid-run via **Continue** (`GameState.hydrate_from_disk()`) in Online mode resumes as **Host** (`host_in_run = True`, treating new joiners as Waiting Scholars).
  - **Simultaneous Boot Tie-Breaker (`peer_id` arbitration):** An active Host keeps a lightweight `LAN_PORT` (`55555`) listener active so if two Hosts detect each other's UDP broadcasts on the same LAN, the instance with the lexicographically higher `peer_id` yields (`_yield_host_to()`), stops hosting, and connects as a Client to the lower-`peer_id` Host.
- **Sanctuary Staging, Group Run Launch & Waiting Scholars:**
  - **Sanctuary-Only Spawning & Session Persistence:** Newly connecting Clients always spawn into **Sanctuary** (`in_sanctuary: bool`), never mid-run into an active macro-world instance. Returning to Sanctuary in Online mode (`GameState.on_enter_sanctuary()`) preserves the active Host/Client LAN session rather than calling `stop_network()`.
  - **Group Run Launch:** When the Host triggers the `WarpPortal` to start a run, all players currently present in Sanctuary warp into the run together (`GameState.join_host_active_run()`, receiving the Host's framed `MAP_RESPONSE` and initial Act 1 world state).
  - **Mid-Run Joiners ("Waiting Scholars"):**
    - Host `HANDSHAKE` responses and 20Hz UDP snapshots replicate `host_in_run: bool` and `waiting_scholars: int`.
    - When `host_in_run` is `True`, newly joining Clients remain in Sanctuary (`waiting_for_host_run = True`, suppressing `fetch_host_map()` until the Host's party returns and starts a new `WarpPortal` run) and display a HUD banner: *"Waiting for current run to finish..."*.
    - Active players out in the run see a live HUD indicator showing the count of waiting players (e.g., *"1 Scholar waiting in Sanctuary"* / *"N Scholars waiting in Sanctuary"*).
    - Whenever `waiting_scholars > 0`, `PauseMenu` surfaces a **"Return to Sanctuary"** option (`GameState.return_party_to_sanctuary()`) so the active party can cleanly abandon the current run (running standard `on_enter_sanctuary()` purification—resetting Torn Pages, run gear, and modifiers—while keeping the Online LAN session alive) and regroup in Sanctuary with the waiting players.
- **Disruptive Host Promotion on Disconnect:**
  - If the Host disconnects or times out (`HOST_DISCONNECT`), surviving Clients do not get kicked to the title screen:
    - Clients retain the latest `session_players` `peer_id` roster (`last_survivor_peer_ids`) across the disconnect frame so all survivors agree deterministically on promotion order.
    - All surviving Clients warp back to **Sanctuary** (cleaning up active run state).
    - The surviving Client with the lexicographically lowest `peer_id` automatically promotes itself to **Host** (`start_hosting()`), while any other surviving Clients reconnect to the newly promoted Host in Sanctuary.

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

## 16. Marginalia Event Engine (`engine/marginalia_events.py`)
The Marginalia Event Engine coordinates mid-run dynamic encounters, boons, and pocket sub-arenas across all run Acts (`current_act in 1..5`, using Act 1 base variants in Act 1 and escalated Act 2 variants in Acts 2–5).

### 1. Per-Act Roll & Trigger Gating
- **Roll Frequency:** Rolls a **20% trigger chance once per Act** (`MARGINALIA_TRIGGER_CHANCE = 0.20`, maximum 1 event per Act).
- **Storm Contraction Gate:** Events may only roll or activate while `weather_manager.current_step_idx < 2` and `weather_manager.bleed_state not in ("BOSS_PHASE", "DILUTION")`.
- **Weather Lock (`WeatherManager.paused`):** While an event is `ACTIVE`, `weather_manager.paused` is set to `True`, freezing `grace_timer` and contraction `timer` progression and suppressing rain exposure damage (`player.is_exposed = False`). `paused` is restored to `False` immediately upon event completion, failure, or Sanctuary return.

### 2. Unified State Schema, Spatial Modes & LAN Sync
- **Shared Event Contract (`MarginaliaEvent`):** Exposes `event_id`, `act_variant` (`1` or `2`), `trigger_mode` (`"auto_safe_zone"` | `"prop_strike"` | `"pitfall_warp"` | `"hunt_timer"`), `spatial_mode` (`"local"` | `"map_anchor"` | `"global_pursuit"`), `time_remaining`, `progress`, and `status` (`"PENDING"` | `"ACTIVE"` | `"COMPLETED"` | `"FAILED"`).
- **Sub-Arena Pitfall & Return Stack (`ReturnAnchor` / `ExitLadder`):** Stepping onto a disguised `PitfallTrigger` (`"Suspicious Leaf Pile"`) pushes `ReturnAnchor(map_path, x, y)` onto `GameState.return_anchor_stack` and warps the party into `"ink_well_cellar"`. Clearing the cellar spawns an `ExitLadder` that pops the `ReturnAnchor` and returns the party to the saved overworld coordinates.
- **Breadcrumb Pursuit (`Enemy.persistent_pursuit`):** Global pursuit hunters (`"relentless_censor"`) track `GameState.player_breadcrumbs` with A* detours within local range and a brief wall-phase fallback if stalled against geometry.
- **Respite Anti-Farming & Economy Rules:** Consumed `map_anchor` events remain consumed across `Respite.execute_rest()` for the remainder of that Act. All Torn Page rewards/penalties mutate the single active run pool (clamped `>= 0`, resetting to `0` on Sanctuary return), events never grant direct Edification level-ups outside Respite Rest, and weapon rewards obey the two-slot Full-Cradle Rule.
- **LAN Co-op Replication:** Host serializes `marginalia_event` and `weather.paused` in 20Hz UDP snapshots to active runner Clients (excluding Waiting Scholars in Sanctuary with `in_sanctuary == True`), and Client `DAMAGE_EVENT` barrel strikes trigger `prop_strike` mimic awakenings on the Host.

## 17. Binder Scripts, Atmospheric VFX & Haptic Feedback
- **Binder Scripts Compiler (`engine/binder_scripts.py`):** **The Binder** (`'&'` in `maps/sanctuary.json`) weaves persistent Scripts into up to `BINDER_MAX_EQUIPPED_SCRIPTS = 4` slots using persistent `margin_scraps`. `compile_binder_scripts()` resolves syntax conflicts when multiple equipped scripts alter the same stat (stronger magnitude wins `ACTIVE`; weaker fails `CONFLICTED` with `0` effect). Recording the ordered 3-stat conflict sequence (`max_hp -> attack -> damage_mitigation`) sets `story_flags["perfect_stitch_completed"] = True`, unlocking the alternate `"STITCH_VICTORY"` (`"THE INK-BLEED HALTED"`) ending.
- **Decoupled Atmospheric Micro-Animations (`constants.py`, `engine/particles.py`, `engine/menu.py`):**
  - **Enhanced Death Sequence (Text Bleaching):** `compute_death_bleach_state()` drives progressive luminance desaturation, subtle camera pull-back into a manuscript margin, rising parchment washout/vignette, and staged `"TEXT BLEACHING..."` typographic fade-in.
  - **Respite Activation Pulse:** `RespitePulseManager` spawns dt-scaled expanding cyan-ink/parchment rings and drifting glyphs around the Respite anchor on rest (and clears on warp/Sanctuary transitions).
  - **Tactile Menu Transitions:** `compute_menu_transition_state()` and `MenuBase.update_transition(dt)` drive non-blocking parchment unroll and vertical-slide animations across Title, Pause, Confirm, and Controls views.
- **Gamepad Rumble Queue (`GameState.trigger_rumble()`, `main.py:dispatch_gamepad_rumble()`):** Priority-ordered rumble impulses (`combat_hit`, `player_damage`, `parry`, `boss_summon` via `RUMBLE_PRESETS` in `constants.py`), gated by persisted `rumble_enabled` and safely dispatched to `Joystick.rumble()` outside `engine/`.
