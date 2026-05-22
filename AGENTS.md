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

## Active Troubleshooting: New Game Confirmation Prompt Rendering Fix

Fix the rendering sequence for the New Game "Y/N" confirmation overlay to ensure text assets are cleanly drawn on top of the active viewport buffer.

### 1. Layering Audit & Drawing Order
- Locate the code section managing the Title Menu states (e.g., `title_screen.py` or the menu interaction switch block).
- Ensure that when the state transitions to `CONFIRM_NEW_GAME`, the drawing sequence strictly follows this execution order:
  1. Draw the base title background/void mask.
  2. Draw the confirmation prompt background card box (if applicable).
  3. Render and draw the "Are you sure you want to start a New Game? (Y/N)" text surface as the absolute top layer.

### 2. Coordinate & Color Verification
- Verify that the $(X, Y)$ coordinates for the confirmation text surface dynamically anchor to the center of the viewport dimensions (`screen.get_rect().center`) rather than relying on stale or absolute window offsets.
- Force the text primitive color to contrast sharply with the menu background (e.g., solid white `#FFFFFF` or light amber) so it is highly visible.

### 3. State-Switch Clean Slate
- Ensure that pressing `N` cleanly reverts the rendering mode back to the standard Title Menu options, and pressing `Y` triggers a full directory purge/reset of `profile_metrics.json` before booting into a pristine `ZONE_SANCTUARY`.
