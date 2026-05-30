"""
Macro-World Generator for Avoid Rain.
Generates a 440x440 grid of modules based on modular_system.md specifications.
"""
import os
import json
import random

class WorldGenerator:
    """Handles the data-driven generation of the macro-world layout."""
    def __init__(self, world_id="macro_generated"):
        self.world_id = world_id
        self.grid_size = 11  # 440 / 40 = 11 sockets per side
        self.socket_size = 40
        self.total_size = 440
        
        # Sockets are stored as a 2D grid of filenames
        self.sockets = [[None for _ in range(self.grid_size)] for _ in range(self.grid_size)]
        
        self.asset_pools = {
            "40x40": ["maps/forest.json", "maps/ruins.json", "maps/smallcave.json"]
        }

    def generate_layout(self):
        """Executes the allocation rule pipeline."""
        # 1. Identify Outer and Inner Sockets
        outer_sockets = []
        inner_sockets = []
        
        # Center is (5, 5) for an 11x11 grid (0-indexed)
        # Inner is roughly the central 200x200 space bounding the center
        # 200x200 / 40x40 = 5x5 area in the center.
        # So sockets from index 3 to 7 (5 sockets) are the 5x5 inner area.
        # But wait, 11x11 total.
        # 0 1 2 3 4 5 6 7 8 9 10
        # O O O O O O O O O O O (0)
        # O . . . . . . . . . O (1)
        # O . . . . . . . . . O (2)
        # O . . I I I I I . . O (3)
        # O . . I I I I I . . O (4)
        # O . . I I I I I . . O (5)
        # O . . I I I I I . . O (6)
        # O . . I I I I I . . O (7)
        # O . . . . . . . . . O (8)
        # O . . . . . . . . . O (9)
        # O O O O O O O O O O O (10)
        
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                if x == 0 or x == 10 or y == 0 or y == 10:
                    outer_sockets.append((x, y))
                elif 3 <= x <= 7 and 3 <= y <= 7:
                    inner_sockets.append((x, y))

        # 2. The Spawn Assignment Phase (The Colophon)
        spawn_pos = random.choice(outer_sockets)
        self.sockets[spawn_pos[1]][spawn_pos[0]] = "maps/the_colophon.json"
        
        # 3. The Target Assignment Phase (Night Boss)
        boss_pos = random.choice(inner_sockets)
        self.sockets[boss_pos[1]][boss_pos[0]] = "maps/night_boss.json"
        
        # 4. The Pool Backfill Pass
        available_assets = self.asset_pools["40x40"]
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                if self.sockets[y][x] is None:
                    self.sockets[y][x] = random.choice(available_assets)

    def export_world(self, filename="maps/generated_world.json"):
        """Exports the layout as a macro-world JSON file."""
        # A macro-world is basically a map file where module_sockets are defined
        # for every 40x40 cell.
        
        module_sockets = []
        for y in range(self.grid_size):
            for x in range(self.grid_size):
                module_sockets.append({
                    "name": f"socket_{x}_{y}",
                    "bounds": {
                        "x": x * self.socket_size,
                        "y": y * self.socket_size,
                        "width": self.socket_size,
                        "height": self.socket_size
                    },
                    "active_plug": self.sockets[y][x]
                })
        
        # Create an empty 440x440 grid (or just walls)
        # Since modules overlay, the base grid can be simple
        base_grid = ["#" * self.total_size for _ in range(self.total_size)]
        
        data = {
            "map_id": self.world_id,
            "dimensions": {"width": self.total_size, "height": self.total_size},
            "legend": {"#": "WALL_STONE"},
            "grid": base_grid,
            "entities": {},
            "module_sockets": module_sockets
        }
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Generated world exported to {filename}")

if __name__ == "__main__":
    gen = WorldGenerator()
    gen.generate_layout()
    gen.export_world()
