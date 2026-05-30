# Development Roadmap & Feature Backlog

## Roadmap Priorities
- **Phase 1 (Current): Core Gameplay Loop.** Focus exclusively on hostile game world mechanics: vector physics, modular assembly, enemy AI, and combat collision.
- **Phase 2 (Future): Hub & Narrative Polish.** Visual expansion of the Sanctuary, advanced NPC dialogue branching, and environment tiling sheets.

---

## Feature Backlog & Future Proposals

> **DISCLAIMER:** This document contains unimplemented features and speculative ideas. Nothing listed here is currently active or guaranteed for immediate production. This serves as a "parking lot" for high-concept mechanical and aesthetic refinements.

---

## 1. Combat Refinement
- **Parry Window:** Implement a frame-perfect parry mechanic that staggers enemies and resets the dash cooldown.
- **Weapon Arts:** Unique special attacks for anomalous weapons (e.g., Ink Bleed triggering a small AoE puddle).
- **Stamina Management:** A "Quill Pressure" meter that limits rapid-fire attacks and dashes, encouraging tactical positioning.

## 2. Input & Accessibility
- **Gamepad Support:** Native controller mapping for Xbox/PlayStation layouts.
- **Remappable Keys:** In-game menu for custom keyboard/controller bindings.
- **Screen Shake Toggle:** Ability to disable or reduce intense combat visual effects.

## 3. Audio & Atmosphere
- **Noir Soundtrack:** Procedural ambient tracks that shift intensity based on proximity to enemies or the Rain.
- **SFX Palette:** Unique sound profiles for different quill types (metal scratching, wet ink splashes, heavy blunt thuds).
- **Environment Audio:** Directional audio for candelabras, wellsprings, and the distant rumble of the author's madness.

## 4. Narrative & Visuals
...
- **Chapter Titles:** Large typographic overlays when entering new modular zones.

## 5. Technical & Network (Future Phases)
- **LAN Multiplayer:** Implement UDP broadcast (`SO_BROADCAST`) for automatic game discovery on the same subnet.
- **Authoritative State:** Design the engine to treat the host's world as the single source of truth, synchronizing client positions via TCP streams.
- **State Serialization:** Ensure player entities cleanly serialize position and movement vectors into lightweight JSON/byte structs for low-latency networking.

## Phase 2: Combat Refinement & Physical Polishing
- **Dynamic Proximity Music Trigger Modules:**
  - **The Engagement Hook:** When an entity with `.is_miniboss == True` enters an aggressive/hostile state with the player, the engine fades down the exploration track and crossfades into `miniboss_combat.ogg`.
  - **The 15-Meter Proximity Rule:** The engine continuously calculates the Euclidean distance between the active player sprite and the hostile miniboss. 
  - **The 3-Second Ticking Cooldown:** If the distance exceeds 15 meters continuously for greater than or equal to 3.0 seconds, the engine flags the combat track to fade out and smoothly restores the regional exploration theme.

## 6. Binder Scripts (Upgrade System)
- **Concept:** The Binder NPC acts as a procedural artisan, weaving "Scripts" (operational metaphors like "Hemming Script" for HP buffs) into the player's frame using Torn Pages.
- **Mechanics:** Scripts act as tiny compilers in the margins altering stat allocations. They can be combined but are subject to "syntax conflicts" where scripts touching the same stat will fight, with the stronger one winning.
- **Lore Integration:** The Binder seeks to "perfect the stitch." Completing a specific sequence of failed scripts may offer a path to a different ending, halting the ink-bleed cycle.
