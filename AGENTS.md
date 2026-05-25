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

### Active Task: Audio System Architecture Mockup & On-Screen Debug Display

Implement an engine track manager mockup that updates a visual HUD overlay element tracking the active soundtrack assignment, including distance-based miniboss combat triggers.

### 1. Audio Track Manager Mockup State
- In `engine/world.py` or your session state controller, create a property string: `player.active_track_name = "sanctuary_hub.ogg"`.
- Set defaults dynamically based on location zones:
  - Title Screen: `title_theme.ogg`
  - Sanctuary: `sanctuary_hub.ogg`
  - World Map Normal Space: `world_exploration.ogg`
  - Death State: `death_screen.ogg`

### 2. Miniboss Proximity Tracking Timer
- In your active game loop, loop through spawned entities. If an enemy has `is_miniboss == True` and is actively engaged:
  - Calculate distance: `distance_meters = player_pos.distance_to(enemy_pos) / pixels_per_meter_ratio`.
  - If `distance_meters <= 15`: Force `player.active_track_name = "miniboss_combat.ogg"` and reset the drop-off timer variable `miniboss_cooldown_accumulator = 0`.
  - If `distance_meters > 15`: Accumulate delta time: `miniboss_cooldown_accumulator += dt`. If `miniboss_cooldown_accumulator >= 3.0`, revert `player.active_track_name = "world_exploration.ogg"`.

### 3. On-Screen Debug HUD OSD Overlay
- In `rendering/renderer.py`, draw a small, clean text block at the top margin edge of your workspace window panel.
- **The Text Output:** Format it as: `[DEBUG_AUDIO: Playing <player.active_track_name>]`. Use the smaller, compact interface font size matching our `[SWAP]` layouts.
