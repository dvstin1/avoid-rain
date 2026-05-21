# Avoid Rain - Hub

## Project Overview
**Concept:** Top-down Action RPG/Roguelike where players must outrun an encroaching lethal rain.
**Stack:** Debian Linux, Pygame, 2D Graphics.

## Architectural Constraints
- **Constants Only:** No magic numbers; all config must be in specialized constants files.
- **dt Scaling:** Frame rate independence is mandatory for all physics and movement.
- **Decoupled Design:** Game logic must be strictly separated from rendering.

## Context Pointers (Hub-and-Spoke)
- **`docs/combat_mechanics.md`**: Detailed logic for movement, sword states, and the rain circle mechanic.
  *Include for physics, AI, or combat implementation.*
- **`docs/asset_manifest.md`**: Registry of all 2D sprites, animations, and tile sets.
  *Include for rendering, animation, or asset loading tasks.*
- **`docs/world_lore.md`**: Narrative background and world rules (shifting maps, rain cycle).
  *Include for level design or world-building context.*

## Feature Roadmap
1. **Phase 1:** Window init, constants system, and WASD movement.
2. **Phase 2:** Static wall grid and bounding box collision.
3. **Phase 3:** Sword state machine, directional hitboxes, and enemy dummy.
