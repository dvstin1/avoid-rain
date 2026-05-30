"""
Macro-World Generator for Avoid Rain.
Generates a symmetric 440x440 grid of modules based on modular_system.md specifications.
Layout: 120 (Room) | 40 (Corridor) | 120 (Room) | 40 (Corridor) | 120 (Room)
"""
import os
import json
import random

class WorldGenerator:
    """Handles the data-driven generation of the macro-world layout."""
    def __init__(self, world_id="macro_generated"):
        self.world_id = world_id
        self.total_size = 440
        
        # Grid layout specification (width/height of each column/row)
        self.layout_steps = [120, 40, 120, 40, 120]
        
        # Sockets will be a list of dicts with bounds and tags
        self.sockets = []
        
        # Asset pools
        self.asset_pools = {
            "120x120": ["maps/forest.json", "maps/ruins.json"],
            "40x40": ["maps/smallcave.json"],
            "40x120": ["maps/smallcave.json"], # Placeholders
            "120x40": ["maps/smallcave.json"]  # Placeholders
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

        # 2. The Spawn Assignment Phase (The Colophon)
        # We need an outer 40x40 junction OR an outer corridor segment.
        # The user requested "randomly assign ... our colophon/night_boss files to their restricted 40x40 slots".
        # This implies we should prioritize the 40x40 junctions.
        # But wait, in a 5x5 grid with [120, 40, 120, 40, 120], junctions are all inner.
        # Let's check if there are any outer 40x40s.
        outer_40s = [s for s in self.sockets if "40x40" in s["tags"] and "outer" in s["tags"]]
        
        # If no outer 40x40s exist in 5x5, we must pick an outer corridor (40x120 or 120x40)
        if not outer_40s:
            outer_corridors = [s for s in self.sockets if "corridor" in s["tags"] and "outer" in s["tags"]]
            spawn_socket = random.choice(outer_corridors)
        else:
            spawn_socket = random.choice(outer_40s)

        spawn_socket["active_plug"] = "maps/the_colophon.json"
        # Store spawn position for the warp trigger
        self.spawn_x = spawn_socket["bounds"]["x"] + 20
        self.spawn_y = spawn_socket["bounds"]["y"] + 20
        
        # 3. The Target Assignment Phase (Night Boss)
        inner_40s = [s for s in self.sockets if "40x40" in s["tags"] and "inner" in s["tags"]]
        if inner_40s:
            boss_socket = random.choice(inner_40s)
            boss_socket["active_plug"] = "maps/night_boss.json"
        
        # 4. The Pool Backfill Pass
        for s in self.sockets:
            if s["active_plug"] is None:
                size_key = f"{s['bounds']['width']}x{s['bounds']['height']}"
                if size_key in self.asset_pools:
                    s["active_plug"] = random.choice(self.asset_pools[size_key])
                else:
                    # Fallback to standard 40x40 or nearest
                    s["active_plug"] = random.choice(self.asset_pools["40x40"])

    def export_world(self, filename="maps/generated_world.json"):
        """Exports the layout as a macro-world JSON file."""
        module_sockets = []
        for s in self.sockets:
            module_sockets.append({
                "name": s["id"],
                "bounds": s["bounds"],
                "active_plug": s["active_plug"]
            })
        
        base_grid = ["#" * self.total_size for _ in range(self.total_size)]
        
        data = {
            "map_id": self.world_id,
            "dimensions": {"width": self.total_size, "height": self.total_size},
            "legend": {"#": "WALL_STONE"},
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
