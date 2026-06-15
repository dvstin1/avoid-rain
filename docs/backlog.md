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
- **Layered Visual System (Ghost Indicators):** [DONE] Implement a decoupled animation system that uses abstract indicators (color tints, squashing, borders) to represent states (WOUNDED, STAGGERED, BIND) without finalized assets.
- **Logical Effect Buffer:** Create an engine-side queue for visual events (INK_DEATH, PARRY_SPARK) that the renderer consumes, ensuring visuals remain decoupled from logic.
- **Chapter Titles:** Large typographic overlays when entering new modular zones. (Partially implemented as Typographic Bloom).

## 4. Technical & Navigation (Future Phases)
- **A* Pathfinding:** Implement a dedicated pathfinding engine to allow Actors (Enemies and NPCs) to navigate around walls and obstacles autonomously.
    - **Dynamic Calculation:** Instead of simple linear vectors, actors will compute a tile-based route to their next PatrolPoint.
    - **Optimization:** Utilize a heat-map or hierarchical A* to manage the large 440x440 grid efficiently in Python.
    - **Obstacle Awareness:** Pathfinding must account for both static wall tiles and solid GameObjects (Bookcases, Candelabras).
- **LAN Multiplayer:** Implement UDP broadcast (`SO_BROADCAST`) for automatic game discovery on the same subnet.
- **State Serialization:** Ensure player entities cleanly serialize position and movement vectors into lightweight JSON/byte structs for low-latency networking.

## 5. Network & Multiplayer Stabilization (High Priority)
- **Client Healing Regressions:**
    - Using a heal as a client sometimes consumes all charges instantly.
    - Healing effects often fail to apply to actual health for clients (authoritative desync).
- **Respite Desync:** Respites are not functioning correctly for clients, preventing level-ups and state checkpoints.
- **Boss Visibility:**
    - Clients cannot see the Night 2 Boss when it manifests.
    - Clients cannot see the "Appendix Revealed" bloom or the resulting Appendix Warp portal.
- **Combat Balance:** Damaging enemies as a client currently results in 'instant kills' regardless of enemy HP, suggesting a multi-hit or data parsing glitch on the Host.

## 6. Combat Refinement (Speculative)
- **Weapon Arts:** Unique special attacks or passive effects for "Anomalous" weapons (e.g., Ink Bleed triggering a small AoE puddle on strike).
- **Quill Pressure (Stamina):** A resource meter that limits rapid-fire attacks and dashes, encouraging tactical positioning and deliberate timing.
- **Advanced Stagger Mechanics:** Variable stagger thresholds based on weapon weight or impact force.

## 7. Binder Scripts (Upgrade System)
- **Concept:** The Binder NPC acts as a procedural artisan, weaving "Scripts" (operational metaphors like "Hemming Script" for HP buffs) into the player's frame using Torn Pages.
- **Mechanics:** Scripts act as tiny compilers in the margins altering stat allocations. They can be combined but are subject to "syntax conflicts" where scripts touching the same stat will fight, with the stronger one winning.
- **Lore Integration:** The Binder seeks to "perfect the stitch." Completing a specific sequence of failed scripts may offer a path to a different ending, halting the ink-bleed cycle.

## 8. Atmospheric Polish & Micro-Animations
Small, code-driven visual beats to enhance the "Scriptorium Noir" feel.
- **Enhanced Death Sequence (Text Bleaching):** Replace the static gray overlay with a dynamic saturation drop and camera pull-back as the player "fades into a rejected draft."
- **Tactile Menu Transitions:** Implement unrolling or sliding animations for the Chronicle (Title/Pause) menus to make them feel like physical parchment.
- **Respite Activation Pulse:** Add a localized typographic bloom effect (drifting letters/glyphs) when resting at a Respite anchor.
- **Typographic Run-Start:** Animate the world map "inking" itself using letters cascading into the room shapes during the Chronicle transition.

## 9. Expanded Progression & Global Leveling
- **Capability Thresholds:** Currently, the player's global 'Understanding' level strictly dictates passive damage reduction. In the future, reaching specific total level thresholds (e.g., Level 5, Level 10) should automatically unlock new capabilities or narrative dialogue paths to provide distinct progression milestones.
