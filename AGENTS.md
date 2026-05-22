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

## Active Task: The Chronicler NPC Implementation

Implement the foundational safe-hub NPC "The Chronicler" inside `ZONE_SANCTUARY` using the State-Driven Dialogue Schema.

### 1. Spatial Placement & Interactivity
- Instantiate The Chronicler as a static `GameObject` near the center of the Sanctuary map (adjacent to the Wellspring fountain if available, or near the spawn layout).
- Set trait flags: `self.is_solid = True` and `self.is_interactive = True`.
- Configure their interaction box to trigger the **Unified Interaction Filter**, displaying a localized text primitive prompt: `"Press [ATTACK] to Speak"`. Combat swings must be suppressed during conversation.

### 2. State-Based Dialogue Matrix
- Read the dialogue branching guidelines defined in your documentation spoke files.
- Wire the dialogue engine to pull text nodes from a localized dictionary mapping directly to the player's persistent `last_run_result` flag:
  - `INIT`: Present calm, objective welcoming text strings.
  - `DEFEAT`: Present quiet, hesitant, low-scrolling dialogue strings.
  - `VICTORY`: Present warm, accelerated celebratory dialogue strings.

### 3. Fail-Safe Verification
- Ensure an empty condition fallback string is registered so the interaction loop never freezes.
- Verify that initializing a new run through *The Chronicle* book object cleanly resets the player's run status back to `INIT` behind the scenes.
