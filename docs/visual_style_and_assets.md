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
| **Player** | `P` | 32x32 | Blue | Kinematic (TILE_SIZE 40) |
| **Wall Tile** | `#` | 40x40 | Dark Gray | Solid |
| **Bookcase** | `h` | 2x1 Tiles | Charcoal | Solid |
| **Ink Urn** | `d` | 1x1 Tile | Slate Blue | Solid |
| **Ink Puddle** | `v` | 1x1 Tile | Black | Hazard (-50% Speed) |
| **Candelabra** | `l` | 1x1 Tile | Amber/Gray | Light Source |

## 3. The Redacting Circle Visuals (The Bleed)
The weather system transitions through distinct visual phases:
- **Clearance / Grace:** Atmosphere is completely clear. No particles.
- **Ink-Collapse (Storm):** Dense, high-velocity vertical green particles. The safe zone is demarcated by a glowing orange boundary ring.
- **The Dilution (Victory):** Ink-rain washes out into a soft, safe blue. The boundary ring dissipates.

## 4. Asset Manifest & VFX
### 4.1. Sprites & Animations
- **Player:** 4-directional walk cycles, attack swings, dashing frames, shield-up stance.
- **Enemies:** Slugs, bats (with wing indicators), smears, and large-scale 2 boss variants.
- **Night Boss:** The ultimate high-tier encounter manifesting in Act II.
- **Environment:** Hub training room, The Libram (book), Respite silhouettes.

### 4.2. UI & VFX
- **Typographic Bloom:** Large, stylized serif titles for zone discovery and system alerts.
- **Damage Numbers:** Floating colored text (Red for damage, Yellow for criticals).
- **Stagger Outlines:** 100ms high-contrast outlines for hit-stop feedback.
- **Bars:** Health, Stamina, and Defense meters. Flask charge counter.

## 5. Art Blueprint Protocols
### 5.1. SVG Generation Rules
- **One per Query:** The agent must output exactly ONE XML SVG block per user query to manage token budget.
- **Tracing Templates:** SVGs are layout guides for Krita/Wacom tablet tracing. Use `shape-rendering="crispEdges"`.
- **Geometric Purity:** Use simple `<rect>`, `<circle>`, and `<path>` tags with flat hex colors.

## 6. Audio Asset Manifest & Technical Standards
To ensure clean loops, the engine utilizes the OGG Vorbis (.ogg) format for all music tracks.

### Asset Directory Tree Structure
```text
assets/
└── audio/
    └── music/
        ├── title_theme.ogg       # Minimalist recorder & slow book slides
        ├── sanctuary_hub.ogg     # Somber, hollow kalimba tracking
        ├── world_exploration.ogg # Low ambient drone & distant percussion
        ├── death_theme.ogg       # Single descending recorder tone & dead silence
        ├── miniboss_combat.ogg   # Tense, rhythmic ad-hoc book slams
        ├── night_boss.ogg        # Aggressive, building composition
        └── final_reckoning.ogg   # Peak structural arrangement
```
