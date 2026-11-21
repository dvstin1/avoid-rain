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
- **A* Pathfinding:** [DONE] Implemented a dedicated headless pathfinding engine (`engine/pathfinding.py`) allowing Actors (Enemies and NPCs) to navigate around walls and solid props autonomously.
    - **Dynamic Calculation:** Actors compute corner-safe 8-way smoothed tile routes (`find_path`, `has_line_of_sight`) for patrol navigation, chase detours, and returning to their nearest patrol marker after breaking aggro.
    - **Optimization:** Uses bounded search radius (`PATHFINDING_MAX_RADIUS_TILES`), node expansion budget (`PATHFINDING_MAX_NODES`), per-actor repath throttling, and spatial-signature cached solid-prop footprints (`get_solid_obstacle_tiles`) for 60fps performance on 440x440 grids.
    - **Obstacle Awareness:** Accounts for both static `TILE_WALL` tiles and active solid `GameObject` footprints (Bookcases, Candelabras, Rocks/Pillars, Barrels).
    - **Live Map Patrols & Breadcrumb Pursuit:** `generate_maps.py` places multi-point Stanza patrol routes (`_place_patrol_routes`) across all 7 biome segment pools with socket-scoped `route_id` namespacing in `LevelLoader.load_json_map()`. `persistent_pursuit` Marginalia hunters use A* within local search range and seamlessly fall back to player breadcrumbs + wall-phase at long range.

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

## 7. Binder Scripts (Upgrade System) [DONE]
- **Concept (`[DONE]`):** **The Binder** NPC (`'&'` in `maps/sanctuary.json`, mirrored across `constants.py`, `engine/world.py`, `tools/edit_map.py`, `generate_maps.py`, and `assets/graphics/binder.png`) acts as a procedural artisan in Sanctuary, weaving **Scripts** (e.g., *Hemming Script*, *Vellum Buckram Script*, *Serifed Edge Script*, *Rubricated Nib Script*, *Marginal Gloss Script*, *Palimpsest Ward Script*) into the Reader's frame using persistent **Margin Scraps** (`margin_scraps`, earned from Night Bosses, Marginalia events, and *The Final Author* while preserving the Closed Volume Paradox where `pages_collected` resets to `0` on Sanctuary entry).
- **Mechanics (`[DONE]`):** Implemented in `engine/binder_scripts.py` (`compile_binder_scripts`, `weave_script`, `toggle_equip_script`) and wired into `Player` (`max_hp`, `attack`, `speed`, `damage_mitigation`, `bleed`) and LAN Co-op (`get_full_player_state` / `cached_client_states`). Scripts act as tiny compilers in the margins altering stat allocations; when multiple equipped scripts touch the same stat, a **syntax conflict** occurs where the stronger magnitude wins (`ACTIVE`) and the weaker script fails (`CONFLICTED`, contributing `0`).
- **Lore Integration & Alternate Ending (`[DONE]`):** Completing the Binder's required 3-step sequence of failed/conflicted scripts (`max_hp -> attack -> damage_mitigation`) sets `story_flags["perfect_stitch_completed"] = True`; defeating *The Final Author* with the Perfect Stitch woven triggers the alternate ending (`last_run_result = "STITCH_VICTORY"`, typographic bloom `"THE INK-BLEED HALTED"`, `story_flags["ink_bleed_halted"] = True`) and unlocks new Chronicler & Binder post-run dialogue.

## 8. Atmospheric Polish & Micro-Animations
Small, code-driven visual beats to enhance the "Scriptorium Noir" feel.
- **Enhanced Death Sequence (Text Bleaching):** Replace the static gray overlay with a dynamic saturation drop and camera pull-back as the player "fades into a rejected draft."
- **Tactile Menu Transitions:** Implement unrolling or sliding animations for the Chronicle (Title/Pause) menus to make them feel like physical parchment.
- **Respite Activation Pulse:** Add a localized typographic bloom effect (drifting letters/glyphs) when resting at a Respite anchor.
- **Typographic Run-Start:** Animate the world map "inking" itself using letters cascading into the room shapes during the Chronicle transition.

## 9. Expanded Progression & Global Leveling
- **Capability Thresholds:** Currently, the player's global 'Understanding' level strictly dictates passive damage reduction. In the future, reaching specific total level thresholds (e.g., Level 5, Level 10) should automatically unlock new capabilities or narrative dialogue paths to provide distinct progression milestones.

## 10. Marginalia Event Engine [DONE]

> **STATUS:** `[DONE]`. Implemented in `engine/marginalia_events.py`, `engine/weather.py`, `engine/world.py`, `engine/enemy.py`, `engine/game_state.py`, and `rendering/renderer.py`, with headless `engine/` execution, unified top-center `BitmapFont` banner presentation, and 20Hz UDP / framed TCP LAN co-op synchronization.

### 10.1. Core Architectural Contract (`[DONE]`)
- **Canonical Act Terminology & Roll Frequency:** Uses canonical `GameState.current_act` (`1` = Act 1 / Night 1, `2` = Act 2 / Night 2). Rolls a **20% trigger chance once per Act** (maximum **1 event in Act 1** and **1 event in Act 2**—never rolled per `120x120` macro-room segment).
- **Trigger Window (`WeatherManager.current_step_idx`):** Events may only trigger before the second storm contraction completes:
  - `weather_manager.current_step_idx < 2`
  - `weather_manager.bleed_state not in ("BOSS_PHASE", "DILUTION")`
- **Weather Lock Contract (`WeatherManager.paused`):**
  - Added `paused: bool = False` to `WeatherManager` (`engine/weather.py`).
  - While `paused = True`, freezes `grace_timer` / step `timer` progression **and** suppresses rain exposure damage (`player.is_exposed = False`) so players outside the shrinking boundary are not killed by storm bleed mid-event.
  - Restores `paused = False` immediately upon event completion, expiration, failure, or Sanctuary return.
- **Unified Event Interface & LAN Co-op Sync (`engine/marginalia_events.py` & `engine/game_state.py`):**
  - Every event implements a shared headless state contract:
    - `event_id`: Unique string identifier (e.g., `"unbound_folio"`).
    - `act_variant`: `1` or `2` (mirrors `current_act`, driving Act 2 escalation and empowered enemy variants).
    - `trigger_mode`: `"auto_safe_zone"` | `"prop_strike"` | `"pitfall_warp"` | `"hunt_timer"`.
    - `spatial_mode`: `"local"` | `"map_anchor"` | `"global_pursuit"`.
    - `time_remaining`: Float seconds remaining (or `None` for untimed events).
    - `progress`: Normalized float `0.0..1.0` or `(current, target)` counter tuple.
    - `status`: `"PENDING"` | `"ACTIVE"` | `"COMPLETED"` | `"FAILED"`.
  - `rendering/renderer.py` consumes this single schema to render one unified top-center Marginalia banner (title, act badge, progress bar/counter, and countdown) without per-event UI special cases.
  - `GameState` & `NetworkManager` replicate this compact event state block from Host to active runner Clients (excluding Waiting Scholars in Sanctuary) so all active runners see synchronized timers, objectives, and outcomes.
- **Respite Rest Persistence:**
  - Resting at a Respite (`R`) resets standard enemies and breakable props per `docs/world_and_lore.md` (*The Fresh View Cycle*), **but triggered/completed `map_anchor` events remain consumed for the rest of that Act** (`MarginaliaEventEngine.on_respite_rest()`) so players cannot farm event rewards via Rest loops.
- **Economy & Cradle Compliance (`docs/world_and_lore.md`):**
  - **Single Run Torn Pages Pool:** All Torn Page rewards and setbacks mutate the active run's Torn Pages pool (clamped at `>= 0` and resetting to `0` on Sanctuary return).
  - **Strict Economy of Review:** Events **never** grant direct Edification level-ups outside of Respite Rest.
  - **The Full-Cradle Rule:** Weapon-roll rewards check both player weapon slots; if both slots are full, they drop an **Anomalous Weapon**, otherwise they fall back to a standard Weapon (`"Refined Quill"`) or Torn Pages drop.

### 10.2. Spatial & Trigger Modes (`[DONE]`)
1. **`"local"` (Dynamic Safe-Zone Overlay):**
   - Spawns a bounded ritual ring, escort path, or encounter zone in a valid safe-zone clearing near the player.
2. **`"map_anchor"` (Prop & Sub-Arena Warp Triggers):**
   - **Prop Ambush:** Binds to an existing cluster of Breakable Barrels (`'B'`), converting the cluster into mimic enemies when the first barrel is struck (locally or via Client `DAMAGE_EVENT`).
   - **Sub-Arena Pitfall & Exit Ladder (`ReturnAnchor` Warp Stack in `engine/world.py` & `GameState`):** Stepping onto a disguised map trigger (`PitfallTrigger`, `"Suspicious Leaf Pile"`) pushes `ReturnAnchor(map_path, x, y)` onto `GameState.return_anchor_stack`, warps into a compact underground pocket arena (`"ink_well_cellar"`) while keeping overworld weather `paused = True`, and spawns an **Exit Ladder** (`ExitLadder`) warp back to the saved `(x, y)` anchor upon victory.
   - **LAN Co-op Party Warp Rule:** Triggering a sub-arena pitfall warps the **entire active runner party** into the pocket arena together and returns the **entire party** together via the Exit Ladder.
3. **`"global_pursuit"` (Relentless Map-Wide Hunter):**
   - Uses `persistent_pursuit: bool = True` on `Enemy` (`engine/enemy.py`, bypassing standard line-of-sight checks and Stanza waypoint leashing).
   - Tracks a lightweight **player movement breadcrumb trail** (`GameState.player_breadcrumbs`) with a brief wall-phase fallback if the hunter stalls against geometry.
   - *Cross-reference:* See Section 4 (**A\* Pathfinding**) for how breadcrumb pursuit serves as an interim/complementary hook until hierarchical A* is implemented.

### 10.3. Full Event Pool Catalog (Act 1 & Act 2 Variants) (`[DONE]`)

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

## 11. Seamless LAN Co-op Lifecycle [DONE]

> **STATUS:** `[DONE]`. Implements Seamless LAN Co-op on top of the Phase 1–4 LAN transport layer (`peer_id`, 4-byte length-prefixed TCP framing, non-blocking `_outbound_queue`, and main-thread `drain_network_events()` in `docs/architecture.md` Section 14) while keeping Section 5's completed stabilization milestones intact.

### 11.1. Title Screen Online/Offline Mode & Name Editing (`[DONE]`)
- **Replace Manual Lobby Flow:** Replaced the manual "Join Game" lobby flow (`TitleMenuState.LOBBY` / `ui/lobby_menu.py`) with an **Online / Offline** mode toggle (`online_mode: bool`, persisted in `save_data.json`) on the Title Screen, defaulting to **Online**.
- **Title Screen Name Editing:** Relocated `[N] Change Name` / `player_name` editing onto the Title Screen so players can customize their display `identity` before entering Sanctuary.
- **Offline Mode:** Runs purely locally with zero UDP/TCP sockets active (`network_mode == "OFFLINE"`).
- **Online Mode (Single Active LAN Session):** Assumes at most one shared co-op session per local network. Upon entering Sanctuary in Online mode (`GameState.start_seamless_lan()`), the client probes `LAN_PORT` (`55555`) for existing host broadcasts (~1.6s window):
  - **Active Host Discovered:** Automatically connects as a **Client** via framed TCP `HANDSHAKE` and spawns directly into **Sanctuary** alongside connected peers.
  - **No Host Discovered:** Automatically promotes self to **Host** (`start_hosting()`) and begins broadcasting on `LAN_PORT` (`55555`) immediately from Sanctuary.
  - **Continue / Saved Mid-Run Resume:** Resuming a saved mid-run via **Continue** (`GameState.hydrate_from_disk()`) in Online mode resumes directly as **Host** (`host_in_run = True`), treating any subsequently connecting peers as Waiting Scholars in Sanctuary.
- **Simultaneous Boot Tie-Breaker (`[DONE]`):** An active Host keeps a lightweight `LAN_PORT` (`55555`) listener active so if two Hosts detect each other's UDP broadcasts on the same LAN, the instance with the lexicographically higher `peer_id` yields (`_yield_host_to()`), stops hosting, and connects as a Client to the lower-`peer_id` Host.

### 11.2. Sanctuary Staging, Group Run Launch & Waiting Scholars (`[DONE]`)
- **Sanctuary-Only Spawning & Session Persistence:**
  - Newly connecting Clients always spawn into **Sanctuary** (`in_sanctuary: bool`), never mid-run into an active macro-world instance.
  - Returning to Sanctuary in Online mode (`GameState.on_enter_sanctuary()`) preserves the active Host/Client LAN session rather than calling `stop_network()`.
- **Group Run Launch:**
  - When the Host triggers the `WarpPortal` in Sanctuary to start a run, all players currently present in Sanctuary warp into the run together (`GameState.join_host_active_run()`, receiving the Host's framed `MAP_RESPONSE` and initial Act 1 world state).
- **Mid-Run Joiners ("Waiting Scholars"):**
  - Host `HANDSHAKE` responses and 20Hz UDP snapshots replicate `host_in_run: bool` and `waiting_scholars: int`.
  - When `host_in_run` is `True`, newly joining Clients remain in Sanctuary (`waiting_for_host_run = True`, suppressing `fetch_host_map()` until the Host's party returns and starts a new `WarpPortal` run) and display a HUD banner: *"Waiting for current run to finish..."*.
  - Active players out in the run see a live HUD indicator showing the count of waiting players (e.g., *"1 Scholar waiting in Sanctuary"* / *"N Scholars waiting in Sanctuary"*).
  - **Pause Menu Regroup Option (`"Return to Sanctuary"`):** Whenever `waiting_scholars > 0`, `PauseMenu` surfaces a **"Return to Sanctuary"** option (`GameState.return_party_to_sanctuary()`) so the active party can cleanly abandon the current run—running standard `on_enter_sanctuary()` purification (resetting Torn Pages, run gear, and modifiers) while keeping the Online LAN session alive—and regroup in Sanctuary with the waiting players.

### 11.3. Disruptive Host Promotion on Disconnect (`[DONE]`)
- If the Host disconnects or times out (`HOST_DISCONNECT`), surviving Clients do not get kicked to the title screen:
  1. **Deterministic Roster Retention:** Clients retain the latest `session_players` `peer_id` roster (`last_survivor_peer_ids`) across the disconnect frame so all survivors agree deterministically on promotion order.
  2. **Sanctuary Regroup:** All surviving Clients warp back to **Sanctuary** (cleaning up active run state via `on_enter_sanctuary()`).
  3. **Lexicographic `peer_id` Promotion:** The surviving Client with the lexicographically lowest `peer_id` automatically promotes itself to **Host** (`start_hosting()`), while any other surviving Clients reconnect to the newly promoted Host in Sanctuary.

## 12. 5-Act Unbound Chronicle Progression & Expanded Biomes [DONE]

> **STATUS:** `[DONE]` — Pass 1 & Pass 2 complete (5-Act `current_act: 1..5` progression, 5-of-7 `CHRONICLE_BIOME_ROSTER` draft & ordering UI, `ACT_SATURATION_MATRIX` scaling, `BIOME_ACT_SEGMENT_POOLS` & `resolve_segment_pool()` lower-Act fallback loader, 5-Act LAN co-op replication, procedural 40x40 PNG tiles/props, and native on-disk `maps/segments/` pools + `tools/edit_map.py` parity for `vitreous_basin` and `sunlit_aqueducts`).

### 12.1. 5-Act Run Structure & "Unbound Chronicle" Biome Draft (`[DONE]`)
- **5-Act Loop (`current_act: 1..5`, `[DONE]`):** Expanded the core run loop from 2 Acts to **5 Acts (Nights 1–5)** (`MAX_ACTS = 5`), framed in lore as binding and arranging the **Unbound Chronicle** (five surviving chapter folios) in Sanctuary before stepping into the rain.
- **Pre-Run Biome Draft & Ordering (`run_biomes` of length 5, `[DONE]`):**
  - Before launching a run via `WarpPortal` (`GameState.open_chronicle_biome_dialog()` and `ui/menu.py:draw_chronicle_biome_menu`), the player—or the **Host** in Seamless LAN Co-op—selects and orders **5 distinct biomes** from the 7-biome `CHRONICLE_BIOME_ROSTER` to assign one biome to each Act (**Act 1 through Act 5**).
- **Act Saturation / Escalation Matrix (Acts 1–5, `[DONE]`):**
  - Each Act rank (`1..5`) progressively increases rain/ink saturation via `ACT_SATURATION_MATRIX`:
    - **Enemy Tiers:** Act 1–2 base castes (`empowered = False`, `1.0x` / `1.25x`) escalating into Act 3–5 empowered and ink-saturated variants (`empowered = True`, `1.6x` / `2.0x` / `2.5x`).
    - **Landmark & Hazard Intensity:** Storm exposure `rain_dps` scales from `2.0` (Act 1) to `4.0` (Act 5), and `MarginaliaEventEngine` supports 1 event roll per Act across Acts 1–5.
    - **Torn Page & Cradle Rewards:** Higher Acts yield increased Torn Page rewards (`1.0x` in Act 1 up to `2.0x` in Act 5 via `scale_pages_for_act()`) within the single active run pool (resetting to `0` upon returning to Sanctuary per `docs/world_and_lore.md`) and weapon rolls that strictly obey the two-slot **Full-Cradle Rule**.

### 12.2. Expanded 7-Biome Pool (`[DONE]`)
Registered `vitreous_basin` and `sunlit_aqueducts` in `CHRONICLE_BIOME_ROSTER`, `BIOME_DISPLAY_NAMES`, `BIOME_THEMES`, `BIOME_PALETTES`, and `BIOME_SEGMENT_POOLS`, with procedural 40x40 PNGs in `assets/graphics/` and on-disk segment JSONs in `maps/segments/`:
1. **Sunken Glass & Salt Flats (*The Vitreous Basin*, `vitreous_basin`, `[DONE]`):**
   - Crystalline salt crusts (`vitreous_salt_floor.png`), fractured reflective glass flats (`vitreous_glass_flat.png`), and jagged salt-spire obstacles (`vitreous_salt_spire.png`), with open-sightline Sentry/Wolf/Flutter/Bat pairings empowering across Acts 1–5.
2. **Overgrown Terracotta & Moss Ruins (*The Sunlit Aqueducts*, `sunlit_aqueducts`, `[DONE]`):**
   - Sun-bleached terracotta flagstones (`aqueduct_terracotta_floor.png`), moss-draped stone walls/channels (`aqueduct_moss_wall.png`), and cracked aqueduct pillars (`aqueduct_pillar.png`), with chokepoint Bindling/Slug/Smear/Wolf/Sentry pairings empowering across Acts 1–5.
- **Per-Biome Implementation & LAN Sync Scope (`[DONE]`):**
  - Deterministic sprite/tile generation (`generate_assets.py`), runtime segment pool generation (`generate_maps.py --generate-pools` -> `maps/segments/<biome>/`), `Renderer` wiring, and `tools/edit_map.py` (`MASTER_TOOL_REGISTRY`) palette parity are all complete.
  - Host-driven 5-Act `run_biomes` (`len == 5`), `act_worlds` (`1..5`), `current_act` (`1..5`), and framed TCP `MAP_RESPONSE` + 20Hz UDP transition sync are `[DONE]` in `engine/game_state.py`.

### 12.3. Act-Keyed Map Segments & Incremental Backfill Architecture (`[DONE]`)
- **Act-Keyed Segment Pools (`(biome_id, act_number)`, `[DONE]`):**
  - `BIOME_ACT_SEGMENT_POOLS[(biome_id, act_number)]` in `constants.py` allows higher Acts to register bespoke room geometry, chokepoints, environmental hazards, and secret vaults incrementally.
- **Lower-Act Fallback Loader (`resolve_segment_pool()`, `[DONE]`):**
  - `engine/world_generator.py:resolve_segment_pool(biome_id, act_number)` resolves `(biome_id, act_number)` by walking `act_number` down to `1` in `BIOME_ACT_SEGMENT_POOLS` and falling back to `BIOME_SEGMENT_POOLS[biome_id]` across all 7 first-class biomes (while future bespoke Act 3–5 segment variants remain an ongoing incremental content track).

## 13. Map Generation & Corridor Pathing Fixes
- **Tech Tower Hallway Chokepoints (`generate_maps.py`, `maps/segments/tech_tower/`):**
  - Heavy Bookcases (`SYMBOL_BOOKCASE` / `'h'`, `80x40`) and Benches (`SYMBOL_BENCH` / `'S'`) placed by `generate_architectural_biome()` in Tech Tower hallways can block navigable paths and narrow corridors.
  - Add hallway/corridor clearance guards during architectural prop dressing to preserve guaranteed walkable throughput, re-verify BFS flood-fill connectivity across all `maps/segments/tech_tower/` rooms and corridors, and regenerate segment pools (`--generate-pools`).

## 14. Combat & Progression Balance [DONE]
- **Attack-Up Scaling Rebalanced (`[DONE]` — `constants.py`, `engine/world.py`, `engine/game_state.py`, `engine/player.py`, `ui/menu.py`, `rendering/renderer.py`):**
  - Added `PROWESS_ATTACK_STEP` (`3`) and `FORTIFICATION_HP_STEP` (`10`) in `constants.py` and replaced hardcoded `* 5` / `// 5` Prowess math across Respite finalization (`Respite.execute_finalize_upgrades()`), staging/upgrades (`GameState.get_staged_respite_info()`, `GameState._handle_upgrade()`), passive Edification (`Player.take_damage()`), Respite menu labels (`ui/menu.py`), and Expanded Inspect HUD (`rendering/renderer.py`).
  - Rebalanced Choice of Fates (`GameState.trigger_choice_of_fates()`) via `CHOICE_OF_FATES_ATTACK_BASE` (`3`), `CHOICE_OF_FATES_HP_BASE` (`5`), and `CHOICE_OF_FATES_MINOR_RATIO` (`0.25`), and toned down Binder Scripts `"serif_minor"` (`+2 Attack`) and `"serif_major"` (`+5 Attack`).
- **Enemy & Boss HP Pools Increased (`[DONE]` — `constants.py`, `engine/enemy.py`):**
  - Raised base HP constants across all standard castes (`SLUG_MAX_HP = 65`, `BAT_MAX_HP = 35`, `FLUTTER_MAX_HP = 15`, `BINDLING_MAX_HP = 80`, `SMEAR_MAX_HP = 95`, `SENTRY_MAX_HP = 70`, `WOLF_MAX_HP = 60`) and `MINIBOSS_MAX_HP = 450`.
  - Added explicit `NIGHT_BOSS_MAX_HP = 950` and `FINAL_AUTHOR_MAX_HP = 1600` constants in `constants.py` wired directly into `NightBoss` and `FinalAuthor`.
- **Normalized Boss Distribution Across All 7 Biomes (`[DONE]` — `constants.py`, `generate_maps.py`, `engine/world_generator.py`, `maps/segments/`):**
  - Standardized `generate_organic_biome()`, `generate_architectural_biome()`, and `generate_biome_segment()` using `SEGMENT_MINIBOSS_MIN_DIM = 100` so all 7 biome pools share identical `[1, 0, 1, 0]` room miniboss quotas and `[0, 0, 0, 0]` corridor quotas, regenerated all 56 segments via `--generate-pools`, and updated `WorldGenerator.generate_layout()` to deal rooms to an exact `ACT_MINIBOSS_BUDGET = 4` minibosses per Act across all 7 biomes.

## 15. Respite Interaction & World Lifecycle Locks [DONE]
- **Block Interaction When Hostiles Are Nearby (`[DONE]` — `constants.py`, `engine/world.py`):**
  - `Respite.execute_interaction()` blocks opening the Respite menu whenever any alive enemy is within `RESPITE_HOSTILE_BLOCK_RADIUS` (`320.0`) of the player or actively aggroed (`CHASE`/`WIND_UP`/`STRIKE`/`RECOVERY`), surfacing a clear Respite Anchor dialogue message.
- **Disable Respite During/After Night Boss Fight (`[DONE]` — `engine/world.py`, `engine/weather.py`, `engine/game_state.py`):**
  - Added `GameState.night_boss_spawned` (set on `NightBoss` spawn; reset on Act transition, `on_enter_sanctuary()`, and `reset_to_new_game()`), locking out `Respite.execute_interaction()` whenever `night_boss_spawned` is `True`, an active `NightBoss` is present, or `WeatherManager.bleed_state` is in `("BOSS_PHASE", "DILUTION", "APPENDIX")`.
- **Auto-Close Respite Menu on Warp (`[DONE]` — `engine/game_state.py`):**
  - Added `GameState.close_respite_menu()` invoked at the start of `GameState.start_warp()` (as well as on rain exposure and Night Boss spawn) to clear `active_respite`, dismiss Respite-tied `active_dialogue`, and reset `respite_upgrades`, `respite_selection_idx`, `respite_marked_idx`, and `player.has_rested_this_session`.
- **Defer Enemy Aggro Until Respite Menu Closes (`[DONE]` — `engine/actor.py`, `engine/enemy.py`, `engine/world.py`):**
  - `Actor.get_active_runner_positions()` and `Enemy.attempt_damage_player()` exclude the resting local player while `state.active_respite` is open (covering `Actor._update_state_logic()`, `FlutterEnemy._update_state_logic()`, and melee contact damage while keeping non-resting LAN Co-op peers targetable), restoring normal aggro immediately once the Respite menu closes or is closed by rain.
