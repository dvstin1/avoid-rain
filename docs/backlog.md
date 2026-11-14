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

## 11. Seamless LAN Co-op Lifecycle [PROPOSED]

> **STATUS:** `[PROPOSED]` (Not Yet Implemented). Builds on the implemented Phase 1–4 LAN transport layer (`peer_id`, 4-byte length-prefixed TCP framing, non-blocking `_outbound_queue`, and main-thread `drain_network_events()` in `docs/architecture.md` Section 14.1) while keeping Section 5's completed stabilization milestones intact.

### 11.1. Title Screen Online/Offline Mode & Name Editing (`[PROPOSED]`)
- **Replace Manual Lobby Flow:** Remove the manual "Join Game" lobby flow (`TitleMenuState.LOBBY` / `ui/lobby_menu.py`) and replace it with an **Online / Offline** mode toggle (`online_mode: bool`, `(proposed)`) on the Title Screen, defaulting to **Online**.
- **Title Screen Name Editing:** Relocate `[N] Change Name` / `player_name` editing onto the Title Screen when `TitleMenuState.LOBBY` is removed so players can still customize their display `identity` before entering Sanctuary.
- **Offline Mode:** Runs purely locally with zero UDP/TCP sockets active (`network_mode == "OFFLINE"`).
- **Online Mode (Single Active LAN Session):** Assumes at most one shared co-op session per local network. Upon entering Sanctuary in Online mode, the client probes `LAN_PORT` (`55555`) for existing host broadcasts (~1.5–2.0s window):
  - **Active Host Discovered:** Automatically connect as a **Client** via framed TCP `HANDSHAKE` and spawn directly into **Sanctuary** alongside connected peers.
  - **No Host Discovered:** Automatically promote self to **Host** (`start_hosting()`) and begin broadcasting on `LAN_PORT` (`55555`) immediately from Sanctuary.
  - **Continue / Saved Mid-Run Resume:** Resuming a saved mid-run via **Continue** (`GameState.hydrate_from_disk()`) in Online mode resumes directly as **Host** (`host_in_run = True`, `(proposed)`), treating any subsequently connecting peers as Waiting Scholars in Sanctuary.
- **Simultaneous Boot Tie-Breaker (`[PROPOSED]`):** An active Host keeps a lightweight `LAN_PORT` (`55555`) listener (or periodic probe) active so if two Hosts detect each other's UDP broadcasts on the same LAN, the instance with the lexicographically higher `peer_id` yields, stops hosting, and connects as a Client to the lower-`peer_id` Host.

### 11.2. Sanctuary Staging, Group Run Launch & Waiting Scholars (`[PROPOSED]`)
- **Sanctuary-Only Spawning & Session Persistence:**
  - Newly connecting Clients always spawn into **Sanctuary** (`in_sanctuary: bool`, `(proposed)`), never mid-run into an active macro-world instance.
  - Returning to Sanctuary in Online mode (`GameState.on_enter_sanctuary()`) preserves the active Host/Client LAN session rather than calling `stop_network()`.
- **Group Run Launch:**
  - When the Host triggers the `WarpPortal` in Sanctuary to start a run, all players currently present in Sanctuary warp into the run together (receiving the Host's framed `MAP_RESPONSE` and initial Act 1 world state).
- **Mid-Run Joiners ("Waiting Scholars"):**
  - Host `HANDSHAKE` responses and 20Hz UDP snapshots replicate `host_in_run: bool` `(proposed)` and `waiting_scholars: int` `(proposed)`.
  - When `host_in_run` is `True`, newly joining Clients remain in Sanctuary (suppressing `fetch_host_map()` until the Host's party returns and starts a new `WarpPortal` run) and display a HUD banner: *"Waiting for current run to finish..."*.
  - Active players out in the run see a live HUD indicator showing the count of waiting players (e.g., *"1 Scholar waiting in Sanctuary"* / *"N Scholars waiting in Sanctuary"*).
  - **Pause Menu Regroup Option (`"Return to Sanctuary"`, `(proposed)`):** Whenever `waiting_scholars > 0` `(proposed)`, `PauseMenu` surfaces a **"Return to Sanctuary"** `(proposed)` option so the active party can cleanly abandon the current run—running standard `on_enter_sanctuary()` purification (resetting Torn Pages, run gear, and modifiers) while keeping the Online LAN session alive—and regroup in Sanctuary with the waiting players.

### 11.3. Disruptive Host Promotion on Disconnect (`[PROPOSED]`)
- If the Host disconnects or times out (`HOST_DISCONNECT`), surviving Clients do not get kicked to the title screen:
  1. **Deterministic Roster Retention:** Clients retain the latest `session_players` `peer_id` roster across the disconnect frame so all survivors agree deterministically on promotion order.
  2. **Sanctuary Regroup:** All surviving Clients warp back to **Sanctuary** (cleaning up active run state via `on_enter_sanctuary()`).
  3. **Lexicographic `peer_id` Promotion:** The surviving Client with the lexicographically lowest `peer_id` automatically promotes itself to **Host** (`start_hosting()`), while any other surviving Clients reconnect to the newly promoted Host in Sanctuary within one discovery cycle.

## 12. 5-Act Unbound Chronicle Progression & Expanded Biomes [PROPOSED]

> **STATUS:** `[PROPOSED]` (Not Yet Implemented). Expands the current 2-Act (`current_act in (1, 2)`) run loop into a 5-Act chapter draft across a 7-biome roster with Act-keyed segment pools. All new mechanics, biomes, and progression fields below are `[PROPOSED]`.

### 12.1. 5-Act Run Structure & "Unbound Chronicle" Biome Draft (`[PROPOSED]`)
- **5-Act Loop (`current_act: 1..5`, `[PROPOSED]`):** Expand the core run loop from 2 Acts to **5 Acts (Nights 1–5)** (`[PROPOSED]`), framed in lore as binding and arranging the **Unbound Chronicle** (five surviving chapter folios) in Sanctuary before stepping into the rain.
- **Pre-Run Biome Draft & Ordering (`run_biomes: list[str]` of length 5, `[PROPOSED]`):**
  - Before launching a run via `WarpPortal` (extending `GameState.open_chronicle_biome_dialog()` or a proposed Sanctuary lectern/folio draft UI), the player—or the **Host** in Seamless LAN Co-op—selects and orders **5 distinct biomes** from the expanded 7-biome pool to assign one biome to each Act (**Act 1 through Act 5**).
- **Act Saturation / Escalation Matrix (Acts 1–5, `[PROPOSED]`):**
  - Each Act rank (`1..5`) progressively increases rain/ink saturation, scaling:
    - **Enemy Tiers:** Act 1–2 base castes escalating into Act 3–5 empowered and ink-saturated variants.
    - **Landmark & Hazard Intensity:** Biome-specific environmental hazards, storm contraction pressure, and interactive landmark behaviors.
    - **Torn Page & Cradle Rewards:** Higher Acts yield increased Torn Page rewards within the single active run pool (which still resets to `0` upon returning to Sanctuary per `docs/world_and_lore.md`) and higher-tier rare weapon rolls that strictly obey the two-slot **Full-Cradle Rule** (dropping an **Anomalous Weapon** only when both cradle slots are already occupied).
  - Because every biome behaves and rewards differently at Act 1 vs. Act 5, drafting and ordering the 5 chapter folios becomes a primary strategic and replayability decision.

### 12.2. Expanded 7-Biome Pool (`[PROPOSED]`)
Expand the existing 5-biome roster (`windy_ridge`, `pastoral_valley`, `swamp_mire`, `frozen_peaks`, `tech_tower`) to **7 biomes** (`[PROPOSED]`) so every 5-Act run drafts 5 of 7 biomes in a player-chosen sequence:
1. **Sunken Glass & Salt Flats (*The Vitreous Basin*, `vitreous_basin`, `[PROPOSED]`):**
   - Crystalline salt crusts, reflective/refractive glass flats, and high-exposure rain plains where higher Acts (`3..5`) intensify storm glare, fracture brittle glass terrain into hazards, and guard high-value rare drops (respecting the Full-Cradle Rule).
2. **Overgrown Terracotta & Moss Ruins (*The Sunlit Aqueducts*, `sunlit_aqueducts`, `[PROPOSED]`):**
   - Sun-bleached stone channels, moss-choked viaducts, and terraced ruin chokepoints where higher Acts (`3..5`) flood aqueduct channels, awaken overgrown/empowered defenders, and unseal elevated shrine caches.
- **Per-Biome Implementation & LAN Sync Scope (`[PROPOSED]`):**
  - Deterministic sprite/tile generation (`generate_assets.py` via `_rng("<key>")` and `write_surface_if_changed()`), runtime segment pool generation (`generate_maps.py --generate-pools` -> `maps/segments/<biome>/`, registered in `BIOME_SEGMENT_POOLS`), `tools/edit_map.py` (`MASTER_TOOL_REGISTRY`) palette parity, and biome-specific enemy pairings will be scoped per biome as each is built out.
  - Host-driven 5-Act `run_biomes` (`len == 5`), `current_act` (`1..5`), and framed TCP `MAP_RESPONSE` (or per-Act transition sync) replication in `engine/network_manager.py` will generalize the existing 2-Act LAN map synchronization.

### 12.3. Act-Keyed Map Segments & Incremental Backfill Architecture (`[PROPOSED]`)
- **Act-Keyed Segment Pools (`(biome_id, act_number)`, `[PROPOSED]`):**
  - Replace identical Act 1 / Act 2 map reuse with **Act-keyed map segments and layouts** (`BIOME_ACT_SEGMENT_POOLS[(biome_id, act_number)]`, `[PROPOSED]`) so higher Acts feature distinct room geometry, chokepoints, environmental hazards, and secret vaults—not merely enemy stat multipliers.
- **Lower-Act Fallback Rule (`[PROPOSED]`):**
  - The level loader/generator (`engine/modular_builder.py` / `generate_maps.py`) will resolve `(biome_id, act_number)` by falling back to the **highest authored lower-Act segment pool** (`act_number - 1` down to `1`, and then `BIOME_SEGMENT_POOLS[biome_id]`) whenever bespoke Act `N` segments have not yet been authored for that biome.
  - This guarantees every 5-Act permutation is playable immediately while allowing individual `(biome_id, act_number)` slices and signature mechanics to be authored and backfilled incrementally one at a time.
