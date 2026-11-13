"""
Macro-World Generator for Avoid Rain.
Generates a symmetric 440x440 grid of modules based on modular_system.md specifications.
Grid Blueprint: 9 rooms (120x120) and connecting corridors/junctions (40x40).
"""
import os
import json
import random
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import (
    get_generated_world_path,
    BIOME_SEGMENT_POOLS,
    POOL_MONTHLY_REPORT,
    POOL_CORRIDOR,
)


class WorldGenerator:
    """Handles the data-driven generation of a single-biome macro-world layout."""

    def __init__(self, world_id="macro_generated", biome=None):
        self.world_id = world_id
        self.total_size = 440
        self.sockets = []
        self.spawn_x = 0
        self.spawn_y = 0
        self.boss_coords_list = []

        available_biomes = list(BIOME_SEGMENT_POOLS.keys())
        if biome and biome in BIOME_SEGMENT_POOLS:
            self.biome = biome
        else:
            self.biome = random.choice(available_biomes)

        biome_pool = BIOME_SEGMENT_POOLS.get(self.biome, {})
        # Asset pools strictly scoped to the selected cohesive biome
        self.asset_pools = {
            "120x120": list(biome_pool.get("rooms", POOL_MONTHLY_REPORT)),
            "40x40": list(biome_pool.get("corridors", POOL_CORRIDOR)),
        }

    def generate_layout(self):
        """Executes the allocation rule pipeline using an 11x11 unit grid base."""
        self.sockets = []
        unit = 40
        grid_size = 11

        # 1. Create the grid of sockets
        for gy in range(grid_size):
            for gx in range(grid_size):
                # Room logic: Rooms are 3x3 units (120x120) starting at indices (0,4,8)
                is_room_origin = gx in (0, 4, 8) and gy in (0, 4, 8)
                
                # Check if this cell is part of ANY room
                in_room_x = (0 <= gx <= 2) or (4 <= gx <= 6) or (8 <= gx <= 10)
                in_room_y = (0 <= gy <= 2) or (4 <= gy <= 6) or (8 <= gy <= 10)
                is_part_of_room = in_room_x and in_room_y

                if is_room_origin:
                    self.sockets.append({
                        "id": f"Room_{gx}_{gy}",
                        "bounds": {"x": gx * unit, "y": gy * unit, "width": 120, "height": 120},
                        "tags": ["120x120", "room"],
                        "active_plug": None
                    })
                elif not is_part_of_room:
                    # It's a 40x40 corridor or junction
                    tags = ["40x40", "corridor"]
                    if gx == 0 or gx == 10 or gy == 0 or gy == 10:
                        tags.append("outer")
                    else:
                        tags.append("inner")
                    
                    self.sockets.append({
                        "id": f"Socket_{gx}_{gy}",
                        "bounds": {"x": gx * unit, "y": gy * unit, "width": 40, "height": 40},
                        "tags": tags,
                        "active_plug": None
                    })

        # 2. Hard Size Filter Pass (Purge legacy or mismatch files)
        def validate_pool(file_list, expected_w, expected_h):
            valid = []
            for path in file_list:
                if not os.path.exists(path): continue
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    dw, dh = data["dimensions"]["width"], data["dimensions"]["height"]
                    if dw == expected_w and dh == expected_h:
                        valid.append(path)
                    else:
                        print(f"[FILTER] Ignoring {path}: expected {expected_w}x{expected_h}, got {dw}x{dh}")
                except Exception: continue
            return valid

        filtered_120 = validate_pool(self.asset_pools["120x120"], 120, 120)
        filtered_40 = validate_pool(self.asset_pools["40x40"], 40, 40)

        # 3. The Spawn Assignment Phase (The Colophon)
        outer_40s = [s for s in self.sockets if "40x40" in s["tags"] and "outer" in s["tags"]]
        spawn_socket = random.choice(outer_40s)
        spawn_socket["active_plug"] = "maps/the_colophon.json"
        # Corrected: bounds are already in tiles, no division by TILE_SIZE needed
        self.spawn_x = spawn_socket["bounds"]["x"] + 20
        self.spawn_y = spawn_socket["bounds"]["y"] + 20

        # 4. The Target Assignment Phase (Act Circle-Closing Night Boss)
        inner_40s = [s for s in self.sockets if "40x40" in s["tags"] and "inner" in s["tags"]]
        boss_socket = random.choice(inner_40s) if inner_40s else None

        self.boss_coords_list = []
        if boss_socket is not None:
            boss_socket["active_plug"] = random.choice(filtered_40) if filtered_40 else "maps/smallcave.json"
            bx = boss_socket["bounds"]["x"] + 20
            by = boss_socket["bounds"]["y"] + 20
            self.boss_coords_list.append({"x": bx, "y": by})

        
        # 5. The Pool Backfill Pass (Single cohesive biome deck across all sockets)
        room_deck = []
        corridor_deck = []
        fallback_room = f"maps/{self.biome}.json"
        for s in self.sockets:
            if s["active_plug"] is None:
                is_large = "120x120" in s["tags"]
                if is_large:
                    if not room_deck and filtered_120:
                        room_deck = list(filtered_120)
                        random.shuffle(room_deck)
                    if room_deck:
                        s["active_plug"] = room_deck.pop()
                    elif os.path.exists(fallback_room):
                        s["active_plug"] = fallback_room
                    else:
                        s["active_plug"] = "maps/smallcave.json"
                else:
                    if not corridor_deck and filtered_40:
                        corridor_deck = list(filtered_40)
                        random.shuffle(corridor_deck)
                    if corridor_deck:
                        s["active_plug"] = corridor_deck.pop()
                    else:
                        s["active_plug"] = "maps/smallcave.json"

    def to_dict(self):
        """Builds the serializable macro-world JSON dictionary."""
        module_sockets = [
            {
                "name": s["id"],
                "bounds": s["bounds"],
                "active_plug": s["active_plug"],
            }
            for s in self.sockets
        ]
        base_grid = [" " * self.total_size for _ in range(self.total_size)]
        return {
            "map_id": self.world_id,
            "biome": self.biome,
            "dimensions": {"width": self.total_size, "height": self.total_size},
            "legend": {"#": "WALL_STONE", " ": "FLOOR_CLEAN", ".": "FLOOR_CLEAN"},
            "grid": base_grid,
            "entities": {},
            "module_sockets": module_sockets,
            "spawn_coords": {"x": self.spawn_x, "y": self.spawn_y},
            "boss_coords_list": self.boss_coords_list,
        }

    def export_world(self, filename=None):
        """Exports the layout as a single-biome macro-world JSON file."""
        if filename is None:
            filename = get_generated_world_path()

        data = self.to_dict()
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Generated world exported to {filename}")


def resolve_run_biomes(act1_choice=None, act2_choice=None):
    """Resolves Act 1 and Act 2 biomes, guaranteeing Act 1 != Act 2."""
    all_biomes = list(BIOME_SEGMENT_POOLS.keys())
    if act1_choice and act1_choice in BIOME_SEGMENT_POOLS:
        act1 = act1_choice
    else:
        act1 = random.choice(all_biomes)

    remaining = [b for b in all_biomes if b != act1]
    if act2_choice and act2_choice in BIOME_SEGMENT_POOLS and act2_choice != act1:
        act2 = act2_choice
    else:
        act2 = random.choice(remaining) if remaining else act1

    return act1, act2


def generate_dual_worlds(act1_choice=None, act2_choice=None):
    """Generates both Act 1 and Act 2 single-biome world maps upfront for a two-act run."""
    act1_biome, act2_biome = resolve_run_biomes(act1_choice, act2_choice)

    gen1 = WorldGenerator(world_id="macro_act1", biome=act1_biome)
    gen1.generate_layout()
    act1_path = get_generated_world_path()
    gen1.export_world(act1_path)

    gen2 = WorldGenerator(world_id="macro_act2", biome=act2_biome)
    gen2.generate_layout()
    act2_path = act1_path.replace(".json", "_act2.json")
    gen2.export_world(act2_path)

    return {
        "act1_biome": act1_biome,
        "act2_biome": act2_biome,
        "act1_data": gen1.to_dict(),
        "act2_data": gen2.to_dict(),
        "act1_path": act1_path,
        "act2_path": act2_path,
    }

if __name__ == "__main__":
    gen = WorldGenerator()
    gen.generate_layout()
    gen.export_world()
