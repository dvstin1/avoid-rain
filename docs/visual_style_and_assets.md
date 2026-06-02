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
        ├── final_reckoning.ogg   # Peak structural arrangement (Final Author)
        └── victory_theme.ogg     # 10s serene crescendo for the Chapter Complete sequence
    └── sfx/
        ├── attack_swing.ogg      # A sharp, metallic "sing" or "whoosh" (The Whiff)
        ├── attack_hit.ogg        # A heavy "thud" or "ink splash" (Overlay with swing for landed hits)
        ├── enemy_telegraph.ogg   # A sharp, high-pitched "shink" or "glint" (Start of wind-up)
        ├── combat_parry.ogg      # A resonant, high-frequency "clang" (Successful parry)
        ├── player_hurt_rain.ogg  # A low, sizzling hiss (played when receiving acid damage)
        ├── bleed_start.ogg       # A distant, seismic rumble followed by a low mechanical grind
        ├── respite_rest.ogg      # A warm, harmonic chime that resolves with a soft exhale
        ├── player_dash.ogg       # A rapid, cutting wind whoosh
        ├── player_block.ogg      # A heavy wooden thud or metallic clunk
        ├── flask_use.ogg         # A liquid slosh followed by a soft glass "tink"
        ├── page_pickup.ogg       # A dry paper rustle or crisp parchment snap
        ├── weapon_swap.ogg       # A metallic slide or quill-scratching-stone sound
        ├── warp_trigger.ogg      # A low-frequency mystical hum or "vacuum" sound
        ├── enemy_death.ogg       # A wet ink splash or shattering glass sound
        ├── prop_break.ogg        # Splintering wood or crumbling stone thud
        ├── menu_navigate.ogg     # A soft, typewriter-key click
        └── menu_confirm.ogg      # A resonant "stamp" or heavy ink-blot sound
```

### Technical Specs for Victory Theme
- **Duration:** Exactly 10.0 seconds to match the "Dilution" extraction window.
- **Composition:** Should begin with a sharp resolution of the tension, followed by a serene, atmospheric fade-out that bridges the gap between the final arena and the Scriptorium hub.
- **Trigger:** Played automatically upon the defeat of The Final Author during the "CHAPTER COMPLETE" bloom overlay.

### SFX Production Guidelines
- **The Layered Attack Rule:** To maximize feedback, landed attacks should trigger *both* `attack_swing.ogg` and `attack_hit.ogg` simultaneously. This creates a distinct, weighted feel compared to a "whiff" which only plays the swing.
- **The Environmental Hiss:** `player_hurt_rain.ogg` should be short and loopable, providing constant auditory feedback that the player is currently exposed and losing health.
- **The Seismic Rumble:** `bleed_start.ogg` triggers the moment the safe circle begins a contraction phase, signaling that the "margins are shifting."
- **The Respite Resolution:** `respite_rest.ogg` should feel like a moment of absolute safety, cleansing the cold "ink" atmosphere with a warmer tonal palette.
