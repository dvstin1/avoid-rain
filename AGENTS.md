## Current Phase & Execution Rules
* **Current Project Phase:** CODING
* **Goal:** Phase 1: Core Gameplay Loop (Combat, Physics, and Map Generation).

## Architectural Constraints
- **Constants Only:** No magic numbers; all config must be in specialized constants files.
- **dt Scaling:** Frame rate independence is mandatory for all physics and movement.
- **Decoupled Design:** Game logic must be strictly separated from rendering.
- **Testing Mandate:** All engine logic (physics, state transitions, math) must have unit tests using `pytest`.
- **Quality Control:** All code must pass `pylint` with a score of 8.0 or higher.

## Agent Behavior Rules
- Always create a single git commit for each user prompt that requires code or documentation changes. Each commit should be atomic, include a clear message, and include the required Co-authored-by trailer.
- Do NOT push commits to remote automatically. Pushing is not needed unless explicitly requested.
- Keep changes low-coupled and limited to the files required by the user's request.

## Definition of Ready (DoR) Checklist
1. [X] **Application Architecture Defined:** See `docs/architecture.md`.
2. [X] **State Schema Defined:** See `docs/state_schema.md`.
3. [X] **Combat & Collision Rules:** See `docs/architecture.md`.
4. [X] **Input Handling Specification:** See `docs/input_handling.md`.
5. [X] **Asset Manifest:** See `docs/asset_manifest.md`.
6. [X] **Initial Scope (Sanctuary) Archived:** See `CHANGELOG.md`.

## Context Pointers (Hub-and-Spoke)
- **`docs/architecture.md`**: Permanent technical architectures and system specs (Main Loop, Climate Engine, Physics, Interaction, Map Topography).
- **`docs/state_schema.md`**: Data models for Player, Rain, and World state.
- **`docs/input_handling.md`**: Detailed mapping of raw inputs to engine actions.
- **`docs/asset_manifest.md`**: Registry of sprites and tile sets.
- **`docs/world_lore.md`**: Narrative background and world rules.
- **`CHANGELOG.md`**: Archive of completed features and deliverables.

## Active Task: Documentation Audit & Consolidation
Currently performing a comprehensive documentation cleanup to remove contradictions, consolidate architecture, and archive completed features into `CHANGELOG.md`.

<!-- SINGLE ACTIVE PLACEHOLDER SECTION -->
## Active Troubleshooting: Enemy Population Reset Lifecycle Fix

Correct the room initialization sequence to ensure that when the player warps into a combat zone, the enemy group array is fully re-instantiated and populated fresh, rather than pulling an exhausted or dead state tracking array from memory.

### 1. Verification of Level Spawning
- Audit the centralized cleanup loop inside `GameState.update`. Ensure that deleting a dead enemy instance from the active sprite groups does NOT permanently delete their character code spawn symbol from the master blueprint template in `room_definitions.py`.

### 2. The Re-Population Hook
- Update the `LevelLoader.parse_map` or scene-warp transition function:
  - The exact moment a player triggers a warp or resets a run via death, the engine must clear the old enemy array completely and re-read the map layout symbols (`BatEnemy` symbols, etc.).
  - Re-instantiate brand new, full-health `BatEnemy` objects at their designated grid coordinate spaces.

### 3. State Preservation Isolation
- Ensure mid-run suspended snapshots ONLY track dead enemies if a run is actively suspended mid-room. If a run has completely reset or a new map layout loads, the enemy group must reset to 100% capacity.
