# Visual Style, Assets & Art Blueprints

This document defines the "Scriptorium Noir" aesthetic and the technical protocols for asset generation and management.

## 1. The Scriptorium Noir Aesthetic
- **Mood:** Oppressive, academic, eerie, and melancholic, contrasted by the safe, warm, candle-lit Hub.
- **Palette:**
    - **Sanctuary (Warm):** Sepia, soft amber, aged parchment.
    - **Combat (Cold):** Stark charcoal, deep ink blues, cold grays.
    - **Highlights:** Glowing cyan (The Chronicle), toxic lime (Acid Rain).
- **Perspective:** Top-down orthographic (flat 2D view, no isometric skewing).

## 2. Atmospheric Entity Standards
Entities use primitive shapes during the prototyping phase, with specific colors and physics properties.

| Entity | Symbol | Dimensions | Color | Traits |
| :--- | :--- | :--- | :--- | :--- |
| **Player** | `P` | 32x32 | Blue | Kinematic |
| **Wall Tile** | `#` | 32x32 | Dark Gray | Solid |
| **Bookcase** | `h` | 2x1 Tiles | Charcoal | Solid |
| **Ink Urn** | `d` | 1x1 Tile | Slate Blue | Solid |
| **Ink Puddle** | `v` | 1x1 Tile | Black | Hazard (-50% Speed) |
| **Candelabra** | `l` | 1x1 Tile | Amber/Gray | Light Source |

## 3. The Devouring Storm Visuals
The weather system transitions through two distinct visual phases:
- **Act I (Ambient Weep):** Sparse, rhythmic background particles. Translucent grey or soft cyan.
- **Act II (Ink-Collapse):** Dense, high-velocity "heavy" particles. Deep ink-black or neon cyan. The safe zone is demarcated by a glowing amber boundary ring.

## 4. Asset Manifest & VFX
### 4.1. Sprites & Animations
- **Player:** 4-directional walk cycles, attack swings, dashing frames, shield-up stance.
- **NPCs:** Unique shopkeeper and quest-giver sprites.
- **Enemies:** Grunts, bats (with wing indicators), and large-scale 2D bosses.
- **Environment:** Hub training room, The Libram (book), Respite silhouettes.

### 4.2. UI & VFX
- **Damage Numbers:** Floating colored text (Red for damage, Yellow for criticals).
- **Stagger Outlines:** 100ms high-contrast outlines for hit-stop feedback.
- **Bars:** Health, Stamina, and Defense meters. Flask charge counter with upgrade levels (e.g., +1).

## 5. Art Blueprint Protocols
### 5.1. SVG Generation Rules
- **One per Query:** The agent must output exactly ONE XML SVG block per user query to manage token budget.
- **Tracing Templates:** SVGs are layout guides for Krita/Wacom tablet tracing. Use `shape-rendering="crispEdges"` and explicit `viewBox` coordinates.
- **Geometric Purity:** Use simple `<rect>`, `<circle>`, and `<path>` tags with flat hex colors. Avoid gradients or complex shading.

### 5.2. Registry Schema
Every asset added to the registry must include:
- **ID & Filename:** (e.g., `#03 - tile_wall_brick.svg`)
- **Dimensions:** Targeted pixel boundaries.
- **Composition:** Geometric arrangement rules (e.g., "centered horizontally").
- **Contrast Rule:** How the asset visually separates from the background.

## 4. Audio Asset Manifest & Technical Layout Standards

To ensure clean file discovery and gapless loops, the engine utilizes the OGG Vorbis (.ogg) container format for all music tracks. MP3 is avoided due to compression-induced silent padding frames which disrupt seamless repetition.

### Asset Directory Tree Structure
```text
assets/
└── audio/
    └── music/
        ├── title_theme.ogg       # Minimalist recorder & slow book slides
        ├── sanctuary_hub.ogg     # Somber, hollow kalimba tracking
        ├── world_exploration.ogg # Low ambient drone & distant percussion
        ├── death_screen.ogg      # Single descending recorder tone & dead silence
        ├── miniboss_combat.ogg   # Tense, rhythmic ad-hoc book slams
        ├── night_boss_core.ogg   # Aggressive, building composition
        └── final_reckoning.ogg   # Peak structural arrangement
```
