## Current Phase & Execution Rules
* **Current Project Phase:** CODING
* **Goal:** Implement Phase 1: Sanctuary Foundation.

## Architectural Constraints
- **Constants Only:** No magic numbers; all config must be in specialized constants files.
- **dt Scaling:** Frame rate independence is mandatory for all physics and movement.
- **Decoupled Design:** Game logic must be strictly separated from rendering.
- **Testing Mandate:** All engine logic (physics, state transitions, math) must have unit tests using `pytest`.
- **Quality Control:** All code must pass `pylint` with a score of 8.0 or higher.

## Definition of Ready (DoR) Checklist
Before transitioning to Phase 2 (Coding), the following criteria must be checked [X] by the user or confirmed by the agent:
1. [X] **File Directory Blueprint Defined:** See `docs/file_blueprint.md`.
2. [X] **Application Architecture Defined:** See `docs/architecture.md`.
3. [X] **State Schema Defined:** See `docs/state_schema.md`.
4. [X] **Combat & Collision Math Rules:** See `docs/combat_mechanics.md` and `docs/physics_rules.md`.
5. [X] **Input Handling Specification:** See `docs/input_handling.md`.
6. [X] **First Iteration Scope:** Defined in `docs/iteration_scope.md`.
7. [X] **Asset Manifest:** See `docs/asset_manifest.md`.

## PLANNING COMPLETE: You are ready to flip the phase to CODING. Update the agent.md to proceed.

## Agent Behavior Rule
- Always create a single git commit for each user prompt that requires code or documentation changes. Each commit should be atomic, include a clear message, and include the required Co-authored-by trailer.
- Do NOT push commits to remote automatically. Pushing is not needed unless explicitly requested.
- Keep changes low-coupled and limited to the files required by the user's request.


## Context Pointers (Hub-and-Spoke)

Note: docs/extended-notes contains long, optional notes — do not read those files unless explicitly instructed to do so.

- **`docs/combat_mechanics.md`**: Detailed logic for movement, sword states, and the rain circle mechanic.
- **`docs/asset_manifest.md`**: Registry of all 2D sprites, animations, and tile sets.
- **`docs/world_lore.md`**: Narrative background and world rules (shifting maps, rain cycle).
- **`docs/file_blueprint.md`**: The decoupled directory structure and import rules.
- **`docs/architecture.md`**: Application lifecycle and main loop skeleton.
- **`docs/state_schema.md`**: Data models for Player, Rain, and World state.
- **`docs/input_handling.md`**: Mapping of raw inputs to engine actions.
- **`docs/physics_rules.md`**: Boundary clamping and collision order of operations.

## Feature Roadmap
1. **Phase 1:** Window init, constants system, and WASD movement in the Sanctuary.
2. **Phase 2:** Static wall grid and bounding box collision.
3. **Phase 3:** Sword state machine, directional hitboxes, and enemy dummy.

## Dialogue System Architecture: The Blackboard Protocol

To ensure absolute modularity and eliminate side effects across unrelated systems, the dialogue engine must be strictly decoupled from active game state data. It must utilize a unified **Blackboard State & Query Model**.

### 1. The Global Blackboard (The Data State)
The game must maintain a flat, persistent dictionary (the Blackboard) that records primitive values tracking historical narrative milestones. No other script may directly read dialogue code; they only push facts to this dictionary.

```python
# Conceptual Structure (Do not write logic files yet, follow this schema)
dialogue_blackboard = {
    "last_run_result": "DEFEAT",    # Enum: INIT, VICTORY, DEFEAT
    "level": 14,                    # Integer
    "has_item_iron_key": True,      # Boolean flag per unique item
    "boss_night1_encountered": True,# Boolean flag per critical encounter
    "boss_author_slain": False      # Boolean flag per boss kill
}

## System Architecture: The Wellspring Interface (Stats & Bestiary)

To keep the hub scene files lightweight, the tracking of lifetime player metrics must be managed by a decoupled, standalone file serialization process, which is pulled into a dedicated UI display layout only upon active interaction.

### 1. The Persistence Matrix (The Data File)
The engine must serialize a flat, lightweight JSON or dictionary schema file named `profile_metrics.json` inside the root user save path (default: ~/.avoid-rain/profile_metrics.json in the user's home directory). This file is updated instantly when milestones occur and remains independent of active level generation memory:

```json
{
  "lifetime_stats": {
    "runs_started": 0,
    "wins_chapters_cleared": 0,
    "losses_bleed_wipes": 0,
    "deaths_standard_respawns": 0,
    "forced_quit_outs": 0
  },
  "discovered_bestiary": {
    "enemy_id_01_slug": true,
    "boss_id_night1_censor": false
  }
}

## Strict Implementation Directive: The Rule of Low-Coupling Isolation

To maximize development efficiency, minimize regression side effects, and optimize token usage, the AI agent must adhere to a strict **One-Thing-At-A-Time** implementation cycle:

1. **Identify Isolation:** Pick exactly ONE feature from the roadmap that is unshaded/unimplemented. This feature must be highly "low-coupled"—meaning its backend architecture can be fully built, verified, and sealed without depending on or altering any other incomplete feature branches.
2. **Design Invariance:** Prioritize systems whose data schemas are structurally independent (e.g., the `StatisticsTracker` JSON serialization, the `LootManager` probability engine, or the `Escape Pause Menu` state interceptor). Do not build highly dependent intermediate logic until its parent framework is fully set in stone.
3. **The Test-Driven Mandate:** For the selected feature, you must write the modular framework logic alongside dedicated unit or behavioral tests. Do not proceed to any other task or file directory until the tests for this specific node pass cleanly.
4. **Zero Feature Creep:** Implement the selected feature exactly to the specifications documented—no more, no less. Do not leave placeholder comments ("TODO") pointing to unbuilt features. Keep the execution completely self-contained.

## Active Task: Grid-Based Level Parser Implementation

Implement a clean, data-driven map parsing engine that reads 2D text matrix strings and instantiates the initial structural layout using placeholder colored primitives.

### 1. Data Schema
- Create a dedicated container module `map_data.py` to hold the `ROOM_PROTOTYPES` string array dictionary. 
- Define a base layout size constraint (e.g., `TILE_SIZE = 32` or `48` pixels).

### 2. Parser Logic
- Write a `LevelLoader` class that loops through a chosen string matrix grid.
- Multiplies row and column indices by `TILE_SIZE` to calculate exact $(X, Y)$ rendering coordinates.
- Maps symbols to basic sprite primitive groups:
  - `#` -> Static Wall (Solid grey rectangle)
  - `T` -> Static Obstacle/Tree (Solid dark green circle)
  - `B` -> Placeholder Prop/Barrel (Solid brown rectangle; acts as a standard solid object for now)
  - `.` -> Open Floor (Skips collision, handles background tile rendering if applicable)

### 3. Integration Constraints
- The player entity and existing warp objects must be cleanly positioned using designated coordinate start hooks or dedicated characters inside the string grid (e.g., `P` for Player start, `W` for Warp).
- The physics engine's collision detection loops must universally evaluate these newly parsed sprite groups using the `is_solid` boundary checks.

## Active Task: Destructible Prop Layer & Tier 4 Loot Roll

Implement the destruction state engine for the placeholder Barrel (`B`) prop and integrate the baseline `LootManager` probability engine for Tier 4 drops.

### 1. Prop Health & Interaction States
- Update the base `GameObject` initialization for entities spawned with the `"barrel"` configuration flag:
  - Set `self.is_breakable = True`
  - Initialize a flat health tracking property: `self.health = 1`
- Implement a `take_damage(self, amount)` method. When an active combat swing hitbox intersects a breakable prop, decrement its health.

### 2. The LootManager Serialization (Tier 4)
- Create a modular `loot_manager.py` file to handle entity drop tables.
- Write a `roll_drop(source_tier, position)` function. 
- For a **Tier 4** event (Barrel Destruction):
  - Run a floating-point probability check against a **15% drop chance**.
  - If successful, instantiate a tiny floating text primitive or primitive item particle at the object's exact $(X, Y)$ coordinate space representing either `torn_pages: 1` or a minor heal.
  - When the player bounding box intersects this dropped item, increment the respective value in the player profile dictionary and destroy the item instance.

### 3. Destruction Clean-Up
- Upon a barrel's health hitting 0, instantly remove the entity instance from the active `is_solid` collision tracking group so it no longer blocks player/enemy kinematics.
- Trigger a brief 3-frame fading or shrinking primitive animation sequence before entirely purging the object instance from active memory loops.

## Active Task: Map Data Layout Population

Populate the `ROOM_PROTOTYPES` dictionary inside your map data files with distinct structural test layouts to verify the physical distribution of walls, trees, and breakable barrels across both zones.

### 1. Layout Blueprints

#### Room 1: The Sanctuary / Scriptorium Hub
- A safe square chamber containing a centralized Respite anchor and a clear path to the Chapter 1 Warp portal.

#### Room 2: Chapter 1 - The Ink-Stained Wilds
- A larger room structured with perimeter stone walls (`#`), organic clusters of static trees (`T`), clusters of destructible barrels (`B`) tucked into corners or blocking narrow pathways, and a hostile enemy spawn coordinate.

### 2. Layout Integration Constraint
- Ensure the character parsing loops match your tile dimensions exactly so the player doesn't spawn inside a solid stone wall block (`#`).
