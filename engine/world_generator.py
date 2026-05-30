"""
Macro-World Generator for Avoid Rain.
Generates a symmetric 440x440 grid of modules based on modular_system.md specifications.
Layout: 120 (Room) | 40 (Corridor) | 120 (Room) | 40 (Corridor) | 120 (Room)
"""
import os
import json
import random
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class WorldGenerator:
    """Handles the data-driven generation of the macro-world layout."""
    def __init__(self, world_id="macro_generated"):
        self.world_id = world_id
        self.total_size = 440
        
        # Grid layout specification (width/height of each column/row)
        self.layout_steps = [120, 40, 120, 40, 120]
        
        # Sockets will be a list of dicts with bounds and tags
        self.sockets = []
        
        # Asset pools (Strictly mapped by size)
        self.asset_pools = {
            "120x120": ["maps/forest.json", "maps/ruins.json"],
            "40x40": ["maps/smallcave.json"]
        }

    def generate_layout(self):
        """Executes the allocation rule pipeline."""
        self.sockets = []
        
        # 1. Create the grid of sockets (5x5)
        current_y = 0
        for row_idx, h in enumerate(self.layout_steps):
            current_x = 0
            for col_idx, w in enumerate(self.layout_steps):
                tags = []
                tags.append(f"{w}x{h}")
                
                # Classification tags
                if w == 120 and h == 120:
                    tags.append("room")
                elif w == 40 and h == 40:
                    tags.append("junction")
                    if row_idx in (1, 3) and col_idx in (1, 3):
                        tags.append("inner")
                    else:
                        tags.append("outer")
                else:
                    tags.append("corridor")
                    if row_idx == 0 or row_idx == 4 or col_idx == 0 or col_idx == 4:
                        tags.append("outer")
                    else:
                        tags.append("inner")
                
                self.sockets.append({
                    "id": f"S_{col_idx}_{row_idx}",
                    "bounds": {"x": current_x, "y": current_y, "width": w, "height": h},
                    "tags": tags,
                    "active_plug": None
                })
                current_x += w
            current_y += h

        # 2. Hard Size Filter Pass (Validation of Pools)
        def validate_pool(file_list, expected_w, expected_h):
            valid = []
            for path in file_list:
                if not os.path.exists(path):
                    continue
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    dw = data["dimensions"]["width"]
                    dh = data["dimensions"]["height"]
                    if dw == expected_w and dh == expected_h:
                        valid.append(path)
                    else:
                        print(f"[FILTER] Ignoring {path}: expected {expected_w}x{expected_h}, got {dw}x{dh}")
                except Exception:
                    continue
            return valid

        # Filter the pools
        filtered_120 = validate_pool(self.asset_pools["120x120"], 120, 120)
        filtered_40 = validate_pool(self.asset_pools["40x40"], 40, 40)

        # 3. The Spawn Assignment Phase (The Colophon)
        outer_40s = [s for s in self.sockets if "40x40" in s["tags"] and "outer" in s["tags"]]
        if not outer_40s:
            outer_corridors = [s for s in self.sockets if "corridor" in s["tags"] and "outer" in s["tags"]]
            spawn_socket = random.choice(outer_corridors)
        else:
            spawn_socket = random.choice(outer_40s)

        spawn_socket["active_plug"] = "maps/the_colophon.json"
        self.spawn_x = spawn_socket["bounds"]["x"] + (spawn_socket["bounds"]["width"] // 2)
        self.spawn_y = spawn_socket["bounds"]["y"] + (spawn_socket["bounds"]["height"] // 2)
        
        # 4. The Target Assignment Phase (Night Boss)
        inner_40s = [s for s in self.sockets if "40x40" in s["tags"] and "inner" in s["tags"]]
        if inner_40s:
            boss_socket = random.choice(inner_40s)
            boss_socket["active_plug"] = "maps/night_boss_arena.json"
        
        # 5. The Pool Backfill Pass
        from constants import POOL_SPECIAL_EDITION, POOL_MONTHLY_REPORT
        for s in self.sockets:
            if s["active_plug"] is None:
                is_large = s["bounds"]["width"] == 120
                pool = filtered_120 if is_large else filtered_40
                
                # 10% Anomaly Roll with Graceful Fallback
                if is_large and random.random() < 0.1:
                    if POOL_SPECIAL_EDITION:
                        s["active_plug"] = random.choice(POOL_SPECIAL_EDITION)
                    else:
                        # Fallback to standard pool if SE pool is empty
                        s["active_plug"] = random.choice(pool) if pool else "maps/smallcave.json"
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
        
        # Canvas Initialization: Use open floor space (" ")
        base_grid = [" " * self.total_size for _ in range(self.total_size)]
        
        data = {
            "map_id": self.world_id,
            "dimensions": {"width": self.total_size, "height": self.total_size},
            "legend": {"#": "WALL_STONE", " ": "FLOOR_CLEAN", ".": "FLOOR_CLEAN"},
            "grid": base_grid,
            "entities": {},
            "module_sockets": module_sockets,
            "spawn_coords": {"x": self.spawn_x, "y": self.spawn_y}
        }
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Generated world exported to {filename}")

if __name__ == "__main__":
    gen = WorldGenerator()
    gen.generate_layout()
    gen.export_world()
