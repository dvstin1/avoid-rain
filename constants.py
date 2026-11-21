"""
Central registry for all game configuration and 'magic numbers'.
"""

import tempfile
from pathlib import Path

def get_generated_world_path() -> str:
    """Returns a cross-platform temporary path for the transient generated world JSON."""
    temp_dir = Path(tempfile.gettempdir())
    return str(temp_dir / "avoid_rain_generated_world.json")

# Window & Engine Configuration
ENGINE_REVISION = 2  # Increment when changes break compatibility with older save_data.json files
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Avoid Rain"

# Network Configuration (Phase 1: Discovery)
DEFAULT_PLAYER_NAME = "Scholar"
LAN_PORT = 55555

# Input Modes
INPUT_MODE_KEYBOARD = "KEYBOARD"
INPUT_MODE_GAMEPAD = "GAMEPAD"

# Selection & UI Colors
COLOR_SELECTION = (120, 255, 100) # Toxic Green
COLOR_MODE_KEYBOARD = (220, 220, 220)
COLOR_MODE_GAMEPAD = COLOR_SELECTION

# Gamepad Configuration
JOYSTICK_DEADZONE = 0.2

# Colors (R, G, B)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (200, 50, 50)
COLOR_YELLOW = (220, 200, 50) # Legacy support
COLOR_BLUE = (50, 50, 200)
COLOR_GREEN = (50, 200, 50)
COLOR_GREY = (100, 100, 100)
COLOR_CYAN = (0, 255, 255)
COLOR_PURPLE = (150, 50, 250)
COLOR_DARK_GREY = (40, 40, 40)

# Scriptorium Noir Palette
COLOR_SEPIA_AMBER = (40, 30, 20)  # Warm, low-contrast dark sepia
COLOR_CHARCOAL = (15, 15, 20)     # Cold, stark dark charcoal
COLOR_DEEP_SLATE = (45, 55, 70)   # Deep slate blue for Ink Urns
COLOR_INK_PUDDLE = (10, 10, 25)   # Deep ink blue/black
COLOR_CANDLE_AMBER = (255, 190, 40) # Warm candle light (Iron Candelabra)
COLOR_MARGIN_RED = (255, 60, 40)   # High-contrast telegraph color
COLOR_PARCHMENT_WHITE = (235, 230, 215) # Muted parchment white for player damage glyphs
COLOR_INK_CHARCOAL = (35, 25, 30)      # Archaic dark ink charcoal for damage glyphs

# Glyph Splatter Particle System
GLYPH_SPLATTER_POOL = ['†', '‡', '§', '¶', 'ø', '※', '×', '░', '▒']
GLYPH_MIN_COUNT = 4
GLYPH_MAX_COUNT = 7
GLYPH_MIN_LIFESPAN_FRAMES = 18
GLYPH_MAX_LIFESPAN_FRAMES = 28
GLYPH_GRAVITY_PER_FRAME = 0.25
GLYPH_FRICTION_X = 0.94
GLYPH_FONT_SIZE = 14

# The Ink & Fog Warp Transition Sequence
WARP_STAGE_IDLE = "IDLE"
WARP_STAGE_DEPARTURE = "DEPARTURE"
WARP_STAGE_THE_VEIL = "THE_VEIL"
WARP_STAGE_ARRIVAL = "ARRIVAL"
WARP_DEPARTURE_FRAMES = 35.0
WARP_VEIL_FRAMES = 12.0
WARP_ARRIVAL_FRAMES = 30.0
WARP_FOG_PUFF_COUNT = 24
WARP_GLYPH_COUNT = 16
WARP_GLYPH_POOL = ['†', '‡', '§', '¶', 'ø', '※', '×']
COLOR_WARP_FOG_INK = (18, 14, 22)
COLOR_WARP_FOG_PARCHMENT = (235, 230, 215)
COLOR_WARP_GLYPH_MUTED = (90, 80, 75)
WARP_PUFF_MIN_RADIUS = 16.0
WARP_PUFF_MAX_RADIUS = 32.0
WARP_PUFF_MIN_ALPHA = 70
WARP_PUFF_MAX_ALPHA = 160

# Combat Polish
STAGGER_DURATION = 0.25      # Seconds entities are locked when hit
PARRY_WINDOW = 0.15          # First frames of block/dash that count as parry
PARRY_STUN_DURATION = 0.8    # How long enemy is stunned after parry
SCREEN_SHAKE_INTENSITY = 4.0 # Pixels of max displacement
SCREEN_SHAKE_DURATION = 0.15 # Seconds of shake after hit
HIT_STOP_DURATION = 0.05     # Seconds of engine freeze on hit (approx 3 frames at 60fps)

# Player Configuration
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 40
PLAYER_START_X = SCREEN_WIDTH // 2
PLAYER_START_Y = SCREEN_HEIGHT // 2
PLAYER_SPEED = 300.0  # Pixels per second
PLAYER_MAX_HP = 100
FLASK_MAX_CHARGES = 3
FLASK_HEAL_AMOUNT = 40

# Dash Mechanics
DASH_DURATION = 0.2
BIND_DURATION = 1.5
DASH_COOLDOWN = 0.5
DASH_SPEED_MULTIPLIER = 3.0
DASH_SUBSTEP_MAX_PX = 8.0

# Block & Warding Mechanics
BLOCK_DAMAGE_REDUCTION = 0.5
WARDING_RAIN_DAMAGE_REDUCTION = 0.20
BLOCK_SPEED_MULTIPLIER = 0.5

# Combat Configuration
STAGGER_OUTLINE_TIME = 0.1  # Seconds
DAMAGE_NUMBER_LIFETIME = 1.0  # Seconds
DAMAGE_NUMBER_SPEED = 50.0  # Pixels per second upwards
SWORD_WIDTH = 60
SWORD_HEIGHT = 20
SWORD_OFFSET = 30 # Distance from player center
SWORD_DURATION = 0.2 # How long the attack lasts (seconds)
SWORD_DAMAGE = 10
SWORD_REACH = 64.0 # Max radius of sword slash matching visual sweep (pixels)
SWORD_ARC_RADIANS = 2.10 # Angular swing span (~120 degrees) matching renderer

# Anomalous Weapon Visual & Combat Feedback Colors
COLOR_ANOMALOUS_BLEED = (235, 55, 75)       # Crimson / Ink-Bleed
COLOR_ANOMALOUS_REGEN = (80, 235, 150)      # Verdant Emerald / Life-Thread / Vampirism
COLOR_ANOMALOUS_NEGATION = (255, 195, 60)   # Golden Amber / Iron-Nib / Fortitude
COLOR_ANOMALOUS_STOUT = (185, 95, 255)      # Deep Void Amethyst / Stout-Draft / Void-Strike
COLOR_ANOMALOUS_DEFAULT = (175, 75, 250)    # Standard Anomalous Arcane Purple
COLOR_SWORD_SLASH_DEFAULT = COLOR_CYAN      # Standard Common Weapon Cyan Shimmer
COLOR_IMPACT_SPARK_CORE = (255, 250, 220)   # Bright incandescent impact spark core
COLOR_IMPACT_SPARK_GLOW = (255, 200, 100)   # Warm outer spark halo

# Attack Feedback Visual Arc & Impact Sparks Configuration
SWORD_ARC_STEPS = 12
SLASH_FADE_DURATION = 0.14                  # Seconds the full visual slash arc fades after strike
IMPACT_SPARK_COUNT = 6                      # Number of sparks emitted per landed hit
IMPACT_SPARK_LIFETIME = 0.18                # Seconds sparks persist
IMPACT_SPARK_SPEED_MIN = 60.0               # Minimum initial spark speed (px/s)
IMPACT_SPARK_SPEED_MAX = 160.0              # Maximum initial spark speed (px/s)
IMPACT_SPARK_LENGTH = 5.0                   # Visual length of spark streak


def get_weapon_passive_color(weapon):
    """Return the dynamic tint color for a weapon's attack arc and feedback."""
    if not weapon:
        return COLOR_SWORD_SLASH_DEFAULT
    mods = weapon.get("modifiers", {})
    name = weapon.get("name", "").lower()

    if "bleed" in mods or "ink_bleed" in mods or "bleed" in name:
        color = COLOR_ANOMALOUS_BLEED
    elif "slow_hp_regen" in mods or "vampirism" in mods or "regen" in mods or "life" in name:
        color = COLOR_ANOMALOUS_REGEN
    elif (
        "damage_negation_on_hit" in mods
        or "parry_window" in mods
        or "negation" in mods
        or "iron" in name
    ):
        color = COLOR_ANOMALOUS_NEGATION
    elif "max_hp_boost" in mods or "void_strike" in mods or "stout" in mods or "void" in name:
        color = COLOR_ANOMALOUS_STOUT
    elif mods or "anomalous" in name:
        color = COLOR_ANOMALOUS_DEFAULT
    else:
        color = COLOR_SWORD_SLASH_DEFAULT
    return color


# Low-tier Slug enemy configuration
SLUG_MAX_HP = 65
SLUG_SPEED = 80.0  # pixels per second (slow approach)
SLUG_DETECT_METERS = 5  # detection radius in 'meters' (meters * TILE_SIZE)
SLUG_DAMAGE = 10  # damage dealt on contact
SLUG_DAMAGE_COOLDOWN = 1.0  # seconds between contact damage attempts
STAGGER_THRESHOLD = 20 # Damage needed to stagger
RECOVERY_TIME = 0.3 # Time spent in stagger/recovery

# Fast-pursuit Bat enemy configuration
BAT_MAX_HP = 35
BAT_SPEED = 150.0  # pixels per second (fast pursuit)
BAT_DETECT_METERS = 7  # detection radius
BAT_DAMAGE = 5  # damage dealt on contact
BAT_DAMAGE_COOLDOWN = 0.5  # seconds between contact damage attempts

# Skittish Flutter enemy configuration
FLUTTER_MAX_HP = 15
FLUTTER_SPEED = 200.0  # pixels per second (fast flee)
FLUTTER_DETECT_METERS = 6  # detection radius for fleeing
FLUTTER_DAMAGE = 2  # very low contact damage
FLUTTER_DAMAGE_COOLDOWN = 1.0

# Harasser Bindling enemy configuration
BINDLING_MAX_HP = 80
BINDLING_SPEED = 120.0  # Moderate speed
BINDLING_DETECT_METERS = 8
BINDLING_DAMAGE = 8
BINDLING_DAMAGE_COOLDOWN = 1.5
BINDLING_HEAL_RATE = 5.0  # HP per second near margins
BINDLING_HEAL_RADIUS = 2.0 # Tiles away from wall to trigger healing
BINDLING_BIND_DURATION = 1.0 # Duration of movement penalty applied to player

# Amorphous Smear enemy configuration
SMEAR_MAX_HP = 95
SMEAR_SPEED = 60.0 # Slow, viscous movement
SMEAR_DETECT_METERS = 6
SMEAR_DAMAGE = 10
SMEAR_DAMAGE_COOLDOWN = 1.2
SMEAR_PUDDLE_CHANCE = 0.5 # Chance per second to drop a puddle

# Techno-Sentry Anchor/Artillery enemy configuration
SENTRY_MAX_HP = 70
SENTRY_SPEED = 70.0
SENTRY_DETECT_METERS = 9
SENTRY_DAMAGE = 12
SENTRY_DAMAGE_COOLDOWN = 1.4
SENTRY_BEAM_RANGE = 160.0
SENTRY_BEAM_WIDTH = 24.0

# Punctuation Wolf pack-predator configuration
WOLF_MAX_HP = 60
WOLF_SPEED = 115.0
WOLF_POUNCE_SPEED = 360.0
WOLF_DETECT_METERS = 10
WOLF_POUNCE_RANGE = 175.0
WOLF_DAMAGE = 14
WOLF_DAMAGE_COOLDOWN = 1.15

# Edification Leveling Constants
EDIFICATION_BASE_COST = 10
EDIFICATION_COST_SCALE = 5
EDIFICATION_MAX_LEVEL = 50
PROWESS_ATTACK_STEP = 3
FORTIFICATION_HP_STEP = 10
CHOICE_OF_FATES_ATTACK_BASE = 3
CHOICE_OF_FATES_HP_BASE = 5
CHOICE_OF_FATES_MINOR_RATIO = 0.25
RESPITE_HOSTILE_BLOCK_RADIUS = 320.0

# Grid & World Configuration
TILE_SIZE = 40
MACRO_MAP_SIZE = 440
# Extra tiles to make the world larger than the visible screen (low-coupling constant)
WORLD_EXTRA_TILES_X = 60
WORLD_EXTRA_TILES_Y = 40
GRID_WIDTH = MACRO_MAP_SIZE
GRID_HEIGHT = MACRO_MAP_SIZE

# Camera smoothing configuration (how quickly the camera follows the target)
# Higher values = snappier (1.0 means it will take ~1s to reach target)
CAMERA_LERP_SPEED = 8.0

# Miniboss & Boss configuration
MINIBOSS_MAX_HP = 450
MINIBOSS_SPEED = 145.0
MINIBOSS_M2_SPEED = 175.0
MINIBOSS_M3_SPEED = 105.0
MINIBOSS_DAMAGE = 20
MINIBOSS_DAMAGE_COOLDOWN = 1.15
BOSS_WIND_UP_DURATION = 0.36
BOSS_STRIKE_DURATION = 0.25
BOSS_RECOVERY_DURATION = 0.52
BOSS_SWING_EXTRA_WIND_UP = 0.14
FINAL_AUTHOR_WIND_UP_DURATION = 0.50
BOSS_ANTI_CHEESE_RANGE = 360.0
BOSS_ANTI_CHEESE_STALL_TIME = 1.2
BOSS_RANGED_COOLDOWN = 2.4
BOSS_BOLT_SPEED = 320.0
BOSS_BOLT_DAMAGE = 12.0
BOSS_BOLT_RADIUS = 8
BOSS_BOLT_MAX_LIFETIME = 2.0
BOSS_FLANK_WEIGHT = 0.70
BOSS_STALL_MOVE_RATIO = 0.20
NIGHT_BOSS_MAX_HP = 950
FINAL_AUTHOR_MAX_HP = 1600
ACT_MINIBOSS_BUDGET = 4
SEGMENT_MINIBOSS_MIN_DIM = 100

# Autosave configuration
# Interval (seconds) between automatic saves
AUTOSAVE_INTERVAL = 30.0
# How long (seconds) a "Saved" indicator is shown after an autosave
AUTOSAVE_INDICATOR_DURATION = 2.0

# Sanctuary Roof Overhangs, Interior Fade & Atmospheric Micro-Animations (Pass 3)
SANCTUARY_INTERIOR_FADE_SPEED = 3.5
SANCTUARY_EXTERIOR_BLACKOUT_ALPHA = 235
SANCTUARY_CANDLE_GLOW_BASE_RADIUS = 32
SANCTUARY_CANDLE_GLOW_RADIUS_AMP = 5
SANCTUARY_CANDLE_GLOW_BASE_ALPHA = 68
SANCTUARY_CANDLE_GLOW_ALPHA_AMP = 22
SANCTUARY_FIREFLY_COUNT = 9
SANCTUARY_POND_RIPPLE_MAX_RADIUS = 16

# UI Overlay Constants
UI_ALPHA = 160
HUD_PANEL_W = 640
HUD_PANEL_H = 120
HUD_SLOT_W = 100
HUD_SLOT_H = 60
HUD_SWAP_BTN_W = 60
HUD_SWAP_BTN_H = 30
HUD_PICKUP_BTN_W = 80
HUD_PICKUP_BTN_H = 30
# Position buttons adjacent to each other in the HUD panel
HUD_SWAP_BTN_RECT = (110, 45, HUD_SWAP_BTN_W, HUD_SWAP_BTN_H)
HUD_PICKUP_BTN_RECT = (180, 45, HUD_PICKUP_BTN_W, HUD_PICKUP_BTN_H)

# Minimap configuration (pixels)
MINIMAP_WIDTH = 200
MINIMAP_HEIGHT = 150
MINIMAP_PADDING = 8
# Minimap tile marker color
MINIMAP_WALL_COLOR = (120, 120, 120)
MINIMAP_PLAYER_COLOR = (255, 255, 255) # Rule: Radar player dot is White
MINIMAP_ENEMY_COLOR = (255, 0, 0) # Debug mode high-contrast enemy dot
MINIMAP_ENEMY_STEALTH_COLOR = (135, 140, 148, 175) # Normal play muted slate-grey enemy dot
MINIMAP_LOOT_COLOR = (220, 200, 50)
# Zoom SCALE factor: Increased zoom (smaller fraction of world shown)
MINIMAP_VIEWPORT_FRAC = 2.5

# Map Module Pools
POOL_MONTHLY_REPORT = [
    "maps/windy_ridge.json",
    "maps/pastoral_valley.json",
    "maps/swamp_mire.json",
    "maps/frozen_peaks.json",
    "maps/tech_tower.json"
]
POOL_SPECIAL_EDITION = ["maps/tech_tower.json"]
POOL_CORRIDOR = [
    "maps/smallcave.json",
]

# Per-Biome Modular Segment Pools (Single-Biome World Stitching — All 7 Chronicle Biomes)
BIOME_SEGMENT_POOLS = {
    biome: {
        "rooms": [f"maps/segments/{biome}/{biome}_room_{i}.json" for i in range(1, 5)],
        "corridors": [f"maps/segments/{biome}/{biome}_corridor_{i}.json" for i in range(1, 5)],
    }
    for biome in (
        "windy_ridge",
        "pastoral_valley",
        "swamp_mire",
        "frozen_peaks",
        "tech_tower",
        "vitreous_basin",
        "sunlit_aqueducts",
    )
}

# Act-Keyed Segment Pools ((biome_id, act_number) -> {"rooms": [...], "corridors": [...]})
BIOME_ACT_SEGMENT_POOLS = {
    (biome, 1): {
        "rooms": list(pool["rooms"]),
        "corridors": list(pool["corridors"]),
    }
    for biome, pool in BIOME_SEGMENT_POOLS.items()
}

# Segment Fallback Mapping (reserved for unknown/unauthored future biome aliases)
BIOME_FALLBACK_MAP = {}

# 5-Act Unbound Chronicle Biome Selection & 7-Biome Roster (Section 12)
MAX_ACTS = 5
DEBUG_BIOME_SELECT = True
CHRONICLE_BIOME_ROSTER = (
    "windy_ridge",
    "pastoral_valley",
    "swamp_mire",
    "frozen_peaks",
    "tech_tower",
    "vitreous_basin",
    "sunlit_aqueducts",
)
BIOME_DISPLAY_NAMES = {
    "windy_ridge": "Windy Ridge",
    "pastoral_valley": "Pastoral Valley",
    "swamp_mire": "Swamp Mire",
    "frozen_peaks": "Frozen Peaks",
    "tech_tower": "Tech Tower",
    "vitreous_basin": "The Vitreous Basin",
    "sunlit_aqueducts": "The Sunlit Aqueducts",
}
BIOME_THEMES = {
    "windy_ridge": "Highland Scriptorium & Gale Cliffs",
    "pastoral_valley": "Sun-Drenched Meadow & Tar Sinks",
    "swamp_mire": "Bruised Hive Peat & Spore Pools",
    "frozen_peaks": "Rime-Frosted Slate & Mirror Ice",
    "tech_tower": "Brushed Titanium & Data-Bus Gantries",
    "vitreous_basin": "Sunken Glass & Refractive Salt Flats",
    "sunlit_aqueducts": "Overgrown Terracotta & Moss Viaducts",
}

# Weather System: The Bleed (Shrinking Circle)
# Measurements in pixels
WEATHER_MAX_RADIUS = 10000.0
WEATHER_MIN_RADIUS = 800.0  # Approx size of 40x40 module
WEATHER_WAIT_DURATION = 60.0  # Phase 1 duration
WEATHER_SHRINK_DURATION = 45.0 # Phase 2 duration
WEATHER_DAMAGE_PER_SECOND = 2.0
COLOR_TOXIC_RAIN = (120, 255, 100, 100) # RGBA for translucent toxic green
COLOR_SAFE_RAIN = (100, 200, 255, 80) # RGBA for clear, mundane rain (The Dilution)

# Tile Types
TILE_EMPTY = 0
TILE_WALL = 1
TILE_WARP = 2  # Special tile that warps the player to another map
TILE_RESPITE = 3
TILE_OBSTACLE = 4
TILE_PROP = 5
TILE_LOTUS_FRAME = 6
TILE_LORE = 7
TILE_HAZARD = 8
TILE_LIGHT = 9
TILE_STRUCTURE = 10
TILE_PATROL = 11
TILE_GRASS = 12
TILE_THICKET = 13

TILE_KEY = {
    '#': TILE_WALL,
    ' ': TILE_EMPTY, # Explicitly open floor
    '.': TILE_EMPTY,
    'g': TILE_GRASS,
    'G': TILE_THICKET,
    'W': TILE_WARP,
    'R': TILE_RESPITE,
    'T': TILE_STRUCTURE, # Protective Structure
    'B': TILE_PROP,
    'S': TILE_OBSTACLE, # Seat/Bench
    'K': TILE_OBSTACLE, # Rock
    'Z': 101, # SlugEnemy Spawn
    'A': 102, # BatEnemy Spawn
    'E': 103, # Miniboss Spawn
    'f': 104, # FlutterEnemy Spawn
    'b': 105, # BindlingEnemy Spawn
    's': 106, # SmearEnemy Spawn
    'P': 100, # Special marker for player start
    'M': TILE_LOTUS_FRAME,
    'X': TILE_WALL, # X also acts as a wall boundary
    'L': TILE_LORE,
    '&': TILE_PROP, # The Binder NPC
    'h': TILE_PROP, # Heavy Bookcase
    'd': TILE_PROP, # Ink-Drip Urn
    'v': TILE_HAZARD, # Spilled Inkwell Puddle
    'l': TILE_LIGHT, # Iron Candelabra
    'N': 107, # NightBoss Spawn
    '!': 108, # FinalAuthor Spawn
    'Y': 109, # SentryEnemy Spawn
    'w': 110, # PunctuationWolfEnemy Spawn
    '1': TILE_PATROL, # Patrol Marker 1
    '2': TILE_PATROL, # Patrol Marker 2
    '3': TILE_PATROL, # Patrol Marker 3
    '4': TILE_PATROL, # Patrol Marker 4
    '5': TILE_PATROL, # Patrol Marker 5
    '6': TILE_PATROL, # Patrol Marker 6
    '7': TILE_PATROL, # Patrol Marker 7
    '8': TILE_PATROL, # Patrol Marker 8
    '9': TILE_PATROL, # Patrol Marker 9
}

# Typographic Bloom (Chapter Titles)
BLOOM_FADE_IN = 1.0     # Seconds
BLOOM_HOLD = 2.0        # Seconds
BLOOM_FADE_OUT = 1.0    # Seconds
BLOOM_TOTAL_DURATION = BLOOM_FADE_IN + BLOOM_HOLD + BLOOM_FADE_OUT
BLOOM_COOLDOWN = 10.0   # Seconds between same-zone triggers
COLOR_BLOOM_TEXT = (220, 220, 220)
COLOR_BLOOM_SHADOW = (10, 10, 10)

# Colors for Tiles
COLOR_WALL = (60, 60, 60)
COLOR_FLOOR = (25, 25, 25)

# Procedural Enemy Colors
COLOR_BAT_BODY = (45, 40, 55)
COLOR_BAT_WING = (75, 50, 90)
COLOR_WOLF_GLYPH = (255, 215, 166)
COLOR_WOLF_SPINE = (132, 225, 255)
COLOR_WOLF_INK = (24, 32, 46)
COLOR_BAT_EYE = (255, 240, 200)
COLOR_FLUTTER_BODY = (207, 239, 255)
COLOR_FLUTTER_WING = (132, 225, 255)
COLOR_FLUTTER_MOTE = (191, 232, 255)
COLOR_BINDLING_PARCHMENT = (225, 240, 245)
COLOR_BINDLING_HOOD = (195, 225, 235)
COLOR_BINDLING_STITCH = (15, 40, 60)
COLOR_SMEAR_BLOB = (15, 35, 50)
COLOR_SMEAR_CORE = (110, 185, 210)
COLOR_BOSS_ARMOR = (75, 63, 53)
COLOR_BOSS_PAULDRON = (60, 47, 37)
COLOR_BOSS_VISOR = (44, 33, 32)
COLOR_BOSS_EYE = (255, 100, 100)
COLOR_SENTRY_CHASSIS = (48, 62, 88)
COLOR_SENTRY_FIN = (135, 170, 210)
COLOR_SENTRY_RING = (255, 65, 190)
COLOR_SENTRY_EYE = (0, 245, 255)
COLOR_SENTRY_BEAM = (0, 235, 255)

# Procedural Player (Scholar) & Weapon Colors
COLOR_PLAYER_CLOAK = (30, 50, 95)
COLOR_PLAYER_MANTLE = (55, 90, 155)
COLOR_PLAYER_HOOD = (40, 68, 125)
COLOR_PLAYER_COWL = (18, 24, 38)
COLOR_PLAYER_TRIM = (215, 185, 110)
COLOR_PLAYER_BOOT = (35, 30, 28)
COLOR_PLAYER_EYE = (180, 245, 255)
COLOR_PLAYER_SHIELD = (70, 95, 130)
COLOR_WEAPON_HILT = (65, 55, 50)
COLOR_WEAPON_GUARD = (190, 165, 105)
COLOR_WEAPON_BLADE = (210, 220, 235)
COLOR_WEAPON_EDGE = (245, 250, 255)
COLOR_WEAPON_FULLER = (50, 60, 80)

# High-Contrast 8-Bit Action-RPG Biome Tile Palettes (Ref: docs/reference.md)
BIOME_PALETTES = {
    "windy_ridge": {
        "floor_base": (26, 98, 60),
        "floor_alt": (34, 122, 74),
        "floor_accent": (110, 215, 130),
        "floor_speck": (235, 210, 110),
        "strata": [
            ((18, 76, 52), (28, 98, 66)),    # Stratum 0: Deep Viridian Clover Basin
            ((26, 98, 60), (42, 132, 78)),   # Stratum 1: Sunlit Emerald Meadow
            ((148, 122, 76), (175, 148, 96)) # Stratum 2: Ancient Limestone Cobble Trail
        ],
        "wall_top": (75, 105, 138),
        "wall_hi": (150, 215, 240),
        "wall_face": (46, 64, 92),
        "wall_mortar": (22, 32, 50),
        "wall_glow": (90, 235, 180)
    },
    "pastoral_valley": {
        "floor_base": (74, 198, 98),
        "floor_alt": (96, 220, 118),
        "floor_accent": (50, 158, 74),
        "floor_speck": (214, 178, 118),
        "strata": [
            ((28, 12, 42), (48, 22, 68)),     # Stratum 0: Recessed Deep-Plum Tar / Poison Swamp
            ((74, 198, 98), (96, 220, 118)),  # Stratum 1: Bright Lime/Mint Meadow Canvas
            ((188, 148, 92), (214, 178, 118)) # Stratum 2: Warm Tan & Soft Earthy Pathway
        ],
        "wall_top": (154, 114, 74),
        "wall_hi": (216, 178, 128),
        "wall_face": (94, 108, 126),
        "wall_mortar": (26, 22, 30),
        "wall_glow": (126, 88, 54)
    },
    "swamp_mire": {
        "floor_base": (34, 18, 48),      # Deep eggplant purple
        "floor_alt": (56, 28, 76),       # Bruised violet midtone
        "floor_accent": (142, 172, 44),  # Sickly mustard / pea-green highlight
        "floor_speck": (195, 168, 220),  # Pale lilac spore flecks
        "strata": [
            ((22, 10, 32), (32, 16, 44)),   # Stratum 0: Viscous Fluid & Sunken Sludge
            ((34, 18, 48), (56, 28, 76)),   # Stratum 1: Deep Eggplant Purple & Bruised Violet
            ((64, 34, 68), (96, 56, 92))   # Stratum 2: Raised Calcified Hive Chitin & Peat Bank
        ],
        "wall_top": (86, 44, 82),        # Mounded cellular hive tissue
        "wall_hi": (216, 202, 226),      # Pale lilac / bone-white upper bulge highlight
        "wall_face": (66, 30, 62),       # Fleshy bruised maroon/purple vertical face
        "wall_mortar": (18, 8, 22),      # Deep maroon/black undercut shadow
        "wall_glow": (148, 215, 68)      # Sickly pea-green spore glow
    },
    "frozen_peaks": {
        "floor_base": (68, 128, 182),
        "floor_alt": (88, 152, 208),
        "floor_accent": (180, 238, 255),
        "floor_speck": (240, 250, 255),
        "strata": [
            ((38, 86, 148), (58, 116, 182)), # Stratum 0: Deep Mirror-Glacier Ice
            ((68, 128, 182), (96, 162, 216)),# Stratum 1: Rime-Frosted Mountain Slate
            ((185, 225, 248), (220, 242, 255))# Stratum 2: Fresh Powder Snowdrifts
        ],
        "wall_top": (125, 188, 235),
        "wall_hi": (235, 250, 255),
        "wall_face": (68, 115, 168),
        "wall_mortar": (32, 58, 98),
        "wall_glow": (140, 245, 255)
    },
    "tech_tower": {
        "floor_base": (30, 40, 62),
        "floor_alt": (40, 54, 82),
        "floor_accent": (0, 230, 255),
        "floor_speck": (255, 65, 185),
        "strata": [
            ((14, 20, 36), (0, 145, 185)),   # Stratum 0: Recessed Reactor Trench Grating
            ((30, 40, 62), (46, 62, 92)),    # Stratum 1: Brushed Titanium Deck Plating
            ((58, 70, 102), (82, 98, 138))   # Stratum 2: Illuminated Data-Bus Walkway
        ],
        "wall_top": (64, 82, 112),
        "wall_hi": (160, 195, 230),
        "wall_face": (42, 54, 78),
        "wall_mortar": (18, 24, 38),
        "wall_glow": (0, 245, 255)
    },
    "sanctuary": {
        "floor_base": (48, 36, 26),
        "floor_alt": (60, 45, 32),
        "floor_accent": (135, 105, 68),
        "floor_speck": (215, 175, 95),
        "strata": [
            ((38, 28, 20), (52, 38, 28)),
            ((48, 36, 26), (64, 48, 34)),
            ((72, 54, 38), (96, 72, 50))
        ],
        "wall_top": (78, 64, 52),
        "wall_hi": (145, 120, 92),
        "wall_face": (52, 42, 34),
        "wall_mortar": (26, 20, 16),
        "wall_glow": (255, 195, 70)
    },
    "vitreous_basin": {
        "floor_base": (152, 195, 212),
        "floor_alt": (176, 218, 232),
        "floor_accent": (228, 248, 255),
        "floor_speck": (255, 255, 255),
        "strata": [
            ((86, 134, 162), (112, 164, 192)),
            ((152, 195, 212), (176, 218, 232)),
            ((212, 238, 246), (238, 250, 255))
        ],
        "wall_top": (168, 215, 232),
        "wall_hi": (240, 252, 255),
        "wall_face": (96, 142, 168),
        "wall_mortar": (42, 68, 88),
        "wall_glow": (180, 250, 255)
    },
    "sunlit_aqueducts": {
        "floor_base": (168, 108, 72),
        "floor_alt": (192, 128, 88),
        "floor_accent": (88, 178, 96),
        "floor_speck": (235, 204, 148),
        "strata": [
            ((42, 112, 128), (64, 144, 158)),
            ((168, 108, 72), (192, 128, 88)),
            ((92, 164, 84), (118, 192, 108))
        ],
        "wall_top": (186, 122, 82),
        "wall_hi": (232, 184, 136),
        "wall_face": (128, 76, 52),
        "wall_mortar": (54, 32, 24),
        "wall_glow": (132, 224, 124)
    }
}

# Structural Schema enforced for all conversation manifests
CHRONICLER_MUMBLE_SFX = {
    "neutral": "chronicler_mumble_neutral.ogg",
    "happy": "chronicler_mumble_happy.ogg",
    "disappointed": "chronicler_mumble_disappointed.ogg",
}

DIALOGUE_MANIFEST = {
    "chronicler": [
        {
            "id": "chr_stitch_victory",
            "conditions": {"last_run_result": "STITCH_VICTORY"},
            "priority": "120",
            "emotion": "happy",
            "text": (
                "The margin holds! I felt the Binder's counter-stitch lock the spine together—"
                "the ink-bleed cycle has truly halted. You have saved the Libram, Reader!"
            ),
        },
        {
            "id": "chr_victory",
            "conditions": {"last_run_result": "VICTORY"},
            "priority": "100",
            "emotion": "happy",
            "text": (
                "You did it! The wash was beautiful—the pages inside me felt "
                "completely clear for the first time in an age. You are a master editor, my friend!"
            )
        },
        {
            "id": "chr_defeat",
            "conditions": {"last_run_result": "DEFEAT"},
            "priority": "100",
            "emotion": "disappointed",
            "text": (
                "You return... cold. I can still smell the burning ink on your hands. "
                "Please... give me a moment of quiet before you open the cover again."
            )
        },
        {
            "id": "chr_init",
            "conditions": {"last_run_result": "INIT"},
            "priority": "50",
            "emotion": "neutral",
            "text": "Welcome back to the Scriptorium, Reader. The pages are waiting whenever you are ready to begin."
        },
        {
            "id": "chr_fallback",
            "conditions": {}, # Empty means always valid
            "priority": "0",  # Checked last
            "emotion": "neutral",
            "text": "The pages are waiting whenever you are ready."
        }
    ],
    "binder": [
        {
            "id": "binder_stitch_victory",
            "conditions": {"last_run_result": "STITCH_VICTORY"},
            "priority": "130",
            "emotion": "happy",
            "text": (
                "Three broken syntax seams, bound into a single counter-knot... "
                "and the Author's quill shattered against it. The stitch is whole, Reader. The bleed is over."
            ),
        },
        {
            "id": "binder_perfect_ready",
            "conditions": {"perfect_stitch_completed": True},
            "priority": "110",
            "emotion": "happy",
            "text": (
                "Listen to the margins hum! You resolved the three failed syntax seams in order. "
                "Carry this Perfect Stitch to the Final Author and we will halt the ink-bleed forever."
            ),
        },
        {
            "id": "binder_victory",
            "conditions": {"last_run_result": "VICTORY"},
            "priority": "90",
            "emotion": "neutral",
            "text": (
                "A clean wash, yet the spine still weeps. Force three syntax conflicts in sequence—"
                "Hemming, Serif, then Gloss—if you wish to bind the Author's madness permanently."
            ),
        },
        {
            "id": "binder_fallback",
            "conditions": {},
            "priority": "0",
            "emotion": "neutral",
            "text": (
                "Weave Margin Scraps into persistent run passives. Two scripts on the same stat clash—"
                "the stronger overwrites the weaker. Force three conflicts in sequence "
                "(Hemming -> Serif -> Gloss) to unlock the True Stitch ending."
            ),
        },
    ],
    "lore_fragments": {
        "wellspring_origin": (
            "The Wellspring. It sits at the absolute center of the Scriptorium. "
            "It doesn't draw from water tables in the earth; it is an active artesian "
            "pressure valve connected directly to the original, untainted source—the Unwritten Page."
        ),
        "chronicler_nature": (
            "The Chronicler is the physical manifestation of the book's original purpose. "
            "Before the Author went mad and corrupted the manuscript with 'The Bleed', "
            "the Chronicler was the entity designed to record history with clarity and care."
        ),
        "lotus_page": (
        "Within the Libram, reality follows typography. The master map structure is called "
        "the Lotus Page. The solid frame represents the immutable, preserved margins. "
        "The hollow cells are literal blank windows where stories are drafted."
        ),
        "half_cleft_manuscript": (
        "The quill was never meant to be a weapon. It was a tool of preservation. "
        "But when the ink began to boil, we had no choice but to sharpen the nibs. "
        "Half the world is now Cleft, separated by a margin that no longer holds its shape. "
        "If you are reading this, you are the last Editor. Please... finish the sentence we could not."
        ),
        "smear_viscosity": (
            "Smears are the most primitive of the Menagerie. They are little more than "
            "unfocused intent—ink that refused to dry and instead began to crawl. "
            "They are viscous and stubborn, often splitting into smaller blots when "
            "severed, as if trying to rewrite themselves into multiple sentences."
        )
        }
        }

# Sound attenuation constants
SFX_FULL_VOLUME_DIST = 120.0  # 3 units (3 * TILE_SIZE)
SFX_MIN_VOLUME_DIST = 1280.0  # Across the screen
SFX_MIN_VOLUME = 0.05

# Dynamic Rain Ambient Audio Constants
RAIN_LOOP_SFX = "rain_loop.ogg"
RAIN_CAMERA_VIEW_RADIUS = ((SCREEN_WIDTH / 2.0) ** 2 + (SCREEN_HEIGHT / 2.0) ** 2) ** 0.5
RAIN_AUDIO_WARNING_BUFFER = 1.5 * RAIN_CAMERA_VIEW_RADIUS
RAIN_AUDIO_APPROACH_MAX = 0.45
RAIN_AUDIO_INSIDE_MIN = 0.85
RAIN_AUDIO_INSIDE_MAX = 1.0
RAIN_AUDIO_INSIDE_RAMP_DIST = 240.0
RAIN_AUDIO_BOSS_FADE_DURATION = 1.25
BOSS_COMBAT_TRACKS = ("miniboss_combat.ogg", "night_boss.ogg", "final_reckoning.ogg")

# Title Screen Storm-and-Lightning Transition Constants
STORM_INTRO_SFX = "storm_intro.ogg"
TITLE_TRANSITION_FADE_IN_DURATION = 0.5
TITLE_TRANSITION_STORM_DURATION = 2.4
TITLE_TRANSITION_FADE_OUT_DURATION = 0.5
TITLE_LIGHTNING_BOLTS = ((0.35, 0.28), (1.25, 0.24))

# Act 2 & Final Boss Escalation Constants
ACT2_HP_MULTIPLIER = 2.0
ACT2_DAMAGE_MULTIPLIER = 2.0
ACT2_ESCALATION_BANNER = "THE STORM DEEPENS — EMPOWERED FOES STIR"
ACT2_ESCALATION_SFX = "bleed_start.ogg"

# 5-Act Saturation / Escalation Matrix (Nights 1–5, Section 12.1)
ACT_SATURATION_MATRIX = {
    1: {
        "act": 1,
        "tier": "base",
        "empowered": False,
        "hp_multiplier": 1.0,
        "damage_multiplier": 1.0,
        "rain_dps": 2.0,
        "page_yield_multiplier": 1.0,
        "banner": "ACT I: THE FIRST FOLIO",
        "label": "Night 1 — Low Saturation (Base Castes, 1.0x Pages)",
    },
    2: {
        "act": 2,
        "tier": "base",
        "empowered": False,
        "hp_multiplier": 1.25,
        "damage_multiplier": 1.25,
        "rain_dps": 2.5,
        "page_yield_multiplier": 1.25,
        "banner": "ACT II: THE SECOND FOLIO",
        "label": "Night 2 — Rising Saturation (Base+ Castes, 1.25x Pages)",
    },
    3: {
        "act": 3,
        "tier": "empowered",
        "empowered": True,
        "hp_multiplier": 1.6,
        "damage_multiplier": 1.6,
        "rain_dps": 3.0,
        "page_yield_multiplier": 1.5,
        "banner": "ACT III: THE SATURATED MARGIN",
        "label": "Night 3 — High Saturation (Empowered Castes, 1.5x Pages)",
    },
    4: {
        "act": 4,
        "tier": "empowered",
        "empowered": True,
        "hp_multiplier": 2.0,
        "damage_multiplier": 2.0,
        "rain_dps": 3.5,
        "page_yield_multiplier": 1.75,
        "banner": "ACT IV: THE DEEPENING BLEED",
        "label": "Night 4 — Severe Saturation (Empowered Castes, 1.75x Pages)",
    },
    5: {
        "act": 5,
        "tier": "empowered",
        "empowered": True,
        "hp_multiplier": 2.5,
        "damage_multiplier": 2.5,
        "rain_dps": 4.0,
        "page_yield_multiplier": 2.0,
        "banner": "ACT V: THE FINAL FOLIO",
        "label": "Night 5 — Abyssal Saturation (Saturated Castes, 2.0x Pages)",
    },
}


def get_act_saturation(act_number: int) -> dict:
    """Return the Act Saturation / Escalation config for the given Act (clamped to 1..MAX_ACTS)."""
    clamped = max(1, min(MAX_ACTS, int(act_number or 1)))
    return dict(ACT_SATURATION_MATRIX[clamped])


def scale_pages_for_act(base_pages: int, act_number: int) -> int:
    """Scale a positive Torn Page reward by the Act's saturation yield multiplier."""
    if base_pages <= 0:
        return int(base_pages)
    mult = float(get_act_saturation(act_number).get("page_yield_multiplier", 1.0))
    return max(1, int(round(base_pages * mult)))

# Marginalia Event Engine Constants (Section 10)
MARGINALIA_TRIGGER_CHANCE = 0.20
MARGINALIA_UNBLOTTED_WEIGHT = 0.14
MARGINALIA_MAX_STEP_IDX = 2
MARGINALIA_BANNER_HOLD_DURATION = 4.0
MARGINALIA_BREADCRUMB_MIN_DIST = 40.0
MARGINALIA_BREADCRUMB_MAX_LEN = 32
MARGINALIA_HUNTER_STALL_TIME = 0.35
MARGINALIA_HUNTER_PHASE_TIME = 0.45
MARGINALIA_FOLIO_DURATION = 35.0
MARGINALIA_FOLIO_RADIUS = 220.0
MARGINALIA_ERRATA_DURATION = 30.0
MARGINALIA_ERRATA_DIST = 240.0
MARGINALIA_CENSORED_DURATION = 25.0
MARGINALIA_CENSORED_TARGET_CHARGE = 8.0
MARGINALIA_CENSORED_RADIUS_ACT1 = 160.0
MARGINALIA_CENSORED_RADIUS_MIN_ACT2 = 95.0
MARGINALIA_DUEL_DURATION = 35.0
MARGINALIA_DUEL_RADIUS = 200.0
MARGINALIA_TOLL_DURATION = 30.0
MARGINALIA_CENSOR_HUNT_DURATION = 40.0
MARGINALIA_PRISTINE_SHIELD_DURATION = 25.0
MARGINALIA_STORM_IMMUNITY_DURATION = 15.0
MARGINALIA_ATTACK_SPEED_BUFF_DURATION = 20.0
MARGINALIA_DEBUFF_DURATION = 10.0
MARGINALIA_VIGNETTE_DURATION = 12.0
MARGINALIA_CELLAR_GRID_SIZE = 24

# A* Pathfinding & Patrol Navigation Constants (Section 4)
ACTOR_ACTIVE_SIMULATION_RADIUS_TILES = 48
PATHFINDING_MAX_RADIUS_TILES = 28
PATHFINDING_MAX_NODES = 650
PATHFINDING_REPATH_INTERVAL = 0.45
PATHFINDING_PATROL_REPATH_INTERVAL = 1.0
PATHFINDING_LOS_CACHE_INTERVAL = 0.40
PATHFINDING_WAYPOINT_REACH_PX = 12.0
PATROL_RETURN_SPEED_MULTIPLIER = 0.65
PATROL_STALL_SKIP_TIME = 2.5

# Section 7: Binder Scripts & Margin Scraps Economy Constants
SCRAPS_REWARD_NIGHT_BOSS_BASE = 1
SCRAPS_REWARD_NIGHT_BOSS_EMPOWERED = 2
SCRAPS_REWARD_MARGINALIA_EVENT = 0
SCRAPS_REWARD_FINAL_AUTHOR = 3
BINDER_MAX_EQUIPPED_SCRIPTS = 4
BINDER_MAX_DAMAGE_MITIGATION = 0.50
BINDER_PERFECT_STITCH_SEQUENCE = ("max_hp", "attack", "damage_mitigation")
BINDER_STITCH_STEP_LABELS = {
    "max_hp": "Hemming (HP)",
    "attack": "Serif (ATK)",
    "damage_mitigation": "Gloss (MIT)",
}

BINDER_SCRIPT_CATALOG = (
    {
        "id": "hemming_minor",
        "name": "Hemming Script",
        "stat": "max_hp",
        "value": 15.0,
        "cost": 2,
        "summary": "+15 Max HP",
        "desc": "Double-stitched margin thread that reinforces the Reader's vitality.",
    },
    {
        "id": "hemming_major",
        "name": "Vellum Buckram Script",
        "stat": "max_hp",
        "value": 35.0,
        "cost": 4,
        "summary": "+35 Max HP",
        "desc": "Heavy buckram backing that overrides weaker vitality hems.",
    },
    {
        "id": "serif_minor",
        "name": "Serifed Edge Script",
        "stat": "attack",
        "value": 2.0,
        "cost": 2,
        "summary": "+2 Attack",
        "desc": "Sharpens terminal strokes so every quill slash bites deeper.",
    },
    {
        "id": "serif_major",
        "name": "Rubricated Nib Script",
        "stat": "attack",
        "value": 5.0,
        "cost": 4,
        "summary": "+5 Attack",
        "desc": "Crimson rubrication compiler that overpowers lesser attack scripts.",
    },
    {
        "id": "footnote_minor",
        "name": "Running Footnote Script",
        "stat": "speed",
        "value": 18.0,
        "cost": 2,
        "summary": "+18 Move Speed",
        "desc": "Low-margin cadence notes that hasten the Reader's stride.",
    },
    {
        "id": "footnote_major",
        "name": "Cursive Ligature Script",
        "stat": "speed",
        "value": 36.0,
        "cost": 4,
        "summary": "+36 Move Speed",
        "desc": "Continuous joined glyph-strokes that eclipse minor footnote scripts.",
    },
    {
        "id": "gloss_minor",
        "name": "Marginal Gloss Script",
        "stat": "damage_mitigation",
        "value": 0.10,
        "cost": 2,
        "summary": "+10% Mitigation",
        "desc": "Protective commentary that absorbs a tenth of incoming harm.",
    },
    {
        "id": "gloss_major",
        "name": "Palimpsest Ward Script",
        "stat": "damage_mitigation",
        "value": 0.20,
        "cost": 4,
        "summary": "+20% Mitigation",
        "desc": "Layered parchment ward that overwrites thinner protective glosses.",
    },
    {
        "id": "gall_minor",
        "name": "Gall-Ink Thread Script",
        "stat": "bleed",
        "value": 3.0,
        "cost": 2,
        "summary": "+3.0 Bleed DPS",
        "desc": "Corrosive iron-gall filament that inflicts lingering ink-bleed on hit.",
    },
    {
        "id": "gall_major",
        "name": "Vitriol Stitch Script",
        "stat": "bleed",
        "value": 6.5,
        "cost": 4,
        "summary": "+6.5 Bleed DPS",
        "desc": "Caustic vitriol seam that dominates weaker bleed incisions.",
    },
)

BINDER_SCRIPTS_BY_ID = {entry["id"]: entry for entry in BINDER_SCRIPT_CATALOG}
