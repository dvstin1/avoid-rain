## Current Phase & Execution Rules
* **Current Project Phase:** PLANNING (Strictly Banned: Generating python code blocks)
* **Goal:** Refine game mechanics, file structure, and data state until the Definition of Ready is met.

## Architectural Constraints
- **Constants Only:** No magic numbers; all config must be in specialized constants files.
- **dt Scaling:** Frame rate independence is mandatory for all physics and movement.
- **Decoupled Design:** Game logic must be strictly separated from rendering.
- **Testing Mandate:** All engine logic (physics, state transitions, math) must have unit tests using `pytest`.
- **Quality Control:** All code must pass `pylint` with a score of 8.0 or higher.

## Definition of Ready (DoR) Checklist
Before transitioning to Phase 2 (Coding), the following criteria must be checked [X] by the user or confirmed by the agent:
1. [X] **File Directory Blueprint Defined:** See `docs/file_blueprint.md`.
2. [X] **State Schema Defined:** See `docs/state_schema.md`.
3. [X] **Combat & Collision Math Rules:** See `docs/combat_mechanics.md` (AABB and Normalization).
4. [X] **First Iteration Scope:** Defined in `docs/iteration_scope.md`.
5. [X] **Asset Manifest:** See `docs/asset_manifest.md`.

## PLANNING COMPLETE: You are ready to flip the phase to CODING. Update the agent.md to proceed.

## Agent Behavior Rule
...

## Context Pointers (Hub-and-Spoke)
- **`docs/combat_mechanics.md`**: Detailed logic for movement, sword states, and the rain circle mechanic.
- **`docs/asset_manifest.md`**: Registry of all 2D sprites, animations, and tile sets.
- **`docs/world_lore.md`**: Narrative background and world rules (shifting maps, rain cycle).
- **`docs/file_blueprint.md`**: The decoupled directory structure and import rules.
- **`docs/state_schema.md`**: Data models for Player, Rain, and World state.

## Feature Roadmap
...

2. **Phase 2:** Static wall grid and bounding box collision.
3. **Phase 3:** Sword state machine, directional hitboxes, and enemy dummy.
