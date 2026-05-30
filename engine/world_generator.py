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

from constants import TILE_SIZE

class WorldGenerator:
    """Handles the data-driven generation of the macro-world layout."""
    def __init__(self, world_id="macro_generated"):
        self.world_id = world_id
        self.total_size = 440
        self.sockets = []
        self.spawn_x = 0
        self.spawn_y = 0
        self.boss_coords_list = []
        
        # Asset pools (Strictly mapped by size)
        self.asset_pools = {
            "120x120": ["maps/forest.json", "maps/ruins.json"],
            "40x40": ["maps/smallcave.json"]
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

        # 4. The Target Assignment Phase (Night Boss - DUAL)
        inner_40s = [s for s in self.sockets if "40x40" in s["tags"] and "inner" in s["tags"]]
        # Select two distinct arenas
        arenas = random.sample(inner_40s, 2) if len(inner_40s) >= 2 else inner_40s

        self.boss_coords_list = []
        for i, boss_socket in enumerate(arenas):
            boss_socket["active_plug"] = "maps/night_boss_arena.json"
            # Corrected: bounds are already in tiles
            bx = boss_socket["bounds"]["x"] + 20
            by = boss_socket["bounds"]["y"] + 20
            self.boss_coords_list.append({"x": bx, "y": by})

        
        # 5. The Pool Backfill Pass
        from constants import POOL_SPECIAL_EDITION, POOL_MONTHLY_REPORT
        for s in self.sockets:
            if s["active_plug"] is None:
                is_large = "120x120" in s["tags"]
                pool = filtered_120 if is_large else filtered_40
                
                # 10% Anomaly Roll
                if is_large and random.random() < 0.1 and POOL_SPECIAL_EDITION:
                    s["active_plug"] = random.choice(POOL_SPECIAL_EDITION)
                else:
                    s["active_plug"] = random.choice(pool) if pool else "maps/smallcave.json"

    def export_world(self, filename="maps/generated_world.json"):
        """Exports the layout as a macro-world JSON file."""
        module_sockets = []
        for s in self.sockets:
            module_sockets.append({
                "name": s["id"],
                "bounds": s["bounds"],
                "active_plug": s["active_plug"]
            })
        
        base_grid = [" " * self.total_size for _ in range(self.total_size)]
        
        data = {
            "map_id": self.world_id,
            "dimensions": {"width": self.total_size, "height": self.total_size},
            "legend": {"#": "WALL_STONE", " ": "FLOOR_CLEAN", ".": "FLOOR_CLEAN"},
            "grid": base_grid,
            "entities": {},
            "module_sockets": module_sockets,
            "spawn_coords": {"x": self.spawn_x, "y": self.spawn_y},
            "boss_coords_list": self.boss_coords_list
        }
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Generated world exported to {filename}")

if __name__ == "__main__":
    gen = WorldGenerator()
    gen.generate_layout()
    gen.export_world()
