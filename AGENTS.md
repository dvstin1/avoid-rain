## Current Phase & Execution Rules
* **Current Project Phase:** CODING
* **Goal:** Phase 1: Core Gameplay Loop (Combat, Physics, and Map Generation).
* **Task Lifecycle Rule (Continuous Cleanup Protocol):** The moment an active task is fully verified, functional, and complete, you must instantly execute a documentation pass before moving to the next phase:
  1. Cut the entire task block out of the active slot in `AGENTS.md`.
  2. Append it to the bottom of `docs/CHANGELOG.md` as a past-tense historical entry (e.g., `## [ARCHIVED] Core Map JSON Migration - May 2026`).
  3. Leave the active section in `AGENTS.md` clean, blank, and completely primed for the next action.

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

## Active Task: 

### 1. 
## Active Task: Emergency Scope Fix & Input Event Order Realignment

Resolve the `COLOR_WHITE` local variable scope crash during combat and fix the input blocking preventing the Chronicle gateway from processing Spacebar interactions.

### 1. Global Color Scope Correction
- Audit the combat interaction and damage display functions (likely inside `engine/enemy.py`, `engine/player.py`, or `rendering/renderer.py`).
- Ensure any color constants like `COLOR_WHITE` are read strictly from your global configuration/rendering module, or explicitly declare them at the very top of the local function to resolve the `UnboundLocalError`.

### 2. Event Loop Ordering (Interaction vs. Attack)
- Inspect the core input handler or event polling loop in `engine/input.py` / `main.py`.
- **The Event Priority Rule:** When the player presses `pygame.K_SPACE`, the engine must *first* check for contextual proximity interactions (Is the player standing on the Chronicle? Is the player next to an NPC/Wellspring?). 
  - If an interaction prompt is active, execute the interaction block and **consume the input event** (`return` or `break`) so it doesn't trigger an attack.
  - If no interactable entity is within range, default the spacebar input to trigger the standard weapon attack swing.
- Ensure the player can successfully warp into `world_map1` from the Sanctuary by hitting Spacebar.
