# Development Roadmap & Feature Backlog

## Roadmap Priorities
- **Phase 1 (Current): Core Gameplay Loop.** Focus exclusively on hostile game world mechanics: vector physics, modular assembly, enemy AI, and combat collision.
- **Phase 2 (Future): Hub & Narrative Polish.** Visual expansion of the Sanctuary, advanced NPC dialogue branching, and environment tiling sheets.

---

## Feature Backlog & Future Proposals

> **DISCLAIMER:** This document contains unimplemented features and speculative ideas. Nothing listed here is currently active or guaranteed for immediate production. This serves as a "parking lot" for high-concept mechanical and aesthetic refinements.

---

## 1. Combat Refinement & The Parry System

This system aims to transform combat from simple proximity damage to a high-skill "dance" of anticipation and reaction.

### Phase 1: Telegraphed Enemy Attacks (Prerequisite)
Before a parry can be implemented, prototype enemies must be adapted to exhibit predictable, readable behaviors:
- **The Wind-Up State:** All offensive actions must begin with a clear visual "tell" (e.g., the entity flashing a "Margin Red" outline or pulsing in size for 0.3s–0.5s).
- **The Active Strike:** The actual damage-dealing frames.
- **The Recovery State:** A post-attack cooldown where the enemy is physically locked, leaving a "Stanza Gap" for the player to counter-attack or reposition.
- **Attack Variety:**
    - **Thrusts:** Linear, high-velocity lunges. Narrow hitbox, fast wind-up. Harder to dodge, easiest to parry.
    - **Swings:** Arc-based wide strikes. Slower execution, covers a larger radius. Easier to out-space, requires precise parry timing.

### Phase 2: The Frame-Perfect Parry
- **The Mechanic:** Triggered by initiating a block or dash within the first few frames of an incoming strike.
- **Visual Feedback:** A high-contrast "Spark" or "Ink Splash" at the point of impact.
- **The Reward:**
    - **Enemy Stagger:** Instantly forces the attacker into a long stagger state (0.5s–1.0s).
    - **Kinetic Reset:** Resets the player's Dash cooldown instantly, allowing for aggressive repositioning.
- **Weapon Arts:** Unique special attacks for anomalous weapons (e.g., Ink Bleed triggering a small AoE puddle).
- **Stamina Management:** A "Quill Pressure" meter that limits rapid-fire attacks and dashes, encouraging tactical positioning.

## 2. Input & Accessibility
- **Gamepad Support:** Native controller mapping for Xbox/PlayStation layouts.
- **Remappable Keys:** In-game menu for custom keyboard/controller bindings.
- **Screen Shake Toggle:** Ability to disable or reduce intense combat visual effects.

## 3. Audio & Atmosphere
- **Noir Soundtrack:** Procedural ambient tracks that shift intensity based on proximity to enemies or the Rain.
- **Layered SFX Feedback:**
    - **Combat:** Distinct sounds for attack whiffs (`attack_swing.ogg`) vs. hits (layered `attack_swing` + `attack_hit`).
    - **Environment:** Immediate auditory feedback for acid rain exposure (`player_hurt_rain.ogg`).
    - **System Alerts:** Seismic audio cues for safe circle contraction starts (`bleed_start.ogg`).
    - **Progression:** Thematic "safety" resolution sound for Respite resting (`respite_rest.ogg`).
- **Environment Audio:** Directional audio for candelabras, wellsprings, and the distant rumble of the author's madness.

## 4. Narrative & Visuals
...
- **Chapter Titles:** Large typographic overlays when entering new modular zones.

## 5. Technical & Navigation (Future Phases)
- **A* Pathfinding:** Implement a dedicated pathfinding engine to allow Actors (Enemies and NPCs) to navigate around walls and obstacles autonomously.
    - **Dynamic Calculation:** Instead of simple linear vectors, actors will compute a tile-based route to their next PatrolPoint.
    - **Optimization:** Utilize a heat-map or hierarchical A* to manage the large 440x440 grid efficiently in Python.
    - **Obstacle Awareness:** Pathfinding must account for both static wall tiles and solid GameObjects (Bookcases, Candelabras).
- **LAN Multiplayer:** Implement UDP broadcast (`SO_BROADCAST`) for automatic game discovery on the same subnet.
...
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

---

## 7. Actor State Machine & Patrol Stanzas (The Stanza System)
This system elevates the macro-world from a simple combat arena to a "Living Manuscript" by providing complex, scriptable behaviors for all mobile entities.

### 1. Unified Actor Base Class
- **The Concept:** Merge common update logic between `Enemy` and `NPC` types into a single `Actor` hierarchy.
- **The State Machine:** Actors oscillate between the following internal states:
    - **IDLE:** Standing at a post or wandering randomly.
    - **PATROLLING:** Moving between sequential markers in a designated "Stanza."
    - **CHASE:** Aggressive pursuit of the player (Enemies only).
    - **ENGAGED:** Paused routine to interact with the player (NPCs only).

### 2. Marker-Based "Stanza" Routes
- **Opt-In Logic:** Maps without markers remain static. If an actor detects a `PatrolPoint` within proximity (e.g., 5 tiles) at spawn, they anchor to that route.
- **Route ID & Indexing:** Markers with the same `route_id` form a connected chain. The actor follows them in numerical symbol order (`1` -> `2` -> `3`).
- **The Loop Rule:** Routes are circular by default (3 -> 1) but can be configured as "back-and-forth" paths (`is_loop: False`).

### 3. The Caste Filter (Granular Scene Control)
- **Caste Definition:** Each `PatrolPoint` can have a `caste_filter` list (e.g., `["SlugEnemy"]`).
- **Exclusive Logic:** Actors only anchor to markers that match their specific type. This allows for overlapping, distinct routes (e.g., Slugs patrolling a floor while Bats sleep on a separate ceiling route).
- **Universal Routes:** If the filter is empty, any nearby actor can anchor to it.

### 4. Behavioral Nuance (Realism)
- **Stanza Speed:** Actors use their base speed but can be modified by a `patrol_speed_multiplier` (default `0.5`) to simulate "walking" vs "sprinting."
- **Patience Variable:** When reaching a marker, actors roll a randomized wait timer (`wait_min`, `wait_max`) before proceeding. 
- **The Deep Study:** Specific markers (e.g., Chronicler at a bookshelf) can be flagged with a `long_wait` attribute for extended idling.
- **Dormancy:** Enemies can be flagged as `is_stationary: True` in map data. They will remain in a "sleeping" state at their spawn point until their detection radius is breached, ignoring all patrol logic.
