#!/usr/bin/env python3
"""Standalone offline procedural map generator for Avoid Rain.

Generates organic and architectural level maps using real procedural algorithms:
1. Organic Biomes (Swamp, Wilds, Windy Ridge, Pastoral Valley):
   - Cellular Automata smoothing combined with meandering Drunkard's Walk paths.
   - Irregular shorelines, islands, shallow ink puddle pockets, and organic clearings.
   - Smart edge-weighted foliage, thickets, and rock/clutter clustering.
2. Architectural Biomes (Ruins, Sanctuary, The Colophon, Tech Tower):
   - Multi-room layouts with chamfered 45-degree corners and recessed wall alcoves.
   - Symmetrical pillar rows, central focal altars/dais, and L-shaped/stepped corridors.
   - Smart perimeter placement for bookcases, benches, candelabras, and debris.
3. Playability Validation:
   - BFS flood-fill connectivity pass guaranteeing all walkable tiles and exits are reachable.
4. Visual Previews:
   - Color-coded minimap PNG generation saved directly to maps/previews/.
"""
# pylint: disable=too-many-lines,too-many-locals,too-many-arguments,too-many-branches
# pylint: disable=too-many-statements,too-many-instance-attributes,no-member,too-many-positional-arguments

import argparse
import json
import os
import random
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
import pygame

# ==============================================================================
# CONFIGURABLE CONSTANTS & SCHEMA REGISTRY
# ==============================================================================

DEFAULT_MAP_WIDTH = 40
DEFAULT_MAP_HEIGHT = 40
PREVIEW_TILE_SIZE = 8

# Output Directories
MAPS_DIR = "maps"
PREVIEWS_DIR = os.path.join(MAPS_DIR, "previews")

# Complete 28-Entry Symbol Registry & Descriptions (docs/visual_style_and_assets.md)
SYMBOL_WALL = '#'
SYMBOL_WALL_BORDER = 'X'
SYMBOL_FLOOR = '.'
SYMBOL_GRASS = 'g'
SYMBOL_THICKET = 'G'
SYMBOL_ALTAR = 'a'
SYMBOL_BARREL = 'B'
SYMBOL_BENCH = 'S'
SYMBOL_CLUTTER = 'K'
SYMBOL_STRUCTURE = 'T'
SYMBOL_BOOKCASE = 'h'
SYMBOL_INK_URN = 'd'
SYMBOL_INK_PUDDLE = 'v'
SYMBOL_CANDELABRA = 'l'
SYMBOL_LOTUS_FRAME = 'M'
SYMBOL_LORE = 'L'
SYMBOL_WELLSPRING = 'F'
SYMBOL_RESPITE = 'R'
SYMBOL_CHRONICLER = 'C'
SYMBOL_WARP = 'W'
SYMBOL_PLAYER = 'P'
SYMBOL_ENEMY_BAT = 'A'
SYMBOL_ENEMY_SLUG = 'Z'
SYMBOL_ENEMY_FLUTTER = 'f'
SYMBOL_ENEMY_BINDLING = 'b'
SYMBOL_ENEMY_SMEAR = 's'
SYMBOL_ENEMY_SENTRY = 'Y'
SYMBOL_MINIBOSS_M1 = 'E'
SYMBOL_MINIBOSS_M2 = '2'
SYMBOL_MINIBOSS_M3 = '3'
SYMBOL_FINAL_AUTHOR = '!'

MAP_LEGEND: Dict[str, str] = {
    SYMBOL_WALL: "Wall Tile",
    SYMBOL_WALL_BORDER: "Wall Boundary",
    SYMBOL_FLOOR: "Floor Tile",
    SYMBOL_GRASS: "Grass Floor",
    SYMBOL_THICKET: "Overgrown Thicket",
    SYMBOL_ALTAR: "Attunement Altar",
    SYMBOL_BARREL: "Barrel",
    SYMBOL_BENCH: "Bench",
    SYMBOL_CLUTTER: "Rock / Clutter",
    SYMBOL_STRUCTURE: "Structure",
    SYMBOL_BOOKCASE: "Bookcase",
    SYMBOL_INK_URN: "Ink Urn",
    SYMBOL_INK_PUDDLE: "Ink Puddle",
    SYMBOL_CANDELABRA: "Candelabra",
    SYMBOL_LOTUS_FRAME: "Lotus Frame",
    SYMBOL_LORE: "Lore",
    SYMBOL_WELLSPRING: "Wellspring",
    SYMBOL_RESPITE: "Respite",
    SYMBOL_CHRONICLER: "Chronicler",
    SYMBOL_WARP: "Warp Point",
    SYMBOL_PLAYER: "Player Start",
    SYMBOL_ENEMY_BAT: "Bat",
    SYMBOL_ENEMY_SLUG: "Slug",
    SYMBOL_ENEMY_FLUTTER: "Flutter",
    SYMBOL_ENEMY_BINDLING: "Bindling",
    SYMBOL_ENEMY_SMEAR: "Smear",
    SYMBOL_ENEMY_SENTRY: "Techno-Sentry",
    SYMBOL_MINIBOSS_M1: "Miniboss M1",
    SYMBOL_MINIBOSS_M2: "Miniboss M2",
    SYMBOL_MINIBOSS_M3: "Miniboss M3",
    SYMBOL_FINAL_AUTHOR: "The Final Author",
}

# Scriptorium Noir Minimap Preview Color Palette (RGB)
COLOR_PREVIEW_WALL = (32, 32, 40)
COLOR_PREVIEW_FLOOR = (52, 48, 46)
COLOR_PREVIEW_GRASS = (68, 88, 56)
COLOR_PREVIEW_THICKET = (38, 62, 38)
COLOR_PREVIEW_PUDDLE = (18, 28, 54)
COLOR_PREVIEW_PLAYER = (0, 245, 255)
COLOR_PREVIEW_WARP = (255, 205, 70)
COLOR_PREVIEW_RESPITE = (255, 185, 50)
COLOR_PREVIEW_ALTAR = (0, 230, 200)
COLOR_PREVIEW_WELLSPRING = (120, 210, 255)
COLOR_PREVIEW_CLUTTER = (125, 120, 115)
COLOR_PREVIEW_BARREL = (120, 85, 45)
COLOR_PREVIEW_BENCH = (140, 105, 75)
COLOR_PREVIEW_STRUCTURE = (95, 75, 60)
COLOR_PREVIEW_BOOKCASE = (90, 55, 38)
COLOR_PREVIEW_CANDELABRA = (255, 220, 90)
COLOR_PREVIEW_URN = (45, 55, 75)
COLOR_PREVIEW_LORE = (235, 230, 210)
COLOR_PREVIEW_ENEMY = (220, 48, 64)
COLOR_PREVIEW_MINIBOSS = (175, 75, 250)
COLOR_PREVIEW_CHRONICLER = (190, 160, 110)

SYMBOL_COLOR_MAP: Dict[str, Tuple[int, int, int]] = {
    SYMBOL_WALL: COLOR_PREVIEW_WALL,
    SYMBOL_WALL_BORDER: COLOR_PREVIEW_WALL,
    SYMBOL_FLOOR: COLOR_PREVIEW_FLOOR,
    SYMBOL_GRASS: COLOR_PREVIEW_GRASS,
    SYMBOL_THICKET: COLOR_PREVIEW_THICKET,
    SYMBOL_INK_PUDDLE: COLOR_PREVIEW_PUDDLE,
    SYMBOL_PLAYER: COLOR_PREVIEW_PLAYER,
    SYMBOL_WARP: COLOR_PREVIEW_WARP,
    SYMBOL_RESPITE: COLOR_PREVIEW_RESPITE,
    SYMBOL_ALTAR: COLOR_PREVIEW_ALTAR,
    SYMBOL_WELLSPRING: COLOR_PREVIEW_WELLSPRING,
    SYMBOL_CLUTTER: COLOR_PREVIEW_CLUTTER,
    SYMBOL_BARREL: COLOR_PREVIEW_BARREL,
    SYMBOL_BENCH: COLOR_PREVIEW_BENCH,
    SYMBOL_STRUCTURE: COLOR_PREVIEW_STRUCTURE,
    SYMBOL_BOOKCASE: COLOR_PREVIEW_BOOKCASE,
    SYMBOL_CANDELABRA: COLOR_PREVIEW_CANDELABRA,
    SYMBOL_INK_URN: COLOR_PREVIEW_URN,
    SYMBOL_LORE: COLOR_PREVIEW_LORE,
    SYMBOL_CHRONICLER: COLOR_PREVIEW_CHRONICLER,
    SYMBOL_LOTUS_FRAME: COLOR_PREVIEW_ALTAR,
    SYMBOL_ENEMY_BAT: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_SLUG: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_FLUTTER: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_BINDLING: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_SMEAR: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_SENTRY: COLOR_PREVIEW_ENEMY,
    SYMBOL_MINIBOSS_M1: COLOR_PREVIEW_MINIBOSS,
    SYMBOL_MINIBOSS_M2: COLOR_PREVIEW_MINIBOSS,
    SYMBOL_MINIBOSS_M3: COLOR_PREVIEW_MINIBOSS,
    SYMBOL_FINAL_AUTHOR: COLOR_PREVIEW_MINIBOSS,
}

# Biome Classification Sets
ORGANIC_BIOMES: Set[str] = {
    "swamp_mire", "swamp", "wilds", "windy_ridge", "pastoral_valley", "forest", "mire_causeway"
}
ARCHITECTURAL_BIOMES: Set[str] = {
    "ruins", "sanctuary", "the_colophon", "tech_tower", "chambers", "gantry_bridge", "crypt"
}

# Procedural Tuning Parameters
ORGANIC_CA_INIT_WALL_CHANCE = 0.45
ORGANIC_CA_STEPS = 4
ORGANIC_CA_BIRTH_LIMIT = 5
ORGANIC_CA_DEATH_LIMIT = 4

ARCH_MIN_ROOMS = 3
ARCH_MAX_ROOMS = 6
ARCH_MIN_ROOM_SIZE = 7
ARCH_MAX_ROOM_SIZE = 14
ARCH_CHAMFER_SIZE = 2
ARCH_PILLAR_INTERVAL = 3

# 2.5D Elevation Tiers & Shadow Casters
ELEVATION_PIT = -1
ELEVATION_LOWER = 0
ELEVATION_TERRACE = 1

SHADOW_CASTER_SYMBOLS: Set[str] = {
    SYMBOL_WALL,
    SYMBOL_WALL_BORDER,
    SYMBOL_STRUCTURE,
    SYMBOL_BOOKCASE,
    SYMBOL_BARREL,
    SYMBOL_CLUTTER,
    SYMBOL_BENCH,
    SYMBOL_INK_URN,
    SYMBOL_CANDELABRA,
}


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

class GeneratedMap:
    """Represents a procedurally generated level map conforming to the Avoid Rain schema."""

    def __init__(
        self,
        map_id: str,
        biome: str,
        width: int,
        height: int,
        grid: List[List[str]],
        entities: Optional[Dict[str, dict]] = None,
        module_sockets: Optional[list] = None,
        seed: Optional[int] = None,
        elevation_grid: Optional[List[List[int]]] = None,
        verticality_layers: Optional[dict] = None,
    ):
        self.map_id = map_id
        self.biome = biome
        self.width = width
        self.height = height
        self.grid = grid
        self.entities = entities or {}
        self.module_sockets = module_sockets or []
        self.seed = seed
        self.elevation_grid = elevation_grid or [
            [ELEVATION_LOWER for _ in range(width)] for _ in range(height)
        ]
        self.verticality_layers = verticality_layers or {}

    def to_dict(self) -> dict:
        """Serializes the map into the canonical Avoid Rain JSON schema dictionary."""
        return {
            "map_id": self.map_id,
            "biome": self.biome,
            "dimensions": {
                "width": self.width,
                "height": self.height,
            },
            "legend": MAP_LEGEND,
            "grid": ["".join(row) for row in self.grid],
            "entities": self.entities,
            "module_sockets": self.module_sockets,
            "elevation_grid": self.elevation_grid,
            "verticality_layers": self.verticality_layers,
        }

    def to_json(self, indent: int = 2) -> str:
        """Exports the map as a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_ascii_lines(self) -> str:
        """Exports the map grid as plain text ASCII rows."""
        return "\n".join("".join(row) for row in self.grid) + "\n"

    def save(self, filepath: str, file_format: str = "json", format_type: Optional[str] = None) -> str:
        """Writes the map file to disk in JSON or plain text format."""
        fmt = (format_type or file_format).lower()
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        content = self.to_ascii_lines() if fmt in ("txt", "ascii") else self.to_json()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath


# ==============================================================================
# CONNECTIVITY VALIDATION & BFS CARVING PASS
# ==============================================================================

def validate_and_carve_connectivity(
    grid: List[List[str]],
    rng: random.Random,
    mandatory_coords: Optional[List[Tuple[int, int]]] = None,
) -> bool:
    """BFS flood-fill pass that connects all isolated walkable chambers or fills dead pockets."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    if w == 0 or h == 0:
        return False

    def is_walkable(tile: str) -> bool:
        return tile not in (SYMBOL_WALL, SYMBOL_WALL_BORDER)

    # 1. Identify all connected components of walkable tiles
    visited: Set[Tuple[int, int]] = set()
    components: List[List[Tuple[int, int]]] = []

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if is_walkable(grid[y][x]) and (x, y) not in visited:
                comp: List[Tuple[int, int]] = []
                queue = deque([(x, y)])
                visited.add((x, y))

                while queue:
                    cx, cy = queue.popleft()
                    comp.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 1 <= nx < w - 1 and 1 <= ny < h - 1:
                            if is_walkable(grid[ny][nx]) and (nx, ny) not in visited:
                                visited.add((nx, ny))
                                queue.append((nx, ny))
                components.append(comp)

    if not components:
        return False

    # 2. Designate primary component (largest or containing mandatory coords)
    mandatory = mandatory_coords or []
    primary_idx = 0
    for idx, comp in enumerate(components):
        comp_set = set(comp)
        if any(pt in comp_set for pt in mandatory):
            primary_idx = idx
            break
    if primary_idx == 0:
        components.sort(key=len, reverse=True)
        primary_idx = 0

    main_comp = set(components[primary_idx])

    # 3. For all other components: carve connection or seal small dead ends
    for idx, comp in enumerate(components):
        if idx == primary_idx:
            continue

        comp_has_mandatory = any(pt in main_comp for pt in comp)
        if len(comp) < 12 and not comp_has_mandatory:
            # Small isolated pocket: seal into solid wall
            for cx, cy in comp:
                grid[cy][cx] = SYMBOL_WALL
        else:
            # Carve L-shaped or direct tunnel between nearest points
            best_pair = None
            min_dist = float("inf")
            sample_src = comp if len(comp) < 20 else rng.sample(comp, 20)
            sample_dst = list(main_comp) if len(main_comp) < 30 else rng.sample(list(main_comp), 30)

            for sx, sy in sample_src:
                for dx, dy in sample_dst:
                    dist = abs(sx - dx) + abs(sy - dy)
                    if dist < min_dist:
                        min_dist = dist
                        best_pair = ((sx, sy), (dx, dy))

            if best_pair:
                (x1, y1), (x2, y2) = best_pair
                # Carve horizontal then vertical
                cur_x, cur_y = x1, y1
                step_x = 1 if x2 >= x1 else -1
                step_y = 1 if y2 >= y1 else -1

                while cur_x != x2:
                    if 1 <= cur_x < w - 1 and 1 <= cur_y < h - 1:
                        if grid[cur_y][cur_x] in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                            grid[cur_y][cur_x] = SYMBOL_FLOOR
                    cur_x += step_x

                while cur_y != y2:
                    if 1 <= cur_x < w - 1 and 1 <= cur_y < h - 1:
                        if grid[cur_y][cur_x] in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                            grid[cur_y][cur_x] = SYMBOL_FLOOR
                    cur_y += step_y

                for pt in comp:
                    main_comp.add(pt)

    return True


# ==============================================================================
# ORGANIC BIOME GENERATOR (Cellular Automata + Drunkard's Walk)
# ==============================================================================

def generate_organic_biome(
    width: int = DEFAULT_MAP_WIDTH,
    height: int = DEFAULT_MAP_HEIGHT,
    biome: str = "swamp_mire",
    seed: Optional[int] = None,
    biome_name: Optional[str] = None,
) -> GeneratedMap:
    """Generates an organic natural map using Drunkard's Walk and Cellular Automata smoothing."""
    active_biome = biome_name if biome_name is not None else biome
    rng = random.Random(seed)
    grid = [[SYMBOL_WALL for _ in range(width)] for _ in range(height)]

    # 1. Meandering Drunkard's Walk paths (The Spine & Tributaries)
    start_x, start_y = width // 4, height // 2
    walkers = [
        {"x": start_x, "y": start_y, "steps": int(width * height * 0.18), "radius": 2},
        {"x": width // 2, "y": height // 3, "steps": int(width * height * 0.12), "radius": 1},
        {"x": width * 3 // 4, "y": height * 2 // 3, "steps": int(width * height * 0.12), "radius": 1},
    ]

    for w in walkers:
        cur_x, cur_y = w["x"], w["y"]
        steps = w["steps"]
        rad = w["radius"]

        for _ in range(steps):
            for dy in range(-rad, rad + 1):
                for dx in range(-rad, rad + 1):
                    tx, ty = cur_x + dx, cur_y + dy
                    if 2 <= tx < width - 2 and 2 <= ty < height - 2:
                        grid[ty][tx] = SYMBOL_FLOOR

            move = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)])
            cur_x = max(3, min(width - 4, cur_x + move[0]))
            cur_y = max(3, min(height - 4, cur_y + move[1]))

    # 2. Cellular Automata Noise Injection
    for y in range(2, height - 2):
        for x in range(2, width - 2):
            if grid[y][x] == SYMBOL_WALL and rng.random() > ORGANIC_CA_INIT_WALL_CHANCE:
                grid[y][x] = SYMBOL_FLOOR

    # 3. Cellular Automata Smoothing Passes
    for _ in range(ORGANIC_CA_STEPS):
        next_grid = [row[:] for row in grid]
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                wall_count = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if grid[y + dy][x + dx] in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                            wall_count += 1
                if grid[y][x] in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                    next_grid[y][x] = SYMBOL_WALL if wall_count >= ORGANIC_CA_DEATH_LIMIT else SYMBOL_FLOOR
                else:
                    next_grid[y][x] = SYMBOL_WALL if wall_count >= ORGANIC_CA_BIRTH_LIMIT else SYMBOL_FLOOR
        grid = next_grid

    # Enforce solid boundary frame
    for x in range(width):
        grid[0][x] = SYMBOL_WALL
        grid[height - 1][x] = SYMBOL_WALL
    for y in range(height):
        grid[y][0] = SYMBOL_WALL
        grid[y][width - 1] = SYMBOL_WALL

    # 4. Connectivity Pass
    validate_and_carve_connectivity(grid, rng)

    # 5. Natural Stratification: Grass, Thicket, Shallow Water/Puddles
    dist_map = _compute_wall_distances(grid)
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == SYMBOL_FLOOR:
                dist = dist_map[y][x]
                if dist == 1 and rng.random() < 0.45:
                    grid[y][x] = SYMBOL_GRASS
                elif dist == 2 and rng.random() < 0.25:
                    grid[y][x] = SYMBOL_GRASS if rng.random() < 0.7 else SYMBOL_THICKET
                elif dist >= 3 and rng.random() < 0.05:
                    grid[y][x] = SYMBOL_INK_PUDDLE  # Shallow swamp puddle pocket

    # 6. Smart Edge-Weighted Prop & Clutter Placement
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] in (SYMBOL_FLOOR, SYMBOL_GRASS):
                dist = dist_map[y][x]
                # High clutter near walls (dist 1-2), keep open clearing centers clear (dist >= 3)
                if dist == 1 and rng.random() < 0.12:
                    grid[y][x] = SYMBOL_CLUTTER
                elif dist == 2 and rng.random() < 0.06:
                    grid[y][x] = SYMBOL_BARREL if rng.random() < 0.4 else SYMBOL_CLUTTER
                elif dist >= 4 and rng.random() < 0.015:
                    grid[y][x] = SYMBOL_STRUCTURE  # Giant fungus or ancient hollow tree

    # 7. Strategic Landmark & Spawner Anchors
    open_floors = [(x, y) for y in range(2, height - 2) for x in range(2, width - 2) if grid[y][x] == SYMBOL_FLOOR]
    rng.shuffle(open_floors)

    entities: Dict[str, dict] = {}
    if open_floors:
        # Player start in safe clearing
        px, py = open_floors.pop()
        grid[py][px] = SYMBOL_PLAYER

        # Primary landmark altar or respite
        if open_floors:
            ax, ay = open_floors.pop()
            grid[ay][ax] = SYMBOL_ALTAR if "swamp" in active_biome else SYMBOL_RESPITE

        # Far warp portal
        if open_floors:
            wx, wy = open_floors.pop()
            grid[wy][wx] = SYMBOL_WARP
            entities[f"{wx},{wy}"] = {"target": "macro_world", "name": "Mire Extraction Gate"}

        # Lore manuscript fragment tucked away
        if open_floors:
            lx, ly = open_floors.pop()
            grid[ly][lx] = SYMBOL_LORE
            entities[f"{lx},{ly}"] = {"fragment_id": f"{active_biome}_chronicle", "name": "Weathered Parchment"}

        # Scatter themed organic enemies
        enemy_types = [SYMBOL_ENEMY_SLUG, SYMBOL_ENEMY_BAT, SYMBOL_ENEMY_FLUTTER, SYMBOL_ENEMY_SMEAR]
        num_enemies = max(3, (width * height) // 130)
        for _ in range(num_enemies):
            if open_floors:
                ex, ey = open_floors.pop()
                grid[ey][ex] = rng.choice(enemy_types)

    elevation_grid, stairs = build_elevation_grid(
        grid, terrace_center=(width // 2, height // 2), terrace_radius=max(4, min(width, height) // 6)
    )
    verticality_layers = apply_verticality_post_pass(grid, elevation_grid, stairs)

    map_id = f"{active_biome}_{seed or rng.randint(1000, 9999)}"
    return GeneratedMap(
        map_id,
        active_biome,
        width,
        height,
        grid,
        entities=entities,
        seed=seed,
        elevation_grid=elevation_grid,
        verticality_layers=verticality_layers,
    )


# ==============================================================================
# ARCHITECTURAL BIOME GENERATOR (Chamfered Chambers, Pillars, Alcoves)
# ==============================================================================

def generate_architectural_biome(
    width: int = DEFAULT_MAP_WIDTH,
    height: int = DEFAULT_MAP_HEIGHT,
    biome: str = "ruins",
    seed: Optional[int] = None,
    biome_name: Optional[str] = None,
) -> GeneratedMap:
    """Generates an architectural map with chamfered halls, alcoves, pillar rows, and altars."""
    active_biome = biome_name if biome_name is not None else biome
    rng = random.Random(seed)
    grid = [[SYMBOL_WALL for _ in range(width)] for _ in range(height)]
    entities: Dict[str, dict] = {}

    # 1. Multi-Room Partitioning
    num_rooms = rng.randint(ARCH_MIN_ROOMS, ARCH_MAX_ROOMS)
    rooms: List[dict] = []

    # Guaranteed central Great Sanctum
    center_w = rng.randint(10, 14)
    center_h = rng.randint(10, 14)
    center_x = (width - center_w) // 2
    center_y = (height - center_h) // 2
    rooms.append({"x": center_x, "y": center_y, "w": center_w, "h": center_h, "is_sanctum": True})

    # Peripheral wing rooms
    for _ in range(num_rooms - 1):
        rw = rng.randint(ARCH_MIN_ROOM_SIZE, ARCH_MAX_ROOM_SIZE)
        rh = rng.randint(ARCH_MIN_ROOM_SIZE, ARCH_MAX_ROOM_SIZE)
        rx = rng.randint(3, max(4, width - rw - 3))
        ry = rng.randint(3, max(4, height - rh - 3))

        # Check reasonable overlap/spacing
        overlaps = False
        for existing in rooms:
            if (
                rx < existing["x"] + existing["w"] + 2
                and rx + rw > existing["x"] - 2
                and ry < existing["y"] + existing["h"] + 2
                and ry + rh > existing["y"] - 2
            ):
                overlaps = True
                break
        if not overlaps or len(rooms) < 3:
            rooms.append({"x": rx, "y": ry, "w": rw, "h": rh, "is_sanctum": False})

    # 2. Carve Rooms with Chamfered (Beveled) 45-Degree Corners
    for r in rooms:
        rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
        chamfer = ARCH_CHAMFER_SIZE if min(rw, rh) >= 8 else 1

        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                if 1 <= x < width - 1 and 1 <= y < height - 1:
                    # Chamfer corners
                    is_corner = (
                        (x - rx + y - ry < chamfer)  # Top-left
                        or (rx + rw - 1 - x + y - ry < chamfer)  # Top-right
                        or (x - rx + ry + rh - 1 - y < chamfer)  # Bottom-left
                        or (rx + rw - 1 - x + ry + rh - 1 - y < chamfer)  # Bottom-right
                    )
                    if not is_corner:
                        grid[y][x] = SYMBOL_FLOOR

    # 3. Recessed Wall Alcoves
    for r in rooms:
        rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
        # Add 1-2 alcoves on outer room walls
        if rw >= 8:
            alcove_x = rx + rw // 2
            if ry - 1 > 1:
                grid[ry - 1][alcove_x] = SYMBOL_FLOOR  # North alcove
                grid[ry - 1][alcove_x + 1] = SYMBOL_FLOOR
            if ry + rh < height - 2:
                grid[ry + rh][alcove_x] = SYMBOL_FLOOR  # South alcove
                grid[ry + rh][alcove_x + 1] = SYMBOL_FLOOR

    # 4. Connect Rooms with Stepped & L-Shaped Corridors
    sanctum = rooms[0]
    for r in rooms[1:]:
        # Connect each wing to sanctum
        sx, sy = r["x"] + r["w"] // 2, r["y"] + r["h"] // 2
        tx, ty = sanctum["x"] + sanctum["w"] // 2, sanctum["y"] + sanctum["h"] // 2

        # 2-tile wide corridor
        cx, cy = sx, sy
        step_x = 1 if tx >= sx else -1
        step_y = 1 if ty >= sy else -1

        while cx != tx:
            for offset in (0, 1):
                if 1 <= cx < width - 1 and 1 <= cy + offset < height - 1:
                    grid[cy + offset][cx] = SYMBOL_FLOOR
            cx += step_x

        while cy != ty:
            for offset in (0, 1):
                if 1 <= cx + offset < width - 1 and 1 <= cy < height - 1:
                    grid[cy][cx + offset] = SYMBOL_FLOOR
            cy += step_y

    # 5. Symmetrical Pillar Rows in the Central Sanctum
    sw, sh = sanctum["w"], sanctum["h"]
    sx, sy = sanctum["x"], sanctum["y"]
    if sw >= 10 and sh >= 10:
        for py in range(sy + 3, sy + sh - 3, ARCH_PILLAR_INTERVAL):
            for px in (sx + 3, sx + sw - 4):
                if grid[py][px] == SYMBOL_FLOOR:
                    grid[py][px] = SYMBOL_WALL  # Stone column pillar

    # 6. Central Focal Dais & Altar
    cx, cy = sx + sw // 2, sy + sh // 2
    grid[cy][cx] = SYMBOL_ALTAR if "sanctuary" in active_biome else SYMBOL_RESPITE

    # Flanking candelabras or urns
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        if grid[cy + dy][cx + dx] == SYMBOL_FLOOR:
            grid[cy + dy][cx + dx] = SYMBOL_CANDELABRA if rng.random() < 0.6 else SYMBOL_INK_URN

    # 7. BFS Connectivity & Tunnel Validation
    validate_and_carve_connectivity(grid, rng, mandatory_coords=[(cx, cy)])

    # 8. Smart Architectural Dressing: Bookcases, Benches, Barrels, Rubble
    dist_map = _compute_wall_distances(grid)
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == SYMBOL_FLOOR and (x, y) != (cx, cy):
                dist = dist_map[y][x]
                if dist == 1:
                    # Flush against wall
                    n_wall = grid[y - 1][x] == SYMBOL_WALL
                    s_wall = grid[y + 1][x] == SYMBOL_WALL
                    if (n_wall or s_wall) and rng.random() < 0.08:
                        grid[y][x] = SYMBOL_BOOKCASE if rng.random() < 0.5 else SYMBOL_BENCH
                    elif rng.random() < 0.07:
                        grid[y][x] = SYMBOL_BARREL
                    elif rng.random() < 0.05:
                        grid[y][x] = SYMBOL_CLUTTER  # Crumbled masonry / rubble

    # 9. Spawners & Key Entrances
    open_floors = [(x, y) for y in range(2, height - 2) for x in range(2, width - 2) if grid[y][x] == SYMBOL_FLOOR]
    rng.shuffle(open_floors)

    # Player start in wing room
    if open_floors:
        px, py = open_floors.pop()
        grid[py][px] = SYMBOL_PLAYER

    # Warp portal
    if open_floors:
        wx, wy = open_floors.pop()
        grid[wy][wx] = SYMBOL_WARP
        entities[f"{wx},{wy}"] = {"target": "macro_world", "name": "Chamber Exit Warp"}

    # Wellspring or lore in an alcove
    if open_floors:
        fx, fy = open_floors.pop()
        grid[fy][fx] = SYMBOL_WELLSPRING if rng.random() < 0.5 else SYMBOL_LORE

    # Tactical enemies: Sentries at corridors, Bindlings & Bats in wings, Miniboss in sanctum
    if open_floors:
        # Miniboss M1 near sanctum perimeter
        mx, my = open_floors.pop()
        grid[my][mx] = SYMBOL_MINIBOSS_M1

    arch_enemies = [SYMBOL_ENEMY_SENTRY, SYMBOL_ENEMY_BINDLING, SYMBOL_ENEMY_BAT, SYMBOL_ENEMY_SLUG]
    num_enemies = max(3, (width * height) // 140)
    for _ in range(num_enemies):
        if open_floors:
            ex, ey = open_floors.pop()
            grid[ey][ex] = rng.choice(arch_enemies)

    # Enforce solid boundary frame
    for x in range(width):
        grid[0][x] = SYMBOL_WALL
        grid[height - 1][x] = SYMBOL_WALL
    for y in range(height):
        grid[y][0] = SYMBOL_WALL
        grid[y][width - 1] = SYMBOL_WALL

    elevation_grid, stairs = build_elevation_grid(
        grid, terrace_rect=(sx, sy, sw, sh)
    )
    verticality_layers = apply_verticality_post_pass(grid, elevation_grid, stairs)

    map_id = f"{active_biome}_{seed or rng.randint(1000, 9999)}"
    return GeneratedMap(
        map_id,
        active_biome,
        width,
        height,
        grid,
        entities=entities,
        seed=seed,
        elevation_grid=elevation_grid,
        verticality_layers=verticality_layers,
    )


# ==============================================================================
# UTILITIES: WALL DISTANCES & VISUAL PREVIEW RENDERING
# ==============================================================================

def _compute_wall_distances(grid: List[List[str]]) -> List[List[int]]:
    """Calculates Manhattan distance from every floor tile to the nearest wall."""
    h = len(grid)
    w = len(grid[0])
    dist = [[999 for _ in range(w)] for _ in range(h)]
    queue: deque = deque()

    for y in range(h):
        for x in range(w):
            if grid[y][x] in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                dist[y][x] = 0
                queue.append((x, y))

    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h:
                if dist[ny][nx] > dist[cy][cx] + 1:
                    dist[ny][nx] = dist[cy][cx] + 1
                    queue.append((nx, ny))
    return dist


def find_spawn_point(grid: List[List[str]], symbol: str = SYMBOL_PLAYER) -> Optional[Tuple[int, int]]:
    """Returns the (x, y) coordinates of the first occurrence of symbol in grid, or None."""
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell == symbol:
                return (x, y)
    return None


def _is_walkable_tile(tile: str) -> bool:
    """Returns True if tile is not a solid wall."""
    return tile not in (SYMBOL_WALL, SYMBOL_WALL_BORDER)


def build_elevation_grid(
    grid: List[List[str]],
    terrace_center: Optional[Tuple[int, int]] = None,
    terrace_radius: int = 5,
    terrace_rect: Optional[Tuple[int, int, int, int]] = None,
) -> Tuple[List[List[int]], List[List[int]]]:
    """Builds elevation tier grid (Pit=-1, Lower=0, Terrace=1) and connecting staircase coordinates."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    elev = [[ELEVATION_LOWER for _ in range(w)] for _ in range(h)]

    # 1. Assign Pit/Abyss (-1) to deep outer wall void with no nearby walkable floor
    for y in range(h):
        for x in range(w):
            if not _is_walkable_tile(grid[y][x]):
                has_walkable_neighbor = False
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and _is_walkable_tile(grid[ny][nx]):
                            has_walkable_neighbor = True
                            break
                    if has_walkable_neighbor:
                        break
                if not has_walkable_neighbor:
                    elev[y][x] = ELEVATION_PIT

    # 2. Assign Raised Terrace (1) for focal sanctum rect or dry organic plateau
    if terrace_rect is not None:
        rx, ry, rw, rh = terrace_rect
        for y in range(max(1, ry), min(h - 1, ry + rh)):
            for x in range(max(1, rx), min(w - 1, rx + rw)):
                if _is_walkable_tile(grid[y][x]) and grid[y][x] != SYMBOL_INK_PUDDLE:
                    elev[y][x] = ELEVATION_TERRACE
    elif terrace_center is not None:
        cx, cy = terrace_center
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if _is_walkable_tile(grid[y][x]) and grid[y][x] != SYMBOL_INK_PUDDLE:
                    if abs(x - cx) + abs(y - cy) <= terrace_radius:
                        elev[y][x] = ELEVATION_TERRACE

    # 3. Place staircase connections where Terrace (1) meets Lower (0) on walkable approaches
    stairs: List[List[int]] = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if elev[y][x] == ELEVATION_TERRACE and _is_walkable_tile(grid[y][x]):
                borders_lower = any(
                    _is_walkable_tile(grid[y + dy][x + dx]) and elev[y + dy][x + dx] == ELEVATION_LOWER
                    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
                )
                # Keep staircase placement along cardinal axes or threshold edges
                if borders_lower and (x % 3 == 0 or y % 3 == 0):
                    stairs.append([x, y])

    # Ensure at least one staircase exists if any terrace borders lower floor
    if not stairs:
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if elev[y][x] == ELEVATION_TERRACE and _is_walkable_tile(grid[y][x]):
                    if any(
                        _is_walkable_tile(grid[y + dy][x + dx]) and elev[y + dy][x + dx] == ELEVATION_LOWER
                        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
                    ):
                        stairs.append([x, y])
                        break
            if stairs:
                break

    return elev, stairs


def apply_verticality_post_pass(
    grid: List[List[str]],
    elevation_grid: List[List[int]],
    stairs_coords: Optional[List[List[int]]] = None,
) -> dict:
    """Auto-shading and auto-facing post-pass for 2.5D verticality layers."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    stair_set = {(sx, sy) for sx, sy in (stairs_coords or [])}

    wall_front_faces: List[List[int]] = []
    wall_top_caps: List[List[int]] = []
    shadows_south: List[List[int]] = []
    shadows_east: List[List[int]] = []
    shadows_corner: List[List[int]] = []
    cliff_edges: List[List[int]] = []
    pit_rims: List[List[int]] = []

    for y in range(h):
        for x in range(w):
            tile = grid[y][x]
            elev = elevation_grid[y][x]

            # 1. Wall Front Faces vs Top Caps
            if tile in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                south_walkable = (
                    y + 1 < h
                    and _is_walkable_tile(grid[y + 1][x])
                    and elevation_grid[y + 1][x] != ELEVATION_PIT
                )
                if south_walkable:
                    wall_front_faces.append([x, y])
                else:
                    wall_top_caps.append([x, y])

            # 2. Chasm / Pit Rims
            if elev == ELEVATION_PIT:
                borders_solid = any(
                    0 <= x + dx < w and 0 <= y + dy < h and elevation_grid[y + dy][x + dx] != ELEVATION_PIT
                    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0))
                )
                if borders_solid:
                    pit_rims.append([x, y])
                continue

            # 3. Walkable Floor Drop-Shadow Overlays & Cliff Ledges
            if _is_walkable_tile(tile):
                north_casts = (
                    (y > 0 and grid[y - 1][x] in SHADOW_CASTER_SYMBOLS)
                    or (y > 0 and elevation_grid[y - 1][x] > elev)
                )
                west_casts = (
                    (x > 0 and grid[y][x - 1] in SHADOW_CASTER_SYMBOLS)
                    or (x > 0 and elevation_grid[y][x - 1] > elev)
                )
                nw_casts = (
                    x > 0 and y > 0 and grid[y - 1][x - 1] in SHADOW_CASTER_SYMBOLS
                )

                if north_casts:
                    shadows_south.append([x, y])
                if west_casts:
                    shadows_east.append([x, y])
                if nw_casts and not north_casts and not west_casts:
                    shadows_corner.append([x, y])

                # Cliff ledge on south drop-off from Terrace -> Lower without stairs
                if (
                    elev == ELEVATION_TERRACE
                    and (x, y) not in stair_set
                    and y + 1 < h
                    and _is_walkable_tile(grid[y + 1][x])
                    and elevation_grid[y + 1][x] < elev
                ):
                    cliff_edges.append([x, y])

    return {
        "wall_faces": {
            "front_face": wall_front_faces,
            "top_cap": wall_top_caps,
        },
        "floor_shadows": {
            "south": shadows_south,
            "east": shadows_east,
            "corner": shadows_corner,
        },
        "cliff_edges": cliff_edges,
        "stairs": stairs_coords or [],
        "pit_rims": pit_rims,
    }


def render_map_preview(
    gen_map: GeneratedMap,
    output_path: Optional[str] = None,
    scale: int = PREVIEW_TILE_SIZE,
) -> str:
    """Renders a 2.5D verticality-aware color-coded minimap PNG preview of the generated map."""
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()

    w_px = gen_map.width * scale
    h_px = gen_map.height * scale
    surf = pygame.Surface((w_px, h_px))
    surf.fill((8, 8, 13))

    v_layers = gen_map.verticality_layers or apply_verticality_post_pass(
        gen_map.grid, gen_map.elevation_grid
    )
    front_faces = {tuple(pt) for pt in v_layers.get("wall_faces", {}).get("front_face", [])}
    south_shadows = {tuple(pt) for pt in v_layers.get("floor_shadows", {}).get("south", [])}
    east_shadows = {tuple(pt) for pt in v_layers.get("floor_shadows", {}).get("east", [])}
    corner_shadows = {tuple(pt) for pt in v_layers.get("floor_shadows", {}).get("corner", [])}
    cliff_edges = {tuple(pt) for pt in v_layers.get("cliff_edges", [])}
    stair_coords = {tuple(pt) for pt in v_layers.get("stairs", [])}
    pit_rims = {tuple(pt) for pt in v_layers.get("pit_rims", [])}

    for y in range(gen_map.height):
        for x in range(gen_map.width):
            tile = gen_map.grid[y][x]
            elev = gen_map.elevation_grid[y][x] if y < len(gen_map.elevation_grid) else ELEVATION_LOWER
            rect = pygame.Rect(x * scale, y * scale, scale, scale)

            if elev == ELEVATION_PIT:
                pygame.draw.rect(surf, (8, 8, 13), rect)
                if (x, y) in pit_rims:
                    pygame.draw.line(surf, (58, 56, 66), (rect.left, rect.top), (rect.right - 1, rect.top), 1)
                continue

            if tile in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                if (x, y) in front_faces:
                    pygame.draw.rect(surf, (24, 27, 36), rect)
                    pygame.draw.line(
                        surf, (46, 52, 66), (rect.left, rect.top), (rect.right - 1, rect.top), 1
                    )
                else:
                    pygame.draw.rect(surf, (58, 64, 78), rect)
                continue

            col = SYMBOL_COLOR_MAP.get(tile, COLOR_PREVIEW_FLOOR)
            if elev == ELEVATION_TERRACE and tile == SYMBOL_FLOOR:
                col = (min(255, col[0] + 18), min(255, col[1] + 16), min(255, col[2] + 16))
            pygame.draw.rect(surf, col, rect)

            if (x, y) in cliff_edges:
                pygame.draw.line(
                    surf, (112, 106, 98), (rect.left, rect.bottom - 2), (rect.right - 1, rect.bottom - 2), 1
                )
                pygame.draw.line(
                    surf, (16, 16, 22), (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1), 1
                )
            elif (x, y) in stair_coords:
                for step_y in range(1, scale, 2):
                    pygame.draw.line(
                        surf, (140, 134, 124), (rect.left + 1, rect.top + step_y), (rect.right - 2, rect.top + step_y)
                    )

            # Composite floor drop-shadows
            if (x, y) in south_shadows:
                sh_s = pygame.Surface((scale, max(2, scale // 2)), pygame.SRCALPHA)
                sh_s.fill((6, 7, 12, 115))
                surf.blit(sh_s, (rect.left, rect.top))
            if (x, y) in east_shadows:
                sh_e = pygame.Surface((max(2, scale // 2), scale), pygame.SRCALPHA)
                sh_e.fill((6, 7, 12, 95))
                surf.blit(sh_e, (rect.left, rect.top))
            if (x, y) in corner_shadows:
                sh_c = pygame.Surface((max(2, scale // 2), max(2, scale // 2)), pygame.SRCALPHA)
                sh_c.fill((6, 7, 12, 95))
                surf.blit(sh_c, (rect.left, rect.top))

            # Highlight landmark and player tiles with crisp inner accents
            if tile in (SYMBOL_PLAYER, SYMBOL_WARP, SYMBOL_RESPITE, SYMBOL_ALTAR, SYMBOL_MINIBOSS_M1):
                pygame.draw.rect(surf, (255, 255, 255), rect, 1)

    if not output_path:
        os.makedirs(PREVIEWS_DIR, exist_ok=True)
        output_path = os.path.join(PREVIEWS_DIR, f"{gen_map.map_id}_preview.png")
    else:
        dir_name = os.path.dirname(output_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    pygame.image.save(surf, output_path)
    return output_path


# ==============================================================================
# MAIN GENERATOR DISPATCHER & CLI
# ==============================================================================

def generate_map(
    biome: str = "swamp_mire",
    width: int = DEFAULT_MAP_WIDTH,
    height: int = DEFAULT_MAP_HEIGHT,
    seed: Optional[int] = None,
) -> GeneratedMap:
    """Dispatches to organic or architectural level generators based on biome classification."""
    normalized_biome = biome.lower().strip()
    is_organic = (
        normalized_biome in ORGANIC_BIOMES
        or any(term in normalized_biome for term in ("swamp", "wild", "pastor", "ridge"))
    )
    if is_organic:
        return generate_organic_biome(width, height, normalized_biome, seed)
    return generate_architectural_biome(width, height, normalized_biome, seed)


# Convenient alias
generate_procedural_map = generate_map


def parse_arguments() -> argparse.Namespace:
    """Configures and parses CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Procedural offline map generator for Avoid Rain (Organic & Architectural algorithms)."
    )
    parser.add_argument(
        "--biome",
        type=str,
        default="swamp_mire",
        help="Target biome theme (e.g. swamp_mire, ruins, sanctuary, the_colophon, windy_ridge, pastoral_valley).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Integer RNG seed for deterministic reproduction.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_MAP_WIDTH,
        help="Map grid width in tiles (default: 40).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_MAP_HEIGHT,
        help="Map grid height in tiles (default: 40).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Target filepath to save map (e.g. maps/custom_room.json). Inferred from biome and seed if omitted.",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "txt"],
        default="json",
        help="Map serialization format: 'json' schema (default) or 'txt' text file.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Render a color-coded minimap PNG preview into maps/previews/.",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=1,
        help="Number of distinct procedural maps to generate.",
    )
    parser.add_argument(
        "--list-biomes",
        action="store_true",
        help="List available biomes and their procedural generation classification.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry point for procedural map generation."""
    args = parse_arguments()

    if args.list_biomes:
        print("Avoid Rain - Procedural Biome Classifications:")
        print("  Organic Algorithms (Cellular Automata + Drunkard's Walk):")
        for b in sorted(ORGANIC_BIOMES):
            print(f"    - {b}")
        print("  Architectural Algorithms (Chamfered Chambers + Pillars + Alcoves):")
        for b in sorted(ARCHITECTURAL_BIOMES):
            print(f"    - {b}")
        return

    base_seed = args.seed if args.seed is not None else random.randint(1000, 99999)

    print("==================================================")
    print(" Avoid Rain - Procedural Map Generator")
    print("==================================================")
    print(f"Biome:      {args.biome}")
    print(f"Dimensions: {args.width}x{args.height} tiles")
    print(f"Base Seed:  {base_seed}")
    print(f"Batch Count:{args.batch}")

    for i in range(args.batch):
        current_seed = base_seed + i
        gen_map = generate_map(
            biome=args.biome,
            width=args.width,
            height=args.height,
            seed=current_seed,
        )

        out_path = args.output
        if not out_path or args.batch > 1:
            ext = args.format
            out_path = os.path.join(MAPS_DIR, f"{gen_map.map_id}.{ext}")

        saved_path = gen_map.save(out_path, file_format=args.format)
        print(f"  [+] Map Generated -> {saved_path} ({gen_map.width}x{gen_map.height})")

        if args.preview:
            preview_filename = f"{gen_map.map_id}_preview.png"
            preview_path = os.path.join(PREVIEWS_DIR, preview_filename)
            render_map_preview(gen_map, preview_path)
            print(f"      Preview Saved -> {preview_path}")

    print("Generation complete.")


if __name__ == "__main__":
    main()
