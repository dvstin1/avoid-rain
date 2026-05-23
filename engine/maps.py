"""Map factory for creating world instances from prototypes.
"""
import os
from engine.world import World, LevelLoader

def create_world(name: str) -> World:
    """Factory function to create and populate a World instance by name."""
    print(f"[DEBUG] Fetching room prototype: {name}")

    # Realignment Rule: 'macro_world' identifier now maps to 'world_map1.json'
    if name == "macro_world":
        name = "world_map1"

    world = World(name=name)

    # Check for external JSON map first
    json_path = os.path.join("maps", f"{name}.json")
    if os.path.exists(json_path):
        world.grid, world.interactables, world.warp_tiles, world.player_start, world.enemies = \
            LevelLoader.load_json_map(json_path)
        return world

    # Fallback to programmatic/hardcoded prototypes
    if name == "outside":
        return create_world("macro_world")

    return world
