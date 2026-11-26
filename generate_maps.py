#!/usr/bin/env python3
# copyright 2026 Dustin Massop, License: GPLv2
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

from constants import (
    BENCH_VERTICAL_FACINGS,
    SEGMENT_MINIBOSS_MIN_DIM,
    get_bench_footprint_tiles,
    normalize_bench_facing,
)

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
SYMBOL_BARREL = 'B'
SYMBOL_BENCH = 'S'
SYMBOL_CLUTTER = 'K'
SYMBOL_STRUCTURE = 'T'
SYMBOL_BOOKCASE = 'h'
SYMBOL_INK_URN = 'd'
SYMBOL_INK_PUDDLE = 'v'
SYMBOL_CANDELABRA = 'l'
SYMBOL_FIRE_CHALICE = 'V'
SYMBOL_LOTUS_FRAME = 'M'
SYMBOL_LORE = 'L'
SYMBOL_WELLSPRING = 'F'
SYMBOL_RESPITE = 'R'
SYMBOL_CHRONICLER = 'C'
SYMBOL_BINDER = '&'
SYMBOL_WARP = 'W'
SYMBOL_PLAYER = 'P'
SYMBOL_ENEMY_BAT = 'A'
SYMBOL_ENEMY_SLUG = 'Z'
SYMBOL_ENEMY_FLUTTER = 'f'
SYMBOL_ENEMY_BINDLING = 'b'
SYMBOL_ENEMY_SMEAR = 's'
SYMBOL_ENEMY_SENTRY = 'Y'
SYMBOL_ENEMY_WOLF = 'w'
SYMBOL_MINIBOSS_M1 = 'E'
SYMBOL_MINIBOSS_M2 = '2'
SYMBOL_MINIBOSS_M3 = '3'
SYMBOL_FINAL_AUTHOR = '!'
SYMBOL_PATROL_WAYPOINTS: Tuple[str, ...] = ('1', '2', '3', '4')

MAP_LEGEND: Dict[str, str] = {
    SYMBOL_WALL: "Wall Tile",
    SYMBOL_WALL_BORDER: "Wall Boundary",
    SYMBOL_FLOOR: "Floor Tile",
    SYMBOL_GRASS: "Grass Floor",
    SYMBOL_THICKET: "Overgrown Thicket",
    SYMBOL_BARREL: "Barrel",
    SYMBOL_BENCH: "Bench",
    SYMBOL_CLUTTER: "Rock / Clutter",
    SYMBOL_STRUCTURE: "Structure",
    SYMBOL_BOOKCASE: "Bookcase",
    SYMBOL_INK_URN: "Ink Urn",
    SYMBOL_INK_PUDDLE: "Ink Puddle",
    SYMBOL_CANDELABRA: "Candelabra",
    SYMBOL_FIRE_CHALICE: "Fire Chalice",
    SYMBOL_LOTUS_FRAME: "Lotus Frame",
    SYMBOL_LORE: "Lore",
    SYMBOL_WELLSPRING: "Wellspring",
    SYMBOL_RESPITE: "Respite",
    SYMBOL_CHRONICLER: "Chronicler",
    SYMBOL_BINDER: "The Binder",
    SYMBOL_WARP: "Warp Point",
    SYMBOL_PLAYER: "Player Start",
    "1": "Patrol Marker 1",
    "4": "Patrol Marker 4",
    SYMBOL_ENEMY_BAT: "Bat",
    SYMBOL_ENEMY_SLUG: "Slug",
    SYMBOL_ENEMY_FLUTTER: "Flutter",
    SYMBOL_ENEMY_BINDLING: "Bindling",
    SYMBOL_ENEMY_SMEAR: "Smear",
    SYMBOL_ENEMY_SENTRY: "Techno-Sentry",
    SYMBOL_ENEMY_WOLF: "Punctuation Wolf",
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
COLOR_PREVIEW_LOTUS = (0, 230, 200)
COLOR_PREVIEW_WELLSPRING = (120, 210, 255)
COLOR_PREVIEW_CLUTTER = (125, 120, 115)
COLOR_PREVIEW_BARREL = (120, 85, 45)
COLOR_PREVIEW_BENCH = (140, 105, 75)
COLOR_PREVIEW_STRUCTURE = (95, 75, 60)
COLOR_PREVIEW_BOOKCASE = (90, 55, 38)
COLOR_PREVIEW_CANDELABRA = (255, 220, 90)
COLOR_PREVIEW_FIRE_CHALICE = (255, 132, 36)
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
    SYMBOL_WELLSPRING: COLOR_PREVIEW_WELLSPRING,
    SYMBOL_CLUTTER: COLOR_PREVIEW_CLUTTER,
    SYMBOL_BARREL: COLOR_PREVIEW_BARREL,
    SYMBOL_BENCH: COLOR_PREVIEW_BENCH,
    SYMBOL_STRUCTURE: COLOR_PREVIEW_STRUCTURE,
    SYMBOL_BOOKCASE: COLOR_PREVIEW_BOOKCASE,
    SYMBOL_CANDELABRA: COLOR_PREVIEW_CANDELABRA,
    SYMBOL_FIRE_CHALICE: COLOR_PREVIEW_FIRE_CHALICE,
    SYMBOL_INK_URN: COLOR_PREVIEW_URN,
    SYMBOL_LORE: COLOR_PREVIEW_LORE,
    SYMBOL_CHRONICLER: COLOR_PREVIEW_CHRONICLER,
    SYMBOL_LOTUS_FRAME: COLOR_PREVIEW_LOTUS,
    SYMBOL_ENEMY_BAT: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_SLUG: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_FLUTTER: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_BINDLING: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_SMEAR: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_SENTRY: COLOR_PREVIEW_ENEMY,
    SYMBOL_ENEMY_WOLF: COLOR_PREVIEW_ENEMY,
    SYMBOL_MINIBOSS_M1: COLOR_PREVIEW_MINIBOSS,
    SYMBOL_MINIBOSS_M2: COLOR_PREVIEW_MINIBOSS,
    SYMBOL_MINIBOSS_M3: COLOR_PREVIEW_MINIBOSS,
    SYMBOL_FINAL_AUTHOR: COLOR_PREVIEW_MINIBOSS,
}

# Biome Classification Sets
ORGANIC_BIOMES: Set[str] = {
    "swamp_mire", "swamp", "wilds", "windy_ridge", "pastoral_valley",
    "forest", "frozen_peaks", "vitreous_basin",
}
ARCHITECTURAL_BIOMES: Set[str] = {
    "ruins", "sanctuary", "the_colophon", "tech_tower", "chambers", "crypt",
    "sunlit_aqueducts",
}
ACTIVE_WORLD_BIOMES: Tuple[str, ...] = (
    "windy_ridge",
    "pastoral_valley",
    "swamp_mire",
    "frozen_peaks",
    "tech_tower",
    "vitreous_basin",
    "sunlit_aqueducts",
)
SEGMENTS_DIR = os.path.join(MAPS_DIR, "segments")
DEFAULT_SEGMENTS_PER_BIOME = 4
CONNECTOR_HALF_WIDTH = 3

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

# Solid Prop Collision & Hallway Clearance Constants (Section 13)
SOLID_PROP_SYMBOLS: Tuple[str, ...] = (
    SYMBOL_BOOKCASE,
    SYMBOL_BENCH,
    SYMBOL_BARREL,
    SYMBOL_STRUCTURE,
    SYMBOL_INK_URN,
    SYMBOL_CANDELABRA,
    SYMBOL_FIRE_CHALICE,
)
WIDE_SOLID_PROP_SYMBOLS: Tuple[str, ...] = (SYMBOL_BOOKCASE, SYMBOL_BENCH)
LARGE_SOLID_PROP_SYMBOLS: Tuple[str, ...] = (SYMBOL_FIRE_CHALICE,)
HALLWAY_MIN_CLEAR_SPAN = 3
BOOKCASE_MIN_HORIZ_SPAN = 4
PROP_LOCAL_WINDOW_RADIUS = 2
RESPITE_WIDE_PROP_CLEARANCE = 1

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
    SYMBOL_FIRE_CHALICE,
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
        zones: Optional[Dict[str, list]] = None,
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
        self.zones = zones

    def to_dict(self) -> dict:
        """Serializes the map into the canonical Avoid Rain JSON schema dictionary."""
        payload = {
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
        if self.zones is not None:
            payload["zones"] = self.zones
        return payload

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
    mandatory_set = set(mandatory)
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

        comp_has_mandatory = any(pt in mandatory_set for pt in comp)
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


def _get_bench_facing(entities: Optional[Dict[str, dict]], x: int, y: int) -> str:
    """Return normalized bench facing for grid cell (x, y) from optional entities metadata."""
    if not entities:
        return "south"
    meta = entities.get(f"{x},{y}")
    return normalize_bench_facing(meta.get("facing") if isinstance(meta, dict) else None)


def _get_wide_prop_cells(
    ch: str,
    x: int,
    y: int,
    entities: Optional[Dict[str, dict]] = None,
) -> Tuple[Tuple[int, int], ...]:
    """Return all occupied grid cells for a prop symbol anchored at (x, y)."""
    if ch == SYMBOL_BENCH:
        return get_bench_footprint_tiles(x, y, _get_bench_facing(entities, x, y))
    if ch in WIDE_SOLID_PROP_SYMBOLS:
        return ((x, y), (x + 1, y))
    if ch in LARGE_SOLID_PROP_SYMBOLS:
        return ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1))
    return ((x, y),)


def _get_solid_prop_footprint(
    grid: List[List[str]],
    entities: Optional[Dict[str, dict]] = None,
) -> Tuple[Set[Tuple[int, int]], Dict[Tuple[int, int], Tuple[int, int]]]:
    """Compute impassable wall + solid-prop tiles (incl. 2x1, 1x2 vertical benches, and 2x2) and owners."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    impassable: Set[Tuple[int, int]] = set()
    prop_owners: Dict[Tuple[int, int], Tuple[int, int]] = {}
    solid_props = set(SOLID_PROP_SYMBOLS)

    for y in range(h):
        for x in range(w):
            cell = grid[y][x]
            if cell in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                impassable.add((x, y))
            elif cell in solid_props:
                for nx_p, ny_p in _get_wide_prop_cells(cell, x, y, entities):
                    if 0 <= nx_p < w and 0 <= ny_p < h:
                        impassable.add((nx_p, ny_p))
                        if (nx_p, ny_p) == (x, y) or grid[ny_p][nx_p] not in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                            prop_owners[(nx_p, ny_p)] = (x, y)
    return impassable, prop_owners


def _can_place_architectural_prop(
    grid: List[List[str]],
    candidate_cells: List[Tuple[int, int]],
    occupied_solid: Set[Tuple[int, int]],
) -> bool:
    """Return True if placing a solid prop preserves hallway width and local walkable connectivity."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    cand_set = set(candidate_cells)
    is_horiz_multi = len(candidate_cells) > 1 and any(c[0] != candidate_cells[0][0] for c in candidate_cells)
    is_vert_multi = len(candidate_cells) > 1 and any(c[1] != candidate_cells[0][1] for c in candidate_cells)
    min_horiz = BOOKCASE_MIN_HORIZ_SPAN if is_horiz_multi else HALLWAY_MIN_CLEAR_SPAN
    min_vert = BOOKCASE_MIN_HORIZ_SPAN if is_vert_multi else HALLWAY_MIN_CLEAR_SPAN

    def is_open(tx: int, ty: int) -> bool:
        if not (1 <= tx < w - 1 and 1 <= ty < h - 1):
            return False
        if grid[ty][tx] in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
            return False
        if (tx, ty) in occupied_solid:
            return False
        return True

    # 1. Span clearance guard: reject narrow hallways, 1-2 tile corridors, and tight doorway mouths
    for cx, cy in candidate_cells:
        if not is_open(cx, cy):
            return False
        left = 0
        while left < 6 and is_open(cx - left - 1, cy):
            left += 1
        right = 0
        while right < 6 and is_open(cx + right + 1, cy):
            right += 1
        horiz_span = 1 + left + right

        up = 0
        while up < 6 and is_open(cx, cy - up - 1):
            up += 1
        down = 0
        while down < 6 and is_open(cx, cy + down + 1):
            down += 1
        vert_span = 1 + up + down

        if horiz_span < min_horiz or vert_span < min_vert:
            return False

    # 2. Local articulation check: all 4-adjacent walkable neighbors must stay connected in a 5x5 window
    min_x = max(1, min(cx for cx, _ in candidate_cells) - PROP_LOCAL_WINDOW_RADIUS)
    max_x = min(w - 2, max(cx for cx, _ in candidate_cells) + PROP_LOCAL_WINDOW_RADIUS)
    min_y = max(1, min(cy for _, cy in candidate_cells) - PROP_LOCAL_WINDOW_RADIUS)
    max_y = min(h - 2, max(cy for _, cy in candidate_cells) + PROP_LOCAL_WINDOW_RADIUS)

    neighbors: List[Tuple[int, int]] = []
    for cx, cy in candidate_cells:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if (nx, ny) not in cand_set and is_open(nx, ny) and (nx, ny) not in neighbors:
                neighbors.append((nx, ny))

    if len(neighbors) <= 1:
        return True

    visited = {neighbors[0]}
    queue = deque([neighbors[0]])
    while queue:
        qx, qy = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = qx + dx, qy + dy
            if (
                min_x <= nx <= max_x
                and min_y <= ny <= max_y
                and (nx, ny) not in cand_set
                and (nx, ny) not in visited
                and is_open(nx, ny)
            ):
                visited.add((nx, ny))
                queue.append((nx, ny))

    return all(nb in visited for nb in neighbors)


def _has_respite_clearance(
    grid: List[List[str]],
    candidate_cells: List[Tuple[int, int]],
    clearance: int = RESPITE_WIDE_PROP_CLEARANCE,
) -> bool:
    """Return True if none of candidate_cells overlap or crowd a Bookmark/Respite ('R')."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    for cx, cy in candidate_cells:
        for dy in range(-clearance, clearance + 1):
            ny = cy + dy
            if ny < 0 or ny >= h:
                continue
            for dx in range(-clearance, clearance + 1):
                nx = cx + dx
                if 0 <= nx < w and grid[ny][nx] == SYMBOL_RESPITE:
                    return False
    return True


def validate_wide_prop_clearances(
    grid: List[List[str]],
    respite_clearance: int = RESPITE_WIDE_PROP_CLEARANCE,
    entities: Optional[Dict[str, dict]] = None,
) -> int:
    """Clear any multi-tile prop ('h', 'S' 2x1/1x2, 'V' 2x2) overlapping walls, props, borders, or Respites ('R')."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    if w == 0 or h == 0:
        return 0

    respite_coords = [
        (rx, ry)
        for ry in range(h)
        for rx in range(w)
        if grid[ry][rx] == SYMBOL_RESPITE
    ]
    claimed_cells: Set[Tuple[int, int]] = set()
    cleared = 0
    for y in range(h):
        for x in range(w):
            ch = grid[y][x]
            if ch not in WIDE_SOLID_PROP_SYMBOLS and ch not in LARGE_SOLID_PROP_SYMBOLS:
                continue
            cells = _get_wide_prop_cells(ch, x, y, entities)
            extra_cells = cells[1:]
            oob_or_border = any(px <= 0 or px >= w - 1 or py <= 0 or py >= h - 1 for px, py in cells)
            blocked = oob_or_border or any(grid[py][px] != SYMBOL_FLOOR for px, py in extra_cells)
            overlaps_claimed = any(pt in claimed_cells for pt in cells)
            crowds_respite = any(
                max(abs(px - rx), abs(py - ry)) <= respite_clearance
                for px, py in cells
                for rx, ry in respite_coords
            )
            if blocked or overlaps_claimed or crowds_respite:
                grid[y][x] = SYMBOL_FLOOR
                if entities is not None and ch == SYMBOL_BENCH:
                    entities.pop(f"{x},{y}", None)
                cleared += 1
            else:
                claimed_cells.update(cells)
    return cleared


def validate_prop_walkable_connectivity(
    grid: List[List[str]],
    mandatory_coords: Optional[List[Tuple[int, int]]] = None,
    entities: Optional[Dict[str, dict]] = None,
) -> int:
    """Post-dressing pass treating walls + solid props ('h', 'S' N/S/E/W, 'V','B','T','d','l') as impassable.

    Clears clipping multi-tile props first, then clears the minimum set of blocking props via 0-1 BFS
    whenever a hallway, doorway, or walkable pocket becomes pinched or disconnected.
    Returns the total number of blocking/clipping props cleared.
    """
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    if w == 0 or h == 0:
        return 0

    mandatory = [pt for pt in (mandatory_coords or []) if 0 <= pt[0] < w and 0 <= pt[1] < h]
    cleared = validate_wide_prop_clearances(grid, entities=entities)

    # Ensure mandatory coordinates themselves are never covered by a solid prop or secondary cell
    _, init_owners = _get_solid_prop_footprint(grid, entities=entities)
    for mx, my in mandatory:
        owner = init_owners.get((mx, my))
        if owner is not None:
            ox, oy = owner
            if grid[oy][ox] in SOLID_PROP_SYMBOLS:
                if entities is not None and grid[oy][ox] == SYMBOL_BENCH:
                    entities.pop(f"{ox},{oy}", None)
                grid[oy][ox] = SYMBOL_FLOOR
                cleared += 1

    max_passes = 256
    for _ in range(max_passes):
        impassable, prop_owners = _get_solid_prop_footprint(grid, entities=entities)
        walkable = {(x, y) for y in range(h) for x in range(w) if (x, y) not in impassable}
        if not walkable:
            break

        visited: Set[Tuple[int, int]] = set()
        components: List[Set[Tuple[int, int]]] = []
        for pt in walkable:
            if pt in visited:
                continue
            comp: Set[Tuple[int, int]] = set()
            queue = deque([pt])
            visited.add(pt)
            while queue:
                cx, cy = queue.popleft()
                comp.add((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (nx, ny) in walkable and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            components.append(comp)

        mandatory_walkable = [pt for pt in mandatory if pt in walkable]
        components.sort(
            key=lambda c, mw=mandatory_walkable: (sum(1 for m in mw if m in c), len(c)),
            reverse=True,
        )
        primary = components[0]
        unreachable_mandatory = [m for m in mandatory_walkable if m not in primary]
        if len(components) <= 1 and not unreachable_mandatory:
            break

        # 0-1 BFS from primary component through walkable tiles (cost 0) and removable solid props (cost 1)
        dist: Dict[Tuple[int, int], int] = {pt: 0 for pt in primary}
        parent: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {pt: None for pt in primary}
        bfs_q = deque(primary)

        target_set = set(unreachable_mandatory) if unreachable_mandatory else (walkable - primary)
        found_target: Optional[Tuple[int, int]] = None

        while bfs_q:
            ux, uy = bfs_q.popleft()
            cur_d = dist[(ux, uy)]
            if (ux, uy) in target_set:
                found_target = (ux, uy)
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = ux + dx, uy + dy
                if not (0 <= nx < w and 0 <= ny < h):
                    continue
                if grid[ny][nx] in (SYMBOL_WALL, SYMBOL_WALL_BORDER):
                    continue
                step_cost = 1 if (nx, ny) in impassable else 0
                if step_cost == 1 and (nx, ny) not in prop_owners:
                    continue
                new_d = cur_d + step_cost
                if new_d < dist.get((nx, ny), 10**9):
                    dist[(nx, ny)] = new_d
                    parent[(nx, ny)] = (ux, uy)
                    if step_cost == 0:
                        bfs_q.appendleft((nx, ny))
                    else:
                        bfs_q.append((nx, ny))

        if found_target is None:
            break

        # Clear all solid props along the minimum-cost bridge path
        props_to_clear: Set[Tuple[int, int]] = set()
        cursor: Optional[Tuple[int, int]] = found_target
        while cursor is not None:
            owner = prop_owners.get(cursor)
            if owner is not None:
                props_to_clear.add(owner)
            cursor = parent.get(cursor)

        if not props_to_clear:
            break

        for ox, oy in props_to_clear:
            if grid[oy][ox] in SOLID_PROP_SYMBOLS:
                if entities is not None and grid[oy][ox] == SYMBOL_BENCH:
                    entities.pop(f"{ox},{oy}", None)
                grid[oy][ox] = SYMBOL_FLOOR
                cleared += 1

    return cleared


def _place_patrol_routes(
    grid: List[List[str]],
    entities: Dict[str, dict],
    rng: random.Random,
    active_biome: str,
) -> int:
    """Place multi-point Stanza patrol routes near enemy clusters, away from Respites and borders."""
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    if width < 14 or height < 14:
        return 0

    enemy_syms = {
        SYMBOL_ENEMY_SLUG,
        SYMBOL_ENEMY_BAT,
        SYMBOL_ENEMY_FLUTTER,
        SYMBOL_ENEMY_SMEAR,
        SYMBOL_ENEMY_BINDLING,
        SYMBOL_ENEMY_SENTRY,
        SYMBOL_ENEMY_WOLF,
    }
    enemy_coords: List[Tuple[int, int]] = []
    respite_coords: List[Tuple[int, int]] = []
    candidates: List[Tuple[int, int]] = []
    border = 4

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            cell = grid[y][x]
            if cell == SYMBOL_RESPITE:
                respite_coords.append((x, y))
            elif cell in enemy_syms:
                enemy_coords.append((x, y))

    for y in range(border, height - border):
        for x in range(border, width - border):
            if grid[y][x] != SYMBOL_FLOOR:
                continue
            if x > 0 and grid[y][x - 1] in WIDE_SOLID_PROP_SYMBOLS:
                continue
            if any(max(abs(x - rx), abs(y - ry)) <= 6 for rx, ry in respite_coords):
                continue
            candidates.append((x, y))

    if len(candidates) < 4:
        return 0

    target_routes = max(1, min(4, len(enemy_coords) // 3)) if width >= 100 else min(2, max(1, len(enemy_coords) // 2))
    rng.shuffle(enemy_coords)
    anchors: List[Tuple[int, int]] = list(enemy_coords)
    if not anchors:
        anchors = rng.sample(candidates, min(target_routes, len(candidates)))

    placed_anchors: List[Tuple[int, int]] = []
    used_tiles: Set[Tuple[int, int]] = set()
    routes_placed = 0

    for ax, ay in anchors:
        if routes_placed >= target_routes:
            break
        if any(abs(ax - px) + abs(ay - py) < 14 for px, py in placed_anchors):
            continue

        # Pick 3-4 spread-out floor waypoints near this anchor
        nearby = [
            pt for pt in candidates
            if pt not in used_tiles and 2 <= abs(pt[0] - ax) + abs(pt[1] - ay) <= 14
        ]
        if len(nearby) < 3:
            continue

        rng.shuffle(nearby)
        route_pts: List[Tuple[int, int]] = [nearby[0]]
        for pt in nearby[1:]:
            if len(route_pts) >= 4:
                break
            prev = route_pts[-1]
            step_dist = abs(pt[0] - prev[0]) + abs(pt[1] - prev[1])
            if 4 <= step_dist <= 12 and all(abs(pt[0] - op[0]) + abs(pt[1] - op[1]) >= 4 for op in route_pts):
                route_pts.append(pt)

        if len(route_pts) < 3:
            continue

        route_id = f"{active_biome}_r{routes_placed + 1}"
        for sym, (wx, wy) in zip(SYMBOL_PATROL_WAYPOINTS, route_pts):
            grid[wy][wx] = sym
            entities[f"{wx},{wy}"] = {
                "route_id": route_id,
                "wait_min": 1.2,
                "wait_max": 2.6,
            }
            used_tiles.add((wx, wy))

        placed_anchors.append((ax, ay))
        routes_placed += 1

    return routes_placed


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
    is_vitreous = active_biome == "vitreous_basin"
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == SYMBOL_FLOOR:
                dist = dist_map[y][x]
                if is_vitreous:
                    # Open reflective salt-flat sightlines with shallow glass-brine pockets
                    if dist >= 3 and rng.random() < 0.08:
                        grid[y][x] = SYMBOL_INK_PUDDLE
                    elif dist == 1 and rng.random() < 0.14:
                        grid[y][x] = SYMBOL_GRASS
                else:
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
                if is_vitreous:
                    # Sun-baked amber salt spires & ground clutter along basin rims and mid-flats
                    if dist == 1 and rng.random() < 0.09:
                        grid[y][x] = SYMBOL_CLUTTER
                    elif dist >= 3 and rng.random() < 0.022:
                        grid[y][x] = SYMBOL_STRUCTURE if rng.random() < 0.45 else SYMBOL_CLUTTER
                else:
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

        # Primary landmark respite
        if open_floors:
            ax, ay = open_floors.pop()
            grid[ay][ax] = SYMBOL_RESPITE

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

        # Normalized mid-run miniboss anchor on large room-scale organic maps
        if width >= SEGMENT_MINIBOSS_MIN_DIM and height >= SEGMENT_MINIBOSS_MIN_DIM and open_floors:
            mx, my = open_floors.pop()
            grid[my][mx] = SYMBOL_MINIBOSS_M1

        # Scatter themed organic enemies (balanced density for UDP sync & pacing)
        if is_vitreous:
            enemy_types = [
                SYMBOL_ENEMY_SENTRY,
                SYMBOL_ENEMY_WOLF,
                SYMBOL_ENEMY_WOLF,
                SYMBOL_ENEMY_FLUTTER,
                SYMBOL_ENEMY_BAT,
            ]
        else:
            enemy_types = [SYMBOL_ENEMY_SLUG, SYMBOL_ENEMY_BAT, SYMBOL_ENEMY_FLUTTER, SYMBOL_ENEMY_SMEAR]
            if active_biome in ("windy_ridge", "pastoral_valley"):
                enemy_types.extend([SYMBOL_ENEMY_WOLF, SYMBOL_ENEMY_WOLF])
        num_enemies = min(20, max(4, (width * height) // 750))
        for _ in range(num_enemies):
            if open_floors:
                ex, ey = open_floors.pop()
                grid[ey][ex] = rng.choice(enemy_types)

        # Place 80x80 (2x2) blazing Fire Chalices across open Vitreous Basin clearings
        if is_vitreous:
            chalice_target = max(2, min(6, (width * height) // 1800))
            chalice_candidates = [
                (cx_c, cy_c)
                for cy_c in range(3, height - 4)
                for cx_c in range(3, width - 4)
                if dist_map[cy_c][cx_c] >= 3
                and all(
                    grid[cy_c + dy_c][cx_c + dx_c] == SYMBOL_FLOOR
                    for dx_c in (0, 1)
                    for dy_c in (0, 1)
                )
            ]
            rng.shuffle(chalice_candidates)
            placed_chalices: List[Tuple[int, int]] = []
            for cx_c, cy_c in chalice_candidates:
                if len(placed_chalices) >= chalice_target:
                    break
                footprint = [(cx_c, cy_c), (cx_c + 1, cy_c), (cx_c, cy_c + 1), (cx_c + 1, cy_c + 1)]
                if any(grid[py_c][px_c] != SYMBOL_FLOOR for px_c, py_c in footprint):
                    continue
                if any(abs(cx_c - px_0) + abs(cy_c - py_0) < 8 for px_0, py_0 in placed_chalices):
                    continue
                if not _has_respite_clearance(grid, footprint):
                    continue
                grid[cy_c][cx_c] = SYMBOL_FIRE_CHALICE
                placed_chalices.append((cx_c, cy_c))

    _place_patrol_routes(grid, entities, rng, active_biome)

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

    # 6. Central Focal Dais & Respite
    cx, cy = sx + sw // 2, sy + sh // 2
    grid[cy][cx] = SYMBOL_RESPITE

    # Flanking candelabras or urns
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        if grid[cy + dy][cx + dx] == SYMBOL_FLOOR:
            grid[cy + dy][cx + dx] = SYMBOL_CANDELABRA if rng.random() < 0.6 else SYMBOL_INK_URN

    # 7. BFS Connectivity & Tunnel Validation
    validate_and_carve_connectivity(grid, rng, mandatory_coords=[(cx, cy)])

    # 8. Smart Architectural Dressing: Bookcases, Directional Benches, Barrels, Rubble / Aqueduct Moss
    dist_map = _compute_wall_distances(grid)
    is_aqueduct = active_biome == "sunlit_aqueducts"
    bookcase_reserved: Set[Tuple[int, int]] = set()
    occupied_solid, _ = _get_solid_prop_footprint(grid, entities=entities)
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == SYMBOL_FLOOR and (x, y) != (cx, cy) and (x, y) not in bookcase_reserved:
                dist = dist_map[y][x]
                if dist == 1:
                    # Flush against wall: orient benches inward away from their backing wall
                    n_wall = grid[y - 1][x] == SYMBOL_WALL
                    s_wall = grid[y + 1][x] == SYMBOL_WALL
                    w_wall = grid[y][x - 1] == SYMBOL_WALL
                    e_wall = grid[y][x + 1] == SYMBOL_WALL
                    if is_aqueduct:
                        if rng.random() < 0.24:
                            grid[y][x] = SYMBOL_GRASS
                        elif (n_wall or s_wall) and rng.random() < 0.08:
                            grid[y][x] = SYMBOL_CLUTTER  # Cracked aqueduct rubble
                        elif rng.random() < 0.05 and _can_place_architectural_prop(grid, [(x, y)], occupied_solid):
                            grid[y][x] = SYMBOL_BARREL
                            occupied_solid.add((x, y))
                    else:
                        placed_bench_or_case = False
                        if (n_wall or s_wall) and not (n_wall and s_wall) and rng.random() < 0.08:
                            can_place_wide = (
                                x + 1 < width - 1
                                and grid[y][x + 1] == SYMBOL_FLOOR
                                and (x + 1, y) != (cx, cy)
                                and (x + 1, y) not in bookcase_reserved
                                and (
                                    (n_wall and grid[y - 1][x + 1] == SYMBOL_WALL)
                                    or (s_wall and grid[y + 1][x + 1] == SYMBOL_WALL)
                                )
                                and _has_respite_clearance(grid, [(x, y), (x + 1, y)])
                                and _can_place_architectural_prop(grid, [(x, y), (x + 1, y)], occupied_solid)
                            )
                            if can_place_wide:
                                if rng.random() < 0.5:
                                    grid[y][x] = SYMBOL_BOOKCASE
                                else:
                                    grid[y][x] = SYMBOL_BENCH
                                    entities[f"{x},{y}"] = {"facing": "south" if n_wall else "north"}
                                bookcase_reserved.add((x + 1, y))
                                occupied_solid.add((x, y))
                                occupied_solid.add((x + 1, y))
                                placed_bench_or_case = True
                        elif (w_wall or e_wall) and not (w_wall and e_wall) and not (n_wall or s_wall):
                            if rng.random() < 0.06:
                                can_place_tall = (
                                    y + 1 < height - 1
                                    and grid[y + 1][x] == SYMBOL_FLOOR
                                    and (x, y + 1) != (cx, cy)
                                    and (x, y + 1) not in bookcase_reserved
                                    and (
                                        (w_wall and grid[y + 1][x - 1] == SYMBOL_WALL)
                                        or (e_wall and grid[y + 1][x + 1] == SYMBOL_WALL)
                                    )
                                    and _has_respite_clearance(grid, [(x, y), (x, y + 1)])
                                    and _can_place_architectural_prop(grid, [(x, y), (x, y + 1)], occupied_solid)
                                )
                                if can_place_tall:
                                    grid[y][x] = SYMBOL_BENCH
                                    entities[f"{x},{y}"] = {"facing": "east" if w_wall else "west"}
                                    bookcase_reserved.add((x, y + 1))
                                    occupied_solid.add((x, y))
                                    occupied_solid.add((x, y + 1))
                                    placed_bench_or_case = True
                        if not placed_bench_or_case:
                            if rng.random() < 0.07 and _can_place_architectural_prop(grid, [(x, y)], occupied_solid):
                                grid[y][x] = SYMBOL_BARREL
                                occupied_solid.add((x, y))
                            elif rng.random() < 0.05:
                                grid[y][x] = SYMBOL_CLUTTER  # Crumbled masonry / rubble
                elif is_aqueduct and dist == 2 and rng.random() < 0.06:
                    grid[y][x] = SYMBOL_INK_PUDDLE  # Shallow sunlit aqueduct runnel

    # 8b. Post-dressing walkable connectivity check treating walls + solid props as impassable
    validate_prop_walkable_connectivity(grid, mandatory_coords=[(cx, cy)], entities=entities)
    bookcase_reserved = set()
    for y in range(height):
        for x in range(width):
            if grid[y][x] in WIDE_SOLID_PROP_SYMBOLS or grid[y][x] in LARGE_SOLID_PROP_SYMBOLS:
                for pt in _get_wide_prop_cells(grid[y][x], x, y, entities)[1:]:
                    bookcase_reserved.add(pt)

    # 9. Spawners & Key Entrances
    open_floors = [
        (x, y)
        for y in range(2, height - 2)
        for x in range(2, width - 2)
        if grid[y][x] == SYMBOL_FLOOR and (x, y) not in bookcase_reserved
    ]
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

    # Tactical enemies: Sentries at corridors, Bindlings & Bats in wings, Miniboss in large sanctums only
    if width >= SEGMENT_MINIBOSS_MIN_DIM and height >= SEGMENT_MINIBOSS_MIN_DIM and open_floors:
        # Miniboss M1 near sanctum perimeter
        mx, my = open_floors.pop()
        grid[my][mx] = SYMBOL_MINIBOSS_M1

    if is_aqueduct:
        arch_enemies = [
            SYMBOL_ENEMY_BINDLING,
            SYMBOL_ENEMY_SLUG,
            SYMBOL_ENEMY_SMEAR,
            SYMBOL_ENEMY_WOLF,
            SYMBOL_ENEMY_SENTRY,
        ]
    else:
        arch_enemies = [SYMBOL_ENEMY_SENTRY, SYMBOL_ENEMY_BINDLING, SYMBOL_ENEMY_BAT, SYMBOL_ENEMY_SLUG]
    num_enemies = min(20, max(4, (width * height) // 750))
    for _ in range(num_enemies):
        if open_floors:
            ex, ey = open_floors.pop()
            grid[ey][ex] = rng.choice(arch_enemies)

    _place_patrol_routes(grid, entities, rng, active_biome)

    # Enforce solid boundary frame and validate wide-prop footprints against all spawns/borders
    for x in range(width):
        grid[0][x] = SYMBOL_WALL
        grid[height - 1][x] = SYMBOL_WALL
    for y in range(height):
        grid[y][0] = SYMBOL_WALL
        grid[y][width - 1] = SYMBOL_WALL
    validate_wide_prop_clearances(grid, entities=entities)

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
            if tile in (SYMBOL_PLAYER, SYMBOL_WARP, SYMBOL_RESPITE, SYMBOL_MINIBOSS_M1):
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
        or any(term in normalized_biome for term in ("swamp", "wild", "pastor", "ridge", "frozen", "vitreous", "basin"))
    )
    if is_organic:
        return generate_organic_biome(width, height, normalized_biome, seed)
    return generate_architectural_biome(width, height, normalized_biome, seed)


# Convenient alias
generate_procedural_map = generate_map


def carve_segment_connectors(
    grid: List[List[str]],
    half_width: int = CONNECTOR_HALF_WIDTH,
    entities: Optional[Dict[str, dict]] = None,
) -> List[Tuple[int, int]]:
    """Opens aligned cardinal doorway connectors on N/S/E/W edges for seamless module stitching."""
    h = len(grid)
    w = len(grid[0]) if h > 0 else 0
    mid_x = w // 2
    mid_y = h // 2
    depth = min(4, max(2, min(w, h) // 10))

    def _clear_cell(cx: int, cy: int) -> None:
        if entities is not None and grid[cy][cx] == SYMBOL_BENCH:
            entities.pop(f"{cx},{cy}", None)
        grid[cy][cx] = SYMBOL_FLOOR

    # North & South centered connectors
    for y in range(depth):
        for x in range(max(1, mid_x - half_width), min(w - 1, mid_x + half_width)):
            _clear_cell(x, y)
            _clear_cell(x, h - 1 - y)
        left_edge = max(1, mid_x - half_width) - 1
        if left_edge >= 0:
            if grid[y][left_edge] in WIDE_SOLID_PROP_SYMBOLS:
                _clear_cell(left_edge, y)
            if grid[h - 1 - y][left_edge] in WIDE_SOLID_PROP_SYMBOLS:
                _clear_cell(left_edge, h - 1 - y)
    south_top = h - depth - 1
    if south_top >= 0:
        for x in range(max(1, mid_x - half_width), min(w - 1, mid_x + half_width)):
            if (
                grid[south_top][x] == SYMBOL_BENCH
                and _get_bench_facing(entities, x, south_top) in BENCH_VERTICAL_FACINGS
            ):
                _clear_cell(x, south_top)

    # West & East centered connectors
    for x in range(depth):
        for y in range(max(1, mid_y - half_width), min(h - 1, mid_y + half_width)):
            _clear_cell(x, y)
            _clear_cell(w - 1 - x, y)
        top_edge = max(1, mid_y - half_width) - 1
        if top_edge >= 0:
            if grid[top_edge][x] == SYMBOL_BENCH and _get_bench_facing(entities, x, top_edge) in BENCH_VERTICAL_FACINGS:
                _clear_cell(x, top_edge)
            if (
                grid[top_edge][w - 1 - x] == SYMBOL_BENCH
                and _get_bench_facing(entities, w - 1 - x, top_edge) in BENCH_VERTICAL_FACINGS
            ):
                _clear_cell(w - 1 - x, top_edge)
    for y in range(max(1, mid_y - half_width), min(h - 1, mid_y + half_width)):
        east_left = w - depth - 1
        if east_left >= 0 and grid[y][east_left] in WIDE_SOLID_PROP_SYMBOLS:
            _clear_cell(east_left, y)

    return [
        (mid_x, 1),
        (mid_x, h - 2),
        (1, mid_y),
        (w - 2, mid_y),
    ]


def generate_biome_segment(
    biome: str,
    width: int,
    height: int,
    variant_index: int = 1,
    seed: Optional[int] = None,
) -> GeneratedMap:
    """Generates a stitchable biome module segment with aligned connectors and 2.5D verticality."""
    rng = random.Random(seed)
    gen_map = generate_map(biome=biome, width=width, height=height, seed=seed)
    grid = gen_map.grid

    # Remove standalone map-level spawn/warp markers from modular world segments
    for y in range(height):
        for x in range(width):
            if grid[y][x] in (SYMBOL_PLAYER, SYMBOL_WARP):
                grid[y][x] = SYMBOL_FLOOR

    # Normalize mid-run miniboss quotas across all 7 biome pools:
    # - Corridors (< SEGMENT_MINIBOSS_MIN_DIM) always carry 0 minibosses.
    # - Large rooms (>= SEGMENT_MINIBOSS_MIN_DIM) carry 1 miniboss on odd variants and 0 on even variants.
    is_room_segment = width >= SEGMENT_MINIBOSS_MIN_DIM and height >= SEGMENT_MINIBOSS_MIN_DIM
    target_minibosses = 1 if (is_room_segment and variant_index % 2 == 1) else 0
    existing_minibosses = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if grid[y][x] == SYMBOL_MINIBOSS_M1
    ]
    while len(existing_minibosses) > target_minibosses:
        mx, my = existing_minibosses.pop()
        grid[my][mx] = SYMBOL_FLOOR
    if len(existing_minibosses) < target_minibosses:
        _, occupied_owners = _get_solid_prop_footprint(grid, entities=gen_map.entities)
        candidate_floors = [
            (x, y)
            for y in range(4, height - 4)
            for x in range(4, width - 4)
            if grid[y][x] == SYMBOL_FLOOR and (x, y) not in occupied_owners
        ]
        if candidate_floors:
            mx, my = rng.choice(candidate_floors)
            grid[my][mx] = SYMBOL_MINIBOSS_M1

    connectors = carve_segment_connectors(grid, entities=gen_map.entities)
    validate_and_carve_connectivity(grid, rng, mandatory_coords=connectors)
    mid_x, mid_y = width // 2, height // 2
    doorway_edges = [
        (mid_x, 0),
        (mid_x, height - 1),
        (0, mid_y),
        (width - 1, mid_y),
    ]
    validate_prop_walkable_connectivity(grid, mandatory_coords=connectors + doorway_edges, entities=gen_map.entities)

    # Recompute elevation & verticality layers cleanly after carving connectors
    if gen_map.biome in ARCHITECTURAL_BIOMES or "tech" in gen_map.biome:
        margin = max(4, min(width, height) // 4)
        elevation_grid, stairs = build_elevation_grid(
            grid, terrace_rect=(margin, margin, width - 2 * margin, height - 2 * margin)
        )
    else:
        elevation_grid, stairs = build_elevation_grid(
            grid, terrace_center=(width // 2, height // 2), terrace_radius=max(4, min(width, height) // 6)
        )

    # Ensure connector doorway thresholds remain on ELEVATION_LOWER for flat stitching
    for cx, cy in connectors:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    elevation_grid[ny][nx] = ELEVATION_LOWER

    gen_map.elevation_grid = elevation_grid
    gen_map.verticality_layers = apply_verticality_post_pass(grid, elevation_grid, stairs)

    seg_kind = "room" if width >= 120 else "corridor"
    gen_map.map_id = f"{gen_map.biome}_{seg_kind}_{variant_index}"
    return gen_map


def generate_biome_segment_pools(
    biomes: Tuple[str, ...] = ACTIVE_WORLD_BIOMES,
    segments_per_biome: int = DEFAULT_SEGMENTS_PER_BIOME,
    output_dir: str = SEGMENTS_DIR,
    base_seed: int = 1000,
    render_previews: bool = False,
) -> Dict[str, Dict[str, List[str]]]:
    """Generates multi-segment room (120x120) and corridor (40x40) pools for each active biome."""
    manifest: Dict[str, Dict[str, List[str]]] = {}
    for b_idx, biome in enumerate(biomes):
        biome_dir = os.path.join(output_dir, biome)
        os.makedirs(biome_dir, exist_ok=True)
        rooms: List[str] = []
        corridors: List[str] = []

        for v_idx in range(1, segments_per_biome + 1):
            room_seed = base_seed + b_idx * 100 + v_idx * 2
            room_map = generate_biome_segment(biome, 120, 120, variant_index=v_idx, seed=room_seed)
            room_path = os.path.join(biome_dir, f"{biome}_room_{v_idx}.json")
            room_map.save(room_path, file_format="json")
            rooms.append(room_path)

            corr_seed = base_seed + b_idx * 100 + v_idx * 2 + 1
            corr_map = generate_biome_segment(biome, 40, 40, variant_index=v_idx, seed=corr_seed)
            corr_path = os.path.join(biome_dir, f"{biome}_corridor_{v_idx}.json")
            corr_map.save(corr_path, file_format="json")
            corridors.append(corr_path)

            if render_previews:
                render_map_preview(room_map, os.path.join(PREVIEWS_DIR, f"{room_map.map_id}_preview.png"))
                render_map_preview(corr_map, os.path.join(PREVIEWS_DIR, f"{corr_map.map_id}_preview.png"))

        manifest[biome] = {"rooms": rooms, "corridors": corridors}
    return manifest


def generate_sanctuary(
    width: int = 56,
    height: int = 40,
    seed: Optional[int] = 108,
) -> GeneratedMap:
    """Generates the expanded Sanctuary hub (maps/sanctuary.json) with courtyard, pond, shed, and Scriptorium."""
    rng = random.Random(seed)
    grid = [[SYMBOL_FLOOR for _ in range(width)] for _ in range(height)]
    entities: Dict[str, dict] = {}

    # 1. Solid outer perimeter frame (guarantees grid[0][0] == '#')
    for x in range(width):
        grid[0][x] = SYMBOL_WALL
        grid[height - 1][x] = SYMBOL_WALL
    for y in range(height):
        grid[y][0] = SYMBOL_WALL
        grid[y][width - 1] = SYMBOL_WALL

    # 2. Northwest Corner — Locked 5x5 Stone Shed (x=4..8, y=4..8) & Mossy Gravestone
    # Fill the locked shed interior with '#' so it is solid masonry behind the padlocked door
    shed_x, shed_y, shed_w, shed_h = 4, 4, 5, 5
    for y in range(shed_y, shed_y + shed_h):
        for x in range(shed_x, shed_x + shed_w):
            grid[y][x] = SYMBOL_WALL
    shed_door_x, shed_door_y = shed_x + 2, shed_y + shed_h - 1
    grid[shed_door_y][shed_door_x] = SYMBOL_STRUCTURE
    entities[f"{shed_door_x},{shed_door_y}"] = {
        "prop_type": "locked_shed_door",
        "name": "Weathered Shed Door",
        "dialogue": (
            "A heavy brass padlock seals the shed. Whatever garden tools or forgotten drafts "
            "rest inside are kept well away from the rain."
        ),
    }

    # Mossy gravestone tucked beside the shed clearing
    grave_x, grave_y = 12, 6
    grid[grave_y][grave_x] = SYMBOL_STRUCTURE
    entities[f"{grave_x},{grave_y}"] = {
        "prop_type": "mossy_gravestone",
        "name": "Mossy Gravestone",
        "dialogue": (
            "Velvet moss has nearly swallowed the epitaph. Only a weathered colophon glyph "
            "remains legible beneath the lichen."
        ),
    }

    # 3. East Wing — Cozy Multi-Candle Oak-Floored Scriptorium Hall (x=28..49, y=7..21)
    hall_x, hall_y, hall_w, hall_h = 28, 7, 22, 15
    for y in range(hall_y, hall_y + hall_h):
        for x in range(hall_x, hall_x + hall_w):
            if x in (hall_x, hall_x + hall_w - 1) or y in (hall_y, hall_y + hall_h - 1):
                grid[y][x] = SYMBOL_WALL

    # Southern single-tile (40px) centered Scriptorium entrance doorway at x=38, y=21
    grid[hall_y + hall_h - 1][38] = SYMBOL_FLOOR

    # Bookcases ('h', 2x1 horizontal, reserving open right-half floor) along north interior wall
    for bx, by in ((30, 8), (34, 8), (41, 8), (45, 8)):
        if bx + 1 < width - 1 and grid[by][bx] == SYMBOL_FLOOR and grid[by][bx + 1] == SYMBOL_FLOOR:
            grid[by][bx] = SYMBOL_BOOKCASE

    # 6 warm candelabras illuminating the Scriptorium hall
    for lx, ly in ((32, 9), (38, 9), (44, 9), (30, 16), (47, 16), (35, 19)):
        grid[ly][lx] = SYMBOL_CANDELABRA

    # Flanking Ink Urns & reading benches inside the Scriptorium (facing north toward the Chronicle interior)
    for ux, uy in ((29, 10), (48, 10), (29, 19), (48, 19)):
        grid[uy][ux] = SYMBOL_INK_URN
    for sx, sy, b_facing in ((31, 19, "north"), (45, 19, "north")):
        cells = get_bench_footprint_tiles(sx, sy, b_facing)
        if all(1 <= px < width - 1 and 1 <= py < height - 1 and grid[py][px] == SYMBOL_FLOOR for px, py in cells):
            grid[sy][sx] = SYMBOL_BENCH
            entities[f"{sx},{sy}"] = {"facing": b_facing}

    # Core Sanctuary NPCs, Stations, Lore, and Player Start:
    # - Player start 'P' at (38, 14) with unobstructed open floor immediately west (37, 14)
    spawn_x, spawn_y = 38, 14
    grid[spawn_y][spawn_x] = SYMBOL_PLAYER

    # - The Chronicle Warp Portal ('W') centered south of spawn
    grid[16][38] = SYMBOL_WARP
    entities["38,16"] = {
        "target": "macro_world",
        "name": "The Chronicle",
        "spawn_x": 680,
        "spawn_y": 280,
    }

    # - The Chronicler ('C') + research patrol route
    grid[13][34] = SYMBOL_CHRONICLER
    grid[12][31] = "1"
    entities["31,12"] = {
        "type": "PatrolPoint",
        "route_id": "chron_research",
        "caste_filter": ["Chronicler"],
        "wait_min": 10.0,
        "wait_max": 20.0,
    }
    grid[12][44] = "2"
    entities["44,12"] = {
        "type": "PatrolPoint",
        "route_id": "chron_research",
        "caste_filter": ["Chronicler"],
        "wait_min": 15.0,
        "wait_max": 30.0,
    }

    # - The Binder ('&') — exactly 1 in Sanctuary + gentle workbench patrol route
    grid[15][44] = SYMBOL_BINDER
    grid[17][43] = "3"
    entities["43,17"] = {
        "type": "PatrolPoint",
        "route_id": "binder_work",
        "caste_filter": ["Binder"],
        "wait_min": 4.0,
        "wait_max": 8.0,
    }
    grid[14][46] = "4"
    entities["46,14"] = {
        "type": "PatrolPoint",
        "route_id": "binder_work",
        "caste_filter": ["Binder"],
        "wait_min": 4.0,
        "wait_max": 8.0,
    }

    # - The Wellspring ('F') — spaced clear of player spawn
    grid[14][42] = SYMBOL_WELLSPRING

    # - LoreFragment ('L') — chronicler_nature / Faded Note (first and only LoreFragment)
    grid[14][31] = SYMBOL_LORE
    entities["31,14"] = {
        "fragment_id": "chronicler_nature",
        "name": "Faded Note",
    }

    # 4. West Courtyard — Organic Pond Basin & Lily/Reed Accents
    pond_tiles: List[List[int]] = []
    pond_cx, pond_cy = 12.5, 24.0
    for y in range(19, 30):
        for x in range(6, 20):
            nx = (x - pond_cx) / 6.2
            ny = (y - pond_cy) / 4.2
            wobble = 0.14 * ((x * 5 + y * 3) % 3 - 1)
            if nx * nx + ny * ny + wobble <= 1.0:
                pond_tiles.append([x, y])

    pond_set = {(px, py) for px, py in pond_tiles}
    for rx, ry in ((9, 22), (14, 22), (11, 25), (16, 25), (13, 27)):
        if (rx, ry) in pond_set:
            grid[ry][rx] = SYMBOL_INK_PUDDLE
            entities[f"{rx},{ry}"] = {"prop_type": "pond_lily_reeds"}

    # 5. Winding Dirt Garden Paths & Courtyard Benches / Barrels
    dirt_rects = [
        {"x": 20, "y": 23, "w": 19, "h": 3},  # Courtyard approach from Scriptorium south doorway to pond
        {"x": 20, "y": 9, "w": 3, "h": 15},   # North garden lane up toward shed & gravestone
        {"x": 6, "y": 9, "w": 15, "h": 2},    # Path fronting Weathered Shed Door & Mossy Gravestone
        {"x": 11, "y": 30, "w": 12, "h": 2},  # Southern pond overlook garden path
        {"x": 20, "y": 25, "w": 3, "h": 7},   # Spur connecting east path to south pond overlook
    ]
    dirt_set: Set[Tuple[int, int]] = set()
    for rect in dirt_rects:
        for y in range(rect["y"], rect["y"] + rect["h"]):
            for x in range(rect["x"], rect["x"] + rect["w"]):
                if (x, y) not in pond_set:
                    dirt_set.add((x, y))

    # Courtyard benches oriented toward focal features (3 benches framing the Sanctuary lake + south garden bench)
    courtyard_benches = (
        (23, 21, "west"),   # East of pond/path -> faces west toward the Sanctuary lake (40x80 vertical)
        (15, 32, "north"),  # South of pond -> faces north directly toward the Sanctuary lake (80x40 horizontal)
        (4, 23, "east"),    # West shore of pond -> faces east toward the Sanctuary lake (40x80 vertical)
        (43, 24, "south"),  # South of Scriptorium facade -> back to hall wall, faces south garden (80x40)
    )
    for sx, sy, b_facing in courtyard_benches:
        cells = get_bench_footprint_tiles(sx, sy, b_facing)
        if all(
            1 <= px < width - 1
            and 1 <= py < height - 1
            and grid[py][px] == SYMBOL_FLOOR
            and (px, py) not in pond_set
            for px, py in cells
        ):
            grid[sy][sx] = SYMBOL_BENCH
            entities[f"{sx},{sy}"] = {"facing": b_facing}
    for bx, by in ((26, 10), (26, 11), (51, 12), (51, 13), (3, 12)):
        if grid[by][bx] == SYMBOL_FLOOR:
            grid[by][bx] = SYMBOL_BARREL

    # 6. Perimeter Woodland Gnarled Trees & Overgrown Garden Flora
    wide_prop_reserved: Set[Tuple[int, int]] = set()
    for y in range(height):
        for x in range(width):
            if grid[y][x] in WIDE_SOLID_PROP_SYMBOLS or grid[y][x] in LARGE_SOLID_PROP_SYMBOLS:
                for px, py in _get_wide_prop_cells(grid[y][x], x, y, entities):
                    if 0 <= px < width and 0 <= py < height:
                        wide_prop_reserved.add((px, py))
    reserved_clear: Set[Tuple[int, int]] = set(dirt_set) | pond_set | wide_prop_reserved
    for y in range(hall_y - 1, hall_y + hall_h + 2):
        for x in range(hall_x - 1, hall_x + hall_w + 2):
            reserved_clear.add((x, y))
    for y in range(shed_y - 1, shed_y + shed_h + 2):
        for x in range(shed_x - 1, shed_x + shed_w + 2):
            reserved_clear.add((x, y))

    tree_coords = [
        # North & Northwest woodland edge
        (2, 2), (16, 2), (22, 2), (28, 2), (35, 2), (42, 2), (49, 2), (53, 3),
        # West woodland framing the garden & pond
        (2, 13), (2, 19), (2, 26), (2, 33), (5, 36),
        # South woodland framing
        (11, 36), (18, 36), (26, 36), (34, 36), (42, 36), (49, 36), (53, 35),
        # East woodland framing behind the Scriptorium
        (53, 9), (53, 17), (53, 24), (53, 30),
        # Courtyard accent trees
        (16, 14), (24, 31), (46, 29),
    ]
    for tx, ty in tree_coords:
        if (
            1 < tx < width - 1
            and 1 < ty < height - 1
            and grid[ty][tx] == SYMBOL_FLOOR
            and (tx, ty) not in reserved_clear
        ):
            grid[ty][tx] = SYMBOL_STRUCTURE
            entities[f"{tx},{ty}"] = {"prop_type": "sanctuary_tree"}

    # Grass patches & garden wildflower/fern flora around pond, gravestone, and woodland edges
    garden_flora_coords = [
        (10, 6), (14, 6), (11, 13), (15, 16), (6, 17), (19, 17), (5, 23), (5, 28),
        (8, 31), (18, 32), (27, 29), (33, 28), (41, 30), (48, 26), (24, 6), (32, 4), (47, 4),
    ]
    for fx, fy in garden_flora_coords:
        if (
            1 <= fx < width - 1
            and 1 <= fy < height - 1
            and grid[fy][fx] == SYMBOL_FLOOR
            and (fx, fy) not in pond_set
            and (fx, fy) not in wide_prop_reserved
        ):
            grid[fy][fx] = SYMBOL_CLUTTER
            entities[f"{fx},{fy}"] = {"prop_type": "garden_flora"}

    # Soft grass tufts in open garden meadow around the pond and southern courtyard
    for y in range(2, height - 2):
        for x in range(2, width - 2):
            if grid[y][x] != SYMBOL_FLOOR or (x, y) in reserved_clear:
                continue
            near_pond = abs(x - pond_cx) <= 10 and abs(y - pond_cy) <= 8
            near_edge = x <= 4 or x >= width - 5 or y <= 4 or y >= height - 5
            if (near_pond or near_edge) and rng.random() < 0.24:
                grid[y][x] = SYMBOL_GRASS if rng.random() < 0.8 else SYMBOL_THICKET

    # 7. Validate walkable connectivity across Scriptorium interior + courtyard + garden paths
    mandatory = [
        (spawn_x, spawn_y),
        (spawn_x - 1, spawn_y),
        (38, 21),
        (21, 24),
        (21, 10),
        (shed_door_x, shed_door_y + 1),
        (grave_x, grave_y + 1),
        (15, 31),
    ]
    validate_prop_walkable_connectivity(grid, mandatory_coords=mandatory, entities=entities)

    zones = {
        "wood_floor": [
            {"name": "scriptorium_interior", "x": hall_x + 1, "y": hall_y + 1, "w": hall_w - 2, "h": hall_h - 2},
        ],
        "dirt_path": dirt_rects,
        "pond_water": pond_tiles,
        "south_facade": {
            "windows": [[30, 21], [33, 21], [35, 21], [41, 21], [43, 21], [46, 21]],
            "doorway": [[38, 21]],
        },
        "roof_zones": [
            {
                "name": "scriptorium_roof",
                "x": hall_x,
                "y": hall_y,
                "w": hall_w,
                "h": hall_h - 1,
                "interior": [hall_x + 1, hall_y + 1, hall_w - 2, hall_h - 2],
                "footprint": [hall_x, hall_y, hall_w, hall_h],
                "chimney": [hall_x + hall_w - 4, hall_y],
            },
            {
                "name": "shed_roof",
                "x": shed_x,
                "y": shed_y,
                "w": shed_w,
                "h": shed_h - 1,
                "interior": [shed_x + 1, shed_y + 1, shed_w - 2, shed_h - 2],
            },
        ],
    }

    elevation_grid = [[ELEVATION_LOWER for _ in range(width)] for _ in range(height)]
    verticality_layers = apply_verticality_post_pass(grid, elevation_grid, [])

    return GeneratedMap(
        map_id="sanctuary",
        biome="sanctuary",
        width=width,
        height=height,
        grid=grid,
        entities=entities,
        seed=seed,
        elevation_grid=elevation_grid,
        verticality_layers=verticality_layers,
        zones=zones,
    )


def generate_colophon_sanctum(
    width: int = DEFAULT_MAP_WIDTH,
    height: int = DEFAULT_MAP_HEIGHT,
    seed: Optional[int] = 404,
) -> GeneratedMap:
    """Generates the enclosed, atmospheric Scriptorium starting sanctum (maps/the_colophon.json)."""
    rng = random.Random(seed)
    grid = [[SYMBOL_WALL for _ in range(width)] for _ in range(height)]
    mid_x = width // 2
    mid_y = height // 2

    # 1. Carve chamfered central Scriptorium arrival hall (leaving solid outer wall frame)
    hall_margin = 5
    chamfer = 4
    hx0, hy0 = hall_margin, hall_margin
    hx1, hy1 = width - hall_margin, height - hall_margin
    for y in range(hy0, hy1):
        for x in range(hx0, hx1):
            is_corner = (
                (x - hx0 + y - hy0 < chamfer)
                or (hx1 - 1 - x + y - hy0 < chamfer)
                or (x - hx0 + hy1 - 1 - y < chamfer)
                or (hx1 - 1 - x + hy1 - 1 - y < chamfer)
            )
            if not is_corner:
                grid[y][x] = SYMBOL_FLOOR

    # 2. Carve wide cardinal egress halls connecting the sanctum to all 4 stitched edges
    corridor_half = CONNECTOR_HALF_WIDTH
    for y in range(1, height - 1):
        for x in range(max(1, mid_x - corridor_half), min(width - 1, mid_x + corridor_half)):
            grid[y][x] = SYMBOL_FLOOR
    for x in range(1, width - 1):
        for y in range(max(1, mid_y - corridor_half), min(height - 1, mid_y + corridor_half)):
            grid[y][x] = SYMBOL_FLOOR

    # 3. Symmetrical interior architectural pillars framing the arrival plaza
    for py in (hy0 + 5, hy1 - 6):
        for px in (hx0 + 5, hx1 - 6):
            if grid[py][px] == SYMBOL_FLOOR:
                grid[py][px] = SYMBOL_WALL

    # 4. Central arrival plaza (guaranteed clear around spawn 'P' at mid_x, mid_y)
    safe_plaza: Set[Tuple[int, int]] = {
        (x, y)
        for y in range(mid_y - 3, mid_y + 4)
        for x in range(mid_x - 3, mid_x + 4)
    }

    # Flanking candelabras lighting the arrival dais and cardinal approaches
    candelabra_spots = [
        (mid_x - 4, mid_y - 4),
        (mid_x + 4, mid_y - 4),
        (mid_x - 4, mid_y + 4),
        (mid_x + 4, mid_y + 4),
    ]
    for lx, ly in candelabra_spots:
        if 1 <= lx < width - 1 and 1 <= ly < height - 1 and grid[ly][lx] == SYMBOL_FLOOR:
            grid[ly][lx] = SYMBOL_CANDELABRA

    # Decorative corner ink urns framing the sanctum hall
    urn_spots = [
        (hx0 + 3, hy0 + 3),
        (hx1 - 4, hy0 + 3),
        (hx0 + 3, hy1 - 4),
        (hx1 - 4, hy1 - 4),
    ]
    for ux, uy in urn_spots:
        if 1 <= ux < width - 1 and 1 <= uy < height - 1 and grid[uy][ux] == SYMBOL_FLOOR:
            grid[uy][ux] = SYMBOL_INK_URN

    # 5. Smart Scriptorium wall-perimeter dressing (bookcases, inward-facing directional benches, barrels, clutter)
    entities: Dict[str, dict] = {}
    dist_map = _compute_wall_distances(grid)
    occupied_solid, _ = _get_solid_prop_footprint(grid, entities=entities)
    bookcase_reserved: Set[Tuple[int, int]] = set()
    corridor_band_x = range(mid_x - corridor_half - 1, mid_x + corridor_half + 1)
    corridor_band_y = range(mid_y - corridor_half - 1, mid_y + corridor_half + 1)

    for y in range(hy0, hy1):
        for x in range(hx0, hx1):
            if (
                grid[y][x] != SYMBOL_FLOOR
                or (x, y) in safe_plaza
                or (x, y) in bookcase_reserved
                or x in corridor_band_x
                or y in corridor_band_y
            ):
                continue
            if dist_map[y][x] != 1:
                continue
            n_wall = grid[y - 1][x] == SYMBOL_WALL
            s_wall = grid[y + 1][x] == SYMBOL_WALL
            w_wall = grid[y][x - 1] == SYMBOL_WALL
            e_wall = grid[y][x + 1] == SYMBOL_WALL
            placed_wide = False
            if (n_wall or s_wall) and not (n_wall and s_wall) and rng.random() < 0.22:
                can_wide = (
                    x + 1 < hx1
                    and grid[y][x + 1] == SYMBOL_FLOOR
                    and (x + 1, y) not in safe_plaza
                    and (x + 1, y) not in bookcase_reserved
                    and (x + 1) not in corridor_band_x
                    and (
                        (n_wall and grid[y - 1][x + 1] == SYMBOL_WALL)
                        or (s_wall and grid[y + 1][x + 1] == SYMBOL_WALL)
                    )
                    and _can_place_architectural_prop(grid, [(x, y), (x + 1, y)], occupied_solid)
                )
                if can_wide:
                    if rng.random() < 0.55:
                        grid[y][x] = SYMBOL_BOOKCASE
                    else:
                        grid[y][x] = SYMBOL_BENCH
                        entities[f"{x},{y}"] = {"facing": "south" if n_wall else "north"}
                    bookcase_reserved.add((x + 1, y))
                    occupied_solid.add((x, y))
                    occupied_solid.add((x + 1, y))
                    placed_wide = True
            elif (w_wall or e_wall) and not (w_wall and e_wall) and not (n_wall or s_wall) and rng.random() < 0.16:
                can_tall = (
                    y + 1 < hy1
                    and grid[y + 1][x] == SYMBOL_FLOOR
                    and (x, y + 1) not in safe_plaza
                    and (x, y + 1) not in bookcase_reserved
                    and (y + 1) not in corridor_band_y
                    and (
                        (w_wall and grid[y + 1][x - 1] == SYMBOL_WALL)
                        or (e_wall and grid[y + 1][x + 1] == SYMBOL_WALL)
                    )
                    and _can_place_architectural_prop(grid, [(x, y), (x, y + 1)], occupied_solid)
                )
                if can_tall:
                    grid[y][x] = SYMBOL_BENCH
                    entities[f"{x},{y}"] = {"facing": "east" if w_wall else "west"}
                    bookcase_reserved.add((x, y + 1))
                    occupied_solid.add((x, y))
                    occupied_solid.add((x, y + 1))
                    placed_wide = True
            if not placed_wide:
                if rng.random() < 0.14 and _can_place_architectural_prop(grid, [(x, y)], occupied_solid):
                    grid[y][x] = SYMBOL_BARREL
                    occupied_solid.add((x, y))
                elif rng.random() < 0.12:
                    grid[y][x] = SYMBOL_CLUTTER

    # Guarantee at least one of each signature Scriptorium prop if RNG skipped any
    placed_syms = {cell for row in grid for cell in row}
    for req_sym in (SYMBOL_BOOKCASE, SYMBOL_BENCH, SYMBOL_BARREL, SYMBOL_CLUTTER):
        if req_sym in placed_syms:
            continue
        for y in range(hy0, hy1):
            placed_one = False
            for x in range(hx0, hx1):
                if (
                    grid[y][x] != SYMBOL_FLOOR
                    or (x, y) in safe_plaza
                    or (x, y) in bookcase_reserved
                    or x in corridor_band_x
                    or y in corridor_band_y
                    or dist_map[y][x] != 1
                ):
                    continue
                if req_sym in WIDE_SOLID_PROP_SYMBOLS:
                    n_wall = grid[y - 1][x] == SYMBOL_WALL
                    s_wall = grid[y + 1][x] == SYMBOL_WALL
                    if (
                        (n_wall or s_wall)
                        and x + 1 < hx1
                        and grid[y][x + 1] == SYMBOL_FLOOR
                        and (x + 1, y) not in safe_plaza
                        and (x + 1, y) not in bookcase_reserved
                        and (x + 1) not in corridor_band_x
                        and _can_place_architectural_prop(grid, [(x, y), (x + 1, y)], occupied_solid)
                    ):
                        grid[y][x] = req_sym
                        if req_sym == SYMBOL_BENCH:
                            entities[f"{x},{y}"] = {"facing": "south" if n_wall else "north"}
                        bookcase_reserved.add((x + 1, y))
                        occupied_solid.add((x, y))
                        occupied_solid.add((x + 1, y))
                        placed_one = True
                        break
                elif req_sym == SYMBOL_CLUTTER:
                    grid[y][x] = SYMBOL_CLUTTER
                    placed_one = True
                    break
                elif _can_place_architectural_prop(grid, [(x, y)], occupied_solid):
                    grid[y][x] = req_sym
                    occupied_solid.add((x, y))
                    placed_one = True
                    break
            if placed_one:
                break

    # 6. Place Player Start 'P' at sanctum center, carve cardinal connectors, and validate prop connectivity
    grid[mid_y][mid_x] = SYMBOL_PLAYER
    connectors = carve_segment_connectors(grid, entities=entities)
    doorway_edges = [(mid_x, 0), (mid_x, height - 1), (0, mid_y), (width - 1, mid_y)]
    validate_and_carve_connectivity(grid, rng, mandatory_coords=connectors + [(mid_x, mid_y)])
    validate_prop_walkable_connectivity(
        grid, mandatory_coords=connectors + doorway_edges + [(mid_x, mid_y)], entities=entities
    )

    # 7. Compute 2.5D elevation & verticality layers with flat doorway thresholds
    elevation_grid, stairs = build_elevation_grid(
        grid, terrace_rect=(mid_x - 5, mid_y - 5, 10, 10)
    )
    for cx, cy in connectors + doorway_edges:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height:
                    elevation_grid[ny][nx] = ELEVATION_LOWER
    verticality_layers = apply_verticality_post_pass(grid, elevation_grid, stairs)

    return GeneratedMap(
        map_id="the_colophon",
        biome="the_colophon",
        width=width,
        height=height,
        grid=grid,
        entities=entities,
        seed=seed,
        elevation_grid=elevation_grid,
        verticality_layers=verticality_layers,
    )


def generate_final_boss_arena(
    width: int = 72,
    height: int = 72,
    seed: Optional[int] = 777,
) -> GeneratedMap:
    """Generates the expanded Final Boss Arena (night_boss_arena) with dais, pillars, and abyssal rim."""
    grid = [[SYMBOL_WALL for _ in range(width)] for _ in range(height)]
    elev = [[ELEVATION_PIT for _ in range(width)] for _ in range(height)]

    margin = 4
    # Carve wide flanking walkways inside the outer arena wall
    for y in range(margin + 1, height - margin - 1):
        for x in range(margin + 1, width - margin - 1):
            grid[y][x] = SYMBOL_FLOOR
            elev[y][x] = ELEVATION_LOWER

    # Ensure solid arena perimeter walls sit on ELEVATION_LOWER bordering the outer abyssal pit
    for x in range(margin, width - margin):
        grid[margin][x] = SYMBOL_WALL
        grid[height - margin - 1][x] = SYMBOL_WALL
        elev[margin][x] = ELEVATION_LOWER
        elev[height - margin - 1][x] = ELEVATION_LOWER
    for y in range(margin, height - margin):
        grid[y][margin] = SYMBOL_WALL
        grid[y][width - margin - 1] = SYMBOL_WALL
        elev[y][margin] = ELEVATION_LOWER
        elev[y][width - margin - 1] = ELEVATION_LOWER

    # Chamfered outer arena corners for a grand octagonal silhouette
    chamfer = 6
    for dy in range(chamfer):
        for dx in range(chamfer - dy):
            for cy, cx in (
                (margin + 1 + dy, margin + 1 + dx),
                (margin + 1 + dy, width - margin - 2 - dx),
                (height - margin - 2 - dy, margin + 1 + dx),
                (height - margin - 2 - dy, width - margin - 2 - dx),
            ):
                grid[cy][cx] = SYMBOL_WALL
                elev[cy][cx] = ELEVATION_LOWER

    # Elevated central ritual dais (chamfered octagon)
    cx, cy = width // 2, height // 2
    dais_half = 11
    for y in range(cy - dais_half, cy + dais_half + 1):
        for x in range(cx - dais_half, cx + dais_half + 1):
            if abs(x - cx) + abs(y - cy) <= dais_half + 6:
                elev[y][x] = ELEVATION_TERRACE

    # Four cardinal 4-tile-wide staircases connecting flanking walkways to the ritual dais
    stairs: List[List[int]] = []
    for offset in range(-2, 2):
        # North & South stairs
        for sx in (cx + offset,):
            stairs.append([sx, cy - dais_half])
            stairs.append([sx, cy + dais_half])
        # West & East stairs
        for sy in (cy + offset,):
            stairs.append([cx - dais_half, sy])
            stairs.append([cx + dais_half, sy])

    # Cover pillars (#) around the flanking walkways & dais corners
    pillar_offsets = [
        (-16, -16), (16, -16), (-16, 16), (16, 16),
        (-18, 0), (18, 0), (0, -18), (0, 18),
        (-8, -8), (8, -8), (-8, 8), (8, 8),
    ]
    for ox, oy in pillar_offsets:
        px, py = cx + ox, cy + oy
        for dy in (0, 1):
            for dx in (0, 1):
                if 0 <= px + dx < width and 0 <= py + dy < height:
                    grid[py + dy][px + dx] = SYMBOL_WALL

    # Flanking candelabras & destructible ritual props/cover
    for ox, oy in ((-12, -4), (12, -4), (-12, 4), (12, 4), (-4, -12), (4, -12), (-4, 12), (4, 12)):
        grid[cy + oy][cx + ox] = SYMBOL_CANDELABRA

    for ox, oy in ((-14, -10), (14, -10), (-14, 10), (14, 10)):
        grid[cy + oy][cx + ox] = SYMBOL_BARREL
        grid[cy + oy][cx + ox + (1 if ox < 0 else -1)] = SYMBOL_INK_URN

    # Canonical Player Start (south promenade) & Final Author Boss Spawn (central dais)
    player_x, player_y = cx, height - margin - 8
    boss_x, boss_y = cx, cy - 2
    grid[player_y][player_x] = SYMBOL_PLAYER
    grid[boss_y][boss_x] = SYMBOL_FINAL_AUTHOR

    verticality_layers = apply_verticality_post_pass(grid, elev, stairs_coords=stairs)
    return GeneratedMap(
        map_id="night_boss_arena",
        biome="ruins",
        width=width,
        height=height,
        grid=grid,
        entities={},
        seed=seed,
        elevation_grid=elev,
        verticality_layers=verticality_layers,
    )


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
    parser.add_argument(
        "--generate-pools",
        action="store_true",
        help="Generate multi-segment 120x120 and 40x40 pools for all active world biomes into maps/segments/.",
    )
    parser.add_argument(
        "--segments-per-biome",
        type=int,
        default=DEFAULT_SEGMENTS_PER_BIOME,
        help="Number of room/corridor segments to generate per biome with --generate-pools (default: 4).",
    )
    parser.add_argument(
        "--generate-boss-arena",
        action="store_true",
        help="Regenerate the expanded Final Boss Arena (maps/night_boss_arena.json).",
    )
    parser.add_argument(
        "--generate-colophon",
        action="store_true",
        help="Regenerate the enclosed Scriptorium starting sanctum (maps/the_colophon.json).",
    )
    parser.add_argument(
        "--generate-sanctuary",
        action="store_true",
        help="Regenerate the expanded Sanctuary hub layout (maps/sanctuary.json).",
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

    if args.generate_pools:
        print("==================================================")
        print(" Avoid Rain - Per-Biome Segment Pool Generator")
        print("==================================================")
        manifest = generate_biome_segment_pools(
            segments_per_biome=args.segments_per_biome,
            base_seed=base_seed,
            render_previews=args.preview,
        )
        for biome, pools in manifest.items():
            print(f"  [+] {biome:<16} -> {len(pools['rooms'])} rooms (120x120), "
                  f"{len(pools['corridors'])} corridors (40x40)")
        print("Segment pool generation complete.")
        return

    if args.generate_boss_arena:
        arena_map = generate_final_boss_arena(seed=base_seed)
        arena_path = args.output or os.path.join(MAPS_DIR, "night_boss_arena.json")
        arena_map.save(arena_path, file_format="json")
        print(f"  [+] Expanded Final Boss Arena -> {arena_path} ({arena_map.width}x{arena_map.height})")
        if args.preview:
            p_path = render_map_preview(arena_map, os.path.join(PREVIEWS_DIR, "night_boss_arena_preview.png"))
            print(f"      Preview Saved -> {p_path}")
        return

    if args.generate_colophon:
        colophon_seed = args.seed if args.seed is not None else 404
        colophon_map = generate_colophon_sanctum(seed=colophon_seed)
        colophon_path = args.output or os.path.join(MAPS_DIR, "the_colophon.json")
        colophon_map.save(colophon_path, file_format="json")
        print(f"  [+] Scriptorium Starting Sanctum -> {colophon_path} ({colophon_map.width}x{colophon_map.height})")
        if args.preview:
            p_path = render_map_preview(colophon_map, os.path.join(PREVIEWS_DIR, "the_colophon_preview.png"))
            print(f"      Preview Saved -> {p_path}")
        return

    if args.generate_sanctuary:
        sanctuary_seed = args.seed if args.seed is not None else 108
        sanctuary_map = generate_sanctuary(seed=sanctuary_seed)
        sanctuary_path = args.output or os.path.join(MAPS_DIR, "sanctuary.json")
        sanctuary_map.save(sanctuary_path, file_format="json")
        print(f"  [+] Expanded Sanctuary Hub -> {sanctuary_path} ({sanctuary_map.width}x{sanctuary_map.height})")
        if args.preview:
            p_path = render_map_preview(sanctuary_map, os.path.join(PREVIEWS_DIR, "sanctuary_preview.png"))
            print(f"      Preview Saved -> {p_path}")
        return

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
