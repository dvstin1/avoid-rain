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
- **Map Editor Architecture Rules:**
  1. **Palette Divergence Law:** Whenever a new structural tile, item type, or enemy symbol (e.g., Miniboss strains) is added to the core game engine, you must instantly update the map editor's palette loading dictionary to mirror that addition. The palette layout must never fall out of synchronization with engine configurations.

## Definition of Ready (DoR) Checklist
1. [X] **Application Architecture Defined:** See `docs/architecture.md`.
2. [X] **State Schema Defined:** See `docs/architecture.md`.
3. [X] **Combat & Collision Rules:** See `docs/architecture.md`.
4. [X] **Input Handling Specification:** See `docs/navigation_and_ui.md`.
5. [X] **Asset Manifest:** See `docs/visual_style_and_assets.md`.
6. [X] **Initial Scope (Sanctuary) Archived:** See `CHANGELOG.md`.

## Context Pointers (Hub-and-Spoke)
- **`docs/architecture.md`**: Permanent technical architectures, system specs, and state schemas.
- **`docs/navigation_and_ui.md`**: Viewport management (Camera), Minimap, and Input Handling.
- **`docs/visual_style_and_assets.md`**: Registry of sprites, tile sets, and art blueprints.
- **`docs/world_and_lore.md`**: Narrative background, world rules, and geographical classifications.
- **`docs/modular_system.md`**: Level serialization schema and "Master Loom" assembly logic.
- **`docs/persistence.md`**: Statistics integration and autosave mechanics.
- **`docs/backlog.md`**: Development roadmap and future feature proposals.
- **`CHANGELOG.md`**: Archive of completed features and deliverables.
<!-- SINGLE ACTIVE PLACEHOLDER SECTION -->

## Active Task: 

### Active Task: Respite Level-Up Lock, Input Ratchet Debounce, & HUD Font Scaling Alignment

Resolve input spamming inside menu overlays, enforce the single-use level-up restriction per rest cycle, and align HUD layout text fonts.

#### 1. Level-Up Lock State Integration
- In `ui/menu.py` or your respite loop handler, track the state variable `player.has_rested_this_session`.
- Toggle it to `True` strictly when the player triggers the active "Rest" routine (which resets the standard enemies).
- Once the level-up transaction executes or the menu closes, immediately flag `player.has_rested_this_session = False`. 
- Gray out or display an interactive message block reading `"[Must Rest to Unblock Level Up]"` if they try to access the option again without resting.

#### 2. UI Input Ratchet (Key-Up Release Safeguard)
- In your UI input listener system, add a debounce condition to prevent rapid menu selections:
  - Do not process continuous held inputs for transaction triggers.
  - Require the user to fully lift their interaction key or mouse click button before allowing a subsequent `Level Up` purchase to process.

#### 3. HUD Status Metric Font Realignment
- In `rendering/renderer.py`, locate the top-level HUD drawing module where player parameters (`HP`, `Flasks`, `Pages`) are written to the screen.
- **The Typography Fix:** Downgrade the font size used for this text object line to exactly match the smaller, compact font assets utilized by your lower action panels (such as `[SWAP]` and `[PICK UP]`). Ensure clean vertical padding so everything sits perfectly contained inside the HUD margin boundaries.
