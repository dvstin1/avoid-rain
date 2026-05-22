## Current Phase & Execution Rules
* **Current Project Phase:** CODING
* **Goal:** Phase 1: Core Gameplay Loop (Combat, Physics, and Map Generation).

## Architectural Constraints
- **Constants Only:** No magic numbers; all config must be in specialized constants files.
- **dt Scaling:** Frame rate independence is mandatory for all physics and movement.
- **Decoupled Design:** Game logic must be strictly separated from rendering.
- **Testing Mandate:** All engine logic (physics, state transitions, math) must have unit tests using `pytest`.
- **Quality Control:** All code must pass `pylint` with a score of 8.0 or higher.
- **Coding Style Rule:** All Python source files must adhere to a maximum line length constraint of **120 characters** (instead of 79/80). Prioritize clear, single-line mathematical expressions and readable Pygame rendering chains.

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

<!-- SINGLE ACTIVE PLACEHOLDER SECTION -->
## Active Task: Macro-Map Framework & Replicated Section Injection

Establish the foundation for the massive world map by building a macro-grid loader that embeds copies of the `chapter1` layout into multiple modular coordinates.

### 1. Macro-Grid Blueprint Definition
- Inside `engine/world.py` or your level loading module, define a grand map size constant: `MACRO_MAP_SIZE = 120`.
- Program a generator function `generate_macro_lotus_world()` that builds a basic frame layout grid. 
- Carve out four separate $20 \times 20$ empty grid sectors (e.g., North, South, East, West chambers) within this large framework.

### 2. Section Replication Parser
- Update the `LevelLoader` to stitch text matrices together. 
- When building the macro world, programmatically copy and paste the rows of the pre-existing, interesting `chapter1` layout (containing your benches, bookcases, ink puddles, and bats) directly into each of the four empty carved-out sectors.
- Anchor the initial player spawn point safely on the central framework tissue outside of these replicated combat zones.

### 3. Verification Trace
- Limit code lengths across files to the newly established 120-character rule.
- Print a debug message on boot to track world scaling: `print(f"[WORLD MATRIX] Initialized 120x120 Macro-Grid with 4 replicated test sectors.")`
