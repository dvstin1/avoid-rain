#!/usr/bin/env python3
# copyright 2026 Dustin Massop, License: GPLv2
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
import zlib
from pathlib import Path
from typing import Dict, List, Set, Tuple
import pygame

import constants

DEFAULT_ASSET_SEED = 42

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
DEFAULT_CHRONICLE_PATH = os.path.join("assets", "graphics", "chronicle.png")
DEFAULT_RESPITE_PATH = os.path.join("assets", "graphics", "respite.png")
DEFAULT_RESPITE_CORRUPTED_PATH = os.path.join("assets", "graphics", "respite_corrupted.png")
DEFAULT_CHRONICLER_PATH = os.path.join("assets", "graphics", "chronicler.png")
DEFAULT_BINDER_PATH = os.path.join("assets", "graphics", "binder.png")
DEFAULT_SWAMP_FUNGUS_PATH = os.path.join("assets", "graphics", "swamp_fungus.png")
DEFAULT_SWAMP_VENT_PATH = os.path.join("assets", "graphics", "swamp_gas_vent.png")
DEFAULT_SWAMP_THORNS_PATH = os.path.join("assets", "graphics", "swamp_thorns.png")
DEFAULT_RUINS_RUBBLE_PATH = os.path.join("assets", "graphics", "ruins_rubble.png")
DEFAULT_SWAMP_FLORA_PATH = os.path.join("assets", "graphics", "swamp_flora.png")
DEFAULT_CRYPT_CLUTTER_PATH = os.path.join("assets", "graphics", "crypt_clutter.png")

# Pass 2 Expanded Biome Asset Paths (The Vitreous Basin & The Sunlit Aqueducts)
DEFAULT_VITREOUS_SALT_FLOOR_PATH = os.path.join("assets", "graphics", "vitreous_salt_floor.png")
DEFAULT_VITREOUS_GLASS_FLAT_PATH = os.path.join("assets", "graphics", "vitreous_glass_flat.png")
DEFAULT_VITREOUS_SALT_SPIRE_PATH = os.path.join("assets", "graphics", "vitreous_salt_spire.png")
DEFAULT_VITREOUS_FIRE_CHALICE_PATH = os.path.join("assets", "graphics", "vitreous_fire_chalice.png")
DEFAULT_AQUEDUCT_TERRACOTTA_FLOOR_PATH = os.path.join("assets", "graphics", "aqueduct_terracotta_floor.png")
DEFAULT_AQUEDUCT_MOSS_WALL_PATH = os.path.join("assets", "graphics", "aqueduct_moss_wall.png")
DEFAULT_AQUEDUCT_PILLAR_PATH = os.path.join("assets", "graphics", "aqueduct_pillar.png")

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

# Legacy Prop & Landmark Asset Paths
DEFAULT_WELLSPRING_PATH = os.path.join("assets", "graphics", "wellspring.png")
DEFAULT_LOTUS_FRAME_PATH = os.path.join("assets", "graphics", "lotus_frame.png")
DEFAULT_BENCH_PATH = os.path.join("assets", "graphics", "bench.png")
DEFAULT_BENCH_NORTH_PATH = os.path.join("assets", "graphics", "bench_north.png")
DEFAULT_BENCH_EAST_PATH = os.path.join("assets", "graphics", "bench_east.png")
DEFAULT_BENCH_WEST_PATH = os.path.join("assets", "graphics", "bench_west.png")
DEFAULT_HEAVY_BOOKCASE_PATH = os.path.join("assets", "graphics", "heavy_bookcase.png")
DEFAULT_INK_URN_PATH = os.path.join("assets", "graphics", "ink_urn.png")
DEFAULT_INKWELL_PUDDLE_PATH = os.path.join("assets", "graphics", "inkwell_puddle.png")
DEFAULT_CANDELABRA_PATH = os.path.join("assets", "graphics", "candelabra.png")
DEFAULT_TREE_STRUCTURE_PATH = os.path.join("assets", "graphics", "tree_structure.png")

# Act 1 / Un-Empowered Base Enemy & Boss Asset Paths
DEFAULT_BAT_PATH = os.path.join("assets", "graphics", "bat.png")
DEFAULT_FLUTTER_PATH = os.path.join("assets", "graphics", "flutter.png")
DEFAULT_BINDLING_PATH = os.path.join("assets", "graphics", "bindling.png")
DEFAULT_SMEAR_PATH = os.path.join("assets", "graphics", "smear.png")
DEFAULT_SENTRY_PATH = os.path.join("assets", "graphics", "sentry.png")
DEFAULT_PUNCTUATION_WOLF_PATH = os.path.join("assets", "graphics", "punctuation_wolf.png")
DEFAULT_EVENT_CHAMPION_PATH = os.path.join("assets", "graphics", "event_champion.png")
DEFAULT_MINIBOSS_PATH = os.path.join("assets", "graphics", "miniboss.png")
DEFAULT_NIGHT_BOSS_PATH = os.path.join("assets", "graphics", "night_boss.png")
DEFAULT_FINAL_AUTHOR_PATH = os.path.join("assets", "graphics", "final_author.png")
DEFAULT_TORN_PAGE_PATH = os.path.join("assets", "graphics", "torn_page.png")

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
    (0, 0.12),  # Outermost perimeter pixel (12% darker for soft flat tiling)
    (1, 0.06),  # 1px inward (6% darker)
    (2, 0.03),  # 2px inward (3% darker)
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
# GENERATIVE PIPELINE 8B: VITREOUS BASIN & SUNLIT AQUEDUCTS BIOME ASSETS
# ==============================================================================

def generate_vitreous_salt_floor_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x40 sun-baked ochre/amber salt-crust floor tile for The Vitreous Basin."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_rgb = (204, 154, 92)
    crest_rgb = (242, 202, 134)
    seam_rgb = (158, 106, 66)

    for y in range(height):
        for x in range(width):
            jit = rng.randint(-6, 6)
            edge_dist = min(x, y, width - 1 - x, height - 1 - y)
            shade = -8 if edge_dist == 0 else (-4 if edge_dist == 1 else 0)
            surface.set_at(
                (x, y),
                (
                    _clamp(base_rgb[0] + jit + shade),
                    _clamp(base_rgb[1] + jit + shade),
                    _clamp(base_rgb[2] + jit // 2 + shade // 2),
                ),
            )

    # Polygonal sun-baked salt-flat crust seams & warm amber-ochre raised ridges
    crust_lines = [
        ((0, 14), (16, 10), (30, 18), (width - 1, 13)),
        ((12, 0), (16, 10), (14, 28), (19, height - 1)),
        ((28, 18), (24, 30), (36, height - 1)),
    ]
    for poly in crust_lines:
        for i in range(len(poly) - 1):
            p1, p2 = poly[i], poly[i + 1]
            pygame.draw.line(surface, seam_rgb, p1, p2, 1)
            pygame.draw.line(surface, crest_rgb, (p1[0], max(0, p1[1] - 1)), (p2[0], max(0, p2[1] - 1)), 1)

    for _ in range(26):
        sx = rng.randint(2, width - 3)
        sy = rng.randint(2, height - 3)
        surface.set_at((sx, sy), (250, 218, 142) if rng.random() < 0.6 else (158, 96, 54))

    return surface


def generate_vitreous_glass_flat_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x40 kiln-fused amber/terracotta glass flat tile for The Vitreous Basin."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    base_rgb = (158, 92, 54)
    for y in range(height):
        diag_band = int(12 * math.sin((x_band := y) * 0.14))
        for x in range(width):
            sheen = 18 if 8 <= (x + x_band) % 24 <= 12 else 0
            jit = rng.randint(-4, 4)
            surface.set_at(
                (x, y),
                (
                    _clamp(base_rgb[0] + sheen + jit + 6),
                    _clamp(base_rgb[1] + sheen + jit + diag_band // 3),
                    _clamp(base_rgb[2] + sheen // 2 + jit),
                ),
            )

    # Diagonal golden heat-glint streaks & dark terracotta glass fracture web
    pygame.draw.line(surface, (248, 194, 108), (4, 32), (24, 12), 2)
    pygame.draw.line(surface, (255, 226, 152), (18, 35), (36, 17), 1)
    fractures = [
        ((0, 22), (18, 18), (39, 8)),
        ((18, 18), (22, 34), (35, 39)),
        ((18, 18), (10, 3)),
    ]
    for path in fractures:
        for i in range(len(path) - 1):
            p1, p2 = path[i], path[i + 1]
            pygame.draw.line(surface, (116, 68, 42), p1, p2, 1)
            pygame.draw.line(surface, (236, 176, 98), (p1[0] + 1, p1[1]), (p2[0] + 1, p2[1]), 1)

    return surface


def generate_vitreous_salt_spire(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x40 transparent jagged amber-quartz salt-spire & vitrified glass cluster."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(surface, (66, 34, 18, 130), (4, height - 12, width - 8, 9))

    shards = [
        ([(8, 32), (12, 14), (18, 31)], (184, 112, 58, 255), (242, 192, 116, 255)),
        ([(24, 33), (29, 12), (34, 32)], (166, 96, 48, 255), (234, 178, 102, 255)),
        ([(14, 34), (20, 4), (27, 34)], (212, 144, 72, 255), (252, 218, 144, 255)),
    ]
    for poly, body_col, hi_col in shards:
        pygame.draw.polygon(surface, body_col, poly)
        apex = poly[1]
        left_pt = poly[0]
        pygame.draw.polygon(surface, hi_col, [left_pt, apex, (apex[0] + 1, poly[2][1] - 2)])
        pygame.draw.polygon(surface, (78, 40, 22, 255), poly, 1)

    for _ in range(10):
        gx = rng.randint(10, 30)
        gy = rng.randint(14, 34)
        if surface.get_at((gx, gy)).a > 120:
            surface.set_at((gx, gy), (255, 232, 168, 255))

    return surface


def generate_vitreous_fire_chalice(
    width: int = 80,
    height: int = 80,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate an 80x80 SRCALPHA blazing bronze-and-terracotta fire chalice for The Vitreous Basin."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2

    # 1. Warm scorched ground shadow ellipse
    pygame.draw.ellipse(surface, (52, 24, 12, 140), (10, height - 16, width - 20, 14))

    # 2. Stepped kiln-terracotta & hammered-bronze pedestal base
    pygame.draw.rect(surface, (86, 44, 24, 255), (16, 64, 48, 10), border_radius=3)
    pygame.draw.rect(surface, (148, 84, 46, 255), (18, 65, 44, 6), border_radius=2)
    pygame.draw.rect(surface, (186, 118, 66, 255), (20, 65, 40, 2))
    pygame.draw.rect(surface, (96, 52, 28, 255), (24, 57, 32, 8), border_radius=2)
    pygame.draw.rect(surface, (168, 102, 54, 255), (26, 58, 28, 4))

    # 3. Fluted bronze stem with gilded collar band
    pygame.draw.rect(surface, (82, 46, 26, 255), (cx - 10, 46, 20, 13))
    pygame.draw.rect(surface, (142, 84, 46, 255), (cx - 7, 46, 14, 13))
    pygame.draw.rect(surface, (204, 142, 74, 255), (cx - 4, 46, 5, 13))
    pygame.draw.rect(surface, (236, 186, 92, 255), (cx - 11, 51, 22, 3), border_radius=1)

    # 4. Wide hammered-bronze brazier bowl with dark obsidian ribs & gilded rivets
    bowl_outer = [(12, 32), (68, 32), (60, 47), (20, 47)]
    bowl_inner = [(16, 33), (64, 33), (57, 45), (23, 45)]
    pygame.draw.polygon(surface, (68, 36, 20, 255), bowl_outer)
    pygame.draw.polygon(surface, (152, 88, 44, 255), bowl_inner)
    pygame.draw.polygon(surface, (206, 136, 68, 255), [(18, 34), (42, 34), (38, 44), (24, 44)])
    pygame.draw.polygon(surface, (58, 28, 16, 255), bowl_outer, 2)
    # Ornate rim lip & side handles
    pygame.draw.rect(surface, (218, 158, 76, 255), (10, 29, 60, 5), border_radius=2)
    pygame.draw.rect(surface, (82, 42, 22, 255), (10, 29, 60, 5), 1, border_radius=2)
    pygame.draw.arc(surface, (192, 128, 62, 255), (6, 33, 12, 13), math.pi * 0.5, math.pi * 1.5, 3)
    pygame.draw.arc(surface, (192, 128, 62, 255), (62, 33, 12, 13), -math.pi * 0.5, math.pi * 0.5, 3)
    for rx in (22, 31, 40, 49, 58):
        pygame.draw.circle(surface, (250, 212, 122, 255), (rx, 39), 2)

    # 5. Glowing ember coal bed inside the rim
    pygame.draw.ellipse(surface, (196, 48, 18, 255), (15, 25, 50, 9))
    pygame.draw.ellipse(surface, (255, 134, 30, 255), (20, 26, 40, 7))
    pygame.draw.ellipse(surface, (255, 216, 86, 255), (26, 27, 28, 5))

    # 6. Multi-layered roaring flame plume
    outer_flame = [
        (18, 29), (16, 20), (24, 22), (26, 11), (34, 18),
        (cx, 4), (47, 17), (54, 10), (57, 21), (64, 19), (62, 29),
    ]
    mid_flame = [
        (22, 29), (22, 21), (29, 23), (31, 14), (37, 20),
        (cx, 9), (44, 19), (50, 14), (53, 22), (58, 29),
    ]
    core_flame = [
        (28, 29), (30, 21), (36, 22), (cx, 14), (44, 22), (50, 21), (52, 29),
    ]
    heart_flame = [(33, 29), (36, 23), (cx, 19), (44, 23), (47, 29)]

    pygame.draw.polygon(surface, (232, 66, 22, 245), outer_flame)
    pygame.draw.polygon(surface, (255, 146, 34, 250), mid_flame)
    pygame.draw.polygon(surface, (255, 222, 88, 255), core_flame)
    pygame.draw.polygon(surface, (255, 248, 196, 255), heart_flame)

    # 7. Rising ember sparks floating above the flame crown
    for _ in range(12):
        ex = rng.randint(16, width - 17)
        ey = rng.randint(2, 20)
        rad = 1 if rng.random() < 0.7 else 2
        col = (255, 214, 96, 240) if rng.random() < 0.6 else (255, 116, 36, 230)
        pygame.draw.circle(surface, col, (ex, ey), rad)

    return surface


def generate_aqueduct_terracotta_floor_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x40 sun-bleached terracotta flagstone floor tile for The Sunlit Aqueducts."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    mortar_rgb = (134, 84, 58)
    surface.fill(mortar_rgb)

    slabs = [
        (1, 1, 18, 18, (186, 126, 86)),
        (21, 1, 18, 18, (172, 112, 74)),
        (1, 21, 12, 18, (168, 108, 72)),
        (15, 21, 24, 18, (194, 134, 92)),
    ]
    for sx, sy, sw, sh, tone in slabs:
        pygame.draw.rect(surface, tone, (sx, sy, sw, sh))
        for py in range(sy, sy + sh):
            for px in range(sx, sx + sw):
                jit = rng.randint(-7, 7)
                surface.set_at(
                    (px, py),
                    (_clamp(tone[0] + jit), _clamp(tone[1] + jit), _clamp(tone[2] + jit)),
                )
        pygame.draw.line(surface, (208, 154, 110), (sx, sy), (sx + sw - 1, sy), 1)
        pygame.draw.line(surface, (144, 92, 64), (sx, sy + sh - 1), (sx + sw - 1, sy + sh - 1), 1)

    # Sun-baked mineral chips & creeping seam moss tufts
    for mx, my in ((19, 19), (20, 18), (14, 21), (13, 35)):
        pygame.draw.circle(surface, (84, 168, 86), (mx, my), 2)
        surface.set_at((mx, max(0, my - 1)), (128, 216, 116))

    return surface


def generate_aqueduct_moss_wall_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x40 moss-draped stone wall / aqueduct channel tile."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height))
    mortar_rgb = (54, 32, 24)
    surface.fill(mortar_rgb)

    # Upper aqueduct cornice & sun-bleached stone courses
    courses = [(0, 12), (13, 13), (27, 13)]
    for c_idx, (cy, ch) in enumerate(courses):
        offset = 10 if c_idx == 1 else 0
        for bx in range(-offset, width, 20):
            x0 = max(0, bx + 1)
            x1 = min(width, bx + 19)
            if x1 <= x0:
                continue
            tone = (188, 132, 90) if c_idx == 0 else (142, 88, 58)
            for py in range(cy, min(height - 1, cy + ch - 1)):
                for px in range(x0, x1):
                    jit = rng.randint(-6, 6)
                    surface.set_at(
                        (px, py),
                        (_clamp(tone[0] + jit), _clamp(tone[1] + jit), _clamp(tone[2] + jit)),
                    )
            pygame.draw.line(surface, (232, 184, 136), (x0, cy), (x1 - 1, cy), 1)

    # Recessed aqueduct water trickle channel & trailing sunlit moss clusters
    pygame.draw.rect(surface, (46, 118, 134), (16, 15, 8, 22))
    pygame.draw.line(surface, (112, 206, 218), (19, 16), (19, 36), 2)
    for mx, my, mr in ((7, 11, 4), (11, 14, 3), (30, 10, 4), (32, 16, 3), (26, 26, 3)):
        pygame.draw.circle(surface, (68, 148, 72), (mx, my), mr)
        pygame.draw.circle(surface, (124, 214, 110), (mx - 1, my - 1), max(1, mr - 2))

    return surface


def generate_aqueduct_pillar(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x40 transparent cracked aqueduct pillar / overgrown arch obstacle."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(surface, (38, 22, 16, 125), (5, height - 11, width - 10, 9))

    # Stepped terracotta stone plinth & cracked arch crown
    pygame.draw.rect(surface, (132, 82, 54, 255), (9, 27, 22, 8), border_radius=2)
    pygame.draw.rect(surface, (176, 118, 82, 255), (12, 11, 16, 18), border_radius=2)
    pygame.draw.rect(surface, (214, 158, 114, 255), (8, 7, 24, 6), border_radius=2)
    # Fluting & sunlit bevel
    for fx in (15, 20, 25):
        pygame.draw.line(surface, (114, 68, 44, 255), (fx, 13), (fx, 27), 1)
    pygame.draw.line(surface, (238, 198, 152, 255), (9, 7), (30, 7), 1)
    # Jagged crack across shaft
    pygame.draw.lines(surface, (54, 32, 24, 255), False, [(13, 14), (19, 18), (17, 24), (24, 29)], 2)
    # Overgrown moss drape along cornice and plinth
    for mx, my, mr in ((10, 9, 4), (14, 12, 3), (27, 26, 4), (11, 29, 3)):
        pygame.draw.circle(surface, (72, 156, 76, 255), (mx, my), mr)
        pygame.draw.circle(surface, (132, 222, 118, 255), (mx - 1, my - 1), max(1, mr - 2))

    # Subtle weathered stone speckles
    for _ in range(8):
        px = rng.randint(12, 27)
        py = rng.randint(12, 27)
        if surface.get_at((px, py)).a > 200:
            surface.set_at((px, py), (154, 98, 66, 255))

    return surface


def generate_binder(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x40 sprite for The Binder artisan NPC (robed bookbinder with gold needles & spools)."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2

    # 1. Ground shadow
    pygame.draw.ellipse(surface, (14, 10, 18, 125), (8, height - 10, width - 16, 7))

    # 2. Crimson-trimmed binding cloak & parchment apron
    cloak_poly = [(cx - 11, 33), (cx - 8, 14), (cx + 8, 14), (cx + 11, 33)]
    pygame.draw.polygon(surface, (62, 32, 46, 255), cloak_poly)
    pygame.draw.polygon(surface, (164, 52, 74, 255), cloak_poly, 1)
    pygame.draw.rect(surface, (206, 188, 148, 255), (cx - 5, 18, 10, 14), border_radius=2)

    # 3. Crossed golden stitching thread across apron
    pygame.draw.line(surface, (238, 198, 96, 255), (cx - 5, 20), (cx + 4, 30), 1)
    pygame.draw.line(surface, (238, 198, 96, 255), (cx + 4, 20), (cx - 5, 30), 1)

    # 4. Hooded artisan cowl & spectacles
    pygame.draw.circle(surface, (78, 42, 58, 255), (cx, 11), 7)
    pygame.draw.circle(surface, (26, 18, 28, 255), (cx, 12), 4)
    pygame.draw.circle(surface, (245, 212, 118, 255), (cx - 2, 12), 1)
    pygame.draw.circle(surface, (245, 212, 118, 255), (cx + 2, 12), 1)

    # 5. Long brass bookbinding needle & trailing crimson thread
    pygame.draw.line(surface, (242, 214, 124, 255), (cx + 9, 28), (cx + 14, 8), 2)
    pygame.draw.line(surface, (218, 58, 84, 255), (cx + 14, 8), (cx + 6, 16), 1)

    for _ in range(8):
        px = rng.randint(cx - 8, cx + 8)
        py = rng.randint(15, 32)
        col = surface.get_at((px, py))
        if col.a > 200:
            jit = rng.randint(-6, 6)
            surface.set_at((px, py), (_clamp(col.r + jit), _clamp(col.g + jit), _clamp(col.b + jit), 255))

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


def generate_chronicle(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Procedurally generate a 40x40 ornate lectern holding an open gilded magical tome."""
    if rng is None:
        rng = random.Random()

    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1. Ground drop shadow under lectern base
    shadow = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (10, 10, 14, 150), (6, 31, 28, 7))
    surface.blit(shadow, (0, 0))

    # 2. Carved dark-oak / stone lectern base & column
    pygame.draw.rect(surface, (42, 30, 24, 255), (10, 30, 20, 6), border_radius=1)
    pygame.draw.line(surface, (86, 62, 46, 255), (10, 30), (29, 30), 1)
    pygame.draw.rect(surface, (52, 36, 28, 255), (15, 20, 10, 11))
    pygame.draw.line(surface, (82, 58, 44, 255), (15, 20), (15, 30), 1)
    # Angled reading desk top
    pygame.draw.rect(surface, (62, 42, 30, 255), (6, 13, 28, 10), border_radius=2)
    pygame.draw.rect(surface, (36, 24, 18, 255), (6, 13, 28, 10), 1, border_radius=2)

    # 3. Open gilded magical tome resting on the lectern
    # Gilded brass/gold cover & trim
    pygame.draw.rect(surface, (168, 128, 48, 255), (7, 8, 26, 14), border_radius=2)
    pygame.draw.rect(surface, (218, 178, 78, 255), (7, 8, 26, 14), 1, border_radius=2)
    # Left & right parchment pages
    for rx, rw in ((9, 10), (21, 10)):
        for py in range(10, 20):
            for px in range(rx, rx + rw):
                jit = rng.randint(-6, 6)
                surface.set_at((px, py), (_clamp(226 + jit), _clamp(214 + jit), _clamp(186 + jit), 255))
    # Center spine crease
    pygame.draw.line(surface, (92, 68, 42, 255), (19, 9), (19, 20), 1)
    pygame.draw.line(surface, (124, 92, 52, 255), (20, 9), (20, 20), 1)

    # 4. Glowing cyan ink runes & arcane aura motes
    glow = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (0, 225, 255, 55), (8, 6, 24, 16))
    pygame.draw.ellipse(glow, (0, 245, 255, 110), (11, 9, 18, 10))
    surface.blit(glow, (0, 0))

    # Crisp arcane script lines on both pages
    for lx in (11, 13, 15, 23, 25, 27):
        surface.set_at((lx, 12), (0, 220, 245, 255))
        surface.set_at((lx + 1, 15), (40, 245, 255, 255))
    surface.set_at((14, 17), (190, 255, 255, 255))
    surface.set_at((25, 17), (190, 255, 255, 255))
    for mx, my in ((13, 5), (26, 6), (20, 4)):
        surface.set_at((mx, my), (120, 250, 255, rng.randint(150, 220)))

    return surface


# ==============================================================================
# BATCH GENERATION & CLI ENTRY POINT
# ==============================================================================

def generate_respite(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
    corrupted: bool = False,
) -> pygame.Surface:
    """Generate The Respite ('First Edition' anchor plinth) in safe or rain-corrupted state."""
    if rng is None:
        rng = random.Random(431 if not corrupted else 432)

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    cx, cy = width // 2, height // 2

    # Grounded plinth shadow
    pygame.draw.ellipse(surface, (12, 12, 18, 130), (3, height - 10, width - 6, 8))

    # Carved weathered marble/slate stepped pedestal
    base_rect = pygame.Rect(4, 7, width - 8, height - 12)
    pygame.draw.rect(surface, (52, 56, 66, 255), base_rect, border_radius=3)
    pygame.draw.rect(surface, (82, 88, 100, 255), base_rect, 1, border_radius=3)

    top_rect = pygame.Rect(7, 9, width - 14, height - 18)
    slab_col = (148, 152, 160, 255) if not corrupted else (88, 90, 98, 255)
    pygame.draw.rect(surface, slab_col, top_rect, border_radius=2)
    # Beveled stone highlight & lower shadow
    pygame.draw.line(surface, (192, 196, 204, 255) if not corrupted else (118, 120, 128, 255),
                     (top_rect.left + 1, top_rect.top), (top_rect.right - 2, top_rect.top))
    pygame.draw.line(surface, (66, 70, 80, 255),
                     (top_rect.left + 1, top_rect.bottom), (top_rect.right - 2, top_rect.bottom))

    # Subtle weathered stone grain
    for _ in range(14):
        gx = rng.randint(top_rect.left + 2, top_rect.right - 3)
        gy = rng.randint(top_rect.top + 2, top_rect.bottom - 3)
        delta = rng.randint(-14, 10)
        c_val = max(40, min(210, slab_col[0] + delta))
        surface.set_at((gx, gy), (c_val, c_val + 2, c_val + 6, 255))

    # Inlaid gold/brass corner brackets
    brass = (212, 174, 86, 255) if not corrupted else (120, 96, 52, 255)
    brass_dark = (132, 102, 42, 255) if not corrupted else (70, 56, 30, 255)
    corners = [
        (top_rect.left, top_rect.top, 1, 1),
        (top_rect.right - 1, top_rect.top, -1, 1),
        (top_rect.left, top_rect.bottom - 1, 1, -1),
        (top_rect.right - 1, top_rect.bottom - 1, -1, -1),
    ]
    for bx, by, dx, dy in corners:
        pygame.draw.line(surface, brass, (bx, by), (bx + 4 * dx, by))
        pygame.draw.line(surface, brass, (bx, by), (bx, by + 4 * dy))
        surface.set_at((bx + dx, by + dy), brass_dark)

    # Open carved manuscript / bookmark relief at core
    book_rect = pygame.Rect(cx - 8, cy - 7, 16, 12)
    pygame.draw.rect(surface, (62, 66, 76, 255), book_rect.inflate(2, 2), border_radius=1)
    page_col = (218, 212, 196, 255) if not corrupted else (98, 96, 94, 255)
    pygame.draw.rect(surface, page_col, book_rect)
    pygame.draw.line(surface, (110, 106, 100, 255), (cx, book_rect.top), (cx, book_rect.bottom - 1))
    # Bookmark ribbon extending downward
    ribbon_col = (196, 62, 68, 255) if not corrupted else (54, 24, 30, 255)
    pygame.draw.line(surface, ribbon_col, (cx, book_rect.bottom), (cx, book_rect.bottom + 3), 2)

    if not corrupted:
        # Luminous cyan ink-glyph runes etched into the stone and pages
        rune_glow = (60, 235, 255, 110)
        rune_core = (150, 250, 255, 255)
        for rx, ry in [(cx - 5, cy - 4), (cx - 4, cy - 1), (cx + 3, cy - 4), (cx + 4, cy - 1)]:
            pygame.draw.line(surface, rune_glow, (rx - 1, ry), (rx + 2, ry), 2)
            pygame.draw.line(surface, rune_core, (rx, ry), (rx + 2, ry))
        for rx, ry in [(top_rect.left + 3, cy), (top_rect.right - 4, cy), (cx, top_rect.top + 2)]:
            pygame.draw.circle(surface, rune_glow, (rx, ry), 2)
            surface.set_at((rx, ry), rune_core)
    else:
        # Smothered under glossy, dripping black liquid ink pools
        ink_dark = (14, 14, 20, 245)
        ink_edge = (28, 30, 42, 230)
        ink_shine = (88, 96, 122, 210)
        pygame.draw.ellipse(surface, ink_dark, (cx - 10, cy - 6, 20, 13))
        pygame.draw.ellipse(surface, ink_edge, (cx - 11, cy - 3, 9, 8))
        pygame.draw.ellipse(surface, ink_dark, (cx + 2, cy - 8, 9, 9))
        # Dripping ink tendrils over the plinth's lower lip
        for dx, drip_len in [(-6, 7), (-1, 9), (5, 6)]:
            pygame.draw.line(surface, ink_dark, (cx + dx, cy + 4), (cx + dx, cy + 4 + drip_len), 2)
            surface.set_at((cx + dx, cy + 4 + drip_len), ink_edge)
        # Glossy specular highlights on liquid ink
        pygame.draw.line(surface, ink_shine, (cx - 6, cy - 3), (cx - 2, cy - 4))
        pygame.draw.line(surface, ink_shine, (cx + 4, cy - 5), (cx + 7, cy - 5))

    return surface


def generate_chronicler(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate The Chronicler top-down / 2.5D scholar sprite."""
    if rng is None:
        rng = random.Random(433)

    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2

    # Grounded shadow
    pygame.draw.ellipse(surface, (10, 10, 16, 135), (7, height - 10, width - 14, 7))

    # Layered pale parchment-ivory scholar robes with ink-stained lower hem
    robe_outer = (196, 186, 164, 255)
    robe_inner = (224, 216, 196, 255)
    ink_hem = (46, 48, 62, 240)
    robe_poly = [(cx - 9, 17), (cx + 9, 17), (cx + 12, height - 7), (cx - 12, height - 7)]
    pygame.draw.polygon(surface, robe_outer, robe_poly)
    pygame.draw.polygon(surface, robe_inner, [(cx - 6, 18), (cx + 6, 18), (cx + 8, height - 9), (cx - 8, height - 9)])
    pygame.draw.line(surface, ink_hem, (cx - 11, height - 8), (cx + 11, height - 8), 2)
    for _ in range(6):
        sx = rng.randint(cx - 10, cx + 10)
        sy = rng.randint(height - 11, height - 8)
        surface.set_at((sx, sy), ink_hem)

    # Draped archival stole/scarf with gold trim
    stole_col = (58, 72, 98, 255)
    gold_trim = (218, 178, 84, 255)
    pygame.draw.rect(surface, stole_col, (cx - 5, 16, 3, 14))
    pygame.draw.rect(surface, stole_col, (cx + 2, 16, 3, 14))
    pygame.draw.line(surface, gold_trim, (cx - 5, 16), (cx - 5, 29))
    pygame.draw.line(surface, gold_trim, (cx + 4, 16), (cx + 4, 29))
    pygame.draw.line(surface, gold_trim, (cx - 5, 29), (cx - 3, 29))
    pygame.draw.line(surface, gold_trim, (cx + 2, 29), (cx + 4, 29))

    # Heavy bound ledger & quill tucked at right side
    ledger_rect = pygame.Rect(cx + 6, 20, 6, 9)
    pygame.draw.rect(surface, (108, 64, 42, 255), ledger_rect, border_radius=1)
    pygame.draw.rect(surface, gold_trim, ledger_rect, 1, border_radius=1)
    pygame.draw.line(surface, (238, 232, 214, 255), (cx + 10, 21), (cx + 13, 15))

    # Lantern-lit glow near left hand
    pygame.draw.circle(surface, (255, 205, 110, 75), (cx - 9, 23), 6)
    pygame.draw.rect(surface, (255, 218, 128, 255), (cx - 10, 22, 3, 4))

    # Shadowed hood framing a warm lantern-lit visage
    hood_outer = (158, 148, 128, 255)
    hood_shadow = (44, 40, 48, 255)
    pygame.draw.ellipse(surface, hood_outer, (cx - 8, 5, 16, 15))
    pygame.draw.ellipse(surface, hood_shadow, (cx - 5, 8, 10, 10))
    # Warm lantern-lit face & subtle eyes
    pygame.draw.ellipse(surface, (232, 192, 150, 255), (cx - 4, 10, 8, 7))
    surface.set_at((cx - 2, 12), (48, 38, 34, 255))
    surface.set_at((cx + 1, 12), (48, 38, 34, 255))
    # Hood rim highlight
    pygame.draw.arc(surface, (226, 218, 198, 255), (cx - 8, 5, 16, 14), 0.35, 2.8, 1)

    return surface


def generate_wellspring(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 ornate stone/ink ritual basin with a glowing cyan runic water core."""
    if rng is None:
        rng = _asset_rng(DEFAULT_ASSET_SEED, "wellspring")
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    # Outer shadow & carved slate rim
    pygame.draw.rect(surface, (18, 20, 28, 180), (2, 3, width - 3, height - 3), border_radius=6)
    pygame.draw.rect(surface, (58, 64, 78, 255), (2, 2, width - 4, height - 4), border_radius=6)
    pygame.draw.rect(surface, (86, 94, 112, 255), (3, 3, width - 6, height - 6), 1, border_radius=5)
    # Corner tarnished-brass clasps
    for cx, cy in ((4, 4), (width - 8, 4), (4, height - 8), (width - 8, height - 8)):
        pygame.draw.rect(surface, (148, 122, 68, 255), (cx, cy, 4, 4))
    # Deep basin recess & luminous cyan runic water core
    pygame.draw.rect(surface, (14, 34, 62, 255), (6, 6, width - 12, height - 12), border_radius=4)
    pygame.draw.rect(surface, (28, 92, 138, 255), (8, 8, width - 16, height - 16), border_radius=3)
    for _ in range(14):
        rx = rng.randint(9, width - 11)
        ry = rng.randint(9, height - 11)
        col = (110, 235, 255, 220) if rng.random() < 0.55 else (48, 168, 210, 200)
        surface.set_at((rx, ry), col)
    # Central runic diamond
    mid_x, mid_y = width // 2, height // 2
    pygame.draw.polygon(
        surface,
        (165, 250, 255, 230),
        [(mid_x, mid_y - 6), (mid_x + 6, mid_y), (mid_x, mid_y + 6), (mid_x - 6, mid_y)],
        1,
    )
    return surface


def generate_lotus_frame(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 dark indigo/obsidian carved frame with cyan-magenta filigree petals."""
    if rng is None:
        rng = _asset_rng(DEFAULT_ASSET_SEED, "lotus_frame")
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    # Obsidian-indigo carved base
    pygame.draw.rect(surface, (26, 30, 56, 255), (1, 1, width - 2, height - 2), border_radius=4)
    pygame.draw.rect(surface, (44, 54, 96, 255), (2, 2, width - 4, height - 4), 2, border_radius=4)
    pygame.draw.rect(surface, (16, 18, 34, 255), (7, 7, width - 14, height - 14), border_radius=3)
    # Corner cyan-magenta filigree petals
    mid_x, mid_y = width // 2, height // 2
    petal_cols = [(0, 220, 245, 230), (220, 75, 185, 230)]
    for idx, (px, py) in enumerate(((mid_x, 5), (width - 6, mid_y), (mid_x, height - 6), (5, mid_y))):
        col = petal_cols[idx % 2]
        pygame.draw.circle(surface, col, (px, py), 3)
        surface.set_at((px, py), (235, 250, 255, 255))
    # Inner filigree ring & subtle stone grit
    pygame.draw.circle(surface, (74, 156, 210, 200), (mid_x, mid_y), 7, 1)
    pygame.draw.circle(surface, (205, 80, 175, 220), (mid_x, mid_y), 3)
    for _ in range(10):
        gx, gy = rng.randint(3, width - 4), rng.randint(3, height - 4)
        if gx < 7 or gx > width - 8 or gy < 7 or gy > height - 8:
            surface.set_at((gx, gy), (62, 74, 122, 220))
    return surface


def generate_bench(
    width: int | None = None,
    height: int | None = None,
    rng: random.Random | None = None,
    facing: str = "south",
) -> pygame.Surface:
    """Generate a directional weathered dark-oak reading bench (80x40 N/S, 40x80 E/W) with iron brackets."""
    norm_facing = constants.normalize_bench_facing(facing)
    if width is None or height is None:
        default_w, default_h = constants.get_bench_dimensions(norm_facing)
        width = default_w if width is None else width
        height = default_h if height is None else height
    if rng is None:
        seed_key = "bench" if norm_facing == "south" else f"bench_{norm_facing}"
        rng = _asset_rng(DEFAULT_ASSET_SEED, seed_key)
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))

    if norm_facing == "south":
        # Soft floor shadow
        pygame.draw.ellipse(surface, (12, 10, 14, 130), (3, height - 11, width - 6, 8))
        # Iron legs & side/center brackets
        leg_xs = [5, width - 10]
        if width >= TILE_WIDTH * 2:
            leg_xs.append(width // 2 - 2)
        for lx in leg_xs:
            pygame.draw.rect(surface, (36, 38, 46, 255), (lx, 12, 5, height - 16))
            pygame.draw.rect(surface, (78, 82, 94, 255), (lx + 1, 13, 2, height - 18))
        # Backrest (top) & seat planks (bottom) in weathered dark oak
        pygame.draw.rect(surface, (62, 38, 22, 255), (4, 8, width - 8, 9), border_radius=2)
        pygame.draw.rect(surface, (108, 70, 40, 255), (4, 9, width - 8, 3))
        pygame.draw.rect(surface, (78, 48, 26, 255), (3, 19, width - 6, 11), border_radius=2)
        pygame.draw.rect(surface, (124, 84, 48, 255), (4, 19, width - 8, 3))
        pygame.draw.line(surface, (42, 24, 14, 255), (4, 24), (width - 5, 24), 1)
        rivet_xs = [7, width - 8]
        if width >= TILE_WIDTH * 2:
            rivet_xs.append(width // 2)
        for rx in rivet_xs:
            surface.set_at((rx, 12), (160, 165, 178, 255))
            surface.set_at((rx, 21), (160, 165, 178, 255))
        grain_count = 24 if width >= TILE_WIDTH * 2 else 12
        for _ in range(grain_count):
            gx = rng.randint(5, width - 6)
            gy = rng.choice([11, 13, 21, 26])
            surface.set_at((gx, gy), (52, 30, 18, 220))
        return surface

    if norm_facing == "north":
        # Facing north: viewer looks at the rear of the sturdy backrest with seat peeking above
        pygame.draw.ellipse(surface, (12, 10, 14, 135), (3, height - 10, width - 6, 8))
        # Recessed northern seat edge visible above the backrest
        pygame.draw.rect(surface, (74, 46, 25, 255), (4, 8, width - 8, 8), border_radius=2)
        pygame.draw.rect(surface, (112, 74, 42, 255), (5, 9, width - 10, 2))
        pygame.draw.line(surface, (42, 24, 14, 255), (5, 14), (width - 6, 14), 1)
        # Rear lower iron legs peeking under the backrest
        leg_xs = [6, width - 11]
        if width >= TILE_WIDTH * 2:
            leg_xs.append(width // 2 - 2)
        for lx in leg_xs:
            pygame.draw.rect(surface, (34, 36, 44, 255), (lx, 26, 5, height - 30))
            pygame.draw.rect(surface, (74, 78, 90, 255), (lx + 1, 27, 2, height - 32))
        # Foreground tall weathered oak backrest (seen from behind)
        pygame.draw.rect(surface, (56, 34, 20, 255), (3, 14, width - 6, 15), border_radius=2)
        pygame.draw.rect(surface, (116, 78, 44, 255), (4, 14, width - 8, 3))
        pygame.draw.rect(surface, (44, 26, 15, 255), (4, 26, width - 8, 3))
        pygame.draw.line(surface, (38, 22, 12, 255), (4, 21), (width - 5, 21), 1)
        # Vertical iron rear support straps + rivets across the back panel
        for lx in leg_xs:
            pygame.draw.rect(surface, (44, 46, 56, 255), (lx, 15, 5, 14))
            pygame.draw.rect(surface, (86, 90, 104, 255), (lx + 1, 16, 2, 12))
            surface.set_at((lx + 2, 17), (168, 174, 188, 255))
            surface.set_at((lx + 2, 24), (168, 174, 188, 255))
        grain_count = 24 if width >= TILE_WIDTH * 2 else 12
        for _ in range(grain_count):
            gx = rng.randint(5, width - 6)
            gy = rng.choice([17, 19, 23, 25])
            if not any(lx <= gx <= lx + 4 for lx in leg_xs):
                surface.set_at((gx, gy), (44, 24, 14, 220))
        return surface

    # Vertical 40x80 bench (east or west)
    pygame.draw.ellipse(surface, (12, 10, 14, 130), (5, height - 11, width - 10, 9))
    pygame.draw.rect(surface, (12, 10, 14, 90), (6, 8, width - 12, height - 15), border_radius=4)
    brace_ys = [8, height - 13]
    if height >= TILE_HEIGHT * 2:
        brace_ys.append(height // 2 - 2)
    for by in brace_ys:
        pygame.draw.rect(surface, (36, 38, 46, 255), (6, by, width - 12, 5))
        pygame.draw.rect(surface, (78, 82, 94, 255), (7, by + 1, width - 14, 2))

    if norm_facing == "east":
        # Backrest along west (left) edge, seat plank facing east (right)
        back_x, back_w = 7, 9
        seat_x, seat_w = 17, 15
        back_hi_x = back_x + 1
        seat_hi_x = seat_x + seat_w - 4
        seat_seam_x = seat_x + 7
        rivet_xs = (back_x + 4, seat_x + 5)
    else:
        # Backrest along east (right) edge, seat plank facing west (left)
        back_x, back_w = width - 16, 9
        seat_x, seat_w = 8, 15
        back_hi_x = back_x + 1
        seat_hi_x = seat_x + 1
        seat_seam_x = seat_x + 8
        rivet_xs = (back_x + 4, seat_x + seat_w - 6)

    # Tall vertical backrest timber
    pygame.draw.rect(surface, (60, 36, 21, 255), (back_x, 4, back_w, height - 8), border_radius=2)
    pygame.draw.rect(surface, (112, 74, 42, 255), (back_hi_x, 5, 3, height - 10))
    pygame.draw.line(surface, (38, 22, 12, 255), (back_x + back_w - 1, 5), (back_x + back_w - 1, height - 6), 1)
    # Wider vertical seat planks
    pygame.draw.rect(surface, (78, 48, 26, 255), (seat_x, 3, seat_w, height - 6), border_radius=2)
    pygame.draw.rect(surface, (124, 84, 48, 255), (seat_hi_x, 4, 3, height - 8))
    pygame.draw.line(surface, (42, 24, 14, 255), (seat_seam_x, 4), (seat_seam_x, height - 5), 1)
    # Iron end-straps & rivets
    for by in brace_ys:
        pygame.draw.rect(surface, (46, 48, 58, 255), (min(back_x, seat_x), by, back_w + seat_w + 1, 3))
        for rx in rivet_xs:
            surface.set_at((rx, by + 1), (165, 170, 184, 255))
    grain_count = 24 if height >= TILE_HEIGHT * 2 else 12
    for _ in range(grain_count):
        gx = rng.choice([back_x + 3, back_x + 6, seat_x + 4, seat_x + 10])
        gy = rng.randint(5, height - 6)
        surface.set_at((gx, gy), (50, 28, 16, 220))
    return surface


def generate_heavy_bookcase(
    width: int = TILE_WIDTH * 2,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate an 80x40 double-wide tall timber-and-iron archive shelf packed with tomes."""
    if rng is None:
        rng = _asset_rng(DEFAULT_ASSET_SEED, "heavy_bookcase")
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    # Outer dark mahogany frame & top cornice
    pygame.draw.rect(surface, (34, 22, 16, 255), (0, 0, width, height), border_radius=3)
    pygame.draw.rect(surface, (68, 44, 30, 255), (1, 1, width - 2, height - 2), border_radius=2)
    pygame.draw.rect(surface, (128, 92, 56, 255), (1, 1, width - 2, 4))
    # Recessed shelf interiors
    pygame.draw.rect(surface, (24, 16, 12, 255), (4, 7, width - 8, height // 2 - 8))
    pygame.draw.rect(surface, (24, 16, 12, 255), (4, height // 2 + 2, width - 8, height // 2 - 6))
    # Iron corner rivets & vertical divider
    pygame.draw.rect(surface, (46, 48, 56, 255), (width // 2 - 2, 5, 4, height - 7))
    for rx in (2, width - 4, width // 2 - 1):
        surface.set_at((rx, 2), (145, 150, 164, 255))
        surface.set_at((rx, height - 3), (145, 150, 164, 255))
    # Crooked leather & parchment tomes on both shelves
    spine_palette = [
        (132, 48, 44, 255),
        (56, 98, 128, 255),
        (168, 144, 96, 255),
        (92, 58, 108, 255),
        (68, 104, 72, 255),
        (146, 98, 52, 255),
    ]
    for shelf_y, shelf_h in ((7, height // 2 - 8), (height // 2 + 2, height // 2 - 6)):
        bx = 5
        while bx < width - 9:
            if bx in range(width // 2 - 4, width // 2 + 3):
                bx += 3
                continue
            bw = rng.randint(4, 6)
            bh = max(6, shelf_h - rng.randint(0, 4))
            col = rng.choice(spine_palette)
            by = shelf_y + (shelf_h - bh)
            pygame.draw.rect(surface, col, (bx, by, bw, bh))
            pygame.draw.line(surface, (220, 205, 175, 160), (bx + 1, by + 2), (bx + bw - 2, by + 2), 1)
            bx += bw + rng.randint(1, 2)
    return surface


def generate_ink_urn(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 cracked obsidian/ceramic amphora overflowing with black-violet ink."""
    if rng is None:
        rng = _asset_rng(DEFAULT_ASSET_SEED, "ink_urn")
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    cx, cy = width // 2, height // 2
    # Base ink spill puddle
    pygame.draw.ellipse(surface, (18, 10, 28, 210), (7, height - 11, width - 14, 8))
    # Ceramic/obsidian amphora body
    pygame.draw.ellipse(surface, (36, 44, 68, 255), (9, 10, width - 18, height - 15))
    pygame.draw.ellipse(surface, (58, 74, 110, 255), (10, 11, width - 22, height - 19))
    pygame.draw.circle(surface, (112, 162, 215, 210), (cx - 4, cy), 3)
    # Tarnished brass neck & rim
    pygame.draw.rect(surface, (158, 134, 82, 255), (12, 5, width - 24, 6), border_radius=2)
    pygame.draw.ellipse(surface, (20, 12, 34, 255), (13, 6, width - 26, 3))
    # Crack & overflowing glossy black-violet ink drips
    pygame.draw.line(surface, (14, 10, 22, 255), (cx + 2, 13), (cx + 5, 22), 1)
    pygame.draw.line(surface, (14, 10, 22, 255), (cx + 5, 22), (cx + 3, 28), 1)
    for dx, dh in ((-3, 12), (1, 16), (4, 10)):
        pygame.draw.rect(surface, (28, 12, 46, 255), (cx + dx, 8, 2, dh))
        if rng.random() < 0.7:
            surface.set_at((cx + dx, 8 + dh // 2), (145, 72, 195, 230))
    return surface


def generate_inkwell_puddle(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 glossy dark ink pool with specular sheen highlights."""
    if rng is None:
        rng = _asset_rng(DEFAULT_ASSET_SEED, "inkwell_puddle")
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    cx, cy = width // 2, height // 2
    # Irregular outer ink lobes
    pygame.draw.circle(surface, (14, 8, 22, 235), (cx, cy), width // 2 - 2)
    pygame.draw.circle(surface, (28, 14, 46, 240), (cx - 4, cy - 2), width // 3 + 1)
    pygame.draw.circle(surface, (28, 14, 46, 240), (cx + 5, cy + 3), width // 3)
    pygame.draw.circle(surface, (18, 8, 30, 245), (cx, cy), width // 3 - 1)
    # Specular violet-slate sheen arcs and droplets
    pygame.draw.arc(surface, (132, 72, 172, 190), (cx - 10, cy - 9, 18, 14), 0.5, 2.4, 1)
    for _ in range(8):
        sx = rng.randint(cx - 10, cx + 10)
        sy = rng.randint(cy - 10, cy + 10)
        surface.set_at((sx, sy), (168, 110, 212, 200))
    return surface


def generate_candelabra(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 wrought-iron multi-arm stand with flickering amber tallow candles."""
    if rng is None:
        rng = _asset_rng(DEFAULT_ASSET_SEED, "candelabra")
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    cx = width // 2
    # Shadow & tripod wrought-iron base
    pygame.draw.ellipse(surface, (12, 10, 14, 140), (cx - 10, height - 8, 20, 6))
    pygame.draw.line(surface, (42, 44, 52, 255), (cx, height - 8), (cx - 8, height - 4), 2)
    pygame.draw.line(surface, (42, 44, 52, 255), (cx, height - 8), (cx + 8, height - 4), 2)
    pygame.draw.rect(surface, (52, 54, 64, 255), (cx - 2, 13, 4, height - 19))
    # Cross-arms
    pygame.draw.rect(surface, (58, 60, 72, 255), (cx - 9, 17, 18, 2))
    for arm_x in (cx - 8, cx + 8):
        pygame.draw.rect(surface, (58, 60, 72, 255), (arm_x - 1, 13, 2, 5))
    # Three tallow candles & warm amber/gold flames
    candle_positions = ((cx - 8, 9), (cx, 6), (cx + 8, 9))
    for kx, ky in candle_positions:
        pygame.draw.rect(surface, (226, 214, 184, 255), (kx - 1, ky + 3, 3, 5))
        pygame.draw.circle(surface, (255, 175, 42, 220), (kx, ky + 1), 2)
        surface.set_at((kx, ky), (255, 245, 175, 255))
        if rng.random() < 0.5:
            surface.set_at((kx, ky + 4), (242, 232, 208, 255))
    return surface


def generate_tree_structure(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
    variant: int = 0,
) -> pygame.Surface:
    """Generate a 40x40 forest tree sprite with variant surface roots and foliage tints (variants 0..3)."""
    v_idx = int(variant) % 4
    if rng is None:
        rng = _asset_rng(DEFAULT_ASSET_SEED, f"tree_structure_{v_idx}" if v_idx else "tree_structure")
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    cx, cy = width // 2, height // 2 - 4

    palettes = {
        0: {
            "bark_dark": (46, 30, 20, 255),
            "bark_hi": (68, 44, 28, 255),
            "outer": (20, 38, 28, 255),
            "mid": (34, 72, 46, 255),
            "inner": (54, 108, 64, 255),
            "hi_dot": (98, 148, 86, 230),
            "sh_dot": (26, 48, 34, 230),
        },
        1: {
            "bark_dark": (56, 36, 22, 255),
            "bark_hi": (92, 60, 34, 255),
            "outer": (42, 46, 20, 255),
            "mid": (82, 90, 34, 255),
            "inner": (136, 128, 48, 255),
            "hi_dot": (182, 166, 72, 235),
            "sh_dot": (52, 54, 24, 230),
        },
        2: {
            "bark_dark": (42, 28, 20, 255),
            "bark_hi": (74, 52, 34, 255),
            "outer": (16, 46, 36, 255),
            "mid": (28, 92, 64, 255),
            "inner": (48, 138, 86, 255),
            "hi_dot": (94, 182, 114, 235),
            "sh_dot": (20, 56, 42, 230),
        },
        3: {
            "bark_dark": (54, 30, 22, 255),
            "bark_hi": (94, 54, 34, 255),
            "outer": (64, 30, 18, 255),
            "mid": (122, 56, 26, 255),
            "inner": (176, 104, 38, 255),
            "hi_dot": (218, 158, 62, 235),
            "sh_dot": (78, 36, 20, 230),
        },
    }
    pal = palettes[v_idx]

    # Ground shadow & gnarled bark trunk
    pygame.draw.ellipse(surface, (14, 18, 16, 150), (cx - 13, height - 11, 26, 8))
    pygame.draw.rect(surface, pal["bark_dark"], (cx - 5, height - 18, 10, 12), border_radius=2)

    # Surface roots (progressively more expressive across variants 1..3)
    if v_idx == 0:
        pygame.draw.line(surface, pal["bark_hi"], (cx - 4, height - 8), (cx - 9, height - 5), 2)
        pygame.draw.line(surface, pal["bark_hi"], (cx + 4, height - 8), (cx + 9, height - 5), 2)
    elif v_idx == 1:
        # Visible gnarled surface roots radiating onto ground
        for pts in (
            [(cx - 4, height - 10), (cx - 10, height - 7), (cx - 15, height - 4)],
            [(cx + 4, height - 10), (cx + 10, height - 6), (cx + 15, height - 4)],
            [(cx - 1, height - 8), (cx - 4, height - 4), (cx - 6, height - 2)],
            [(cx + 2, height - 8), (cx + 5, height - 3)],
        ):
            pygame.draw.lines(surface, pal["bark_dark"], False, pts, 3)
            pygame.draw.lines(surface, pal["bark_hi"], False, pts[:2], 1)
    elif v_idx == 2:
        # Flared buttress roots gripping soil
        buttress = [
            (cx - 13, height - 4),
            (cx - 6, height - 13),
            (cx + 6, height - 13),
            (cx + 13, height - 4),
            (cx + 7, height - 6),
            (cx, height - 3),
            (cx - 7, height - 6),
        ]
        pygame.draw.polygon(surface, pal["bark_dark"], buttress)
        pygame.draw.line(surface, pal["bark_hi"], (cx - 4, height - 12), (cx - 11, height - 5), 2)
        pygame.draw.line(surface, pal["bark_hi"], (cx + 4, height - 12), (cx + 11, height - 5), 2)
        pygame.draw.line(surface, pal["bark_hi"], (cx, height - 11), (cx, height - 4), 1)
    else:
        # Exposed spreading autumn root tendrils
        for pts in (
            [(cx - 5, height - 11), (cx - 11, height - 8), (cx - 16, height - 6)],
            [(cx - 3, height - 8), (cx - 8, height - 3), (cx - 12, height - 2)],
            [(cx + 3, height - 8), (cx + 9, height - 4), (cx + 14, height - 2)],
            [(cx + 5, height - 11), (cx + 12, height - 8), (cx + 16, height - 5)],
        ):
            pygame.draw.lines(surface, pal["bark_dark"], False, pts, 3)
            pygame.draw.lines(surface, pal["bark_hi"], False, pts[:2], 1)

    # Layered canopy with distinct lobe geometry per variant
    if v_idx == 2:
        # Multi-lobed moss-emerald crown
        for ox_l, oy_l, rad in ((-6, 1, 11), (6, 1, 11), (0, -4, 12)):
            pygame.draw.circle(surface, pal["outer"], (cx + ox_l, cy + oy_l), rad)
        for ox_l, oy_l, rad in ((-5, 0, 9), (5, 0, 9), (-1, -4, 10)):
            pygame.draw.circle(surface, pal["mid"], (cx + ox_l, cy + oy_l), rad)
        pygame.draw.circle(surface, pal["inner"], (cx - 2, cy - 4), 9)
    elif v_idx == 3:
        # Wind-tilted russet-gold autumn crown
        pygame.draw.circle(surface, pal["outer"], (cx + 1, cy + 1), width // 2 - 2)
        pygame.draw.circle(surface, pal["mid"], (cx, cy - 1), width // 2 - 4)
        pygame.draw.circle(surface, pal["inner"], (cx - 2, cy - 4), width // 3 + 1)
        pygame.draw.circle(surface, pal["hi_dot"], (cx - 5, cy - 6), 4)
    else:
        pygame.draw.circle(surface, pal["outer"], (cx, cy + 1), width // 2 - 2)
        pygame.draw.circle(surface, pal["mid"], (cx - 2, cy), width // 2 - 5)
        pygame.draw.circle(surface, pal["inner"], (cx - 3, cy - 3), width // 3)

    for _ in range(30):
        lx = rng.randint(6, width - 7)
        ly = rng.randint(4, cy + 8)
        if math.hypot(lx - cx, ly - cy) <= width // 2 - 4:
            col = pal["hi_dot"] if rng.random() < 0.45 else pal["sh_dot"]
            surface.set_at((lx, ly), col)
    return surface


def generate_flutter_frame(
    frame: int = 0,
    empowered: bool = False,
    width: int = 40,
    height: int = 40,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA wing-pose frame (0=mid, 1=upstroke, 2=downstroke) for FlutterEnemy."""
    f_idx = int(frame) % 3
    tag = f"flutter_{'empowered_' if empowered else ''}{f_idx}"
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, tag)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx, cy = width // 2, height // 2

    if empowered:
        wing_fill = (36, 32, 42, 255)
        wing_hi = (58, 44, 66, 255)
        wing_edge = (186, 36, 68, 255)
        spine_col = (18, 14, 22, 255)
        script_col = (155, 65, 220, 220)
        seal_col = (242, 74, 108, 255)
        glint_col = (255, 198, 220, 255)
    else:
        wing_fill = (198, 184, 152, 255)
        wing_hi = (224, 212, 182, 255)
        wing_edge = (88, 76, 58, 255)
        spine_col = (118, 102, 78, 255)
        script_col = (56, 50, 46, 220)
        seal_col = (152, 46, 48, 255)
        glint_col = (238, 148, 134, 255)

    if f_idx == 0:
        # Frame 0: Wings spread mid-stroke with fluttering parchment corner curl
        left_wing = [(cx, cy - 8), (5, cy - 11), (3, cy + 5), (12, cy + 10), (cx, cy + 8)]
        right_wing = [(cx, cy - 8), (width - 6, cy - 12), (width - 4, cy + 4), (width - 11, cy + 11), (cx, cy + 8)]
        seal_pos = (cx + 4, cy + 3)
        glint_pos = (cx + 3, cy + 2)
        mote_pts = ((6, cy - 12), (width - 7, cy + 11))
    elif f_idx == 1:
        # Frame 1: Wings arched high on the upstroke with tucked lower corners & shifted wax-seal glint
        left_wing = [(cx, cy - 4), (6, 4), (4, 15), (13, cy + 5), (cx, cy + 9)]
        right_wing = [(cx, cy - 4), (width - 7, 3), (width - 5, 14), (width - 13, cy + 5), (cx, cy + 9)]
        seal_pos = (cx + 3, cy + 4)
        glint_pos = (cx + 4, cy + 2)
        mote_pts = ((5, 6), (width - 6, 6))
    else:
        # Frame 2: Wings swept low/forward on the downstroke with arched spine crease
        left_wing = [(cx, cy - 10), (9, cy - 3), (4, height - 6), (13, height - 4), (cx, cy + 5)]
        right_wing = [
            (cx, cy - 10), (width - 10, cy - 3), (width - 5, height - 6),
            (width - 14, height - 4), (cx, cy + 5),
        ]
        seal_pos = (cx + 2, cy)
        glint_pos = (cx + 1, cy - 1)
        mote_pts = ((7, height - 5), (width - 8, height - 5))

    # Draw left & right parchment wing lobes
    for poly in (left_wing, right_wing):
        pygame.draw.polygon(surf, wing_fill, poly)
        pygame.draw.polygon(surf, wing_edge, poly, 1)

    # Subtle highlight curl along upper leading edges
    pygame.draw.line(surf, wing_hi, left_wing[0], left_wing[1], 1)
    pygame.draw.line(surf, wing_hi, right_wing[0], right_wing[1], 1)

    # Central manuscript spine crease
    spine_top = (cx, min(left_wing[0][1], right_wing[0][1]))
    spine_bot = (cx, max(left_wing[-1][1], right_wing[-1][1]))
    pygame.draw.line(surf, spine_col, spine_top, spine_bot, 2)

    # Charcoal/violet script lines following wing tilt
    tilt = 0 if f_idx == 0 else (-3 if f_idx == 1 else 3)
    for row_off in (-4, 0, 4):
        ly = cy + row_off
        jit_l = gen.randint(0, 2)
        jit_r = gen.randint(0, 2)
        pygame.draw.line(surf, script_col, (cx - 3, ly), (cx - 11 + jit_l, ly + tilt), 1)
        pygame.draw.line(surf, script_col, (cx + 3, ly), (cx + 11 - jit_r, ly + tilt), 1)

    # Wax seal + glint & trailing ink motes
    pygame.draw.circle(surf, seal_col, seal_pos, 3)
    surf.set_at(glint_pos, glint_col)
    mote_col = (155, 65, 220, 235) if empowered else (48, 44, 52, 220)
    for mx, my in mote_pts:
        if 0 <= mx < width and 0 <= my < height:
            pygame.draw.circle(surf, mote_col, (mx, my), 1)
    return surf


def _boss_stride_offsets(frame: int) -> tuple[int, int, int]:
    """Return (left_shift_y, right_shift_y, sway_x) for 3-frame boss stride animation."""
    f_idx = int(frame) % 3
    if f_idx == 1:
        return (-2, 2, -2)
    if f_idx == 2:
        return (2, -2, 2)
    return (0, 0, 0)


def generate_miniboss_sprite(
    width: int = 40,
    height: int = 40,
    rng: random.Random | None = None,
    direction: str = "down",
    frame: int = 0,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA Archivist Enforcer miniboss sprite (down/up/side x frames 0..2)."""
    d_key = direction if direction in ("down", "up", "side") else "down"
    f_idx = int(frame) % 3
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, f"miniboss_{d_key}_{f_idx}")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2
    l_dy, r_dy, sway = _boss_stride_offsets(f_idx)
    bob = -1 if f_idx != 0 else 0

    # Ground shadow & heavy armored boots
    pygame.draw.ellipse(surf, (14, 14, 20, 125), (6, height - 9, width - 12, 7))
    slate_dark = (36, 40, 50, 255)
    slate_mid = (58, 64, 78, 255)
    slate_hi = (98, 108, 126, 255)
    brass = (182, 146, 72, 255)
    brass_hi = (232, 198, 108, 255)
    parchment = (212, 198, 166, 255)
    outline = (16, 18, 24, 255)

    if d_key == "side":
        # Three-quarter right-facing Archivist Enforcer
        # Striding boots
        pygame.draw.rect(surf, slate_dark, (cx - 7 - sway, height - 11, 6, 7), border_radius=2)
        pygame.draw.rect(surf, slate_mid, (cx + 1 + sway, height - 10, 6, 7), border_radius=2)
        # Swept-back slate cloak tail trailing left
        cloak = [(cx - 3, 13 + bob), (6 - sway // 2, 22), (4 - sway // 2, height - 9), (cx + 4, height - 9)]
        pygame.draw.polygon(surf, (30, 34, 44, 255), cloak)
        pygame.draw.polygon(surf, outline, cloak, 1)
        # Armored torso & leather-ledger tabard
        torso = pygame.Rect(cx - 7, 13 + bob, 16, 19)
        pygame.draw.rect(surf, slate_mid, torso, border_radius=4)
        pygame.draw.rect(surf, outline, torso, 1, border_radius=4)
        pygame.draw.line(surf, brass, (cx + 4, 15 + bob), (cx + 4, 30 + bob), 2)
        # Heavy iron-bound ledger shield-pauldron on forward right shoulder
        shield = pygame.Rect(cx - 2, 13 + l_dy // 2 + bob, 13, 12)
        pygame.draw.rect(surf, (52, 42, 36, 255), shield, border_radius=2)
        pygame.draw.rect(surf, parchment, (shield.left + 2, shield.bottom - 3, shield.width - 4, 2))
        pygame.draw.rect(surf, brass, shield, 1, border_radius=2)
        # Hooded cowl & riveted brass brow-plate facing right with glowing amber lantern eye
        hood = [(cx - 7, 14 + bob), (cx - 4, 4 + bob), (cx + 6, 5 + bob), (cx + 9, 13 + bob)]
        pygame.draw.polygon(surf, slate_dark, hood)
        pygame.draw.polygon(surf, outline, hood, 1)
        pygame.draw.rect(surf, brass, (cx - 2, 7 + bob, 10, 3))
        surf.set_at((cx + 1, 8 + bob), brass_hi)
        surf.set_at((cx + 5, 8 + bob), brass_hi)
        pygame.draw.rect(surf, (14, 14, 20, 255), (cx + 1, 10 + bob, 7, 4))
        pygame.draw.circle(surf, (246, 188, 72, 255), (cx + 5, 12 + bob), 2)
        surf.set_at((cx + 5, 11 + bob), (255, 240, 178, 255))
    elif d_key == "up":
        # Back-turned Archivist Enforcer (iron-spined cloak & heavy shield pauldrons, no eyes)
        pygame.draw.rect(surf, slate_dark, (cx - 8, height - 10 + l_dy // 2, 6, 7), border_radius=2)
        pygame.draw.rect(surf, slate_dark, (cx + 2, height - 10 + r_dy // 2, 6, 7), border_radius=2)
        cloak = [
            (cx - 12, 13 + bob), (cx + 12, 13 + bob),
            (cx + 14 + sway // 2, height - 8), (cx, height - 6), (cx - 14 + sway // 2, height - 8),
        ]
        pygame.draw.polygon(surf, slate_dark, cloak)
        pygame.draw.polygon(surf, outline, cloak, 1)
        pygame.draw.line(surf, brass, (cx, 15 + bob), (cx + sway // 2, height - 9), 2)
        # Heavy rear ledger shield-pauldrons
        for sx_p, dy_p in ((5, l_dy // 2), (width - 15, r_dy // 2)):
            pr = pygame.Rect(sx_p, 12 + dy_p + bob, 10, 11)
            pygame.draw.rect(surf, slate_mid, pr, border_radius=2)
            pygame.draw.rect(surf, brass, pr, 1, border_radius=2)
        # Hood crown from behind + brass brow-band wrap
        pygame.draw.ellipse(surf, slate_mid, (cx - 8, 4 + bob, 16, 13))
        pygame.draw.ellipse(surf, outline, (cx - 8, 4 + bob, 16, 13), 1)
        pygame.draw.line(surf, slate_hi, (cx - 4, 6 + bob), (cx + 4, 6 + bob), 1)
        pygame.draw.rect(surf, brass, (cx - 7, 11 + bob, 14, 2))
    else:
        # Front-facing Archivist Enforcer (canonical miniboss.png)
        pygame.draw.rect(surf, slate_dark, (cx - 8, height - 10 + l_dy // 2, 6, 7), border_radius=2)
        pygame.draw.rect(surf, slate_dark, (cx + 2, height - 10 + r_dy // 2, 6, 7), border_radius=2)
        # Heavy iron-bound ledger shield-pauldrons with stacked parchment edge & brass clasps
        for sx_p, dy_p in ((3, l_dy // 2), (width - 13, r_dy // 2)):
            pr = pygame.Rect(sx_p, 12 + dy_p + bob, 10, 13)
            pygame.draw.rect(surf, (52, 42, 36, 255), pr, border_radius=2)
            pygame.draw.rect(surf, parchment, (pr.left + 2, pr.bottom - 3, pr.width - 4, 2))
            pygame.draw.rect(surf, slate_hi, (pr.left + 1, pr.top + 1, pr.width - 2, 3))
            pygame.draw.rect(surf, brass, pr, 1, border_radius=2)
            surf.set_at((pr.centerx, pr.top + 5), brass_hi)
        # Armored cuirass & parchment tabard
        torso = pygame.Rect(10, 12 + bob, width - 20, height - 19)
        pygame.draw.rect(surf, slate_mid, torso, border_radius=5)
        pygame.draw.rect(surf, outline, torso, 1, border_radius=5)
        tab = pygame.Rect(cx - 4, 20 + bob, 8, height - 27)
        pygame.draw.rect(surf, parchment, tab)
        pygame.draw.line(surf, (92, 74, 52, 230), (cx, 21 + bob), (cx, height - 9), 1)
        # Hooded dark-slate cowl & riveted brass brow-plate
        hood = [(cx - 9, 16 + bob), (cx - 7, 4 + bob), (cx + 7, 4 + bob), (cx + 9, 16 + bob)]
        pygame.draw.polygon(surf, slate_dark, hood)
        pygame.draw.polygon(surf, outline, hood, 1)
        pygame.draw.rect(surf, brass, (cx - 8, 8 + bob, 16, 3))
        for rx in (cx - 6, cx, cx + 6):
            surf.set_at((rx, 9 + bob), brass_hi)
        # Shadowed visor recess & twin warm-amber lantern eyes
        pygame.draw.rect(surf, (14, 14, 20, 255), (cx - 6, 11 + bob, 12, 5), border_radius=2)
        eye_dx = -1 if f_idx == 1 else (1 if f_idx == 2 else 0)
        pygame.draw.circle(surf, (246, 188, 72, 255), (cx - 3 + eye_dx, 13 + bob), 2)
        pygame.draw.circle(surf, (246, 188, 72, 255), (cx + 3 + eye_dx, 13 + bob), 2)
        surf.set_at((cx - 3 + eye_dx, 13 + bob), (255, 242, 184, 255))
        surf.set_at((cx + 3 + eye_dx, 13 + bob), (255, 242, 184, 255))

    for _ in range(18):
        gx, gy = gen.randint(5, width - 6), gen.randint(6, height - 8)
        c = surf.get_at((gx, gy))
        if c.a > 200:
            d = gen.randint(-8, 8)
            surf.set_at((gx, gy), (max(0, min(255, c.r + d)), max(0, min(255, c.g + d)), max(0, min(255, c.b + d)), 255))
    return surf


def generate_night_boss_sprite(
    width: int = 64,
    height: int = 64,
    rng: random.Random | None = None,
    direction: str = "down",
    frame: int = 0,
) -> pygame.Surface:
    """Generate a 64x64 SRCALPHA Margin Warden Night Boss sprite (down/up/side x frames 0..2)."""
    d_key = direction if direction in ("down", "up", "side") else "down"
    f_idx = int(frame) % 3
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, f"night_boss_{d_key}_{f_idx}")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2
    l_dy, r_dy, sway = _boss_stride_offsets(f_idx)
    bob = -1 if f_idx != 0 else 0

    indigo_dark = (22, 24, 42, 255)
    indigo_mid = (38, 42, 70, 255)
    indigo_rim = (96, 114, 162, 255)
    gold = (198, 162, 74, 255)
    gold_hi = (244, 220, 128, 255)
    parchment = (188, 174, 140, 245)
    rune_cyan = (116, 224, 246, 245)
    outline = (12, 14, 24, 255)

    # Soft ground shadow
    pygame.draw.ellipse(surf, (10, 12, 22, 135), (12, height - 12, width - 24, 9))

    if d_key == "side":
        # Three-quarter right-facing Margin Warden with sweeping tattered cloak & spectral cyan eye
        cloak = [
            (cx - 2, 14 + bob), (cx + 12, 20 + bob), (cx + 15 + sway, height - 9),
            (cx + 4 + sway, height - 6), (cx - 6 + sway, height - 10),
            (10 - sway, height - 8), (14 - sway, 38), (cx - 10, 22 + bob),
        ]
        pygame.draw.polygon(surf, indigo_dark, cloak)
        pygame.draw.polygon(surf, indigo_mid, [(cx - 6, 20 + bob), (cx + 10, 21 + bob), (cx + 10, 48), (cx - 8, 46)])
        pygame.draw.lines(surf, indigo_rim, False, [(14 - sway, 38), (cx - 10, 22 + bob), (cx - 2, 14 + bob)], 2)
        pygame.draw.polygon(surf, outline, cloak, 1)
        # Forward gold-clasped rune stole & parchment sash
        stole = [(cx + 2, 23 + bob), (cx + 11, 23 + bob), (cx + 13 + sway, height - 11), (cx + 4 + sway, height - 13)]
        pygame.draw.polygon(surf, parchment, stole)
        pygame.draw.polygon(surf, (88, 76, 56, 255), stole, 1)
        for ry in range(29 + bob, height - 16, 6):
            pygame.draw.line(surf, rune_cyan, (cx + 5, ry), (cx + 10, ry + 1), 1)
        pygame.draw.rect(surf, gold, (cx + 1, 21 + bob, 10, 4), border_radius=1)
        surf.set_at((cx + 6, 22 + bob), gold_hi)
        # Turned cowl hood with single spectral cyan eye facing right
        cowl = [(cx - 10, 21 + bob), (cx - 5, 7 + bob), (cx + 9, 8 + bob), (cx + 13, 19 + bob)]
        pygame.draw.polygon(surf, indigo_mid, cowl)
        pygame.draw.polygon(surf, outline, cowl, 1)
        pygame.draw.ellipse(surf, (10, 12, 20, 255), (cx + 1, 12 + bob, 10, 9))
        pygame.draw.circle(surf, rune_cyan, (cx + 7, 16 + bob), 2)
        surf.set_at((cx + 7, 16 + bob), (235, 252, 255, 255))
    elif d_key == "up":
        # Back-turned towering tattered cloak with layered mantle & fluttering parchment sash ends
        cloak = [
            (cx - 18, 20 + bob), (cx + 18, 20 + bob),
            (width - 10 + sway, height - 9), (cx + 10 + sway, height - 5),
            (cx, height - 11), (cx - 10 + sway, height - 5), (10 + sway, height - 9),
        ]
        pygame.draw.polygon(surf, indigo_dark, cloak)
        mantle = [(cx - 20, 22 + l_dy // 2 + bob), (cx, 15 + bob), (cx + 20, 22 + r_dy // 2 + bob), (cx + 15, 36 + bob), (cx - 15, 36 + bob)]
        pygame.draw.polygon(surf, indigo_mid, mantle)
        pygame.draw.lines(surf, indigo_rim, False, [(cx - 19, 22 + l_dy // 2 + bob), (cx, 15 + bob), (cx + 19, 22 + r_dy // 2 + bob)], 2)
        pygame.draw.polygon(surf, outline, cloak, 1)
        # Trailing rear parchment sash ribbons with cyan script flecks
        for ox_s, dy_s in ((-7, l_dy), (5, r_dy)):
            rib = [(cx + ox_s, 32 + bob), (cx + ox_s + 5, 32 + bob), (cx + ox_s + 4 + sway, height - 9 + dy_s // 2), (cx + ox_s - 1 + sway, height - 11 + dy_s // 2)]
            pygame.draw.polygon(surf, parchment, rib)
            pygame.draw.line(surf, rune_cyan, (cx + ox_s + 2, 38 + bob), (cx + ox_s + 2 + sway // 2, 48 + bob), 1)
        # Rear pointed cowl hood + gold collar clasp
        hood = [(cx - 12, 22 + bob), (cx, 5 + bob), (cx + 12, 22 + bob)]
        pygame.draw.polygon(surf, indigo_mid, hood)
        pygame.draw.polygon(surf, outline, hood, 1)
        pygame.draw.line(surf, gold, (cx - 10, 22 + bob), (cx + 10, 22 + bob), 2)
    else:
        # Front-facing Margin Warden (canonical night_boss.png)
        cloak = [
            (cx - 17, 21 + bob), (cx + 17, 21 + bob),
            (width - 9 + sway, height - 9), (cx + 13 + sway, height - 6),
            (cx + 5, height - 11), (cx - 5, height - 11),
            (cx - 13 + sway, height - 6), (9 + sway, height - 9),
        ]
        pygame.draw.polygon(surf, indigo_dark, cloak)
        pygame.draw.polygon(surf, outline, cloak, 1)
        # Layered tattered shoulder mantle with indigo-silver rim highlights
        mantle = [
            (cx - 21, 24 + l_dy // 2 + bob), (cx - 10, 17 + bob),
            (cx + 10, 17 + bob), (cx + 21, 24 + r_dy // 2 + bob),
            (cx + 16, 36 + r_dy // 2 + bob), (cx - 16, 36 + l_dy // 2 + bob),
        ]
        pygame.draw.polygon(surf, indigo_mid, mantle)
        pygame.draw.lines(surf, indigo_rim, False, [(cx - 20, 24 + l_dy // 2 + bob), (cx - 10, 17 + bob), (cx + 10, 17 + bob), (cx + 20, 24 + r_dy // 2 + bob)], 2)
        # Twin weathered parchment stoles etched with glowing cyan script runes
        for side_s, dy_s in ((-1, l_dy), (1, r_dy)):
            sx0 = cx + side_s * 7
            stole = [
                (sx0 - 4, 24 + bob), (sx0 + 4, 24 + bob),
                (sx0 + 5 + sway // 2, height - 10 + dy_s // 2),
                (sx0 - 3 + sway // 2, height - 12 + dy_s // 2),
            ]
            pygame.draw.polygon(surf, parchment, stole)
            pygame.draw.polygon(surf, (92, 78, 58, 255), stole, 1)
            for ry in range(30 + bob, height - 16, 6):
                pygame.draw.line(surf, rune_cyan, (sx0 - 2, ry), (sx0 + 2, ry), 1)
        # Gold collar clasps linking stoles
        pygame.draw.rect(surf, gold, (cx - 13, 22 + l_dy // 2 + bob, 6, 4), border_radius=1)
        pygame.draw.rect(surf, gold, (cx + 7, 22 + r_dy // 2 + bob, 6, 4), border_radius=1)
        pygame.draw.line(surf, gold_hi, (cx - 7, 24 + bob), (cx + 7, 24 + bob), 1)
        # Shadowed pointed cowl & twin spectral cyan eyes
        hood = [(cx - 13, 23 + bob), (cx - 9, 8 + bob), (cx, 5 + bob), (cx + 9, 8 + bob), (cx + 13, 23 + bob)]
        pygame.draw.polygon(surf, indigo_mid, hood)
        pygame.draw.polygon(surf, outline, hood, 1)
        pygame.draw.ellipse(surf, (10, 12, 20, 255), (cx - 8, 12 + bob, 16, 11))
        eye_dx = -1 if f_idx == 1 else (1 if f_idx == 2 else 0)
        pygame.draw.circle(surf, rune_cyan, (cx - 3 + eye_dx, 17 + bob), 2)
        pygame.draw.circle(surf, rune_cyan, (cx + 3 + eye_dx, 17 + bob), 2)
        surf.set_at((cx - 3 + eye_dx, 17 + bob), (240, 254, 255, 255))
        surf.set_at((cx + 3 + eye_dx, 17 + bob), (240, 254, 255, 255))

    for _ in range(32):
        gx, gy = gen.randint(10, width - 11), gen.randint(8, height - 10)
        c = surf.get_at((gx, gy))
        if c.a > 200:
            d = gen.randint(-9, 9)
            surf.set_at((gx, gy), (max(0, min(255, c.r + d)), max(0, min(255, c.g + d)), max(0, min(255, c.b + d)), 255))
    return surf


def generate_final_author_sprite(
    width: int = 80,
    height: int = 80,
    rng: random.Random | None = None,
    direction: str = "down",
    frame: int = 0,
) -> pygame.Surface:
    """Generate an 80x80 SRCALPHA Final Author sovereign arbiter sprite (down/up/side x frames 0..2)."""
    d_key = direction if direction in ("down", "up", "side") else "down"
    f_idx = int(frame) % 3
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, f"final_author_{d_key}_{f_idx}")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2
    l_dy, r_dy, sway = _boss_stride_offsets(f_idx)
    bob = -1 if f_idx != 0 else 0

    obsidian = (24, 22, 34, 255)
    robe_mid = (42, 38, 56, 255)
    parchment = (212, 196, 152, 255)
    parchment_hi = (242, 232, 196, 255)
    gold = (196, 158, 68, 255)
    gold_hi = (248, 224, 128, 255)
    outline = (14, 12, 20, 255)

    pygame.draw.ellipse(surf, (10, 8, 16, 140), (14, height - 13, width - 28, 10))

    if d_key == "side":
        # Regal three-quarter right-facing sovereign silhouette
        robe = [
            (cx - 4, 24 + bob), (cx + 15, 27 + bob), (cx + 19 + sway, height - 8),
            (cx + 4 + sway, height - 5), (12 - sway, height - 8), (17 - sway, 46), (cx - 12, 28 + bob),
        ]
        pygame.draw.polygon(surf, obsidian, robe)
        pygame.draw.polygon(surf, outline, robe, 1)
        # Gold script trim running along sweeping robe hem & front edge
        pygame.draw.line(surf, gold, (cx + 12, 28 + bob), (cx + 15 + sway, height - 10), 3)
        pygame.draw.line(surf, gold_hi, (cx + 12, 28 + bob), (cx + 15 + sway, height - 10), 1)
        # Sculpted high gilded-parchment collar framing turned profile
        collar = [(cx - 16, 30 + bob), (cx - 12, 12 + bob), (cx + 4, 17 + bob), (cx + 10, 32 + bob)]
        pygame.draw.polygon(surf, parchment, collar)
        pygame.draw.polygon(surf, gold, collar, 2)
        # Angled three-spired quill/ink-nib crown
        for ox_q, top_y in ((-5, 5), (2, 3), (8, 7)):
            pygame.draw.polygon(surf, parchment_hi, [(cx + ox_q + 2, top_y + bob), (cx + ox_q - 2, 17 + bob), (cx + ox_q + 4, 17 + bob)])
            pygame.draw.line(surf, gold, (cx + ox_q + 2, top_y + bob), (cx + ox_q + 1, 17 + bob), 1)
        # Shadowed visage & piercing golden eye facing right
        pygame.draw.ellipse(surf, (14, 12, 20, 255), (cx - 2, 15 + bob, 14, 13))
        pygame.draw.circle(surf, gold_hi, (cx + 7, 21 + bob), 2)
        surf.set_at((cx + 7, 21 + bob), (255, 252, 224, 255))
    elif d_key == "up":
        # Regal back-turned mantle, tall gilded collar & vertical gold script spine-band (no eyes)
        robe = [
            (cx - 24, 28 + bob), (cx + 24, 28 + bob),
            (width - 10 + sway, height - 8), (cx, height - 4), (10 + sway, height - 8),
        ]
        pygame.draw.polygon(surf, obsidian, robe)
        pygame.draw.polygon(surf, robe_mid, [(cx - 18, 30 + bob), (cx + 18, 30 + bob), (cx + 20 + sway, height - 11), (cx - 20 + sway, height - 11)])
        pygame.draw.polygon(surf, outline, robe, 1)
        # Vertical gold script spine band down back of mantle
        pygame.draw.rect(surf, gold, (cx - 4 + sway // 2, 30 + bob, 8, height - 38))
        for sy in range(35 + bob, height - 12, 7):
            pygame.draw.line(surf, obsidian, (cx - 2 + sway // 2, sy), (cx + 2 + sway // 2, sy), 1)
        # Tall gilded-parchment rear high collar
        collar = [(cx - 22, 32 + l_dy // 2 + bob), (cx - 18, 12 + bob), (cx, 18 + bob), (cx + 18, 12 + bob), (cx + 22, 32 + r_dy // 2 + bob)]
        pygame.draw.polygon(surf, parchment, collar)
        pygame.draw.polygon(surf, gold, collar, 2)
        # Rear silhouette of three-spired quill crown
        for qx, top_y in ((cx - 10, 6), (cx, 3), (cx + 10, 6)):
            pygame.draw.polygon(surf, parchment_hi, [(qx, top_y + bob), (qx - 4, 18 + bob), (qx + 4, 18 + bob)])
            pygame.draw.polygon(surf, gold, [(qx, top_y + bob), (qx - 4, 18 + bob), (qx + 4, 18 + bob)], 1)
    else:
        # Front-facing Final Author (canonical final_author.png)
        robe = [
            (cx - 24, 28 + bob), (cx + 24, 28 + bob),
            (width - 10 + sway, height - 8), (cx + 14 + sway, height - 5),
            (cx, height - 8), (cx - 14 + sway, height - 5), (10 + sway, height - 8),
        ]
        pygame.draw.polygon(surf, obsidian, robe)
        pygame.draw.polygon(surf, outline, robe, 1)
        # Flowing gold-trimmed inner vestment & script bands
        vestment = [(cx - 14, 30 + bob), (cx + 14, 30 + bob), (cx + 11 + sway // 2, height - 10), (cx - 11 + sway // 2, height - 10)]
        pygame.draw.polygon(surf, robe_mid, vestment)
        pygame.draw.polygon(surf, gold, vestment, 2)
        for sy in range(36 + bob, height - 14, 7):
            pygame.draw.line(surf, gold_hi, (cx - 7, sy), (cx + 7, sy), 1)
        # Tall gilded-parchment high collar & sculpted regal shoulder mantle
        collar = [
            (cx - 26, 33 + l_dy // 2 + bob), (cx - 20, 13 + bob),
            (cx - 10, 22 + bob), (cx + 10, 22 + bob),
            (cx + 20, 13 + bob), (cx + 26, 33 + r_dy // 2 + bob),
            (cx + 16, 40 + r_dy // 2 + bob), (cx - 16, 40 + l_dy // 2 + bob),
        ]
        pygame.draw.polygon(surf, parchment, collar)
        pygame.draw.polygon(surf, gold, collar, 2)
        pygame.draw.polygon(surf, gold, [(cx - 18, 30 + bob), (cx + 18, 30 + bob), (cx + 10, 41 + bob), (cx - 10, 41 + bob)])
        # Three-spired quill/ink-nib crown
        for qx, top_y in ((cx - 11, 6), (cx, 2), (cx + 11, 6)):
            spire = [(qx, top_y + bob), (qx - 4, 18 + bob), (qx + 4, 18 + bob)]
            pygame.draw.polygon(surf, parchment_hi, spire)
            pygame.draw.polygon(surf, gold, spire, 1)
            pygame.draw.line(surf, (64, 52, 36, 230), (qx, top_y + 2 + bob), (qx, 16 + bob), 1)
        # Shadowed visage & twin sovereign golden eyes
        pygame.draw.ellipse(surf, (14, 12, 20, 255), (cx - 11, 15 + bob, 22, 16))
        eye_dx = -1 if f_idx == 1 else (1 if f_idx == 2 else 0)
        pygame.draw.circle(surf, gold_hi, (cx - 4 + eye_dx, 22 + bob), 2)
        pygame.draw.circle(surf, gold_hi, (cx + 4 + eye_dx, 22 + bob), 2)
        surf.set_at((cx - 4 + eye_dx, 22 + bob), (255, 252, 226, 255))
        surf.set_at((cx + 4 + eye_dx, 22 + bob), (255, 252, 226, 255))

    for _ in range(44):
        gx, gy = gen.randint(12, width - 13), gen.randint(10, height - 10)
        c = surf.get_at((gx, gy))
        if c.a > 200:
            d = gen.randint(-8, 8)
            surf.set_at((gx, gy), (max(0, min(255, c.r + d)), max(0, min(255, c.g + d)), max(0, min(255, c.b + d)), 255))
    return surf


def generate_boss_empowered_sprite(
    width: int = 64,
    height: int = 64,
    rng: random.Random | None = None,
    direction: str = "down",
    frame: int = 0,
) -> pygame.Surface:
    """Generate a 64x64 SRCALPHA Abyssal Sentinel empowered boss sprite (down/up/side x frames 0..2)."""
    d_key = direction if direction in ("down", "up", "side") else "down"
    f_idx = int(frame) % 3
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, f"boss_empowered_{d_key}_{f_idx}")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2
    l_dy, r_dy, sway = _boss_stride_offsets(f_idx)
    bob = -1 if f_idx != 0 else 0

    obsidian = (20, 16, 28, 255)
    plate_mid = (42, 34, 54, 255)
    plate_hi = (78, 64, 98, 255)
    crimson = (196, 36, 70, 255)
    crimson_hi = (252, 92, 124, 255)
    violet = (162, 68, 226, 220)

    pygame.draw.ellipse(surf, (12, 6, 18, 140), (10, height - 12, width - 20, 9))
    # Floating violet-crimson arcane sigil arcs pulsing around silhouette
    sig_off = (-2, 0, 2)[f_idx]
    pygame.draw.arc(surf, violet, (5, 7 + sig_off, width - 10, height - 18), 0.3, 1.35, 2)
    pygame.draw.arc(surf, crimson, (5, 7 - sig_off, width - 10, height - 18), 1.8, 2.85, 2)

    if d_key == "side":
        # Three-quarter right-facing Abyssal Sentinel with forward horned helm & spiked pauldron
        cape = [(cx - 4, 19 + bob), (9 - sway, 32), (6 - sway, height - 9), (cx + 4, height - 9)]
        pygame.draw.polygon(surf, (44, 16, 30, 255), cape)
        pygame.draw.line(surf, crimson, (9 - sway, 32), (6 - sway, height - 9), 2)
        # Armored legs striding
        pygame.draw.polygon(surf, obsidian, [(cx - 6 - sway, 44), (cx - 1 - sway, 44), (cx - 3 - sway, height - 7), (cx - 9 - sway, height - 7)])
        pygame.draw.polygon(surf, plate_mid, [(cx + 2 + sway, 44), (cx + 9 + sway, 44), (cx + 11 + sway, height - 7), (cx + 4 + sway, height - 7)])
        # Faceted cuirass torso
        cuirass = [(cx - 10, 21 + bob), (cx + 11, 21 + bob), (cx + 13, 45 + bob), (cx - 8, 45 + bob)]
        pygame.draw.polygon(surf, obsidian, cuirass)
        pygame.draw.polygon(surf, crimson, cuirass, 2)
        # Prominent forward spiked pauldron
        pauldron = [(cx - 4, 21 + l_dy // 2 + bob), (cx + 8, 15 + l_dy // 2 + bob), (cx + 16, 25 + l_dy // 2 + bob), (cx + 2, 31 + l_dy // 2 + bob)]
        pygame.draw.polygon(surf, plate_mid, pauldron)
        pygame.draw.polygon(surf, crimson, pauldron, 2)
        pygame.draw.polygon(surf, plate_hi, [(cx + 8, 15 + l_dy // 2 + bob), (cx + 14, 10 + l_dy // 2 + bob), (cx + 12, 19 + l_dy // 2 + bob)])
        # Horned obsidian helm facing right + glowing crimson visor slit
        helm = [(cx - 7, 21 + bob), (cx - 5, 10 + bob), (cx + 8, 10 + bob), (cx + 12, 19 + bob)]
        pygame.draw.polygon(surf, obsidian, helm)
        pygame.draw.polygon(surf, violet, helm, 1)
        pygame.draw.polygon(surf, crimson, [(cx - 4, 11 + bob), (cx - 10, 4 + bob), (cx, 10 + bob)])
        pygame.draw.polygon(surf, crimson, [(cx + 4, 11 + bob), (cx + 12, 4 + bob), (cx + 8, 12 + bob)])
        pygame.draw.line(surf, crimson_hi, (cx + 3, 15 + bob), (cx + 11, 15 + bob), 2)
    elif d_key == "up":
        # Back-turned Abyssal Sentinel (crimson-edged cape, jagged backplate, rear horns, no visor)
        cape = [(cx - 18, 22 + bob), (cx + 18, 22 + bob), (width - 9 + sway, height - 8), (cx, height - 5), (9 + sway, height - 8)]
        pygame.draw.polygon(surf, (38, 14, 28, 255), cape)
        pygame.draw.polygon(surf, crimson, cape, 2)
        backplate = [(cx - 14, 22 + bob), (cx + 14, 22 + bob), (cx + 10, 44 + bob), (cx, 48 + bob), (cx - 10, 44 + bob)]
        pygame.draw.polygon(surf, obsidian, backplate)
        pygame.draw.polygon(surf, plate_hi, backplate, 1)
        pygame.draw.line(surf, violet, (cx, 24 + bob), (cx, 45 + bob), 2)
        for side_p, dy_p in ((-1, l_dy // 2), (1, r_dy // 2)):
            px0 = cx + side_p * 16
            sp = [(px0 - side_p * 5, 22 + dy_p + bob), (px0 + side_p * 7, 15 + dy_p + bob), (px0 + side_p * 9, 28 + dy_p + bob), (px0 - side_p * 3, 30 + dy_p + bob)]
            pygame.draw.polygon(surf, plate_mid, sp)
            pygame.draw.polygon(surf, crimson, sp, 1)
        # Rear horned helm crest
        pygame.draw.ellipse(surf, obsidian, (cx - 9, 10 + bob, 18, 14))
        pygame.draw.polygon(surf, crimson, [(cx - 8, 13 + bob), (cx - 15, 4 + bob), (cx - 4, 10 + bob)])
        pygame.draw.polygon(surf, crimson, [(cx + 8, 13 + bob), (cx + 15, 4 + bob), (cx + 4, 10 + bob)])
    else:
        # Front-facing Abyssal Sentinel (canonical boss_empowered.png)
        # Armored greaves & tassets
        pygame.draw.polygon(surf, obsidian, [(cx - 12, 46), (cx - 4, 46), (cx - 5, height - 7 + l_dy // 2), (cx - 13, height - 7 + l_dy // 2)])
        pygame.draw.polygon(surf, obsidian, [(cx + 4, 46), (cx + 12, 46), (cx + 13, height - 7 + r_dy // 2), (cx + 5, height - 7 + r_dy // 2)])
        # Layered spiked pauldrons
        for side_p, dy_p in ((-1, l_dy // 2), (1, r_dy // 2)):
            px0 = cx + side_p * 16
            pauldron = [
                (px0 - side_p * 5, 21 + dy_p + bob),
                (px0 + side_p * 8, 14 + dy_p + bob),
                (px0 + side_p * 11, 27 + dy_p + bob),
                (px0 - side_p * 2, 31 + dy_p + bob),
            ]
            pygame.draw.polygon(surf, plate_mid, pauldron)
            pygame.draw.polygon(surf, crimson, pauldron, 2)
            # Upward pauldron spike
            pygame.draw.polygon(
                surf, plate_hi,
                [(px0 + side_p * 4, 16 + dy_p + bob), (px0 + side_p * 10, 9 + dy_p + bob), (px0 + side_p * 8, 19 + dy_p + bob)],
            )
        # Faceted obsidian-and-crimson plate cuirass
        cuirass = [(cx - 14, 21 + bob), (cx + 14, 21 + bob), (cx + 11, 46 + bob), (cx, 52 + bob), (cx - 11, 46 + bob)]
        pygame.draw.polygon(surf, obsidian, cuirass)
        pygame.draw.polygon(surf, plate_mid, [(cx - 14, 21 + bob), (cx, 21 + bob), (cx, 52 + bob), (cx - 11, 46 + bob)])
        pygame.draw.polygon(surf, violet, cuirass, 2)
        # Glowing crimson core chest sigil
        core = [(cx, 27 + bob), (cx + 5, 35 + bob), (cx, 43 + bob), (cx - 5, 35 + bob)]
        pygame.draw.polygon(surf, crimson, core)
        pygame.draw.polygon(surf, crimson_hi, [(cx, 30 + bob), (cx + 2, 35 + bob), (cx, 40 + bob), (cx - 2, 35 + bob)])
        # Horned helm with glowing crimson visor slit
        helm = [(cx - 10, 22 + bob), (cx - 9, 10 + bob), (cx, 7 + bob), (cx + 9, 10 + bob), (cx + 10, 22 + bob)]
        pygame.draw.polygon(surf, obsidian, helm)
        pygame.draw.polygon(surf, plate_hi, helm, 1)
        pygame.draw.polygon(surf, crimson, [(cx - 8, 12 + bob), (cx - 16, 3 + bob), (cx - 4, 9 + bob)])
        pygame.draw.polygon(surf, crimson, [(cx + 8, 12 + bob), (cx + 16, 3 + bob), (cx + 4, 9 + bob)])
        eye_dx = -1 if f_idx == 1 else (1 if f_idx == 2 else 0)
        pygame.draw.rect(surf, (10, 6, 16, 255), (cx - 7, 14 + bob, 14, 5), border_radius=2)
        pygame.draw.line(surf, crimson_hi, (cx - 5 + eye_dx, 16 + bob), (cx + 5 + eye_dx, 16 + bob), 2)

    for _ in range(34):
        gx, gy = gen.randint(8, width - 9), gen.randint(6, height - 9)
        c = surf.get_at((gx, gy))
        if c.a > 200:
            d = gen.randint(-10, 10)
            surf.set_at((gx, gy), (max(0, min(255, c.r + d)), max(0, min(255, c.g + d // 2)), max(0, min(255, c.b + d)), 255))
    return surf


def generate_base_enemy_sprite(
    kind: str,
    width: int = 40,
    height: int = 40,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate muted ink/parchment/brass Act 1 base sprites for enemies and bosses."""
    if rng is None:
        rng = _asset_rng(DEFAULT_ASSET_SEED, kind)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx, cy = width // 2, height // 2

    if kind == "bat":
        # Charcoal body & tattered parchment-vellum wings
        wing_col = (158, 142, 114, 255)
        wing_edge = (64, 54, 46, 255)
        pygame.draw.polygon(surf, wing_col, [(cx, cy), (3, cy - 8), (6, cy + 6), (cx - 4, cy + 3)])
        pygame.draw.polygon(surf, wing_col, [(cx, cy), (width - 4, cy - 8), (width - 7, cy + 6), (cx + 4, cy + 3)])
        pygame.draw.line(surf, wing_edge, (cx, cy), (3, cy - 8), 2)
        pygame.draw.line(surf, wing_edge, (cx, cy), (width - 4, cy - 8), 2)
        pygame.draw.circle(surf, (44, 42, 48, 255), (cx, cy), max(6, width // 5))
        pygame.draw.polygon(surf, (44, 42, 48, 255), [(cx - 5, cy - 4), (cx - 3, cy - 11), (cx - 1, cy - 4)])
        pygame.draw.polygon(surf, (44, 42, 48, 255), [(cx + 1, cy - 4), (cx + 3, cy - 11), (cx + 5, cy - 4)])
        surf.set_at((cx - 2, cy - 1), (225, 185, 95, 255))
        surf.set_at((cx + 2, cy - 1), (225, 185, 95, 255))
        surf.set_at((cx - 2, cy + 3), (235, 228, 210, 255))
        surf.set_at((cx + 2, cy + 3), (235, 228, 210, 255))
        return surf

    if kind == "flutter":
        return generate_flutter_frame(frame=0, empowered=False, width=width, height=height, rng=rng)

    if kind == "bindling":
        # Stitched leather-and-twine book-construct crawler
        pygame.draw.rect(surf, (88, 58, 42, 255), (6, 6, width - 12, height - 12), border_radius=5)
        pygame.draw.rect(surf, (54, 34, 24, 255), (8, 7, width - 16, 10), border_radius=3)
        pygame.draw.line(surf, (206, 192, 162, 255), (10, 18), (width - 11, height - 10), 2)
        pygame.draw.line(surf, (206, 192, 162, 255), (width - 11, 18), (10, height - 10), 2)
        pygame.draw.rect(surf, (158, 134, 78, 255), (6, cy - 2, 3, 5))
        pygame.draw.rect(surf, (158, 134, 78, 255), (width - 9, cy - 2, 3, 5))
        pygame.draw.circle(surf, (218, 206, 178, 255), (cx - 1, cy + 2), 2)
        return surf

    if kind == "smear":
        # Amorphous wet-ink blot creature in charcoal-indigo with glossy highlights
        pygame.draw.circle(surf, (24, 22, 34, 245), (cx, cy), width // 3)
        for ang in (0.4, 1.9, 3.5, 5.1):
            lx = cx + int(math.cos(ang) * (width * 0.22))
            ly = cy + int(math.sin(ang) * (height * 0.22))
            pygame.draw.circle(surf, (32, 28, 46, 240), (lx, ly), max(4, width // 5))
        pygame.draw.circle(surf, (130, 195, 210, 245), (cx, cy + 2), 4)
        pygame.draw.arc(surf, (112, 106, 138, 190), (cx - 9, cy - 9, 16, 12), 0.6, 2.5, 1)
        return surf

    if kind == "sentry":
        # Act 1 Scriptorium brass-and-slate hovering turret automaton
        for ang_idx in range(4):
            ang = ang_idx * (math.pi / 2.0) + (math.pi / 4.0)
            fx = cx + int(math.cos(ang) * (width * 0.42))
            fy = cy + int(math.sin(ang) * (height * 0.42))
            pygame.draw.line(surf, (154, 128, 76, 255), (cx, cy), (fx, fy), 3)
            pygame.draw.circle(surf, (110, 152, 184, 255), (fx, fy), 3)
        core = pygame.Rect(7, 7, width - 14, height - 14)
        pygame.draw.rect(surf, (54, 64, 82, 255), core, border_radius=7)
        pygame.draw.rect(surf, (168, 142, 86, 255), core, 2, border_radius=7)
        pygame.draw.circle(surf, (88, 124, 154, 255), (cx, cy), max(6, width // 4), 2)
        pygame.draw.circle(surf, (110, 216, 236, 255), (cx + 3, cy), 4)
        surf.set_at((cx + 2, cy - 1), (240, 252, 255, 255))
        return surf

    if kind == "punctuation_wolf":
        # Act 1 ink-and-parchment calligraphic hound with cyan glyph spine & gold tail tip
        body_poly = [(6, cy + 5), (12, cy - 6), (cx + 4, cy - 8), (width - 6, cy - 1), (cx + 6, cy + 8)]
        pygame.draw.polygon(surf, (32, 38, 52, 255), body_poly)
        pygame.draw.polygon(surf, (218, 194, 146, 255), [(10, cy - 4), (14, 7), (18, cy - 4)])
        pygame.draw.polygon(surf, (218, 194, 146, 255), [(cx - 1, cy - 5), (cx + 3, 6), (cx + 6, cy - 5)])
        pygame.draw.arc(surf, (118, 198, 224, 255), (5, cy - 10, width - 10, 18), 0.2, 2.9, 2)
        pygame.draw.line(surf, (118, 198, 224, 255), (6, cy + 3), (2, cy - 5), 2)
        pygame.draw.circle(surf, (238, 204, 114, 255), (3, cy - 8), 2)
        pygame.draw.line(surf, (238, 226, 196, 255), (width - 9, cy + 1), (width - 9, cy + 6), 2)
        pygame.draw.circle(surf, (242, 212, 126, 255), (width - 12, cy - 3), 2)
        return surf

    if kind == "event_champion":
        # Marginalia event inquisitor-scribe (Overwritten Elite / Relentless Censor)
        pygame.draw.polygon(
            surf,
            (36, 28, 42, 255),
            [(cx, 4), (width - 5, height - 5), (cx, height - 2), (5, height - 5)],
        )
        # Parchment-and-brass inquisitor pauldrons
        pygame.draw.circle(surf, (164, 146, 108, 255), (9, cy - 3), 7)
        pygame.draw.circle(surf, (164, 146, 108, 255), (width - 9, cy - 3), 7)
        pygame.draw.circle(surf, (92, 68, 44, 255), (9, cy - 3), 7, 1)
        pygame.draw.circle(surf, (92, 68, 44, 255), (width - 9, cy - 3), 7, 1)
        # Armored torso with crossed crimson censor sash
        torso = pygame.Rect(9, 10, width - 18, height - 15)
        pygame.draw.rect(surf, (48, 38, 56, 255), torso, border_radius=5)
        pygame.draw.line(surf, (186, 46, 62, 255), (10, 13), (width - 11, height - 7), 3)
        pygame.draw.line(surf, (222, 178, 86, 255), (10, 12), (width - 11, 12), 2)
        # Hooded censor mask with twin amber-gold eyes
        pygame.draw.ellipse(surf, (20, 16, 26, 255), (cx - 8, 5, 16, 13))
        pygame.draw.circle(surf, (246, 198, 92, 255), (cx - 3, 11), 2)
        pygame.draw.circle(surf, (246, 198, 92, 255), (cx + 3, 11), 2)
        return surf

    if kind == "miniboss":
        return generate_miniboss_sprite(width, height, rng=rng, direction="down", frame=0)

    if kind == "night_boss":
        return generate_night_boss_sprite(width, height, rng=rng, direction="down", frame=0)

    return generate_final_author_sprite(width, height, rng=rng, direction="down", frame=0)


def generate_weapon_pickup_sprite(
    variant: str,
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a distinct 40x40 pixel-art weapon pickup sprite for standard or anomalous drops."""
    _ = rng
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    outline = (16, 12, 20, 255)

    # Subtle ground drop shadow beneath every floor weapon
    pygame.draw.ellipse(surf, (10, 8, 14, 115), (7, height - 10, width - 14, 7))

    if variant == "weapon_quill_standard":
        # Classic diagonal ivory calligraphy quill with ink-dipped nib & brass ferrule
        plume = [(16, 22), (18, 11), (26, 5), (34, 5), (33, 13), (26, 20), (19, 24)]
        pygame.draw.polygon(surf, outline, [(x, y) for x, y in plume])
        pygame.draw.polygon(surf, (222, 212, 188, 255), [(17, 21), (19, 12), (26, 6), (33, 6), (32, 13), (25, 19)])
        pygame.draw.polygon(surf, (246, 240, 224, 255), [(20, 16), (26, 8), (31, 7), (28, 13)])
        # Feather notches
        pygame.draw.line(surf, (132, 118, 96, 255), (22, 11), (25, 14), 1)
        pygame.draw.line(surf, (132, 118, 96, 255), (27, 8), (29, 11), 1)
        # Central rachis shaft
        pygame.draw.line(surf, (112, 92, 68, 255), (14, 26), (31, 8), 2)
        # Brass ferrule
        pygame.draw.polygon(surf, (198, 154, 62, 255), [(12, 24), (16, 21), (19, 24), (15, 28)])
        # Dark ink-dipped steel nib pointing SW
        nib = [(6, 33), (12, 24), (16, 28)]
        pygame.draw.polygon(surf, outline, [(5, 34), (12, 23), (17, 28)])
        pygame.draw.polygon(surf, (66, 76, 94, 255), nib)
        pygame.draw.circle(surf, (24, 18, 36, 255), (8, 31), 2)
        return surf

    if variant == "weapon_quill_refined":
        # Elongated silver-and-gilt Archivist's fountain quill with twin vanes & cyan sheen
        pygame.draw.circle(surf, (95, 220, 240, 52), (20, 20), 15)
        plume_outer = [(15, 20), (16, 9), (25, 3), (35, 3), (35, 12), (27, 21), (19, 25)]
        pygame.draw.polygon(surf, outline, plume_outer)
        pygame.draw.polygon(surf, (192, 218, 232, 255), [(16, 19), (18, 10), (26, 4), (34, 4), (34, 12), (26, 20)])
        pygame.draw.polygon(surf, (238, 248, 255, 255), [(19, 16), (25, 6), (32, 5), (29, 12)])
        # Gilded filigree guard collar
        pygame.draw.line(surf, (240, 196, 78, 255), (10, 20), (20, 30), 3)
        pygame.draw.circle(surf, (255, 232, 130, 255), (15, 25), 3)
        # Elongated gleaming silver nib-blade
        pygame.draw.polygon(surf, outline, [(4, 35), (11, 22), (18, 29)])
        pygame.draw.polygon(surf, (160, 228, 248, 255), [(6, 33), (12, 24), (16, 28)])
        pygame.draw.line(surf, (245, 252, 255, 255), (7, 32), (14, 25), 1)
        # Twin golden accent spine
        pygame.draw.line(surf, (218, 174, 62, 255), (16, 24), (32, 7), 2)
        return surf

    if variant == "weapon_scriber_blade":
        # Compact steel Scriber's Letter-Blade / dagger with leather grip & brass crossguard
        blade_outer = [(16, 18), (33, 4), (35, 6), (22, 24)]
        pygame.draw.polygon(surf, outline, [(15, 18), (34, 3), (36, 6), (22, 25)])
        pygame.draw.polygon(surf, (176, 190, 206, 255), blade_outer)
        pygame.draw.polygon(surf, (234, 242, 250, 255), [(18, 18), (33, 5), (31, 9), (20, 20)])
        pygame.draw.line(surf, (112, 124, 140, 255), (19, 20), (31, 8), 1)
        # Brass crossguard
        pygame.draw.line(surf, outline, (11, 16), (24, 29), 5)
        pygame.draw.line(surf, (212, 168, 66, 255), (12, 17), (23, 28), 3)
        # Leather-wrapped grip & pommel
        pygame.draw.line(surf, outline, (7, 33), (17, 23), 6)
        pygame.draw.line(surf, (116, 68, 42, 255), (8, 32), (16, 24), 4)
        pygame.draw.circle(surf, (218, 176, 74, 255), (7, 33), 3)
        return surf

    # Anomalous Weapons (4 passive-keyed + 1 arcane fallback)
    anomalous_palettes = {
        "weapon_anomalous_bleed": ((235, 55, 75), (165, 24, 48), (255, 140, 150)),
        "weapon_anomalous_regen": ((80, 235, 150), (32, 134, 82), (188, 255, 214)),
        "weapon_anomalous_negation": ((255, 195, 60), (166, 112, 24), (255, 238, 160)),
        "weapon_anomalous_stout": ((185, 95, 255), (104, 44, 166), (232, 186, 255)),
        "weapon_anomalous_default": ((175, 75, 250), (96, 38, 156), (226, 178, 255)),
    }
    aura_rgb, deep_rgb, hi_rgb = anomalous_palettes.get(
        variant, anomalous_palettes["weapon_anomalous_default"]
    )
    # Soft arcane halo behind anomalous weapon
    pygame.draw.circle(surf, (*aura_rgb, 68), (20, 19), 16)
    pygame.draw.circle(surf, (*hi_rgb, 48), (20, 19), 11)

    if variant == "weapon_anomalous_bleed":
        # Jagged crimson Ink-Bleed quill-scythe with dripping ruby ink droplets
        vane = [(14, 20), (16, 8), (24, 4), (35, 4), (31, 11), (34, 15), (25, 21), (18, 25)]
        pygame.draw.polygon(surf, outline, vane)
        pygame.draw.polygon(surf, (*deep_rgb, 255), [(15, 19), (17, 9), (25, 5), (34, 5), (30, 12), (24, 20)])
        pygame.draw.polygon(surf, (*aura_rgb, 255), [(18, 16), (24, 7), (32, 6), (27, 13)])
        pygame.draw.line(surf, (*hi_rgb, 255), (15, 24), (31, 8), 2)
        # Hooked crimson blade-nib
        pygame.draw.polygon(surf, outline, [(5, 34), (11, 22), (18, 28), (10, 32)])
        pygame.draw.polygon(surf, (*aura_rgb, 255), [(7, 32), (12, 24), (16, 27)])
        # Dripping crimson ink droplets
        pygame.draw.circle(surf, (*aura_rgb, 255), (9, 36), 2)
        pygame.draw.circle(surf, (*hi_rgb, 255), (14, 34), 1)
    elif variant == "weapon_anomalous_regen":
        # Verdant Life-Thread botanical stylus entwined with luminous emerald stitch-thread
        leaf = [(15, 21), (15, 10), (24, 4), (34, 5), (32, 15), (24, 22), (18, 24)]
        pygame.draw.polygon(surf, outline, leaf)
        pygame.draw.polygon(surf, (*deep_rgb, 255), [(16, 20), (17, 11), (24, 5), (33, 6), (31, 14), (24, 21)])
        pygame.draw.polygon(surf, (*aura_rgb, 255), [(19, 17), (24, 7), (31, 7), (28, 14)])
        # Glowing emerald spine & wrapped thread rings
        pygame.draw.line(surf, (*hi_rgb, 255), (9, 31), (31, 8), 2)
        pygame.draw.arc(surf, (*hi_rgb, 255), (11, 13, 14, 14), 0.3, 3.2, 2)
        pygame.draw.polygon(surf, outline, [(5, 34), (11, 24), (16, 29)])
        pygame.draw.polygon(surf, (*aura_rgb, 255), [(7, 32), (11, 25), (15, 28)])
        pygame.draw.circle(surf, (*hi_rgb, 255), (27, 11), 2)
    elif variant == "weapon_anomalous_negation":
        # Heavy forged golden Iron-Nib broad-blade with wide buckler crossguard
        blade = [(17, 16), (31, 4), (35, 8), (24, 23)]
        pygame.draw.polygon(surf, outline, [(15, 16), (31, 3), (36, 8), (24, 25)])
        pygame.draw.polygon(surf, (*deep_rgb, 255), blade)
        pygame.draw.polygon(surf, (*aura_rgb, 255), [(18, 16), (31, 5), (33, 8), (22, 20)])
        pygame.draw.line(surf, (*hi_rgb, 255), (19, 18), (32, 7), 2)
        # Wide gilded buckler crossguard
        pygame.draw.line(surf, outline, (9, 15), (25, 31), 6)
        pygame.draw.line(surf, (*aura_rgb, 255), (10, 16), (24, 30), 4)
        pygame.draw.circle(surf, (*hi_rgb, 255), (17, 23), 3)
        # Heavy pommel handle
        pygame.draw.line(surf, outline, (7, 33), (16, 24), 6)
        pygame.draw.line(surf, (*deep_rgb, 255), (8, 32), (15, 25), 3)
        pygame.draw.circle(surf, (*hi_rgb, 255), (7, 33), 3)
    elif variant == "weapon_anomalous_stout":
        # Twin-pronged amethyst Stout-Draft manuscript spear-nib with crystal core
        pygame.draw.line(surf, outline, (7, 33), (27, 13), 6)
        pygame.draw.line(surf, (*deep_rgb, 255), (8, 32), (26, 14), 4)
        # Twin spear prongs pointing NE
        pygame.draw.polygon(surf, outline, [(20, 14), (27, 3), (30, 8), (24, 16)])
        pygame.draw.polygon(surf, outline, [(24, 16), (32, 10), (36, 13), (26, 20)])
        pygame.draw.polygon(surf, (*aura_rgb, 255), [(21, 14), (27, 5), (29, 8), (24, 15)])
        pygame.draw.polygon(surf, (*aura_rgb, 255), [(25, 16), (32, 11), (35, 13), (26, 19)])
        # Crystalline void core at collar
        pygame.draw.polygon(surf, (*hi_rgb, 255), [(20, 16), (24, 12), (28, 16), (24, 20)])
        pygame.draw.circle(surf, (*aura_rgb, 255), (8, 32), 3)
    else:
        # Arcane violet star-crested fallback quill
        plume = [(15, 21), (17, 10), (26, 4), (35, 4), (33, 14), (25, 21), (18, 24)]
        pygame.draw.polygon(surf, outline, plume)
        pygame.draw.polygon(surf, (*deep_rgb, 255), [(16, 20), (18, 11), (26, 5), (34, 5), (32, 14), (25, 20)])
        pygame.draw.polygon(surf, (*aura_rgb, 255), [(19, 17), (25, 7), (32, 6), (29, 13)])
        pygame.draw.line(surf, (*hi_rgb, 255), (14, 25), (31, 8), 2)
        pygame.draw.polygon(surf, outline, [(5, 34), (11, 23), (17, 28)])
        pygame.draw.polygon(surf, (*hi_rgb, 255), [(7, 32), (12, 24), (15, 28)])
        # Star crest sparkle
        pygame.draw.line(surf, (*hi_rgb, 255), (26, 7), (26, 13), 1)
        pygame.draw.line(surf, (*hi_rgb, 255), (23, 10), (29, 10), 1)

    return surf


def generate_player_hood_sprite(
    direction: str = "s",
    pose: str = "idle",
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 25-35 deg steep-overhead Scholar hood-and-shoulder pixmap.

    5 unique canonical directions ('n', 'ne', 'e', 'se', 's') across 4 poses
    ('idle', 'walk_0', 'walk_1', 'attack'). Passing 'nw', 'w', or 'sw' mirrors
    the corresponding eastern sprite horizontally.
    """
    d_raw = str(direction or "s").lower()
    mirror_lookup = {"nw": "ne", "w": "e", "sw": "se"}
    flip_x = d_raw in mirror_lookup
    d_key = mirror_lookup.get(d_raw, d_raw)
    if d_key not in ("n", "ne", "e", "se", "s"):
        d_key = "s"

    p_key = str(pose or "idle").lower()
    if p_key not in ("idle", "walk_0", "walk_1", "attack"):
        p_key = "idle"

    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, f"player_hood_{d_key}_{p_key}")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    cx = width // 2
    outline = (14, 18, 28, 255)
    cloak_dark = (22, 38, 76, 255)
    mantle_base = (52, 86, 148, 255)
    mantle_hi = (82, 122, 188, 255)
    hood_base = (42, 72, 130, 255)
    hood_shadow = (26, 44, 86, 255)
    hood_hi = (98, 138, 208, 255)
    cowl_void = (14, 18, 30, 255)
    gold_trim = (215, 185, 110, 255)
    gold_hi = (246, 224, 154, 255)
    eye_glow = (180, 245, 255, 255)
    eye_core = (236, 252, 255, 255)

    # Pose kinematics: stride counter-rotation, bob, and forward attack lunge
    bob_y = 0
    l_sh = 0
    r_sh = 0
    lunge = 0
    tail_sway = 0
    if p_key == "walk_0":
        bob_y = -1
        l_sh = -2
        r_sh = 2
        tail_sway = -2
    elif p_key == "walk_1":
        bob_y = -1
        l_sh = 2
        r_sh = -2
        tail_sway = 2
    elif p_key == "attack":
        bob_y = 1
        l_sh = -2
        r_sh = 3
        lunge = 3
        tail_sway = -3

    if d_key == "s":
        # Facing South (front steep-overhead): broad symmetric mantle, gold stole, glowing twin eyes
        ly = bob_y + (2 if lunge else 0)
        mantle_poly = [
            (cx - 13, 18 + l_sh // 2 + ly),
            (cx - 9, 13 + ly),
            (cx + 9, 13 + ly),
            (cx + 13, 18 + r_sh // 2 + ly),
            (cx + 11, 29 + r_sh // 2 + ly),
            (cx, 31 + ly),
            (cx - 11, 29 + l_sh // 2 + ly),
        ]
        pygame.draw.polygon(surf, cloak_dark, mantle_poly)
        inner_mantle = [
            (cx - 11, 18 + l_sh // 2 + ly),
            (cx - 8, 14 + ly),
            (cx + 8, 14 + ly),
            (cx + 11, 18 + r_sh // 2 + ly),
            (cx + 9, 26 + r_sh // 2 + ly),
            (cx, 28 + ly),
            (cx - 9, 26 + l_sh // 2 + ly),
        ]
        pygame.draw.polygon(surf, mantle_base, inner_mantle)
        pygame.draw.polygon(surf, outline, mantle_poly, 1)
        # Shoulder highlight arcs & gold archival stole + brass throat clasp
        pygame.draw.line(surf, mantle_hi, (cx - 10, 17 + l_sh // 2 + ly), (cx - 5, 15 + ly), 2)
        pygame.draw.line(surf, mantle_hi, (cx + 5, 15 + ly), (cx + 10, 17 + r_sh // 2 + ly), 2)
        pygame.draw.line(surf, gold_trim, (cx - 4, 18 + ly), (cx - 4, 29 + ly), 2)
        pygame.draw.line(surf, gold_trim, (cx + 3, 18 + ly), (cx + 3, 29 + ly), 2)
        pygame.draw.line(surf, gold_trim, (cx - 9, 25 + ly), (cx + 9, 25 + ly), 1)
        pygame.draw.rect(surf, gold_hi, (cx - 2, 18 + ly, 4, 3))

        # Steep-overhead hood crown, subtle top peak, shadowed cowl & twin glowing cyan eyes
        hy = 12 + ly
        peak = [(cx - 3 + tail_sway // 2, hy - 8), (cx + 3 + tail_sway // 2, hy - 8), (cx + tail_sway // 2, hy - 10)]
        pygame.draw.polygon(surf, hood_shadow, peak)
        pygame.draw.ellipse(surf, hood_base, (cx - 9, hy - 8, 18, 16))
        pygame.draw.ellipse(surf, outline, (cx - 9, hy - 8, 18, 16), 1)
        pygame.draw.arc(surf, hood_hi, (cx - 7, hy - 7, 14, 10), 0.35, 2.8, 2)
        pygame.draw.ellipse(surf, cowl_void, (cx - 6, hy - 1, 12, 8))
        pygame.draw.line(surf, gold_trim, (cx - 6, hy + 5), (cx + 6, hy + 5), 1)
        # Glowing cyan eyes under cowl shadow
        pygame.draw.circle(surf, eye_glow, (cx - 3, hy + 3), 2)
        pygame.draw.circle(surf, eye_glow, (cx + 3, hy + 3), 2)
        surf.set_at((cx - 3, hy + 3), eye_core)
        surf.set_at((cx + 3, hy + 3), eye_core)

    elif d_key == "se":
        # Facing Southeast (3/4 front-right steep-overhead)
        ox = 1 + (2 if lunge else 0)
        oy = bob_y + (2 if lunge else 0)
        mantle_poly = [
            (cx - 12 + ox // 2, 17 + l_sh // 2 + oy),
            (cx - 5 + ox // 2, 13 + oy),
            (cx + 9 + ox, 14 + oy),
            (cx + 12 + ox, 20 + r_sh // 2 + oy),
            (cx + 8 + ox, 30 + oy),
            (cx - 4 + ox // 2, 30 + oy),
            (cx - 11 + ox // 2, 26 + l_sh // 2 + oy),
        ]
        pygame.draw.polygon(surf, cloak_dark, mantle_poly)
        inner_mantle = [
            (cx - 10 + ox // 2, 18 + l_sh // 2 + oy),
            (cx - 4 + ox // 2, 14 + oy),
            (cx + 8 + ox, 15 + oy),
            (cx + 10 + ox, 20 + r_sh // 2 + oy),
            (cx + 6 + ox, 27 + oy),
            (cx - 3 + ox // 2, 27 + oy),
            (cx - 9 + ox // 2, 24 + l_sh // 2 + oy),
        ]
        pygame.draw.polygon(surf, mantle_base, inner_mantle)
        pygame.draw.polygon(surf, outline, mantle_poly, 1)
        pygame.draw.line(surf, mantle_hi, (cx - 8 + ox // 2, 16 + oy), (cx + 4 + ox, 15 + oy), 2)
        # Off-center 3/4 gold stole & shoulder clasp
        pygame.draw.line(surf, gold_trim, (cx + 1 + ox, 18 + oy), (cx + 3 + ox, 29 + oy), 2)
        pygame.draw.line(surf, gold_trim, (cx - 6 + ox // 2, 23 + oy), (cx + 8 + ox, 26 + oy), 1)
        pygame.draw.rect(surf, gold_hi, (cx + 2 + ox, 18 + oy, 3, 3))

        # Angled hood with NW trailing peak and lower-right cowl + 3/4 twin eyes
        hx, hy = cx + ox, 12 + oy
        hood_tail = [
            (hx - 11 + tail_sway // 2, hy - 5),
            (hx - 4, hy - 8),
            (hx - 6, hy + 1),
        ]
        pygame.draw.polygon(surf, hood_shadow, hood_tail)
        pygame.draw.polygon(surf, outline, hood_tail, 1)
        pygame.draw.ellipse(surf, hood_base, (hx - 9, hy - 8, 17, 15))
        pygame.draw.ellipse(surf, outline, (hx - 9, hy - 8, 17, 15), 1)
        pygame.draw.arc(surf, hood_hi, (hx - 8, hy - 7, 13, 10), 0.5, 2.9, 2)
        pygame.draw.ellipse(surf, cowl_void, (hx - 2, hy - 1, 9, 8))
        pygame.draw.circle(surf, eye_glow, (hx + 1, hy + 3), 2)
        pygame.draw.circle(surf, eye_glow, (hx + 5, hy + 3), 1)
        surf.set_at((hx + 1, hy + 3), eye_core)
        surf.set_at((hx + 5, hy + 3), eye_core)

    elif d_key == "e":
        # Facing East (right profile steep-overhead): sweeping left hood peak & single side eye
        ox = 1 + lunge
        oy = bob_y
        # Trailing back-mantle cape fold to the left
        back_fold = [
            (cx - 12 + tail_sway // 2, 17 + oy),
            (cx - 3 + ox // 2, 14 + oy),
            (cx - 2 + ox // 2, 28 + oy),
            (cx - 11 + tail_sway // 2, 27 + oy),
        ]
        pygame.draw.polygon(surf, cloak_dark, back_fold)
        pygame.draw.polygon(surf, outline, back_fold, 1)
        # Compact side-profile shoulder mantle
        mantle_poly = [
            (cx - 8 + ox // 2, 15 + l_sh // 2 + oy),
            (cx + 5 + ox, 14 + oy),
            (cx + 10 + ox, 20 + r_sh // 2 + oy),
            (cx + 7 + ox, 29 + oy),
            (cx - 5 + ox // 2, 29 + oy),
            (cx - 9 + ox // 2, 23 + l_sh // 2 + oy),
        ]
        pygame.draw.polygon(surf, mantle_base, mantle_poly)
        pygame.draw.polygon(surf, outline, mantle_poly, 1)
        pygame.draw.line(surf, mantle_hi, (cx - 5 + ox // 2, 16 + oy), (cx + 5 + ox, 16 + oy), 2)
        pygame.draw.line(surf, gold_trim, (cx + 5 + ox, 17 + oy), (cx + 6 + ox, 28 + oy), 2)
        pygame.draw.line(surf, gold_trim, (cx - 6 + ox // 2, 25 + oy), (cx + 6 + ox, 25 + oy), 1)
        pygame.draw.rect(surf, gold_hi, (cx + 4 + ox, 17 + oy, 3, 3))

        # Sculpted profile hood with long rear point sweeping West
        hx, hy = cx + ox, 11 + oy
        hood_peak = [
            (hx - 13 + tail_sway // 2, hy - 1),
            (hx - 4, hy - 7),
            (hx - 3, hy + 4),
        ]
        pygame.draw.polygon(surf, hood_shadow, hood_peak)
        pygame.draw.polygon(surf, outline, hood_peak, 1)
        pygame.draw.ellipse(surf, hood_base, (hx - 8, hy - 7, 16, 14))
        pygame.draw.ellipse(surf, outline, (hx - 8, hy - 7, 16, 14), 1)
        pygame.draw.arc(surf, hood_hi, (hx - 7, hy - 6, 12, 9), 0.7, 2.9, 2)
        # Right-side cowl cavity & single bright profile eye
        pygame.draw.ellipse(surf, cowl_void, (hx + 1, hy - 3, 7, 9))
        pygame.draw.circle(surf, eye_glow, (hx + 5, hy + 1), 2)
        surf.set_at((hx + 5, hy + 1), eye_core)

    elif d_key == "ne":
        # Facing Northeast (3/4 back-right steep-overhead): draped hood tail down-left, no forward eyes
        ox = 1 + (2 if lunge else 0)
        oy = bob_y - (2 if lunge else 0)
        mantle_poly = [
            (cx - 12 + ox // 2, 18 + l_sh // 2 + oy),
            (cx - 6 + ox // 2, 13 + oy),
            (cx + 8 + ox, 13 + oy),
            (cx + 12 + ox, 19 + r_sh // 2 + oy),
            (cx + 9 + ox, 29 + oy),
            (cx - 4 + ox // 2, 30 + oy),
            (cx - 11 + ox // 2, 27 + l_sh // 2 + oy),
        ]
        pygame.draw.polygon(surf, cloak_dark, mantle_poly)
        inner_mantle = [
            (cx - 10 + ox // 2, 19 + l_sh // 2 + oy),
            (cx - 5 + ox // 2, 14 + oy),
            (cx + 7 + ox, 14 + oy),
            (cx + 10 + ox, 19 + r_sh // 2 + oy),
            (cx + 7 + ox, 26 + oy),
            (cx - 3 + ox // 2, 27 + oy),
            (cx - 9 + ox // 2, 24 + l_sh // 2 + oy),
        ]
        pygame.draw.polygon(surf, mantle_base, inner_mantle)
        pygame.draw.polygon(surf, outline, mantle_poly, 1)
        # Diagonal rear gold yoke & shoulder ridge
        pygame.draw.line(surf, gold_trim, (cx - 8 + ox // 2, 24 + oy), (cx + 8 + ox, 22 + oy), 1)
        pygame.draw.line(surf, gold_trim, (cx - 1 + ox // 2, 17 + oy), (cx - 3 + ox // 2, 29 + oy), 2)
        pygame.draw.line(surf, mantle_hi, (cx - 4 + ox // 2, 15 + oy), (cx + 7 + ox, 15 + oy), 2)

        # Back-turned 3/4 hood crown with small cowl rim sliver on far upper-right & draped SW hood tail
        hx, hy = cx + ox, 11 + oy
        pygame.draw.ellipse(surf, hood_base, (hx - 9, hy - 7, 17, 15))
        pygame.draw.ellipse(surf, outline, (hx - 9, hy - 7, 17, 15), 1)
        pygame.draw.arc(surf, hood_hi, (hx - 7, hy - 6, 13, 9), 0.3, 2.7, 2)
        # Faint far-side cowl shadow sliver at upper-right temple (no eyes)
        pygame.draw.line(surf, cowl_void, (hx + 6, hy - 3), (hx + 7, hy + 2), 2)
        # Pointed hood tail draping down-left across the upper back
        drape_tail = [
            (hx - 6, hy + 1),
            (hx + 2, hy + 3),
            (hx - 7 + tail_sway // 2, hy + 11),
        ]
        pygame.draw.polygon(surf, hood_shadow, drape_tail)
        pygame.draw.polygon(surf, outline, drape_tail, 1)
        pygame.draw.line(surf, gold_trim, (hx - 5, hy + 6), (hx - 6 + tail_sway // 2, hy + 10), 1)

    else:
        # Facing North (full back steep-overhead): symmetric back-mantle, gold spine seam, centered hood tail
        ly = bob_y - (2 if lunge else 0)
        mantle_poly = [
            (cx - 13, 18 + l_sh // 2 + ly),
            (cx - 9, 13 + ly),
            (cx + 9, 13 + ly),
            (cx + 13, 18 + r_sh // 2 + ly),
            (cx + 11, 29 + r_sh // 2 + ly),
            (cx, 31 + ly),
            (cx - 11, 29 + l_sh // 2 + ly),
        ]
        pygame.draw.polygon(surf, cloak_dark, mantle_poly)
        inner_mantle = [
            (cx - 11, 18 + l_sh // 2 + ly),
            (cx - 8, 14 + ly),
            (cx + 8, 14 + ly),
            (cx + 11, 18 + r_sh // 2 + ly),
            (cx + 9, 26 + r_sh // 2 + ly),
            (cx, 28 + ly),
            (cx - 9, 26 + l_sh // 2 + ly),
        ]
        pygame.draw.polygon(surf, mantle_base, inner_mantle)
        pygame.draw.polygon(surf, outline, mantle_poly, 1)
        # Back-mantle shoulder rim highlights & central gold spine seam
        pygame.draw.line(surf, mantle_hi, (cx - 9, 16 + l_sh // 2 + ly), (cx - 4, 14 + ly), 2)
        pygame.draw.line(surf, mantle_hi, (cx + 4, 14 + ly), (cx + 9, 16 + r_sh // 2 + ly), 2)
        pygame.draw.line(surf, gold_trim, (cx, 19 + ly), (cx + tail_sway // 2, 30 + ly), 2)
        pygame.draw.line(surf, gold_trim, (cx - 9, 25 + ly), (cx + 9, 25 + ly), 1)

        # Back of hood crown + prominent hanging pointed hood tail down center-back (no face/eyes)
        hy = 11 + ly
        pygame.draw.ellipse(surf, hood_base, (cx - 9, hy - 7, 18, 15))
        pygame.draw.ellipse(surf, outline, (cx - 9, hy - 7, 18, 15), 1)
        pygame.draw.arc(surf, hood_hi, (cx - 7, hy - 6, 14, 9), 0.35, 2.8, 2)
        hood_tail = [
            (cx - 5, hy + 2),
            (cx + 5, hy + 2),
            (cx + tail_sway, hy + 13),
        ]
        pygame.draw.polygon(surf, hood_shadow, hood_tail)
        pygame.draw.polygon(surf, outline, hood_tail, 1)
        pygame.draw.line(surf, hood_base, (cx - 2, hy + 4), (cx + tail_sway // 2, hy + 10), 2)
        surf.set_at((cx + tail_sway, hy + 12), gold_hi)

    # Subtle fabric-weave micro-grit on indigo hood/mantle pixels (preserving eyes, gold trim, and dark outline)
    for _ in range(18):
        gx = gen.randint(6, width - 7)
        gy = gen.randint(5, height - 9)
        col = surf.get_at((gx, gy))
        if col.a > 220 and col.b > col.r + 18 and col.r < 140:
            jit = gen.randint(-8, 8)
            surf.set_at(
                (gx, gy),
                (_clamp(col.r + jit), _clamp(col.g + jit), _clamp(col.b + jit), col.a),
            )

    if flip_x:
        surf = pygame.transform.flip(surf, True, False)
    return surf


def _clamp_rgb_delta(base: Tuple[int, int, int], dr: int, dg: int, db: int, limit: int = 12) -> Tuple[int, int, int]:
    """Offset a base RGB color while strictly bounding each channel delta to <= +-limit."""
    return (
        max(0, min(255, base[0] + max(-limit, min(limit, dr)))),
        max(0, min(255, base[1] + max(-limit, min(limit, dg)))),
        max(0, min(255, base[2] + max(-limit, min(limit, db)))),
    )


def generate_sanctuary_flagstone_tile(
    variant_index: int = 0,
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a low-contrast weathered Sanctuary courtyard flagstone tile (delta <= +-12 RGB)."""
    gen = rng if rng is not None else random.Random(4100 + variant_index * 37)
    base = (66, 61, 55)
    surf = pygame.Surface((width, height))
    surf.fill(base)

    # 1. Subtle low-contrast stone grain across the tile (+-6 RGB)
    for y in range(height):
        for x in range(width):
            grain = gen.randint(-6, 6)
            tint = gen.randint(-2, 2)
            surf.set_at((x, y), _clamp_rgb_delta(base, grain + tint, grain, grain - tint, limit=12))

    # 2. Soft staggered courtyard flagstone seams (within -10..+6 RGB, no harsh gridlines)
    seam_col = _clamp_rgb_delta(base, -10, -10, -9, limit=12)
    hi_col = _clamp_rgb_delta(base, 6, 6, 5, limit=12)
    h_split = 18 + (variant_index % 2) * 4
    v_top = 14 + (variant_index * 7) % 14
    v_bot = (v_top + 18) % (width - 8) + 4

    pygame.draw.line(surf, seam_col, (0, h_split), (width - 1, h_split), 1)
    pygame.draw.line(surf, hi_col, (0, min(height - 1, h_split + 1)), (width - 1, min(height - 1, h_split + 1)), 1)
    pygame.draw.line(surf, seam_col, (v_top, 0), (v_top, h_split), 1)
    pygame.draw.line(surf, seam_col, (v_bot, h_split), (v_bot, height - 1), 1)

    # 3. Delicate hairline stone cracks on odd variants
    if variant_index in (1, 3):
        crack_col = _clamp_rgb_delta(base, -11, -11, -10, limit=12)
        cx = 8 + variant_index * 6
        cy = 6 + (variant_index % 2) * 14
        pts = [(cx, cy), (cx + 4, cy + 3), (cx + 6, cy + 8), (cx + 10, cy + 10)]
        pygame.draw.lines(surf, crack_col, False, pts, 1)

    # 4. Subtle muted moss speckles along joints on variants 2 and 3 (strictly <= +-12 RGB)
    if variant_index in (2, 3):
        moss_col = _clamp_rgb_delta(base, -10, 9, -8, limit=12)
        for _ in range(10 + variant_index * 3):
            mx = gen.randint(2, width - 3)
            my = h_split + gen.randint(-2, 2) if gen.random() < 0.7 else gen.randint(2, height - 3)
            my = max(0, min(height - 1, my))
            surf.set_at((mx, my), moss_col)

    return surf


def generate_sanctuary_dirt_path_tile(
    variant_index: int = 0,
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a low-contrast worn Sanctuary garden dirt path tile (delta <= +-12 RGB)."""
    gen = rng if rng is not None else random.Random(4200 + variant_index * 41)
    base = (82, 66, 50)
    surf = pygame.Surface((width, height))
    surf.fill(base)

    # 1. Soft organic earth grit with faint horizontal foot-worn streaks
    for y in range(height):
        row_shift = -2 if (y + variant_index * 3) % 7 < 2 else 0
        for x in range(width):
            grain = gen.randint(-6, 6) + row_shift
            surf.set_at((x, y), _clamp_rgb_delta(base, grain, grain - 1, grain - 2, limit=12))

    # 2. Scattered low-contrast pebbles & worn depressions
    pebble_hi = _clamp_rgb_delta(base, 10, 9, 8, limit=12)
    pebble_lo = _clamp_rgb_delta(base, -10, -10, -9, limit=12)
    for _ in range(7 + variant_index * 2):
        px = gen.randint(2, width - 4)
        py = gen.randint(2, height - 4)
        surf.set_at((px, py), pebble_hi)
        surf.set_at((px + 1, py + 1), pebble_lo)

    # 3. Sparse mossy/grass edge flecks on variants 2 and 3
    if variant_index in (2, 3):
        fleck = _clamp_rgb_delta(base, -10, 10, -8, limit=12)
        for _ in range(9):
            fx = gen.randint(1, width - 2)
            fy = gen.randint(1, height - 2)
            surf.set_at((fx, fy), fleck)

    return surf


def generate_sanctuary_wood_floor_tile(
    variant_index: int = 0,
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a low-contrast warm Scriptorium wooden floorboard tile (delta <= +-12 RGB)."""
    gen = rng if rng is not None else random.Random(4300 + variant_index * 53)
    base = (78, 57, 41)
    surf = pygame.Surface((width, height))
    surf.fill(base)

    plank_h = 10
    seam_col = _clamp_rgb_delta(base, -11, -10, -9, limit=12)
    hi_col = _clamp_rgb_delta(base, 7, 6, 4, limit=12)
    nail_col = _clamp_rgb_delta(base, -12, -12, -11, limit=12)

    for plank_idx in range(height // plank_h):
        y0 = plank_idx * plank_h
        plank_shift = ((plank_idx + variant_index) % 3 - 1) * 3
        for y in range(y0, min(height, y0 + plank_h)):
            streak = ((y - y0) % 3 - 1) * 2
            for x in range(width):
                grain = plank_shift + streak + gen.randint(-3, 3)
                surf.set_at((x, y), _clamp_rgb_delta(base, grain, grain, grain - 1, limit=12))
        # Soft plank joint and top highlight
        pygame.draw.line(surf, seam_col, (0, y0), (width - 1, y0), 1)
        if y0 + 1 < height:
            pygame.draw.line(surf, hi_col, (0, y0 + 1), (width - 1, y0 + 1), 1)
        # Staggered vertical plank end-seam with subtle nail dots
        joint_x = (8 + plank_idx * 13 + variant_index * 9) % (width - 6) + 3
        pygame.draw.line(surf, seam_col, (joint_x, y0), (joint_x, min(height - 1, y0 + plank_h - 1)), 1)
        if joint_x + 2 < width and y0 + 3 < height:
            surf.set_at((joint_x + 2, y0 + 3), nail_col)
        if joint_x + 2 < width and y0 + plank_h - 3 < height:
            surf.set_at((joint_x + 2, y0 + plank_h - 3), nail_col)

    return surf


def generate_sanctuary_roof_tile(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
    variant: int = 0,
) -> pygame.Surface:
    """Generate a 40x40 weathered dark slate roof shingle tile (variants 0..3; clean base without grid moss)."""
    v_idx = int(variant) % 4
    gen = rng if rng is not None else random.Random(4401 + v_idx * 97)
    base_tones = (
        (42, 46, 56),
        (39, 43, 53),
        (44, 48, 57),
        (40, 44, 52),
    )
    base = base_tones[v_idx]
    surf = pygame.Surface((width, height))
    surf.fill(base)

    course_h = 10
    for row_idx in range(height // course_h):
        y0 = row_idx * course_h
        offset_x = ((row_idx + (v_idx % 2)) % 2) * 10
        for y in range(y0, min(height, y0 + course_h)):
            shade = -6 if y >= y0 + course_h - 2 else (6 if y == y0 else 0)
            for x in range(width):
                shingle_id = (x + offset_x) // 20
                tile_shift = ((shingle_id * 5 + row_idx * 3 + v_idx * 7) % 5) - 2
                n = gen.randint(-3, 3) + shade + tile_shift
                surf.set_at((x, y), _clamp_rgb_delta(base, n, n + 1, n + 3, limit=18))
        # Overlapping shingle course shadow & top highlight
        bot_y = min(height - 1, y0 + course_h - 1)
        pygame.draw.line(surf, (24, 27, 35), (0, bot_y), (width - 1, bot_y), 1)
        pygame.draw.line(surf, (58, 64, 78), (0, y0), (width - 1, y0), 1)
        # Shingle vertical dividers
        for sx in range(offset_x, width, 20):
            pygame.draw.line(surf, (28, 31, 40), (sx, y0), (sx, bot_y), 1)

    # Subtle per-variant weathering (variant 0 stays completely clean slate; moss is composited organically per-roof)
    if v_idx == 1:
        # Faint rain-streaked darker shingle & tiny corner lichen speck
        pygame.draw.rect(surf, (34, 38, 48), (11, 11, 18, 7))
        pygame.draw.line(surf, (50, 56, 68), (11, 11), (28, 11), 1)
        pygame.draw.circle(surf, (52, 70, 48), (29, 19), 2)
    elif v_idx == 2:
        # Chipped slate corner & single understated seam moss tuft
        pygame.draw.polygon(surf, (26, 29, 38), [(20, 20), (24, 20), (20, 24)])
        pygame.draw.ellipse(surf, (46, 66, 42), (4, 28, 9, 4))
        pygame.draw.ellipse(surf, (62, 86, 54), (5, 28, 5, 2))
    elif v_idx == 3:
        # Subtle warm weathered slate patch & damp seam streak
        pygame.draw.rect(surf, (47, 50, 58), (2, 21, 16, 7))
        pygame.draw.line(surf, (30, 34, 42), (24, 3), (34, 37), 1)

    return surf


def generate_sanctuary_chimney(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT * 2,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x80 SRCALPHA stone chimney stack with corbeled cap and faint hearth smoke."""
    gen = rng if rng is not None else random.Random(4402)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    outline = (18, 16, 22, 255)

    # Soft wispy smoke plumes curling above the flue
    for sx, sy, sr, alpha in ((20, 12, 6, 62), (24, 7, 5, 48), (18, 4, 4, 34)):
        pygame.draw.circle(surf, (175, 178, 188, alpha), (sx, sy), sr)

    # Main masonry stack rising from lower roof anchor (y=24..76)
    stack_rect = pygame.Rect(8, 24, width - 16, height - 28)
    pygame.draw.rect(surf, outline, stack_rect.inflate(2, 2))
    pygame.draw.rect(surf, (76, 72, 68, 255), stack_rect)

    # Brick/stone courses and mortar joints
    for cy in range(28, height - 4, 6):
        pygame.draw.line(surf, (44, 41, 40, 255), (stack_rect.left, cy), (stack_rect.right - 1, cy), 1)
        off = 4 if ((cy // 6) % 2 == 0) else 10
        for cx in range(stack_rect.left + off, stack_rect.right - 2, 10):
            pygame.draw.line(surf, (44, 41, 40, 255), (cx, cy - 6), (cx, cy), 1)
    # Stone grit & left-side highlight
    for _ in range(36):
        gx = gen.randint(stack_rect.left + 1, stack_rect.right - 2)
        gy = gen.randint(stack_rect.top + 1, stack_rect.bottom - 2)
        delta = gen.randint(-12, 12)
        grit_rgb = _clamp_rgb_delta((76, 72, 68), delta, delta, delta, limit=12)
        surf.set_at((gx, gy), (*grit_rgb, 255))
    pygame.draw.line(
        surf,
        (108, 102, 96, 255),
        (stack_rect.left + 1, stack_rect.top),
        (stack_rect.left + 1, stack_rect.bottom - 1),
        2,
    )

    # Corbeled stone chimney cap & dark soot flue
    cap_rect = pygame.Rect(5, 16, width - 10, 9)
    pygame.draw.rect(surf, outline, cap_rect.inflate(2, 2))
    pygame.draw.rect(surf, (94, 90, 86, 255), cap_rect)
    pygame.draw.line(surf, (124, 120, 114, 255), (cap_rect.left, cap_rect.top), (cap_rect.right - 1, cap_rect.top), 2)
    pygame.draw.rect(surf, (24, 22, 26, 255), (12, 17, width - 24, 4))

    # Moss tuft near the roof flashing base
    pygame.draw.ellipse(surf, (54, 78, 48, 255), (8, height - 10, 12, 5))
    pygame.draw.ellipse(surf, (72, 100, 60, 255), (10, height - 9, 7, 3))
    return surf


def generate_sanctuary_tree_canopy(
    width: int = TILE_WIDTH * 2,
    height: int = 100,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate an 80x100 SRCALPHA multi-tile gnarled Sanctuary oak/willow anchored on a 40x40 base."""
    gen = rng if rng is not None else random.Random(4403)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2

    # 1. Soft dappled ground shadow beneath base footprint (y=78..98)
    pygame.draw.ellipse(surf, (12, 16, 12, 115), (14, height - 22, width - 28, 18))

    # 2. Gnarled buttress roots & twisted oak trunk anchored in lower 40x40 (x=20..60, y=54..92)
    trunk_pts = [
        (cx - 14, height - 10),
        (cx - 8, height - 24),
        (cx - 7, height - 46),
        (cx + 7, height - 46),
        (cx + 8, height - 24),
        (cx + 14, height - 10),
        (cx + 5, height - 13),
        (cx, height - 8),
        (cx - 5, height - 13),
    ]
    pygame.draw.polygon(surf, (24, 18, 14, 255), trunk_pts)
    inner_trunk = [
        (cx - 10, height - 12),
        (cx - 6, height - 24),
        (cx - 5, height - 46),
        (cx + 5, height - 46),
        (cx + 6, height - 24),
        (cx + 10, height - 12),
    ]
    pygame.draw.polygon(surf, (68, 48, 34, 255), inner_trunk)
    pygame.draw.line(surf, (94, 70, 48, 255), (cx - 4, height - 44), (cx - 5, height - 16), 2)
    pygame.draw.line(surf, (44, 30, 22, 255), (cx + 2, height - 42), (cx + 3, height - 14), 2)
    # Moss creeping up trunk base
    pygame.draw.ellipse(surf, (56, 86, 48, 255), (cx - 10, height - 20, 10, 6))

    # 3. Layered gnarled oak/willow canopy crown (y=6..66)
    deep_leaf = (28, 52, 34, 255)
    mid_leaf = (46, 82, 48, 255)
    lit_leaf = (76, 118, 66, 255)
    sun_leaf = (108, 146, 82, 255)

    # Dark outer silhouette lobes
    outer_lobes = [
        (cx, 34, 34),
        (cx - 18, 38, 20),
        (cx + 18, 38, 20),
        (cx - 14, 22, 18),
        (cx + 14, 22, 18),
        (cx, 18, 18),
    ]
    for lx, ly, lr in outer_lobes:
        pygame.draw.circle(surf, (18, 32, 22, 255), (lx, ly), lr + 2)
    for lx, ly, lr in outer_lobes:
        pygame.draw.circle(surf, deep_leaf, (lx, ly), lr)

    # Midtone foliage clusters
    mid_lobes = [
        (cx - 16, 34, 15),
        (cx + 15, 35, 14),
        (cx - 10, 20, 14),
        (cx + 12, 21, 13),
        (cx, 28, 18),
    ]
    for lx, ly, lr in mid_lobes:
        pygame.draw.circle(surf, mid_leaf, (lx, ly), lr)

    # Sunlit upper-left canopy highlights & dappled leaf specks
    for lx, ly, lr in ((cx - 12, 18, 10), (cx + 6, 16, 9), (cx - 18, 30, 8), (cx + 2, 26, 9)):
        pygame.draw.circle(surf, lit_leaf, (lx, ly), lr)
    for _ in range(42):
        sx = gen.randint(12, width - 13)
        sy = gen.randint(10, 52)
        if surf.get_at((sx, sy))[3] > 0:
            surf.set_at((sx, sy), sun_leaf if gen.random() < 0.45 else lit_leaf)

    # Drooping willow tendrils framing left & right canopy skirt
    for vx in (14, 20, 26, 54, 60, 66):
        vy0 = 46 + (vx % 5)
        vlen = gen.randint(10, 17)
        pygame.draw.line(surf, mid_leaf, (vx, vy0), (vx + gen.randint(-1, 1), vy0 + vlen), 2)
        pygame.draw.line(surf, lit_leaf, (vx, vy0), (vx, vy0 + vlen // 2), 1)

    return surf


def generate_pond_lily_reeds(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA water lily & cattail reed cluster for the Sanctuary pond."""
    _ = rng
    surf = pygame.Surface((width, height), pygame.SRCALPHA)

    # Soft translucent water ripple rings
    pygame.draw.ellipse(surf, (130, 188, 198, 90), (4, 16, 26, 18), 1)
    pygame.draw.ellipse(surf, (150, 212, 220, 70), (8, 20, 18, 11), 1)

    # Two notched emerald lily pads
    for cx, cy, r in ((15, 25, 8), (24, 19, 6)):
        pygame.draw.circle(surf, (24, 54, 34, 255), (cx, cy), r + 1)
        pygame.draw.circle(surf, (46, 104, 58, 255), (cx, cy), r)
        pygame.draw.circle(surf, (74, 138, 76, 255), (cx - 1, cy - 1), max(2, r - 3))
        # Classic V-notch wedge
        pygame.draw.polygon(surf, (0, 0, 0, 0), [(cx, cy), (cx + r + 1, cy - 2), (cx + r + 1, cy + 3)])

    # Pale cream-rose water lily blossom on primary pad
    bx, by = 14, 24
    for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, -2)):
        pygame.draw.circle(surf, (238, 216, 220, 255), (bx + dx, by + dy), 2)
    pygame.draw.circle(surf, (245, 205, 95, 255), (bx, by), 2)

    # Swaying cattail reeds on the right flank
    for rx, top_y in ((31, 6), (35, 10), (28, 12)):
        pygame.draw.line(surf, (42, 84, 44, 255), (rx, height - 4), (rx - 2, top_y), 2)
        pygame.draw.line(surf, (76, 124, 62, 255), (rx - 1, height - 4), (rx - 3, top_y + 4), 1)
    # Velvet brown cattail heads
    pygame.draw.rect(surf, (96, 56, 34, 255), (28, 8, 3, 8), border_radius=1)
    pygame.draw.rect(surf, (112, 68, 42, 255), (32, 12, 3, 7), border_radius=1)
    return surf


def generate_garden_flora(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA fern and courtyard wildflower cluster for Sanctuary gardens."""
    gen = rng if rng is not None else random.Random(4405)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx, cy = width // 2, height // 2 + 2

    # Soft ground shadow
    pygame.draw.ellipse(surf, (14, 22, 14, 95), (6, height - 13, width - 12, 9))

    # Radiating dark-emerald fern fronds
    frond_tips = [
        (6, 12), (12, 6), (22, 5), (32, 9), (35, 19), (32, 30), (20, 33), (9, 29), (5, 21),
    ]
    for tx, ty in frond_tips:
        pygame.draw.line(surf, (28, 62, 36, 255), (cx, cy), (tx, ty), 3)
        pygame.draw.line(surf, (56, 108, 56, 255), (cx, cy), (tx, ty), 1)
        mid_x, mid_y = (cx + tx) // 2, (cy + ty) // 2
        pygame.draw.circle(surf, (48, 96, 48, 255), (mid_x, mid_y), 3)

    # Layered clover/herb foliage core
    for _ in range(10):
        lx = cx + gen.randint(-9, 9)
        ly = cy + gen.randint(-7, 7)
        pygame.draw.circle(surf, (70, 126, 62, 255), (lx, ly), 3)

    # Muted gold & lavender-cream courtyard wildflowers
    blossoms = [
        ((13, 14), (235, 198, 96, 255)),
        ((26, 13), (212, 196, 232, 255)),
        ((23, 25), (235, 198, 96, 255)),
        ((14, 24), (226, 218, 238, 255)),
        ((20, 17), (242, 212, 118, 255)),
    ]
    for (fx, fy), col in blossoms:
        pygame.draw.circle(surf, col, (fx, fy), 2)
        surf.set_at((fx, fy), (255, 248, 226, 255))
    return surf


def generate_locked_shed_door(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA weathered timber shed door secured by a brass padlock."""
    _ = rng
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    outline = (20, 15, 14, 255)

    # Stone jamb & lintel frame
    pygame.draw.rect(surf, outline, (4, 2, width - 8, height - 3), border_radius=2)
    pygame.draw.rect(surf, (82, 78, 74, 255), (5, 3, width - 10, height - 5), border_radius=2)
    pygame.draw.line(surf, (112, 108, 102, 255), (5, 3), (width - 6, 3), 2)

    # Recessed weathered wooden door planks
    door = pygame.Rect(9, 7, width - 18, height - 10)
    pygame.draw.rect(surf, (76, 52, 34, 255), door)
    for px in range(door.left + 5, door.right, 5):
        pygame.draw.line(surf, (46, 30, 20, 255), (px, door.top), (px, door.bottom - 1), 1)
    # Cross-brace timber bars
    pygame.draw.rect(surf, (62, 42, 28, 255), (door.left, door.top + 5, door.width, 4))
    pygame.draw.rect(surf, (62, 42, 28, 255), (door.left, door.bottom - 9, door.width, 4))

    # Wrought-iron strap hinges on left edge
    for hy in (12, 27):
        pygame.draw.rect(surf, (38, 40, 46, 255), (door.left, hy, 10, 3))
        surf.set_at((door.left + 8, hy + 1), (96, 100, 110, 255))

    # Iron hasp + prominent tarnished brass padlock on right side
    pygame.draw.rect(surf, (46, 48, 54, 255), (door.right - 10, 18, 9, 4))
    pygame.draw.arc(surf, (148, 154, 166, 255), (door.right - 9, 17, 7, 7), 0.0, 3.14, 2)
    pygame.draw.rect(surf, outline, (door.right - 10, 21, 9, 9), border_radius=1)
    pygame.draw.rect(surf, (206, 162, 58, 255), (door.right - 9, 22, 7, 7), border_radius=1)
    pygame.draw.line(surf, (242, 212, 116, 255), (door.right - 9, 22), (door.right - 3, 22), 1)
    surf.set_at((door.right - 6, 25), (32, 24, 16, 255))
    return surf


def generate_mossy_gravestone(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA weathered mossy gravestone marker for the Sanctuary courtyard."""
    _ = rng
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    outline = (22, 22, 26, 255)

    # Ground shadow & base plinth
    pygame.draw.ellipse(surf, (12, 14, 12, 110), (7, height - 10, width - 14, 7))
    pygame.draw.rect(surf, outline, (8, height - 12, width - 16, 6), border_radius=1)
    pygame.draw.rect(surf, (78, 78, 76, 255), (9, height - 11, width - 18, 4))

    # Arched weathered stone tablet
    pygame.draw.circle(surf, outline, (width // 2, 15), 10)
    pygame.draw.rect(surf, outline, (10, 15, width - 20, height - 26))
    pygame.draw.circle(surf, (104, 102, 98, 255), (width // 2, 15), 9)
    pygame.draw.rect(surf, (104, 102, 98, 255), (11, 15, width - 22, height - 26))
    # Subtle beveled highlight along left rim
    pygame.draw.line(surf, (136, 134, 128, 255), (12, 14), (12, height - 12), 1)

    # Worn carved inscription lines & diagonal crack
    for iy in (15, 19, 23):
        pygame.draw.line(surf, (66, 64, 62, 255), (15, iy), (width - 16, iy), 1)
    pygame.draw.lines(surf, (50, 50, 52, 255), False, [(26, 13), (23, 17), (25, 21)], 1)

    # Creeping moss cap on top-left shoulder & base grass tufts
    pygame.draw.ellipse(surf, (52, 86, 46, 255), (10, 7, 13, 7))
    pygame.draw.ellipse(surf, (76, 118, 62, 255), (12, 8, 8, 4))
    for gx in (9, 12, 28, 31):
        pygame.draw.line(surf, (54, 96, 48, 255), (gx, height - 8), (gx + (-1 if gx < 20 else 1), height - 13), 2)
    return surf


def generate_torn_page_sprite(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA illuminated Torn Page pickup sprite with curled corners and gold seal."""
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, "torn_page")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)

    # Soft ground drop shadow
    pygame.draw.ellipse(surf, (18, 14, 10, 95), (7, height - 9, width - 14, 6))

    # Ragged weathered parchment polygon with jagged torn lower edge
    parchment_poly = [
        (9, 7),
        (26, 6),
        (31, 11),
        (30, 29),
        (26, 33),
        (22, 30),
        (17, 34),
        (13, 30),
        (8, 32),
        (9, 14),
    ]
    pygame.draw.polygon(surf, (96, 76, 50, 255), [(px + 1, py + 1) for px, py in parchment_poly])
    pygame.draw.polygon(surf, (232, 218, 184, 255), parchment_poly)
    pygame.draw.polygon(surf, (118, 92, 58, 255), parchment_poly, 1)

    # Subtle weathered paper fiber grain
    for _ in range(16):
        gx = gen.randint(11, 28)
        gy = gen.randint(9, 29)
        if surf.get_at((gx, gy)).a > 200:
            tone = (218, 200, 162, 255) if gen.random() < 0.5 else (242, 232, 206, 255)
            surf.set_at((gx, gy), tone)

    # Curled top-right dog-ear corner & subtle bottom-left curl highlight
    pygame.draw.polygon(surf, (158, 134, 96, 255), [(25, 6), (31, 12), (24, 13)])
    pygame.draw.polygon(surf, (248, 238, 214, 255), [(25, 6), (31, 11), (25, 11)])
    pygame.draw.line(surf, (108, 86, 54, 255), (25, 6), (25, 12), 1)
    pygame.draw.line(surf, (248, 238, 214, 255), (9, 30), (13, 28), 1)

    # Illuminated gold drop-cap initial & dark-gold calligraphy script lines
    pygame.draw.rect(surf, (218, 174, 72, 255), (12, 11, 5, 6))
    pygame.draw.rect(surf, (132, 96, 36, 255), (12, 11, 5, 6), 1)
    pygame.draw.line(surf, (132, 102, 48, 240), (19, 12), (25, 12), 1)
    pygame.draw.line(surf, (94, 70, 38, 235), (19, 15), (27, 15), 1)
    pygame.draw.line(surf, (132, 102, 48, 240), (12, 19), (27, 19), 1)
    pygame.draw.line(surf, (94, 70, 38, 235), (12, 22), (24, 22), 1)
    pygame.draw.line(surf, (132, 102, 48, 230), (12, 25), (20, 25), 1)

    # Warm amber-gold ink wax seal at lower right
    pygame.draw.circle(surf, (148, 86, 24, 255), (24, 26), 4)
    pygame.draw.circle(surf, (218, 154, 46, 255), (24, 26), 3)
    surf.set_at((23, 25), (252, 224, 134, 255))
    return surf


def generate_sanctuary_window_wall(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 Sanctuary stone wall facade with a warm candle-lit leaded glass window."""
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, "sanctuary_window_wall")
    surf = pygame.Surface((width, height))
    surf.fill((62, 64, 68))

    # Coursed stone masonry blocks
    mortar = (40, 42, 46)
    row_h = 10
    for row_idx in range(0, height, row_h):
        pygame.draw.line(surf, mortar, (0, row_idx), (width - 1, row_idx), 1)
        offset = 8 if (row_idx // row_h) % 2 == 1 else 0
        for bx in range(offset, width, 16):
            pygame.draw.line(surf, mortar, (bx, row_idx), (bx, min(height - 1, row_idx + row_h)), 1)
            tone = 60 + gen.randint(-6, 6)
            pygame.draw.rect(
                surf,
                (tone, tone + 2, tone + 5),
                (bx + 1, row_idx + 1, min(14, width - bx - 1), min(row_h - 1, height - row_idx - 1)),
            )

    # Recessed stone window surround & arched top
    win_x, win_y, win_w, win_h = 10, 8, width - 20, height - 16
    pygame.draw.rect(surf, (38, 36, 38), (win_x - 2, win_y - 2, win_w + 4, win_h + 4), border_radius=4)
    pygame.draw.rect(surf, (52, 42, 34), (win_x, win_y, win_w, win_h), border_radius=3)

    # Warm candle-lit amber glass panes with soft vertical gradient
    glass_rect = pygame.Rect(win_x + 2, win_y + 2, win_w - 4, win_h - 4)
    for gy in range(glass_rect.top, glass_rect.bottom):
        t = (gy - glass_rect.top) / max(1, glass_rect.height - 1)
        r_col = int(224 + 28 * t)
        g_col = int(164 + 54 * t)
        b_col = int(72 + 54 * t)
        pygame.draw.line(surf, (r_col, g_col, b_col), (glass_rect.left, gy), (glass_rect.right - 1, gy), 1)

    # Leaded mullion crossbars and diamond lattice accents
    cx = width // 2
    cy = glass_rect.centery
    pygame.draw.line(surf, (52, 42, 36), (cx, glass_rect.top), (cx, glass_rect.bottom - 1), 2)
    pygame.draw.line(surf, (52, 42, 36), (glass_rect.left, cy), (glass_rect.right - 1, cy), 2)
    pygame.draw.line(surf, (72, 56, 44), (glass_rect.left, glass_rect.top), (cx, cy), 1)
    pygame.draw.line(surf, (72, 56, 44), (glass_rect.right - 1, glass_rect.top), (cx, cy), 1)

    # Carved stone windowsill catching warm candlelight
    pygame.draw.rect(surf, (84, 82, 78), (win_x - 3, win_y + win_h, win_w + 6, 4))
    pygame.draw.line(surf, (158, 134, 92), (win_x - 2, win_y + win_h), (win_x + win_w + 2, win_y + win_h), 1)
    # Subtle base moss trim along footing
    for mx in (3, 7, 32, 36):
        pygame.draw.rect(surf, (56, 84, 50), (mx, height - 3, 3, 3))
    return surf


def generate_sanctuary_arch_doorway(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 Sanctuary stone archway facade with recessed timber double-doors."""
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, "sanctuary_arch_doorway")
    surf = pygame.Surface((width, height))
    surf.fill((58, 60, 64))

    # Flanking masonry stone courses
    for row_idx in range(0, height, 10):
        tone = 58 + gen.randint(-5, 5)
        pygame.draw.rect(surf, (tone, tone + 2, tone + 4), (0, row_idx, width, 9))
        pygame.draw.line(surf, (38, 40, 44), (0, row_idx + 9), (width - 1, row_idx + 9), 1)

    # Carved stone arch ring & keystone
    cx = width // 2
    pygame.draw.circle(surf, (40, 40, 44), (cx, 16), 15)
    pygame.draw.rect(surf, (40, 40, 44), (cx - 15, 16, 30, height - 16))
    pygame.draw.circle(surf, (92, 92, 90), (cx, 16), 14)
    pygame.draw.rect(surf, (92, 92, 90), (cx - 14, 16, 28, height - 16))
    # Keystone accent at top center of arch
    pygame.draw.polygon(surf, (118, 116, 110), [(cx - 3, 2), (cx + 3, 2), (cx + 2, 7), (cx - 2, 7)])

    # Recessed dark timber double-doors inside the archway
    pygame.draw.circle(surf, (24, 18, 16), (cx, 16), 11)
    pygame.draw.rect(surf, (24, 18, 16), (cx - 11, 16, 22, height - 16))
    pygame.draw.circle(surf, (78, 52, 34), (cx, 16), 10)
    pygame.draw.rect(surf, (78, 52, 34), (cx - 10, 16, 20, height - 16))

    # Vertical plank seams & center split between double doors
    for px in (cx - 6, cx + 6):
        pygame.draw.line(surf, (58, 38, 24), (px, 9), (px, height - 2), 1)
    pygame.draw.line(surf, (30, 20, 14), (cx, 6), (cx, height - 1), 2)

    # Wrought-iron strap hinges & brass door rings
    for hy in (18, 30):
        pygame.draw.line(surf, (44, 44, 48), (cx - 10, hy), (cx - 4, hy), 2)
        pygame.draw.line(surf, (44, 44, 48), (cx + 4, hy), (cx + 10, hy), 2)
    pygame.draw.circle(surf, (208, 174, 86), (cx - 3, 24), 2, 1)
    pygame.draw.circle(surf, (208, 174, 86), (cx + 3, 24), 2, 1)

    # Warm candle threshold seam along the bottom step
    pygame.draw.line(surf, (232, 186, 94), (cx - 9, height - 2), (cx + 9, height - 2), 1)
    return surf


def generate_highland_monolith(
    width: int = TILE_WIDTH,
    height: int = 60,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x60 SRCALPHA weathered highland monolith with mossy base and faint carved runes."""
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, "highland_monolith")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2

    # Soft ground contact shadow beneath the 40x40 base footprint
    pygame.draw.ellipse(surf, (12, 18, 22, 115), (4, height - 10, width - 8, 8))

    # Stepped weathered plinth at base
    outline = (22, 32, 48, 255)
    pygame.draw.rect(surf, outline, (6, height - 14, width - 12, 9), border_radius=2)
    pygame.draw.rect(surf, (56, 76, 106, 255), (7, height - 13, width - 14, 7), border_radius=2)
    pygame.draw.line(surf, (132, 192, 222, 255), (8, height - 13), (width - 9, height - 13), 1)

    # Tall fractured highland monolith shaft (asymmetric chipped top crown)
    shaft_outline = [
        (10, height - 13),
        (11, 12),
        (16, 4),
        (24, 6),
        (29, 14),
        (30, height - 13),
    ]
    pygame.draw.polygon(surf, outline, shaft_outline)
    shaft_main = [
        (11, height - 14),
        (12, 13),
        (17, 6),
        (23, 7),
        (28, 15),
        (29, height - 14),
    ]
    pygame.draw.polygon(surf, (68, 96, 128, 255), shaft_main)

    # Shaded east stone facet & windward sky-blue rim highlight
    east_facet = [
        (cx + 2, 7),
        (23, 7),
        (28, 15),
        (29, height - 14),
        (cx + 2, height - 14),
    ]
    pygame.draw.polygon(surf, (46, 64, 92, 255), east_facet)
    pygame.draw.lines(surf, (150, 215, 240, 255), False, [(12, height - 16), (12, 13), (17, 6), (22, 7)], 2)

    # Subtle weathered stone grit & hairline horizontal fracture
    for _ in range(24):
        gx = gen.randint(13, 27)
        gy = gen.randint(10, height - 16)
        col = surf.get_at((gx, gy))
        if col.a > 200:
            delta = gen.randint(-10, 10)
            surf.set_at(
                (gx, gy),
                (
                    max(0, min(255, col.r + delta)),
                    max(0, min(255, col.g + delta)),
                    max(0, min(255, col.b + delta)),
                    255,
                ),
            )
    pygame.draw.lines(surf, (30, 44, 66, 255), False, [(13, 28), (19, 26), (26, 30)], 1)

    # Non-religious geometric wind-spiral & interlocking angular slate glyph carvings
    rune_glow = (90, 228, 178, 185)
    rune_core = (156, 246, 212, 215)
    # Upper stepped wind-spiral scroll (open geometric coil, no cross intersection)
    spiral_pts = [
        (cx - 5, 19),
        (cx - 5, 13),
        (cx + 3, 13),
        (cx + 3, 21),
        (cx - 2, 21),
        (cx - 2, 16),
        (cx + 1, 16),
    ]
    pygame.draw.lines(surf, rune_glow, False, spiral_pts, 1)
    surf.set_at((cx, 17), rune_core)
    # Lower stacked interlocking wind-chevron bands
    pygame.draw.lines(surf, rune_glow, False, [(cx - 5, 34), (cx - 1, 31), (cx + 4, 34)], 1)
    pygame.draw.lines(surf, rune_core, False, [(cx - 4, 39), (cx, 36), (cx + 4, 39)], 1)
    pygame.draw.line(surf, rune_glow, (cx - 4, 43), (cx + 3, 41), 1)

    # Mossy highland base tufts clinging to plinth
    pygame.draw.ellipse(surf, (32, 88, 54, 255), (6, height - 12, 12, 6))
    pygame.draw.ellipse(surf, (48, 122, 70, 255), (8, height - 11, 8, 4))
    pygame.draw.ellipse(surf, (32, 88, 54, 255), (22, height - 11, 12, 5))
    pygame.draw.ellipse(surf, (56, 134, 76, 255), (24, height - 10, 7, 3))
    return surf


def generate_tech_server_pylon(
    width: int = TILE_WIDTH, height: int = 60, rng: random.Random = None
) -> pygame.Surface:
    """Generate a 40x60 brushed-titanium data-core server monolith with louvers and cyan/magenta telemetry LEDs."""
    gen = rng if rng is not None else random.Random(2041)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2

    # Soft ground contact shadow under base pedestal
    pygame.draw.ellipse(surf, (6, 12, 22, 118), (4, height - 10, width - 8, 8))

    # Chamfered dark-steel base plinth anchored on bottom 40x40 footprint
    plinth_pts = [
        (5, height - 7),
        (7, height - 14),
        (width - 8, height - 14),
        (width - 6, height - 7),
    ]
    pygame.draw.polygon(surf, (34, 46, 62, 255), plinth_pts)
    pygame.draw.polygon(surf, (16, 22, 34, 255), plinth_pts, 1)
    pygame.draw.line(surf, (88, 112, 138, 255), (8, height - 14), (width - 9, height - 14), 1)
    for bx in (9, width - 10):
        surf.set_at((bx, height - 11), (132, 158, 184, 255))

    # Chamfered brushed-titanium server chassis
    chassis_pts = [
        (8, height - 14),
        (8, 9),
        (12, 4),
        (width - 13, 4),
        (width - 9, 9),
        (width - 9, height - 14),
    ]
    pygame.draw.polygon(surf, (76, 92, 112, 255), chassis_pts)

    # Shaded east metallic bevel & crisp left titanium highlight
    east_panel = [
        (cx + 4, 5),
        (width - 13, 5),
        (width - 9, 9),
        (width - 9, height - 14),
        (cx + 4, height - 14),
    ]
    pygame.draw.polygon(surf, (54, 68, 86, 255), east_panel)
    pygame.draw.polygon(surf, (20, 28, 40, 255), chassis_pts, 1)
    pygame.draw.lines(
        surf,
        (148, 174, 198, 255),
        False,
        [(9, height - 15), (9, 9), (12, 5), (width - 14, 5)],
        1,
    )

    # Subtle horizontal brushed-titanium grain across chassis
    for gy in range(7, height - 15, 2):
        delta = gen.randint(-7, 7)
        for gx in range(10, width - 10):
            col = surf.get_at((gx, gy))
            if col.a > 200:
                surf.set_at(
                    (gx, gy),
                    (
                        max(0, min(255, col.r + delta)),
                        max(0, min(255, col.g + delta)),
                        max(0, min(255, col.b + delta)),
                        255,
                    ),
                )

    # Recessed central core bay
    bay_rect = pygame.Rect(12, 10, width - 24, height - 27)
    pygame.draw.rect(surf, (24, 34, 48, 255), bay_rect, border_radius=2)
    pygame.draw.rect(surf, (44, 58, 76, 255), bay_rect, 1, border_radius=2)

    # Dark heatsink louver slats inside upper & lower bay
    for ly in (14, 18, 22, 34, 38, 42):
        pygame.draw.line(surf, (12, 18, 28, 255), (14, ly), (width - 15, ly), 2)
        pygame.draw.line(surf, (62, 78, 98, 255), (14, ly + 1), (width - 15, ly + 1), 1)

    # Central glowing cyan data-core slit
    pygame.draw.rect(surf, (18, 66, 88, 255), (14, 26, width - 28, 5), border_radius=1)
    pygame.draw.line(surf, (78, 228, 248, 255), (15, 28), (width - 16, 28), 1)
    pygame.draw.line(surf, (192, 248, 255, 255), (18, 28), (width - 19, 28), 1)

    # Vertical cyan & magenta status telemetry LED rails
    cyan_glow = (48, 212, 238, 235)
    cyan_core = (188, 250, 255, 255)
    mag_glow = (212, 76, 168, 235)
    mag_core = (248, 176, 224, 255)
    for idx, py_led in enumerate((12, 17, 22, 32, 37, 42)):
        # Left rail: cool cyan telemetry pips
        pygame.draw.rect(surf, cyan_glow, (10, py_led, 2, 2))
        if idx % 2 == 0:
            surf.set_at((10, py_led), cyan_core)
        # Right rail: magenta status pips (alternating active/dim)
        if idx in (0, 2, 3, 5):
            pygame.draw.rect(surf, mag_glow, (width - 12, py_led, 2, 2))
            if idx in (0, 3):
                surf.set_at((width - 12, py_led), mag_core)
        else:
            pygame.draw.rect(surf, (66, 40, 66, 255), (width - 12, py_led, 2, 2))

    # Top antenna / status crown pip
    pygame.draw.rect(surf, (46, 60, 78, 255), (cx - 4, 2, 8, 3))
    pygame.draw.line(surf, (82, 224, 246, 255), (cx - 2, 3), (cx + 1, 3), 1)
    return surf


def generate_tech_canister(
    width: int = TILE_WIDTH, height: int = TILE_HEIGHT, rng: random.Random = None
) -> pygame.Surface:
    """Generate a 40x40 pressurized metallic coolant/ink canister with steel endcaps, hazard trim, and cyan gauge."""
    gen = rng if rng is not None else random.Random(2042)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2

    # Ground contact shadow
    pygame.draw.ellipse(surf, (8, 14, 24, 118), (6, height - 9, width - 12, 7))

    # Cylindrical brushed-steel canister body
    body_rect = pygame.Rect(9, 8, width - 18, height - 15)
    pygame.draw.rect(surf, (78, 94, 114, 255), body_rect, border_radius=3)
    # Cylindrical lighting: brighter left highlight, shaded right flank
    pygame.draw.rect(surf, (112, 132, 154, 255), (11, 9, 5, height - 17))
    pygame.draw.rect(surf, (52, 66, 84, 255), (cx + 3, 9, width - 13 - cx, height - 17))
    pygame.draw.rect(surf, (20, 28, 40, 255), body_rect, 1, border_radius=3)

    # Subtle metallic surface grain
    for _ in range(18):
        gx = gen.randint(10, width - 11)
        gy = gen.randint(11, height - 11)
        col = surf.get_at((gx, gy))
        if col.a > 200:
            delta = gen.randint(-8, 8)
            surf.set_at(
                (gx, gy),
                (
                    max(0, min(255, col.r + delta)),
                    max(0, min(255, col.g + delta)),
                    max(0, min(255, col.b + delta)),
                    255,
                ),
            )

    # Flanged steel top & bottom endcaps + pressure valve nozzle
    top_cap = pygame.Rect(7, 6, width - 14, 5)
    bot_cap = pygame.Rect(7, height - 11, width - 14, 5)
    for cap_rect in (top_cap, bot_cap):
        pygame.draw.rect(surf, (56, 70, 88, 255), cap_rect, border_radius=2)
        pygame.draw.line(
            surf,
            (136, 158, 182, 255),
            (cap_rect.left + 2, cap_rect.top + 1),
            (cap_rect.right - 3, cap_rect.top + 1),
            1,
        )
        pygame.draw.rect(surf, (18, 26, 38, 255), cap_rect, 1, border_radius=2)
        surf.set_at((cap_rect.left + 2, cap_rect.top + 2), (168, 190, 212, 255))
        surf.set_at((cap_rect.right - 3, cap_rect.top + 2), (168, 190, 212, 255))

    # Top valve cap
    pygame.draw.rect(surf, (44, 58, 74, 255), (cx - 4, 3, 8, 4), border_radius=1)
    pygame.draw.line(surf, (132, 156, 180, 255), (cx - 3, 4), (cx + 2, 4), 1)
    pygame.draw.rect(surf, (18, 26, 38, 255), (cx - 4, 3, 8, 4), 1, border_radius=1)

    # Restrained industrial hazard trim strip above bottom flange
    haz_y = height - 14
    pygame.draw.rect(surf, (36, 40, 48, 255), (10, haz_y, width - 20, 3))
    for hx in range(11, width - 12, 5):
        pygame.draw.line(surf, (206, 162, 56, 255), (hx, haz_y + 2), (hx + 2, haz_y), 2)

    # Glowing cyan pressurized level gauge in center
    gauge_outer = pygame.Rect(cx - 4, 12, 8, 13)
    pygame.draw.rect(surf, (16, 24, 36, 255), gauge_outer, border_radius=2)
    pygame.draw.rect(surf, (44, 62, 82, 255), gauge_outer, 1, border_radius=2)
    # Coolant fluid column (~75% full)
    pygame.draw.rect(surf, (26, 178, 212, 255), (cx - 2, 15, 4, 9))
    pygame.draw.rect(surf, (88, 236, 252, 255), (cx - 1, 15, 2, 9))
    pygame.draw.line(surf, (206, 252, 255, 255), (cx - 2, 15), (cx + 1, 15), 1)
    # Subtle glass graduation ticks
    for ty in (16, 19, 22):
        surf.set_at((cx + 2, ty), (132, 162, 184, 255))
    return surf


def generate_swamp_spore_pod(
    width: int = TILE_WIDTH, height: int = TILE_HEIGHT, rng: random.Random = None
) -> pygame.Surface:
    """Generate a 40x40 bloated bruised-violet chitin spore pod with chartreuse/amber veins and anchor roots."""
    gen = rng if rng is not None else random.Random(2043)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2

    # Ground contact shadow under bloated sac
    pygame.draw.ellipse(surf, (12, 6, 18, 128), (5, height - 10, width - 10, 8))

    # Dark anchoring root tendrils gripping bog floor around base
    root_dark = (26, 12, 30, 255)
    root_mid = (52, 26, 56, 255)
    tendrils = (
        [(cx - 9, height - 12), (cx - 14, height - 8), (cx - 16, height - 5)],
        [(cx - 4, height - 10), (cx - 7, height - 6), (cx - 9, height - 4)],
        [(cx + 4, height - 10), (cx + 8, height - 6), (cx + 10, height - 4)],
        [(cx + 9, height - 12), (cx + 14, height - 8), (cx + 16, height - 5)],
    )
    for pts in tendrils:
        pygame.draw.lines(surf, root_dark, False, pts, 3)
        pygame.draw.lines(surf, root_mid, False, pts[:2], 1)

    # Bloated bulbous bruised-violet chitin sac
    sac_rect = pygame.Rect(8, 8, width - 16, height - 15)
    pygame.draw.ellipse(surf, (76, 38, 76, 255), sac_rect)
    # Shaded right curvature & soft bruised-lilac upper-left dome highlight
    pygame.draw.ellipse(surf, (52, 24, 54, 255), (cx - 1, 10, width // 2 - 8, height - 18))
    pygame.draw.ellipse(surf, (108, 64, 112, 255), (11, 11, 10, 12))
    pygame.draw.arc(surf, (158, 124, 168, 255), (10, 9, width - 20, height - 18), 1.4, 2.8, 1)
    pygame.draw.ellipse(surf, (20, 9, 24, 255), sac_rect, 1)

    # Subtle organic chitin surface grit
    for _ in range(20):
        gx = gen.randint(10, width - 11)
        gy = gen.randint(11, height - 11)
        col = surf.get_at((gx, gy))
        if col.a > 200:
            delta = gen.randint(-8, 8)
            surf.set_at(
                (gx, gy),
                (
                    max(0, min(255, col.r + delta)),
                    max(0, min(255, col.g + delta // 2)),
                    max(0, min(255, col.b + delta)),
                    255,
                ),
            )

    # Flared chitin crown / spore orifice at apex
    crown_rect = pygame.Rect(cx - 6, 5, 12, 6)
    pygame.draw.ellipse(surf, (48, 22, 52, 255), crown_rect)
    pygame.draw.ellipse(surf, (20, 9, 24, 255), crown_rect, 1)
    pygame.draw.ellipse(surf, (148, 212, 62, 255), (cx - 3, 7, 6, 3))
    surf.set_at((cx, 8), (218, 248, 148, 255))

    # Branching chartreuse & warm-amber bioluminescent spore veins across sac wall
    vein_green = (138, 198, 52, 240)
    vein_amber = (204, 174, 56, 235)
    vein_core = (212, 246, 134, 255)
    pygame.draw.lines(surf, vein_green, False, [(cx, 11), (cx - 4, 17), (cx - 7, 24), (cx - 5, 29)], 2)
    pygame.draw.lines(surf, vein_amber, False, [(cx - 4, 17), (cx + 1, 21), (cx + 5, 27)], 1)
    pygame.draw.lines(surf, vein_green, False, [(cx + 2, 12), (cx + 6, 18), (cx + 8, 24)], 1)

    # Glowing spore pustule blisters along veins
    for px, py, col in (
        (cx - 4, 18, vein_core),
        (cx + 5, 19, vein_amber),
        (cx - 6, 25, vein_green),
        (cx + 2, 24, vein_core),
    ):
        pygame.draw.circle(surf, (38, 18, 42, 255), (px, py), 3)
        pygame.draw.circle(surf, col, (px, py), 2)
        surf.set_at((px, py), (232, 252, 176, 255))

    return surf


def generate_slug_boss(
    width: int = 112,
    height: int = 112,
    rng: random.Random = None,
    direction: str = "down",
    frame: int = 0,
) -> pygame.Surface:
    """Generate a 112x112 organic asymmetrical gastropod Swamp Night Boss (down/up/side x frames 0..2)."""
    d_key = direction if direction in ("down", "up", "side") else "down"
    f_idx = int(frame) % 3
    gen = rng if rng is not None else random.Random(2044 + f_idx * 17 + (0 if d_key == "down" else 101 if d_key == "up" else 211))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2
    l_dy, r_dy, sway = _boss_stride_offsets(f_idx)
    bob = -1 if f_idx != 0 else 0

    if d_key == "side":
        # Elongated right-facing gastropod profile: curled tail left, forward-leaning crowned head right
        pygame.draw.ellipse(surf, (18, 12, 24, 128), (6, height - 24, width - 12, 18))
        pygame.draw.ellipse(surf, (92, 138, 38, 100), (6, height - 20, width - 20, 12))
        foot = [
            (8, 82), (18, 90 + l_dy // 2), (32, 87 + r_dy // 2), (48, 93 + l_dy // 2),
            (64, 88 + r_dy // 2), (82, 92 + l_dy // 2), (98, 86), (102, 76), (16, 75),
        ]
        pygame.draw.polygon(surf, (146, 110, 28, 255), foot)
        pygame.draw.polygon(surf, (64, 46, 20, 255), foot, 1)
        body = [
            (10, 80), (8, 69), (16, 61 + bob), (30, 56 + bob), (45, 38 + bob),
            (64, 29 + bob), (82, 32 + bob), (96, 46 + bob), (102, 66), (96, 82), (46, 86),
        ]
        pygame.draw.polygon(surf, (206, 168, 50, 255), body)
        pygame.draw.ellipse(surf, (220, 184, 62, 255), (42, 32 + bob, 50, 40))
        pygame.draw.ellipse(surf, (172, 132, 36, 255), (16, 58, 42, 24))
        pygame.draw.polygon(surf, (62, 44, 18, 255), body, 2)
        # Irregular bruised-magenta dorsal blotches
        pygame.draw.ellipse(surf, (158, 44, 106, 255), (34, 48 + bob, 28, 20))
        pygame.draw.ellipse(surf, (214, 82, 150, 240), (42, 42 + bob, 26, 18))
        pygame.draw.ellipse(surf, (248, 228, 136, 230), (62, 38 + bob, 16, 8))
        # 3 angled blades along the dorsal profile
        for (ex, ey), (hx, hy), thick in (
            ((34, 58 + bob), (16, 36 + bob), 5),
            ((54, 42 + bob), (42, 18 + bob), 6),
            ((24, 72), (8, 64), 4),
        ):
            pygame.draw.ellipse(surf, (124, 188, 52, 255), (ex - 5, ey - 3, 10, 6))
            mx, my = (ex + hx) // 2, (ey + hy) // 2
            pygame.draw.line(surf, (78, 86, 100, 255), (ex, ey), (mx, my), thick)
            pygame.draw.line(surf, (182, 192, 204, 255), (ex, ey), (mx, my), max(2, thick - 2))
            pygame.draw.line(surf, (88, 44, 52, 255), (mx, my), (hx, hy), 3)
            pygame.draw.circle(surf, (196, 160, 68, 255), (hx, hy), 3)
        # Forward-angled eye-stalks on right head
        for (ex_b, ey_b), (ex_t, ey_t) in (
            ((86, 40 + bob), (102 + sway // 2, 22 + l_dy // 2)),
            ((78, 36 + bob), (94 + sway // 2, 18 + r_dy // 2)),
        ):
            pygame.draw.line(surf, (162, 124, 34, 255), (ex_b, ey_b), (ex_t, ey_t), 5)
            pygame.draw.line(surf, (224, 188, 66, 255), (ex_b, ey_b), (ex_t, ey_t), 3)
            pygame.draw.circle(surf, (56, 38, 24, 255), (ex_t, ey_t), 5)
            pygame.draw.circle(surf, (244, 238, 192, 255), (ex_t, ey_t), 3)
            surf.set_at((ex_t + 1, ey_t), (24, 14, 24, 255))
        # Soft burnished-gold & plum-velvet crown perched on right-facing head
        ccx = 76
        pygame.draw.ellipse(surf, (124, 42, 92, 255), (ccx - 13, 12 + bob, 26, 13))
        pygame.draw.ellipse(surf, (124, 42, 92, 255), (ccx - 14, 26 + bob, 28, 6))
        c_pts = [(ccx - 14, 28 + bob), (ccx - 16, 14 + bob), (ccx - 7, 21 + bob), (ccx, 10 + bob), (ccx + 8, 21 + bob), (ccx + 15, 14 + bob), (ccx + 13, 28 + bob)]
        pygame.draw.polygon(surf, (222, 184, 72, 255), c_pts)
        pygame.draw.polygon(surf, (176, 140, 56, 255), c_pts, 2)
        pygame.draw.line(surf, (244, 222, 132, 255), (ccx - 12, 25 + bob), (ccx + 11, 25 + bob), 2)
        return surf

    if d_key == "up":
        # Back-turned gastropod view: broad magenta-mottled rear mantle, curled tail & 3 blades (no eyes)
        pygame.draw.ellipse(surf, (18, 12, 24, 128), (10, height - 25, width - 20, 19))
        pygame.draw.ellipse(surf, (92, 138, 38, 100), (16, height - 21, width - 32, 13))
        foot = [
            (14, 82), (26, 92 + l_dy // 2), (44, 89 + r_dy // 2), (62, 94 + l_dy // 2),
            (80, 90 + r_dy // 2), (96, 84), (94, 72), (16, 74),
        ]
        pygame.draw.polygon(surf, (146, 110, 28, 255), foot)
        pygame.draw.polygon(surf, (64, 46, 20, 255), foot, 1)
        body = [
            (14, 78), (13, 56), (22, 34 + bob), (42, 24 + bob), (68, 26 + bob),
            (86, 38 + bob), (96, 62), (92, 82), (56, 88), (22, 84),
        ]
        pygame.draw.polygon(surf, (204, 166, 48, 255), body)
        pygame.draw.ellipse(surf, (166, 128, 34, 255), (26, 52, 62, 34))
        pygame.draw.polygon(surf, (62, 44, 18, 255), body, 2)
        # Broad magenta dorsal mottling dominating back view
        pygame.draw.ellipse(surf, (158, 44, 106, 255), (30, 32 + bob, 48, 44))
        pygame.draw.ellipse(surf, (214, 82, 150, 240), (38, 40 + bob, 32, 30))
        pygame.draw.ellipse(surf, (246, 166, 208, 215), (46, 44 + bob, 12, 8))
        # Rear blades protruding asymmetrically
        for (ex, ey), (hx, hy), thick in (
            ((30, 48 + bob), (12, 22 + bob), 6),
            ((82, 62 + bob), (102, 50 + bob), 4),
            ((72, 36 + bob), (92, 16 + bob), 4),
        ):
            pygame.draw.ellipse(surf, (124, 188, 52, 255), (ex - 5, ey - 3, 10, 6))
            mx, my = (ex + hx) // 2, (ey + hy) // 2
            pygame.draw.line(surf, (78, 86, 100, 255), (ex, ey), (mx, my), thick)
            pygame.draw.line(surf, (182, 192, 204, 255), (ex, ey), (mx, my), max(2, thick - 2))
            pygame.draw.line(surf, (88, 44, 52, 255), (mx, my), (hx, hy), 3)
            pygame.draw.circle(surf, (196, 160, 68, 255), (hx, hy), 3)
        # Rear rim of soft burnished-gold crown & plum velvet cap
        pygame.draw.ellipse(surf, (124, 42, 92, 255), (cx - 14, 11 + bob, 28, 13))
        c_pts = [(cx - 16, 26 + bob), (cx - 17, 13 + bob), (cx - 8, 19 + bob), (cx, 8 + bob), (cx + 8, 19 + bob), (cx + 17, 13 + bob), (cx + 16, 26 + bob)]
        pygame.draw.polygon(surf, (196, 160, 64, 255), c_pts)
        pygame.draw.polygon(surf, (176, 140, 56, 255), c_pts, 2)
        return surf

    # 1. Ground slime trail & asymmetrical wet contact shadow under heavy foot & curled tail
    pygame.draw.ellipse(surf, (18, 12, 24, 128), (10, height - 25, width - 16, 19))
    pygame.draw.ellipse(surf, (92, 138, 38, 100), (18, height - 21, width - 22, 13))
    pygame.draw.ellipse(surf, (132, 186, 56, 78), (66, height - 18, 38, 9))

    # 2. Undulating wet muscular gastropod foot-skirt & curled fleshy tail lobe on the east side
    foot_skirt = [
        (12, 82), (18, 91 + l_dy // 2), (28, 88 + r_dy // 2), (38, 94 + l_dy // 2),
        (50, 91 + r_dy // 2), (62, 95 + l_dy // 2), (74, 90 + r_dy // 2), (88, 92 + l_dy // 2),
        (101 + sway // 2, 84), (104 + sway // 2, 74), (96 + sway // 2, 66), (86, 72),
        (80, 77), (16, 76),
    ]
    pygame.draw.polygon(surf, (146, 110, 28, 255), foot_skirt)
    pygame.draw.lines(
        surf, (194, 158, 56, 230), False,
        [(16, 86), (28, 85 + l_dy // 2), (40, 89), (54, 87 + r_dy // 2), (68, 89), (84, 86), (97 + sway // 2, 81)], 2,
    )
    pygame.draw.polygon(surf, (64, 46, 20, 255), foot_skirt, 1)

    # 3. Organic asymmetrical heavy gastropod body & bulbous mantle folds (head leaning forward-left, curled rear)
    body_poly = [
        (14, 78), (11, 63), (15, 45 + bob), (25, 33 + bob), (40, 27 + bob), (56, 28 + bob),
        (71, 35 + bob), (82, 47 + bob), (87, 61), (95 + sway // 2, 65), (99 + sway // 2, 73), (92, 82),
        (77, 86), (56, 88), (32, 86),
    ]
    pygame.draw.polygon(surf, (206, 168, 50, 255), body_poly)
    # Layered bulbous mantle folds & lower-right belly weight
    pygame.draw.ellipse(surf, (220, 184, 62, 255), (18, 32 + bob, 52, 40))
    pygame.draw.ellipse(surf, (194, 156, 44, 255), (42, 38 + bob, 44, 40))
    pygame.draw.ellipse(surf, (166, 128, 34, 255), (50, 54, 38, 30))
    # Curled fleshy tail ridge
    pygame.draw.ellipse(surf, (192, 154, 46, 255), (76 + sway // 2, 62, 24, 20))
    pygame.draw.arc(surf, (124, 92, 26, 220), (74 + sway // 2, 62, 24, 18), 3.4, 6.0, 2)
    # Soft belly crease folds
    pygame.draw.arc(surf, (132, 98, 28, 200), (20, 58, 38, 22), 3.3, 5.7, 2)
    pygame.draw.arc(surf, (132, 98, 28, 190), (46, 60, 34, 20), 3.5, 5.9, 2)
    pygame.draw.polygon(surf, (62, 44, 18, 255), body_poly, 2)

    # 4. Irregular bruised-magenta dorsal mottling & organic blotches (asymmetrical, not a straight stripe)
    blotches = (
        [(36, 32 + bob), (51, 31 + bob), (59, 44 + bob), (50, 56 + bob), (34, 52 + bob), (30, 41 + bob)],
        [(46, 48 + bob), (64, 46 + bob), (72, 60), (63, 75), (48, 74), (42, 61)],
        [(64, 60), (79, 59), (84, 70), (74, 78), (62, 72)],
        [(26, 50 + bob), (37, 48 + bob), (40, 62), (28, 65)],
    )
    for b_idx, poly in enumerate(blotches):
        outer_c = (158, 44, 106, 255) if b_idx % 2 == 0 else (142, 38, 98, 255)
        pygame.draw.polygon(surf, outer_c, poly)
    pygame.draw.ellipse(surf, (214, 82, 150, 240), (36, 36 + bob, 18, 16))
    pygame.draw.ellipse(surf, (224, 94, 160, 235), (48, 52, 19, 18))
    pygame.draw.ellipse(surf, (198, 68, 136, 230), (66, 64, 13, 10))
    # Wet glistening slime specular highlights along curved dorsal dome
    pygame.draw.ellipse(surf, (248, 228, 136, 235), (22, 39 + bob, 14, 8))
    pygame.draw.arc(surf, (252, 240, 178, 220), (24, 34 + bob, 34, 20), 1.2, 2.7, 2)
    pygame.draw.ellipse(surf, (246, 166, 208, 210), (42, 40 + bob, 7, 4))
    pygame.draw.ellipse(surf, (248, 232, 146, 215), (82 + sway // 2, 67, 10, 5))

    # Organic skin mucus speckles
    for _ in range(38):
        gx = gen.randint(18, width - 18)
        gy = gen.randint(34, height - 26)
        col = surf.get_at((gx, gy))
        if col.a > 200:
            delta = gen.randint(-12, 12)
            surf.set_at(
                (gx, gy),
                (
                    max(0, min(255, col.r + delta)),
                    max(0, min(255, col.g + delta)),
                    max(0, min(255, col.b + delta // 2)),
                    255,
                ),
            )

    # 5. Three asymmetrically embedded blades (varying lengths, angles, and insertion depths)
    blade_metal = (182, 192, 204, 255)
    blade_dark = (78, 86, 100, 255)
    hilt_gold = (196, 160, 68, 255)
    hilt_wrap = (88, 44, 52, 255)

    # Blade A: Crooked broken broadsword jutting high from left shoulder
    a_entry, a_mid, a_hilt = (30, 50 + bob), (20, 32 + bob), (12, 19 + bob)
    pygame.draw.ellipse(surf, (124, 188, 52, 255), (a_entry[0] - 6, a_entry[1] - 3, 12, 6))
    pygame.draw.line(surf, blade_dark, a_entry, a_mid, 7)
    pygame.draw.line(surf, blade_metal, a_entry, a_mid, 4)
    pygame.draw.line(surf, (232, 240, 248, 255), (27, 46 + bob), (21, 35 + bob), 1)
    pygame.draw.line(surf, hilt_gold, (12, 36 + bob), (27, 27 + bob), 4)
    pygame.draw.line(surf, hilt_wrap, a_mid, a_hilt, 4)
    pygame.draw.circle(surf, hilt_gold, a_hilt, 4)

    # Blade B: Notched dagger wedged low and shallow in the lower-right flank
    b_entry, b_mid, b_hilt = (81, 71), (92, 65), (103, 59)
    pygame.draw.ellipse(surf, (118, 180, 50, 255), (b_entry[0] - 4, b_entry[1] - 3, 9, 6))
    pygame.draw.line(surf, blade_dark, b_entry, b_mid, 4)
    pygame.draw.line(surf, blade_metal, b_entry, b_mid, 2)
    pygame.draw.line(surf, (152, 124, 54, 255), (89, 59), (95, 70), 3)
    pygame.draw.line(surf, hilt_wrap, b_mid, b_hilt, 3)
    pygame.draw.circle(surf, hilt_gold, b_hilt, 2)

    # Blade C: Bent rapier hilt protruding obliquely from the rear upper mantle
    c_entry, c_mid, c_hilt = (67, 41 + bob), (81, 30 + bob), (94, 22 + bob)
    pygame.draw.ellipse(surf, (130, 192, 54, 255), (c_entry[0] - 5, c_entry[1] - 3, 10, 5))
    pygame.draw.line(surf, blade_dark, c_entry, c_mid, 4)
    pygame.draw.line(surf, (206, 216, 228, 255), c_entry, c_mid, 2)
    pygame.draw.arc(surf, hilt_gold, (74, 23 + bob, 14, 14), 0.4, 3.6, 2)
    pygame.draw.line(surf, (74, 40, 62, 255), c_mid, c_hilt, 2)
    pygame.draw.circle(surf, (222, 188, 86, 255), c_hilt, 3)

    # 6. Expressive asymmetrical eye-stalks rising from forward-left head
    for (ex_b, ey_b), (ex_t, ey_t), pupil_dx in (
        ((cx - 18, 36 + bob), (cx - 26 + sway // 2, 18 + l_dy // 2), -1),
        ((cx + 2, 34 + bob), (cx + 8 + sway // 2, 17 + r_dy // 2), 1),
    ):
        pygame.draw.line(surf, (162, 124, 34, 255), (ex_b, ey_b), (ex_t, ey_t), 5)
        pygame.draw.line(surf, (224, 188, 66, 255), (ex_b, ey_b), (ex_t, ey_t), 3)
        pygame.draw.circle(surf, (56, 38, 24, 255), (ex_t, ey_t), 5)
        pygame.draw.circle(surf, (244, 238, 192, 255), (ex_t, ey_t), 3)
        surf.set_at((ex_t + pupil_dx, ey_t), (24, 14, 24, 255))

    # 7. Soft burnished-gold crown perched atop head with plum-velvet inner cap trim (low-contrast edge)
    crown_cx = cx - 7
    # Subtle plum/magenta velvet inner cap doming behind the gold prongs & trimming the lower cushion base
    pygame.draw.ellipse(surf, (124, 42, 92, 255), (crown_cx - 14, 11 + bob, 28, 14))
    pygame.draw.ellipse(surf, (166, 62, 122, 245), (crown_cx - 10, 12 + bob, 20, 9))
    pygame.draw.ellipse(surf, (124, 42, 92, 255), (crown_cx - 16, 26 + bob, 31, 6))
    crown_pts = [
        (crown_cx - 16, 28 + bob),
        (crown_cx - 18, 13 + bob),
        (crown_cx - 8, 20 + bob),
        (crown_cx, 8 + bob),
        (crown_cx + 8, 20 + bob),
        (crown_cx + 17, 13 + bob),
        (crown_cx + 15, 28 + bob),
    ]
    crown_shade = [
        (crown_cx, 28 + bob),
        (crown_cx, 9 + bob),
        (crown_cx + 8, 20 + bob),
        (crown_cx + 17, 13 + bob),
        (crown_cx + 15, 28 + bob),
    ]
    pygame.draw.polygon(surf, (222, 184, 72, 255), crown_pts)
    pygame.draw.polygon(surf, (192, 156, 68, 255), crown_shade)
    pygame.draw.polygon(surf, (176, 140, 56, 255), crown_pts, 2)
    pygame.draw.line(surf, (244, 222, 132, 255), (crown_cx - 14, 25 + bob), (crown_cx + 13, 25 + bob), 2)
    pygame.draw.line(surf, (244, 222, 132, 235), (crown_cx - 16, 15 + bob), (crown_cx - 15, 24 + bob), 1)
    for jx, jy, jcol in (
        (crown_cx, 20 + bob, (218, 66, 142, 255)),
        (crown_cx - 10, 24 + bob, (132, 204, 62, 255)),
        (crown_cx + 10, 24 + bob, (132, 204, 62, 255)),
    ):
        pygame.draw.circle(surf, jcol, (jx, jy), 2)

    return surf


def generate_slug_boss_crown(
    width: int = 44, height: int = 32, rng: random.Random = None
) -> pygame.Surface:
    """Generate a 44x32 soft burnished-gold crown resting tilted on the ground after SlugBoss death."""
    _ = rng
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2

    # Soft ground shadow & tiny residual chartreuse slime puddle beneath fallen crown
    pygame.draw.ellipse(surf, (14, 8, 20, 118), (5, height - 10, width - 10, 8))
    pygame.draw.ellipse(surf, (112, 158, 46, 95), (9, height - 9, width - 18, 6))

    # Subtle plum velvet inner cap lining peeking behind crown prongs
    pygame.draw.ellipse(surf, (132, 48, 98, 240), (10, 13, width - 20, 10))

    # Slightly tilted burnished antique-gold crown circlet (low-contrast edge, warm highlights)
    crown_pts = [
        (8, height - 8),
        (6, 10),
        (15, 16),
        (cx, 5),
        (width - 15, 16),
        (width - 6, 9),
        (width - 8, height - 8),
    ]
    tarnish_pts = [
        (cx, height - 8),
        (cx, 6),
        (width - 15, 16),
        (width - 6, 9),
        (width - 8, height - 8),
    ]
    pygame.draw.polygon(surf, (218, 180, 68, 255), crown_pts)
    pygame.draw.polygon(surf, (188, 152, 66, 255), tarnish_pts)
    pygame.draw.polygon(surf, (176, 140, 56, 255), crown_pts, 2)
    pygame.draw.line(surf, (244, 222, 132, 255), (10, height - 10), (cx + 5, height - 10), 2)
    pygame.draw.line(surf, (244, 222, 132, 230), (8, 12), (9, height - 10), 1)

    # Crown jewel studs (center jewel covers (22, 16) cleanly)
    pygame.draw.circle(surf, (216, 66, 142, 255), (cx, 17), 3)
    pygame.draw.circle(surf, (248, 174, 212, 255), (cx - 1, 16), 1)
    pygame.draw.circle(surf, (132, 204, 58, 255), (13, 19), 2)
    pygame.draw.circle(surf, (132, 204, 58, 255), (width - 13, 19), 2)
    return surf


def generate_barrel_frame(
    stage: int = 0,
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA coopered oak barrel across break stages 0 (intact) -> 3 (rubble)."""
    st = max(0, min(3, int(stage)))
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, f"barrel_{st}")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx, cy = width // 2, height // 2

    oak_dark = (68, 42, 22, 255)
    oak_mid = (118, 74, 38, 255)
    oak_hi = (158, 108, 58, 255)
    outline = (28, 16, 10, 255)
    iron_dark = (42, 46, 56, 255)
    iron_hi = (128, 136, 152, 255)

    if st == 0:
        # Intact coopered oak barrel with wrought-iron hoops, wood-grain staves, and brass bung
        pygame.draw.ellipse(surf, (14, 10, 12, 130), (5, height - 10, width - 10, 8))
        # Curved barrel body silhouette
        body = pygame.Rect(8, 7, width - 16, height - 14)
        pygame.draw.ellipse(surf, oak_dark, (6, 9, width - 12, height - 18))
        pygame.draw.rect(surf, oak_mid, body, border_radius=7)
        # Sunlit left stave highlight & shaded east flank
        pygame.draw.rect(surf, oak_hi, (10, 9, 6, height - 18), border_radius=3)
        pygame.draw.rect(surf, oak_dark, (cx + 4, 9, width - 13 - cx, height - 18), border_radius=3)
        pygame.draw.rect(surf, outline, body, 1, border_radius=7)
        # Vertical stave seam lines
        for sx in (13, 18, 23, 28):
            pygame.draw.line(surf, (52, 30, 16, 220), (sx, 9), (sx, height - 9), 1)
        # Recessed top oak lid
        lid_rect = pygame.Rect(10, 5, width - 20, 8)
        pygame.draw.ellipse(surf, oak_hi, lid_rect)
        pygame.draw.ellipse(surf, outline, lid_rect, 1)
        pygame.draw.line(surf, oak_dark, (15, 7), (15, 11), 1)
        pygame.draw.line(surf, oak_dark, (24, 7), (24, 11), 1)
        # Forged wrought-iron hoops + rivets
        for hy in (12, height - 14):
            pygame.draw.rect(surf, iron_dark, (7, hy, width - 14, 4), border_radius=2)
            pygame.draw.line(surf, iron_hi, (9, hy + 1), (width - 10, hy + 1), 1)
            pygame.draw.rect(surf, outline, (7, hy, width - 14, 4), 1, border_radius=2)
            surf.set_at((11, hy + 2), (186, 194, 210, 255))
            surf.set_at((width - 12, hy + 2), (186, 194, 210, 255))
        # Brass bung plug on center stave
        pygame.draw.circle(surf, (132, 92, 30, 255), (cx, cy + 1), 3)
        pygame.draw.circle(surf, (222, 178, 72, 255), (cx, cy + 1), 2)
        surf.set_at((cx - 1, cy), (252, 232, 152, 255))
        # Subtle oak wood grain flecks
        for _ in range(16):
            gx = gen.randint(10, width - 11)
            gy = gen.randint(10, height - 10)
            if surf.get_at((gx, gy)).a > 200:
                surf.set_at((gx, gy), (84, 50, 24, 215))
        return surf

    if st == 1:
        # Initial fracture split + snapped iron hoop + flying splinters
        pygame.draw.ellipse(surf, (14, 10, 12, 115), (4, height - 10, width - 8, 8))
        # Left & right splitting halves tilting outward
        left_half = [(7, 10), (18, 8), (16, 31), (6, 29)]
        right_half = [(22, 9), (33, 11), (34, 30), (24, 31)]
        pygame.draw.polygon(surf, oak_mid, left_half)
        pygame.draw.polygon(surf, oak_hi, [(9, 11), (14, 10), (13, 28), (8, 27)])
        pygame.draw.polygon(surf, outline, left_half, 1)
        pygame.draw.polygon(surf, oak_dark, right_half)
        pygame.draw.polygon(surf, outline, right_half, 1)
        # Jagged fracture fissure down middle
        pygame.draw.lines(surf, (24, 14, 12, 255), False, [(19, 7), (21, 16), (18, 24), (21, 32)], 2)
        # Snapped iron hoop ends springing outward
        pygame.draw.lines(surf, iron_dark, False, [(5, 14), (17, 15)], 3)
        pygame.draw.lines(surf, iron_hi, False, [(6, 13), (16, 14)], 1)
        pygame.draw.lines(surf, iron_dark, False, [(23, 14), (35, 16)], 3)
        pygame.draw.lines(surf, iron_dark, False, [(6, 26), (34, 27)], 3)
        # Flying splinters
        for sx, sy, ex, ey in ((4, 6, 10, 10), (31, 6, 36, 10), (3, 21, 8, 19), (33, 23, 37, 20)):
            pygame.draw.line(surf, oak_hi, (sx, sy), (ex, ey), 2)
        return surf

    if st == 2:
        # Collapsed staves splayed outward + bent iron hoop + dust burst
        pygame.draw.ellipse(surf, (28, 20, 16, 95), (6, 11, width - 12, height - 18))
        staves = (
            [(5, 17), (17, 13), (18, 18), (6, 22)],
            [(22, 12), (35, 16), (33, 21), (21, 17)],
            [(8, 25), (19, 21), (21, 26), (10, 31)],
            [(20, 22), (33, 26), (31, 31), (19, 27)],
            [(14, 8), (24, 7), (25, 12), (15, 13)],
        )
        for idx, poly in enumerate(staves):
            col = oak_hi if idx % 2 == 0 else oak_mid
            pygame.draw.polygon(surf, col, poly)
            pygame.draw.polygon(surf, outline, poly, 1)
        pygame.draw.arc(surf, iron_dark, (6, 12, 26, 18), 0.3, 2.7, 3)
        pygame.draw.arc(surf, iron_hi, (7, 12, 24, 16), 0.5, 2.2, 1)
        return surf

    # Stage 3: Flat splintered wood rubble resting on floor
    pygame.draw.ellipse(surf, (12, 10, 12, 92), (5, 18, width - 10, 16))
    rubble_planks = (
        [(6, 24), (19, 19), (21, 23), (8, 28)],
        [(16, 26), (32, 22), (34, 26), (18, 30)],
        [(11, 29), (25, 27), (26, 31), (12, 33)],
        [(22, 17), (33, 20), (31, 23), (20, 20)],
    )
    for idx, poly in enumerate(rubble_planks):
        col = oak_mid if idx % 2 == 0 else oak_dark
        pygame.draw.polygon(surf, col, poly)
        pygame.draw.polygon(surf, outline, poly, 1)
    # Bent iron hoop scrap & small wood chips
    pygame.draw.arc(surf, iron_dark, (10, 20, 20, 12), 3.3, 5.9, 2)
    for chip_x, chip_y in ((9, 20), (28, 30), (15, 23), (33, 27)):
        pygame.draw.rect(surf, oak_hi, (chip_x, chip_y, 3, 2))
    return surf


def generate_swamp_barrel(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x40 SRCALPHA moss-slimed rotting oak barrel with corroded iron hoops for swamp_mire."""
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, "swamp_barrel")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2

    # Dark bog shadow & damp ooze around base
    pygame.draw.ellipse(surf, (14, 18, 12, 138), (5, height - 10, width - 10, 8))
    pygame.draw.ellipse(surf, (44, 68, 28, 145), (8, height - 11, width - 16, 6))

    # Warped rotting damp-oak barrel silhouette
    rot_dark = (42, 34, 24, 255)
    rot_mid = (68, 56, 36, 255)
    rot_hi = (94, 82, 50, 255)
    outline = (20, 18, 14, 255)
    body = pygame.Rect(8, 8, width - 16, height - 15)
    pygame.draw.rect(surf, rot_mid, body, border_radius=6)
    pygame.draw.rect(surf, rot_hi, (10, 9, 6, height - 18), border_radius=2)
    pygame.draw.rect(surf, rot_dark, (cx + 4, 9, width - 13 - cx, height - 18), border_radius=2)
    pygame.draw.rect(surf, outline, body, 1, border_radius=6)

    # Split/warped stave seams
    for sx in (13, 19, 24, 29):
        pygame.draw.line(surf, (28, 24, 18, 230), (sx, 9), (sx + gen.randint(-1, 1), height - 9), 1)

    # Sunken waterlogged top lid
    lid_rect = pygame.Rect(10, 6, width - 20, 7)
    pygame.draw.ellipse(surf, (58, 52, 34, 255), lid_rect)
    pygame.draw.ellipse(surf, outline, lid_rect, 1)
    pygame.draw.line(surf, (24, 20, 16, 255), (16, 8), (24, 11), 1)

    # Corroded rust-pitted iron hoops
    rust_dark = (58, 36, 26, 255)
    rust_mid = (114, 64, 34, 255)
    for hy in (13, height - 14):
        pygame.draw.rect(surf, rust_dark, (7, hy, width - 14, 4), border_radius=2)
        pygame.draw.line(surf, rust_mid, (9, hy + 1), (width - 11, hy + 1), 1)
        pygame.draw.rect(surf, outline, (7, hy, width - 14, 4), 1, border_radius=2)

    # Dripping bog moss & slime streaks clinging to lid and staves
    moss_dark = (48, 88, 36, 255)
    moss_bright = (104, 152, 54, 255)
    pygame.draw.ellipse(surf, moss_dark, (10, 9, 11, 5))
    pygame.draw.ellipse(surf, moss_bright, (11, 10, 7, 3))
    pygame.draw.line(surf, moss_dark, (14, 13), (14, 23), 2)
    pygame.draw.line(surf, moss_bright, (14, 13), (14, 19), 1)
    pygame.draw.ellipse(surf, moss_dark, (21, 21, 10, 6))
    pygame.draw.ellipse(surf, moss_bright, (23, 22, 6, 3))
    for _ in range(14):
        gx = gen.randint(10, width - 11)
        gy = gen.randint(10, height - 10)
        if surf.get_at((gx, gy)).a > 200:
            surf.set_at((gx, gy), (52, 66, 32, 220))
    return surf


def generate_pastoral_rock(
    width: int = 40,
    height: int = 60,
    rng: random.Random | None = None,
) -> pygame.Surface:
    """Generate a 40x60 SRCALPHA weathered pale-limestone meadow boulder with lichen and grass tufts."""
    gen = rng if rng is not None else _asset_rng(DEFAULT_ASSET_SEED, "pastoral_rock")
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    # Ground contact shadow centered on lower 40x40 footprint
    pygame.draw.ellipse(surf, (24, 22, 26, 112), (4, height - 12, width - 8, 9))

    # Broad natural meadow boulder silhouette (sits lower & wider than a tall milestone cairn)
    boulder_poly = [
        (6, height - 10),
        (5, 34),
        (10, 24),
        (19, 20),
        (29, 23),
        (35, 33),
        (34, height - 10),
    ]
    pygame.draw.polygon(surf, (176, 166, 144, 255), boulder_poly)
    # Warm sunlit upper-left bevel & shaded lower-right limestone facet
    lit_poly = [
        (7, 34),
        (11, 25),
        (19, 21),
        (26, 24),
        (18, 33),
    ]
    shade_poly = [
        (21, height - 10),
        (23, 25),
        (29, 23),
        (35, 33),
        (34, height - 10),
    ]
    pygame.draw.polygon(surf, (214, 202, 176, 255), lit_poly)
    pygame.draw.polygon(surf, (132, 122, 102, 255), shade_poly)
    pygame.draw.polygon(surf, (62, 54, 44, 255), boulder_poly, 1)

    # Natural limestone strata cracks & speckled grit
    pygame.draw.lines(surf, (96, 86, 72, 220), False, [(11, 35), (19, 32), (28, 36)], 1)
    pygame.draw.line(surf, (96, 86, 72, 200), (14, 42), (24, 41), 1)
    for _ in range(22):
        px = gen.randint(8, 32)
        py = gen.randint(23, height - 13)
        col = surf.get_at((px, py))
        if col.a > 200:
            delta = gen.choice((-12, 10))
            surf.set_at(
                (px, py),
                (
                    max(0, min(255, col.r + delta)),
                    max(0, min(255, col.g + delta)),
                    max(0, min(255, col.b + delta)),
                    255,
                ),
            )

    # Golden-sage lichen patches on sunlit rock shoulder
    pygame.draw.ellipse(surf, (148, 166, 74, 235), (12, 25, 7, 4))
    pygame.draw.ellipse(surf, (192, 188, 92, 225), (14, 26, 4, 2))
    pygame.draw.ellipse(surf, (124, 154, 72, 225), (24, 29, 5, 3))

    # Lush meadow grass tufts tucked along boulder base
    for gx, gy, gw in ((5, height - 14, 12), (23, height - 13, 12)):
        pygame.draw.ellipse(surf, (52, 142, 66, 255), (gx, gy, gw, 6))
        pygame.draw.ellipse(surf, (98, 198, 98, 255), (gx + 2, gy, gw - 4, 4))
    return surf


def generate_pastoral_shepherd_cairn(
    width: int = 40, height: int = 60, rng: random.Random = None
) -> pygame.Surface:
    """Generate a 40x60 weathered stone milestone with shepherd's crook, brass lantern ring & tar-stained wheat."""
    if rng is None:
        rng = random.Random(5101)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    # Ground contact shadow and creeping dark-plum tar smear at foot
    pygame.draw.ellipse(surf, (24, 14, 34, 118), (4, height - 12, width - 8, 9))
    pygame.draw.ellipse(surf, (46, 20, 68, 150), (16, height - 11, 18, 6))

    # Weathered limestone / sandstone cairn milestone body
    stone_poly = [
        (11, height - 9),
        (12, 20),
        (16, 13),
        (24, 14),
        (28, 21),
        (29, height - 9),
    ]
    pygame.draw.polygon(surf, (176, 158, 126, 255), stone_poly)
    # Right-side shadow facet
    shade_poly = [
        (21, height - 9),
        (22, 14),
        (24, 14),
        (28, 21),
        (29, height - 9),
    ]
    pygame.draw.polygon(surf, (134, 116, 88, 255), shade_poly)
    pygame.draw.polygon(surf, (56, 44, 34, 255), stone_poly, 1)

    # Warm parchment top-left highlight & weathered stone cracks
    pygame.draw.lines(
        surf,
        (226, 208, 174, 255),
        False,
        [(13, height - 13), (13, 21), (16, 14), (22, 15)],
        2,
    )
    pygame.draw.line(surf, (96, 82, 64, 220), (14, 30), (24, 32), 1)
    pygame.draw.line(surf, (96, 82, 64, 220), (15, 42), (25, 40), 1)
    for _ in range(18):
        px = rng.randint(13, 26)
        py = rng.randint(17, height - 13)
        delta = rng.choice((-14, 12))
        base = (168, 148, 118)
        col = tuple(max(0, min(255, c + delta)) for c in base) + (255,)
        surf.set_at((px, py), col)

    # Meadow moss tufts tucked around stone base
    pygame.draw.ellipse(surf, (52, 146, 68, 255), (8, height - 14, 11, 6))
    pygame.draw.ellipse(surf, (96, 204, 102, 255), (10, height - 14, 7, 4))

    # Leaning wooden shepherd's crook resting against the left flank
    wood_dark = (74, 44, 24, 255)
    wood_mid = (128, 82, 42, 255)
    wood_hi = (176, 124, 68, 255)
    pygame.draw.line(surf, wood_dark, (6, height - 7), (14, 12), 4)
    pygame.draw.line(surf, wood_mid, (6, height - 7), (14, 12), 2)
    pygame.draw.line(surf, wood_hi, (7, height - 10), (13, 14), 1)
    crook_pts = [(14, 12), (16, 6), (21, 6), (23, 10), (20, 14)]
    pygame.draw.lines(surf, wood_dark, False, crook_pts, 4)
    pygame.draw.lines(surf, wood_mid, False, crook_pts, 2)

    # Brass lantern ring mounted on the upper stone face
    pygame.draw.circle(surf, (132, 94, 32, 255), (23, 25), 4, 2)
    pygame.draw.circle(surf, (232, 188, 72, 255), (23, 25), 3, 1)
    pygame.draw.circle(surf, (252, 224, 126, 230), (23, 26), 1)

    # Tar-stained golden wheat sheaf leaning on lower-right side
    wheat_gold = (224, 186, 84, 255)
    wheat_shadow = (174, 134, 52, 255)
    tar_stain = (54, 22, 76, 255)
    for ox_s, tip_x, tip_y in ((26, 33, 35), (28, 35, 39), (24, 30, 33)):
        pygame.draw.line(surf, wheat_shadow, (ox_s, height - 10), (tip_x, tip_y), 2)
        pygame.draw.line(surf, wheat_gold, (ox_s, height - 10), (tip_x - 1, tip_y), 1)
        pygame.draw.circle(surf, wheat_gold, (tip_x, tip_y), 2)
    # Binding twine and dark plum tar splash staining the bottom of the sheaf
    pygame.draw.line(surf, (108, 68, 34, 255), (24, height - 17), (32, height - 15), 2)
    pygame.draw.ellipse(surf, tar_stain, (24, height - 14, 9, 5))
    return surf


def generate_pastoral_hay_crate(
    width: int = 40, height: int = 40, rng: random.Random = None
) -> pygame.Surface:
    """Generate a 40x40 destructible golden bound wheat bale / tar-stained shepherd crate."""
    if rng is None:
        rng = random.Random(5102)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    # Ground contact shadow
    pygame.draw.ellipse(surf, (26, 16, 32, 112), (4, height - 9, width - 8, 7))

    # Main golden hay bale / rustic crate body
    bale_rect = pygame.Rect(6, 8, width - 12, height - 14)
    pygame.draw.rect(surf, (198, 158, 70, 255), bale_rect, border_radius=4)
    # Sunlit top bevel face
    pygame.draw.rect(surf, (232, 198, 106, 255), (7, 9, width - 14, 9), border_radius=3)
    # Lower shaded face
    pygame.draw.rect(surf, (154, 116, 46, 255), (7, height - 14, width - 14, 7), border_radius=2)

    # Woven horizontal straw texture lines
    for sy in range(11, height - 8, 3):
        x0 = 8 + rng.randint(0, 3)
        x1 = width - 9 - rng.randint(0, 3)
        col = (242, 212, 126, 235) if sy % 2 == 0 else (162, 122, 48, 235)
        pygame.draw.line(surf, col, (x0, sy), (x1, sy), 1)

    # Protruding loose straw wisps around edges
    for (sx, sy), (ex, ey) in (
        ((6, 13), (3, 11)),
        ((6, 22), (2, 24)),
        ((width - 7, 14), (width - 3, 12)),
        ((width - 7, 25), (width - 3, 27)),
        ((15, 8), (13, 5)),
        ((26, 8), (28, 5)),
    ):
        pygame.draw.line(surf, (234, 198, 98, 255), (sx, sy), (ex, ey), 1)

    # Two dark-timber / hemp rope binding straps
    for bx in (13, width - 16):
        pygame.draw.rect(surf, (88, 54, 28, 255), (bx, 8, 3, height - 14))
        pygame.draw.line(surf, (142, 98, 54, 255), (bx + 1, 9), (bx + 1, height - 8), 1)

    # Crisp dark outline
    pygame.draw.rect(surf, (58, 38, 22, 255), bale_rect, 1, border_radius=4)

    # Creeping deep-plum tar-ink stain on lower-left corner
    pygame.draw.ellipse(surf, (44, 18, 64, 235), (7, height - 17, 12, 10))
    pygame.draw.ellipse(surf, (78, 34, 108, 215), (9, height - 15, 7, 6))
    surf.set_at((12, height - 13), (146, 72, 186, 220))
    return surf


def generate_meadow_censor_boss(
    width: int = 104,
    height: int = 104,
    rng: random.Random = None,
    direction: str = "down",
    frame: int = 0,
) -> pygame.Surface:
    """Generate a 104x104 Pastoral Valley Night Boss (The Meadow Censor) (down/up/side x frames 0..2)."""
    d_key = direction if direction in ("down", "up", "side") else "down"
    f_idx = int(frame) % 3
    if rng is None:
        rng = random.Random(5201 + f_idx * 19 + (0 if d_key == "down" else 71 if d_key == "up" else 139))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2
    l_dy, r_dy, sway = _boss_stride_offsets(f_idx)
    bob = -1 if f_idx != 0 else 0

    # 1. Ground contact shadow & seeping deep-plum tar-ink puddle at hem
    pygame.draw.ellipse(surf, (22, 10, 32, 150), (14, height - 20, width - 28, 16))
    pygame.draw.ellipse(surf, (64, 26, 92, 175), (20, height - 18, width - 40, 12))

    # 2. Cracked tarnished brass astrolabe halo behind shoulders/head (subtly rotates per stride frame)
    halo_cx = cx - 4 if d_key == "side" else cx
    halo_cy = 34 + bob
    rot_off = (0, 8, -8)[f_idx]
    pygame.draw.circle(surf, (136, 98, 34, 230), (halo_cx, halo_cy), 28, 3)
    pygame.draw.circle(surf, (218, 178, 72, 240), (halo_cx, halo_cy), 26, 2)
    pygame.draw.circle(surf, (176, 136, 48, 200), (halo_cx, halo_cy), 19, 1)
    for ang_deg in (20, 75, 130, 210, 295, 340):
        rad = math.radians(ang_deg + rot_off)
        x0 = int(halo_cx + math.cos(rad) * 18)
        y0 = int(halo_cy + math.sin(rad) * 18)
        x1 = int(halo_cx + math.cos(rad) * 28)
        y1 = int(halo_cy + math.sin(rad) * 28)
        pygame.draw.line(surf, (226, 188, 86, 235), (x0, y0), (x1, y1), 2)

    if d_key == "side":
        # Three-quarter right-facing inquisitor profile
        robe = [
            (cx - 20 - sway, height - 12), (cx - 16, 46 + bob), (cx - 12, 35 + bob),
            (cx + 15, 36 + bob), (cx + 21 + sway, height - 12), (cx + 4 + sway, height - 10),
        ]
        pygame.draw.polygon(surf, (46, 24, 62, 255), robe)
        pygame.draw.polygon(surf, (24, 10, 34, 255), robe, 2)
        tabard = [(cx + 2, 40 + bob), (cx + 15, 40 + bob), (cx + 17 + sway, height - 18), (cx + 4 + sway, height - 16)]
        pygame.draw.polygon(surf, (216, 198, 160, 255), tabard)
        pygame.draw.polygon(surf, (96, 74, 52, 255), tabard, 1)
        # Head & glowing amber eye peering right beneath tilted shepherd's hat
        pygame.draw.ellipse(surf, (22, 12, 30, 255), (cx - 6, 24 + bob, 18, 16))
        pygame.draw.circle(surf, (248, 206, 86, 255), (cx + 7, 32 + bob), 2)
        surf.set_at((cx + 7, 32 + bob), (255, 248, 208, 255))
        pygame.draw.ellipse(surf, (38, 24, 48, 255), (cx - 22, 19 + bob, 50, 12))
        pygame.draw.ellipse(surf, (20, 10, 28, 255), (cx - 22, 19 + bob, 50, 12), 2)
        hat_crown = [(cx - 10, 22 + bob), (cx - 5, 8 + bob), (cx + 9, 10 + bob), (cx + 13, 22 + bob)]
        pygame.draw.polygon(surf, (52, 34, 62, 255), hat_crown)
        pygame.draw.line(surf, (214, 174, 68, 255), (cx - 9, 20 + bob), (cx + 12, 20 + bob), 2)
        # Forward-held redaction scythe tilting across stride frames
        sy_off = l_dy
        pygame.draw.line(surf, (66, 38, 22, 255), (cx - 8, height - 12), (width - 14, 18 + sy_off), 6)
        pygame.draw.line(surf, (118, 76, 42, 255), (cx - 8, height - 12), (width - 14, 18 + sy_off), 3)
        blade = [
            (width - 14, 16 + sy_off), (width - 3, 23 + sy_off), (width - 4, 42 + sy_off),
            (width - 18, 52 + sy_off), (width - 13, 35 + sy_off),
        ]
        pygame.draw.polygon(surf, (176, 186, 202, 255), blade)
        pygame.draw.polygon(surf, (52, 46, 68, 255), blade, 2)
        return surf

    if d_key == "up":
        # Back-turned shepherd-inquisitor: broad tar-soaked wool cloak, rear scythe & wide hat (no eyes)
        robe = [
            (cx - 24 + sway, height - 11), (cx - 19, 44 + bob), (cx - 22, 35 + bob),
            (cx + 22, 35 + bob), (cx + 19, 44 + bob), (cx + 24 + sway, height - 11),
            (cx, height - 8),
        ]
        pygame.draw.polygon(surf, (42, 20, 58, 255), robe)
        pygame.draw.polygon(surf, (24, 10, 34, 255), robe, 2)
        # Tar-stained lower cloak hem & rear scythe shaft crossing back
        pygame.draw.ellipse(surf, (38, 14, 58, 235), (cx - 20 + sway, height - 24, 40, 12))
        pygame.draw.line(surf, (66, 38, 22, 255), (20, height - 14), (width - 18, 20 + r_dy), 5)
        pygame.draw.line(surf, (118, 76, 42, 255), (20, height - 14), (width - 18, 20 + r_dy), 2)
        # Wide-brimmed weathered wool shepherd's hat from behind
        pygame.draw.ellipse(surf, (38, 24, 48, 255), (cx - 26, 20 + bob, 52, 12))
        pygame.draw.ellipse(surf, (20, 10, 28, 255), (cx - 26, 20 + bob, 52, 12), 2)
        hat_crown = [(cx - 12, 23 + bob), (cx - 8, 9 + bob), (cx + 8, 9 + bob), (cx + 12, 23 + bob)]
        pygame.draw.polygon(surf, (52, 34, 62, 255), hat_crown)
        pygame.draw.line(surf, (214, 174, 68, 255), (cx - 11, 21 + bob), (cx + 11, 21 + bob), 2)
        return surf

    # Crack notches in the upper brass ring (front canonical view)
    pygame.draw.line(surf, (24, 12, 34, 255), (cx + 12, halo_cy - 24), (cx + 18, halo_cy - 18), 3)
    pygame.draw.line(surf, (24, 12, 34, 255), (cx - 22, halo_cy - 12), (cx - 15, halo_cy - 8), 2)

    # 3. Gaunt shepherd-inquisitor torso in tar-soaked wool robes & tattered ruled-parchment stoles
    robe_poly = [
        (cx - 22 + sway, height - 12),
        (cx - 17, 46 + bob),
        (cx - 22, 36 + l_dy // 2 + bob),
        (cx + 22, 36 + r_dy // 2 + bob),
        (cx + 17, 46 + bob),
        (cx + 24 + sway, height - 12),
        (cx + 10 + sway, height - 16),
        (cx, height - 10),
        (cx - 10 + sway, height - 16),
    ]
    pygame.draw.polygon(surf, (46, 24, 62, 255), robe_poly)
    pygame.draw.polygon(surf, (24, 10, 34, 255), robe_poly, 2)

    # Ruled-parchment inquisitor tabard / shoulder stoles with horizontal ledger ink lines
    tabard = [
        (cx - 11, 39 + bob),
        (cx + 11, 39 + bob),
        (cx + 13 + sway // 2, height - 20),
        (cx + sway // 2, height - 15),
        (cx - 13 + sway // 2, height - 20),
    ]
    pygame.draw.polygon(surf, (216, 198, 160, 255), tabard)
    pygame.draw.polygon(surf, (96, 74, 52, 255), tabard, 1)
    for ly in range(44 + bob, height - 22, 6):
        pygame.draw.line(surf, (148, 124, 86, 210), (cx - 10, ly), (cx + 10, ly), 1)
    # Creeping violet-black tar stains climbing the hem of the parchment tabard
    pygame.draw.ellipse(surf, (42, 16, 62, 245), (cx - 13 + sway // 2, height - 30, 26, 14))
    pygame.draw.ellipse(surf, (138, 52, 174, 210), (cx - 8 + sway // 2, height - 26, 16, 7))
    for _ in range(18):
        gx = rng.randint(cx - 18, cx + 18)
        gy = rng.randint(42, height - 18)
        surf.set_at((gx, gy), (74, 34, 98, 220))

    # 4. Wide-brimmed dark shepherd's hat & hooded shadow face with glowing amber/violet eyes
    pygame.draw.ellipse(surf, (22, 12, 30, 255), (cx - 11, 24 + bob, 22, 18))
    eye_dx = -1 if f_idx == 1 else (1 if f_idx == 2 else 0)
    pygame.draw.circle(surf, (248, 206, 86, 255), (cx - 4 + eye_dx, 33 + bob), 2)
    pygame.draw.circle(surf, (248, 206, 86, 255), (cx + 4 + eye_dx, 33 + bob), 2)
    surf.set_at((cx - 4 + eye_dx, 33 + bob), (255, 248, 208, 255))
    surf.set_at((cx + 4 + eye_dx, 33 + bob), (255, 248, 208, 255))
    pygame.draw.ellipse(surf, (38, 24, 48, 255), (cx - 26, 20 + bob, 52, 12))
    pygame.draw.ellipse(surf, (20, 10, 28, 255), (cx - 26, 20 + bob, 52, 12), 2)
    hat_crown = [(cx - 12, 23 + bob), (cx - 8, 9 + bob), (cx + 7, 10 + bob), (cx + 12, 23 + bob)]
    pygame.draw.polygon(surf, (52, 34, 62, 255), hat_crown)
    pygame.draw.polygon(surf, (20, 10, 28, 255), hat_crown, 1)
    pygame.draw.line(surf, (214, 174, 68, 255), (cx - 11, 21 + bob), (cx + 11, 21 + bob), 2)

    # 5. Hooked redaction scythe held diagonally across body, dripping violet-black tar-ink
    pygame.draw.line(surf, (66, 38, 22, 255), (16, height - 10), (width - 20, 18 + r_dy), 6)
    pygame.draw.line(surf, (118, 76, 42, 255), (16, height - 10), (width - 20, 18 + r_dy), 3)
    pygame.draw.circle(surf, (214, 174, 68, 255), (width - 21, 19 + r_dy), 4)
    blade_pts = [
        (width - 20, 16 + r_dy),
        (width - 6, 22 + r_dy),
        (width - 4, 38 + r_dy),
        (width - 14, 52 + r_dy),
        (width - 24, 54 + r_dy),
        (width - 16, 44 + r_dy),
        (width - 13, 33 + r_dy),
        (width - 17, 24 + r_dy),
    ]
    pygame.draw.polygon(surf, (176, 186, 202, 255), blade_pts)
    pygame.draw.polygon(surf, (52, 46, 68, 255), blade_pts, 2)
    pygame.draw.lines(
        surf,
        (240, 244, 252, 255),
        False,
        [(width - 18, 17 + r_dy), (width - 7, 23 + r_dy), (width - 6, 37 + r_dy), (width - 14, 50 + r_dy)],
        2,
    )
    for dx_t, dy_t in ((width - 14, 55 + r_dy), (width - 18, 63 + r_dy), (width - 10, 48 + r_dy)):
        pygame.draw.ellipse(surf, (38, 14, 58, 245), (dx_t - 3, dy_t - 2, 6, 7))
        pygame.draw.circle(surf, (182, 84, 216, 230), (dx_t - 1, dy_t), 2)

    return surf


def generate_meadow_censor_scythe(
    width: int = 48, height: int = 56, rng: random.Random = None
) -> pygame.Surface:
    """Generate a 48x56 hooked redaction scythe planted upright in the turf after MeadowCensorBoss death."""
    _ = rng
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx = width // 2

    # Turf shadow & residual violet-black tar-ink puddle around planted shaft
    pygame.draw.ellipse(surf, (22, 10, 32, 140), (6, height - 12, width - 12, 9))
    pygame.draw.ellipse(surf, (78, 32, 112, 170), (11, height - 10, width - 22, 6))

    # Planted wooden haft leaning slightly into the ground
    pygame.draw.line(surf, (66, 38, 22, 255), (cx - 4, height - 7), (cx + 3, 9), 5)
    pygame.draw.line(surf, (124, 80, 44, 255), (cx - 4, height - 7), (cx + 3, 9), 3)
    pygame.draw.line(surf, (168, 118, 68, 255), (cx - 3, height - 10), (cx + 2, 11), 1)
    # Brass ferrule at blade mount
    pygame.draw.rect(surf, (214, 174, 68, 255), (cx, 8, 6, 5), border_radius=1)

    # Hooked crescent scythe blade curving to the right
    blade_pts = [
        (cx + 3, 9),
        (width - 6, 13),
        (width - 4, 26),
        (width - 12, 36),
        (cx + 4, 34),
        (width - 12, 27),
        (width - 11, 18),
        (cx + 3, 14),
    ]
    pygame.draw.polygon(surf, (176, 188, 204, 255), blade_pts)
    pygame.draw.polygon(surf, (48, 38, 62, 255), blade_pts, 2)
    pygame.draw.lines(
        surf,
        (242, 246, 255, 255),
        False,
        [(cx + 5, 10), (width - 7, 14), (width - 6, 25), (width - 12, 34)],
        1,
    )
    # Tar-ink droplets hanging from the scythe tip
    pygame.draw.ellipse(surf, (42, 16, 64, 245), (width - 14, 36, 5, 7))
    pygame.draw.circle(surf, (186, 86, 220, 230), (width - 12, 38), 1)
    return surf


def generate_frozen_script_monolith(
    width: int = TILE_WIDTH,
    height: int = 60,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x60 jagged glacier spire with suspended frozen ink script and rime-ice base."""
    if rng is None:
        rng = random.Random(DEFAULT_ASSET_SEED + 610)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2

    # Ground shadow and frosted snow/rime base
    pygame.draw.ellipse(surf, (18, 36, 64, 118), (4, height - 11, width - 8, 9))
    pygame.draw.ellipse(surf, (218, 240, 255, 245), (5, height - 14, width - 10, 10))
    pygame.draw.ellipse(surf, (164, 214, 246, 235), (8, height - 12, width - 16, 7))

    # Jagged translucent cobalt glacier spire silhouette
    spire_poly = [
        (7, height - 10),
        (9, 28),
        (13, 14),
        (cx - 1, 3),
        (cx + 6, 11),
        (width - 10, 22),
        (width - 7, height - 10),
    ]
    pygame.draw.polygon(surf, (78, 152, 214, 226), spire_poly)

    # Secondary dark glacier facet (right flank) & luminous ice bevel (left flank)
    right_facet = [
        (cx + 1, 6),
        (cx + 6, 11),
        (width - 10, 22),
        (width - 7, height - 10),
        (cx + 2, height - 10),
    ]
    pygame.draw.polygon(surf, (46, 104, 168, 228), right_facet)
    left_bevel = [
        (7, height - 10),
        (9, 28),
        (13, 14),
        (cx - 1, 3),
        (cx - 3, height - 11),
    ]
    pygame.draw.polygon(surf, (132, 206, 248, 195), left_bevel)

    # Suspended frozen columns of panicked Archivist ink script trapped inside the glacier core
    script_col_dark = (22, 34, 62, 215)
    script_col_mid = (36, 62, 108, 190)
    for col_x in (cx - 6, cx + 1):
        for gy in range(15, height - 15, 5):
            stroke_w = rng.randint(3, 5)
            col = script_col_dark if (gy % 10 == 0) else script_col_mid
            pygame.draw.line(surf, col, (col_x, gy), (col_x + stroke_w, gy), 1)
            if rng.random() < 0.65:
                pygame.draw.line(surf, col, (col_x + 1, gy + 2), (col_x + max(2, stroke_w - 1), gy + 2), 1)

    # Side glacial crystal shard jutting from lower left
    shard_poly = [(4, height - 12), (8, height - 26), (13, height - 14), (11, height - 9)]
    pygame.draw.polygon(surf, (148, 220, 255, 225), shard_poly)
    pygame.draw.polygon(surf, (226, 248, 255, 240), shard_poly, 1)

    # Crisp specular frost ridges and outline
    pygame.draw.line(surf, (232, 248, 255, 245), (cx - 1, 5), (cx - 4, height - 14), 1)
    pygame.draw.line(surf, (210, 242, 255, 220), (14, 16), (cx + 7, 30), 1)
    pygame.draw.polygon(surf, (28, 62, 108, 245), spire_poly, 1)

    # Rime snow tufts clinging to base edges
    for rx, ry, rr in ((10, height - 11, 3), (cx, height - 9, 4), (width - 11, height - 11, 3)):
        pygame.draw.circle(surf, (238, 250, 255, 245), (rx, ry), rr)
    return surf


def generate_frozen_rime_cask(
    width: int = TILE_WIDTH,
    height: int = TILE_HEIGHT,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 40x40 iron-hooped timber supply cask encrusted with thick rime frost and icicles."""
    if rng is None:
        rng = random.Random(DEFAULT_ASSET_SEED + 611)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)

    # Ground shadow
    pygame.draw.ellipse(surf, (18, 32, 54, 124), (5, height - 9, width - 10, 7))

    # Timber cask body (weathered frost-chilled oak)
    body_rect = pygame.Rect(8, 8, width - 16, height - 14)
    pygame.draw.rect(surf, (94, 78, 68, 255), body_rect, border_radius=6)
    pygame.draw.rect(surf, (74, 62, 56, 255), (10, 12, width - 20, height - 20), border_radius=4)

    # Vertical wooden staves with subtle frost grain
    for sx in range(12, width - 10, 4):
        shade = 108 if (sx % 8 == 0) else 66
        pygame.draw.line(surf, (shade, shade - 8, shade - 12, 235), (sx, 10), (sx, height - 8), 1)

    # Dark corroded iron hoops
    for hy in (15, height - 13):
        pygame.draw.rect(surf, (46, 56, 72, 255), (7, hy, width - 14, 4), border_radius=2)
        pygame.draw.line(surf, (148, 198, 228, 220), (9, hy), (width - 10, hy), 1)

    # Thick rime-frost snow cap over lid & upper rim
    pygame.draw.ellipse(surf, (220, 242, 255, 250), (7, 5, width - 14, 10))
    pygame.draw.ellipse(surf, (164, 214, 246, 240), (9, 7, width - 18, 6))
    pygame.draw.arc(surf, (245, 252, 255, 255), (8, 5, width - 16, 9), 0.15, 2.95, 2)

    # Hanging jagged icicles along the frosted upper rim
    icicle_specs = ((10, 13, 7), (15, 14, 9), (21, 14, 6), (26, 13, 10), (30, 13, 6))
    for ix, iy, ilen in icicle_specs:
        pts = [(ix - 2, iy), (ix + 2, iy), (ix, iy + ilen)]
        pygame.draw.polygon(surf, (186, 232, 255, 242), pts)
        pygame.draw.line(surf, (242, 252, 255, 255), (ix, iy), (ix, iy + max(2, ilen - 2)), 1)

    # Scattered rime frost flecks on lower staves
    for _ in range(10):
        fx = rng.randint(10, width - 11)
        fy = rng.randint(20, height - 9)
        surf.set_at((fx, fy), (212, 238, 255, 225))

    pygame.draw.rect(surf, (32, 48, 72, 250), body_rect, 1, border_radius=6)
    return surf


def generate_rimecrest_arbiter_boss(
    width: int = 104,
    height: int = 104,
    rng: random.Random = None,
    direction: str = "down",
    frame: int = 0,
) -> pygame.Surface:
    """Generate the 104x104 Rimecrest Arbiter boss sprite (down/up/side x frames 0..2)."""
    d_key = direction if direction in ("down", "up", "side") else "down"
    f_idx = int(frame) % 3
    if rng is None:
        rng = random.Random(DEFAULT_ASSET_SEED + 620 + f_idx * 23 + (0 if d_key == "down" else 89 if d_key == "up" else 173))
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2
    l_dy, r_dy, sway = _boss_stride_offsets(f_idx)
    bob = -1 if f_idx != 0 else 0

    # Glacial frost aura shadow at base
    pygame.draw.ellipse(surf, (16, 40, 74, 128), (18, height - 18, width - 36, 14))
    pygame.draw.ellipse(surf, (124, 212, 248, 86), (22, height - 16, width - 44, 10))

    if d_key == "side":
        # Three-quarter right-facing mirror-ice sentinel with billowing cloak & forward halberd
        cloak = [(cx - 8, 40 + bob), (14 - sway, 62), (10 - sway, height - 12), (cx + 12, height - 13)]
        pygame.draw.polygon(surf, (34, 72, 124, 255), cloak)
        pygame.draw.polygon(surf, (132, 206, 246, 220), cloak, 2)
        # Striding faceted greaves
        pygame.draw.polygon(surf, (52, 114, 178, 250), [(cx - 8 - sway, 68), (cx - 1 - sway, 68), (cx - 4 - sway, height - 10), (cx - 12 - sway, height - 10)])
        pygame.draw.polygon(surf, (88, 168, 226, 252), [(cx + 4 + sway, 68), (cx + 13 + sway, 68), (cx + 16 + sway, height - 10), (cx + 6 + sway, height - 10)])
        torso = [(cx - 12, 34 + bob), (cx + 14, 34 + bob), (cx + 16, 70 + bob), (cx - 10, 70 + bob)]
        pygame.draw.polygon(surf, (88, 168, 226, 252), torso)
        pygame.draw.polygon(surf, (218, 246, 255, 245), torso, 2)
        # Prominent forward jagged crystalline pauldron
        pauldron = [(cx - 6, 36 + l_dy // 2 + bob), (cx + 10, 26 + l_dy // 2 + bob), (cx + 22, 42 + l_dy // 2 + bob), (cx + 2, 48 + l_dy // 2 + bob)]
        pygame.draw.polygon(surf, (118, 198, 244, 250), pauldron)
        pygame.draw.polygon(surf, (226, 248, 255, 245), pauldron, 2)
        # Angled crystalline crown helm & right-facing cyan visor slit
        helm = [(cx - 10, 33 + bob), (cx - 9, 14 + bob), (cx - 2, 6 + bob), (cx + 8, 12 + bob), (cx + 14, 22 + bob), (cx + 12, 33 + bob)]
        pygame.draw.polygon(surf, (124, 204, 248, 255), helm)
        pygame.draw.polygon(surf, (238, 252, 255, 255), helm, 2)
        pygame.draw.rect(surf, (16, 36, 68, 255), (cx + 2, 21 + bob, 11, 6), border_radius=2)
        pygame.draw.line(surf, (176, 248, 255, 255), (cx + 4, 24 + bob), (cx + 12, 24 + bob), 2)
        # Forward-braced mirror-ice halberd
        hy_off = r_dy
        pygame.draw.line(surf, (46, 64, 92, 255), (cx - 4, height - 14), (width - 10, 12 + hy_off), 4)
        axe = [(width - 13, 15 + hy_off), (width - 2, 20 + hy_off), (width - 3, 38 + hy_off), (width - 14, 42 + hy_off), (width - 18, 30 + hy_off)]
        pygame.draw.polygon(surf, (132, 214, 252, 250), axe)
        pygame.draw.polygon(surf, (242, 252, 255, 255), axe, 2)
        return surf

    if d_key == "up":
        # Back-turned mirror-ice sentinel: rime-frosted cape, faceted backplate, rear crown (no visor)
        cloak = [
            (cx - 25, 40 + bob), (cx + 25, 40 + bob), (cx + 31 + sway, height - 11),
            (cx + 12 + sway, height - 15), (cx, height - 9), (cx - 12 + sway, height - 15), (cx - 31 + sway, height - 11),
        ]
        pygame.draw.polygon(surf, (30, 64, 112, 255), cloak)
        pygame.draw.polygon(surf, (132, 206, 246, 220), cloak, 2)
        # Rear halberd shaft angled behind shoulders
        pygame.draw.line(surf, (46, 64, 92, 255), (cx - 18, height - 14), (width - 16, 12 + r_dy), 4)
        # Faceted icy backplate & pauldrons
        back = [(cx - 18, 34 + bob), (cx + 18, 34 + bob), (cx + 14, 68 + bob), (cx, 75 + bob), (cx - 14, 68 + bob)]
        pygame.draw.polygon(surf, (56, 122, 188, 250), back)
        pygame.draw.polygon(surf, (218, 246, 255, 240), back, 2)
        pygame.draw.line(surf, (186, 246, 255, 240), (cx, 38 + bob), (cx, 70 + bob), 2)
        for side_p, dy_p in ((-1, l_dy // 2), (1, r_dy // 2)):
            p_poly = [(cx + side_p * 34, 46 + dy_p + bob), (cx + side_p * 26, 28 + dy_p + bob), (cx + side_p * 14, 32 + dy_p + bob), (cx + side_p * 16, 48 + dy_p + bob)]
            pygame.draw.polygon(surf, (88, 168, 226, 250), p_poly)
            pygame.draw.polygon(surf, (226, 248, 255, 245), p_poly, 2)
        # Rear crystalline crown helm
        helm = [(cx - 13, 33 + bob), (cx - 14, 19 + bob), (cx - 9, 9 + bob), (cx - 4, 16 + bob), (cx, 5 + bob), (cx + 4, 16 + bob), (cx + 9, 9 + bob), (cx + 14, 19 + bob), (cx + 13, 33 + bob)]
        pygame.draw.polygon(surf, (96, 178, 232, 255), helm)
        pygame.draw.polygon(surf, (238, 252, 255, 255), helm, 2)
        return surf

    # Tattered rime-frosted surcoat / lower armor skirt (front canonical view)
    cloak_poly = [
        (cx - 24, 42 + bob),
        (cx + 24, 42 + bob),
        (cx + 30 + sway, height - 12),
        (cx + 12 + sway, height - 16),
        (cx, height - 10),
        (cx - 12 + sway, height - 16),
        (cx - 30 + sway, height - 12),
    ]
    pygame.draw.polygon(surf, (34, 72, 124, 255), cloak_poly)
    pygame.draw.polygon(surf, (132, 206, 246, 220), cloak_poly, 2)

    # Faceted mirror-ice breastplate & greaves
    torso_poly = [
        (cx - 19, 34 + bob),
        (cx + 19, 34 + bob),
        (cx + 15, 70 + bob),
        (cx, 78 + bob),
        (cx - 15, 70 + bob),
    ]
    pygame.draw.polygon(surf, (88, 168, 226, 252), torso_poly)
    right_chest = [(cx, 34 + bob), (cx + 19, 34 + bob), (cx + 15, 70 + bob), (cx, 78 + bob)]
    pygame.draw.polygon(surf, (52, 114, 178, 250), right_chest)
    pygame.draw.polygon(surf, (218, 246, 255, 245), torso_poly, 2)
    sigil = [(cx, 43 + bob), (cx + 7, 54 + bob), (cx, 65 + bob), (cx - 7, 54 + bob)]
    pygame.draw.polygon(surf, (186, 246, 255, 255), sigil)
    pygame.draw.polygon(surf, (248, 254, 255, 255), [(cx, 47 + bob), (cx + 3, 54 + bob), (cx, 61 + bob), (cx - 3, 54 + bob)])

    # Jagged crystalline ice pauldrons (left & right shoulders)
    left_pauldron = [(cx - 34, 46 + l_dy // 2 + bob), (cx - 26, 28 + l_dy // 2 + bob), (cx - 14, 32 + l_dy // 2 + bob), (cx - 16, 48 + l_dy // 2 + bob)]
    right_pauldron = [(cx + 34, 46 + r_dy // 2 + bob), (cx + 26, 28 + r_dy // 2 + bob), (cx + 14, 32 + r_dy // 2 + bob), (cx + 16, 48 + r_dy // 2 + bob)]
    pygame.draw.polygon(surf, (118, 198, 244, 250), left_pauldron)
    pygame.draw.polygon(surf, (68, 138, 198, 250), right_pauldron)
    pygame.draw.polygon(surf, (226, 248, 255, 245), left_pauldron, 2)
    pygame.draw.polygon(surf, (216, 244, 255, 245), right_pauldron, 2)

    # Crystalline crown helm & glowing ice-cyan visor slit
    helm_poly = [
        (cx - 13, 33 + bob),
        (cx - 14, 19 + bob),
        (cx - 9, 9 + bob),
        (cx - 4, 16 + bob),
        (cx, 5 + bob),
        (cx + 4, 16 + bob),
        (cx + 9, 9 + bob),
        (cx + 14, 19 + bob),
        (cx + 13, 33 + bob),
    ]
    pygame.draw.polygon(surf, (124, 204, 248, 255), helm_poly)
    pygame.draw.polygon(surf, (238, 252, 255, 255), helm_poly, 2)
    eye_dx = -1 if f_idx == 1 else (1 if f_idx == 2 else 0)
    pygame.draw.rect(surf, (16, 36, 68, 255), (cx - 9, 22 + bob, 18, 6), border_radius=2)
    pygame.draw.line(surf, (176, 248, 255, 255), (cx - 7 + eye_dx, 25 + bob), (cx + 7 + eye_dx, 25 + bob), 2)

    # Long frost-bound mirror-ice halberd held diagonally on the right
    shaft_start = (cx + 12, height - 10)
    shaft_end = (width - 14, 10 + r_dy)
    pygame.draw.line(surf, (46, 64, 92, 255), shaft_start, shaft_end, 4)
    pygame.draw.line(surf, (176, 228, 252, 235), (shaft_start[0] - 1, shaft_start[1]), (shaft_end[0] - 1, shaft_end[1]), 1)
    axe_head = [
        (width - 17, 15 + r_dy),
        (width - 4, 18 + r_dy),
        (width - 3, 36 + r_dy),
        (width - 15, 42 + r_dy),
        (width - 21, 31 + r_dy),
    ]
    pygame.draw.polygon(surf, (132, 214, 252, 250), axe_head)
    pygame.draw.polygon(surf, (242, 252, 255, 255), axe_head, 2)
    spear_tip = [(width - 16, 13 + r_dy), (width - 10, 2 + r_dy), (width - 9, 15 + r_dy)]
    pygame.draw.polygon(surf, (212, 246, 255, 255), spear_tip)

    # Fine frost-crystal glints across the armor
    for _ in range(18):
        gx = rng.randint(cx - 26, cx + 26)
        gy = rng.randint(16, height - 18)
        if surf.get_at((gx, gy)).a > 160:
            surf.set_at((gx, gy), (240, 252, 255, 245))
    return surf


def generate_rimecrest_halberd(
    width: int = 48,
    height: int = 56,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 48x56 shattered mirror-ice halberd planted upright in cracked rime slate."""
    if rng is None:
        rng = random.Random(DEFAULT_ASSET_SEED + 621)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2

    # Cracked rime slate base & frost pool
    pygame.draw.ellipse(surf, (26, 56, 94, 155), (6, height - 14, width - 12, 11))
    pygame.draw.ellipse(surf, (172, 224, 252, 225), (10, height - 12, width - 20, 7))

    # Planted iron-frost shaft tilted slightly upright
    pygame.draw.line(surf, (44, 62, 92, 255), (cx - 4, height - 8), (cx + 4, 7), 4)
    pygame.draw.line(surf, (186, 232, 255, 235), (cx - 5, height - 9), (cx + 3, 7), 1)

    # Shattered crystalline mirror-ice halberd head
    blade_poly = [
        (cx + 3, 10),
        (width - 6, 14),
        (width - 7, 30),
        (cx + 1, 34),
        (cx - 2, 22),
    ]
    pygame.draw.polygon(surf, (112, 198, 246, 245), blade_poly)
    pygame.draw.polygon(surf, (238, 252, 255, 255), blade_poly, 2)
    # Jagged fracture notch in the blade & spear point
    pygame.draw.line(surf, (30, 64, 112, 240), (cx + 4, 20), (width - 9, 25), 2)
    pygame.draw.polygon(surf, (206, 244, 255, 255), [(cx + 1, 9), (cx + 6, 2), (cx + 8, 11)])

    # Broken crystalline frost splinters resting around the base
    for sx, sy, sr in ((cx - 11, height - 11, 3), (cx + 9, height - 10, 4), (cx + 2, height - 7, 2)):
        pts = [(sx - sr, sy), (sx, sy - sr - 2), (sx + sr, sy + 1)]
        pygame.draw.polygon(surf, (188, 236, 255, 240), pts)
    for _ in range(6):
        fx = rng.randint(10, width - 10)
        fy = rng.randint(height - 14, height - 5)
        surf.set_at((fx, fy), (242, 252, 255, 235))
    return surf


def generate_frozen_ice_block_stage(
    stage: int = 0,
    width: int = 64,
    height: int = 64,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 64x64 translucent crystalline Ice Block overlay for stage 0 (pristine), 1 (cracked), or 2 (shattering)."""
    stage = max(0, min(2, int(stage)))
    if rng is None:
        rng = random.Random(DEFAULT_ASSET_SEED + 622 + stage * 13)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx, cy = width // 2, height // 2

    # Translucent faceted crystal block outline (slightly notched at stage 2)
    if stage < 2:
        block_poly = [
            (10, 14),
            (22, 5),
            (46, 6),
            (55, 16),
            (57, 48),
            (48, 58),
            (15, 58),
            (7, 47),
        ]
    else:
        block_poly = [
            (11, 16),
            (20, 7),
            (32, 11),
            (45, 7),
            (54, 18),
            (56, 46),
            (47, 57),
            (16, 57),
            (8, 46),
        ]

    # Translucent body so encased Scholar remains clearly visible inside
    fill_alpha = (138, 126, 112)[stage]
    pygame.draw.polygon(surf, (118, 212, 252, fill_alpha), block_poly)
    # Bevel highlights along top-left facet & deep cobalt shade along bottom-right
    pygame.draw.polygon(
        surf,
        (210, 246, 255, 120),
        [(10, 14), (22, 5), (46, 6), (34, 22), (14, 28)],
    )
    pygame.draw.polygon(
        surf,
        (46, 118, 184, 96),
        [(55, 16), (57, 48), (48, 58), (34, 54), (44, 30)],
    )
    # Diagonal specular ice streaks
    pygame.draw.line(surf, (246, 254, 255, 190), (16, 16), (29, 32), 2)
    pygame.draw.line(surf, (246, 254, 255, 160), (26, 12), (41, 28), 1)
    pygame.draw.polygon(surf, (226, 248, 255, 235), block_poly, 2)

    # Stage 1+: fractured web cracks radiating from center
    if stage >= 1:
        crack_col = (242, 252, 255, 240)
        shadow_col = (26, 70, 124, 215)
        web_lines = [
            ((cx - 2, cy - 2), (16, 16)),
            ((cx - 2, cy - 2), (48, 14)),
            ((cx - 2, cy - 2), (14, 46)),
            ((cx - 2, cy - 2), (50, 48)),
            ((24, 24), (11, 30)),
            ((40, 24), (53, 28)),
        ]
        for p0, p1 in web_lines:
            pygame.draw.line(surf, shadow_col, (p0[0] + 1, p0[1] + 1), (p1[0] + 1, p1[1] + 1), 2)
            pygame.draw.line(surf, crack_col, p0, p1, 1)

    # Stage 2: deep shattered fissures + flying crystalline frost splinters
    if stage >= 2:
        deep_fissures = [
            ((cx, cy), (cx - 18, 8)),
            ((cx, cy), (cx + 16, 56)),
            ((cx, cy), (8, cy + 4)),
            ((cx, cy), (56, cy - 6)),
            ((22, 40), (34, 54)),
            ((42, 36), (30, 12)),
        ]
        for p0, p1 in deep_fissures:
            pygame.draw.line(surf, (18, 52, 98, 235), p0, p1, 3)
            pygame.draw.line(surf, (248, 254, 255, 250), p0, p1, 1)
        for sx, sy in ((5, 11), (58, 12), (4, 52), (59, 51)):
            pts = [(sx, sy), (sx + 3, sy - 4), (sx + 4, sy + 2)]
            pygame.draw.polygon(surf, (216, 246, 255, 235), pts)
    for _ in range(8):
        fx = rng.randint(12, width - 12)
        fy = rng.randint(12, height - 12)
        if surf.get_at((fx, fy)).a > 40:
            surf.set_at((fx, fy), (245, 253, 255, 220))
    return surf


def generate_ice_rubble_pile(
    width: int = 48,
    height: int = 36,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a 48x36 scattered pile of jagged translucent ice shards on the ground."""
    if rng is None:
        rng = random.Random(DEFAULT_ASSET_SEED + 626)
    surf = pygame.Surface((width, height), pygame.SRCALPHA)

    # Frost dust bed
    pygame.draw.ellipse(surf, (166, 222, 250, 110), (4, 8, width - 8, height - 12))
    shards = [
        [(7, 22), (14, 11), (21, 18), (15, 27)],
        [(18, 14), (28, 6), (35, 16), (25, 22)],
        [(26, 24), (36, 15), (43, 24), (33, 30)],
        [(12, 27), (22, 21), (27, 29), (18, 32)],
        [(5, 15), (10, 9), (13, 15)],
        [(36, 11), (42, 8), (44, 15)],
    ]
    for idx, poly in enumerate(shards):
        col = (128, 214, 252, 226) if idx % 2 == 0 else (84, 174, 232, 220)
        pygame.draw.polygon(surf, col, poly)
        pygame.draw.polygon(surf, (238, 252, 255, 245), poly, 1)
    for _ in range(14):
        fx = rng.randint(6, width - 7)
        fy = rng.randint(7, height - 6)
        surf.set_at((fx, fy), (240, 252, 255, 225))
    return surf


def generate_all_assets(
    floor_path: str = DEFAULT_FLOOR_PATH,
    wall_path: str = DEFAULT_WALL_PATH,
    grass_path: str = DEFAULT_GRASS_PATH,
    rock_path: str = DEFAULT_ROCK_PATH,
    chronicle_path: str = DEFAULT_CHRONICLE_PATH,
    respite_path: str = DEFAULT_RESPITE_PATH,
    respite_corrupted_path: str = DEFAULT_RESPITE_CORRUPTED_PATH,
    chronicler_path: str = DEFAULT_CHRONICLER_PATH,
    binder_path: str = DEFAULT_BINDER_PATH,
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
    vitreous_salt_floor_path: str = DEFAULT_VITREOUS_SALT_FLOOR_PATH,
    vitreous_glass_flat_path: str = DEFAULT_VITREOUS_GLASS_FLAT_PATH,
    vitreous_salt_spire_path: str = DEFAULT_VITREOUS_SALT_SPIRE_PATH,
    vitreous_fire_chalice_path: str = DEFAULT_VITREOUS_FIRE_CHALICE_PATH,
    aqueduct_terracotta_floor_path: str = DEFAULT_AQUEDUCT_TERRACOTTA_FLOOR_PATH,
    aqueduct_moss_wall_path: str = DEFAULT_AQUEDUCT_MOSS_WALL_PATH,
    aqueduct_pillar_path: str = DEFAULT_AQUEDUCT_PILLAR_PATH,
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
    wellspring_path: str = DEFAULT_WELLSPRING_PATH,
    lotus_frame_path: str = DEFAULT_LOTUS_FRAME_PATH,
    bench_path: str = DEFAULT_BENCH_PATH,
    bench_north_path: str = DEFAULT_BENCH_NORTH_PATH,
    bench_east_path: str = DEFAULT_BENCH_EAST_PATH,
    bench_west_path: str = DEFAULT_BENCH_WEST_PATH,
    heavy_bookcase_path: str = DEFAULT_HEAVY_BOOKCASE_PATH,
    ink_urn_path: str = DEFAULT_INK_URN_PATH,
    inkwell_puddle_path: str = DEFAULT_INKWELL_PUDDLE_PATH,
    candelabra_path: str = DEFAULT_CANDELABRA_PATH,
    tree_structure_path: str = DEFAULT_TREE_STRUCTURE_PATH,
    bat_path: str = DEFAULT_BAT_PATH,
    flutter_path: str = DEFAULT_FLUTTER_PATH,
    bindling_path: str = DEFAULT_BINDLING_PATH,
    smear_path: str = DEFAULT_SMEAR_PATH,
    sentry_path: str = DEFAULT_SENTRY_PATH,
    punctuation_wolf_path: str = DEFAULT_PUNCTUATION_WOLF_PATH,
    event_champion_path: str = DEFAULT_EVENT_CHAMPION_PATH,
    miniboss_path: str = DEFAULT_MINIBOSS_PATH,
    night_boss_path: str = DEFAULT_NIGHT_BOSS_PATH,
    final_author_path: str = DEFAULT_FINAL_AUTHOR_PATH,
    torn_page_path: str = DEFAULT_TORN_PAGE_PATH,
    seed: int = DEFAULT_ASSET_SEED,
    stats_out: Dict[str, int] | None = None,
) -> Dict[str, str]:
    """Generate all procedural assets and save them to disk when pixel content changes.

    Returns a dictionary mapping asset names to their output file paths.
    """
    base_seed = DEFAULT_ASSET_SEED if seed is None else seed
    results: Dict[str, str] = {}
    updated_count = 0
    unchanged_count = 0

    def _emit(key: str, out_path: str, surf: pygame.Surface) -> None:
        nonlocal updated_count, unchanged_count
        if write_surface_if_changed(surf, out_path):
            updated_count += 1
        else:
            unchanged_count += 1
        results[key] = out_path

    def _rng(key: str) -> random.Random:
        return _asset_rng(base_seed, key)

    # 1-8. Core Tiles, Swamp Surfaces, Sanctuary Props, Swamp Props, and Biome Clutter
    core_specs = [
        ("floor_tile", floor_path, generate_floor_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("floor_tile"))),
        (
            "wall_tile",
            wall_path,
            generate_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("wall_tile"), variant="standard"),
        ),
        (
            "wall_tile_cracked",
            wall_cracked_path,
            generate_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("wall_tile_cracked"), variant="cracked"),
        ),
        (
            "wall_tile_mossy",
            wall_mossy_path,
            generate_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("wall_tile_mossy"), variant="mossy"),
        ),
        (
            "wall_tile_webbed",
            wall_webbed_path,
            generate_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("wall_tile_webbed"), variant="webbed"),
        ),
        ("swamp_water", swamp_water_path, generate_swamp_water_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("swamp_water"))),
        ("mud_turf", mud_turf_path, generate_mud_turf_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("mud_turf"))),
        ("peat_bank", peat_bank_path, generate_peat_bank_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("peat_bank"))),
        ("swamp_wall", swamp_wall_path, generate_swamp_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("swamp_wall"))),
        ("grass_natural", grass_path, generate_grass_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("grass_natural"))),
        ("rock_cluster", rock_path, generate_rock_cluster(TILE_WIDTH, TILE_HEIGHT, rng=_rng("rock_cluster"))),
        ("chronicle", chronicle_path, generate_chronicle(TILE_WIDTH, TILE_HEIGHT, rng=_rng("chronicle"))),
        ("respite", respite_path, generate_respite(TILE_WIDTH, TILE_HEIGHT, rng=_rng("respite"), corrupted=False)),
        (
            "respite_corrupted",
            respite_corrupted_path,
            generate_respite(TILE_WIDTH, TILE_HEIGHT, rng=_rng("respite_corrupted"), corrupted=True),
        ),
        ("chronicler", chronicler_path, generate_chronicler(TILE_WIDTH, TILE_HEIGHT, rng=_rng("chronicler"))),
        ("binder", binder_path, generate_binder(TILE_WIDTH, TILE_HEIGHT, rng=_rng("binder"))),
        ("swamp_fungus", swamp_fungus_path, generate_swamp_fungus(TILE_WIDTH, TILE_HEIGHT, rng=_rng("swamp_fungus"))),
        (
            "swamp_gas_vent",
            swamp_vent_path,
            generate_swamp_gas_vent(TILE_WIDTH, TILE_HEIGHT, rng=_rng("swamp_gas_vent")),
        ),
        ("swamp_thorns", swamp_thorns_path, generate_swamp_thorns(TILE_WIDTH, TILE_HEIGHT, rng=_rng("swamp_thorns"))),
        ("ruins_rubble", ruins_rubble_path, generate_ruins_rubble(TILE_WIDTH, TILE_HEIGHT, rng=_rng("ruins_rubble"))),
        ("swamp_flora", swamp_flora_path, generate_swamp_flora(TILE_WIDTH, TILE_HEIGHT, rng=_rng("swamp_flora"))),
        (
            "crypt_clutter",
            crypt_clutter_path,
            generate_crypt_clutter(TILE_WIDTH, TILE_HEIGHT, rng=_rng("crypt_clutter")),
        ),
        (
            "vitreous_salt_floor",
            vitreous_salt_floor_path,
            generate_vitreous_salt_floor_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("vitreous_salt_floor")),
        ),
        (
            "vitreous_glass_flat",
            vitreous_glass_flat_path,
            generate_vitreous_glass_flat_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("vitreous_glass_flat")),
        ),
        (
            "vitreous_salt_spire",
            vitreous_salt_spire_path,
            generate_vitreous_salt_spire(TILE_WIDTH, TILE_HEIGHT, rng=_rng("vitreous_salt_spire")),
        ),
        (
            "vitreous_fire_chalice",
            vitreous_fire_chalice_path,
            generate_vitreous_fire_chalice(80, 80, rng=_rng("vitreous_fire_chalice")),
        ),
        (
            "aqueduct_terracotta_floor",
            aqueduct_terracotta_floor_path,
            generate_aqueduct_terracotta_floor_tile(
                TILE_WIDTH, TILE_HEIGHT, rng=_rng("aqueduct_terracotta_floor")
            ),
        ),
        (
            "aqueduct_moss_wall",
            aqueduct_moss_wall_path,
            generate_aqueduct_moss_wall_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("aqueduct_moss_wall")),
        ),
        (
            "aqueduct_pillar",
            aqueduct_pillar_path,
            generate_aqueduct_pillar(TILE_WIDTH, TILE_HEIGHT, rng=_rng("aqueduct_pillar")),
        ),
    ]
    for key, out_path, surf in core_specs:
        _emit(key, out_path, surf)

    # 9. 2.5D Verticality & Elevation Assets
    verticality_specs = [
        ("wall_top_cap", wall_top_cap_path, generate_wall_top_cap(TILE_WIDTH, TILE_HEIGHT, rng=_rng("wall_top_cap"))),
        (
            "wall_front_face",
            wall_front_face_path,
            generate_wall_front_face(TILE_WIDTH, TILE_HEIGHT, rng=_rng("wall_front_face")),
        ),
        (
            "shadow_south",
            shadow_south_path,
            generate_floor_shadow_overlay(TILE_WIDTH, TILE_HEIGHT, "south", rng=_rng("shadow_south")),
        ),
        (
            "shadow_east",
            shadow_east_path,
            generate_floor_shadow_overlay(TILE_WIDTH, TILE_HEIGHT, "east", rng=_rng("shadow_east")),
        ),
        (
            "shadow_corner",
            shadow_corner_path,
            generate_floor_shadow_overlay(TILE_WIDTH, TILE_HEIGHT, "corner", rng=_rng("shadow_corner")),
        ),
        ("cliff_edge", cliff_edge_path, generate_cliff_edge_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("cliff_edge"))),
        (
            "staircase_tile",
            staircase_path,
            generate_staircase_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("staircase_tile")),
        ),
        ("pit_rim", pit_rim_path, generate_pit_rim_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("pit_rim"))),
        (
            "boss_dais_tile",
            boss_dais_path,
            generate_boss_dais_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("boss_dais_tile")),
        ),
        (
            "boss_pillar_tile",
            boss_pillar_path,
            generate_boss_pillar_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("boss_pillar_tile")),
        ),
        (
            "boss_abyss_rim",
            boss_abyss_rim_path,
            generate_boss_abyss_rim(TILE_WIDTH, TILE_HEIGHT, rng=_rng("boss_abyss_rim")),
        ),
    ]
    for key, out_path, surf in verticality_specs:
        _emit(key, out_path, surf)

    # Pipeline 11: Act 2 Empowered / Corrupted Procedural Enemy Variants
    empowered_specs = [
        ("bat_empowered", "bat", 40, 40),
        ("flutter_empowered", "flutter", 40, 40),
        ("bindling_empowered", "bindling", 40, 40),
        ("smear_empowered", "smear", 40, 40),
        ("sentry_empowered", "sentry", 40, 40),
        ("punctuation_wolf_empowered", "punctuation_wolf", 40, 40),
        ("boss_empowered", "boss", 64, 64),
    ]
    for key, kind, w, h in empowered_specs:
        out_path = os.path.join("assets", "graphics", f"{key}.png")
        surf = generate_empowered_enemy_sprite(kind, w, h, rng=_rng(key))
        _emit(key, out_path, surf)

    # Pipeline 12: Legacy Props & Landmarks
    legacy_prop_specs = [
        ("wellspring", wellspring_path, generate_wellspring(TILE_WIDTH, TILE_HEIGHT, rng=_rng("wellspring"))),
        ("lotus_frame", lotus_frame_path, generate_lotus_frame(TILE_WIDTH, TILE_HEIGHT, rng=_rng("lotus_frame"))),
        ("bench", bench_path, generate_bench(TILE_WIDTH * 2, TILE_HEIGHT, rng=_rng("bench"), facing="south")),
        (
            "bench_north",
            bench_north_path,
            generate_bench(TILE_WIDTH * 2, TILE_HEIGHT, rng=_rng("bench_north"), facing="north"),
        ),
        (
            "bench_east",
            bench_east_path,
            generate_bench(TILE_WIDTH, TILE_HEIGHT * 2, rng=_rng("bench_east"), facing="east"),
        ),
        (
            "bench_west",
            bench_west_path,
            generate_bench(TILE_WIDTH, TILE_HEIGHT * 2, rng=_rng("bench_west"), facing="west"),
        ),
        (
            "heavy_bookcase",
            heavy_bookcase_path,
            generate_heavy_bookcase(TILE_WIDTH * 2, TILE_HEIGHT, rng=_rng("heavy_bookcase")),
        ),
        ("ink_urn", ink_urn_path, generate_ink_urn(TILE_WIDTH, TILE_HEIGHT, rng=_rng("ink_urn"))),
        (
            "inkwell_puddle",
            inkwell_puddle_path,
            generate_inkwell_puddle(TILE_WIDTH, TILE_HEIGHT, rng=_rng("inkwell_puddle")),
        ),
        ("candelabra", candelabra_path, generate_candelabra(TILE_WIDTH, TILE_HEIGHT, rng=_rng("candelabra"))),
        (
            "tree_structure",
            tree_structure_path,
            generate_tree_structure(TILE_WIDTH, TILE_HEIGHT, rng=_rng("tree_structure")),
        ),
    ]
    for key, out_path, surf in legacy_prop_specs:
        _emit(key, out_path, surf)

    # Pipeline 13: Act 1 / Un-Empowered Base Enemies & Bosses
    base_enemy_specs = [
        ("bat", bat_path, "bat", 40, 40),
        ("flutter", flutter_path, "flutter", 40, 40),
        ("bindling", bindling_path, "bindling", 40, 40),
        ("smear", smear_path, "smear", 40, 40),
        ("sentry", sentry_path, "sentry", 40, 40),
        ("punctuation_wolf", punctuation_wolf_path, "punctuation_wolf", 40, 40),
        ("event_champion", event_champion_path, "event_champion", 40, 40),
        ("miniboss", miniboss_path, "miniboss", 40, 40),
        ("night_boss", night_boss_path, "night_boss", 64, 64),
        ("final_author", final_author_path, "final_author", 80, 80),
    ]
    for key, out_path, kind, w, h in base_enemy_specs:
        surf = generate_base_enemy_sprite(kind, w, h, rng=_rng(key))
        _emit(key, out_path, surf)

    # Torn Page collectible pickup sprite
    _emit("torn_page", torn_page_path, generate_torn_page_sprite(TILE_WIDTH, TILE_HEIGHT, rng=_rng("torn_page")))

    # Pipeline 14: Assorted Procedural Weapon Pickup Sprites (Standard & Anomalous)
    weapon_pickup_specs = (
        "weapon_quill_standard",
        "weapon_quill_refined",
        "weapon_scriber_blade",
        "weapon_anomalous_bleed",
        "weapon_anomalous_regen",
        "weapon_anomalous_negation",
        "weapon_anomalous_stout",
        "weapon_anomalous_default",
    )
    for w_key in weapon_pickup_specs:
        out_path = os.path.join("assets", "graphics", f"{w_key}.png")
        surf = generate_weapon_pickup_sprite(w_key, TILE_WIDTH, TILE_HEIGHT, rng=_rng(w_key))
        _emit(w_key, out_path, surf)

    # Pipeline 15: Sanctuary Visual Assets & Low-Contrast Ground Texture Polish
    for idx in range(4):
        for prefix, gen_fn in (
            ("sanctuary_flagstone", generate_sanctuary_flagstone_tile),
            ("sanctuary_dirt_path", generate_sanctuary_dirt_path_tile),
            ("sanctuary_wood_floor", generate_sanctuary_wood_floor_tile),
        ):
            s_key = f"{prefix}_{idx}"
            out_path = os.path.join("assets", "graphics", f"{s_key}.png")
            surf = gen_fn(idx, TILE_WIDTH, TILE_HEIGHT, rng=_rng(s_key))
            _emit(s_key, out_path, surf)

    sanctuary_prop_specs = (
        (
            "sanctuary_roof_tile",
            generate_sanctuary_roof_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("sanctuary_roof_tile"), variant=0),
        ),
        (
            "sanctuary_roof_tile_1",
            generate_sanctuary_roof_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("sanctuary_roof_tile_1"), variant=1),
        ),
        (
            "sanctuary_roof_tile_2",
            generate_sanctuary_roof_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("sanctuary_roof_tile_2"), variant=2),
        ),
        (
            "sanctuary_roof_tile_3",
            generate_sanctuary_roof_tile(TILE_WIDTH, TILE_HEIGHT, rng=_rng("sanctuary_roof_tile_3"), variant=3),
        ),
        ("flutter_1", generate_flutter_frame(1, empowered=False, width=40, height=40, rng=_rng("flutter_1"))),
        ("flutter_2", generate_flutter_frame(2, empowered=False, width=40, height=40, rng=_rng("flutter_2"))),
        (
            "flutter_empowered_1",
            generate_flutter_frame(1, empowered=True, width=40, height=40, rng=_rng("flutter_empowered_1")),
        ),
        (
            "flutter_empowered_2",
            generate_flutter_frame(2, empowered=True, width=40, height=40, rng=_rng("flutter_empowered_2")),
        ),
        ("barrel_0", generate_barrel_frame(0, TILE_WIDTH, TILE_HEIGHT, rng=_rng("barrel_0"))),
        ("barrel_1", generate_barrel_frame(1, TILE_WIDTH, TILE_HEIGHT, rng=_rng("barrel_1"))),
        ("barrel_2", generate_barrel_frame(2, TILE_WIDTH, TILE_HEIGHT, rng=_rng("barrel_2"))),
        ("barrel_3", generate_barrel_frame(3, TILE_WIDTH, TILE_HEIGHT, rng=_rng("barrel_3"))),
        ("swamp_barrel", generate_swamp_barrel(TILE_WIDTH, TILE_HEIGHT, rng=_rng("swamp_barrel"))),
        ("pastoral_rock", generate_pastoral_rock(TILE_WIDTH, 60, rng=_rng("pastoral_rock"))),
        ("tree_structure_1", generate_tree_structure(TILE_WIDTH, TILE_HEIGHT, rng=_rng("tree_structure_1"), variant=1)),
        ("tree_structure_2", generate_tree_structure(TILE_WIDTH, TILE_HEIGHT, rng=_rng("tree_structure_2"), variant=2)),
        ("tree_structure_3", generate_tree_structure(TILE_WIDTH, TILE_HEIGHT, rng=_rng("tree_structure_3"), variant=3)),
        ("sanctuary_chimney", generate_sanctuary_chimney(TILE_WIDTH, TILE_HEIGHT * 2, rng=_rng("sanctuary_chimney"))),
        (
            "sanctuary_tree_canopy",
            generate_sanctuary_tree_canopy(TILE_WIDTH * 2, 100, rng=_rng("sanctuary_tree_canopy")),
        ),
        ("pond_lily_reeds", generate_pond_lily_reeds(TILE_WIDTH, TILE_HEIGHT, rng=_rng("pond_lily_reeds"))),
        ("garden_flora", generate_garden_flora(TILE_WIDTH, TILE_HEIGHT, rng=_rng("garden_flora"))),
        ("locked_shed_door", generate_locked_shed_door(TILE_WIDTH, TILE_HEIGHT, rng=_rng("locked_shed_door"))),
        ("mossy_gravestone", generate_mossy_gravestone(TILE_WIDTH, TILE_HEIGHT, rng=_rng("mossy_gravestone"))),
        (
            "sanctuary_window_wall",
            generate_sanctuary_window_wall(TILE_WIDTH, TILE_HEIGHT, rng=_rng("sanctuary_window_wall")),
        ),
        (
            "sanctuary_arch_doorway",
            generate_sanctuary_arch_doorway(TILE_WIDTH, TILE_HEIGHT, rng=_rng("sanctuary_arch_doorway")),
        ),
        (
            "highland_monolith",
            generate_highland_monolith(TILE_WIDTH, 60, rng=_rng("highland_monolith")),
        ),
        (
            "tech_server_pylon",
            generate_tech_server_pylon(TILE_WIDTH, 60, rng=_rng("tech_server_pylon")),
        ),
        (
            "tech_canister",
            generate_tech_canister(TILE_WIDTH, TILE_HEIGHT, rng=_rng("tech_canister")),
        ),
        (
            "swamp_spore_pod",
            generate_swamp_spore_pod(TILE_WIDTH, TILE_HEIGHT, rng=_rng("swamp_spore_pod")),
        ),
        (
            "slug_boss",
            generate_slug_boss(112, 112, rng=_rng("slug_boss")),
        ),
        (
            "slug_boss_crown",
            generate_slug_boss_crown(44, 32, rng=_rng("slug_boss_crown")),
        ),
        (
            "pastoral_shepherd_cairn",
            generate_pastoral_shepherd_cairn(TILE_WIDTH, 60, rng=_rng("pastoral_shepherd_cairn")),
        ),
        (
            "pastoral_hay_crate",
            generate_pastoral_hay_crate(TILE_WIDTH, TILE_HEIGHT, rng=_rng("pastoral_hay_crate")),
        ),
        (
            "meadow_censor_boss",
            generate_meadow_censor_boss(104, 104, rng=_rng("meadow_censor_boss")),
        ),
        (
            "meadow_censor_scythe",
            generate_meadow_censor_scythe(48, 56, rng=_rng("meadow_censor_scythe")),
        ),
        (
            "frozen_script_monolith",
            generate_frozen_script_monolith(TILE_WIDTH, 60, rng=_rng("frozen_script_monolith")),
        ),
        (
            "frozen_rime_cask",
            generate_frozen_rime_cask(TILE_WIDTH, TILE_HEIGHT, rng=_rng("frozen_rime_cask")),
        ),
        (
            "rimecrest_arbiter_boss",
            generate_rimecrest_arbiter_boss(104, 104, rng=_rng("rimecrest_arbiter_boss")),
        ),
        (
            "rimecrest_halberd",
            generate_rimecrest_halberd(48, 56, rng=_rng("rimecrest_halberd")),
        ),
        (
            "frozen_ice_block_0",
            generate_frozen_ice_block_stage(0, 64, 64, rng=_rng("frozen_ice_block_0")),
        ),
        (
            "frozen_ice_block_1",
            generate_frozen_ice_block_stage(1, 64, 64, rng=_rng("frozen_ice_block_1")),
        ),
        (
            "frozen_ice_block_2",
            generate_frozen_ice_block_stage(2, 64, 64, rng=_rng("frozen_ice_block_2")),
        ),
        (
            "ice_rubble_pile",
            generate_ice_rubble_pile(48, 36, rng=_rng("ice_rubble_pile")),
        ),
    )
    for sp_key, sp_surf in sanctuary_prop_specs:
        out_path = os.path.join("assets", "graphics", f"{sp_key}.png")
        _emit(sp_key, out_path, sp_surf)

    # Pipeline 16: 3-Frame Directional Boss Animations (down 1..2, up 0..2, side 0..2 for all 7 bosses)
    boss_anim_specs = (
        ("miniboss", 40, 40, generate_miniboss_sprite),
        ("night_boss", 64, 64, generate_night_boss_sprite),
        ("final_author", 80, 80, generate_final_author_sprite),
        ("boss_empowered", 64, 64, generate_boss_empowered_sprite),
        ("slug_boss", 112, 112, generate_slug_boss),
        ("meadow_censor_boss", 104, 104, generate_meadow_censor_boss),
        ("rimecrest_arbiter_boss", 104, 104, generate_rimecrest_arbiter_boss),
    )
    for b_stem, bw, bh, b_fn in boss_anim_specs:
        for b_dir in ("down", "up", "side"):
            for b_frame in (0, 1, 2):
                if b_dir == "down" and b_frame == 0:
                    continue  # Canonical <boss>.png already emitted above
                v_key = f"{b_stem}_{b_frame}" if b_dir == "down" else f"{b_stem}_{b_dir}_{b_frame}"
                out_path = os.path.join("assets", "graphics", f"{v_key}.png")
                surf = b_fn(bw, bh, rng=_rng(v_key), direction=b_dir, frame=b_frame)
                _emit(v_key, out_path, surf)

    # Pipeline 17: 5-Direction Steep-Overhead Player Hood-and-Shoulder Pixmaps (N/NE/E/SE/S x 4 poses)
    for p_dir in ("n", "ne", "e", "se", "s"):
        for p_pose in ("idle", "walk_0", "walk_1", "attack"):
            p_key = f"player_hood_{p_dir}_{p_pose}"
            out_path = os.path.join("assets", "graphics", f"{p_key}.png")
            surf = generate_player_hood_sprite(
                direction=p_dir,
                pose=p_pose,
                width=TILE_WIDTH,
                height=TILE_HEIGHT,
                rng=_rng(p_key),
            )
            _emit(p_key, out_path, surf)

    if stats_out is not None:
        stats_out["updated"] = updated_count
        stats_out["unchanged"] = unchanged_count
    return results


def generate_empowered_enemy_sprite(
    kind: str,
    width: int = 40,
    height: int = 40,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate a high-contrast Act 2 empowered enemy sprite with crimson/violet accents."""
    if rng is None:
        rng = random.Random(42 + sum(ord(c) for c in kind))

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
        return generate_flutter_frame(frame=0, empowered=True, width=width, height=height, rng=rng)
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
    elif kind == "punctuation_wolf":
        # Lupine silhouette shaped from punctuation glyphs & arching spine
        body_poly = [(6, cy + 5), (12, cy - 6), (cx + 4, cy - 8), (width - 6, cy - 1), (cx + 6, cy + 8)]
        pygame.draw.polygon(surf, obsidian, body_poly)
        pygame.draw.polygon(surf, charcoal, [(10, cy - 4), (14, 7), (18, cy - 4)])
        pygame.draw.polygon(surf, charcoal, [(cx - 1, cy - 5), (cx + 3, 6), (cx + 6, cy - 5)])
        # Arching crimson/violet spine arc & tail glyph
        pygame.draw.arc(surf, eclipse_violet, (5, cy - 10, width - 10, 18), 0.2, 2.9, 2)
        pygame.draw.line(surf, crimson, (6, cy + 3), (2, cy - 5), 2)
        pygame.draw.circle(surf, bright_crimson, (3, cy - 8), 2)
        # Sharp glyph fangs & predator eye
        pygame.draw.line(surf, bright_crimson, (width - 9, cy + 1), (width - 9, cy + 6), 2)
        pygame.draw.circle(surf, bright_crimson, (width - 12, cy - 3), 2)
    else:  # boss (Miniboss / Night Boss / Final Author)
        return generate_boss_empowered_sprite(width, height, rng=rng, direction="down", frame=0)

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


def generate_punctuation_wolf_empowered(
    width: int = 40,
    height: int = 40,
    rng: random.Random = None,
) -> pygame.Surface:
    """Generate the Act 2 empowered Punctuation Wolf sprite (40x40)."""
    return generate_empowered_enemy_sprite("punctuation_wolf", width, height, rng=rng)


def _asset_rng(base_seed: int, key: str) -> random.Random:
    """Return a deterministic per-asset Random instance independent of call order."""
    digest = zlib.crc32(f"{base_seed}:{key}".encode("utf-8"))
    return random.Random(digest)


def _surface_pixel_signature(surface: pygame.Surface) -> tuple[bool, bytes]:
    """Return (has_alpha, raw_bytes) using RGB for opaque surfaces and RGBA for alpha surfaces."""
    has_alpha = bool(surface.get_flags() & pygame.SRCALPHA) or surface.get_masks()[3] != 0
    fmt = "RGBA" if has_alpha else "RGB"
    return has_alpha, pygame.image.tobytes(surface, fmt)


def write_surface_if_changed(surface: pygame.Surface, output_path: str | Path) -> bool:
    """Save surface to output_path only if missing or pixels changed. Returns True if written."""
    target = str(output_path)
    if os.path.exists(target):
        try:
            existing = pygame.image.load(target)
            if (
                existing.get_size() == surface.get_size()
                and _surface_pixel_signature(existing) == _surface_pixel_signature(surface)
            ):
                return False
        except pygame.error:
            pass
    _ensure_directory(target)
    pygame.image.save(surface, target)
    return True


def main() -> None:
    """CLI entry point for procedural asset generation."""
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()

    print("==================================================")
    print(" Avoid Rain - Procedural PNG Asset Generator")
    print("==================================================")
    print("Generating dark-fantasy grit pixel art assets...")

    gen_stats: Dict[str, int] = {}
    written = generate_all_assets(stats_out=gen_stats)
    for name, path in written.items():
        size_kb = os.path.getsize(path) / 1024.0 if os.path.exists(path) else 0.0
        dims = f"{TILE_WIDTH}x{TILE_HEIGHT}"
        if os.path.exists(path):
            try:
                w_px, h_px = pygame.image.load(path).get_size()
                dims = f"{w_px}x{h_px}"
            except pygame.error:
                pass
        print(f"  [+] {name:<18} -> {path} ({size_kb:.1f} KB, {dims})")

    print(
        f"All assets processed: {gen_stats.get('updated', 0)} updated, "
        f"{gen_stats.get('unchanged', 0)} unchanged."
    )


if __name__ == "__main__":
    main()
