# Application Architecture & Engine Lifecycle

This document outlines the high-level execution flow, data schemas, and environmental systems of *Avoid Rain*.

## 1. Core Lifecycle (main.py)
To ensure clean execution and process management, the main entry point follows a structured `try-finally` pattern:
- **Initialization:** Pygame context, screen setup, and core state objects (`GameState`, `Renderer`).
- **Main Loop:** Delta-time (`dt`) calculation, event handling, polling, engine updates, and rendering.
- **Clean Exit:** Mandated `pygame.quit()` and `sys.exit()` in the `finally` block to prevent orphaned processes on Debian Linux.

## 2. Decoupled Directory Structure
- `engine/`: **Pure Logic.** No Pygame imports. Contains state management, physics, combat, and world generation.
- `rendering/`: **Visuals & Input.** Handles drawing, camera offsets, and mapping raw input to engine actions.
- `constants.py`: **Central Registry.** All magic numbers and configuration must reside here.

## 3. State Schema (The Single Source of Truth)
The `GameState` object manages the following data structures:
- **PlayerState:** Position, velocity, HP, flask charges, active weapon stats, and animation state (IDLE, ATTACKING, etc.).
- **RainState:** Center coordinates, active radius, and shrink rate.
- **WorldState:** Chapter ID, active modular sections, story flags, and respawn anchors.
- **Persistence Snapshot:** Lifetime metrics, discovered bestiary, and serialized `run_state`.

## 4. Climate Engine: The Bleed (The Redacting Circle)
"The Bleed" is a spatial contraction mechanic that shrinks a designated safe perimeter down toward the Night Boss Arena.

### 1. Radial Proximity Math
- **The Center Anchor:** Upon map generation, the engine registers the center coordinates of the Night Boss module: `(center_x, center_y)`.
- **The Safe Zone Radius:** The engine tracks a float variable: `active_safe_radius`.
- **The Exposure Condition:** During every update frame, the engine calculates the Euclidean distance between the player's position and the boss center:
  - **Inside Circle:** If `Distance <= active_safe_radius`, the player is safe.
  - **Outside Circle (In The Bleed):** If `Distance > active_safe_radius`, the player is exposed to the ink-storm. They receive damage over time (2 HP/sec) unless standing beneath a protective structure tile (`"T"`).

### 2. The Step-Contraction Lifecycle
The safe circle progresses through sequential stages:
- **Phase 1: Static (Wait):** Radius is fixed at maximum scale (e.g., 8000 pixels).
- **Phase 2: Collapsing (Contract):** Radius linearly interpolates downward toward a target interval value.
- **Phase 3: Finality (Clamp):** The radius clamps permanently at a radius matching the Night Boss Arena boundaries (approx. 800 pixels).

## 5. Physics & Collision Architecture
- **Order of Operations:** 1. Apply Velocity -> 2. Resolve Wall Collisions (AABB) -> 3. Boundary Clamp -> 4. Finalize Coordinates.
- **Normalization:** Movement vectors are normalized to ensure consistent diagonal speed.
- **Soft-Body Repulsion:** Mobile entities (Player/Enemies) calculate separation vectors upon overlap to prevent graphic clipping and maintain combat readability.

## 6. Combat Logic & Hitbox Rules
- **Relative Hitboxes:** Calculated based on player center and cardinal facing direction (e.g., $60 \times 20$ for horizontal swings).
- **Resolution:** Damage is applied to all enemies overlapping the active sword hitbox during the `ATTACKING` state.

## 7. Map Topography: The Radiant Lotus Wheel
The world is a massive $120 \times 120$ tile grid designed to prevent traversal traps.
- **The Central Well:** Large open plaza for final stand-offs.
- **The Tissue (Spokes):** Multi-tile walkways radiating from the center at specific angles.
- **The Outer Rim:** A continuous circular path linking all spokes, ensuring zero dead ends.
- **The Vault Cells:** $20 \times 20$ modular content zones nested between the spokes.

## 8. State Hooks: Modular Cleansing
- **Kill-Signal:** Defeating a Miniboss broadcasts a `SIG_CLEANSE_MODULE` event.
- **Cleansing Effect:** Toggles the socket's `is_cleansed` flag, materializes a dormant `RespiteAnchor`, and permanently suppresses enemy respawns in that region.

## 9. Respite Interaction State Machine & Edification Math

To facilitate long-term progression and strategic risk management, the engine implements a "Resting" loop and a persistent leveling system (Edification).

### 1. The Resting Loop (engine/world.py)
Interacting with an unlocked `Respite` object triggers the `execute_rest()` sequence:
- **Character Restoration:** Resets `player.hp` to `player.max_hp` and refills `player.flask_charges`.
- **World Re-population:** Triggers a partial map reload pass. Standard enemy spawners (Symbols: `Z`, `A`, `f`, `b`, `s`) are re-instantiated.
- **Elite Exclusion:** Miniboss strains (`E`, `2`, `3`) are never respawned; they are tracked via the generic `is_miniboss` property.
- **Progression Unlocking:** Sets `player.has_rested_this_session = True`, enabling the edification menu options.

### 2. Edification Leveling & Currency Scaling
Attribute upgrades scale linearly based on the current level index:
- **Math Formula:** `Cost = (current_level + 1) * 50` Pages.
- **Stat Categories:** **Edification** (Passive Defense), **Prowess** (+5 Attack), and **Fortification** (+10 Max HP).
- **The State Lock:** Each edification purchase or menu closure resets `has_rested_this_session = False`. To edify again, the player must commit to a fresh Rest action.

### 3. Conditional Defensive Parsing (engine/player.py)
A passive ability that modifies damage intake based on the player's health threshold:
- **Pristine Concentration:** If `HP > 95%`, damage reduced by `(Edification / 2)%`.
- **Desperate Synthesis:** If `HP < 30%`, damage reduced by `(Edification)%`.

## 10. UI Overlay Constraints & Input Ratchet Specifications

### 1. Input Ratchet (Debounce State Machine)
To prevent event spamming during transactions, UI controls require a distinct `ui_click_released` sequence:
- **Latched State:** Maintain `input_ratchet_latched = True` upon processing a discrete action (e.g., Level Up purchase).
- **Blocking:** While latched, all sequential triggers for that specific action are ignored.
- **Reset:** The latch is cleared only when receiving a native `KEYUP` or `MOUSEBUTTONUP` signal from the OS.

### 2. HUD Scaling Standards
- **Typography Alignment:** Status metrics (`HP`, `Flasks`, `Pages`) must utilize the compact 14pt font assets to match action prompts (`[SWAP]`, `[PICK UP]`), ensuring consistent padding within the HUD panel boundaries.

## 11. Entity Inheritances & The Miniboss Classification Law


## 12. Hub Persistence Boundaries & Notification Gatekeeper Rules

### 1. The Sanctuary Persistence Rule (The Blank Slate)
The Sanctuary acts as a transitional threshold between archival runs. 
- Entering or quitting from the Sanctuary forces the player's runtime `edification_level` to immediately drop back to **1**.
- **File Persistence:** The system must still write a valid session file to `~/.config/avoid_rain/save_data.json` when exiting from the Sanctuary. The main menu must render the **Continue** button if this file is present, bypassing the `in_progress` restriction so players can resume their session directly inside the hub.

### 2. Notification System Debounce
UI text popup alerts (such as `"Not enough pages!"`) must check the state of the `input_ratchet_latched` flag. No error notifications may be appended to the rendering stack if the input frame is currently locked or waiting for a key-release signal.

## 13. Entity Inheritances & The Miniboss Classification Law

### The Live-Check Respite Filter Rule
Minibosses do not persist through resets if they are dead, but they MUST persist if they are alive.
- The engine tracks a global list or bitmask of defeated elite identifiers: `session.defeated_miniboss_ids`.
- **The Evaluation Pass:** When a player triggers a Rest action at a Respite, the engine loops through the sub-map's spawner configurations. 
  - If an entity has `.is_miniboss == True`, the engine checks if its unique ID exists inside `session.defeated_miniboss_ids`.
  - **Condition A (Unbeaten):** If the ID is NOT in the defeated list, the miniboss is treated like a common enemy and is freshly respawned/restored to full health.
  - **Condition B (Beaten):** If the ID IS in the defeated list, the spawner is permanently skipped, ensuring it stays dead to prevent item duplication farming.

## 14. Global Movement Bounds & Module Transition Processing

### The Global Coordinate Rule
Entity collision check subroutines must evaluate position vectors against the total compiled canvas dimensions, rather than local sub-map constraints.
- **Boundaries:** Boundary tracking is enforced globally at `0 <= player.x < 440` and `0 <= player.y < 440` (measured in tile units).
- **Seamless Cross-Blitting:** Local sub-map modules must not append boundary colliders along their outer frame edges (e.g., indices 0 and 39 for a 40x40 map). When modules are stitched into the master grid, their borders must remain perfectly passable to allow fluid traversal between adjacent nodes.

## 15. Spatial Weather Mechanics: The Shrinking Ring (The Redacting Circle)

### 3. Initialization and Initial Grace Period
To prevent instant player death or asset loading freezes upon world instantiation, the safe zone matrix must initialize in an entirely un-redacted state:
- **Maximum Spawn Radius:** At session start, `active_safe_radius` must be explicitly set to a minimum value of **620.0** units (guaranteeing that the entire 440x440 grid fits entirely inside the clear zone).
- **The Initial Grace Clock:** The state machine starts in a `GRACE_PERIOD` holding state for **60.0 seconds**.
- **The Transition Trigger:** Absolutely zero acid rain rendering, zero particle calculations, and zero player damage checks may run while `current_grace_timer < 60.0`. The warning message `"[THE BLEED] The circle is closing"` prints strictly upon the exact frame this grace timer hits zero.

## 16. Boss Lifecycle Sequencing & Damage Resolution Verification

### 1. The Closed Circle Summoning Trigger
The primary `"night_boss"` entity type is strictly restricted from manifesting during run initialization.
- **The Dormant Phase:** While `active_safe_radius` is greater than the boundaries of the 40x40 Night Boss Arena module, the boss sprite is completely un-instantiated/hidden.
- **The Awakening Phase:** The exact frame the circle contraction hits its final `CLAMP` boundary limit, the engine executes `world.spawn_night_boss()`.
- **The Lockdown Rule:** The safe circle timer and radius contraction calculations are permanently locked in the closed state while the Night Boss is alive. The radius cannot open or alter until the boss's internal health variable ticks down to exactly `0`.
