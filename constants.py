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

# Window Configuration
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Avoid Rain"

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
MINIBOSS_MAX_HP = 150
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
HUD_PANEL_W = 320
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
POOL_MONTHLY_REPORT = ["maps/forest.json", "maps/ruins.json"]
POOL_SPECIAL_EDITION = [] # Currently empty, will trigger fallback logic
POOL_CORRIDOR = ["maps/smallcave.json"]

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

TILE_KEY = {
    '#': TILE_WALL,
    ' ': TILE_EMPTY, # Explicitly open floor
    '.': TILE_EMPTY,
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

