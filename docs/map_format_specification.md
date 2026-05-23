# Map Serialization Format & Modular Nesting Protocol

This document defines the JSON structure for external level asset files and details how maps are designed manually and nested modularly.

## 1. JSON Level Schema Blueprint
Every map file saved by our editor must compile to a standard structured JSON document containing metadata and a clean string matrix:

```json
{
  "map_id": "chapter1_arena_alpha",
  "dimensions": { "width": 20, "height": 10 },
  "legend": {
    "#": "WALL_STONE",
    ".": "FLOOR_CLEAN",
    "B": "BREAKABLE_BARREL",
    "S": "BENCH_VERTICAL"
  },
  "grid": [
    "####################",
    "#..................#",
    "#..B............S..#",
    "####################"
  ],
  "entities": {
    "15,9": {
        "target": "macro_world",
        "name": "The Chronicle"
    }
  }
}
```
*Note: Entity keys are stored as "x,y" strings to remain JSON-compliant.*

## 2. Macro-World Map Protocol
Macro-world maps (such as `world_map1.json`) are no longer procedurally generated. They are hand-designed directly within the map editor to maintain absolute control over the world layout, atmospheric corridors, and non-linear looping pathways.

### Future Specification: Manual Multi-Size Modular Splicing
While the game engine expands, macro-world files will support stitching sub-maps of **variable coordinate footprints** (e.g., small $10 \times 10$ alcoves, standard $20 \times 20$ chambers, or massive $40 \times 40$ arenas).

#### Architectural Goals:
- **Spatial Anchoring:** Sub-maps will be injected into a "Master Loom" JSON file that defines coordinate anchors $(x, y)$ for each module.
- **Variable Footprints:** The engine will support modules of any size, dynamically carving out the required space in the master grid at runtime.
- **Portals & Seamless Flow:** Module boundaries will be designed to align perfectly with the Master Loom's corridors, ensuring seamless player movement without loading screens within a chapter.
- **Manual Control:** This replaces procedural noise-based generation with intentional, high-quality level design that guarantees a balanced flow of combat and respite zones.
