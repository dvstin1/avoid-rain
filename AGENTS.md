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

## Active Task: Documentation Audit & Consolidation
Currently performing a comprehensive documentation cleanup to remove contradictions, consolidate architecture, and archive completed features into `CHANGELOG.md`.

<!-- SINGLE ACTIVE PLACEHOLDER SECTION -->
## Active Task: [PENDING SELECTION]

Select the next phase of development from the proposed roadmap items below.

### Option A: The Climate Engine - Phase 1 (The Bleed)
- Implement the "Rain Lifecycle" mentioned in `docs/architecture.md`.
- **Weather State Machine:** Transition between `Clear_Day` and `The_Bleed`.
- **Visuals:** Diagonal cyan rain particles using `pygame.draw.line`.
- **Hazard:** Apply tick damage to the player if they are caught in the rain outside a Respite boundary.

### Option B: Inventory & Stat Menu (The Libram)
- Implement a dedicated UI screen for viewing collected "Torn Pages" and player stats.
- **The Libram:** A toggleable menu (mapped to `TAB` or `I`) that pauses the game and displays the player's current Offensive/Defensive modifiers.
- **Visuals:** A parchment-themed modal using the `EXPANDED` UI architecture.

### Option C: Combat Polish - Stagger & Visual Feedback
- **Stagger Mechanic:** Enemies and the player enter a brief `STAGGERED` state when hit, preventing action.
- **Visual Polish:** Add screen shake on heavy hits and a brief white flash (outline) for entities taking damage.
- **Hit-Stop:** Pause the engine for a few frames (e.g., 50ms) during a successful hit to provide "weight" to combat.
