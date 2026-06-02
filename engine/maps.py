"""Map factory for creating world instances from prototypes.
"""
import os
from engine.world import World, LevelLoader
from constants import get_generated_world_path

def create_world(name: str, saved_enemies=None, defeated_ids=None) -> World:
    """Factory function to create and populate a World instance by name."""
    print(f"[DEBUG] Fetching room prototype: {name}")

    # Realignment Rule: 'macro_world' identifier now triggers the procedural generator
    if name == "macro_world":
        from engine.world_generator import WorldGenerator
        gen = WorldGenerator()
        gen.generate_layout()
        temp_path = get_generated_world_path()
        gen.export_world(temp_path)
        
        # Load from the temporary path
        world = World(name="generated_world")
        world.grid, world.interactables, world.warp_tiles, world.player_start, world.enemies, world.boss_coords_list, world.module_sockets = \
            LevelLoader.load_json_map(temp_path, saved_enemies=saved_enemies, defeated_ids=defeated_ids)
        return world

    world = World(name=name)

    # Check for external JSON map first
    # Special Rule: 'generated_world' loads from the temporary path
    if name == "generated_world":
        json_path = get_generated_world_path()
    else:
        json_path = os.path.join("maps", f"{name}.json")
        
    if os.path.exists(json_path):
        world.grid, world.interactables, world.warp_tiles, world.player_start, world.enemies, world.boss_coords_list, world.module_sockets = \
            LevelLoader.load_json_map(json_path, saved_enemies=saved_enemies, defeated_ids=defeated_ids)
        return world

    # Fallback to programmatic/hardcoded prototypes
    if name == "outside":
        return create_world("macro_world")

    return world
