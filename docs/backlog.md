# Development Roadmap & Feature Backlog

## Roadmap Priorities
- **Phase 1 (Current): Core Gameplay Loop.** Focus exclusively on hostile game world mechanics: vector physics, modular assembly, enemy AI, and combat collision.
- **Phase 2 (Future): Hub & Narrative Polish.** Visual expansion of the Sanctuary, advanced NPC dialogue branching, and environment tiling sheets.

---

## Feature Backlog & Future Proposals

> **DISCLAIMER:** This document contains unimplemented features and speculative ideas. Nothing listed here is currently active or guaranteed for immediate production. This serves as a "parking lot" for high-concept mechanical and aesthetic refinements.

---

## 1. Input & Accessibility
- **Gamepad Support (Polish):** Native controller mapping for Xbox/PlayStation layouts is implemented, but could use further refinement and rumble support.
- **Remappable Keys:** In-game menu for custom keyboard/controller bindings.
- **Screen Shake Toggle:** [DONE] Implemented `Screen Shake: ON/OFF` in the Pause Menu (`screen_shake_enabled`), persisted in `save_data.json` and gating combat/parry camera shake impulses.

## 2. Audio & Atmosphere
- **Noir Soundtrack:** Procedural ambient tracks that shift intensity based on proximity to enemies or the Rain.
- **Environment Audio:** Directional audio for candelabras, wellsprings, and the distant rumble of the author's madness.

## 3. Narrative & Visuals
- **Layered Visual System (Ghost Indicators):** [DONE] Implement a decoupled animation system that uses abstract indicators (color tints, squashing, borders) to represent states (WOUNDED, STAGGERED, BIND) without finalized assets.
- **Logical Effect Buffer:** Create an engine-side queue for visual events (INK_DEATH, PARRY_SPARK) that the renderer consumes, ensuring visuals remain decoupled from logic.
- **Chapter Titles:** [DONE] Large typographic overlays (Typographic Bloom) when entering new modular zones and climatic weather transitions.

## 4. Technical & Navigation (Future Phases)
- **A* Pathfinding:** Implement a dedicated pathfinding engine to allow Actors (Enemies and NPCs) to navigate around walls and obstacles autonomously.
    - **Dynamic Calculation:** Instead of simple linear vectors, actors will compute a tile-based route to their next PatrolPoint.
    - **Optimization:** Utilize a heat-map or hierarchical A* to manage the large 440x440 grid efficiently in Python.
    - **Obstacle Awareness:** Pathfinding must account for both static wall tiles and solid GameObjects (Bookcases, Candelabras).
    - **Interim Complementary Hook (Breadcrumb Pursuit):** For `"global_pursuit"` Marginalia events (see Section 10), `EnemyBase.persistent_pursuit = True` pairs with a lightweight **player movement breadcrumb trail** and brief wall-phase fallback if stalled—providing an immediate map-wide hunter navigation path that later upgrades cleanly onto A* without architectural conflict.

## 5. Network & Multiplayer Stabilization (Completed)
- **LAN Multiplayer:** [DONE] Implemented UDP broadcast (`SO_BROADCAST`), lobby discovery, and TCP socket handshake.
- **State Serialization:** [DONE] Implemented clean 20Hz state packet serialization and client coordinate interpolation.
- **Client Healing Regressions:** [DONE] Implemented input latching and authoritative TCP HEAL_EVENTs to prevent charge-drain and HP desync.
- **Respite Desync:** [DONE] Implemented RESPITE_ACTION events for authoritative resting and edification.
- **Boss Visibility:** [DONE] Host now broadcasts enemy names and dynamic interactables (Appendix Warp), and Clients correctly spawn them mid-session.
- **Combat Balance:** [DONE] Implemented hit-latching to ensure each swing only deals damage once, preventing 'instant kill' glitches.

## 6. Combat Refinement
- **Anomalous Weapon Effects:** [DONE] Implemented passive effects for Anomalous weapons (`INK_BLEED`, `VOID_STRIKE`, `PARRY_WINDOW`, `VAMPIRISM`) in `engine/anomalous_weapon.py`.
- **Quill Pressure (Stamina):** [Speculative] A resource meter that limits rapid-fire attacks and dashes, encouraging tactical positioning and deliberate timing.
- **Advanced Stagger Mechanics:** [Speculative] Variable stagger thresholds based on weapon weight or impact force.

## 7. Binder Scripts (Upgrade System)
- **Concept:** The Binder NPC acts as a procedural artisan, weaving "Scripts" (operational metaphors like "Hemming Script" for HP buffs) into the player's frame using Torn Pages.
- **Mechanics:** Scripts act as tiny compilers in the margins altering stat allocations. They can be combined but are subject to "syntax conflicts" where scripts touching the same stat will fight, with the stronger one winning.
- **Lore Integration:** The Binder seeks to "perfect the stitch." Completing a specific sequence of failed scripts may offer a path to a different ending, halting the ink-bleed cycle.

## 8. Atmospheric Polish & Micro-Animations
Small, code-driven visual beats to enhance the "Scriptorium Noir" feel.
- **Enhanced Death Sequence (Text Bleaching):** Replace the static gray overlay with a dynamic saturation drop and camera pull-back as the player "fades into a rejected draft."
- **Tactile Menu Transitions:** Implement unrolling or sliding animations for the Chronicle (Title/Pause) menus to make them feel like physical parchment.
- **Respite Activation Pulse:** Add a localized typographic bloom effect (drifting letters/glyphs) when resting at a Respite anchor.
- **Typographic Run-Start:** Animate the world map "inking" itself using letters cascading into the room shapes during the Chronicle transition.

## 9. Expanded Progression & Global Leveling
- **Capability Thresholds:** Currently, the player's global 'Understanding' level strictly dictates passive damage reduction. In the future, reaching specific total level thresholds (e.g., Level 5, Level 10) should automatically unlock new capabilities or narrative dialogue paths to provide distinct progression milestones.

## 10. Marginalia Event Engine

> **STATUS:** Proposed Architecture (Not Yet Implemented). Designed for headless `engine/` execution, clean `rendering/renderer.py` banner presentation, and deterministic LAN co-op sync via `engine/network_manager.py`.

### 10.1. Core Architectural Contract
- **Canonical Act Terminology & Roll Frequency:** Uses canonical `GameState.current_act` (`1` = Act 1 / Night 1, `2` = Act 2 / Night 2). Rolls a **20% trigger chance once per Act** (maximum **1 event in Act 1** and **1 event in Act 2**—never rolled per `120x120` macro-room segment).
- **Trigger Window (`WeatherManager.current_step_idx`):** Events may only trigger before the second storm contraction completes:
  - `weather_manager.current_step_idx < 2`
  - `weather_manager.bleed_state not in ("BOSS_PHASE", "DILUTION")`
- **Weather Lock Contract (Proposed `WeatherManager.paused`):**
  - Add `paused: bool = False` to `WeatherManager` (`engine/weather.py`).
  - While `paused = True`, freeze `grace_timer` / step `timer` progression **and** suppress rain exposure damage (`player.is_exposed = False`) so players outside the shrinking boundary are not killed by storm bleed mid-event.
  - Restore `paused = False` immediately upon event completion, expiration, or failure.
- **Unified Event Interface & LAN Co-op Sync (`engine/network_manager.py`):**
  - Every event implements a shared headless state contract:
    - `event_id`: Unique string identifier (e.g., `"unbound_folio"`).
    - `act_variant`: `1` or `2` (mirrors `current_act`, driving Act 2 escalation and empowered enemy variants).
    - `trigger_mode`: `"auto_safe_zone"` | `"prop_strike"` | `"pitfall_warp"` | `"hunt_timer"`.
    - `spatial_mode`: `"local"` | `"map_anchor"` | `"global_pursuit"`.
    - `time_remaining`: Float seconds remaining (or `None` for untimed events).
    - `progress`: Normalized float `0.0..1.0` or `(current, target)` counter tuple.
    - `status`: `"PENDING"` | `"ACTIVE"` | `"COMPLETED"` | `"FAILED"`.
  - `rendering/renderer.py` consumes this single schema to render one unified top-center Marginalia banner (title, act badge, progress bar/counter, and countdown) without per-event UI special cases.
  - `engine/network_manager.py` serializes this compact event state block from Host to Clients so all players see synchronized timers, objectives, and outcomes.
- **Respite Rest Persistence:**
  - Resting at a Respite (`R`) resets standard enemies and breakable props per `docs/world_and_lore.md` (*The Fresh View Cycle*), **but triggered/completed `map_anchor` events remain consumed for the rest of that Act** so players cannot farm event rewards via Rest loops.
- **Economy & Cradle Compliance (`docs/world_and_lore.md`):**
  - **Single Run Torn Pages Pool:** All Torn Page rewards and setbacks mutate the active run's Torn Pages pool (clamped at `>= 0`).
  - **Strict Economy of Review:** Events **never** grant direct Edification level-ups outside of Respite Rest.
  - **The Full-Cradle Rule:** Weapon-roll rewards check both player weapon slots; if both slots are full, they drop an **Anomalous Weapon**, otherwise they fall back to a standard Weapon or Torn Pages drop.

### 10.2. Spatial & Trigger Modes
1. **`"local"` (Dynamic Safe-Zone Overlay):**
   - Spawns a bounded ritual ring, escort path, or encounter zone in a valid safe-zone clearing near the player.
2. **`"map_anchor"` (Prop & Sub-Arena Warp Triggers):**
   - **Prop Ambush:** Binds to an existing cluster of Breakable Barrels (`'B'`), converting the cluster into mimic enemies when the first barrel is struck.
   - **Sub-Arena Pitfall & Exit Ladder (Proposed `ReturnAnchor` Warp Stack in `engine/world.py`):** Stepping onto a disguised map trigger (e.g., a suspicious leaf pile) pushes `ReturnAnchor(map_path, x, y)` onto `GameState`, warps into a compact underground pocket arena while keeping overworld weather `paused = True`, and spawns an **Exit Ladder** warp back to the saved `(x, y)` anchor upon victory.
   - **LAN Co-op Party Warp Rule:** Because `engine/network_manager.py` replicates a single shared `state.world`, triggering a sub-arena pitfall warps the **entire party** into the pocket arena together and returns the **entire party** together via the Exit Ladder.
3. **`"global_pursuit"` (Relentless Map-Wide Hunter):**
   - Uses a proposed `persistent_pursuit: bool = True` flag on `EnemyBase` (bypassing standard line-of-sight checks and Stanza waypoint leashing).
   - Tracks a lightweight **player movement breadcrumb trail** with a brief wall-phase fallback if the hunter stalls against geometry.
   - *Cross-reference:* See Section 4 (**A\* Pathfinding**) for how breadcrumb pursuit serves as an interim/complementary hook until hierarchical A* is implemented.

### 10.3. Full Event Pool Catalog (Act 1 & Act 2 Variants)

| Event | Spatial Mode | Mechanic Summary | Act 1 (`current_act == 1`) | Act 2 (`current_act == 2`) | Rewards | Failure Setback |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **The Unbound Folio** | `"local"` | Timed wave ambush inside bookmark wards | 2 enemy waves | 3 waves with Empowered Punctuation Wolves & Smears | **+3 / +5 Torn Pages + Flask refill** (+ temporary Attack Speed buff in Act 2) | Non-lethal ink knockback burst |
| **The Running Errata** | `"local"` | Mobile escort: protect a fleeing Footnote Wisp to a landmark | Standard interceptors | Faster/empowered interceptors | **Weapon drop (Anomalous if both cradle slots full, per Full-Cradle Rule)** + Torn Pages | Lingering ink hazards + drains 1 Flask charge |
| **The Censored Passage** | `"local"` | King-of-the-Hill cleansing inside a suppression obelisk zone | Static cleansing zone | Shrinking/pulsing cleansing zone | **+3 / +5 Torn Pages + 50% / 75% HP heal** (no direct Edification) | Temporary ink-mist vignette |
| **The Palimpsest Duel** | `"local"` | Elite 1v1 inside a bounded dueling ring | Overwritten Elite | Empowered Champion | **+15 / +25 run `max_hp` + Torn Pages** (+ Full-Cradle weapon roll in Act 2) | Temporary movement/reach debuff |
| **The Margin Toll** | `"local"` | Shatter scattered Ink Seals in the safe zone; each spawns ambushers | 3 Ink Seals | 4 Ink Seals | **Torn Pages + temporary storm-exposure immunity** when weather resumes | Remaining seals detonate; strips **1–2 Torn Pages** from current run pool (clamped at `0`) |
| **The Barrel Mimic Cluster** | `"map_anchor"` | Striking the first `'B'` barrel in an anchored cluster awakens mimics | 8 mimic enemies | 12 mimic enemies | **+4 / +6 Torn Pages, Flask refill, and Weapon/Consumable drop** | — (combat encounter until cleared) |
| **The Sunken Margin / Ink Well Cellar** | `"map_anchor"` | Disguised leaf-pile pitfall warps party via `ReturnAnchor` to pocket arena; victory spawns **Exit Ladder** | Act 1 cellar ambush | Act 2 cellar ambush (empowered variants) | **Pocket arena Torn Pages + Exit Ladder** return to overworld `(x, y)` | — (party remains in cellar until cleared) |
| **The Relentless Censor** | `"global_pursuit"` | 40s hunt by a `persistent_pursuit` hunter following player breadcrumbs | Act 1 Censor hunter | Act 2 Empowered Censor hunter | **Slay:** +4 / +6 Torn Pages, full Flask refill, Full-Cradle weapon roll. **Survive 40s:** partial Torn Pages + heal | Taking a redaction/lethal hit triggers a recoverable setback (Flask drain / temporary debuff) and banishes the hunter |
| **The Unblotted Margin** | `"local"` | **Rare Zero-Risk Boon (~12–15% weight of triggered events).** No enemies, no timer, no failure state | *"A Clear Footnote"*: Full HP, full Flasks, **+2 Torn Pages** | *"The Author's Grace"*: Full HP, full Flasks, **+3 Torn Pages**, + 25s **"Pristine Ink"** damage-block shield | Instant boon | None |
