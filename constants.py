"""
Central registry for all game configuration and 'magic numbers'.
"""

import os
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

# Block Mechanics
BLOCK_DAMAGE_REDUCTION = 0.5
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

# Low-tier Slug enemy configuration
SLUG_MAX_HP = 40
SLUG_SPEED = 80.0  # pixels per second (slow approach)
SLUG_DETECT_METERS = 5  # detection radius in 'meters' (meters * TILE_SIZE)
SLUG_DAMAGE = 10  # damage dealt on contact
SLUG_DAMAGE_COOLDOWN = 1.0  # seconds between contact damage attempts
STAGGER_THRESHOLD = 20 # Damage needed to stagger
RECOVERY_TIME = 0.3 # Time spent in stagger/recovery

# Fast-pursuit Bat enemy configuration
BAT_MAX_HP = 20
BAT_SPEED = 150.0  # pixels per second (fast pursuit)
BAT_DETECT_METERS = 7  # detection radius
BAT_DAMAGE = 5  # damage dealt on contact
BAT_DAMAGE_COOLDOWN = 0.5  # seconds between contact damage attempts

# Skittish Flutter enemy configuration
FLUTTER_MAX_HP = 5
FLUTTER_SPEED = 200.0  # pixels per second (fast flee)
FLUTTER_DETECT_METERS = 6  # detection radius for fleeing
FLUTTER_DAMAGE = 2  # very low contact damage
FLUTTER_DAMAGE_COOLDOWN = 1.0

# Harasser Bindling enemy configuration
BINDLING_MAX_HP = 50
BINDLING_SPEED = 120.0  # Moderate speed
BINDLING_DETECT_METERS = 8
BINDLING_DAMAGE = 8
BINDLING_DAMAGE_COOLDOWN = 1.5
BINDLING_HEAL_RATE = 5.0  # HP per second near margins
BINDLING_HEAL_RADIUS = 2.0 # Tiles away from wall to trigger healing
BINDLING_BIND_DURATION = 1.0 # Duration of movement penalty applied to player

# Amorphous Smear enemy configuration
SMEAR_MAX_HP = 60
SMEAR_SPEED = 60.0 # Slow, viscous movement
SMEAR_DETECT_METERS = 6
SMEAR_DAMAGE = 10
SMEAR_DAMAGE_COOLDOWN = 1.2
SMEAR_PUDDLE_CHANCE = 0.5 # Chance per second to drop a puddle

# Techno-Sentry Anchor/Artillery enemy configuration
SENTRY_MAX_HP = 45
SENTRY_SPEED = 70.0
SENTRY_DETECT_METERS = 9
SENTRY_DAMAGE = 12
SENTRY_DAMAGE_COOLDOWN = 1.4
SENTRY_BEAM_RANGE = 160.0
SENTRY_BEAM_WIDTH = 24.0

# Edification Leveling Constants
EDIFICATION_BASE_COST = 10
EDIFICATION_COST_SCALE = 5
EDIFICATION_MAX_LEVEL = 50

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

# Miniboss configuration
MINIBOSS_MAX_HP = 300
MINIBOSS_SPEED = 100.0
MINIBOSS_DAMAGE = 20
MINIBOSS_DAMAGE_COOLDOWN = 1.5

# Autosave configuration
# Interval (seconds) between automatic saves
AUTOSAVE_INTERVAL = 30.0
# How long (seconds) a "Saved" indicator is shown after an autosave
AUTOSAVE_INDICATOR_DURATION = 2.0

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
MINIMAP_ENEMY_COLOR = (255, 0, 0) # Rule: Radar enemy dot is Red
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
    "maps/gantry_bridge.json",
    "maps/mire_causeway.json"
]

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
    'h': TILE_PROP, # Heavy Bookcase
    'd': TILE_PROP, # Ink-Drip Urn
    'v': TILE_HAZARD, # Spilled Inkwell Puddle
    'l': TILE_LIGHT, # Iron Candelabra
    'N': 107, # NightBoss Spawn
    '!': 108, # FinalAuthor Spawn
    'Y': 109, # SentryEnemy Spawn
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
        "floor_base": (44, 24, 68),
        "floor_alt": (58, 32, 88),
        "floor_accent": (55, 185, 105),
        "floor_speck": (225, 70, 190),
        "strata": [
            ((24, 36, 78), (38, 68, 118)),   # Stratum 0: Bioluminescent Bog Shallows
            ((44, 24, 68), (64, 36, 96)),    # Stratum 1: Murky Violet Spore-Peat
            ((86, 62, 46), (112, 82, 58))    # Stratum 2: Raised Cypress Causeway Planks
        ],
        "wall_top": (82, 46, 112),
        "wall_hi": (195, 95, 225),
        "wall_face": (52, 28, 76),
        "wall_mortar": (24, 12, 38),
        "wall_glow": (120, 255, 110)
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
    }
}

# Structural Schema enforced for all conversation manifests
DIALOGUE_MANIFEST = {
    "chronicler": [
        {
            "id": "chr_victory",
            "conditions": {"last_run_result": "VICTORY"},
            "priority": "100",
            "text": (
                "You did it! The wash was beautiful—the pages inside me felt "
                "completely clear for the first time in an age. You are a master editor, my friend!"
            )
        },
        {
            "id": "chr_defeat",
            "conditions": {"last_run_result": "DEFEAT"},
            "priority": "100",
            "text": (
                "You return... cold. I can still smell the burning ink on your hands. "
                "Please... give me a moment of quiet before you open the cover again."
            )
        },
        {
            "id": "chr_init",
            "conditions": {"last_run_result": "INIT"},
            "priority": "50",
            "text": "Welcome back to the Scriptorium, Reader. The pages are waiting whenever you are ready to begin."
        },
        {
            "id": "chr_fallback",
            "conditions": {}, # Empty means always valid
            "priority": "0",  # Checked last
            "text": "The pages are waiting whenever you are ready."
        }
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


