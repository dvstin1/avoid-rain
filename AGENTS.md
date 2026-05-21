# Avoid Rain - Development Plan

## Project Overview
**Concept:** Top-down Action RPG and Roguelike.
**Environment:** Debian Linux, Pygame, 2D Graphics.

## Architectural Constraints
- **No Magic Numbers:** All configuration variables must reside in specific constants files.
- **Frame Rate Independence:** Use delta time (`dt`) to scale all physics and movement calculations.
- **Logic/Rendering Separation:** Game logic must be strictly decoupled from rendering code.

## Feature Roadmap (Iterative Development)

### Phase 1: Foundation
- Bare bones window initialization.
- Constants management system.
- Simple WASD movement for the player character.

### Phase 2: World & Collision
- Static wall grid array implementation.
- Basic bounding box collision detection.

### Phase 3: Combat Basics
- Swinging sword state machine.
- Directional hitboxes.
- Test enemy dummy for hit detection verification.
