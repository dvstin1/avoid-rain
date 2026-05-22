# Map Serialization Format & Modular Nesting Protocol

This document defines the JSON structure for external level asset files and details how maps can be nested modularly to form expansive game worlds.

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

