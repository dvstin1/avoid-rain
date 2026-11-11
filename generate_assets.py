#!/usr/bin/env python3
"""Standalone offline procedural pixel art PNG asset generator for Avoid Rain.

Generates grit-textured, dark-fantasy game tiles using noise, jitter, and low-contrast
palettes to simulate natural, worn materials:
1. Dirt/Floor Tile (floor_tile.png) - 40x40 desaturated slate-brown/charcoal with sand grit and scuffs.
2. Wall Tile Variants:
   - Standard masonry (wall_tile.png) - 40x40 staggered slate-blue masonry with crumbled joints.
   - Cracked/weathered stone (wall_tile_cracked.png) - jagged stone fissures and chipped edges.
   - Moss-creeping mortar (wall_tile_mossy.png) - dark-fantasy foliage climbing masonry joints.
   - Spiderwebs & pockmarks (wall_tile_webbed.png) - faint web strands and weathered pits.
3. Swamp / Natural Biome Surfaces:
   - Murky swamp water (swamp_water.png) - dark water with algae scum film and emergent reeds.
   - Muddy trampled turf (mud_turf.png) - churned damp silt, trampled puddles, and organic muck.
   - Wet peat bank (peat_bank.png) - fibrous organic dark soil with exposed root filaments.
   - Organic swamp wall (swamp_wall.png) - dark peat cliff embankment with sediment layers and root lip.
4. Moss/Overgrowth Patch (grass_natural.png) - 40x40 transparent alpha organic foliage patch.
5. Rock Cluster (rock_cluster.png) - 40x40 irregular rounded stones with drop shadows and highlight bevels.
"""
# pylint: disable=no-member,too-many-locals,too-many-arguments,too-many-positional-arguments,too-many-lines

import math
import os
import random
from typing import Dict, List, Set, Tuple
import pygame

# ==============================================================================
# CONFIGURABLE PARAMETERS & PALETTES
# ==============================================================================

# Output File Paths (created automatically if missing)
DEFAULT_FLOOR_PATH = os.path.join("assets", "graphics", "floor_tile.png")
DEFAULT_WALL_PATH = os.path.join("assets", "graphics", "wall_tile.png")
DEFAULT_WALL_CRACKED_PATH = os.path.join("assets", "graphics", "wall_tile_cracked.png")
DEFAULT_WALL_MOSSY_PATH = os.path.join("assets", "graphics", "wall_tile_mossy.png")
DEFAULT_WALL_WEBBED_PATH = os.path.join("assets", "graphics", "wall_tile_webbed.png")
DEFAULT_SWAMP_WATER_PATH = os.path.join("assets", "graphics", "swamp_water.png")
DEFAULT_MUD_TURF_PATH = os.path.join("assets", "graphics", "mud_turf.png")
DEFAULT_PEAT_BANK_PATH = os.path.join("assets", "graphics", "peat_bank.png")
DEFAULT_SWAMP_WALL_PATH = os.path.join("assets", "graphics", "swamp_wall.png")
DEFAULT_GRASS_PATH = os.path.join("assets", "graphics", "grass_natural.png")
DEFAULT_ROCK_PATH = os.path.join("assets", "graphics", "rock_cluster.png")
DEFAULT_ALTAR_PATH = os.path.join("assets", "graphics", "attunement_altar.png")

# Canonical Dimensions
TILE_WIDTH = 40
TILE_HEIGHT = 40

# --- 1. Dirt / Floor Tile Parameters ---
# Dark, desaturated slate-brown/charcoal base tone (R:45-55, G:40-48, B:35-42)
FLOOR_BASE_R_RANGE = (45, 55)
FLOOR_BASE_G_RANGE = (40, 48)
FLOOR_BASE_B_RANGE = (35, 42)
FLOOR_NOISE_SHIFT_RANGE = (-8, 8)       # Grit/sand per-pixel channel shifting
FLOOR_SCUFF_COUNT_RANGE = (18, 28)      # Number of irregular dark pit marks/smudges
FLOOR_SCUFF_STEPS_RANGE = (4, 9)        # Size/extent of scuff walker (2-5px irregular)
FLOOR_SCUFF_ALPHA_RANGE = (80, 120)     # Alpha for dark scuffs
FLOOR_SCUFF_DARKEN_DELTA = (14, 24)     # Amount subtracted from base color for scuffs
FLOOR_HIGHLIGHT_COUNT_RANGE = (12, 20)  # Sporadic tiny bright quartz/sand specks
FLOOR_HIGHLIGHT_BOOST_RANGE = (16, 28)  # Brightness boost for tiny highlights
FLOOR_VIGNETTE_LAYERS = [               # Distance from edge -> darkening percentage
    (0, 0.18),  # Outermost perimeter pixel (18% darker)
    (1, 0.10),  # 1px inward (10% darker)
    (2, 0.04),  # 2px inward (4% darker)
]

# --- 2. Wall Tile Segment Parameters ---
# Heavy, desaturated dark slate-blue/grey base tone (R:35-42, G:38-45, B:45-55)
WALL_BASE_R_RANGE = (35, 42)
WALL_BASE_G_RANGE = (38, 45)
WALL_BASE_B_RANGE = (45, 55)
WALL_COURSES = 4                         # 4 horizontal masonry courses
WALL_COURSE_HEIGHT = 10                  # 10px per course for 40px height
WALL_JOINT_COLOR = (16, 18, 24)          # Deep black-blue joint groove color
WALL_JOINT_NOISE_PROBABILITY = 0.35      # Probability of crumbled mortar jitter
WALL_BRICK_VARIATION_RANGE = (-4, 4)     # Individual block tint variation
WALL_FACET_NOISE_RANGE = (-6, 6)         # Micro-speckled stone facet noise
WALL_HIGHLIGHT_COLOR = (66, 72, 82)      # Top & left edge 1px warm grey highlight
WALL_SHADOW_COLOR = (20, 22, 28)         # Bottom & right edge 1px mortar shadow
WALL_SCUFF_COUNT_PER_BRICK = (1, 3)      # Small weathering pits per brick

# --- 2b. Wall Feature Variant Parameters ---
WALL_CRACK_COUNT_RANGE = (2, 3)          # Number of jagged fissure paths
WALL_CRACK_STEPS_RANGE = (8, 14)         # Length of jagged fissure steps
WALL_CRACK_COLOR = (14, 16, 22)          # Deep dark crack line
WALL_CRACK_LIP_COLOR = (72, 78, 88)      # 1px edge highlight lip along crack
WALL_MOSS_CLUSTER_RANGE = (6, 10)        # Mortar moss growth clusters
WALL_MOSS_COLORS = [                     # 3 dark-fantasy foliage green layers
    (28, 44, 22), (44, 70, 32), (68, 104, 48)
]
WALL_WEB_COLOR = (100, 106, 114)         # Delicate spiderweb strand color
WALL_WEB_CROSS_COLOR = (82, 88, 96)      # Spiderweb cross-thread color
WALL_POCKMARK_COUNT_RANGE = (4, 7)       # Weathered cavity pits

# --- 3. Swamp / Natural Biome Surface Parameters ---
# Murky swamp water
SWAMP_WATER_R_RANGE = (24, 32)
SWAMP_WATER_G_RANGE = (30, 42)
SWAMP_WATER_B_RANGE = (38, 52)
SWAMP_SCUM_COLORS = [
    (36, 54, 28), (50, 74, 38), (65, 92, 46)
]
SWAMP_REED_COLOR = (70, 84, 46)
SWAMP_REED_BASE_COLOR = (20, 26, 18)

# Muddy trampled turf
MUD_TURF_R_RANGE = (42, 52)
MUD_TURF_G_RANGE = (34, 44)
MUD_TURF_B_RANGE = (28, 36)
MUD_PUDDLE_COLOR = (26, 20, 16)
MUD_SHEEN_COLOR = (64, 52, 42)

# Wet peat bank
PEAT_BANK_R_RANGE = (36, 46)
PEAT_BANK_G_RANGE = (28, 36)
PEAT_BANK_B_RANGE = (24, 32)
PEAT_ROOT_COLOR = (62, 50, 38)
PEAT_ROOT_TIP_COLOR = (84, 68, 50)

# Organic swamp wall embankment
SWAMP_WALL_R_RANGE = (40, 48)
SWAMP_WALL_G_RANGE = (32, 38)
SWAMP_WALL_B_RANGE = (28, 36)
SWAMP_WALL_SEDIMENT_DARK = (24, 18, 16)
SWAMP_WALL_LIP_COLOR = (58, 46, 38)
SWAMP_WALL_SHADOW_COLOR = (18, 14, 12)

# --- 4. Moss / Overgrowth Vegetation Patch Parameters ---
# Natural dark forest/olive green base tone (R:30-48, G:50-70, B:25-45)
MOSS_SHADOW_COLOR = (24, 38, 20)         # Layer 1: Dark shadow base
MOSS_MIDTONE_COLOR = (42, 68, 34)        # Layer 2: Medium foliage midtone
MOSS_HIGHLIGHT_COLOR = (74, 112, 56)     # Layer 3: Rare light olive/sage green flecks
MOSS_WALKER_COUNT = 7                    # Number of organic drifting walker seeds
MOSS_WALKER_STEPS = 90                   # Steps per drifting walker seed
MOSS_SCUFF_CLUSTER_COUNT = (40, 65)      # Foliage scuff clusters inside silhouette
MOSS_HIGHLIGHT_SPECK_COUNT = (24, 40)    # Rare sunlit leafy speckles
MOSS_EDGE_TRANSLUCENCY_RANGE = (90, 160) # Alpha for feathered perimeter edge pixels

# --- 5. Rock Cluster Parameters ---
# Irregular, rounded grey stone blobs with drop shadows and highlight bevels
ROCK_COUNT_RANGE = (3, 5)                # 3 to 5 stones in cluster
ROCK_BASE_R_RANGE = (64, 82)             # Desaturated stone grey base
ROCK_BASE_G_RANGE = (66, 84)
ROCK_BASE_B_RANGE = (70, 88)
ROCK_RADIUS_MAIN = (7, 10)               # Primary central stone radius
ROCK_RADIUS_SATELLITE = (3, 6)           # Satellite stone radius
ROCK_GRIT_NOISE_RANGE = (-5, 5)          # Surface grit jitter
ROCK_HIGHLIGHT_COLOR = (128, 134, 142)   # 1px top-left highlight bevel
ROCK_SHADOW_COLOR = (14, 16, 20)         # Dark bottom-edge drop shadow
ROCK_SHADOW_ALPHA = 140                  # Drop shadow opacity

# --- 6. Biome Attunement Altar Parameters ---
ALTAR_SHADOW_COLOR = (12, 14, 18)        # Dark ground drop shadow
ALTAR_SHADOW_ALPHA = 130                 # Drop shadow alpha
ALTAR_BASE_STONE = (34, 38, 46)          # Stepped base bottom plinth
ALTAR_MID_STONE = (38, 42, 52)           # Stepped middle tier
ALTAR_TOP_STONE = (42, 48, 58)           # Capital top altar slab
ALTAR_HIGHLIGHT = (84, 96, 112)          # Top-down bevel highlights
ALTAR_SHADOW = (18, 20, 26)              # Underside recess shadow
ALTAR_GLOW_CYAN = (0, 220, 255)          # Cyan runic dial glow
ALTAR_GLOW_CORE = (210, 255, 255)        # Central bright runic core


def _clamp(val: float, low: int = 0, high: int = 255) -> int:
    """Clamp a numerical value within [low, high] as an integer."""
    return max(low, min(high, int(val)))


def _ensure_directory(file_path: str) -> None:
    """Create parent directories for a file path if they do not exist."""
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)


# ==============================================================================
# GENERATIVE PIPELINE 1: DIRT / FLOOR TILE
# ==============================================================================

def _apply_floor_grit_noise(
    surface: pygame.Surface,
    base_rgb: Tuple[int, int, int],
    rng: random.Random,
) -> None:
    """Apply dense low-contrast grit/sand channel jitter to each pixel."""
    width, height = surface.get_size()
    base_r, base_g, base_b = base_rgb
    for y in range(height):
        for x in range(width):
            shift = rng.randint(*FLOOR_NOISE_SHIFT_RANGE)
            r = _clamp(base_r + shift + rng.randint(-2, 2))
            g = _clamp(base_g + shift + rng.randint(-2, 2))
            b = _clamp(base_b + shift + rng.randint(-2, 2))
            surface.set_at((x, y), (r, g, b))


def _apply_floor_scuffs(
    surface: pygame.Surface,
    base_rgb: Tuple[int, int, int],
    rng: random.Random,
) -> None:
    """Stamp irregular dark pit marks and scuffs using 2-5px random walks."""
    width, height = surface.get_size()
    base_r, base_g, base_b = base_rgb
    scuff_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    num_scuffs = rng.randint(*FLOOR_SCUFF_COUNT_RANGE)

    for _ in range(num_scuffs):
        cx = rng.randint(2, width - 3)
        cy = rng.randint(2, height - 3)
        darken = rng.randint(*FLOOR_SCUFF_DARKEN_DELTA)
        color = (
            _clamp(base_r - darken),
            _clamp(base_g - darken),
            _clamp(base_b - darken),
            rng.randint(*FLOOR_SCUFF_ALPHA_RANGE),
        )
        px, py = cx, cy
        steps = rng.randint(*FLOOR_SCUFF_STEPS_RANGE)
        for _ in range(steps):
            if 0 <= px < width and 0 <= py < height:
                scuff_surf.set_at((px, py), color)
            px += rng.choice([-1, 0, 1])
            py += rng.choice([-1, 0, 1])

    surface.blit(scuff_surf, (0, 0))


def _apply_floor_highlights(surface: pygame.Surface, rng: random.Random) -> None:
    """Scatter tiny sporadic bright quartz and mineral flecks."""
    width, height = surface.get_size()
    num_highlights = rng.randint(*FLOOR_HIGHLIGHT_COUNT_RANGE)
    for _ in range(num_highlights):
        hx = rng.randint(1, width - 2)
        hy = rng.randint(1, height - 2)
        boost = rng.randint(*FLOOR_HIGHLIGHT_BOOST_RANGE)
        cur_r, cur_g, cur_b = surface.get_at((hx, hy))[:3]
        hl_color = (_clamp(cur_r + boost), _clamp(cur_g + boost), _clamp(cur_b + boost - 2))
        surface.set_at((hx, hy), hl_color)
        if rng.random() < 0.35:
            nx = _clamp(hx + rng.choice([-1, 1]), 0, width - 1)
            ny = _clamp(hy + rng.choice([-1, 1]), 0, height - 1)
            surface.set_at((nx, ny), hl_color)


def _apply_floor_vignette(surface: pygame.Surface) -> None:
    """Darken outermost 2-3 pixel perimeter for seamless tiling without seams."""
    width, height = surface.get_size()
    vignette_dict = dict(FLOOR_VIGNETTE_LAYERS)
    for y in range(height):
        for x in range(width):
            dist = min(x, y, width - 1 - x, height - 1 - y)
            if dist in vignette_dict:
                factor = 1.0 - vignette_dict[dist]
                cr, cg, cb = surface.get_at((x, y))[:3]
                surface.set_at((x, y), (_clamp(cr * factor), _clamp(cg * factor), _clamp(cb * factor)))


def generate_floor_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a grit-textured 100% opaque dark fantasy floor tile."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_rgb = (
        rng.randint(*FLOOR_BASE_R_RANGE),
        rng.randint(*FLOOR_BASE_G_RANGE),
        rng.randint(*FLOOR_BASE_B_RANGE),
    )
    surface.fill(base_rgb)

    _apply_floor_grit_noise(surface, base_rgb, rng)
    _apply_floor_scuffs(surface, base_rgb, rng)
    _apply_floor_highlights(surface, rng)
    _apply_floor_vignette(surface)

    return surface


# ==============================================================================
# GENERATIVE PIPELINE 2: WALL TILE SEGMENT & FEATURE VARIANTS
# ==============================================================================

def _build_masonry_layout(width: int, height: int) -> List[Tuple[int, int, List[Tuple[int, int, int, int]]]]:
    """Partition surface into 4 courses with staggered vertical brick joints."""
    courses = []
    course_h = height // WALL_COURSES
    for c_idx in range(WALL_COURSES):
        y0 = c_idx * course_h
        y1 = height if c_idx == WALL_COURSES - 1 else (c_idx + 1) * course_h
        if c_idx % 2 == 0:
            bricks = [(0, y0, width // 2, y1), (width // 2, y0, width, y1)]
        else:
            bricks = [
                (0, y0, width // 4, y1),
                (width // 4, y0, (width * 3) // 4, y1),
                ((width * 3) // 4, y0, width, y1),
            ]
        courses.append((y0, y1, bricks))
    return courses


def _render_brick_facets(
    surface: pygame.Surface,
    courses: List[Tuple[int, int, List[Tuple[int, int, int, int]]]],
    base_rgb: Tuple[int, int, int],
    rng: random.Random,
) -> None:
    """Render per-brick tint variation, facet stone noise, and pit marks."""
    base_r, base_g, base_b = base_rgb
    width, height = surface.get_size()

    for _y0, _y1, bricks in courses:
        for bx0, by0, bx1, by1 in bricks:
            var_r = rng.randint(*WALL_BRICK_VARIATION_RANGE)
            var_g = rng.randint(*WALL_BRICK_VARIATION_RANGE)
            var_b = rng.randint(*WALL_BRICK_VARIATION_RANGE)
            b_r = _clamp(base_r + var_r)
            b_g = _clamp(base_g + var_g)
            b_b = _clamp(base_b + var_b)

            for py in range(by0, by1):
                for px in range(bx0, bx1):
                    noise = rng.randint(*WALL_FACET_NOISE_RANGE)
                    surface.set_at((px, py), (
                        _clamp(b_r + noise + rng.randint(-1, 1)),
                        _clamp(b_g + noise + rng.randint(-1, 1)),
                        _clamp(b_b + noise + rng.randint(-1, 1)),
                    ))

            num_pits = rng.randint(*WALL_SCUFF_COUNT_PER_BRICK)
            for _ in range(num_pits):
                pit_x = rng.randint(bx0 + 1, max(bx0 + 1, bx1 - 2))
                pit_y = rng.randint(by0 + 1, max(by0 + 1, by1 - 2))
                p_dark = rng.randint(12, 22)
                for _ in range(rng.randint(2, 4)):
                    if 0 <= pit_x < width and 0 <= pit_y < height:
                        cr, cg, cb = surface.get_at((pit_x, pit_y))[:3]
                        surface.set_at((pit_x, pit_y), (_clamp(cr - p_dark), _clamp(cg - p_dark), _clamp(cb - p_dark)))
                    pit_x += rng.choice([-1, 0, 1])
                    pit_y += rng.choice([-1, 0, 1])


def _render_brick_edge_lighting(
    surface: pygame.Surface,
    courses: List[Tuple[int, int, List[Tuple[int, int, int, int]]]],
    rng: random.Random,
) -> None:
    """Draw top/left warm highlights and bottom/right recess shadows per brick."""
    for _y0, _y1, bricks in courses:
        for bx0, by0, bx1, by1 in bricks:
            for px in range(bx0 + 1, bx1 - 1):
                if rng.random() > 0.15:
                    surface.set_at((px, by0 + 1), WALL_HIGHLIGHT_COLOR)

            for py in range(by0 + 1, by1 - 1):
                if rng.random() > 0.20:
                    surface.set_at((bx0 + 1, py), WALL_HIGHLIGHT_COLOR)

            for px in range(bx0, bx1):
                surface.set_at((px, by1 - 2), WALL_SHADOW_COLOR)

            for py in range(by0, by1):
                surface.set_at((bx1 - 2, py), WALL_SHADOW_COLOR)


def _render_crumbled_joints(
    surface: pygame.Surface,
    courses: List[Tuple[int, int, List[Tuple[int, int, int, int]]]],
    rng: random.Random,
) -> None:
    """Render horizontal and vertical masonry joint grooves with crumbled noise."""
    width, height = surface.get_size()
    course_h = height // WALL_COURSES
    joint_surf = pygame.Surface((width, height), pygame.SRCALPHA)

    for c_idx in range(1, WALL_COURSES):
        jy = c_idx * course_h
        for x in range(width):
            jitter = rng.choice([-1, 0, 1]) if rng.random() < WALL_JOINT_NOISE_PROBABILITY else 0
            curr_y = _clamp(jy + jitter, 0, height - 1)
            joint_surf.set_at((x, curr_y), (*WALL_JOINT_COLOR, 255))
            if rng.random() < 0.4:
                prev_y = _clamp(curr_y - 1, 0, height - 1)
                joint_surf.set_at((x, prev_y), (*WALL_JOINT_COLOR, 220))

    for _y0, _y1, bricks in courses:
        for bx0, by0, _bx1, by1 in bricks:
            if bx0 > 0:
                for y in range(by0, by1):
                    jitter = rng.choice([-1, 0, 1]) if rng.random() < WALL_JOINT_NOISE_PROBABILITY else 0
                    curr_x = _clamp(bx0 + jitter, 0, width - 1)
                    joint_surf.set_at((curr_x, y), (*WALL_JOINT_COLOR, 255))
                    if rng.random() < 0.4:
                        sub_x = _clamp(curr_x - 1, 0, width - 1)
                        joint_surf.set_at((sub_x, y), (*WALL_JOINT_COLOR, 220))

    surface.blit(joint_surf, (0, 0))


def _apply_wall_cracks(
    surface: pygame.Surface,
    courses: List[Tuple[int, int, List[Tuple[int, int, int, int]]]],
    rng: random.Random,
) -> None:
    """Render generator-driven jagged fissures and chipped edges across bricks."""
    width, height = surface.get_size()
    num_cracks = rng.randint(*WALL_CRACK_COUNT_RANGE)

    all_bricks = [b for c in courses for b in c[2]]
    sampled_bricks = rng.sample(all_bricks, min(num_cracks, len(all_bricks)))

    for bx0, by0, bx1, by1 in sampled_bricks:
        # Start crack along an edge of the brick
        cx = rng.randint(bx0 + 2, bx1 - 3)
        cy = by0 + 1 if rng.random() < 0.5 else by1 - 2
        steps = rng.randint(*WALL_CRACK_STEPS_RANGE)

        for _ in range(steps):
            if 0 <= cx < width and 0 <= cy < height:
                surface.set_at((cx, cy), WALL_CRACK_COLOR)
                # 1px highlight lip along the top/left edge of the fissure
                if cy > 0 and surface.get_at((cx, cy - 1))[:3] != WALL_CRACK_COLOR:
                    surface.set_at((cx, cy - 1), WALL_CRACK_LIP_COLOR)
            cx += rng.choice([-1, 0, 1])
            cy += rng.choice([-1, 0, 1])

        # Chipped corner
        chip_x = bx0 if rng.random() < 0.5 else bx1 - 1
        chip_y = by0 if rng.random() < 0.5 else by1 - 1
        if 0 <= chip_x < width and 0 <= chip_y < height:
            surface.set_at((chip_x, chip_y), WALL_CRACK_COLOR)


def _apply_wall_moss(
    surface: pygame.Surface,
    courses: List[Tuple[int, int, List[Tuple[int, int, int, int]]]],
    rng: random.Random,
) -> None:
    """Render generator-driven dark-fantasy foliage climbing masonry joints."""
    width, height = surface.get_size()
    course_h = height // WALL_COURSES
    num_clusters = rng.randint(*WALL_MOSS_CLUSTER_RANGE)

    for _ in range(num_clusters):
        # Anchor cluster on a mortar joint
        if rng.random() < 0.6:
            c_idx = rng.randint(1, WALL_COURSES - 1)
            mx = rng.randint(2, width - 3)
            my = c_idx * course_h + rng.choice([-1, 0, 1])
        else:
            _, _, bricks = rng.choice(courses)
            chosen_brick = rng.choice(bricks)
            mx = chosen_brick[0] + rng.choice([-1, 0, 1])
            my = rng.randint(chosen_brick[1], chosen_brick[3] - 1)

        steps = rng.randint(6, 12)
        px, py = mx, my
        for s in range(steps):
            if 0 <= px < width and 0 <= py < height:
                col_idx = 0 if s < 3 else (1 if s < 8 else 2)
                col = WALL_MOSS_COLORS[col_idx]
                surface.set_at((px, py), col)
            px += rng.choice([-1, 0, 1])
            py += rng.choice([-1, 0, 1])


def _apply_wall_webs_and_pockets(
    surface: pygame.Surface,
    rng: random.Random,
) -> None:
    """Render generator-driven spiderweb corner strands and weathered pit pockmarks."""
    width, height = surface.get_size()

    # 1. Corner Spiderweb Strands
    corner = rng.choice(["tl", "tr"])
    origin_x = 0 if corner == "tl" else width - 1
    dir_x = 1 if corner == "tl" else -1

    web_lines = [
        ((origin_x + dir_x * 9, 0), (origin_x, 7)),
        ((origin_x + dir_x * 7, 0), (origin_x, 9)),
    ]
    for (p1x, p1y), (p2x, p2y) in web_lines:
        pygame.draw.line(surface, WALL_WEB_COLOR, (p1x, p1y), (p2x, p2y), 1)

    # Cross threads
    pygame.draw.line(
        surface, WALL_WEB_CROSS_COLOR,
        (origin_x + dir_x * 4, 1), (origin_x + dir_x * 1, 4), 1
    )
    pygame.draw.line(
        surface, WALL_WEB_CROSS_COLOR,
        (origin_x + dir_x * 7, 2), (origin_x + dir_x * 2, 7), 1
    )

    # 2. Weathered cavity pits (pockmarks)
    num_pocks = rng.randint(*WALL_POCKMARK_COUNT_RANGE)
    for _ in range(num_pocks):
        px = rng.randint(3, width - 4)
        py = rng.randint(3, height - 4)
        surface.set_at((px, py), (18, 20, 26))
        if px + 1 < width:
            surface.set_at((px + 1, py), (18, 20, 26))
        if py + 1 < height:
            surface.set_at((px, py + 1), (68, 74, 84))


def generate_wall_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
    variant: str = "standard",
) -> pygame.Surface:
    """Procedurally generate a heavy slate-blue brick wall segment with feature variants.

    Supported variants:
    - 'standard': Clean staggered masonry with crumbled joints.
    - 'cracked': Weathered masonry with jagged fissures and chipped brick corners.
    - 'mossy': Dark-fantasy foliage and lichen climbing mortar seams.
    - 'webbed': Corner gossamer spiderweb strands and weathered pit pockmarks.
    """
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_rgb = (
        rng.randint(*WALL_BASE_R_RANGE),
        rng.randint(*WALL_BASE_G_RANGE),
        rng.randint(*WALL_BASE_B_RANGE),
    )
    surface.fill(base_rgb)

    courses = _build_masonry_layout(width, height)
    _render_brick_facets(surface, courses, base_rgb, rng)
    _render_brick_edge_lighting(surface, courses, rng)
    _render_crumbled_joints(surface, courses, rng)

    if variant == "cracked":
        _apply_wall_cracks(surface, courses, rng)
    elif variant == "mossy":
        _apply_wall_moss(surface, courses, rng)
    elif variant == "webbed":
        _apply_wall_webs_and_pockets(surface, rng)

    return surface


# ==============================================================================
# GENERATIVE PIPELINE 3: SWAMP & NATURAL BIOME SURFACES (100% OPAQUE)
# ==============================================================================

def generate_swamp_water_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 100% opaque murky swamp water tile with surface scum and reeds."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_r = rng.randint(*SWAMP_WATER_R_RANGE)
    base_g = rng.randint(*SWAMP_WATER_G_RANGE)
    base_b = rng.randint(*SWAMP_WATER_B_RANGE)
    surface.fill((base_r, base_g, base_b))

    # 1. Subtle horizontal wave and liquid ripple noise
    for y in range(height):
        for x in range(width):
            ripple = int(2.5 * math.sin(x * 0.35 + y * 0.15))
            noise = rng.randint(-3, 3)
            r = _clamp(base_r + ripple + noise)
            g = _clamp(base_g + ripple + noise)
            b = _clamp(base_b + ripple * 2 + noise)
            surface.set_at((x, y), (r, g, b))

    # 2. Organic algae / duckweed scum patches
    num_scum = rng.randint(2, 4)
    for _ in range(num_scum):
        cx = rng.randint(4, width - 5)
        cy = rng.randint(4, height - 5)
        radius = rng.randint(3, 6)
        col = rng.choice(SWAMP_SCUM_COLORS)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius + rng.randint(-2, 2):
                    px, py = cx + dx, cy + dy
                    if 0 <= px < width and 0 <= py < height:
                        surface.set_at((px, py), col)

    # 3. Emergent reed stalks (1-2px wide, 4-7px tall)
    num_reeds = rng.randint(1, 3)
    for _ in range(num_reeds):
        rx = rng.randint(3, width - 4)
        ry = rng.randint(8, height - 3)
        r_height = rng.randint(4, 7)
        for h_step in range(r_height):
            py = ry - h_step
            if 0 <= py < height:
                col = SWAMP_REED_BASE_COLOR if h_step < 2 else SWAMP_REED_COLOR
                surface.set_at((rx, py), col)

    # Subtle perimeter vignette for seamless seaming
    _apply_floor_vignette(surface)
    return surface


def generate_mud_turf_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 100% opaque muddy trampled turf tile with damp silt texture."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_r = rng.randint(*MUD_TURF_R_RANGE)
    base_g = rng.randint(*MUD_TURF_G_RANGE)
    base_b = rng.randint(*MUD_TURF_B_RANGE)
    surface.fill((base_r, base_g, base_b))

    # 1. Micro-silt channel noise
    for y in range(height):
        for x in range(width):
            silt = rng.randint(-6, 6)
            surface.set_at((x, y), (
                _clamp(base_r + silt),
                _clamp(base_g + silt),
                _clamp(base_b + silt),
            ))

    # 2. Trampled wet muddy impressions and depressions
    num_depressions = rng.randint(2, 4)
    for _ in range(num_depressions):
        cx = rng.randint(4, width - 5)
        cy = rng.randint(4, height - 5)
        steps = rng.randint(5, 10)
        px, py = cx, cy
        for _ in range(steps):
            if 0 <= px < width and 0 <= py < height:
                surface.set_at((px, py), MUD_PUDDLE_COLOR)
                if py > 0 and rng.random() < 0.4:
                    surface.set_at((px, py - 1), MUD_SHEEN_COLOR)
            px += rng.choice([-1, 0, 1])
            py += rng.choice([-1, 0, 1])

    # 3. Organic debris specks (decayed twigs / peat particles)
    for _ in range(rng.randint(8, 16)):
        dx = rng.randint(2, width - 3)
        dy = rng.randint(2, height - 3)
        surface.set_at((dx, dy), (20, 16, 12))

    _apply_floor_vignette(surface)
    return surface


def generate_peat_bank_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 100% opaque fibrous wet peat bank tile with exposed root filaments."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_r = rng.randint(*PEAT_BANK_R_RANGE)
    base_g = rng.randint(*PEAT_BANK_G_RANGE)
    base_b = rng.randint(*PEAT_BANK_B_RANGE)
    surface.fill((base_r, base_g, base_b))

    # 1. Fibrous directional striations and grain
    for y in range(height):
        for x in range(width):
            fiber = int(3.0 * math.sin(x * 0.5 + y * 0.8)) + rng.randint(-4, 4)
            surface.set_at((x, y), (
                _clamp(base_r + fiber),
                _clamp(base_g + fiber),
                _clamp(base_b + fiber),
            ))

    # 2. Exposed subterranean root filaments
    num_roots = rng.randint(2, 4)
    for _ in range(num_roots):
        rx = rng.randint(2, width - 3)
        ry = rng.randint(2, height - 3)
        root_len = rng.randint(8, 15)
        for _ in range(root_len):
            if 0 <= rx < width and 0 <= ry < height:
                surface.set_at((rx, ry), PEAT_ROOT_COLOR)
                if rng.random() < 0.3:
                    surface.set_at((rx, max(0, ry - 1)), PEAT_ROOT_TIP_COLOR)
            rx += rng.choice([0, 1])
            ry += rng.choice([-1, 0, 1])

    _apply_floor_vignette(surface)
    return surface


def generate_swamp_wall_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 100% opaque organic swamp cliff embankment tile.

    Replaces masonry bricks in swamp biomes with an organic peat cliff face
    featuring sediment strata, overhanging muddy lip, and root filaments.
    """
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_r = rng.randint(*SWAMP_WALL_R_RANGE)
    base_g = rng.randint(*SWAMP_WALL_G_RANGE)
    base_b = rng.randint(*SWAMP_WALL_B_RANGE)
    surface.fill((base_r, base_g, base_b))

    # 1. Horizontal sediment layers and organic earthy strata
    for y in range(height):
        for x in range(width):
            strata_val = int(5.0 * math.sin(y * 0.45) + 3.0 * math.cos(x * 0.2))
            noise = rng.randint(-4, 4)
            surface.set_at((x, y), (
                _clamp(base_r + strata_val + noise),
                _clamp(base_g + strata_val + noise),
                _clamp(base_b + strata_val + noise),
            ))

    # 2. Earthen sediment groove lines
    for gy in (12, 24, 34):
        for x in range(width):
            jitter = rng.choice([-1, 0, 1])
            py = _clamp(gy + jitter, 0, height - 1)
            surface.set_at((x, py), SWAMP_WALL_SEDIMENT_DARK)

    # 3. Overhanging root-lip at top edge
    for x in range(width):
        surface.set_at((x, 0), SWAMP_WALL_LIP_COLOR)
        surface.set_at((x, 1), SWAMP_WALL_LIP_COLOR)
        if rng.random() < 0.35 and 2 < height:
            surface.set_at((x, 2), PEAT_ROOT_COLOR)

    # 4. Dark ground shadow at bottom edge
    for x in range(width):
        surface.set_at((x, height - 1), SWAMP_WALL_SHADOW_COLOR)
        surface.set_at((x, height - 2), SWAMP_WALL_SHADOW_COLOR)

    return surface


# ==============================================================================
# GENERATIVE PIPELINE 4: MOSS / OVERGROWTH VEGETATION PATCH
# ==============================================================================

def _generate_irregular_patch_silhouette(
    width: int,
    height: int,
    rng: random.Random,
) -> Set[Tuple[int, int]]:
    """Generate an uneven, non-circular patch silhouette using drifting random walkers."""
    seeds = [
        (width // 2 + rng.randint(-8, 8), height // 2 + rng.randint(-8, 8))
        for _ in range(MOSS_WALKER_COUNT)
    ]
    footprint: Set[Tuple[int, int]] = set()

    cluster_offsets = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    for sx, sy in seeds:
        wx, wy = sx, sy
        for _ in range(MOSS_WALKER_STEPS):
            for dx, dy in cluster_offsets:
                tx, ty = wx + dx, wy + dy
                if rng.random() < 0.8 and 2 <= tx < width - 2 and 2 <= ty < height - 2:
                    footprint.add((tx, ty))
            wx = _clamp(wx + rng.choice([-1, 0, 1]), 3, width - 4)
            wy = _clamp(wy + rng.choice([-1, 0, 1]), 3, height - 4)

    return footprint


def _render_foliage_layers(
    surface: pygame.Surface,
    footprint: Set[Tuple[int, int]],
    rng: random.Random,
) -> None:
    """Render 3-layer green hierarchy: shadow base, foliage midtone, and light specks."""
    width, height = surface.get_size()

    # Layer 1: Dark shadow base
    for px, py in footprint:
        jit = rng.randint(-3, 3)
        surface.set_at((px, py), (
            _clamp(MOSS_SHADOW_COLOR[0] + jit),
            _clamp(MOSS_SHADOW_COLOR[1] + jit),
            _clamp(MOSS_SHADOW_COLOR[2] + jit),
            255,
        ))

    footprint_list = list(footprint)
    if not footprint_list:
        return

    # Layer 2: Medium foliage midtone scuff clusters
    num_clusters = rng.randint(*MOSS_SCUFF_CLUSTER_COUNT)
    for _ in range(num_clusters):
        cx, cy = rng.choice(footprint_list)
        cluster_steps = rng.randint(4, 9)
        kx, ky = cx, cy
        for _ in range(cluster_steps):
            if (kx, ky) in footprint:
                jit = rng.randint(-4, 4)
                surface.set_at((kx, ky), (
                    _clamp(MOSS_MIDTONE_COLOR[0] + jit),
                    _clamp(MOSS_MIDTONE_COLOR[1] + jit),
                    _clamp(MOSS_MIDTONE_COLOR[2] + jit),
                    255,
                ))
            kx = _clamp(kx + rng.choice([-1, 0, 1]), 2, width - 3)
            ky = _clamp(ky + rng.choice([-1, 0, 1]), 2, height - 3)

    # Layer 3: Rare tiny light olive/sage green sunlit speckles
    num_highlights = rng.randint(*MOSS_HIGHLIGHT_SPECK_COUNT)
    for _ in range(num_highlights):
        hx, hy = rng.choice(footprint_list)
        jit = rng.randint(-5, 5)
        color = (
            _clamp(MOSS_HIGHLIGHT_COLOR[0] + jit),
            _clamp(MOSS_HIGHLIGHT_COLOR[1] + jit),
            _clamp(MOSS_HIGHLIGHT_COLOR[2] + jit),
            255,
        )
        surface.set_at((hx, hy), color)
        if rng.random() < 0.4:
            nx = _clamp(hx + rng.choice([-1, 1]), 0, width - 1)
            ny = _clamp(hy + rng.choice([-1, 1]), 0, height - 1)
            if (nx, ny) in footprint:
                surface.set_at((nx, ny), color)


def _apply_leafy_grain_and_translucency(
    surface: pygame.Surface,
    footprint: Set[Tuple[int, int]],
    rng: random.Random,
) -> None:
    """Feather perimeter edges with translucency and subtle 1px leafy fronds."""
    width, height = surface.get_size()
    perimeter = []

    for px, py in footprint:
        is_edge = any((px + dx, py + dy) not in footprint for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)])
        if is_edge:
            perimeter.append((px, py))

    for ex, ey in perimeter:
        edge_alpha = rng.randint(*MOSS_EDGE_TRANSLUCENCY_RANGE)
        cr, cg, cb = surface.get_at((ex, ey))[:3]
        surface.set_at((ex, ey), (cr, cg, cb, edge_alpha))

        if rng.random() < 0.25:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                fx, fy = ex + dx, ey + dy
                if 0 <= fx < width and 0 <= fy < height and surface.get_at((fx, fy))[3] == 0:
                    surface.set_at((fx, fy), (cr, cg, cb, rng.randint(70, 130)))
                    break


def generate_grass_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate an organic moss/overgrowth patch with alpha transparency."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    footprint = _generate_irregular_patch_silhouette(width, height, rng)
    _render_foliage_layers(surface, footprint, rng)
    _apply_leafy_grain_and_translucency(surface, footprint, rng)

    return surface


# ==============================================================================
# GENERATIVE PIPELINE 5: ROCK CLUSTER
# ==============================================================================

def _generate_rock_shapes(
    width: int,
    height: int,
    rng: random.Random,
) -> List[Dict]:
    """Generate 3-5 irregular rounded rock definitions with randomized placement offsets."""
    num_rocks = rng.randint(*ROCK_COUNT_RANGE)
    main_cx = rng.randint(width // 2 - 3, width // 2 + 3)
    main_cy = rng.randint(height // 2 - 3, height // 2 + 3)
    main_rx = rng.randint(*ROCK_RADIUS_MAIN)
    main_ry = rng.randint(max(4, main_rx - 2), main_rx + 1)

    raw_rocks = [{
        "cx": main_cx,
        "cy": main_cy,
        "rx": main_rx,
        "ry": main_ry,
        "p1": rng.uniform(0.0, 6.28),
        "p2": rng.uniform(0.0, 6.28),
    }]

    for _ in range(num_rocks - 1):
        angle = rng.uniform(0.0, 6.28)
        dist = rng.randint(8, 14)
        sat_cx = _clamp(main_cx + int(dist * math.cos(angle)), 6, width - 7)
        sat_cy = _clamp(main_cy + int(dist * math.sin(angle)), 6, height - 7)
        sat_rx = rng.randint(*ROCK_RADIUS_SATELLITE)
        sat_ry = rng.randint(max(2, sat_rx - 1), sat_rx + 1)
        raw_rocks.append({
            "cx": sat_cx,
            "cy": sat_cy,
            "rx": sat_rx,
            "ry": sat_ry,
            "p1": rng.uniform(0.0, 6.28),
            "p2": rng.uniform(0.0, 6.28),
        })

    rocks = []
    for r_def in raw_rocks:
        cx, cy = r_def["cx"], r_def["cy"]
        rx, ry = r_def["rx"], r_def["ry"]
        p1, p2 = r_def["p1"], r_def["p2"]
        pixels = set()
        for py in range(max(0, cy - ry - 2), min(height, cy + ry + 3)):
            for px in range(max(0, cx - rx - 2), min(width, cx + rx + 3)):
                dx, dy = px - cx, py - cy
                norm_d = math.sqrt((dx / max(1, rx)) ** 2 + (dy / max(1, ry)) ** 2)
                theta = math.atan2(dy, dx)
                deform = 1.0 + 0.16 * math.sin(2 * theta + p1) + 0.12 * math.cos(3 * theta + p2)
                if norm_d <= deform:
                    pixels.add((px, py))
        if pixels:
            rocks.append({"cx": cx, "cy": cy, "pixels": pixels})

    rocks.sort(key=lambda r: r["cy"])
    return rocks


def _render_rock_drop_shadows(
    surface: pygame.Surface,
    rocks: List[Dict],
    width: int,
    height: int,
) -> None:
    """Render dark bottom-edge ground drop shadows beneath each rock."""
    shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for r_def in rocks:
        for px, py in r_def["pixels"]:
            for sy_offset in (1, 2):
                sy = py + sy_offset
                if 0 <= px < width and 0 <= sy < height:
                    shadow_surf.set_at((px, sy), (*ROCK_SHADOW_COLOR, ROCK_SHADOW_ALPHA))
    surface.blit(shadow_surf, (0, 0))


def _render_rock_bodies(
    surface: pygame.Surface,
    rocks: List[Dict],
    rng: random.Random,
) -> None:
    """Render irregular rounded rock bodies with surface grit, form shadows, and highlight bevels."""
    _width, height = surface.get_size()
    for r_def in rocks:
        cx, cy = r_def["cx"], r_def["cy"]
        pixels = r_def["pixels"]
        base_r = rng.randint(*ROCK_BASE_R_RANGE)
        base_g = rng.randint(*ROCK_BASE_G_RANGE)
        base_b = rng.randint(*ROCK_BASE_B_RANGE)

        for px, py in pixels:
            grit = rng.randint(*ROCK_GRIT_NOISE_RANGE)
            r = _clamp(base_r + grit + rng.randint(-1, 1))
            g = _clamp(base_g + grit + rng.randint(-1, 1))
            b = _clamp(base_b + grit + rng.randint(-1, 1))
            if py > cy and (py + 1 >= height or (px, py + 1) not in pixels):
                r = _clamp(r * 0.72)
                g = _clamp(g * 0.72)
                b = _clamp(b * 0.72)
            surface.set_at((px, py), (r, g, b, 255))

        for px, py in pixels:
            is_top_left_edge = (
                (px - 1 < 0 or (px - 1, py) not in pixels) or
                (py - 1 < 0 or (px, py - 1) not in pixels)
            )
            if is_top_left_edge and (px <= cx + 1 or py <= cy + 1):
                hl_jit = rng.randint(-3, 3)
                hl_color = (
                    _clamp(ROCK_HIGHLIGHT_COLOR[0] + hl_jit),
                    _clamp(ROCK_HIGHLIGHT_COLOR[1] + hl_jit),
                    _clamp(ROCK_HIGHLIGHT_COLOR[2] + hl_jit),
                    255,
                )
                surface.set_at((px, py), hl_color)


def generate_rock_cluster(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 rock cluster on a transparent background."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    rocks = _generate_rock_shapes(width, height, rng)
    _render_rock_drop_shadows(surface, rocks, width, height)
    _render_rock_bodies(surface, rocks, rng)

    return surface


# ==============================================================================
# GENERATIVE PIPELINE 6: BIOME ATTUNEMENT ALTAR
# ==============================================================================

def generate_attunement_altar(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 Biome Attunement Altar on a transparent background."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1. Ambient bottom drop shadow
    shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (*ALTAR_SHADOW_COLOR, ALTAR_SHADOW_ALPHA), (4, 30, 32, 8))
    surface.blit(shadow_surf, (0, 0))

    # Helper for stepped stone plinth tier with surface grit noise and bevel highlights
    def _draw_plinth_tier(
        rect: Tuple[int, int, int, int],
        base_col: Tuple[int, int, int],
        hi_col: Tuple[int, int, int],
    ):
        rx, ry, rw, rh = rect
        tier_surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
        for py in range(rh):
            for px in range(rw):
                jitter = rng.randint(-3, 3)
                r = _clamp(base_col[0] + jitter)
                g = _clamp(base_col[1] + jitter)
                b = _clamp(base_col[2] + jitter)
                tier_surf.set_at((px, py), (r, g, b, 255))
        # Top-down bevel highlights (top and left 1px)
        for px in range(rw):
            tier_surf.set_at((px, 0), (*hi_col, 255))
        for py in range(rh):
            tier_surf.set_at((0, py), (*hi_col, 255))
        # Recess shadows (bottom and right 1px)
        for px in range(rw):
            tier_surf.set_at((px, rh - 1), (*ALTAR_SHADOW, 255))
        for py in range(rh):
            tier_surf.set_at((rw - 1, py), (*ALTAR_SHADOW, 255))
        surface.blit(tier_surf, (rx, ry))

    # 2. Stepped Base:
    # Tier 1: Base plinth
    _draw_plinth_tier((6, 26, 28, 8), ALTAR_BASE_STONE, (68, 76, 88))
    # Tier 2: Middle pedestal
    _draw_plinth_tier((9, 18, 22, 9), ALTAR_MID_STONE, (76, 86, 100))
    # Tier 3: Capital top slab
    _draw_plinth_tier((7, 10, 26, 9), ALTAR_TOP_STONE, ALTAR_HIGHLIGHT)

    # 3. Glowing Runic Core / Dial on top
    # Runic basin inset
    pygame.draw.ellipse(surface, (20, 24, 32, 255), (12, 11, 16, 7))

    # Concentric cyan glow halos
    glow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(glow_surf, (*ALTAR_GLOW_CYAN, 45), (10, 9, 20, 11))
    pygame.draw.ellipse(glow_surf, (*ALTAR_GLOW_CYAN, 90), (12, 10, 16, 9))
    pygame.draw.ellipse(glow_surf, (*ALTAR_GLOW_CYAN, 170), (14, 11, 12, 7))
    surface.blit(glow_surf, (0, 0))

    # Inner glowing dial disc
    pygame.draw.ellipse(surface, (*ALTAR_GLOW_CYAN, 240), (16, 12, 8, 5))
    # Central mystic core
    pygame.draw.ellipse(surface, (*ALTAR_GLOW_CORE, 255), (18, 13, 4, 3))

    # Compass rune tick marks
    ticks = [(20, 11), (20, 16), (14, 14), (25, 14)]
    for tx, ty in ticks:
        surface.set_at((tx, ty), (*ALTAR_GLOW_CORE, 255))

    # Floating ethereal aura motes (subtle ambient sparks above the altar)
    motes = [(17, 7), (23, 8), (20, 6)]
    for mx, my in motes:
        alpha = rng.randint(140, 200)
        surface.set_at((mx, my), (*ALTAR_GLOW_CYAN, alpha))
        if mx + 1 < width:
            surface.set_at((mx + 1, my), (*ALTAR_GLOW_CORE, alpha // 2))

    return surface


# ==============================================================================
# BATCH GENERATION & CLI ENTRY POINT
# ==============================================================================

def generate_all_assets(
    floor_path: str = DEFAULT_FLOOR_PATH,
    wall_path: str = DEFAULT_WALL_PATH,
    grass_path: str = DEFAULT_GRASS_PATH,
    rock_path: str = DEFAULT_ROCK_PATH,
    altar_path: str = DEFAULT_ALTAR_PATH,
    wall_cracked_path: str = DEFAULT_WALL_CRACKED_PATH,
    wall_mossy_path: str = DEFAULT_WALL_MOSSY_PATH,
    wall_webbed_path: str = DEFAULT_WALL_WEBBED_PATH,
    swamp_water_path: str = DEFAULT_SWAMP_WATER_PATH,
    mud_turf_path: str = DEFAULT_MUD_TURF_PATH,
    peat_bank_path: str = DEFAULT_PEAT_BANK_PATH,
    swamp_wall_path: str = DEFAULT_SWAMP_WALL_PATH,
    seed: int = None,
) -> Dict[str, str]:
    """Generate all procedural assets and save them to disk.

    Returns a dictionary mapping asset names to their written file paths.
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    results = {}

    # 1. Dirt / Floor Tile (100% opaque)
    _ensure_directory(floor_path)
    floor_surf = generate_floor_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(floor_surf, floor_path)
    results["floor_tile"] = floor_path

    # 2. Wall Tile Variants
    # 2a. Standard masonry
    _ensure_directory(wall_path)
    wall_std_surf = generate_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng, variant="standard")
    pygame.image.save(wall_std_surf, wall_path)
    results["wall_tile"] = wall_path

    # 2b. Cracked / weathered masonry
    _ensure_directory(wall_cracked_path)
    wall_cracked_surf = generate_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng, variant="cracked")
    pygame.image.save(wall_cracked_surf, wall_cracked_path)
    results["wall_tile_cracked"] = wall_cracked_path

    # 2c. Moss-creeping mortar
    _ensure_directory(wall_mossy_path)
    wall_mossy_surf = generate_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng, variant="mossy")
    pygame.image.save(wall_mossy_surf, wall_mossy_path)
    results["wall_tile_mossy"] = wall_mossy_path

    # 2d. Spiderwebs & pockmarks
    _ensure_directory(wall_webbed_path)
    wall_webbed_surf = generate_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng, variant="webbed")
    pygame.image.save(wall_webbed_surf, wall_webbed_path)
    results["wall_tile_webbed"] = wall_webbed_path

    # 3. Swamp / Natural Biome Surfaces (100% opaque)
    # 3a. Murky swamp water
    _ensure_directory(swamp_water_path)
    swamp_water_surf = generate_swamp_water_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(swamp_water_surf, swamp_water_path)
    results["swamp_water"] = swamp_water_path

    # 3b. Muddy trampled turf
    _ensure_directory(mud_turf_path)
    mud_turf_surf = generate_mud_turf_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(mud_turf_surf, mud_turf_path)
    results["mud_turf"] = mud_turf_path

    # 3c. Wet peat bank
    _ensure_directory(peat_bank_path)
    peat_bank_surf = generate_peat_bank_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(peat_bank_surf, peat_bank_path)
    results["peat_bank"] = peat_bank_path

    # 3d. Organic swamp wall embankment
    _ensure_directory(swamp_wall_path)
    swamp_wall_surf = generate_swamp_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(swamp_wall_surf, swamp_wall_path)
    results["swamp_wall"] = swamp_wall_path

    # 4. Moss / Overgrowth Patch
    _ensure_directory(grass_path)
    grass_surf = generate_grass_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(grass_surf, grass_path)
    results["grass_natural"] = grass_path

    # 5. Rock Cluster
    _ensure_directory(rock_path)
    rock_surf = generate_rock_cluster(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(rock_surf, rock_path)
    results["rock_cluster"] = rock_path

    # 6. Biome Attunement Altar
    _ensure_directory(altar_path)
    altar_surf = generate_attunement_altar(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(altar_surf, altar_path)
    results["attunement_altar"] = altar_path

    return results


def main() -> None:
    """CLI entry point for procedural asset generation."""
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()

    print("==================================================")
    print(" Avoid Rain - Procedural PNG Asset Generator")
    print("==================================================")
    print("Generating dark-fantasy grit pixel art assets...")

    written = generate_all_assets()
    for name, path in written.items():
        size_kb = os.path.getsize(path) / 1024.0 if os.path.exists(path) else 0.0
        print(f"  [+] {name:<18} -> {path} ({size_kb:.1f} KB, {TILE_WIDTH}x{TILE_HEIGHT})")

    print("All assets successfully generated.")


if __name__ == "__main__":
    main()
