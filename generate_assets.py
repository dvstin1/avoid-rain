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
6. Swamp Props (swamp_fungus.png, swamp_gas_vent.png, swamp_thorns.png) - organic swamp vegetation & vents.
8. Environmental Biome Clutter:
   - Broken stone pillars / rubble piles (ruins_rubble.png) - 40x40 fluted stone column & chipped debris.
   - Glowing fungal clusters or reeds (swamp_flora.png) - 40x40 bioluminescent marsh reeds & fungal blooms.
   - Scattered ancient scrolls / bone piles (crypt_clutter.png) - 40x40 ancient manuscript parchment & skull fragments.
"""
# pylint: disable=no-member,too-many-locals,too-many-arguments,too-many-lines
# pylint: disable=too-many-positional-arguments,too-many-branches,too-many-statements

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
DEFAULT_SWAMP_FUNGUS_PATH = os.path.join("assets", "graphics", "swamp_fungus.png")
DEFAULT_SWAMP_VENT_PATH = os.path.join("assets", "graphics", "swamp_gas_vent.png")
DEFAULT_SWAMP_THORNS_PATH = os.path.join("assets", "graphics", "swamp_thorns.png")
DEFAULT_RUINS_RUBBLE_PATH = os.path.join("assets", "graphics", "ruins_rubble.png")
DEFAULT_SWAMP_FLORA_PATH = os.path.join("assets", "graphics", "swamp_flora.png")
DEFAULT_CRYPT_CLUTTER_PATH = os.path.join("assets", "graphics", "crypt_clutter.png")

# 2.5D Verticality & Elevation Asset Paths
DEFAULT_WALL_TOP_CAP_PATH = os.path.join("assets", "graphics", "wall_top_cap.png")
DEFAULT_WALL_FRONT_FACE_PATH = os.path.join("assets", "graphics", "wall_front_face.png")
DEFAULT_SHADOW_SOUTH_PATH = os.path.join("assets", "graphics", "shadow_south.png")
DEFAULT_SHADOW_EAST_PATH = os.path.join("assets", "graphics", "shadow_east.png")
DEFAULT_SHADOW_CORNER_PATH = os.path.join("assets", "graphics", "shadow_corner.png")
DEFAULT_CLIFF_EDGE_PATH = os.path.join("assets", "graphics", "cliff_edge.png")
DEFAULT_STAIRCASE_PATH = os.path.join("assets", "graphics", "staircase_tile.png")
DEFAULT_PIT_RIM_PATH = os.path.join("assets", "graphics", "pit_rim.png")

# Final Boss Arena (Eclipse / Dark Ritual) Asset Paths
DEFAULT_BOSS_DAIS_PATH = os.path.join("assets", "graphics", "boss_dais_tile.png")
DEFAULT_BOSS_PILLAR_PATH = os.path.join("assets", "graphics", "boss_pillar_tile.png")
DEFAULT_BOSS_ABYSS_RIM_PATH = os.path.join("assets", "graphics", "boss_abyss_rim.png")

# Canonical Dimensions
TILE_WIDTH = 40
TILE_HEIGHT = 40

# --- 9. 2.5D Verticality & Elevation Parameters ---
WALL_CAP_BASE_RGB = (56, 62, 74)
WALL_CAP_HIGHLIGHT_RGB = (78, 86, 100)
WALL_CAP_BEVEL_RGB = (42, 46, 56)
WALL_FACE_TOP_RGB = (34, 38, 48)
WALL_FACE_BOTTOM_RGB = (18, 20, 26)
SHADOW_MAX_ALPHA = 155
SHADOW_SOUTH_DEPTH = 18
SHADOW_EAST_DEPTH = 16
SHADOW_CORNER_RADIUS = 18
CLIFF_LEDGE_HEIGHT = 11
STAIR_STEP_COUNT = 5
PIT_LIP_HEIGHT = 12
PIT_ABYSS_RGB = (8, 8, 13)

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
# Murky swamp water (viscous fluid: deep eggplant purple, bruised violet, sickly pea-green scum)
SWAMP_WATER_R_RANGE = (26, 36)
SWAMP_WATER_G_RANGE = (14, 22)
SWAMP_WATER_B_RANGE = (38, 54)
SWAMP_SCUM_COLORS = [
    (118, 148, 38), (142, 172, 44), (168, 204, 56)
]
SWAMP_REED_COLOR = (142, 172, 44)
SWAMP_REED_BASE_COLOR = (26, 14, 30)

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

# Organic swamp wall embankment (mounded cellular strata, bruised maroon/purple)
SWAMP_WALL_R_RANGE = (58, 70)
SWAMP_WALL_G_RANGE = (28, 36)
SWAMP_WALL_B_RANGE = (56, 68)
SWAMP_WALL_SEDIMENT_DARK = (18, 8, 22)
SWAMP_WALL_LIP_COLOR = (212, 198, 224)
SWAMP_WALL_SHADOW_COLOR = (14, 6, 18)

# Reference-Driven Swamp Props Parameters
SWAMP_FUNGUS_CAP_BASE = (92, 42, 80)
SWAMP_FUNGUS_CAP_HI = (156, 92, 138)
SWAMP_FUNGUS_CAP_SHADOW = (32, 14, 30)
SWAMP_FUNGUS_SPOTS = [(218, 204, 228), (142, 172, 44)]
SWAMP_FUNGUS_STALK = (68, 50, 74)
SWAMP_FUNGUS_STALK_SHADOW = (34, 20, 38)

SWAMP_VENT_BASE = (58, 28, 54)
SWAMP_VENT_HI = (182, 162, 194)
SWAMP_VENT_SHADOW = (18, 8, 22)
SWAMP_VENT_PUSTULE = (148, 185, 52)
SWAMP_VENT_PUSTULE_CORE = (192, 240, 78)

SWAMP_THORNS_BARK = (185, 178, 192)
SWAMP_THORNS_SHADOW = (22, 12, 26)
SWAMP_THORNS_TIP = (240, 236, 245)

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

# --- 8. Environmental Clutter Parameters ---
# 8a. Ruins Rubble & Broken Stone Pillars (ruins_rubble.png)
RUINS_RUBBLE_SHADOW_COLOR = (14, 16, 20)      # Ground drop shadow
RUINS_RUBBLE_SHADOW_ALPHA = 140               # Drop shadow opacity
RUINS_RUBBLE_BASE_STONE = (58, 62, 70)        # Cold slate stone base
RUINS_RUBBLE_MID_STONE = (72, 78, 88)         # Masonry midtone
RUINS_RUBBLE_HIGHLIGHT = (130, 140, 155)      # Top-left chipped lip bevel highlight
RUINS_RUBBLE_SHADOW = (22, 24, 30)            # Recessed joint & mortar shadow
RUINS_RUBBLE_CRACK = (16, 18, 24)             # Deep fracture crack line

# 8b. Glowing Swamp Flora & Reeds (swamp_flora.png)
SWAMP_FLORA_SHADOW_COLOR = (14, 6, 18)        # Muddy drop shadow
SWAMP_FLORA_SHADOW_ALPHA = 130                # Drop shadow opacity
SWAMP_FLORA_ROOT_BASE = (36, 20, 42)          # Boggy root mound base
SWAMP_FLORA_REED_STEM = (46, 68, 36)          # Swamp reed stalk
SWAMP_FLORA_REED_HI = (105, 155, 68)          # Reed highlight edge
SWAMP_FLORA_CAP_BASE = (135, 195, 50)         # Bioluminescent mushroom cap
SWAMP_FLORA_CAP_CORE = (205, 255, 120)        # Luminous fungal crown & spore motes
SWAMP_FLORA_CAP_SHADOW = (48, 22, 58)         # Cap underside spore shadow
SWAMP_FLORA_GLOW_HALO = (140, 220, 60)        # Ethereal spore glow halo

# 8c. Crypt Clutter: Ancient Scrolls & Bone Piles (crypt_clutter.png)
CRYPT_CLUTTER_SHADOW_COLOR = (16, 14, 18)     # Ambient drop shadow
CRYPT_CLUTTER_SHADOW_ALPHA = 135              # Drop shadow opacity
CRYPT_PARCHMENT_BASE = (182, 162, 126)        # Aged sepia parchment sheet
CRYPT_PARCHMENT_SHADOW = (96, 82, 60)         # Parchment roll underside shadow
CRYPT_PARCHMENT_HI = (226, 212, 178)          # Curled parchment highlight edge
CRYPT_PARCHMENT_INK = (50, 42, 38)            # Faded iron-gall ink script
CRYPT_BONE_BASE = (175, 172, 160)             # Bleached bone cranium & fragments
CRYPT_BONE_SHADOW = (64, 58, 54)              # Eye cavity & suture shadow
CRYPT_BONE_HI = (225, 222, 214)               # Bone highlight bevel


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
    """Procedurally generate a 100% opaque murky swamp water tile with surface scum and reeds.

    Features deep eggplant purple fluid, alternating wavy ripple bands, and sickly pea-green scum.
    """
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_r = rng.randint(*SWAMP_WATER_R_RANGE)
    base_g = rng.randint(*SWAMP_WATER_G_RANGE)
    base_b = rng.randint(*SWAMP_WATER_B_RANGE)
    surface.fill((base_r, base_g, base_b))

    # 1. Viscous fluid alternating horizontal bands and wavy ripples
    for y in range(height):
        wave = int(2.5 * math.sin(y * 0.45) + 1.5 * math.cos(y * 0.2))
        band = 4 if (y // 4) % 2 == 0 else -3
        for x in range(width):
            noise = rng.randint(-3, 3)
            r = _clamp(base_r + band + noise)
            g = _clamp(base_g + band // 2 + noise)
            b = _clamp(base_b + band * 2 + wave + noise)
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

    Features mounded cellular strata, bulbous lumps, horizontal ribbing, pale lilac
    highlights, and deep maroon/black undercut drop shadows.
    """
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_r = rng.randint(*SWAMP_WALL_R_RANGE)
    base_g = rng.randint(*SWAMP_WALL_G_RANGE)
    base_b = rng.randint(*SWAMP_WALL_B_RANGE)
    surface.fill((base_r, base_g, base_b))

    # 1. Mounded cellular strata and horizontal ribbing
    for y in range(height):
        course_y = y % 12
        course_bulb = int(4.0 * math.sin((course_y / 12.0) * math.pi))
        for x in range(width):
            x_lobe = int(3.0 * math.sin(x * 0.35))
            noise = rng.randint(-3, 3)
            r = _clamp(base_r + course_bulb + x_lobe + noise)
            g = _clamp(base_g + course_bulb // 2 + noise)
            b = _clamp(base_b + course_bulb + x_lobe + noise)
            surface.set_at((x, y), (r, g, b))

    # 2. Deep maroon/black undercut groove lines under each bulge
    for gy in (12, 24, 36):
        for x in range(width):
            jitter = rng.choice([-1, 0, 1])
            py = _clamp(gy + jitter, 0, height - 1)
            surface.set_at((x, py), SWAMP_WALL_SEDIMENT_DARK)

    # 3. Stepped pale lilac/bone-white highlights on top bulge edges
    for gy in (1, 13, 25):
        for x in range(width):
            if rng.random() < 0.8:
                py = _clamp(gy, 0, height - 1)
                surface.set_at((x, py), SWAMP_WALL_LIP_COLOR)

    # 4. Occasional pea-green organic nodules / pustules on wall face
    for _ in range(rng.randint(2, 4)):
        nx = rng.randint(4, width - 5)
        ny = rng.randint(4, height - 5)
        surface.set_at((nx, ny), (148, 205, 68))
        if nx + 1 < width:
            surface.set_at((nx + 1, ny), (185, 235, 75))

    # 5. Dark ground shadow at bottom edge
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
# GENERATIVE PIPELINE 7: REFERENCE-DRIVEN SWAMP PROPS (FUNGI, VENTS, THORNS)
# ==============================================================================

def generate_swamp_fungus(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 transparent bulbous fleshy toadstool sprite.

    Features a rounded, spotted purple/maroon mushroom cap with pale lilac and pea-green dots,
    wrinkled stem with root filaments, and ambient drop-shadow.
    """
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1. Ambient bottom drop-shadow (translucent)
    shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (14, 6, 18, 130), (6, height - 10, 28, 8))
    surface.blit(shadow_surf, (0, 0))

    # 2. Wrinkled Stalk / Roots
    cx = width // 2
    stalk_w = 10
    stalk_left = cx - stalk_w // 2
    for sy in range(16, height - 4):
        wrinkle = int(math.sin(sy * 1.2) * 1.5)
        for sx in range(stalk_left + wrinkle, stalk_left + stalk_w + wrinkle):
            if 0 <= sx < width:
                jitter = rng.randint(-3, 3)
                r = _clamp(SWAMP_FUNGUS_STALK[0] + jitter)
                g = _clamp(SWAMP_FUNGUS_STALK[1] + jitter)
                b = _clamp(SWAMP_FUNGUS_STALK[2] + jitter)
                surface.set_at((sx, sy), (r, g, b, 255))
        if sy % 4 == 0:
            for sx in range(stalk_left + wrinkle + 1, stalk_left + stalk_w + wrinkle - 1):
                if 0 <= sx < width:
                    surface.set_at((sx, sy), (*SWAMP_FUNGUS_STALK_SHADOW, 255))

    # Root filaments branching out at base
    root_tips = [(stalk_left - 4, height - 5), (stalk_left + stalk_w + 3, height - 5), (cx, height - 3)]
    for rx, ry in root_tips:
        if 0 <= rx < width and 0 <= ry < height:
            surface.set_at((rx, ry), (*SWAMP_FUNGUS_STALK, 255))
            if ry - 1 >= 0:
                surface.set_at((rx + 1, ry - 1), (*SWAMP_FUNGUS_STALK_SHADOW, 255))

    # 3. Bulbous Cap
    cap_rect = pygame.Rect(4, 5, 32, 18)
    pygame.draw.ellipse(surface, (*SWAMP_FUNGUS_CAP_BASE, 255), cap_rect)

    # Upper stepped highlight
    hi_rect = pygame.Rect(7, 6, 26, 9)
    pygame.draw.ellipse(surface, (*SWAMP_FUNGUS_CAP_HI, 255), hi_rect)

    # Lower shadow crescent
    sh_rect = pygame.Rect(5, 17, 30, 7)
    pygame.draw.ellipse(surface, (*SWAMP_FUNGUS_CAP_SHADOW, 255), sh_rect)

    # 4. Organic spots (pale lilac and pea-green)
    spots = [
        (12, 10, SWAMP_FUNGUS_SPOTS[0], 3),
        (22, 9, SWAMP_FUNGUS_SPOTS[0], 2),
        (28, 12, SWAMP_FUNGUS_SPOTS[1], 2),
        (16, 14, SWAMP_FUNGUS_SPOTS[1], 2),
        (8, 15, SWAMP_FUNGUS_SPOTS[0], 2),
        (31, 15, SWAMP_FUNGUS_SPOTS[0], 1),
    ]
    for sp_x, sp_y, sp_col, sp_rad in spots:
        pygame.draw.circle(surface, (*sp_col, 255), (sp_x, sp_y), sp_rad)

    return surface


def generate_swamp_gas_vent(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 transparent organic gas vent / hive mound sprite.

    Features a raised cellular pod mound with crater pores, glowing toxic pustules,
    and dark base shadow.
    """
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1. Base drop shadow
    shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (14, 6, 18, 140), (4, height - 14, 32, 12))
    surface.blit(shadow_surf, (0, 0))

    # 2. Main cellular mound body
    pygame.draw.ellipse(surface, (*SWAMP_VENT_BASE, 255), (6, 12, 28, 22))
    pygame.draw.ellipse(surface, (*SWAMP_VENT_BASE, 255), (14, 8, 18, 18))

    # Top-left highlight rim
    pygame.draw.arc(surface, (*SWAMP_VENT_HI, 255), (7, 10, 26, 16), 1.8, 3.8, 2)
    pygame.draw.arc(surface, (*SWAMP_VENT_HI, 255), (15, 7, 16, 12), 1.2, 3.2, 1)

    # 3. Crater vent pores (dark sunken cores)
    pores = [(16, 18, 4), (24, 15, 3)]
    for px, py, prad in pores:
        pygame.draw.circle(surface, (*SWAMP_VENT_SHADOW, 255), (px, py), prad)
        pygame.draw.circle(surface, (*SWAMP_VENT_PUSTULE, 255), (px, py), prad + 1, 1)

    # 4. Swollen pustules with glowing cores
    pustules = [(11, 23), (27, 24), (20, 10)]
    for ptx, pty in pustules:
        pygame.draw.circle(surface, (*SWAMP_VENT_PUSTULE, 255), (ptx, pty), 3)
        surface.set_at((ptx, pty), (*SWAMP_VENT_PUSTULE_CORE, 255))

    return surface


def generate_swamp_thorns(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 transparent skeletal thorn and briar patch sprite."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1. Base subtle shadow
    shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (14, 6, 18, 110), (6, height - 8, 28, 6))
    surface.blit(shadow_surf, (0, 0))

    # 2. Gnarled briar stems breaching upward
    branches = [
        [(10, 34), (12, 26), (16, 18), (14, 10)],
        [(20, 36), (22, 28), (26, 20), (30, 12)],
        [(28, 35), (29, 29), (27, 23), (25, 17)],
    ]
    for branch in branches:
        for idx in range(len(branch) - 1):
            p1, p2 = branch[idx], branch[idx + 1]
            pygame.draw.line(surface, (*SWAMP_THORNS_BARK, 255), p1, p2, 2)
            pygame.draw.line(surface, (*SWAMP_THORNS_SHADOW, 255), (p1[0], p1[1] + 1), (p2[0], p2[1] + 1), 1)

    # 3. Sharp 1-pixel calcified thorn tips
    thorns = [
        ((14, 10), (12, 7)),
        ((16, 18), (19, 16)),
        ((30, 12), (33, 9)),
        ((26, 20), (29, 19)),
        ((25, 17), (23, 14)),
        ((12, 26), (8, 24)),
    ]
    for base_pt, tip_pt in thorns:
        pygame.draw.line(surface, (*SWAMP_THORNS_BARK, 255), base_pt, tip_pt, 1)
        surface.set_at(tip_pt, (*SWAMP_THORNS_TIP, 255))

    return surface


# ==============================================================================
# GENERATIVE PIPELINE 8: ENVIRONMENTAL BIOME CLUTTER
# ==============================================================================

def generate_ruins_rubble(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 transparent broken stone pillar / rubble pile sprite."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1. Ambient bottom drop shadow
    shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(
        shadow_surf,
        (*RUINS_RUBBLE_SHADOW_COLOR, RUINS_RUBBLE_SHADOW_ALPHA),
        (3, height - 12, 34, 10),
    )
    surface.blit(shadow_surf, (0, 0))

    # 2. Broken fluted stone pillar stump (approx x: 9..23, y: 13..31)
    pillar_left, pillar_w = 9, 15
    pillar_bot = 31
    for i in range(pillar_w):
        col_x = pillar_left + i
        top_offset = rng.randint(0, 3) if i in (0, pillar_w - 1) else rng.randint(0, 4)
        col_top = 13 + (top_offset if i % 3 != 0 else top_offset + 2)
        if i in (0, 4, 8, 12):
            col_color = RUINS_RUBBLE_HIGHLIGHT
        elif i in (1, 5, 9, 13):
            col_color = RUINS_RUBBLE_MID_STONE
        elif i in (2, 6, 10, 14):
            col_color = RUINS_RUBBLE_BASE_STONE
        else:
            col_color = RUINS_RUBBLE_SHADOW

        for cy in range(col_top, pillar_bot):
            surface.set_at((col_x, cy), (*col_color, 255))
        surface.set_at((col_x, col_top), (*RUINS_RUBBLE_HIGHLIGHT, 255))

    # Diagonal fracture crack cutting across the pillar
    crack_pts = [(10, 19), (13, 21), (15, 20), (19, 25), (22, 27)]
    for idx in range(len(crack_pts) - 1):
        pygame.draw.line(surface, (*RUINS_RUBBLE_CRACK, 255), crack_pts[idx], crack_pts[idx + 1], 1)
        surface.set_at((crack_pts[idx][0], crack_pts[idx][1] - 1), (*RUINS_RUBBLE_HIGHLIGHT, 255))

    # 3. Scattered stone rubble blocks & fractured debris chunks
    chunk_rect = pygame.Rect(26, 21, 9, 8)
    for cy in range(chunk_rect.top, chunk_rect.bottom):
        for cx in range(chunk_rect.left, chunk_rect.right):
            if (cx == chunk_rect.left and cy == chunk_rect.top) or (
                cx == chunk_rect.right - 1 and cy == chunk_rect.top
            ):
                continue
            surface.set_at((cx, cy), (*RUINS_RUBBLE_BASE_STONE, 255))
    pygame.draw.line(
        surface, (*RUINS_RUBBLE_HIGHLIGHT, 255),
        (chunk_rect.left + 1, chunk_rect.top), (chunk_rect.right - 2, chunk_rect.top), 1
    )
    pygame.draw.line(
        surface, (*RUINS_RUBBLE_HIGHLIGHT, 255),
        (chunk_rect.left, chunk_rect.top + 1), (chunk_rect.left, chunk_rect.bottom - 2), 1
    )
    pygame.draw.line(
        surface, (*RUINS_RUBBLE_SHADOW, 255),
        (chunk_rect.left, chunk_rect.bottom - 1), (chunk_rect.right - 1, chunk_rect.bottom - 1), 1
    )
    pygame.draw.line(
        surface, (*RUINS_RUBBLE_SHADOW, 255),
        (chunk_rect.right - 1, chunk_rect.top + 1), (chunk_rect.right - 1, chunk_rect.bottom - 1), 1
    )

    debris = [
        ((5, 26, 5, 4), RUINS_RUBBLE_MID_STONE),
        ((19, 28, 4, 3), RUINS_RUBBLE_BASE_STONE),
        ((32, 26, 4, 4), RUINS_RUBBLE_MID_STONE),
    ]
    for (dx, dy, dw, dh), dcol in debris:
        pygame.draw.rect(surface, (*dcol, 255), (dx, dy, dw, dh))
        surface.set_at((dx, dy), (*RUINS_RUBBLE_HIGHLIGHT, 255))
        surface.set_at((dx + dw - 1, dy + dh - 1), (*RUINS_RUBBLE_SHADOW, 255))

    # 4. Dense surface grit noise on opaque stone pixels
    for y in range(height):
        for x in range(width):
            px = surface.get_at((x, y))
            if px[3] == 255:
                jitter = rng.randint(-4, 4)
                surface.set_at((x, y), (
                    _clamp(px[0] + jitter),
                    _clamp(px[1] + jitter),
                    _clamp(px[2] + jitter),
                    255,
                ))

    return surface


def generate_swamp_flora(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 transparent glowing fungal cluster / reeds sprite."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1. Base subtle muddy shadow
    shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(
        shadow_surf,
        (*SWAMP_FLORA_SHADOW_COLOR, SWAMP_FLORA_SHADOW_ALPHA),
        (5, height - 10, 30, 8),
    )
    surface.blit(shadow_surf, (0, 0))

    # 2. Boggy root knot mound at the base
    pygame.draw.ellipse(surface, (*SWAMP_FLORA_ROOT_BASE, 255), (8, 27, 24, 9))
    for rx, ry in [(9, 32), (18, 34), (28, 33)]:
        pygame.draw.circle(surface, (*SWAMP_FLORA_REED_STEM, 255), (rx, ry), 2)

    # 3. Slender arching marsh reeds reaching upward
    reeds = [
        [(15, 30), (16, 22), (19, 14), (22, 6)],
        [(24, 30), (26, 23), (29, 16), (32, 9)],
        [(18, 29), (16, 21), (13, 15)],
    ]
    for stalk in reeds:
        for idx in range(len(stalk) - 1):
            p1, p2 = stalk[idx], stalk[idx + 1]
            pygame.draw.line(surface, (*SWAMP_FLORA_REED_STEM, 255), p1, p2, 2)
            pygame.draw.line(surface, (*SWAMP_FLORA_REED_HI, 255), (p1[0] - 1, p1[1]), (p2[0] - 1, p2[1]), 1)

    # 4. Spore glow halos for the fungal blooms
    glow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    caps_info = [
        ((20, 18), 7, 5),   # Primary cap center, rx, ry
        ((11, 23), 5, 4),   # Left cap center
        ((27, 23), 5, 4),   # Right cap center
    ]
    for (cx, cy), rx, ry in caps_info:
        pygame.draw.ellipse(
            glow_surf,
            (*SWAMP_FLORA_GLOW_HALO, 60),
            (cx - rx - 3, cy - ry - 3, (rx + 3) * 2, (ry + 3) * 2),
        )
        pygame.draw.ellipse(
            glow_surf,
            (*SWAMP_FLORA_GLOW_HALO, 110),
            (cx - rx - 1, cy - ry - 1, (rx + 1) * 2, (ry + 1) * 2),
        )
    surface.blit(glow_surf, (0, 0))

    # 5. Stems and glowing mushroom caps
    pygame.draw.line(surface, (185, 165, 195, 255), (20, 27), (20, 20), 3)
    pygame.draw.line(surface, (175, 155, 185, 255), (11, 29), (11, 24), 2)
    pygame.draw.line(surface, (175, 155, 185, 255), (27, 29), (27, 24), 2)

    for (cx, cy), rx, ry in caps_info:
        pygame.draw.ellipse(surface, (*SWAMP_FLORA_CAP_SHADOW, 255), (cx - rx, cy - ry + 1, rx * 2, ry * 2))
        pygame.draw.ellipse(surface, (*SWAMP_FLORA_CAP_BASE, 255), (cx - rx, cy - ry, rx * 2, ry * 2 - 1))
        pygame.draw.ellipse(surface, (*SWAMP_FLORA_CAP_CORE, 255), (cx - rx // 2, cy - ry + 1, rx, ry - 1))

    # 6. Floating bioluminescent motes / spore specks in the air
    motes = [(15, 12), (24, 11), (21, 8), (9, 18), (30, 16)]
    for mx, my in motes:
        surface.set_at((mx, my), (*SWAMP_FLORA_CAP_CORE, 255))
        surface.set_at((mx + 1, my), (*SWAMP_FLORA_GLOW_HALO, 140))

    # 7. Surface grit jitter on opaque pixels
    for y in range(height):
        for x in range(width):
            px = surface.get_at((x, y))
            if px[3] == 255:
                jitter = rng.randint(-3, 3)
                surface.set_at((x, y), (
                    _clamp(px[0] + jitter),
                    _clamp(px[1] + jitter),
                    _clamp(px[2] + jitter),
                    255,
                ))

    return surface


def generate_crypt_clutter(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 transparent scattered scrolls / bone piles sprite."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1. Base drop shadow
    shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(
        shadow_surf,
        (*CRYPT_CLUTTER_SHADOW_COLOR, CRYPT_CLUTTER_SHADOW_ALPHA),
        (3, height - 12, 34, 10),
    )
    surface.blit(shadow_surf, (0, 0))

    # 2. Ancient Unrolled Parchment Scroll (approx x: 6..21, y: 19..30)
    scroll_w, scroll_h = 15, 11
    scroll_x, scroll_y = 6, 20
    for sy in range(scroll_y, scroll_y + scroll_h):
        for sx in range(scroll_x, scroll_x + scroll_w):
            surface.set_at((sx, sy), (*CRYPT_PARCHMENT_BASE, 255))

    for sx in range(scroll_x, scroll_x + scroll_w):
        surface.set_at((sx, scroll_y), (*CRYPT_PARCHMENT_HI, 255))
        surface.set_at((sx, scroll_y + scroll_h - 1), (*CRYPT_PARCHMENT_SHADOW, 255))
    for sy in range(scroll_y, scroll_y + scroll_h):
        surface.set_at((scroll_x, sy), (*CRYPT_PARCHMENT_HI, 255))
        surface.set_at((scroll_x + scroll_w - 1, sy), (*CRYPT_PARCHMENT_SHADOW, 255))

    ink_lines = [
        (scroll_x + 3, scroll_y + 3, 9),
        (scroll_x + 2, scroll_y + 5, 11),
        (scroll_x + 3, scroll_y + 7, 8),
    ]
    for lx, ly, llen in ink_lines:
        for ox in range(llen):
            if ox % 3 != 2:
                surface.set_at((lx + ox, ly), (*CRYPT_PARCHMENT_INK, 255))

    # Tightly rolled manuscript cylinder
    roll_rect = pygame.Rect(18, 27, 13, 5)
    pygame.draw.rect(surface, (*CRYPT_PARCHMENT_BASE, 255), roll_rect)
    pygame.draw.line(
        surface, (*CRYPT_PARCHMENT_HI, 255),
        (roll_rect.left, roll_rect.top), (roll_rect.right - 1, roll_rect.top), 1
    )
    pygame.draw.line(
        surface, (*CRYPT_PARCHMENT_SHADOW, 255),
        (roll_rect.left, roll_rect.bottom - 1), (roll_rect.right - 1, roll_rect.bottom - 1), 1
    )
    pygame.draw.circle(surface, (*CRYPT_PARCHMENT_SHADOW, 255), (roll_rect.left, roll_rect.centery), 2)
    surface.set_at((roll_rect.left, roll_rect.centery), (*CRYPT_PARCHMENT_HI, 255))
    pygame.draw.line(
        surface, (82, 54, 42, 255),
        (roll_rect.left + 6, roll_rect.top), (roll_rect.left + 6, roll_rect.bottom - 1), 1
    )

    # 3. Ancient Bone Pile & Skull Fragment
    skull_x, skull_y = 23, 14
    pygame.draw.ellipse(surface, (*CRYPT_BONE_BASE, 255), (skull_x, skull_y, 11, 10))
    pygame.draw.arc(surface, (*CRYPT_BONE_HI, 255), (skull_x, skull_y, 11, 10), 1.0, 3.2, 1)
    surface.set_at((skull_x + 3, skull_y + 5), (*CRYPT_BONE_SHADOW, 255))
    surface.set_at((skull_x + 4, skull_y + 5), (*CRYPT_BONE_SHADOW, 255))
    surface.set_at((skull_x + 4, skull_y + 6), (*CRYPT_BONE_SHADOW, 255))
    surface.set_at((skull_x + 7, skull_y + 6), (*CRYPT_BONE_SHADOW, 255))
    surface.set_at((skull_x + 6, skull_y + 2), (*CRYPT_BONE_SHADOW, 255))
    surface.set_at((skull_x + 7, skull_y + 3), (*CRYPT_BONE_SHADOW, 255))

    bones = [
        ((14, 15), (21, 17)),
        ((7, 28), (12, 33)),
        ((32, 23), (36, 27)),
    ]
    for b_start, b_end in bones:
        pygame.draw.line(surface, (*CRYPT_BONE_BASE, 255), b_start, b_end, 2)
        surface.set_at(b_start, (*CRYPT_BONE_HI, 255))
        surface.set_at(b_end, (*CRYPT_BONE_HI, 255))

    # 4. Surface grit noise on opaque pixels
    for y in range(height):
        for x in range(width):
            px = surface.get_at((x, y))
            if px[3] == 255:
                jitter = rng.randint(-3, 3)
                surface.set_at((x, y), (
                    _clamp(px[0] + jitter),
                    _clamp(px[1] + jitter),
                    _clamp(px[2] + jitter),
                    255,
                ))

    return surface


# ==============================================================================
# GENERATIVE PIPELINE 9: 2.5D VERTICALITY & ELEVATION ASSETS
# ==============================================================================

def generate_wall_top_cap(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates a lighter top-down wall cap with crisp bevel highlights and subtle slab seams."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    surface.fill(WALL_CAP_BASE_RGB)

    # Subtle stone grit & slab seams
    for y in range(height):
        for x in range(width):
            jitter = rng.randint(-5, 5)
            is_seam = (y in (0, 20) and rng.random() < 0.85) or (x in (0, 20) and rng.random() < 0.7)
            if is_seam:
                col = (
                    _clamp(WALL_CAP_BEVEL_RGB[0] + jitter),
                    _clamp(WALL_CAP_BEVEL_RGB[1] + jitter),
                    _clamp(WALL_CAP_BEVEL_RGB[2] + jitter),
                )
            else:
                col = (
                    _clamp(WALL_CAP_BASE_RGB[0] + jitter),
                    _clamp(WALL_CAP_BASE_RGB[1] + jitter),
                    _clamp(WALL_CAP_BASE_RGB[2] + jitter),
                )
            surface.set_at((x, y), col)

    # Top and left crisp bevel highlights + bottom rim bevel
    for x in range(width):
        surface.set_at((x, 0), WALL_CAP_HIGHLIGHT_RGB)
        surface.set_at((x, 1), (68, 75, 88))
        surface.set_at((x, height - 1), WALL_CAP_BEVEL_RGB)
    for y in range(height):
        surface.set_at((0, y), WALL_CAP_HIGHLIGHT_RGB)
        surface.set_at((width - 1, y), WALL_CAP_BEVEL_RGB)

    return surface


def generate_wall_front_face(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates a darker south-facing vertical masonry wall face with vertical shadow gradient."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    courses = _build_masonry_layout(width, height)

    # Base vertical gradient from upper face to darkened ground-contact base
    for y in range(height):
        t = y / max(1, height - 1)
        base_r = int(WALL_FACE_TOP_RGB[0] * (1.0 - t) + WALL_FACE_BOTTOM_RGB[0] * t)
        base_g = int(WALL_FACE_TOP_RGB[1] * (1.0 - t) + WALL_FACE_BOTTOM_RGB[1] * t)
        base_b = int(WALL_FACE_TOP_RGB[2] * (1.0 - t) + WALL_FACE_BOTTOM_RGB[2] * t)
        for x in range(width):
            jitter = rng.randint(-4, 4)
            surface.set_at((x, y), (_clamp(base_r + jitter), _clamp(base_g + jitter), _clamp(base_b + jitter)))

    # Draw recessed horizontal/vertical brick joints and subtle top overhang shadow
    for y_start, c_h, bricks in courses:
        for x_start, _, b_w, b_h in bricks:
            for bx in range(x_start, min(width, x_start + b_w)):
                if y_start < height:
                    surface.set_at((bx, y_start), (14, 15, 20))
                if y_start + 1 < height:
                    cur = surface.get_at((bx, y_start + 1))
                    surface.set_at((bx, y_start + 1), (_clamp(cur[0] + 10), _clamp(cur[1] + 10), _clamp(cur[2] + 12)))
            for by in range(y_start, min(height, y_start + b_h)):
                if x_start < width:
                    surface.set_at((x_start, by), (14, 15, 20))

    # Top 2px overhang shadow beneath the wall cap, plus dark ambient occlusion at y=height-1..height-3
    for x in range(width):
        surface.set_at((x, 0), (14, 16, 22))
        surface.set_at((x, 1), (20, 22, 30))
        for base_y in range(height - 3, height):
            cur = surface.get_at((x, base_y))
            surface.set_at((x, base_y), (_clamp(cur[0] - 8), _clamp(cur[1] - 8), _clamp(cur[2] - 8)))

    return surface


def generate_floor_shadow_overlay(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    direction: str = "south",
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates a semi-transparent dark gradient floor drop-shadow overlay.

    Supported directions:
    - 'south': Wall/pillar shadow falling southward from top edge (y=0).
    - 'east': Wall/pillar shadow falling eastward from left edge (x=0).
    - 'corner': Inner corner drop-shadow radiating from top-left (0, 0).
    """
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))

    for y in range(height):
        for x in range(width):
            alpha = 0
            if direction == "south":
                if y < SHADOW_SOUTH_DEPTH:
                    ratio = 1.0 - (y / SHADOW_SOUTH_DEPTH)
                    alpha = int(SHADOW_MAX_ALPHA * (ratio ** 1.4))
            elif direction == "east":
                if x < SHADOW_EAST_DEPTH:
                    ratio = 1.0 - (x / SHADOW_EAST_DEPTH)
                    alpha = int(SHADOW_MAX_ALPHA * 0.85 * (ratio ** 1.4))
            elif direction == "corner":
                dist = math.hypot(x, y)
                if dist < SHADOW_CORNER_RADIUS:
                    ratio = 1.0 - (dist / SHADOW_CORNER_RADIUS)
                    alpha = int(SHADOW_MAX_ALPHA * 0.9 * (ratio ** 1.35))

            if alpha > 0:
                jitter = rng.randint(-6, 6)
                final_alpha = _clamp(alpha + jitter, 0, 220)
                surface.set_at((x, y), (8, 9, 14, final_alpha))

    return surface


def generate_cliff_edge_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates a raised-terrace cliff edge tile with top plateau lip and striated vertical cliff face."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    # Top terrace lip (0..CLIFF_LEDGE_HEIGHT-1)
    for y in range(CLIFF_LEDGE_HEIGHT):
        for x in range(width):
            jitter = rng.randint(-5, 5)
            base = (62, 58, 54) if y < CLIFF_LEDGE_HEIGHT - 2 else (84, 80, 74)
            surface.set_at((x, y), (_clamp(base[0] + jitter), _clamp(base[1] + jitter), _clamp(base[2] + jitter)))

    # Crisp rim shadow separating terrace top from cliff face
    for x in range(width):
        surface.set_at((x, CLIFF_LEDGE_HEIGHT), (16, 16, 20))

    # Vertical rocky cliff face below ledge
    for y in range(CLIFF_LEDGE_HEIGHT + 1, height):
        t = (y - CLIFF_LEDGE_HEIGHT) / max(1, height - CLIFF_LEDGE_HEIGHT - 1)
        for x in range(width):
            strata_shift = 4 if ((y // 5 + x // 9) % 2 == 0) else -4
            jitter = rng.randint(-5, 5) + strata_shift
            r_val = int(42 * (1.0 - t) + 20 * t) + jitter
            g_val = int(40 * (1.0 - t) + 19 * t) + jitter
            b_val = int(44 * (1.0 - t) + 23 * t) + jitter
            surface.set_at((x, y), (_clamp(r_val), _clamp(g_val), _clamp(b_val)))

    # Vertical rock fissures
    for fx in (9, 21, 32):
        cx = fx + rng.randint(-2, 2)
        for fy in range(CLIFF_LEDGE_HEIGHT + 2, height - 2):
            if rng.random() < 0.75 and 1 <= cx < width - 1:
                surface.set_at((cx, fy), (14, 14, 18))
                surface.set_at((cx + 1, fy), (54, 52, 56))
            cx += rng.choice((-1, 0, 0, 1))

    return surface


def generate_staircase_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates a stepped stone staircase tile with alternating riser highlights and drop shadows."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    step_h = height // STAIR_STEP_COUNT

    for step_idx in range(STAIR_STEP_COUNT):
        y0 = step_idx * step_h
        y1 = height if step_idx == STAIR_STEP_COUNT - 1 else (step_idx + 1) * step_h
        # Progressive darkening down the steps
        shade = step_idx * 4
        for y in range(y0, y1):
            local_y = y - y0
            for x in range(width):
                jitter = rng.randint(-4, 4)
                # Side stone curbs
                if x < 3 or x >= width - 3:
                    col = (44 - shade // 2, 46 - shade // 2, 52 - shade // 2)
                elif local_y == 0:
                    # Bright step lip highlight
                    col = (82 - shade, 80 - shade, 76 - shade)
                elif local_y >= (y1 - y0) - 2:
                    # Deep riser under-shadow
                    col = (18, 19, 24)
                else:
                    # Stone tread surface
                    col = (56 - shade, 54 - shade, 52 - shade)

                surface.set_at((x, y), (_clamp(col[0] + jitter), _clamp(col[1] + jitter), _clamp(col[2] + jitter)))

    return surface


def generate_pit_rim_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates a chasm/pit rim tile showing a thick floor lip dropping off into dark abyssal void."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    # Top stone floor lip
    for y in range(PIT_LIP_HEIGHT):
        for x in range(width):
            jitter = rng.randint(-4, 4)
            if y >= PIT_LIP_HEIGHT - 2:
                # Chipped bright edge highlight right before drop-off
                base = (74, 72, 70)
            else:
                base = (48, 44, 42)
            surface.set_at((x, y), (_clamp(base[0] + jitter), _clamp(base[1] + jitter), _clamp(base[2] + jitter)))

    # Under-lip shadow overhang (4px)
    for y in range(PIT_LIP_HEIGHT, min(height, PIT_LIP_HEIGHT + 4)):
        for x in range(width):
            jitter = rng.randint(-3, 3)
            depth_drop = (y - PIT_LIP_HEIGHT) * 4
            surface.set_at(
                (x, y),
                (_clamp(24 - depth_drop + jitter), _clamp(22 - depth_drop + jitter), _clamp(28 + jitter)),
            )

    # Abyssal chasm void
    for y in range(PIT_LIP_HEIGHT + 4, height):
        for x in range(width):
            jitter = rng.randint(-2, 2)
            abyss_col = (
                _clamp(PIT_ABYSS_RGB[0] + jitter),
                _clamp(PIT_ABYSS_RGB[1] + jitter),
                _clamp(PIT_ABYSS_RGB[2] + jitter),
            )
            surface.set_at((x, y), abyss_col)

    return surface


# ==============================================================================
# GENERATIVE PIPELINE 10: FINAL BOSS ARENA (DARK RITUAL / ECLIPSE) ASSETS
# ==============================================================================

def generate_boss_dais_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates ornate cracked obsidian ritual dais stonework with faint eclipse-gold runes."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_rgb = (28, 26, 36)
    for y in range(height):
        for x in range(width):
            jitter = rng.randint(-4, 4)
            is_border = x in (0, width - 1) or y in (0, height - 1) or x == width // 2 or y == height // 2
            if is_border:
                col = (_clamp(16 + jitter), _clamp(15 + jitter), _clamp(22 + jitter))
            else:
                col = (_clamp(base_rgb[0] + jitter), _clamp(base_rgb[1] + jitter), _clamp(base_rgb[2] + jitter))
            surface.set_at((x, y), col)

    # Ornate eclipse-gold / crimson ritual ring inlay
    cx, cy = width // 2, height // 2
    for y in range(height):
        for x in range(width):
            dist = math.hypot(x - cx, y - cy)
            if 10.5 <= dist <= 12.0 or 4.0 <= dist <= 5.2:
                surface.set_at((x, y), (118, 86, 52))
            elif 9.5 <= dist < 10.5:
                surface.set_at((x, y), (74, 34, 46))

    # Cracked stone fissures
    for _ in range(2):
        fx, fy = rng.randint(4, width - 5), rng.randint(4, height - 5)
        for _ in range(6):
            if 1 <= fx < width - 1 and 1 <= fy < height - 1:
                surface.set_at((fx, fy), (12, 11, 16))
            fx += rng.choice((-1, 0, 1))
            fy += rng.choice((-1, 0, 1))

    return surface


def generate_boss_pillar_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates a towering ruined dark-ritual stone pillar with fluted shaft and cap highlight."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))

    # Ground drop shadow
    pygame.draw.ellipse(surface, (10, 8, 14, 150), (6, height - 12, width - 12, 10))

    # Fluted stone shaft
    for y in range(10, height - 4):
        for x in range(10, width - 10):
            flute = 8 if (x % 4 in (0, 1)) else -6
            shade = int((y - 10) * 0.4)
            jitter = rng.randint(-3, 3)
            r_v = _clamp(48 + flute - shade + jitter)
            g_v = _clamp(46 + flute - shade + jitter)
            b_v = _clamp(58 + flute - shade + jitter)
            surface.set_at((x, y), (r_v, g_v, b_v, 255))

    # Ruined beveled capital top
    for y in range(4, 12):
        for x in range(8, width - 8):
            jitter = rng.randint(-3, 3)
            if y == 4 or x == 8:
                col = (94, 90, 108, 255)
            elif y == 11:
                col = (20, 18, 26, 255)
            else:
                col = (_clamp(64 + jitter), _clamp(60 + jitter), _clamp(76 + jitter), 255)
            surface.set_at((x, y), col)

    return surface


def generate_boss_abyss_rim(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generates an eclipse-tinted abyssal chasm rim tile with fractured stone lip."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    for y in range(height):
        for x in range(width):
            jitter = rng.randint(-3, 3)
            if y < 10:
                base = (44, 40, 54)
            elif y < 13:
                base = (82, 74, 96) if (x % 7 != 0) else (22, 20, 30)
            elif y < 18:
                base = (24, 18, 34)
            else:
                base = (7, 6, 12)
            surface.set_at((x, y), (_clamp(base[0] + jitter), _clamp(base[1] + jitter), _clamp(base[2] + jitter)))

    return surface


# ==============================================================================
# BATCH GENERATION & CLI ENTRY POINT
# ==============================================================================

def generate_all_assets(
    floor_path: str = DEFAULT_FLOOR_PATH,
    wall_path: str = DEFAULT_WALL_PATH,
    grass_path: str = DEFAULT_GRASS_PATH,
    rock_path: str = DEFAULT_ROCK_PATH,
    wall_cracked_path: str = DEFAULT_WALL_CRACKED_PATH,
    wall_mossy_path: str = DEFAULT_WALL_MOSSY_PATH,
    wall_webbed_path: str = DEFAULT_WALL_WEBBED_PATH,
    swamp_water_path: str = DEFAULT_SWAMP_WATER_PATH,
    mud_turf_path: str = DEFAULT_MUD_TURF_PATH,
    peat_bank_path: str = DEFAULT_PEAT_BANK_PATH,
    swamp_wall_path: str = DEFAULT_SWAMP_WALL_PATH,
    swamp_fungus_path: str = DEFAULT_SWAMP_FUNGUS_PATH,
    swamp_vent_path: str = DEFAULT_SWAMP_VENT_PATH,
    swamp_thorns_path: str = DEFAULT_SWAMP_THORNS_PATH,
    ruins_rubble_path: str = DEFAULT_RUINS_RUBBLE_PATH,
    swamp_flora_path: str = DEFAULT_SWAMP_FLORA_PATH,
    crypt_clutter_path: str = DEFAULT_CRYPT_CLUTTER_PATH,
    wall_top_cap_path: str = DEFAULT_WALL_TOP_CAP_PATH,
    wall_front_face_path: str = DEFAULT_WALL_FRONT_FACE_PATH,
    shadow_south_path: str = DEFAULT_SHADOW_SOUTH_PATH,
    shadow_east_path: str = DEFAULT_SHADOW_EAST_PATH,
    shadow_corner_path: str = DEFAULT_SHADOW_CORNER_PATH,
    cliff_edge_path: str = DEFAULT_CLIFF_EDGE_PATH,
    staircase_path: str = DEFAULT_STAIRCASE_PATH,
    pit_rim_path: str = DEFAULT_PIT_RIM_PATH,
    boss_dais_path: str = DEFAULT_BOSS_DAIS_PATH,
    boss_pillar_path: str = DEFAULT_BOSS_PILLAR_PATH,
    boss_abyss_rim_path: str = DEFAULT_BOSS_ABYSS_RIM_PATH,
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

    # 7. Reference-Driven Swamp Props
    # 7a. Bulbous fleshy toadstool / giant fungi
    _ensure_directory(swamp_fungus_path)
    swamp_fungus_surf = generate_swamp_fungus(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(swamp_fungus_surf, swamp_fungus_path)
    results["swamp_fungus"] = swamp_fungus_path

    # 7b. Raised organic gas vent / hive mound
    _ensure_directory(swamp_vent_path)
    swamp_vent_surf = generate_swamp_gas_vent(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(swamp_vent_surf, swamp_vent_path)
    results["swamp_gas_vent"] = swamp_vent_path

    # 7c. Skeletal thorns & briars
    _ensure_directory(swamp_thorns_path)
    swamp_thorns_surf = generate_swamp_thorns(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(swamp_thorns_surf, swamp_thorns_path)
    results["swamp_thorns"] = swamp_thorns_path

    # 8. Environmental Biome Clutter
    # 8a. Broken stone pillars / rubble piles
    _ensure_directory(ruins_rubble_path)
    ruins_rubble_surf = generate_ruins_rubble(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(ruins_rubble_surf, ruins_rubble_path)
    results["ruins_rubble"] = ruins_rubble_path

    # 8b. Glowing fungal clusters or reeds
    _ensure_directory(swamp_flora_path)
    swamp_flora_surf = generate_swamp_flora(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(swamp_flora_surf, swamp_flora_path)
    results["swamp_flora"] = swamp_flora_path

    # 8c. Scattered ancient scrolls / bone piles
    _ensure_directory(crypt_clutter_path)
    crypt_clutter_surf = generate_crypt_clutter(TILE_WIDTH, TILE_HEIGHT, rng=rng)
    pygame.image.save(crypt_clutter_surf, crypt_clutter_path)
    results["crypt_clutter"] = crypt_clutter_path

    # 9. 2.5D Verticality & Elevation Assets
    verticality_specs = [
        ("wall_top_cap", wall_top_cap_path, generate_wall_top_cap(TILE_WIDTH, TILE_HEIGHT, rng=rng)),
        ("wall_front_face", wall_front_face_path, generate_wall_front_face(TILE_WIDTH, TILE_HEIGHT, rng=rng)),
        ("shadow_south", shadow_south_path, generate_floor_shadow_overlay(TILE_WIDTH, TILE_HEIGHT, "south", rng=rng)),
        ("shadow_east", shadow_east_path, generate_floor_shadow_overlay(TILE_WIDTH, TILE_HEIGHT, "east", rng=rng)),
        (
            "shadow_corner",
            shadow_corner_path,
            generate_floor_shadow_overlay(TILE_WIDTH, TILE_HEIGHT, "corner", rng=rng),
        ),
        ("cliff_edge", cliff_edge_path, generate_cliff_edge_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)),
        ("staircase_tile", staircase_path, generate_staircase_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)),
        ("pit_rim", pit_rim_path, generate_pit_rim_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)),
        ("boss_dais_tile", boss_dais_path, generate_boss_dais_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)),
        ("boss_pillar_tile", boss_pillar_path, generate_boss_pillar_tile(TILE_WIDTH, TILE_HEIGHT, rng=rng)),
        ("boss_abyss_rim", boss_abyss_rim_path, generate_boss_abyss_rim(TILE_WIDTH, TILE_HEIGHT, rng=rng)),
    ]
    for key, out_path, surf in verticality_specs:
        _ensure_directory(out_path)
        pygame.image.save(surf, out_path)
        results[key] = out_path

    # Pipeline 11: Act 2 Empowered / Corrupted Procedural Enemy Variants
    empowered_specs = [
        ("bat_empowered", "bat", 40, 40),
        ("flutter_empowered", "flutter", 40, 40),
        ("bindling_empowered", "bindling", 40, 40),
        ("smear_empowered", "smear", 40, 40),
        ("sentry_empowered", "sentry", 40, 40),
        ("boss_empowered", "boss", 64, 64),
    ]
    for key, kind, w, h in empowered_specs:
        out_path = os.path.join("assets", "graphics", f"{key}.png")
        _ensure_directory(out_path)
        surf = generate_empowered_enemy_sprite(kind, w, h, rng=rng)
        pygame.image.save(surf, out_path)
        results[key] = out_path

    return results


def generate_empowered_enemy_sprite(
    kind: str,
    width: int = 40,
    height: int = 40,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a high-contrast Act 2 empowered enemy sprite with crimson/violet accents."""
    if rng is None:
        rng = random.Random(DEFAULT_SEED + hash(kind))

    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx, cy = width // 2, height // 2

    obsidian = (24, 18, 30, 255)
    charcoal = (44, 30, 52, 255)
    crimson = (210, 38, 68, 255)
    bright_crimson = (255, 92, 118, 255)
    eclipse_violet = (155, 65, 220, 255)
    edge_glow = (120, 28, 58, 200)

    if kind == "bat":
        pygame.draw.polygon(surf, charcoal, [(cx, cy), (2, 10), (8, cy + 4), (cx - 4, cy + 2)])
        pygame.draw.polygon(surf, charcoal, [(cx, cy), (width - 3, 10), (width - 9, cy + 4), (cx + 4, cy + 2)])
        pygame.draw.line(surf, crimson, (cx, cy), (3, 11), 2)
        pygame.draw.line(surf, crimson, (cx, cy), (width - 4, 11), 2)
        pygame.draw.circle(surf, obsidian, (cx, cy), max(6, width // 4))
        pygame.draw.circle(surf, edge_glow, (cx, cy), max(6, width // 4), 1)
        pygame.draw.circle(surf, bright_crimson, (cx - 3, cy - 2), 2)
        pygame.draw.circle(surf, bright_crimson, (cx + 3, cy - 2), 2)
    elif kind == "flutter":
        pygame.draw.polygon(surf, charcoal, [(cx - 4, cy), (3, 6), (6, height - 8)])
        pygame.draw.polygon(surf, charcoal, [(cx + 4, cy), (width - 4, 6), (width - 7, height - 8)])
        core = pygame.Rect(cx - width // 5, cy - height // 5, width * 2 // 5, height * 2 // 5)
        pygame.draw.rect(surf, obsidian, core, border_radius=3)
        pygame.draw.rect(surf, crimson, core, 2, border_radius=3)
        pygame.draw.circle(surf, eclipse_violet, (cx - 10, 8), 2)
        pygame.draw.circle(surf, bright_crimson, (cx + 10, height - 9), 2)
    elif kind == "bindling":
        body = pygame.Rect(6, 5, width - 12, height - 10)
        pygame.draw.rect(surf, obsidian, body, border_radius=6)
        pygame.draw.rect(surf, eclipse_violet, body, 2, border_radius=6)
        hood = pygame.Rect(8, 4, width - 16, height // 3)
        pygame.draw.rect(surf, charcoal, hood, border_radius=4)
        pygame.draw.line(surf, crimson, (10, 14), (width - 11, height - 10), 2)
        pygame.draw.circle(surf, bright_crimson, (cx - 3, cy + 2), 2)
        pygame.draw.circle(surf, bright_crimson, (cx + 3, cy + 2), 2)
    elif kind == "smear":
        pygame.draw.circle(surf, obsidian, (cx, cy), width // 3)
        for ang_idx in range(4):
            ang = ang_idx * (math.pi / 2.0) + 0.4
            lx = cx + int(math.cos(ang) * (width * 0.22))
            ly = cy + int(math.sin(ang) * (height * 0.22))
            pygame.draw.circle(surf, charcoal, (lx, ly), width // 5)
        pygame.draw.circle(surf, eclipse_violet, (cx, cy), width // 3, 1)
        pygame.draw.circle(surf, bright_crimson, (cx + 4, cy - 2), 4)
    elif kind == "sentry":
        for ang_idx in range(4):
            ang = ang_idx * (math.pi / 2.0) + (math.pi / 4.0)
            fx = cx + int(math.cos(ang) * (width * 0.42))
            fy = cy + int(math.sin(ang) * (height * 0.42))
            pygame.draw.line(surf, crimson, (cx, cy), (fx, fy), 3)
            pygame.draw.circle(surf, bright_crimson, (fx, fy), 3)
        core = pygame.Rect(7, 7, width - 14, height - 14)
        pygame.draw.rect(surf, obsidian, core, border_radius=7)
        pygame.draw.circle(surf, eclipse_violet, (cx, cy), width // 3, 2)
        pygame.draw.circle(surf, bright_crimson, (cx + 4, cy), 4)
    else:  # boss (Miniboss / Night Boss / Final Author)
        pauldron_r = max(8, width // 4)
        pygame.draw.circle(surf, charcoal, (10, cy - height // 8), pauldron_r)
        pygame.draw.circle(surf, charcoal, (width - 10, cy - height // 8), pauldron_r)
        pygame.draw.circle(surf, crimson, (10, cy - height // 8), pauldron_r, 2)
        pygame.draw.circle(surf, crimson, (width - 10, cy - height // 8), pauldron_r, 2)
        torso = pygame.Rect(8, 6, width - 16, height - 12)
        pygame.draw.rect(surf, obsidian, torso, border_radius=10)
        pygame.draw.rect(surf, eclipse_violet, torso, 2, border_radius=10)
        visor = pygame.Rect(cx - width // 4, 14, width // 2, max(8, height // 6))
        pygame.draw.rect(surf, (12, 8, 18, 255), visor, border_radius=3)
        pygame.draw.circle(surf, bright_crimson, (cx, visor.centery), max(4, width // 12))

    # Subtle dark-fantasy grit speckles inside opaque pixels
    for _ in range((width * height) // 16):
        gx = rng.randrange(0, width)
        gy = rng.randrange(0, height)
        col = surf.get_at((gx, gy))
        if col.a > 180:
            delta = rng.randint(-12, 12)
            surf.set_at(
                (gx, gy),
                (
                    max(0, min(255, col.r + delta)),
                    max(0, min(255, col.g + delta // 2)),
                    max(0, min(255, col.b + delta)),
                    col.a,
                ),
            )
    return surf


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
