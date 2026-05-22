# Weather and World Progression

This document defines the environmental evolution and mechanical shifts that occur during a standard gameplay cycle.

## 1. The Climate Engine Lifecycle

The world of *Avoid Rain* is governed by a rhythmic, corrosive ink-storm known as "The Bleed". Each run follows a 4-stage progression that dictates the player's strategic options.

### Phase 1: Clear Day (Exploration Window)
- **Duration:** 0:00 - 10:00
- **Environmental Hazard:** None.
- **Rules:** The player is free to explore the macro-grid chambers and scavenge for resources.
- **Respites:** Fully active and operational.

### Phase 2: The Bleed (The Corrosive Ink-Storm)
- **Duration:** 10:00 - 15:00 (Variable window)
- **Hazard:** High-density corrosive rain particles.
- **The Closing Shrink:** A safe radial zone begins to shrink toward a randomized central coordinate.
- **Damage:** Players outside the safe zone take 2 damage per second (scaled by `dt`).
- **Respites:** Deactivated and unusable.

### Phase 3: The Dilution (Post-Boss Transition)
- **Trigger:** Occurs immediately upon the defeat of the chapter's Final Boss.
- **Atmosphere:** Rain shifts to a gentle, vertical descent with a translucent white palette.
- **Hazard:** Environmental damage is disabled.
- **Navigation:** The radial boundary dissolves; full map access is restored.

### Phase 4: Clear Night (The Breather)
- **Duration:** Until the next run cycle begins.
- **Atmosphere:** Rain fades out completely over 3 seconds.
- **Respites:** Restored to full functionality.

## 2. World Progression & Scaling

As the player progresses through chapters, the world adapts both in scale and difficulty.

### The Macro-Grid Topology
To facilitate the 10-minute exploration phase, the world uses a massive $120 \times 120$ tile grid. This grid is composed of:
- **Core Framework (Tissue):** The solid walkways and navigational pathways.
- **Modular Sectors:** $20 \times 20$ tile cavities where combat and specific layouts (like `chapter1`) are injected.

### Survival Strategy
1. **Scouting:** Use the first 10 minutes to locate Respites and collect Torn Pages.
2. **Migration:** As "The Bleed" begins, monitor the UI to identify the center of the safe zone and begin moving inward.
3. **Stand-off:** Prepare for the Boss instantiation at the center of the shrinking circle.

## 3. Zone Specific Rules
- **Sanctuary (Hub):** Rain is disabled, and the timer is paused.
- **Dungeon (Chapters):** Full weather cycle active.
- **Boss Arena:** Timer freezes; weather is suppressed during active combat to focus on the duel.
