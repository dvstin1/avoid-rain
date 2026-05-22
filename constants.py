"""
Central registry for all game configuration and 'magic numbers'.
"""

# Window Configuration
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Avoid Rain"

# Colors (R, G, B)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (200, 50, 50)
COLOR_YELLOW = (220, 200, 50)
COLOR_BLUE = (50, 50, 200)
COLOR_GREEN = (50, 200, 50)
COLOR_GREY = (100, 100, 100)
COLOR_CYAN = (0, 255, 255)
COLOR_DARK_GREY = (40, 40, 40)

# Player Configuration
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 40
PLAYER_START_X = SCREEN_WIDTH // 2
PLAYER_START_Y = SCREEN_HEIGHT // 2
PLAYER_SPEED = 300.0  # Pixels per second
PLAYER_MAX_HP = 100
FLASK_MAX_CHARGES = 3
FLASK_HEAL_AMOUNT = 40

# Dummy Configuration
DUMMY_WIDTH = 45
DUMMY_HEIGHT = 45
DUMMY_X = SCREEN_WIDTH // 2 + 200
DUMMY_Y = SCREEN_HEIGHT // 2

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

# Grid & World Configuration
TILE_SIZE = 40
# Extra tiles to make the world larger than the visible screen (low-coupling constant)
WORLD_EXTRA_TILES_X = 10
WORLD_EXTRA_TILES_Y = 5
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE + WORLD_EXTRA_TILES_X
GRID_HEIGHT = SCREEN_HEIGHT // TILE_SIZE + WORLD_EXTRA_TILES_Y

# Camera smoothing configuration (how quickly the camera follows the target)
# Higher values = snappier (1.0 means it will take ~1s to reach target)
CAMERA_LERP_SPEED = 8.0

# Autosave configuration
# Interval (seconds) between automatic saves
AUTOSAVE_INTERVAL = 30.0
# How long (seconds) a "Saved" indicator is shown after an autosave
AUTOSAVE_INDICATOR_DURATION = 2.0

# Minimap configuration (pixels)
MINIMAP_WIDTH = 200
MINIMAP_HEIGHT = 150
MINIMAP_PADDING = 8
# Minimap tile marker color
MINIMAP_WALL_COLOR = (120, 120, 120)
MINIMAP_PLAYER_COLOR = (200, 50, 50)
# Fraction of the world shown in the minimap viewport. Values >1 are
# allowed and will result in the minimap showing the full world (clamped).
# A value around 1.2 is useful for showing some context while still
# demonstrating panning in many world sizes.
MINIMAP_VIEWPORT_FRAC = 1.2

# Tile Types
TILE_EMPTY = 0
TILE_WALL = 1
TILE_WARP = 2  # Special tile that warps the player to another map
TILE_RESPITE = 3
TILE_OBSTACLE = 4
TILE_PROP = 5
TILE_LOTUS_FRAME = 6

TILE_KEY = {
    '#': TILE_WALL,
    '.': TILE_EMPTY,
    'W': TILE_WARP,
    'R': TILE_RESPITE,
    'T': TILE_OBSTACLE,
    'B': TILE_PROP,
    'P': 100, # Special marker for player start
    'M': TILE_LOTUS_FRAME,
    'X': TILE_WALL, # X also acts as a wall boundary
}

# Colors for Tiles
COLOR_WALL = (60, 60, 60)
COLOR_FLOOR = (25, 25, 25)

# Structural Schema enforced for all conversation manifests
DIALOGUE_MANIFEST = {
    "chronicler": [
        {
            "id": "chr_key_reaction",
            "conditions": {"has_item_iron_key": True, "boss_night1_encountered": False},
            "priority": "100", # Checked first due to high specificity
            "text": (
                "That key you hold... its edges match the fractures in the first chapter. "
                "Be careful."
            )
        },
        {
            "id": "chr_standard_defeat",
            "conditions": {"last_run_result": "DEFEAT"},
            "priority": "50",
            "text": "You return cold... I can still smell the burning ink."
        },
        {
            "id": "chr_fallback",
            "conditions": {}, # Empty means always valid
            "priority": "0",  # Checked last
            "text": "The pages are waiting whenever you are ready."
        }
    ]
}
