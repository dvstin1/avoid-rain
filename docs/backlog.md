# Development Roadmap & Feature Backlog

## Roadmap Priorities
- **Phase 1 (Current): Core Gameplay Loop.** Focus exclusively on hostile game world mechanics: vector physics, modular assembly, enemy AI, and combat collision.
- **Phase 2 (Future): Hub & Narrative Polish.** Visual expansion of the Sanctuary, advanced NPC dialogue branching, and environment tiling sheets.

---

## Feature Backlog & Future Proposals

> **DISCLAIMER:** This document contains unimplemented features and speculative ideas. Nothing listed here is currently active or guaranteed for immediate production. This serves as a "parking lot" for high-concept mechanical and aesthetic refinements.

---

## 1. Input & Accessibility
- **Gamepad Support (Polish):** Native controller mapping for Xbox/PlayStation layouts is implemented, but could use further refinement and rumble support.
- **Remappable Keys:** In-game menu for custom keyboard/controller bindings.
- **Screen Shake Toggle:** Ability to disable or reduce intense combat visual effects.

## 2. Audio & Atmosphere
- **Noir Soundtrack:** Procedural ambient tracks that shift intensity based on proximity to enemies or the Rain.
- **Environment Audio:** Directional audio for candelabras, wellsprings, and the distant rumble of the author's madness.

## 3. Narrative & Visuals
- **Chapter Titles:** Large typographic overlays when entering new modular zones. (Partially implemented as Typographic Bloom).

## 4. Technical & Navigation (Future Phases)
- **A* Pathfinding:** Implement a dedicated pathfinding engine to allow Actors (Enemies and NPCs) to navigate around walls and obstacles autonomously.
    - **Dynamic Calculation:** Instead of simple linear vectors, actors will compute a tile-based route to their next PatrolPoint.
    - **Optimization:** Utilize a heat-map or hierarchical A* to manage the large 440x440 grid efficiently in Python.
    - **Obstacle Awareness:** Pathfinding must account for both static wall tiles and solid GameObjects (Bookcases, Candelabras).
- **LAN Multiplayer:** Implement UDP broadcast (`SO_BROADCAST`) for automatic game discovery on the same subnet.
- **State Serialization:** Ensure player entities cleanly serialize position and movement vectors into lightweight JSON/byte structs for low-latency networking.

## 6. Combat Refinement (Speculative)
- **Weapon Arts:** Unique special attacks or passive effects for "Anomalous" weapons (e.g., Ink Bleed triggering a small AoE puddle on strike).
- **Quill Pressure (Stamina):** A resource meter that limits rapid-fire attacks and dashes, encouraging tactical positioning and deliberate timing.
- **Advanced Stagger Mechanics:** Variable stagger thresholds based on weapon weight or impact force.

## 7. Binder Scripts (Upgrade System)
- **Concept:** The Binder NPC acts as a procedural artisan, weaving "Scripts" (operational metaphors like "Hemming Script" for HP buffs) into the player's frame using Torn Pages.
- **Mechanics:** Scripts act as tiny compilers in the margins altering stat allocations. They can be combined but are subject to "syntax conflicts" where scripts touching the same stat will fight, with the stronger one winning.
- **Lore Integration:** The Binder seeks to "perfect the stitch." Completing a specific sequence of failed scripts may offer a path to a different ending, halting the ink-bleed cycle.
