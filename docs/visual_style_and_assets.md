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
| **Player (Scholar)** | `P` | 32x32 (40x40 rig) | Player | 8-direction steep-overhead paper-doll rig (`draw_player_rig`) with visible equipped weapon |
| **Wall Tile** | `#` / `X` | 40x40 | Tile | Solid structural wall obstacle / perimeter boundary |
| **Floor Tile** | `.` / ` ` | 40x40 | Tile | Walkable floor surface with multi-strata elevation and softened floor-zone seams |
| **Grass Floor** | `g` | 40x40 | Tile | Passable grass with decorative tufts and biome clutter |
| **Overgrown Thicket**| `G` | 40x40 | Tile | Dense overgrowth vegetation layer |
| **Barrel** | `B` | 40x40 | Prop | Solid breakable prop with 1 HP; can contain loot or mimic ambush |
| **Bench (4-Way)** | `S` | 80x40 / 40x80 | Obstacle | Multi-directional oak bench (`south`/`north` 80x40; `east`/`west` 40x80 via `entities["x,y"]["facing"]`) |
| **Fire Chalice** | `V` | 80x80 | Prop | Solid 2x2 blazing bronze fire chalice monument (`vitreous_basin`) |
| **Rock / Clutter** | `K` | 40x40 | Obstacle | Biome rock cluster, ruins rubble, salt spires, or crypt clutter |
| **Structure** | `T` | 40x40 | Structure | Shelter structure: trees in forest, giant fungi in swamp, pillars in aqueducts |
| **Bookcase** | `h` | 80x40 | Prop | Solid heavy horizontal bookcase (spans 2x1 tiles) |
| **Ink Urn** | `d` | 40x40 | Prop | Solid ink urn prop; slowly drips ink hazard puddles |
| **Ink Puddle** | `v` | 40x40 | Hazard | Non-solid ink pool hazard (-50% speed penalty) |
| **Candelabra** | `l` | 40x40 | Light | Solid iron light source candleholder prop |
| **Lotus Frame** | `M` | 40x40 | Conduit | Pulsing arcane conduit frame |
| **Lore Fragment** | `L` | 40x40 | Lore | Interactable manuscript page fragment |
| **Wellspring** | `F` | 40x40 | Wellspring | Fountain of clear water; inspects stats and bestiary |
| **Respite** | `R` | 40x40 | Respite | Open Lectern anchor; rests, heals, refills flasks, triggers activation pulse, and edifies |
| **Chronicler** | `C` | 40x40 | NPC | Personification of The Libram; dialogues and run warp |
| **The Binder** | `&` | 40x40 | NPC | Sanctuary Scriptorium artisan (`binder.png`); weaves persistent Binder Scripts for `margin_scraps` |
| **Warp Point** | `W` | 40x40 | Warp | Pedestal chronicle warp gateway |
| **Bat Enemy** | `A` | 40x40 | Enemy | Flying bat with flapping wings and swoop attack |
| **Slug Enemy** | `Z` | 40x40 | Enemy | Ground slug leaving toxic slime trail |
| **Flutter Enemy** | `f` | 40x40 | Enemy | 3-frame animated ethereal manuscript moth with powder motes |
| **Bindling Enemy** | `b` | 40x40 | Enemy | Parchment puppet with stitch lines and grab bind |
| **Smear Enemy** | `s` | 40x40 | Enemy | Liquid ink blob with pulsing core and fading ink puddles |
| **Techno-Sentry** | `Y` | 40x40 | Enemy | Ranged artillery droid with directional plasma beam |
| **Punctuation Wolf** | `w` | 36x36 | Enemy | Glyph-shaped pack predator with cyan spine arc and pounce attack (`punctuation_wolf_empowered.png` in Acts 3–5) |
| **Miniboss M1/M2/M3**| `E`/`2`/`3`| 64x64 | Elite | Elite strains with 3-frame directional sprites, parry windows, and page/weapon drops |
| **Night Boss** | `N` | 64x64 | Boss | Act Night Boss (`NightBoss`, `SlugBoss`, `MeadowCensorBoss`, `RimecrestArbiterBoss`) with 3-frame directional sheets |
| **The Final Author** | `!` | 80x80 | Final Boss | Sovereign quill-crowned Final Boss in `maps/night_boss_arena.json` (`final_author*.png`) |

## 3. The Redacting Circle Visuals (The Bleed)
The weather system transitions through distinct visual phases:
- **Clearance / Grace:** Atmosphere is completely clear. No particles.
- **Ink-Collapse (Storm):** Dense, high-velocity vertical green particles. The safe zone is demarcated by a glowing orange boundary ring.
- **The Dilution (Victory):** Ink-rain washes out into a soft, safe blue. The boundary ring dissipates.

## 4. Asset Manifest & VFX
### 4.1. Sprites & Animations
- **Player & Remote Co-op Rig (`Renderer.draw_player_rig()`):** 8-direction steep-overhead (25–35°) paper-doll rig combining a procedural shadow/boots/cloak-hem/hand-anchor base layer, 20 generated 40x40 hood-and-shoulder pixmaps (`player_hood_<n|ne|e|se|s>_<idle|walk_0|walk_1|attack>.png`, horizontally mirrored in RAM across all 32 direction×pose slots), and a rotated visible equipped-weapon sprite layer (`weapon_*.png`). Reused for 60 FPS interpolated remote LAN players with Cyan (Host) / Magenta (Guest) trim.
- **Enemies:** Slugs (4-frame walk + 2-frame attack), Flutters (3-frame base & empowered), Bats, Bindlings, Smears, Techno-Sentries, and Punctuation Wolves, each with empowered Acts 3–5 variants (`*_empowered.png`).
- **Biome Night Bosses & Final Author:** 3-frame directional walk animations (down, side, up) for `Miniboss`, `NightBoss`, `SlugBoss` (plus `slug_boss_crown.png`), `MeadowCensorBoss` (plus `meadow_censor_scythe.png`), `RimecrestArbiterBoss` (plus `rimecrest_halberd.png`, `frozen_ice_block_0..2.png`), and `FinalAuthor`.
- **Environment:** Sanctuary Scriptorium tiles/roofs/doorways, softened 1px+1px biome floor-zone seams (`FLOOR_SEAM_*`), and full biome prop sets across all 7 run biomes (`windy_ridge`, `pastoral_valley`, `swamp_mire`, `frozen_peaks`, `tech_tower`, `vitreous_basin`, `sunlit_aqueducts`).

### 4.2. UI & VFX
- **Typographic Bloom:** Large, stylized serif titles for zone discovery, Act saturation transitions, and system alerts.
- **Boss Summoning Ritual:** Grey vellum ground circle that erupts on proximity (`BOSS_SUMMON_ERUPTION_RADIUS = 140.0`) with rising typographic glyph squares, `boss_summon.ogg`, and delayed boss music drop.
- **Enhanced Death Sequence (Text Bleaching):** Progressive luminance desaturation, subtle camera pull-back framing the shrinking scene inside a dark-ink manuscript margin, rising pale parchment washout, and staged `"TEXT BLEACHING..."` fade-in.
- **Respite Activation Pulse:** Localized expanding cyan-ink/parchment double ring and rising, swaying drifting manuscript glyphs on Respite rest.
- **Tactile Menu Transitions:** Parchment unroll and vertical-slide animation with a fading scroll roller across Title, Pause, Confirm, and Controls menus.
- **Damage Numbers & Stagger Outlines:** Floating colored text (Red for damage, Yellow for criticals) and 100ms high-contrast outlines for hit-stop feedback.
- **HUD & Boss Bars:** Compact `252x148` lower-left visual HUD (HP bar, Flask vials, Pages, Edification level, dual weapon slots, contextual pickup pill) and bottom-center Boss Name & Health Bar (`Renderer.draw_boss_hud()`).

### 4.3. Procedural Pixel Art Asset Pipeline (`generate_assets.py`)
A standalone, deterministic generator script managing **220** dark-fantasy grit-textured PNG assets under `assets/graphics/`:
- **Core Tiles, Masonry & 2.5D Verticality:**
  - `floor_tile.png`, `wall_tile.png`, `wall_tile_cracked.png`, `wall_tile_mossy.png`, `wall_tile_webbed.png`, `wall_top_cap.png`, `wall_front_face.png`, `shadow_south.png`, `shadow_east.png`, `shadow_corner.png`, `cliff_edge.png`, `staircase_tile.png`, `pit_rim.png`, `boss_dais_tile.png`, `boss_pillar_tile.png`, `boss_abyss_rim.png`.
- **Sanctuary & 7-Biome Terrain / Props:**
  - Sanctuary: `sanctuary_wood_floor_0..3.png`, `sanctuary_flagstone_0..3.png`, `sanctuary_dirt_path_0..3.png`, `sanctuary_roof_tile*.png`, `sanctuary_arch_doorway.png`, `sanctuary_window_wall.png`, `sanctuary_chimney.png`, `sanctuary_tree_canopy.png`, `pond_lily_reeds.png`, `garden_flora.png`.
  - Swamp / Pastoral / Frozen / Tech / Vitreous / Aqueducts: `swamp_water.png`, `mud_turf.png`, `peat_bank.png`, `swamp_wall.png`, `swamp_fungus.png`, `swamp_gas_vent.png`, `swamp_thorns.png`, `swamp_flora.png`, `swamp_barrel.png`, `swamp_spore_pod.png`, `pastoral_hay_crate.png`, `pastoral_rock.png`, `pastoral_shepherd_cairn.png`, `frozen_rime_cask.png`, `frozen_script_monolith.png`, `frozen_ice_block_0..2.png`, `tech_canister.png`, `tech_server_pylon.png`, `vitreous_salt_floor.png`, `vitreous_glass_flat.png`, `vitreous_salt_spire.png`, `vitreous_fire_chalice.png` (80x80), `aqueduct_terracotta_floor.png`, `aqueduct_moss_wall.png`, `aqueduct_pillar.png`.
- **Landmarks, Interior Props & Weapons (Transparent Alpha):**
  - `chronicle.png`, `respite.png`, `respite_corrupted.png`, `chronicler.png`, `binder.png`, `wellspring.png`, `lotus_frame.png`, `heavy_bookcase.png` (80x40), `ink_urn.png`, `inkwell_puddle.png`, `candelabra.png`, `tree_structure*.png`, `barrel_0..3.png`, `ruins_rubble.png`, `crypt_clutter.png`, `grass_natural.png`, `rock_cluster.png`, `torn_page.png`.
  - Multi-Directional Benches: `bench.png` (80x40 south), `bench_north.png` (80x40 north), `bench_east.png` (40x80 east), `bench_west.png` (40x80 west).
  - Player Rig & Weapons: 20 `player_hood_*.png` directional poses + 8 weapon sprites (`weapon_quill_standard.png`, `weapon_quill_refined.png`, `weapon_scriber_blade.png`, `weapon_anomalous_default.png`, `weapon_anomalous_bleed.png`, `weapon_anomalous_regen.png`, `weapon_anomalous_negation.png`, `weapon_anomalous_stout.png`).
- **Enemies & Multi-Frame Boss Sheets (Transparent Alpha):**
  - Base & empowered standard castes (`bat*.png`, `flutter*.png`, `bindling*.png`, `smear*.png`, `sentry*.png`, `punctuation_wolf*.png`, `slug_*.png`, `event_champion.png`).
  - 9-frame directional boss packs (`miniboss*.png`, `night_boss*.png`, `boss_empowered*.png`, `slug_boss*.png`, `meadow_censor_boss*.png`, `rimecrest_arbiter_boss*.png`, `final_author*.png`).

### 4.4. Procedural Bitmap Font Pipeline (`generate_fonts.py` & `rendering/bitmap_font.py`)
Replaces generic system fonts (`pygame.font.SysFont`) with deterministic white-on-transparent (`RGBA`) glyph sprite sheets and JSON metric sidecars under `assets/fonts/`, wrapped at runtime by `BitmapFont`:
- **`ink_sans` (`assets/fonts/ink_sans.png` + `.json`, base height `12px`):** Proportional pixel font scaled `1x` (`12px`, `slot_font`), `2x` (`24px`, `font`), and `3x` (`36px`, `large_font`).
- **`ink_mono` (`assets/fonts/ink_mono.png` + `.json`, base height `14px`):** Fixed-cell `8x14` monospace glyph sheet (`1x` `14px`) for `small_font`, `hud_font`, and `glyph_font`.
- **`manuscript_serif` (`assets/fonts/manuscript_serif.png` + `.json`, base height `18px`):** Calligraphic ink-serif display font scaled `3x` (`54px`, `title_font`) and `4x` (`72px`, `bloom_font`).
- **Coverage & Fallback:** Covers all 95 printable ASCII glyphs (`32..126`), normalizes common Unicode punctuation (`—`, `–`, `’`, `‘`, `“`, `”`, `…`), and falls back gracefully on unknown non-ASCII characters.
- **CLI Specimen Sheet:** `python3 generate_fonts.py --specimen [output_path]` renders a contact sheet of all 95 ASCII glyphs and `1x`/`2x`/`3x` sample lines without modifying `assets/`.

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
    ├── music/ (14 tracks)
    │   ├── title_theme.ogg           # Minimalist recorder & slow book slides
    │   ├── sanctuary_hub.ogg         # Somber, hollow kalimba tracking
    │   ├── world_exploration.ogg     # Low ambient drone & distant percussion
    │   ├── death_theme.ogg           # Single descending recorder tone & dead silence
    │   ├── miniboss_combat.ogg       # Tense, rhythmic ad-hoc book slams
    │   ├── night_boss.ogg            # Default aggressive Night Boss theme
    │   ├── slug_boss_phase1.ogg      # Swamp Night Boss (SlugBoss) Phase 1 theme
    │   ├── slug_boss_phase2.ogg      # Swamp Night Boss (SlugBoss) Phase 2 army summon theme
    │   ├── pastoral_boss_phase1.ogg  # Pastoral Valley (MeadowCensorBoss) Phase 1 folk theme
    │   ├── pastoral_boss_phase2.ogg  # Pastoral Valley (MeadowCensorBoss) Phase 2 tarantella theme
    │   ├── frozen_boss_phase1.ogg    # Frozen Peaks (RimecrestArbiterBoss) Phase 1 glacial theme
    │   ├── frozen_boss_phase2.ogg    # Frozen Peaks (RimecrestArbiterBoss) Phase 2 glacial theme
    │   ├── final_reckoning.ogg       # Peak structural arrangement (Final Author)
    │   └── victory_theme.ogg         # 10s serene crescendo for the Chapter Complete sequence
    └── sfx/ (41 files)
        ├── sword_swing.ogg / sword_hit.ogg        # Pitch-jittered melee swing & once-per-swing hit layer
        ├── attack_swing.ogg / attack_hit.ogg      # Legacy/fallback attack swing & impact layers
        ├── enemy_telegraph.ogg / combat_parry.ogg # Wind-up glint & resonant parry clang
        ├── boss_summon.ogg / bleed_start.ogg      # Boss ritual eruption & storm contraction rumble
        ├── rain_loop.ogg / player_hurt_rain.ogg   # Proximity-scaled rainfall loop & acid hiss
        ├── player_hurt.ogg / player_dash.ogg / player_block.ogg
        ├── flask_use.ogg / flask_empty.ogg / page_pickup.ogg / weapon_swap.ogg
        ├── respite_rest.ogg / warp_trigger.ogg / door_open.ogg / water_step.ogg
        ├── storm_intro.ogg / chronicle_open.ogg
        ├── chronicler_mumble_{neutral,happy,disappointed}.ogg
        ├── bat_{attack,move}.ogg / slug_{attack,move}.ogg / wolf_{attack,telegraph}.ogg
        ├── slug_boss_slime.ogg / meadow_censor_whistle.ogg / frost_breath.ogg
        ├── ice_crack.ogg / ice_shatter.ogg
        ├── enemy_death.ogg / prop_break.ogg / menu_navigate.ogg / menu_confirm.ogg
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
