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

### 1. Abstract Socket Classification Tagging
Every socket registered on the macro layout canvas possesses a regional classification tier determining its pool filtering logic:
- `SIZE_120X120` Pools: Filtered into standard narrative macro-zones (e.g., `Forest`, `Ruins`).
- `SIZE_40X40_OUTER` (The Margins): Sockets along the outermost grid edges. Restricted to filtering the player's initial entry node (`The Colophon / Spawn`) and generic low-tier buffer modules.
- `SIZE_40X40_INNER` (The Crown Ring): Sockets contained inside the central 200x200 space (3x3 to 7x7 in an 11x11 grid), bounding the center socket. Restricted to spawning the high-tier `Night Boss` encounter in a single random node, with adjacent slots pulling from standard hazard pools.

### 2. Runtime Selection Sequence & Rule Logic
1. **The Core Allocation Pass:** The generator calculates dimensions and draws empty socket frames across the canvas matrix.
2. **The Spawn Assignment Phase:** The compiler selects exactly one socket matching the `SIZE_40X40_OUTER` criteria and binds it to `maps/the_colophon.json` (Spawn).
3. **The Target Assignment Phase:** The compiler selects exactly one socket matching the `SIZE_40X40_INNER` criteria and binds it to `maps/night_boss_arena.json`.
4. **The Pool Backfill Pass:** All remaining unassigned sockets independently roll selections from their matching dimension lists (e.g., 120s roll Forest/Ruins; remaining 40s roll from minor encounter pools).

## 6. Runtime Symmetrical Compilation Pipeline (440x440 Matrix)

The WorldGenerator constructs the active run map dynamically using a multi-pass blitting pipeline. It reads standalone module assets and maps them to a synchronized offset grid:

### 1. Coordinate Offsetting Math
The layout coordinates are computed by tracking the cumulative widths of preceding columns and rows:
- Column/Row Index 0, 2, 4: Size = 120 tiles
- Column/Row Index 1, 3: Size = 40 tiles

### 2. The Generation Cycle
When the Chronicle gateway is activated:
1. Initialize a blank 440x440 grid matrix filled with solid wall blocks or void tiles.
2. Filter out one random perimeter 40x40 socket slot and stitch `maps/the_colophon.json` into it. Store these absolute coordinates as the Player Spawn Point.
3. Filter out one random inner 40x40 socket slot and stitch `maps/night_boss.json` into it.
4. Loop through remaining 120x120 slots, randomly choosing between `maps/forest.json` and `maps/ruins.json` per slot.
5. Loop through remaining 40x40 slots, filling them with blank corridor layouts or small encounter modules.

## 7. Macro Matrix Canvas Space & Boss Entity Definitions

### 1. Border Boundary Clamping (Zero-Wall Mapping)
The 440x440 grid represents the total legal coordinate bounds of a run session. Physical perimeter walls are not structurally required to trap the player. The engine's movement processor clamps entity coordinates: `0 <= x_pos < 440` and `0 <= y_pos < 440`. 
- **Canvas Initialization:** The `WorldGenerator` initializes a blank map entirely using empty floor or corridor spacing tiles (`" "`). Sockets overlay their explicit internal geometry, ensuring the spaces connecting modules remain wide-open, passable paths.

### 2. High-Tier Entity: The Night Boss
The Night Boss is a singular high-tier threat variant that inherits all base `.is_miniboss = True` parameters, with distinct unique behavioral traits:
- **Identifier String:** `"night_boss"`
- **Loot Drop Tier:** Guaranteed maximum premium page bundle and special unique anomaly item drops.
- **Spawning Constraint:** Only instantiates via the dedicated `maps/night_boss_arena.json` module.
