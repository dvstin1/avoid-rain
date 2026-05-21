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

# Player Configuration
PLAYER_WIDTH = 40
PLAYER_HEIGHT = 40
PLAYER_START_X = SCREEN_WIDTH // 2
PLAYER_START_Y = SCREEN_HEIGHT // 2
PLAYER_SPEED = 300.0  # Pixels per second

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
STAGGER_THRESHOLD = 20 # Damage needed to stagger
RECOVERY_TIME = 0.3 # Time spent in stagger/recovery

# Grid & World Configuration
TILE_SIZE = 40
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // TILE_SIZE

# Tile Types
TILE_EMPTY = 0
TILE_WALL = 1

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
            "text": "That key you hold... its edges match the fractures in the first chapter. Be careful."
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
