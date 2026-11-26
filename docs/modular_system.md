# Modular Level System & Serialization

This document defines the "Master Loom" modular assembly system and the JSON schema used for all map assets.

## 1. Map Serialization Schema
All map files are structured JSON documents containing metadata, a character-based grid matrix, and entity definitions.

```json
{
  "map_id": "chapter1_arena_alpha",
  "dimensions": { "width": 20, "height": 10 },
  "legend": {
    "#": "WALL_STONE",
    ".": "FLOOR_CLEAN",
    "B": "BREAKABLE_BARREL"
  },
  "grid": [
    "####################",
    "#..................#",
    "####################"
  ],
  "entities": {
    "15,9": { "target": "macro_world", "name": "The Chronicle" }
  },
  "module_sockets": [
    {
      "name": "M1",
      "bounds": { "x": 4, "y": 2, "width": 8, "height": 8 },
      "active_plug": "maps/industrial_core.json"
    }
  ]
}
```
*Note: Entity keys are stored as "x,y" strings. Sockets define regions where sub-maps are dynamically injected at runtime.*

## 2. Runtime Modular Assembly (The Master Loom)
The engine performs a pre-parsing pass whenever a map containing `module_sockets` is loaded.

- **Stitching Pass:** The system overlays sub-map grid matrices onto the master macro-grid using the socket's `(x, y)` offset.
- **Entity Blitting:** Sub-map entities (enemies, items) are transposed into absolute world coordinates: `(socket.x + local.x, socket.y + local.y)`.
- **Validation Rules:**
    - **Dimensions Alignment:** Sub-maps must match the exact width/height of the target socket.
    - **Independent Rolls:** Every socket has a 1 in 10 (10%) chance to independently roll a "Special Edition" module from the anomaly pool.

## 3. Room Design Blueprint
Modules are designed according to geographical archetypes to ensure diverse spatial flows.

| Archetype | Concept | Gimmick / Hazard |
| :--- | :--- | :--- |
| **The Cave** | Narrow serpentine tunnels. | **Line of Sight:** High bat concentration in shadows. |
| **The Ruins** | Rigid geometric matrix. | **Chokepoints:** Easy to get cornered by minibosses. |
| **The Village** | Clusters of buildings. | **Interior vs Exterior:** Safety from range vs. swarm traps. |
| **The Outpost** | High verticality/ramparts. | **High Ground:** Ranged hazards target you from above. |
| **The Forest** | Massive open floor. | **Disorientation:** Lack of walls makes flanking easy. |
| **The Pond** | Large central ink hazard. | **Restriction:** Exterior perimeter paths only. |

## 4. Macro-World Protocol
Macro-world maps (e.g., `world_map1.json`) are hand-designed in the editor to maintain absolute control over non-linear looping pathways. They serve as the "Tissue" frame that links multiple disparate "Cell" modules into a cohesive exploration chapter.

## 5. Macro-Layout Matrix Generator & Dynamic Sub-Map Pool Rules

To support scaling world canvases (e.g., 440x440 grids) with variable socket divisions, the level compiler initializes worlds using an abstract layout manifest descriptor.

### 1. Single-Biome World Cohesion & Per-Biome Segment Pools
To prevent jarring mid-map biome transitions, each generated Act macro-world selects **one cohesive biome** from `BIOME_SEGMENT_POOLS` in `constants.py` across all **7 first-class biomes** (`windy_ridge`, `pastoral_valley`, `swamp_mire`, `frozen_peaks`, `tech_tower`, `vitreous_basin`, `sunlit_aqueducts`) and populates every room and corridor slot exclusively from that biome's segment pool (`maps/segments/<biome>/`, 8 files per biome = 56 active runtime segments).

> **Note:** Top-level `maps/<biome>.json` files (e.g., `maps/windy_ridge.json`, `maps/pastoral_valley.json`) and `maps/smallcave.json` are legacy/test fallbacks only; all active runtime biome layouts and enemy spawns are produced by `generate_maps.py --generate-pools` into `maps/segments/<biome>/` (with corridor clearance, `validate_prop_walkable_connectivity()`, and `validate_wide_prop_clearances()` guards).

Each biome pool contains multiple distinct procedurally generated module segments produced by `generate_maps.py --generate-pools`:
- **120x120 Room Segments (`<biome>_room_1..4.json`):** Varied macro-chambers built using biome-appropriate organic or architectural algorithms, 2.5D verticality/elevation layers, aligned 6-tile-wide cardinal doorway connectors on all four edges, and standardized `[1, 0, 1, 0]` miniboss quotas dealt to an exact `ACT_MINIBOSS_BUDGET = 4` per Act.
- **40x40 Corridor Segments (`<biome>_corridor_1..4.json`):** Varied connecting junctions and passages with aligned cardinal connectors and guaranteed BFS reachability.

### 2. Abstract Socket Classification Tagging
Every socket registered on the macro layout canvas possesses a regional classification tier determining its pool filtering logic:
- `SIZE_120X120` Pools (`resolve_segment_pool(biome, act_number)["rooms"]`): Walks `BIOME_ACT_SEGMENT_POOLS[(biome, k)]` down to `1` and falls back to `BIOME_SEGMENT_POOLS[biome]["rooms"]`, shuffling decks so each Act varies layouts while staying 100% within one biome.
- `SIZE_40X40_OUTER` (The Margins): Sockets along the outermost grid edges. Restricted to filtering the player's initial entry node (`The Colophon / Spawn`: `maps/the_colophon.json`) and corridor segments from `resolve_segment_pool(biome, act_number)["corridors"]`.
- `SIZE_40X40_INNER` (The Crown Ring): Sockets contained inside the central 200x200 space (3x3 to 7x7 in an 11x11 grid), bounding the center socket. One inner socket is reserved for the Act's `Night Boss` encounter center, with adjacent slots pulling exclusively from the selected biome's corridor segment deck.

### 3. Runtime Selection Sequence & Rule Logic
1. **5-Act Unbound Chronicle Biome Resolution (`resolve_run_biomes`):** Drafts **5 distinct biomes** from the 7-biome `CHRONICLE_BIOME_ROSTER` for `Acts 1..5` (`MAX_ACTS = 5`), resolving `Random` slots without duplicates. All 5 Act worlds (`act_worlds[1..5]`) are generated upfront and bundled into the initial framed TCP `MAP_RESPONSE` payload (`act_worlds`, `run_biomes`, `current_act`) for LAN co-op clients.
2. **The Core Allocation Pass:** The generator calculates dimensions and draws empty socket frames across the 440x440 canvas matrix.
3. **The Spawn Assignment Phase:** The compiler selects one `SIZE_40X40_OUTER` socket and binds it to `maps/the_colophon.json` (Spawn).
4. **The Target Assignment Phase:** The compiler selects one `SIZE_40X40_INNER` socket for the Act's Night Boss encounter.
5. **The Single-Biome Pool Backfill Pass:** All remaining unassigned `120x120` and `40x40` sockets are filled from shuffled decks drawn exclusively from the active biome's segment pool (`resolve_segment_pool(biome, act_number)`).

## 6. Runtime Symmetrical Compilation Pipeline (440x440 Matrix)

The WorldGenerator constructs the active run map dynamically using a multi-pass blitting pipeline. It reads standalone module assets and maps them to a synchronized offset grid:

### 1. Coordinate Offsetting Math
The layout coordinates are computed by tracking the cumulative widths of preceding columns and rows:
- Column/Row Index 0, 2, 4: Size = 120 tiles
- Column/Row Index 1, 3: Size = 40 tiles

### 2. The Generation Cycle
When the Chronicle gateway is confirmed:
1. Resolve 5 distinct biomes for Acts 1–5 (`run_biomes`) and generate all 5 440x440 single-biome grids upfront (`act_worlds`).
2. For each Act world, filter out one random perimeter 40x40 socket slot and stitch `maps/the_colophon.json` into it as the Player Spawn Point.
3. Filter out one random inner 40x40 socket slot as the Act's Night Boss Arena center (`boss_coords_list`).
4. Loop through remaining 120x120 slots, popping from a shuffled deck of the selected biome's room segments (`maps/segments/<biome>/<biome>_room_*.json`) matching `ACT_MINIBOSS_BUDGET = 4`.
5. Loop through remaining 40x40 slots, popping from a shuffled deck of the selected biome's corridor segments (`maps/segments/<biome>/<biome>_corridor_*.json`).
6. Upon defeating the Act 5 Night Boss, players warp into the standalone 72x72 Final Boss Arena (`maps/night_boss_arena.json`).

> **Cross-Link:** Sub-arena `"map_anchor"` encounters in the **Marginalia Event Engine** (`docs/architecture.md` Section 16; `docs/backlog.md` Section 10) extend this warp model with a `ReturnAnchor(map_path, x, y)` stack so the party can warp into a compact pocket arena (`"ink_well_cellar"`) and return to the exact overworld coordinates via an Exit Ladder.

## 7. Macro Matrix Canvas Space & Boss Entity Definitions

### 1. Border Boundary Clamping (Zero-Wall Mapping)
The 440x440 grid represents the total legal coordinate bounds of a run session. Physical perimeter walls are not structurally required to trap the player. The engine's movement processor clamps entity coordinates: `0 <= x_pos < 440` and `0 <= y_pos < 440`. 
- **Canvas Initialization:** The `WorldGenerator` initializes a blank map entirely using empty floor or corridor spacing tiles (`" "`). Sockets overlay their explicit internal geometry, ensuring the spaces connecting modules remain wide-open, passable paths.

### 2. High-Tier Entity: The Night Boss
The Night Boss is a singular high-tier threat variant that inherits all base `.is_miniboss = True` parameters, with distinct unique behavioral traits:
- **Identifier String:** `"night_boss"`
- **Loot Drop Tier:** Guaranteed maximum premium page bundle and special unique anomaly item drops.
- **Spawning Constraint:** Only instantiates via the dedicated `maps/night_boss_arena.json` module.
