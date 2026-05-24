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
## Active Task: XDG Config Home Save Redirection & Persistent Flush Fix

Redirect all game session save states to a clean dotfile configuration folder within the user's Home directory, and ensure absolute disk serialization before application termination.

### 1. Dynamic Path Expansion (~/.config/avoid_rain/)
- Do not use relative paths like `"save_data.json"`. Use Python's `os.path.expanduser` or `pathlib.Path.home()` to dynamically resolve the platform-native configuration directory.
- Define your absolute save destination path string as: **`~/.config/avoid_rain/save_data.json`**.
- Before opening a write stream, explicitly invoke `os.makedirs(os.path.dirname(save_path), exist_ok=True)` to safely construct the underlying directory tree if it doesn't exist on boot.

### 2. Guaranteed Disk Serialization Hook
- To prevent the OS from killing the script memory before data hits the disk when closing the window frame, register a formal shutdown function using Python's native `atexit` module:
  ~~~python
  import atexit

  def force_final_save():
      if session_is_active:
          # Open explicit file handler and run json.dump()
          # Force an immediate physical storage sync using f.flush() and os.fsync(f.fileno())

  atexit.register(force_final_save)

    Ensure that your Title Screen's startup check reads from this absolute ~/.config/avoid_rain/save_data.json location so the "Continue" option displays accurately across reboots.
