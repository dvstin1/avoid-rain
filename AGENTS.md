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

### 1. Active Task: Hard Persistent Save File Serialization & Startup Boot Hook

Ensure the game state fully survives application closure by replacing internal in-memory session tracking with absolute, physical JSON disk persistence.

#### 1. Hard Disk Serialization on Exit
- In your session saving module or main application exit event interceptor (where `pygame.QUIT` or Escape quit events are handled):
  - Do not merely write variables to a local state class instance dictionary.
  - Force a hard file serialize block to write directly to a local file (e.g., `save_data.json` or `.save_session.json`):
    ~~~python
    import json
    save_payload = {
        "in_progress": True,
        "player_stats": player.serialize(),
        "active_enemies": [e.serialize() for e in enemy_group]
    }
    with open("save_data.json", "w") as f:
        json.dump(save_payload, f, indent=4)
    ~~~

#### 2. Main Boot Initialization Check
- Update your main game loop initializer or main menu state startup hook (where the game first opens from the desktop terminal context):
  - At the very top of execution, check if `save_data.json` exists on disk using `os.path.exists()`.
  - If the file is present, safely open, read, and parse it:
    ~~~python
    try:
        with open("save_data.json", "r") as f:
            data = json.load(f)
            if data.get("in_progress"):
                # Append 'Continue' to the valid menu list arrays
    except (FileNotFoundError, json.JSONDecodeError):
        # Gracefully handle broken or missing files without crashing
    ~~~

#### 3. Clear Session State on Proper Death
- Ensure that if the player experiences a clean run termination (death or manual game reset inside the Sanctuary), the file code overwrites `in_progress` to `False` or safely removes the file entirely (`os.remove()`) so a broken dead run cannot be indefinitely loaded.
