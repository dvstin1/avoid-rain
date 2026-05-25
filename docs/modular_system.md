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
