"""Map factory for creating world instances from prototypes.
"""
from engine.world import World
from engine.room_definitions import ROOM_PROTOTYPES, ENTITY_MANIFEST
from engine.enemy import SlugEnemy
from constants import TILE_SIZE

def create_world(name: str) -> World:
    """Factory function to create and populate a World instance by name."""
    print(f"[DEBUG] Fetching room prototype: {name}")
    world = World(name=name)
    
    # Check if we have a prototype for this world name
    if name in ROOM_PROTOTYPES:
        prototype = ROOM_PROTOTYPES[name]
        entities = ENTITY_MANIFEST.get(name, {})
        world.load_from_prototype(prototype, entities)
        
        # Room-specific logic (like enemy spawning)
        if name == "chapter1":
            # Spawn a small pack of slug enemies
            world.enemies = [
                SlugEnemy(5 * TILE_SIZE, 5 * TILE_SIZE),
                SlugEnemy(20 * TILE_SIZE, 10 * TILE_SIZE)
            ]
    elif name == "outside":
        # Legacy/Fallback support if needed, but we should prefer 'chapter1'
        return create_world("chapter1")
        
    return world
