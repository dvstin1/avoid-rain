# Documentation Audit & Code-vs-Docs Gap Analysis

**Audit Date:** November 26, 2026  
**Auditor:** Antigravity Agent (`doc-audit` skill)  
**Target Repository:** Avoid Rain (synced against `HEAD` `05cc6a4`)

---

## 1. Executive Summary

A full `doc-audit` pass (Runbook A) was executed across the repository, surveying:
- **11 Core Architectural Documents** in `docs/` (`architecture.md`, `navigation_and_ui.md`, `modular_system.md`,
  `visual_style_and_assets.md`, `world_and_lore.md`, `persistence.md`, `reference.md`, `level_design_concept.md`,
  `backlog.md`, `testing.md`, `CHANGELOG.md`).
- **13 Extended Lore Notes** in `docs/extended-notes/` and HTML reference mocks in `docs/extended-notes/enemies/`
  and `docs/extended-notes/title-screen/` (preserved intact per Lore Preservation guardrail).
- **Central Hub & Skills:** `AGENTS.md`, `README.md`, `.gemini/skills/doc-audit/SKILL.md`, and
  `.gemini/skills/prompt-review/SKILL.md`.
- **Live Codebase Baseline:** `constants.py` (`ENGINE_REVISION = 2`, `MAX_ACTS = 5`, 7-biome roster, 39 `TILE_KEY`
  entries), `engine/` (27 modules), `rendering/renderer.py`, `tools/edit_map.py`, `maps/segments/` (56 segment JSONs),
  `assets/graphics/` (220 files), `assets/audio/music/` (14 tracks), `assets/audio/sfx/` (41 files), and `tests/`
  (136 test modules, 551 passing tests).

### Health & Alignment Score
- **Link Integrity:** 100% (automated check across `AGENTS.md`, `README.md`, and all `docs/**/*.md` found **0** broken
  relative links).
- **Archiving Compliance:** 100% (`AGENTS.md` active slot is clean at `[NONE]`; `docs/CHANGELOG.md` stray blank lines
  removed and November 2026 milestones archived through `05cc6a4`).
- **Code Alignment:** Reconciled all discovered Category B & C drifts across 7 core docs (`architecture.md`,
  `persistence.md`, `navigation_and_ui.md`, `modular_system.md`, `visual_style_and_assets.md`, `world_and_lore.md`,
  `testing.md`).

---

## 2. Category A: Documented but Unimplemented Features (Roadmap / Lore)

The previously recorded Category A items **The Binder NPC & Scripts** (`docs/backlog.md` Section 7) and **A\* Autonomous
Pathfinding** (`docs/backlog.md` Section 4) are now `[DONE]` in the live engine, and **Quill Pressure (Stamina)** was
formally `[DROPPED]` in `docs/backlog.md` Section 6. The genuinely remaining Category A items are:

1. **Environment Audio (`docs/backlog.md` Section 2):**
   - *Concept:* Positional/directional ambient audio for candelabras, wellsprings, and the distant rumble of the
     author's madness.
   - *Status:* Open backlog item (Tier 2 — Contained Mechanics & Local Audio).
2. **Capability Thresholds (`docs/backlog.md` Section 9):**
   - *Concept:* Automatic capability or narrative dialogue path unlocks at global Understanding/Edification level
     milestones (e.g., Level 5, Level 10).
   - *Status:* Open Phase 2 progression proposal (Tier 2–3).
3. **Bespoke Act 3–5 Segment Variants (`docs/backlog.md` Section 12.3):**
   - *Concept:* Dedicated high-Act room/corridor JSON geometry registered under `BIOME_ACT_SEGMENT_POOLS[(biome, 3..5)]`.
   - *Status:* Loader infrastructure (`resolve_segment_pool()`) is `[DONE]` and falls back cleanly to Act 1 pools;
     authoring bespoke Act 3–5 geometry remains an incremental content track.
4. **Market of Margins & Footnote Spirits (`docs/world_and_lore.md` Section 2.1):**
   - *Concept:* Footnote-spirit trading post in the margins between chapters.
   - *Status:* Narrative lore concept reserved for future world expansion.
5. **Constellations of the Void (`docs/world_and_lore.md` Section 2.1, `docs/extended-notes/constellations-of-the-void.md`):**
   - *Concept:* Negative space patterns on the reverse side of the page visible when held up to the Wellspring.
   - *Status:* Narrative lore concept.

---

## 3. Category B: Implemented Mechanics Missing from Documentation (Remediated)

The following live features landed between November 14 and November 26, 2026 and were missing from core technical specs
prior to this audit:

- [X] **`--offline` CLI Lockout & `install-linux.py` (`main.py`, `install-linux.py`):**
  - *Remediation:* Documented in `docs/architecture.md` Section 1.1.
- [X] **Remappable Controls (`ControlsConfigMenu`), Visual HUD Revamp (`252x148`), & Boss Health Bar HUD:**
  - *Remediation:* Updated `docs/navigation_and_ui.md` Sections 1.1, 3.1, 3.2, and 3.3.
- [X] **Gamepad Rumble Queue & Pause Toggle (`rumble_enabled`, `RUMBLE_PRESETS`):**
  - *Remediation:* Documented in `docs/architecture.md` Section 17, `docs/navigation_and_ui.md` Section 3.3, and
    `docs/persistence.md` Section 3.
- [X] **Atmospheric Micro-Animations (Text Bleaching Death Sequence, Respite Activation Pulse, Tactile Menu Transitions):**
  - *Remediation:* Documented across `docs/architecture.md` Section 17, `docs/navigation_and_ui.md` Sections 3.1/6.1,
    and `docs/visual_style_and_assets.md` Section 4.2.
- [X] **8-Direction Steep-Overhead Player Rig, Visible Equipped Weapons, & 60 FPS Remote Player Interpolation:**
  - *Remediation:* Documented in `docs/architecture.md` Section 14.1 (Phase 3) and `docs/visual_style_and_assets.md`
    Sections 2 & 4.1.
- [X] **Proximity-Triggered Boss Summon Eruption, Biome Night Bosses (`SlugBoss`, `MeadowCensorBoss`, `RimecrestArbiterBoss`), & Post-Night-Boss Full Heal:**
  - *Remediation:* Documented in `docs/architecture.md` Section 11.1–11.2 and `docs/visual_style_and_assets.md`
    Sections 2, 4.1, and 6.
- [X] **Respite Interaction & World Lifecycle Locks (`RESPITE_HOSTILE_BLOCK_RADIUS = 320.0`, Night Boss lockout, deferred aggro):**
  - *Remediation:* Documented in `docs/architecture.md` Section 9.1.
- [X] **Binder Scripts Compiler (`engine/binder_scripts.py`), The Binder (`'&'`), & Fire Chalice (`'V'`, `80x80`):**
  - *Remediation:* Documented in `docs/architecture.md` Section 17 and `docs/visual_style_and_assets.md` Sections 2 & 4.3.
- [X] **Expanded Asset & Audio Registries (220 PNGs, 14 Music Tracks, 41 SFX Files):**
  - *Remediation:* Synchronized `docs/visual_style_and_assets.md` Sections 4.3 and 6.

---

## 4. Category C: Contradictions & Drift (Remediated)

- [X] **2-Act / 5-Biome vs. 5-Act / 7-Biome Drift (`docs/architecture.md` §4.1/§16, `docs/modular_system.md` §5–6, `docs/navigation_and_ui.md` §8.5, `docs/world_and_lore.md` §3.3):**
  - *Drift:* Docs still described 2-Act runs (`generate_dual_worlds()`), 2-step Chronicle selection, and 5 biomes.
  - *Code Reality:* Live engine runs 5-Act Unbound Chronicle loops (`MAX_ACTS = 5`, `act_worlds[1..5]`) drafted from all
    7 biomes in `CHRONICLE_BIOME_ROSTER` (56 segments across 7 `maps/segments/<biome>/` pools, `ACT_MINIBOSS_BUDGET = 4`).
- [X] **Prowess Upgrade Step (`docs/architecture.md` §9.2):**
  - *Drift:* Listed Prowess as `+5 Attack`.
  - *Code Reality:* Rebalanced to `PROWESS_ATTACK_STEP = 3` (`+3 Attack`).
- [X] **Act Saturation Multipliers (`docs/architecture.md` §11.2):**
  - *Drift:* Listed `1.0x/1.25x/1.6x/2.0x/2.5x`.
  - *Code Reality:* `constants.ACT_SATURATION_MATRIX` uses HP `1.0x/1.4x/2.0x/2.8x/3.8x`, Damage
    `1.0x/1.35x/1.8x/2.35x/3.0x`, Speed `1.0x..1.28x`, `rain_dps` `2.0..4.0`, and Page yield `1.0x..2.0x`.
- [X] **Duplicate JSON Key & Missing Schema Fields (`docs/persistence.md` §3):**
  - *Drift:* `"last_run_result"` appeared twice in the example JSON block, while `"rumble_enabled"` and `"keybindings"`
    were omitted.
  - *Code Reality:* Synced against `StatisticsTracker().data` in `engine/stats.py`.
- [X] **Bench & Boss Dimensions (`docs/visual_style_and_assets.md` §2 & §4.3):**
  - *Drift:* Bench listed as `40x80` (and `bench.png` as `40x40`), Miniboss as `40x40`, Night Boss as `80x80`, and
    Section 4.2 referenced a dropped Stamina meter.
  - *Code Reality:* Benches are multi-directional (`80x40` for N/S, `40x80` for E/W), Miniboss/Night Boss are `64x64`,
    and `The Final Author` (`!`) is `80x80`.
- [X] **Title Option Labels & Debug-Gated Input Indicator (`docs/navigation_and_ui.md` §3.1 & §8.4):**
  - *Drift:* Referenced `[New Game]` (actual label `"New Draft"`) and stated `[ Input: ... ]` was permanently shown
    (actually gated behind `debug_text_enabled`).
- [X] **Pylint Command Line Length (`docs/testing.md` §5):**
  - *Drift:* Example command omitted `--max-line-length=120`.
  - *Remediation:* Updated to `pylint --max-line-length=120 engine/ rendering/ main.py`.
- [X] **Structural Markdown Hygiene (`docs/architecture.md` §13, `docs/navigation_and_ui.md` §8, `docs/CHANGELOG.md`):**
  - Removed misplaced duplicate `### 2. Minimap Rendering Order` inside `architecture.md` Section 13, fixed duplicate
    `### 2.` heading numbering in `navigation_and_ui.md` Section 8, and removed 11 stray blank lines in `CHANGELOG.md`.

---

## 5. Category D: Broken Links & Stale References

- **Relative Markdown Links:** 100% valid across `AGENTS.md`, `README.md`, and `docs/**/*.md` (**0** dead links).
- **Stale Proposal Cross-Links (Remediated):** Updated `"proposed Marginalia Event Engine"` notices in
  `docs/modular_system.md` and `docs/world_and_lore.md` to reflect its completed `[DONE]` status.
- **Skill File Module References (`[RESOLVED]`):** Updated `.gemini/skills/doc-audit/SKILL.md` to replace stale module
  paths (`engine/boss.py` → `engine/enemy.py`, `engine/weapon.py` → `engine/loot.py`/`engine/world.py`/`engine/combat.py`,
  `engine/minimap.py` → `rendering/renderer.py`, `persistence.py` → `engine/stats.py`/`engine/autosave.py`, and
  `sanctuary_*.txt` → `maps/sanctuary.json`), and aligned `.gemini/skills/prompt-review/SKILL.md` with the live 5-Act
  engine and existing classes.

---

## 6. Action Items & Remediation Log

### Completed in this Audit Pass:
1. Updated `docs/architecture.md` (CLI flags, 5-Act climate & saturation matrix, Respite locks, Prowess `+3`,
   proximity boss summon & biome bosses, 60 FPS remote player interpolation, Section 17 VFX/Binder/Rumble, removed
   misplaced Section 13 duplicate).
2. Updated `docs/persistence.md` (removed duplicate `"last_run_result"` key; added `"rumble_enabled"` and
   `"keybindings"`).
3. Updated `docs/navigation_and_ui.md` (remappable Controls table, Title/Pause/HUD/Boss HUD updates, Tactile Menu
   Transitions, 5-of-7 Chronicle draft, fixed Section 8 heading numbering).
4. Updated `docs/modular_system.md` (7-biome pools, 56 segments, 5-Act generation pipeline, active Marginalia link).
5. Updated `docs/visual_style_and_assets.md` (multi-directional benches, Binder `'&'`, Fire Chalice `'V'`, boss sizes,
   8-direction player rig, 220 graphics + 14 music + 41 SFX manifest alignment).
6. Updated `docs/world_and_lore.md` (5-Act cycle alignment and active Marginalia cross-link while preserving all lore).
7. Updated `docs/testing.md` (`--max-line-length=120` pylint command and hermetic test suite notes).
8. Updated `docs/CHANGELOG.md` (removed stray blank lines and archived November 14–26, 2026 completed milestones).
9. Refreshed this canonical audit report (`docs/AUDIT_GAPS.md`).

### Recommended Next Steps for Future Sprints:
- Evaluate remaining Tier 2 backlog items: **Environment Audio** (`docs/backlog.md` Section 2) and **Capability
  Thresholds** (`docs/backlog.md` Section 9).
- Consider authoring bespoke Act 3–5 segment pool variants in `BIOME_ACT_SEGMENT_POOLS` (`docs/backlog.md` Section 12.3).
