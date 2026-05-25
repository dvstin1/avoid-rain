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

## 4. Climate Engine: The Devouring Storm
> **DEVELOPMENT HOLD:** Implementation of the Climate Engine is deferred until the Macro-Grid framework and core combat loop are fully stable.

The climate engine dictates the pace of gameplay across four distinct phases:
1. **Clear Day (Exploration):** 0:00 - 10:00. Ambient visuals, no hazard, Respites ACTIVE.
2. **The Bleed (Collapse):** 10:00 - 15:00. Corrosive ink-storm. Safe zone shrinks toward a random center. Damage outside radius: 2/sec. Respites DEACTIVATED.
3. **The Dilution (Victory):** Immediate post-boss event. Rain turns Harmless/Clear. Radial boundary dissolves.
4. **Clear Night (Breather):** Rain fades out. Respites REBOOT and return to functionality.

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

## 9. Save File Protocol (XDG Compliance)
Save data resolves to standard filesystem paths:
1. **Primary:** `XDG_STATE_HOME/avoid_rain`
2. **Fallback:** `~/.local/state/avoid_rain`
Directory presence is verified (`mkdir -p`) before every write operation to prevent serialization failures.
