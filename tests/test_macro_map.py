import pytest
import os
import json
from engine.maps import create_world
from engine.world_generator import WorldGenerator
from constants import TILE_SIZE, BIOME_SEGMENT_POOLS

def test_macro_map_generation():
    """Verify that 'macro_world' triggers generative logic and returns a valid world."""
    world = create_world("macro_world")
    
    assert "generated_world" in world.name
    # Should be massive
    assert len(world.grid[0]) >= 40
    assert len(world.grid) >= 30

def test_macro_map_player_spawn():
    """Verify player spawn in generated world."""
    world = create_world("macro_world")
    
    # Generated world has spawn logic
    assert world.player_start is not None
    assert len(world.player_start) == 2

def test_macro_map_entities():
    """Verify entities are loaded/spawned in the world."""
    world = create_world("macro_world")
    # Procedural world should have some interactables (Barrels, Lore, etc)
    assert len(world.interactables) > 0
    assert world.name != "sanctuary"


def test_single_biome_world_stitching(tmp_path):
    """Verify each generated world map draws all rooms & corridors exclusively from one biome pool."""
    for biome, pools in BIOME_SEGMENT_POOLS.items():
        gen = WorldGenerator(world_id=f"test_{biome}", biome=biome)
        gen.generate_layout()
        assert gen.biome == biome

        room_plugs = [s["active_plug"] for s in gen.sockets if "120x120" in s["tags"]]
        corridor_plugs = [
            s["active_plug"]
            for s in gen.sockets
            if "40x40" in s["tags"]
            and s["active_plug"] not in ("maps/the_colophon.json", "maps/night_boss_arena.json")
        ]

        assert len(room_plugs) == 9
        assert all(plug in pools["rooms"] for plug in room_plugs), f"Cross-biome leak in {biome} rooms: {room_plugs}"
        assert len(set(room_plugs)) > 1, f"Expected multiple room variants for {biome}"
        assert all(plug in pools["corridors"] for plug in corridor_plugs), (
            f"Cross-biome leak in {biome} corridors: {corridor_plugs}"
        )

        out_file = tmp_path / f"{biome}_world.json"
        gen.export_world(str(out_file))
        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["biome"] == biome
