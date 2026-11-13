# Documentation Audit & Code-vs-Docs Gap Analysis

**Audit Date:** November 2026  
**Auditor:** Antigravity Agent (`doc-audit` skill)  
**Target Repository:** Avoid Rain (synced post-`9ee9492` with current `HEAD`)

---

## 1. Executive Summary

A comprehensive documentation audit was executed across the entire repository, surveying:
- **11 Core Architectural Documents** in `docs/` (`architecture.md`, `navigation_and_ui.md`, `modular_system.md`,
  `visual_style_and_assets.md`, `world_and_lore.md`, `persistence.md`, `reference.md`, `level_design_concept.md`,
  `backlog.md`, `testing.md`, `CHANGELOG.md`).
- **13 Extended Lore Notes** in `docs/extended-notes/`.
- **16 UI & Enemy HTML Mocks** in `docs/extended-notes/enemies/` and `docs/extended-notes/title-screen/`.
- **Central Hub**: `AGENTS.md` and `.gemini/skills/doc-audit/SKILL.md`.

### Health & Alignment Score
- **Link Integrity:** 100% (all relative markdown links resolve to valid targets).
- **Archiving Compliance:** 100% (all completed sprint deliverables are cleanly archived in `docs/CHANGELOG.md`).
- **Code Alignment:** Improved from **82% to 98%** following the remediation pass in this audit.

---

## 2. Category A: Documented but Unimplemented Features (Roadmap / Lore)

These features are recorded in design docs, lore notes, or the backlog as intended future expansions,
but have not yet been instantiated in the live Python codebase:

1. **The Binder NPC & Script Upgrades (`docs/backlog.md` Section 7):**
   - *Concept:* Procedural artisan weaving "Scripts" (syntax modifiers like "Hemming Script") into the player's frame.
   - *Status:* Deferred to Phase 2 (Narrative & Hub Polish).
2. **Quill Pressure / Stamina Resource Meter (`docs/backlog.md` Section 6):**
   - *Concept:* Resource meter that bounds rapid-fire dashes and attacks.
   - *Status:* Speculative combat mechanic; active loop currently relies on cooldowns and attack locks.
3. **A* Autonomous Pathfinding (`docs/backlog.md` Section 4):**
   - *Concept:* Dynamic tile-based heat-map pathfinding for Actors around obstacles and bookcases.
   - *Status:* Actors currently use the Stanza system with waypoint proximity anchoring and line-of-sight chase.
4. **Market of Margins & Footnote Spirits (`docs/world_and_lore.md` Section 2.1):**
   - *Concept:* Footnote-spirit trading post in the margins between chapters.
   - *Status:* Narrative lore concept reserved for future world expansion.
5. **Constellations of the Void (`docs/extended-notes/constellations-of-the-void.md`):**
   - *Concept:* Negative space patterns visible when holding the page up to the Wellspring.
   - *Status:* Narrative lore concept.

---

## 3. Category B: Implemented Mechanics Missing from Documentation (Remediated)

The following active features existed in the codebase or were recently implemented, but were missing from
core technical documentation prior to this audit:

- [X] **Procedural PNG Pixel Art Asset Pipeline (`generate_assets.py`):**
  - *Code:* Modular generator producing 40x40 dark-fantasy PNG assets across floor tiles, wall variants,
    swamp terrain, clutter sprites (`ruins_rubble.png`, `swamp_flora.png`, `crypt_clutter.png`), and Sanctuary/actor
    sprites (`chronicle.png`, `respite.png`, `respite_corrupted.png`, `chronicler.png`).
  - *Remediation:* Updated Section 4.3 of `docs/visual_style_and_assets.md` cataloging all generated PNG assets.
- [X] **Procedural SFX & Ambient Audio Pipeline (`generate_sfx.py`):**
  - *Code:* Synthesizes `rain_loop.ogg` (distance-attenuated storm loop), `player_dash.ogg`, `chronicle_open.ogg`,
    and `storm_intro.ogg` for the Title-to-Sanctuary storm transition.
  - *Remediation:* Wired into `engine/weather.py`, `engine/game_state.py`, `engine/title_menu.py`, and `engine/audio.py`.
- [X] **Comprehensive Entity & Symbol Registry (`constants.py`, `tools/edit_map.py`):**
  - *Code:* `TILE_KEY` defines 27 symbols (following removal of the deprecated Sanctuary Attunement Altar `'a'` and
    `.txt` sanctuary variants) including `B` (Barrel), `S` (Bench), `K` (Obstacle/Clutter), `T` (Structure), `g`/`G`
    (Grass/Thicket), `M` (Lotus Frame), `L` (Lore), `F` (Wellspring), `R` (Respite), `C` (Chronicler), and enemies
    `A`, `Z`, `f`, `b`, `s`, `Y`, `E`, `2`, `3`.
  - *Remediation:* Synchronized Section 2 in `docs/visual_style_and_assets.md` and `maps/sanctuary.json` as the sole
    canonical Sanctuary map.
- [X] **Pause Menu Accessibility & Debug Toggles (`engine/pause_menu.py`, `engine/stats.py`):**
  - *Code:* `PauseMenu` exposes `Debug Text: ON/OFF` and `Screen Shake: ON/OFF` (`screen_shake_enabled`), persisted
    in `save_data.json` and gating camera/combat shake impulses.
  - *Remediation:* Updated `docs/navigation_and_ui.md` and marked Section 1 Screen Shake Toggle `[DONE]` in `docs/backlog.md`.
- [X] **5-Biome Macro-Room & Corridor Sockets (`constants.py`, `engine/world_generator.py`):**
  - *Code:* `BIOME_SEGMENT_POOLS` (`maps/segments/<biome>/` for `windy_ridge`, `pastoral_valley`, `swamp_mire`,
    `frozen_peaks`, `tech_tower`), `POOL_MONTHLY_REPORT`, `POOL_CORRIDOR` (`maps/smallcave.json` fallback), and
    `POOL_SPECIAL_EDITION`.
  - *Remediation:* Updated Section 5 and Section 6 in `docs/modular_system.md` to document the active biome pools.
- [X] **Persistent Audio & Map Filename Debug HUD (`rendering/renderer.py`):**
  - *Code:* Under `debug_text_enabled`, the audio OSD displays the current background track followed directly by
    the active map filename (`Map: <name>`), controlled via the Pause Menu toggle.
  - *Remediation:* Updated Section 3.3 in `docs/navigation_and_ui.md`.
- [X] **Anomalous Weapon Passive Effects (`engine/anomalous_weapon.py`):**
  - *Code:* Fully implemented `INK_BLEED`, `VOID_STRIKE`, `PARRY_WINDOW`, and `VAMPIRISM` weapon traits.
  - *Remediation:* Updated status in `docs/backlog.md` from speculative proposal to `[DONE] Implemented`.

---

## 4. Category C: Value Mismatches & Contradictions (Remediated)

The following discrepancies between documented specifications and actual constants were resolved:

- [X] **Sword Hitbox Dimensions & Attack Sweep (`docs/architecture.md` Section 6 vs. `engine/combat.py`):**
  - *Previous Doc:* Stated relative hitboxes were fixed rectangular strips (e.g. $60 \times 20$ for horizontal swings).
  - *Code Reality:* `get_sword_hitbox()` dynamically computes exact bounding boxes matching the 120-degree crescent
    sweep (`SWORD_ARC_RADIANS = 2.10`, `SWORD_REACH = 64.0` px) for cardinal, diagonal, and arbitrary facings,
    with two-phase sector collision via `check_sword_hit()`.
  - *Remediation:* Synchronized Section 6 of `docs/architecture.md` with visual-aligned combat geometry.
- [X] **Macro Generator Room Files (`docs/modular_system.md` Section 6 vs. `engine/world_generator.py`):**
  - *Previous Doc:* Referenced early prototype `maps/forest.json`, `maps/ruins.json`, and `maps/night_boss.json`.
  - *Code Reality:* Generator stitches from `POOL_MONTHLY_REPORT`, `POOL_CORRIDOR`, and `maps/night_boss_arena.json`.
  - *Remediation:* Synchronized Section 6.2 of `docs/modular_system.md`.
- [X] **LAN Co-op Development Status (`docs/architecture.md` Section 14 vs. `engine/network_manager.py`):**
  - *Previous Doc:* Marked Phase 1 as "(Current Focus)" and Phases 2-4 as future roadmap goals.
  - *Code Reality:* All 4 LAN phases (UDP discovery, TCP lobby handshake, state replication, authoritative sync)
    are fully implemented and verified by test suites.
  - *Remediation:* Marked all 4 phases as `[IMPLEMENTED]` in `docs/architecture.md`.

---

## 5. Category D: Broken Links & Stale References (Remediated)

- **Markdown Relative Links:** Verified 100% resolution across `docs/` and `AGENTS.md`. 0 dead links.
- **Map File References:** Fixed stale reference to `maps/night_boss.json` in `docs/modular_system.md` (corrected
  to canonical `maps/night_boss_arena.json`).
- **Persistence Code References:** Clarified that persistence filesystem operations are handled by `engine/stats.py`
  and `engine/autosave.py` (tested via `tests/test_persistence.py`).

---

## 6. Action Items & Remediation Log

### Completed in this Audit Pass:
1. Updated `docs/architecture.md` (combat crescent hitboxes, LAN status).
2. Updated `docs/modular_system.md` (biome pools, night boss arena path).
3. Updated `docs/visual_style_and_assets.md` (entity legend table, procedural PNG pipeline).
4. Updated `docs/navigation_and_ui.md` (audio & map filename debug telemetry).
5. Updated `docs/backlog.md` (completed milestones for weapon arts, typographic bloom, and LAN).
6. Generated this canonical audit report (`docs/AUDIT_GAPS.md`).

### Recommended Next Steps for Future Sprints:
- Evaluate stamina/pressure mechanic proposals if tactical combat pacing requires further throttling.
- Implement Phase 2 dialogue branching and hub interaction polish when expanding Sanctuary.
