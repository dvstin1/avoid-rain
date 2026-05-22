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
## Active Task: Arena Sprawl Expansion, Multi-Tile Props, & 2x2 Miniboss

Expand the Chapter 1 level array to a massive layout featuring a clear hallway progression, refactor Benches to a vertical 1x2 footprint, and implement a large 2x2 Miniboss entity.

### 1. Level Design: The Corridor Sprawl
- Rewrite the `chapter1` map grid matrix to be approximately 4 times its current scale.
- **The Topology:** Design a starting room with benches, rocks, and bats, narrow down into a long $1 \times 1$ tile wide connecting hallway corridor, and open up into a large, grand final chamber.

### 2. Multi-Tile Bench & Miniboss Allocation
- **The Bench Refactor (`S`):** Update `LevelLoader` so that reading an `S` character instantiates a vertical rectangle spanning `TILE_SIZE` width and `TILE_SIZE * 2` height.
- **The Miniboss (`M_BOSS`):** Create an elite enemy class in `engine/enemy.py`. 
  - Render it as a large $2 \times 2$ primitive colored block.
  - Position its character spawn anchor exclusively inside the large final chamber room.
  - Give it a simple pursuit vector with an expanded health pool.
