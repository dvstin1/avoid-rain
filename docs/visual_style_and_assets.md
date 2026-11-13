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
Entities and interactive obstacles registered in `constants.py` and `tools/edit_map.py`:

| Entity | Symbol | Dimensions | Type | Traits / Visual Description |
| :--- | :--- | :--- | :--- | :--- |
| **Player (Scholar)** | `P` | 32x32 | Player | Kinematic scholar with hooded cloak, cowl, and shield |
| **Wall Tile** | `#` / `X` | 40x40 | Tile | Solid structural wall obstacle / perimeter boundary |
| **Floor Tile** | `.` / ` ` | 40x40 | Tile | Walkable floor surface with multi-strata elevation |
| **Grass Floor** | `g` | 40x40 | Tile | Passable grass with decorative tufts and biome clutter |
| **Overgrown Thicket**| `G` | 40x40 | Tile | Dense overgrowth vegetation layer |
| **Barrel** | `B` | 40x40 | Prop | Solid breakable prop with 1 HP; can contain loot |
| **Bench** | `S` | 40x80 | Obstacle | Solid sitting bench prop (spans 1x2 tiles) |
| **Rock / Clutter** | `K` | 40x40 | Obstacle | Non-solid/solid obstacle: rock cluster, ruins rubble, crypt clutter |
| **Structure** | `T` | 40x40 | Structure | Shelter structure: trees in forest, giant fungi in swamp |
| **Bookcase** | `h` | 80x40 | Prop | Solid heavy horizontal bookcase (spans 2x1 tiles) |
| **Ink Urn** | `d` | 40x40 | Prop | Solid ink urn prop; slowly drips ink hazard puddles |
| **Ink Puddle** | `v` | 40x40 | Hazard | Non-solid ink pool hazard (-50% speed penalty) |
| **Candelabra** | `l` | 40x40 | Light | Solid iron light source candleholder prop |
| **Lotus Frame** | `M` | 40x40 | Conduit | Pulsing arcane conduit frame |
| **Lore Fragment** | `L` | 40x40 | Lore | Interactable manuscript page fragment |
| **Wellspring** | `F` | 40x40 | Wellspring | Fountain of clear water; inspects stats and bestiary |
| **Respite** | `R` | 40x40 | Respite | Open Lectern anchor; rests, heals, refills flasks, and edifies |
| **Chronicler** | `C` | 40x40 | NPC | Personification of The Libram; dialogues and run warp |
| **Warp Point** | `W` | 40x40 | Warp | Pedestal chronicle warp gateway |
| **Bat Enemy** | `A` | 40x40 | Enemy | Flying bat with flapping wings and swoop attack |
| **Slug Enemy** | `Z` | 40x40 | Enemy | Ground slug leaving toxic slime trail |
| **Flutter Enemy** | `f` | 40x40 | Enemy | Ethereal moth fluttering with powder motes |
| **Bindling Enemy** | `b` | 40x40 | Enemy | Parchment puppet with stitch lines and grab bind |
| **Smear Enemy** | `s` | 40x40 | Enemy | Liquid ink blob with pulsing core |
| **Techno-Sentry** | `Y` | 40x40 | Enemy | Ranged artillery droid with directional plasma beam |
| **Punctuation Wolf** | `w` | 36x36 | Enemy | Glyph-shaped pack predator with cyan spine arc and pounce attack (`punctuation_wolf_empowered.png` in Act 2) |
| **Miniboss M1/M2/M3**| `E`/`2`/`3`| 40x40 | Elite | Elite strains with high HP, parry windows, and page drops |
| **Night Boss** | `"night_boss"`| 80x80 | Boss | Heavy armored tyrant in `maps/night_boss_arena.json` |

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

### 4.3. Procedural Pixel Art Asset Pipeline (`generate_assets.py`)
A standalone, deterministic generator script producing 40x40 dark-fantasy grit-textured PNG assets:
- **Core Tiles & Masonry:**
  - `floor_tile.png`: Dark slate-brown ground with sand grit, scuffs, and edge vignette.
  - `wall_tile.png`, `wall_tile_cracked.png`, `wall_tile_mossy.png`, `wall_tile_webbed.png`: 4 masonry variants.
- **Natural Biome Surfaces (100% Opaque):**
  - `swamp_water.png`: Viscous dark fluid with algae scum and reeds.
  - `mud_turf.png`: Trampled silt and puddle silt.
  - `peat_bank.png`: Fibrous soil with exposed root filaments.
  - `swamp_wall.png`: Peat cliff embankment with layered sediment.
- **Decorative Clutter & Props (Transparent Alpha):**
  - `grass_natural.png`: Multi-seed organic foliage patch.
  - `rock_cluster.png`: Rounded stones with drop shadows and highlight bevels.
  - `chronicle.png`: Ornate reading lectern holding an open gilded magical tome with glowing cyan runes.
  - `respite.png`: "First Edition" anchor plinth — carved weathered marble/slate pedestal with inlaid brass brackets, open manuscript relief, and luminous cyan ink runes.
  - `respite_corrupted.png`: Rain-inverted Respite plinth smothered under glossy, dripping black liquid ink pools when outside the safe circle.
  - `chronicler.png`: Top-down/2.5D scholar sprite with pale parchment-ivory robes, gold-trimmed archival stole, shadowed hood framing a lantern-lit visage, and bound ledger/quill.
  - `swamp_fungus.png`: Spotted toadstools with drop shadow.
  - `swamp_gas_vent.png`: Organic pod mound with open bubbling pores.
  - `swamp_thorns.png`: Skeletal bleached ash briars.
  - `ruins_rubble.png`: Broken fluted stone pillar segments and chipped masonry debris.
  - `swamp_flora.png`: Arching marsh reeds and bioluminescent fungal clusters with spore glow halos.
  - `crypt_clutter.png`: Scattered aged parchment scrolls with faded ink text and bleached skull/bone fragments.

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
        ├── rain_loop.ogg         # Seamless heavy rainfall loop driven by storm circle proximity
        ├── bleed_start.ogg       # A distant, seismic rumble followed by a low mechanical grind
        ├── respite_rest.ogg      # A warm, harmonic chime that resolves with a soft exhale
        ├── player_dash.ogg       # A rapid, cutting wind whoosh
        ├── player_block.ogg      # A heavy wooden thud or metallic clunk
        ├── flask_use.ogg         # A liquid slosh followed by a soft glass "tink"
        ├── page_pickup.ogg       # A dry paper rustle or crisp parchment snap
        ├── weapon_swap.ogg       # A metallic slide or quill-scratching-stone sound
        ├── warp_trigger.ogg      # A low-frequency mystical hum or "vacuum" sound
        ├── storm_intro.ogg       # Swelling rain + electric lightning crack + rolling thunder (title intro)
        ├── chronicle_open.ogg    # Mystical parchment flutter + arcane chime for Chronicle interaction
        ├── chronicler_mumble_neutral.ogg       # Chronicler closed-mouth conversational mumble
        ├── chronicler_mumble_happy.ogg         # Chronicler upbeat closed-mouth mumble (post-victory)
        ├── chronicler_mumble_disappointed.ogg  # Chronicler quiet, low closed-mouth mumble (post-defeat)
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

### 6.1. Procedural SFX Asset Pipeline (`generate_sfx.py`)
Modeled after `generate_assets.py` and `generate_maps.py`, `generate_sfx.py` is a standalone offline DSP synthesizer that outputs game-ready 44.1 kHz mono Ogg Vorbis (`.ogg`) files into `assets/audio/sfx/` and verifies every output with `pygame.mixer.Sound`:
- **DSP Engine:** Supports ADSR/exponential/swell/arch envelopes, exponential pitch sweeps & drops, band-limited additive oscillators & 2-op FM, white/pink/brown noise & sparse crackle, RBJ biquad filters (`lowpass`, `highpass`, `bandpass`, `peak`, and swept cutoffs), soft-clipping, bit-crushing, DC blocking, and peak normalization (`PEAK_TARGET = 0.85`). Uses `numpy` when available with a pure-Python `math` fallback.
- **Presets & Manifest:** Provides 20 synthesis archetypes (`slash`, `whoosh`, `hit_flesh`, `hit_armor`, `explosion`, `footstep`, `pickup`, `level_up`, `ui_select`, `warp`, `arcane`, `boss_roar`, `glint`, `hiss`, `rumble`, `rustle`, `splash`, `rain`, `mumble`, `storm_intro`) and `SOUND_RECIPES` covering the engine SFX files.
- **CLI Usage:**
  - `python generate_sfx.py` — Auto-fill all missing `.ogg` references across the codebase and manifest.
  - `python generate_sfx.py --list-missing` — Report missing `.ogg` references and their source lines.
  - `python generate_sfx.py --preset <name> --name <stem> --seed <N> --variants <K>` — Audition seeded variations into `assets/audio/sfx/variants/`.
