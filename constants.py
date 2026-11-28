# copyright 2026 Dustin Massop, License: GPLv2
"""
Central registry for all game configuration and 'magic numbers'.
"""

import functools
import math
import tempfile
from pathlib import Path
import pygame

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
TEST_LAN_PORT_BASE = 51000

# Input Modes
INPUT_MODE_KEYBOARD = "KEYBOARD"
INPUT_MODE_GAMEPAD = "GAMEPAD"

# Selection & UI Colors
COLOR_SELECTION = (120, 255, 100) # Toxic Green
COLOR_MODE_KEYBOARD = (220, 220, 220)
COLOR_MODE_GAMEPAD = COLOR_SELECTION

# Gamepad Configuration
JOYSTICK_DEADZONE = 0.2

# Default Remappable Keyboard Bindings & Display Labels (Batch 7)
# pylint: disable=no-member
DEFAULT_KEYBINDINGS = {
    "move_up": pygame.K_w,
    "move_down": pygame.K_s,
    "move_left": pygame.K_a,
    "move_right": pygame.K_d,
    "attack": pygame.K_SPACE,
    "block": pygame.K_k,
    "dash": pygame.K_LSHIFT,
    "flask": pygame.K_1,
    "swap": pygame.K_q,
    "inspect": pygame.K_TAB,
    "respite_rest": pygame.K_r,
}
# pylint: enable=no-member

KEYBINDING_ACTION_LABELS = {
    "move_up": "Move Up",
    "move_down": "Move Down",
    "move_left": "Move Left",
    "move_right": "Move Right",
    "attack": "Attack / Interact",
    "block": "Block (Shield)",
    "dash": "Dash (Invulnerable)",
    "flask": "Heal (Flask)",
    "swap": "Swap Weapon",
    "inspect": "Inspect Details",
    "respite_rest": "Respite Rest",
}

KEYBINDING_GAMEPAD_LABELS = {
    "move_up": "(GP) L-Stick Up",
    "move_down": "(GP) L-Stick Down",
    "move_left": "(GP) L-Stick Left",
    "move_right": "(GP) L-Stick Right",
    "attack": "(GP) Cross / Square",
    "block": "(GP) R2",
    "dash": "(GP) Circle",
    "flask": "(GP) Triangle",
    "swap": "(GP) L1",
    "inspect": "(GP) R1",
    "respite_rest": "(GP) Circle (Menu)",
}

_SHORT_KEY_NAMES = {
    "left shift": "LSHIFT",
    "right shift": "RSHIFT",
    "left ctrl": "LCTRL",
    "right ctrl": "RCTRL",
    "left alt": "LALT",
    "right alt": "RALT",
    "left meta": "LMETA",
    "right meta": "RMETA",
    "space": "SPACE",
    "tab": "TAB",
    "return": "ENTER",
    "keypad enter": "KP_ENTER",
    "escape": "ESC",
    "backspace": "BKSP",
    "caps lock": "CAPSLOCK",
}


def format_key_name(key_code: int) -> str:
    """Return a concise uppercase display name for a pygame key code (e.g. 'SPACE', 'LSHIFT', 'TAB')."""
    try:
        code = int(key_code)
    except (TypeError, ValueError):
        return "?"
    try:
        raw = str(pygame.key.name(code) or "").strip()
    except Exception:
        raw = ""
    if not raw or raw == "unknown key":
        return f"KEY_{code}"
    low = raw.lower()
    if low in _SHORT_KEY_NAMES:
        return _SHORT_KEY_NAMES[low]
    return raw.upper().replace(" ", "_")


def normalize_keybindings(raw) -> dict:
    """Return a complete action -> key_code dict hydrated from DEFAULT_KEYBINDINGS."""
    bindings = dict(DEFAULT_KEYBINDINGS)
    if not isinstance(raw, dict):
        return bindings
    # pylint: disable=no-member
    esc_code = pygame.K_ESCAPE
    # pylint: enable=no-member
    for action, default_code in DEFAULT_KEYBINDINGS.items():
        val = raw.get(action, default_code)
        if isinstance(val, int) and not isinstance(val, bool) and val > 0 and val != esc_code:
            bindings[action] = val
    return bindings

# Colors (R, G, B)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (200, 50, 50)
COLOR_YELLOW = (220, 200, 50) # Legacy support
COLOR_BLUE = (50, 50, 200)
COLOR_GREEN = (50, 200, 50)
COLOR_GREY = (100, 100, 100)
COLOR_CYAN = (0, 255, 255)
COLOR_MAGENTA = (255, 0, 255)
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
WARD_BUFF_RAIN_REDUCTION = 0.30
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
SLUG_ATTACK_HITBOX_SIZE = 38.0  # 38x38 forward bite/contact hitbox during STRIKE
SLUG_ATTACK_HITBOX_OFFSET = 10.0  # Forward shift toward target/facing direction
STAGGER_THRESHOLD = 20 # Damage needed to stagger
RECOVERY_TIME = 0.3 # Time spent in stagger/recovery

# Swamp Biome Night Boss (SlugBoss) configuration
SLUG_BOSS_SIZE = 112  # 3.5x regular 32x32 slug
SLUG_BOSS_CROWN_WIDTH = 44
SLUG_BOSS_CROWN_HEIGHT = 32
SLUG_BOSS_SPEED = 95.0
SLUG_BOSS_CHARGE_SPEED_MULTIPLIER = 2.6
SLUG_BOSS_CHARGE_HITBOX_OFFSET = 26.0
SLUG_BOSS_CHARGE_HITBOX_SIZE = 92.0
SLUG_BOSS_SLIME_POOL_DURATION = 4.5
SLUG_BOSS_SLIME_POOL_RADIUS = 44.0
SLUG_BOSS_SLIME_POOL_DAMAGE = 8.0
SLUG_BOSS_SLIME_POOL_TICK_INTERVAL = 0.55
SLUG_BOSS_SLIME_POOL_COUNT = 3
SLUG_BOSS_SLIME_SFX = "slug_boss_slime.ogg"
SLUG_BOSS_PHASE2_HP_RATIO = 0.5
SLUG_BOSS_MINION_COUNT = 10
SLUG_BOSS_PHASE1_MUSIC = "slug_boss_phase1.ogg"
SLUG_BOSS_PHASE2_MUSIC = "slug_boss_phase2.ogg"

# Pastoral Valley Night Boss (MeadowCensorBoss — The Meadow Censor) configuration
MEADOW_CENSOR_SIZE = 104
MEADOW_CENSOR_SCYTHE_WIDTH = 48
MEADOW_CENSOR_SCYTHE_HEIGHT = 56
MEADOW_CENSOR_HP = 680.0
MEADOW_CENSOR_SPEED = 112.0
MEADOW_CENSOR_PULL_DISTANCE = 96.0
MEADOW_CENSOR_TAR_POOL_COUNT = 3
MEADOW_CENSOR_PHASE2_HP_RATIO = 0.5
MEADOW_CENSOR_MINION_COUNT = 4
MEADOW_CENSOR_WHISTLE_SFX = "meadow_censor_whistle.ogg"
MEADOW_CENSOR_PHASE1_MUSIC = "pastoral_boss_phase1.ogg"
MEADOW_CENSOR_PHASE2_MUSIC = "pastoral_boss_phase2.ogg"

# Frozen Peaks Frost Encasement & Night Boss (RimecrestArbiterBoss — The Rimecrest Arbiter) configuration
FROZEN_ICE_BLOCK_HITS = 3
FROZEN_EXPOSURE_DECAY_RATE = 0.45
ICE_RUBBLE_DURATION = 5.0
FROST_BREATH_SFX = "frost_breath.ogg"
ICE_CRACK_SFX = "ice_crack.ogg"
ICE_SHATTER_SFX = "ice_shatter.ogg"
RIMECREST_ARBITER_SIZE = 104
RIMECREST_ARBITER_HALBERD_WIDTH = 48
RIMECREST_ARBITER_HALBERD_HEIGHT = 56
RIMECREST_ARBITER_HP = 720.0
RIMECREST_ARBITER_SPEED = 108.0
RIMECREST_ARBITER_BREATH_RANGE = 195.0
RIMECREST_ARBITER_BREATH_HALF_ANGLE = 0.58
RIMECREST_FREEZE_WINDOW = 10.0
RIMECREST_CHILL_HIT_AMOUNT = 0.5
RIMECREST_ARBITER_EXPOSURE_RATE = 0.85
RIMECREST_ARBITER_BREATH_DPS = 12.0
RIMECREST_ARBITER_HALBERD_EXPOSURE = RIMECREST_CHILL_HIT_AMOUNT
RIMECREST_ARBITER_PHASE2_HP_RATIO = 0.5
RIMECREST_ARBITER_MINION_COUNT = 3
RIMECREST_ARBITER_PHASE1_MUSIC = "frozen_boss_phase1.ogg"
RIMECREST_ARBITER_PHASE2_MUSIC = "frozen_boss_phase2.ogg"

# Windy Ridge Night Boss (The Gale-Vane Raptor) Constants
GALE_RAPTOR_SIZE = 108
GALE_RAPTOR_SPEED = 116.0
GALE_RAPTOR_STRAFE_SPEED = 92.0
GALE_RAPTOR_DASH_SPEED = 360.0
GALE_RAPTOR_DASH_DURATION = 0.34
GALE_RAPTOR_DASH_DAMAGE = 26.0
GALE_RAPTOR_TELEGRAPH_DURATION = 0.55
GALE_RAPTOR_STALL_DURATION = 1.45
GALE_RAPTOR_STALL_STUN_DURATION = 0.35
GALE_RAPTOR_GUARD_DURATION = 3.2
GALE_RAPTOR_VOLLEY_INTERVAL = 1.35
GALE_RAPTOR_PHASE2_HP_RATIO = 0.50
GALE_RAPTOR_ARMOR_DAMAGE_MULT = 0.25
GALE_RAPTOR_WEAKPOINT_DAMAGE_MULT = 2.25
GALE_RAPTOR_BOLT_COUNT_P1 = 3
GALE_RAPTOR_BOLT_COUNT_P2 = 5
GALE_RAPTOR_BOLT_SPREAD_DEG = 16.0
GALE_RAPTOR_DASH_COUNT_P1 = 2
GALE_RAPTOR_DASH_COUNT_P2 = 3
GALE_RAPTOR_TRAIL_LIFE = 0.55
GALE_RAPTOR_MUSIC = "boss_gale_raptor.ogg"

# Tech Tower Night Boss (The Typesetter Automaton) Constants
TYPESETTER_SIZE = 112
TYPESETTER_SPEED = 96.0
TYPESETTER_MARCH_DURATION = 3.4
TYPESETTER_SLUG_INTERVAL = 1.15
TYPESETTER_SLUG_COUNT_P1 = 3
TYPESETTER_SLUG_COUNT_P2 = 5
TYPESETTER_SLUG_SPREAD_DEG = 18.0
TYPESETTER_STAMP_COUNT = 3
TYPESETTER_STAMP_LIFT_DURATION_P1 = 0.56
TYPESETTER_STAMP_LIFT_DURATION_P2 = 0.42
TYPESETTER_STAMP_IMPACT_HOLD_P1 = 0.28
TYPESETTER_STAMP_IMPACT_HOLD_P2 = 0.22
TYPESETTER_STAMP_RING_RADIUS_P1 = 155.0
TYPESETTER_STAMP_RING_RADIUS_P2 = 205.0
TYPESETTER_STAMP_RING_DURATION = 0.52
TYPESETTER_STAMP_RING_BAND = 24.0
TYPESETTER_STAMP_RING_DAMAGE = 24.0
TYPESETTER_STAMP_RADIAL_BOLTS_P1 = 6
TYPESETTER_STAMP_RADIAL_BOLTS_P2 = 8
TYPESETTER_BOILER_VENT_DURATION = 1.50
TYPESETTER_VENT_STUN_DURATION = 0.40
TYPESETTER_PHASE2_HP_RATIO = 0.50
TYPESETTER_ARMOR_DAMAGE_MULT = 0.25
TYPESETTER_WEAKPOINT_DAMAGE_MULT = 2.5
TYPESETTER_PLATEN_LIFT_OFFSET = -26.0
TYPESETTER_PLATEN_SLAM_OFFSET = 14.0
TYPESETTER_STEAM_SPARK_LIFE = 0.55
TYPESETTER_MUSIC = "boss_typesetter.ogg"

# The Vitreous Basin Night Boss (The Glass-Kiln Basilisk) Constants
GLASS_BASILISK_SIZE = 112
GLASS_BASILISK_SPEED = 118.0
GLASS_BASILISK_SLITHER_DURATION = 3.5
GLASS_BASILISK_SLITHER_SWAY_RATE = 4.6
GLASS_BASILISK_SLITHER_LATERAL_WEIGHT = 0.65
GLASS_BASILISK_VOLLEY_INTERVAL = 1.18
GLASS_BASILISK_BOLT_COUNT_P1 = 3
GLASS_BASILISK_BOLT_COUNT_P2 = 5
GLASS_BASILISK_BOLT_SPREAD_DEG = 18.0
GLASS_BASILISK_REFRACTION_CHARGE_P1 = 0.68
GLASS_BASILISK_REFRACTION_CHARGE_P2 = 0.50
GLASS_BASILISK_REFRACTION_SWEEP_P1 = 1.55
GLASS_BASILISK_REFRACTION_SWEEP_P2 = 1.35
GLASS_BASILISK_BEAM_RANGE = 420.0
GLASS_BASILISK_BEAM_HALF_WIDTH = 22.0
GLASS_BASILISK_BEAM_SWEEP_ARC_RAD = 1.65
GLASS_BASILISK_BEAM_FAN_COUNT_P1 = 1
GLASS_BASILISK_BEAM_FAN_COUNT_P2 = 3
GLASS_BASILISK_BEAM_FAN_SPREAD_RAD = 0.42
GLASS_BASILISK_BEAM_DAMAGE = 22.0
GLASS_BASILISK_BEAM_HIT_COOLDOWN = 0.45
GLASS_BASILISK_KILN_CRACK_DURATION = 1.55
GLASS_BASILISK_CRACK_STUN_DURATION = 0.42
GLASS_BASILISK_PHASE2_HP_RATIO = 0.50
GLASS_BASILISK_ARMOR_DAMAGE_MULT = 0.25
GLASS_BASILISK_WEAKPOINT_DAMAGE_MULT = 2.5
GLASS_BASILISK_SPARK_LIFE = 0.55
GLASS_BASILISK_MUSIC = "boss_glass_basilisk.ogg"

# Fast-pursuit Bat enemy configuration
BAT_MAX_HP = 35
BAT_SPEED = 150.0  # pixels per second (fast pursuit)
BAT_DETECT_METERS = 7  # detection radius
BAT_DAMAGE = 5  # damage dealt on contact
BAT_DAMAGE_COOLDOWN = 0.5  # seconds between contact damage attempts
BAT_SINE_AMPLITUDE = 0.35  # Lateral sine wave ratio relative to forward pursuit speed
BAT_SWOOP_SPEED_MULTIPLIER = 2.4  # Forward lunge speed multiplier during STRIKE
BAT_SWOOP_HITBOX_SIZE = 28.0  # 28x28 tight swoop attack hitbox
BAT_SWOOP_HITBOX_OFFSET = 12.0  # Forward shift of the 28x28 hitbox along swoop vector

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
SMEAR_TRAIL_PUDDLE_LIFETIME = 10.0 # Seconds before SmearEnemy walking puddles fade away
SMEAR_TRAIL_FADE_DURATION = 2.5    # Final seconds over which SmearEnemy walking puddles smoothly fade out

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
WELLSPRING_NIGHT_BOSS_FLASK_GRANT = 1

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
SANCTUARY_DOOR_PROXIMITY_TILES = 1.2
SANCTUARY_DOOR_OPEN_SFX = "door_open.ogg"
SANCTUARY_CANDLE_GLOW_BASE_RADIUS = 32
SANCTUARY_CANDLE_GLOW_RADIUS_AMP = 5
SANCTUARY_CANDLE_GLOW_BASE_ALPHA = 68
SANCTUARY_CANDLE_GLOW_ALPHA_AMP = 22
SANCTUARY_FIREFLY_COUNT = 9
SANCTUARY_POND_RIPPLE_MAX_RADIUS = 16
SANCTUARY_POND_SPEED_MULTIPLIER = 0.40
AQUEDUCT_WATER_SPEED_MULTIPLIER = 0.65
WATER_STEP_SFX = "water_step.ogg"
WATER_STEP_INTERVAL = 0.34
PLAYER_HURT_SFX = "player_hurt.ogg"
FLASK_EMPTY_SFX = "flask_empty.ogg"
INTERACTABLE_HOSTILE_LOCK_RADIUS = 180.0
UNBLOTTED_MARGIN_MITIGATION_BONUS = 0.05
BINDER_PATROL_SPEED_MULTIPLIER = 0.35


@functools.lru_cache(maxsize=65536)
def raw_stratum_at(x: int, y: int) -> int:
    """Evaluate the deterministic multi-tile terrain stratum wave (0, 1, or 2) at tile (x, y)."""
    wave = (
        math.sin(x * 0.21 + y * 0.16)
        + math.cos(x * 0.14 - y * 0.23)
        + 0.55 * math.sin((x + y) * 0.09)
        + 0.35 * math.cos((x - y) * 0.12)
    )
    if wave < -0.68:
        return 0
    if wave > 0.68:
        return 2
    return 1


def get_tile_stratum(x: int, y: int) -> int:
    """Compute coherent multi-tile terrain stratum with 1x1 island suppression at tile (x, y)."""
    s_here = raw_stratum_at(x, y)
    if s_here == 1:
        return 1
    same_neighbors = (
        (1 if raw_stratum_at(x - 1, y) == s_here else 0)
        + (1 if raw_stratum_at(x + 1, y) == s_here else 0)
        + (1 if raw_stratum_at(x, y - 1) == s_here else 0)
        + (1 if raw_stratum_at(x, y + 1) == s_here else 0)
    )
    return s_here if same_neighbors >= 2 else 1

# UI Overlay Constants (Batch 8: Tall Compact Visual HUD Card)
UI_ALPHA = 175
HUD_PANEL_W = 252
HUD_PANEL_H = 148
HUD_SLOT_W = 114
HUD_SLOT_H = 58
HUD_SWAP_BTN_W = 114
HUD_SWAP_BTN_H = 58
HUD_PICKUP_BTN_W = 236
HUD_PICKUP_BTN_H = 22
# SLOT B doubles as the clickable swap card; contextual pickup pill floats cleanly above the HUD card
HUD_SWAP_BTN_RECT = (130, 58, HUD_SWAP_BTN_W, HUD_SWAP_BTN_H)
HUD_PICKUP_BTN_RECT = (8, -26, HUD_PICKUP_BTN_W, HUD_PICKUP_BTN_H)

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
        "floor_base": (196, 146, 86),
        "floor_alt": (214, 166, 102),
        "floor_accent": (236, 194, 124),
        "floor_speck": (255, 224, 148),
        "strata": [
            ((154, 88, 52), (182, 108, 62)),
            ((196, 146, 86), (214, 166, 102)),
            ((224, 178, 114), (240, 198, 134))
        ],
        "wall_top": (182, 112, 66),
        "wall_hi": (244, 196, 128),
        "wall_face": (132, 74, 44),
        "wall_mortar": (64, 34, 22),
        "wall_glow": (255, 148, 42)
    },
    "sunlit_aqueducts": {
        "floor_base": (168, 108, 72),
        "floor_alt": (192, 128, 88),
        "floor_accent": (88, 178, 96),
        "floor_speck": (235, 204, 148),
        "strata": [
            ((36, 104, 122), (50, 124, 142)),
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

# Sunlit Aqueducts Continuous Channel Water & Atmosphere (Section 20)
AQUEDUCT_WATER_BASE_COLOR = (36, 104, 122)
AQUEDUCT_WATER_SHIMMER_HI = (108, 194, 208)
AQUEDUCT_WATER_SHIMMER_LO = (58, 138, 156)
AQUEDUCT_TROUGH_RIM_PX = 3
AQUEDUCT_TROUGH_RIM_NORTH = (118, 86, 62)       # Shaded wet-stone/terracotta upper trough lip
AQUEDUCT_TROUGH_RIM_SOUTH = (152, 114, 82)      # Sunlit carved terracotta lower trough lip
AQUEDUCT_TROUGH_RIM_SIDE = (134, 98, 70)        # Carved wet terracotta E/W trough lip
AQUEDUCT_TROUGH_WATERLINE = (24, 78, 96)        # 1px recessed waterline undercut along N/W edge
AQUEDUCT_RIPPLE_COLOR = (164, 224, 234)         # Soft ambient water ripple ring tint
AQUEDUCT_RIPPLE_MAX_RADIUS = 13.0
AQUEDUCT_RIPPLE_MAX_COUNT = 8
AQUEDUCT_CURRENT_STREAK_COUNT = 10
AQUEDUCT_SUNLIT_MOTE_COUNT = 14
AQUEDUCT_MOTE_HALO_COLOR = (255, 226, 148)
AQUEDUCT_MOTE_CORE_COLOR = (255, 248, 214)

# Flat Walkable Floor-Zone Transition Seam Constants
# Keeps flat floor-to-floor boundaries softer than wall/cliff edges across all biomes.
FLOOR_SEAM_OUTER_BLEND = 0.50         # Weight of surrounding canvas stratum on outer 1px seam rim
FLOOR_SEAM_INNER_BLEND = 0.25         # Weight of surrounding canvas stratum on inner 1px feather lip
FLOOR_SEAM_SHADE_FACTOR = 0.90        # Subtle darkening on shaded seam side (vs dark wall_mortar)
FLOOR_SEAM_RECESS_LO_FACTOR = 0.92    # Subtle softening on recessed stratum south/east edge
FLOOR_SEAM_HIGHLIGHT_FACTOR = 1.05    # Subtle lift on lit terrace seam side (vs stark wall_hi)
FLOOR_SEAM_RIM_PX = 1                 # 1px primary floor seam rim (vs 2-4px wall/cliff borders)
FLOOR_SEAM_FEATHER_PX = 1             # 1px inner feather blend (vs 3px cliff lip)
FLOOR_SEAM_CORNER_RADIUS = 8          # Organic 45-degree outer corner bevel radius for flat zones
FLOOR_SEAM_TECH_CORNER_RADIUS = 6     # Clean 45-degree chamfer radius for tech_tower decks
FLOOR_SEAM_TECH_CHAMFER_BLEND = 0.22  # Subtle muted accent blend for tech_tower deck chamfers


def blend_rgb(col_a, col_b, weight_b: float) -> tuple:
    """Linearly interpolate between two RGB tuples by weight_b clamped to [0.0, 1.0]."""
    t = max(0.0, min(1.0, float(weight_b)))
    return (
        max(0, min(255, int(round(col_a[0] * (1.0 - t) + col_b[0] * t)))),
        max(0, min(255, int(round(col_a[1] * (1.0 - t) + col_b[1] * t)))),
        max(0, min(255, int(round(col_a[2] * (1.0 - t) + col_b[2] * t)))),
    )


def scale_rgb(col, factor: float) -> tuple:
    """Scale an RGB tuple by factor and clamp each channel to [0, 255]."""
    return (
        max(0, min(255, int(round(col[0] * factor)))),
        max(0, min(255, int(round(col[1] * factor)))),
        max(0, min(255, int(round(col[2] * factor)))),
    )


def compute_floor_seam_colors(biome: str, pal: dict, s_idx: int) -> dict:
    """Compute low-contrast flat floor-to-floor seam colors for a biome stratum (0 or 2).

    Blends the stratum base color with the surrounding canvas stratum (1) so walkable zone
    transitions read as flat ground rather than cliff edges or elevation drop-offs.
    """
    strata_defs = pal.get("strata", [(pal["floor_base"], pal["floor_alt"])] * 3)
    s_base = strata_defs[s_idx][0]
    outer_canvas = strata_defs[1][0]
    mid = blend_rgb(s_base, outer_canvas, FLOOR_SEAM_OUTER_BLEND)
    inner_lip = blend_rgb(s_base, outer_canvas, FLOOR_SEAM_INNER_BLEND)

    if s_idx == 0:
        rim_hi = scale_rgb(mid, FLOOR_SEAM_SHADE_FACTOR)
        rim_lo = scale_rgb(mid, FLOOR_SEAM_RECESS_LO_FACTOR)
    else:
        rim_hi = scale_rgb(mid, FLOOR_SEAM_HIGHLIGHT_FACTOR)
        rim_lo = scale_rgb(mid, FLOOR_SEAM_SHADE_FACTOR)

    result = {
        "outer_canvas": outer_canvas,
        "rim_hi": rim_hi,
        "rim_lo": rim_lo,
        "inner_lip": inner_lip,
    }

    if biome == "swamp_mire":
        if s_idx == 0:
            result["inner_lip"] = blend_rgb(inner_lip, (64, 84, 38), 0.45)
            result["dab_col"] = blend_rgb(mid, (88, 114, 42), 0.45)
        else:
            result["inner_lip"] = blend_rgb(inner_lip, (88, 52, 92), 0.40)
            result["dab_col"] = blend_rgb(s_base, (108, 74, 114), 0.45)
    elif biome == "tech_tower":
        chamfer_target = (62, 96, 118) if s_idx == 0 else (76, 100, 128)
        result["chamfer_hi"] = blend_rgb(inner_lip, chamfer_target, FLOOR_SEAM_TECH_CHAMFER_BLEND)

    return result

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
            "id": "chr_defeat_unbound_folio",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "unbound_folio"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "An Unbound Folio tore loose from its stitching and overwhelmed you in the ring... "
                "When a signature unravels that violently, Reader, thin the swarm before the waves close in."
            ),
        },
        {
            "id": "chr_defeat_running_errata",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "running_errata"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "You fell chasing the Running Errata across the margin. That wayward wisp draws every ambush "
                "glyph in the chapter—clear its interceptors first before marching alongside it."
            ),
        },
        {
            "id": "chr_defeat_censored_passage",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "censored_passage"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "The black mist of a Censored Passage choked your quill before the glyph-ward could clear. "
                "Hold the anchor's circle steadily next time, and do not let the defenders crowd the blot."
            ),
        },
        {
            "id": "chr_defeat_palimpsest_duel",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "palimpsest_duel"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "Struck down inside a Palimpsest Duel... The Overwritten Champion remembers every cadence "
                "of an older draft. Read its wind-up carefully and parry before trading blows in that ring."
            ),
        },
        {
            "id": "chr_defeat_margin_toll",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "margin_toll"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "The Margin Toll claimed more than Torn Pages from you today. Shatter those resonant "
                "ink-seals quickly when the bell tolls, Reader, or their wards will bleed you dry."
            ),
        },
        {
            "id": "chr_defeat_barrel_mimic_cluster",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "barrel_mimic_cluster"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "Ambushed by a Barrel Mimic Cluster! False ink-casks love to nest in quiet corners of the "
                "draft—test suspicious props from a safe reach before waking the whole cache."
            ),
        },
        {
            "id": "chr_defeat_sunken_margin",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "sunken_margin"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "The floor gave way into a Sunken Margin cellar, and the deep-ink lurkers dragged you under. "
                "Keep your footing moving in that cramped vault until the exit ladder drops."
            ),
        },
        {
            "id": "chr_defeat_relentless_censor",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "relentless_censor"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "I felt the Relentless Censor's redaction blade from here... When that hunter marks your scent "
                "across the page, either break its posture early or use every wall to outlast the hunt."
            ),
        },
        {
            "id": "chr_defeat_unblotted_margin",
            "conditions": {"last_run_result": "DEFEAT", "last_death_event": "unblotted_margin"},
            "priority": "110",
            "emotion": "disappointed",
            "text": (
                "Even with the grace of an Unblotted Margin refreshing your ink, the draft still claimed you. "
                "A rare sanctuary breath in the wild is precious, Reader—spend that vigor wisely."
            ),
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
        ),
        "ink_unsealing_rite": (
            "The Ink-Unsealing Rite: When a redacted Sovereign or Censor forces its way back "
            "from the Margin, a grey vellum colophon circle burns into the floor and fills "
            "outward from its center with pitch-black gall-ink. Hundreds of rising typographic "
            "ash-squares—each stamped with a grey letter torn from an erased manuscript—lift "
            "like Reverse Rain before the seal snaps shut and the terror takes physical form."
        ),
        "windy_ridge_chronicle": [
            (
                "High above the Scriptorium eaves, the Windy Ridge was where fresh vellum sheets "
                "were hung to cure before the Bleed poisoned the sky. Now gale-force drafts tear "
                "loose stanzas from the cliff anchors and hurl them into the acid storm."
            ),
            (
                "The Gale-Warden Scribe still patrols the highest ridge lectern, its heavy iron nib "
                "pinning fluttering folios to the crags. Those who challenge its perch must watch "
                "for its sweeping downstroke when the wind shifts."
            ),
            (
                "We built stone windbreaks along the ridge margin to shield the courier monks from "
                "the green rain, yet the ink-laden gusts seep through every mortar crack."
            ),
            (
                "When the First Folio split open, the updrafts carried burning punctuation marks "
                "into the cliffside rookeries. The bats nested in those charred margins and drank the soot."
            ),
            (
                "An Editor's note pinned beneath a cairn: 'Stay inside the chalk ring when the barometer "
                "drops. On the ridge, the rain does not fall—it hunts horizontally.'"
            ),
            "The text has faded into illegibility.",
        ],
        "swamp_mire_chronicle": [
            (
                "The Swamp Mire formed where discarded drafts and spoiled gall-ink barrels were "
                "dumped below the Scriptorium sluices. Over centuries of the Bleed, the fermented "
                "peat quickened into a breathing, venomous bog."
            ),
            (
                "At the mire's drowned heart slithers the Slug Night Boss—an ancient royal colophon "
                "beast wearing a tarnished brass crown, its mantle still pierced through by the shattered "
                "sword of the first Editor who tried to redact it."
            ),
            (
                "Even impaled by that ancestral blade, the crowned Slug Night Boss drags the steel "
                "through the mire like a scepter, summoning toxic rain-squalls whenever the margin circle "
                "closes around its throne of peat."
            ),
            (
                "Spore-pods along the mire causeways swell with acidic green rainwater. Step lightly "
                "near the ink puddles; the Smears here split and multiply in the damp."
            ),
            (
                "Field report from the Third Binding: 'Do not try to pull the sword from the crowned "
                "Slug's back mid-swing. Strike when it wrenches the buried blade free of the mud.'"
            ),
            "The text has faded into illegibility.",
        ],
        "pastoral_valley_chronicle": [
            (
                "The Pastoral Valley was drafted as a gentle opening chapter—sun-warmed meadow grass "
                "and quiet shepherd stanzas. When the Author's fever broke the spine, boiling black "
                "tar-ink erupted through the sod."
            ),
            (
                "Packs of Punctuation Wolves now stalk the scarred meadow borders, their jagged comma-claws "
                "and dash-fangs herding stray Readers toward the tar sinks before the rain arrives."
            ),
            (
                "The Meadow Censor stands sentinel over the sunken threshing circle, wielding a hooked "
                "redaction scythe that reaps entire paragraphs of tall grass in a single arc."
            ),
            (
                "Beneath the wildflowers, you can still trace the ruled ledger lines of the original "
                "parchment before the green rain bleached the valley's color into ash."
            ),
            (
                "A shepherd's margin gloss: 'When the wolves howl in unison, they are not calling to "
                "the moon—they are marking the boundary of the shrinking safe circle.'"
            ),
            "The text has faded into illegibility.",
        ],
        "frozen_peaks_chronicle": [
            (
                "In desperation to halt the spreading Bleed, the Senior Archivists climbed to the "
                "Frozen Peaks and invoked a rime-seal to flash-freeze the boiling ink in mid-sentence."
            ),
            (
                "The Rimecrest Arbiter guards the glacier pass, encased in mirror-ice armor that "
                "reflects stray quill strikes while its frost-bound halberd shatters brittle footing."
            ),
            (
                "Look closely into the glacier walls: whole columns of panicked script are suspended "
                "inside the blue ice, waiting for a single drop of warm toxic rain to thaw their rage."
            ),
            (
                "Even at this altitude, the green storm clouds boil overhead. When the Bleed rain "
                "strikes the rime slate, it hisses into blinding ink-steam."
            ),
            (
                "Expedition tally carved into frozen vellum: 'Four Scholars ascended the pass. Only "
                "one returned to the Wellspring, his quill nib fused solid with black frost.'"
            ),
            "The text has faded into illegibility.",
        ],
        "tech_tower_chronicle": [
            (
                "The Tech Tower—called the Sky Citadel in the late appendices—was an experimental "
                "typesetting engine built from brushed titanium and copper data-buses to automate "
                "the Libram's index."
            ),
            (
                "When the Bleed infiltrated the tower's logic conduits, the Techno-Sentries locked "
                "into eternal purge mode, sweeping the gantry bridges with scorching plasma beams."
            ),
            (
                "At the spire's crown presides the Architect-Censor, a clockwork inquisitor that "
                "compiles corrupted syntax into lethal shockwaves whenever a Reader breaches the main bus."
            ),
            (
                "Acid rain rattles against the titanium skylight plates, short-circuiting the relay "
                "pillars and showering the lower script-decks in amber sparks."
            ),
            (
                "Maintenance log #404: 'The machine no longer distinguishes between errata and the "
                "Reader. Keep moving across the gantries or the Sentries will triangulate your line.'"
            ),
            "The text has faded into illegibility.",
        ],
        "vitreous_basin_chronicle": [
            (
                "The Vitreous Basin was born when a furnace-draft of white-hot eradication fire "
                "collided with a salt-ink reservoir, fusing the chapter floor into fractured glass "
                "flats and jagged salt spires."
            ),
            (
                "Every step across the refractive basin floor echoes twice. The Vitreous Cantor—the "
                "basin's towering crystalline boss—uses those reflections to blind Readers before "
                "driving its glass lance through the salt crust."
            ),
            (
                "When the toxic Bleed rain pelts the glass flats, the droplets prism into sickly "
                "emerald beams that betray anything hiding behind the salt pillars."
            ),
            (
                "Bindlings cluster around the warm vitrified fissures, drawing dissolved mineral ink "
                "from the glass seams to mend their torn ribbon-limbs."
            ),
            (
                "Scratched onto a shard of obsidian vellum: 'Use the salt spires to break the Cantor's "
                "line of sight, but never linger—its heavy thrust splinters cover into shrapnel.'"
            ),
            "The text has faded into illegibility.",
        ],
        "sunlit_aqueducts_chronicle": [
            (
                "The Sunlit Aqueducts once carried pure, unblemished artesian water from the Sanctuary's "
                "Wellspring out to every distant chapter of the Libram along elevated terracotta channels."
            ),
            (
                "After the Author's madness cracked the main viaduct arches, the channels ran dry of "
                "Wellspring water and filled instead with creeping moss and stagnant green rainwater."
            ),
            (
                "The Viaduct Warden still marches along the central keystone bridge, an armored "
                "construct sworn to keep the poisoned sluice-gates sealed against intruders and ink-beasts alike."
            ),
            (
                "Shafts of pale sunlight pierce the broken arches between storm squalls, illuminating "
                "floating dust motes and ancient Mason-Editor marks carved into the terracotta brick."
            ),
            (
                "Water-warden's final inscription: 'If the aqueducts ever reconnect to the Wellspring "
                "while the Bleed rages, the Sanctuary itself will drown. Guard the sluice at all costs.'"
            ),
            "The text has faded into illegibility.",
        ],
    }
}

# Sound attenuation constants
SFX_FULL_VOLUME_DIST = 120.0  # 3 units (3 * TILE_SIZE)
SFX_MIN_VOLUME_DIST = 1280.0  # Across the screen
SFX_MIN_VOLUME = 0.05
SFX_VOLUME_SCALE = {
    "player_dash.ogg": 0.45,
}
DEATH_SCREEN_DURATION = 5.5  # Full playback duration covering 5.38s death_theme.ogg

# Dynamic Rain Ambient Audio Constants
RAIN_LOOP_SFX = "rain_loop.ogg"

# Environment Audio (Section 2: Directional Stereo Ambient Loops)
AMBIENT_FLAME_SFX = "ambient_flame.ogg"
AMBIENT_WATER_SFX = "ambient_water.ogg"
AMBIENT_AUTHOR_RUMBLE_SFX = "ambient_author_rumble.ogg"

ENV_AUDIO_SLOTS = ("flame", "water", "author_rumble")
ENV_AUDIO_MAX_CHANNELS = len(ENV_AUDIO_SLOTS)   # Reserved channel budget (never starves combat SFX)
ENV_AUDIO_PAN_RANGE = 420.0                     # Horizontal distance (px) reaching full stereo pan bias
ENV_AUDIO_MAX_PAN_BIAS = 0.85                   # Keeps opposite ear subtly audible at full horizontal offset
ENV_AUDIO_FLAME_MAX_DIST = 420.0                # Audible radius for Candelabras & Vitreous Fire Chalices
ENV_AUDIO_FLAME_FULL_DIST = 72.0
ENV_AUDIO_FLAME_BASE_VOL = 0.34
ENV_AUDIO_CHALICE_VOL_MULT = 1.25               # Larger 80x80 Vitreous Fire Chalices burn slightly louder
ENV_AUDIO_WATER_MAX_DIST = 460.0                # Audible radius for Wellsprings, Sanctuary pond, & Aqueduct channels
ENV_AUDIO_WATER_FULL_DIST = 80.0
ENV_AUDIO_WATER_BASE_VOL = 0.30
ENV_AUDIO_RUMBLE_MAX_DIST = 2600.0              # Subterranean Author madness rumble range toward boss/storm center
ENV_AUDIO_RUMBLE_FULL_DIST = 320.0
ENV_AUDIO_RUMBLE_BASE_VOL = 0.38
ENV_AUDIO_RUMBLE_MIN_LATE_STORM = 0.35          # Swell floor during late contraction / BOSS_PHASE / FinalAuthor
ENV_AUDIO_FADE_RATE = 4.5                       # Smooth dt-scaled per-second volume/pan ramp rate
ENV_AUDIO_STOP_EPSILON = 0.005                  # Threshold below which ambient channels stop cleanly


def compute_stereo_volumes(
    dx: float,
    dy: float,
    max_dist: float,
    full_dist: float = SFX_FULL_VOLUME_DIST,
    base_volume: float = 1.0,
    pan_range: float = ENV_AUDIO_PAN_RANGE,
    max_pan_bias: float = ENV_AUDIO_MAX_PAN_BIAS,
    min_attenuation: float = 0.0,
) -> tuple:
    """Compute directional stereo (left, right) gains in [0.0, 1.0] from relative source offset (dx, dy)."""
    vol = max(0.0, min(1.0, float(base_volume)))
    if vol <= 0.0 or max_dist <= 0.0:
        return (0.0, 0.0)

    dist = math.hypot(float(dx), float(dy))
    if dist <= full_dist:
        atten = 1.0
    elif dist >= max_dist:
        atten = max(0.0, min(1.0, float(min_attenuation)))
    else:
        span = max(1e-6, float(max_dist) - float(full_dist))
        frac = (dist - float(full_dist)) / span
        atten = max(float(min_attenuation), (1.0 - frac) ** 1.4)

    if atten <= 0.0:
        return (0.0, 0.0)

    pan = max(-1.0, min(1.0, float(dx) / max(1e-6, float(pan_range))))
    bias = max(0.0, min(1.0, float(max_pan_bias)))
    left_gain = max(0.0, min(1.0, 1.0 - max(0.0, pan) * bias))
    right_gain = max(0.0, min(1.0, 1.0 - max(0.0, -pan) * bias))
    scaled = vol * atten
    return (min(1.0, scaled * left_gain), min(1.0, scaled * right_gain))
RAIN_CAMERA_VIEW_RADIUS = ((SCREEN_WIDTH / 2.0) ** 2 + (SCREEN_HEIGHT / 2.0) ** 2) ** 0.5
RAIN_AUDIO_WARNING_BUFFER = 1.5 * RAIN_CAMERA_VIEW_RADIUS
RAIN_AUDIO_APPROACH_MAX = 0.45
RAIN_AUDIO_INSIDE_MIN = 0.85
RAIN_AUDIO_INSIDE_MAX = 1.0
RAIN_AUDIO_INSIDE_RAMP_DIST = 240.0
RAIN_AUDIO_BOSS_FADE_DURATION = 1.25
BOSS_COMBAT_TRACKS = (
    "miniboss_combat.ogg",
    "night_boss.ogg",
    "final_reckoning.ogg",
    SLUG_BOSS_PHASE1_MUSIC,
    SLUG_BOSS_PHASE2_MUSIC,
    MEADOW_CENSOR_PHASE1_MUSIC,
    MEADOW_CENSOR_PHASE2_MUSIC,
    RIMECREST_ARBITER_PHASE1_MUSIC,
    RIMECREST_ARBITER_PHASE2_MUSIC,
    GALE_RAPTOR_MUSIC,
    TYPESETTER_MUSIC,
    GLASS_BASILISK_MUSIC,
)

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
        "speed_multiplier": 1.0,
        "cooldown_multiplier": 1.0,
        "rain_dps": 2.0,
        "page_yield_multiplier": 1.0,
        "banner": "ACT I: THE FIRST FOLIO",
        "label": "Night 1 — Low Saturation (Base Castes, 1.0x Pages)",
    },
    2: {
        "act": 2,
        "tier": "base",
        "empowered": False,
        "hp_multiplier": 1.4,
        "damage_multiplier": 1.35,
        "speed_multiplier": 1.08,
        "cooldown_multiplier": 0.92,
        "rain_dps": 2.5,
        "page_yield_multiplier": 1.25,
        "banner": "ACT II: THE SECOND FOLIO",
        "label": "Night 2 — Rising Saturation (Base+ Castes, 1.25x Pages)",
    },
    3: {
        "act": 3,
        "tier": "empowered",
        "empowered": True,
        "hp_multiplier": 2.0,
        "damage_multiplier": 1.8,
        "speed_multiplier": 1.15,
        "cooldown_multiplier": 0.85,
        "rain_dps": 3.0,
        "page_yield_multiplier": 1.5,
        "banner": "ACT III: THE SATURATED MARGIN",
        "label": "Night 3 — High Saturation (Empowered Castes, 1.5x Pages)",
    },
    4: {
        "act": 4,
        "tier": "empowered",
        "empowered": True,
        "hp_multiplier": 2.8,
        "damage_multiplier": 2.35,
        "speed_multiplier": 1.22,
        "cooldown_multiplier": 0.78,
        "rain_dps": 3.5,
        "page_yield_multiplier": 1.75,
        "banner": "ACT IV: THE DEEPENING BLEED",
        "label": "Night 4 — Severe Saturation (Empowered Castes, 1.75x Pages)",
    },
    5: {
        "act": 5,
        "tier": "empowered",
        "empowered": True,
        "hp_multiplier": 3.8,
        "damage_multiplier": 3.0,
        "speed_multiplier": 1.28,
        "cooldown_multiplier": 0.72,
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

# Batch 15: Lore-Tied Boss Summoning Ritual (The Ink-Unsealing Rite)
BOSS_SUMMON_SFX = "boss_summon.ogg"
BOSS_SUMMON_DURATION = 2.35
BOSS_SUMMON_EMERGE_TIME = 1.55
BOSS_SUMMON_CIRCLE_RADIUS = 52
BOSS_SUMMON_ERUPTION_RADIUS = 140.0
BOSS_SUMMON_TRIGGER_RADIUS = BOSS_SUMMON_ERUPTION_RADIUS
BOSS_SUMMON_SQUARE_COUNT = 240
BOSS_SUMMON_SQUARE_MAX_SIZE = 8.0
BOSS_SUMMON_SQUARE_MIN_SIZE = 2.0
BOSS_SUMMON_SQUARE_RISE_HEIGHT = 120.0
BOSS_SUMMON_GLYPH_COLOR = (135, 132, 142)

BOSS_SUMMON_PALETTES = {
    "SlugBoss": (
        (246, 244, 252),
        (196, 190, 206),
        (146, 140, 158),
        (168, 76, 228),
        (122, 48, 182),
    ),
    "RimecrestArbiterBoss": (
        (246, 252, 255),
        (192, 206, 220),
        (142, 158, 174),
        (108, 226, 252),
        (64, 176, 224),
    ),
    "MeadowCensorBoss": (
        (248, 244, 236),
        (194, 188, 180),
        (238, 194, 86),
        (168, 92, 222),
        (124, 62, 178),
    ),
    "empowered": (
        (246, 242, 246),
        (188, 180, 194),
        (228, 56, 84),
        (166, 62, 218),
        (120, 42, 158),
    ),
    "default": (
        (246, 244, 240),
        (206, 202, 198),
        (164, 160, 156),
        (124, 120, 116),
    ),
}

# Bottom-Center Boss Name & Health Bar HUD
BOSS_HUD_BAR_WIDTH = 520
BOSS_HUD_BAR_HEIGHT = 16
BOSS_HUD_BOTTOM_MARGIN = 26
BOSS_HUD_NAME_GAP = 8
BOSS_HUD_PROXIMITY_RADIUS = 20 * TILE_SIZE
BOSS_HUD_NAME_COLOR = (248, 242, 226)
BOSS_HUD_OUTLINE_COLOR = (10, 8, 14)
BOSS_HUD_BG_COLOR = (24, 16, 22, 235)
BOSS_HUD_FILL_COLOR = (198, 34, 48)
BOSS_HUD_HIGHLIGHT_COLOR = (238, 88, 98)
BOSS_HUD_BORDER_COLOR = (206, 184, 132)
BOSS_HUD_DISPLAY_NAMES = {
    "SlugBoss": "The Crowned Slug",
    "MeadowCensorBoss": "The Meadow Censor",
    "RimecrestArbiterBoss": "The Rimecrest Arbiter",
    "GaleVaneRaptorBoss": "The Gale-Vane Raptor",
    "TypesetterAutomatonBoss": "The Typesetter Automaton",
    "GlassKilnBasiliskBoss": "The Glass-Kiln Basilisk",
    "NightBoss": "Night Boss",
    "MarginWarden": "The Margin Warden",
    "FinalAuthor": "The Final Author",
}

# Articulated Boss Rig, MarginWarden Sibling Miniboss & Gimmick Armor/Weak-Point Constants
MARGIN_WARDEN_MAX_HP = 480
BOSS_ARMOR_DEFAULT_DAMAGE_MULT = 0.25
BOSS_WEAKPOINT_DEFAULT_DAMAGE_MULT = 2.0
BOSS_RIG_ANGLE_QUANT_DEG = 5
ARMOR_DEFLECT_SFX = "armor_deflect.ogg"
BOSS_EXPOSE_SFX = "boss_expose.ogg"
WEAKPOINT_CRIT_SFX = "weakpoint_crit.ogg"
COLOR_ARMOR_DEFLECT_SPARK = (196, 224, 248)
COLOR_ARMOR_DEFLECT_TEXT = (176, 194, 212)
COLOR_WEAKPOINT_CRIT_TEXT = (255, 196, 72)

# Glass Salt Flats (The Vitreous Basin) Fire Chalice & Heat Atmosphere Constants
VITREOUS_FIRE_CHALICE_SIZE = 80
VITREOUS_HEAT_SHIMMER_BANDS = 4
VITREOUS_EMBER_COUNT = 26

# 8-Direction Steep-Overhead Player Rig & Visible Equipped Weapons (Item #17)
PLAYER_RIG_SPRITE_WIDTH = 40
PLAYER_RIG_SPRITE_HEIGHT = 40
PLAYER_RIG_UNIQUE_DIRECTIONS = ("n", "ne", "e", "se", "s")
PLAYER_RIG_ALL_DIRECTIONS = ("n", "ne", "e", "se", "s", "sw", "w", "nw")
PLAYER_RIG_OCTANT_ORDER = ("e", "se", "s", "sw", "w", "nw", "n", "ne")
PLAYER_RIG_POSES = ("idle", "walk_0", "walk_1", "attack")
PLAYER_RIG_MIRROR_MAP = {
    "n": ("n", False),
    "ne": ("ne", False),
    "e": ("e", False),
    "se": ("se", False),
    "s": ("s", False),
    "sw": ("se", True),
    "w": ("e", True),
    "nw": ("ne", True),
}
PLAYER_RIG_NORTH_DIRECTIONS = frozenset(("n", "ne", "nw"))
PLAYER_RIG_WALK_FRAME_RATE = 8.0
PLAYER_RIG_IDLE_BOB_SPEED = 5.5
PLAYER_RIG_ATTACK_LUNGE_PX = 3.0
PLAYER_RIG_SHADOW_ALPHA = 120
PLAYER_RIG_SHADOW_W_RATIO = 0.68
PLAYER_RIG_SHADOW_H_PX = 9
PLAYER_RIG_HAND_COLOR = (212, 188, 152)
PLAYER_RIG_CUFF_COLOR = (68, 96, 152)
PLAYER_RIG_CLOAK_SHADOW = (18, 30, 62)
PLAYER_RIG_WEAPON_SCALE = 0.80
PLAYER_RIG_WEAPON_ATTACK_SCALE = 0.96
PLAYER_RIG_WEAPON_CARRY_CANT_RAD = 0.28
PLAYER_RIG_WEAPON_ROT_STEP_DEG = 3.0
PLAYER_RIG_WEAPON_CARRY_REACH_PX = 10.0
PLAYER_RIG_WEAPON_ATTACK_OFFSET_PX = 26.0

# Hand anchor offsets (dx, dy) relative to draw_rect center for a 40x40 steep-overhead rig
PLAYER_RIG_HAND_ANCHORS = {
    "n": (10.0, -5.0),
    "ne": (10.0, -2.0),
    "e": (9.0, 5.0),
    "se": (5.0, 9.0),
    "s": (-9.0, 7.0),
    "sw": (-5.0, 9.0),
    "w": (-9.0, 5.0),
    "nw": (-10.0, -2.0),
}

# Native striking-tip angle in pygame CCW-from-+X degrees for each floor-pickup weapon sprite
PLAYER_WEAPON_NATIVE_TIP_DEGREES = {
    "WeaponQuillStandard": -135.0,
    "WeaponQuillRefined": -135.0,
    "WeaponScriberBlade": 45.0,
    "WeaponAnomalousBleed": -135.0,
    "WeaponAnomalousRegen": -135.0,
    "WeaponAnomalousNegation": 45.0,
    "WeaponAnomalousStout": 45.0,
    "WeaponAnomalousDefault": -135.0,
}


def facing_to_direction_8(facing) -> str:
    """Map a 2D facing vector (fx, fy) in screen coordinates to one of 8 compass directions."""
    if not facing or len(facing) < 2:
        return "s"
    fx = float(facing[0])
    fy = float(facing[1])
    if math.hypot(fx, fy) < 1e-6:
        return "s"
    angle = math.atan2(fy, fx)
    octant = int(math.floor((angle + (math.pi / 8.0)) / (math.pi / 4.0))) % 8
    return PLAYER_RIG_OCTANT_ORDER[octant]


def resolve_player_rig_sprite_spec(direction_8: str) -> tuple:
    """Return (canonical_dir, flip_x) for any of the 8 compass directions."""
    key = str(direction_8 or "s").lower()
    return PLAYER_RIG_MIRROR_MAP.get(key, ("s", False))


def get_player_weapon_layer(direction_8: str) -> str:
    """Return 'behind' when facing north (N/NE/NW) and 'front' otherwise (S/SE/SW/E/W)."""
    key = str(direction_8 or "s").lower()
    return "behind" if key in PLAYER_RIG_NORTH_DIRECTIONS else "front"


def compute_player_weapon_rotation_deg(aim_rad: float, weapon_key: str) -> float:
    """Compute pygame.transform.rotate angle (CCW degrees) aligning weapon_key's tip with aim_rad."""
    native_tip = float(PLAYER_WEAPON_NATIVE_TIP_DEGREES.get(weapon_key, -135.0))
    return -math.degrees(float(aim_rad)) - native_tip


# Smooth 60 FPS Remote Player Interpolation & Model Rendering (Item #19)
NET_SNAPSHOT_INTERP_DELAY = 0.065               # ~65 ms snapshot interpolation delay (20 Hz UDP -> 60 FPS)
NET_SNAPSHOT_BUFFER_SIZE = 12                   # Max timestamped snapshots retained per remote peer
NET_DEAD_RECKONING_MAX_EXTRAPOLATION = 0.12     # Max dead-reckoning extrapolation (seconds) on dropped UDP packets
NET_DEAD_RECKONING_MAX_SEGMENT_DT = 0.50        # Max gap between consecutive snapshots eligible for velocity calc
NET_DEAD_RECKONING_MAX_SPEED = PLAYER_SPEED * DASH_SPEED_MULTIPLIER  # Cap extrapolated speed to max dash speed
NET_TELEPORT_SNAP_DISTANCE = 240.0              # Snap immediately instead of lerping across large warps/teleports
NET_REMOTE_WALK_SPEED_THRESHOLD = 18.0          # Interpolated speed (px/s) threshold for walk animation
NET_REMOTE_ATTACK_VISUAL_DURATION = SWORD_DURATION
NET_REMOTE_HOST_TRIM_COLOR = COLOR_CYAN
NET_REMOTE_GUEST_TRIM_COLOR = COLOR_MAGENTA
NET_REMOTE_NAMEPLATE_OFFSET_Y = 16
DEFAULT_PLAYER_WEAPON_KEY = "WeaponQuillStandard"
DEFAULT_REMOTE_FACING = (0.0, 1.0)

_REMOTE_STATE_ALIASES = {
    "IDLE": "IDLE",
    "MOVING": "RUN",
    "RUN": "RUN",
    "ATTACKING": "ATTACK",
    "ATTACK": "ATTACK",
    "DASHING": "DASH",
    "DASH": "DASH",
    "BLOCKING": "BLOCK",
    "BLOCK": "BLOCK",
    "STAGGERED": "STAGGERED",
}


def normalize_remote_player_state(raw_state) -> str:
    """Normalize a PlayerStateEnum or string action state into a canonical rig state key."""
    if raw_state is None:
        return "IDLE"
    val = getattr(raw_state, "value", raw_state)
    token = str(val).strip().upper()
    return _REMOTE_STATE_ALIASES.get(token, "IDLE")


def select_weapon_sprite_key(weapon_data) -> str:
    """Deterministically pick a weapon sprite key from weapon modifiers and name."""
    data = weapon_data if isinstance(weapon_data, dict) else {}
    mods = data.get("modifiers") or {}
    name = str(data.get("name", "")).lower()

    if mods or "anomalous" in name:
        if "bleed" in mods or "ink_bleed" in mods or "bleed" in name:
            return "WeaponAnomalousBleed"
        if "slow_hp_regen" in mods or "vampirism" in mods or "regen" in mods or "life" in name:
            return "WeaponAnomalousRegen"
        if (
            "damage_negation_on_hit" in mods
            or "parry_window" in mods
            or "negation" in mods
            or "iron" in name
        ):
            return "WeaponAnomalousNegation"
        if "max_hp_boost" in mods or "void_strike" in mods or "stout" in mods or "void" in name:
            return "WeaponAnomalousStout"
        return "WeaponAnomalousDefault"

    if "refined" in name:
        return "WeaponQuillRefined"
    if any(tok in name for tok in ("blade", "dagger", "knife", "sword", "scriber")):
        return "WeaponScriberBlade"
    if "standard" in name or not name:
        return DEFAULT_PLAYER_WEAPON_KEY
    standard_keys = ("WeaponQuillStandard", "WeaponQuillRefined", "WeaponScriberBlade")
    return standard_keys[sum(ord(ch) for ch in name) % len(standard_keys)]


# Multi-Directional 80px Benches (South/North: 80x40, East/West: 40x80)
BENCH_FACINGS = ("south", "north", "east", "west")
BENCH_DEFAULT_FACING = "south"
BENCH_HORIZONTAL_FACINGS = frozenset(("south", "north"))
BENCH_VERTICAL_FACINGS = frozenset(("east", "west"))
BENCH_SPRITE_FILENAMES = {
    "south": "bench.png",
    "north": "bench_north.png",
    "east": "bench_east.png",
    "west": "bench_west.png",
}
BENCH_PROP_CACHE_KEYS = {
    "south": "Bench",
    "north": "BenchNorth",
    "east": "BenchEast",
    "west": "BenchWest",
}
_BENCH_FACING_ALIASES = {"s": "south", "n": "north", "e": "east", "w": "west"}


def normalize_bench_facing(facing) -> str:
    """Normalize a bench facing token into one of ('south', 'north', 'east', 'west')."""
    if not facing:
        return BENCH_DEFAULT_FACING
    token = str(facing).strip().lower()
    token = _BENCH_FACING_ALIASES.get(token, token)
    return token if token in BENCH_FACINGS else BENCH_DEFAULT_FACING


def get_bench_dimensions(facing: str = BENCH_DEFAULT_FACING) -> tuple:
    """Return pixel (width, height) for a bench: 80x40 for N/S, 40x80 for E/W."""
    norm = normalize_bench_facing(facing)
    if norm in BENCH_VERTICAL_FACINGS:
        return (TILE_SIZE, TILE_SIZE * 2)
    return (TILE_SIZE * 2, TILE_SIZE)


def get_bench_footprint_tiles(x: int, y: int, facing: str = BENCH_DEFAULT_FACING) -> tuple:
    """Return the 2 occupied grid tile coordinates for a bench anchored at (x, y)."""
    norm = normalize_bench_facing(facing)
    if norm in BENCH_VERTICAL_FACINGS:
        return ((x, y), (x, y + 1))
    return ((x, y), (x + 1, y))


# Enhanced Death Sequence (Text Bleaching — Section 8)
DEATH_BLEACH_DURATION = DEATH_SCREEN_DURATION
DEATH_BLEACH_SATURATION_END = 0.72          # Normalized progress where color desaturation completes
DEATH_BLEACH_WASH_START = 0.14              # Normalized progress where pale parchment washout begins
DEATH_BLEACH_WASH_MAX_ALPHA = 185           # Peak parchment washout alpha (0..255)
DEATH_BLEACH_VIGNETTE_END = 0.55            # Normalized progress where edge ink vignette peaks
DEATH_BLEACH_VIGNETTE_MAX_ALPHA = 135       # Peak dark-ink vignette border alpha
DEATH_BLEACH_CAMERA_PULLBACK_MAX = 0.14     # Max camera zoom-out pull-back fraction (1.0 -> 0.86)
DEATH_BLEACH_TEXT_FADE_START = 0.10         # Progress when 'TEXT BLEACHING...' begins fading in
DEATH_BLEACH_TEXT_FADE_END = 0.40           # Progress when 'TEXT BLEACHING...' reaches full alpha
DEATH_BLEACH_SUBTITLE_FADE_START = 0.34     # Progress when subtitle begins fading in
DEATH_BLEACH_SUBTITLE_FADE_END = 0.62       # Progress when subtitle reaches full alpha
DEATH_BLEACH_TEXT_Y_DRIFT_PX = 14.0         # Subtle upward typographic settle drift during fade-in
DEATH_BLEACH_PARCHMENT_COLOR = (232, 224, 206)
DEATH_BLEACH_MARGIN_COLOR = (26, 22, 24)
DEATH_BLEACH_FRAME_BORDER_COLOR = (128, 118, 102)
DEATH_BLEACH_SUBTITLE_COLOR = (58, 50, 46)
DEATH_BLEACH_TITLE = "TEXT BLEACHING..."
DEATH_BLEACH_SUBTITLE = "FADING INTO A REJECTED DRAFT"


def _smoothstep(edge0: float, edge1: float, value: float) -> float:
    """Evaluate a clamped Hermite smoothstep interpolation in [0.0, 1.0]."""
    span = edge1 - edge0
    if span <= 1e-6:
        return 1.0 if value >= edge1 else 0.0
    t = max(0.0, min(1.0, (float(value) - edge0) / span))
    return t * t * (3.0 - 2.0 * t)


def compute_death_bleach_state(death_timer: float, duration: float = DEATH_SCREEN_DURATION) -> dict:
    """Compute decoupled, dt-driven Text Bleaching animation parameters from remaining death_timer."""
    rem = float(death_timer or 0.0)
    dur = float(duration or 0.0)
    if rem <= 0.0 or dur <= 0.0:
        return {
            "active": False,
            "progress": 0.0,
            "desaturation": 0.0,
            "wash_alpha": 0,
            "vignette_alpha": 0,
            "pullback_ratio": 0.0,
            "camera_scale": 1.0,
            "text_alpha": 0,
            "subtitle_alpha": 0,
            "text_offset_y": 0.0,
        }

    progress = max(0.0, min(1.0, 1.0 - (rem / dur)))
    desaturation = _smoothstep(0.0, DEATH_BLEACH_SATURATION_END, progress)
    wash_t = _smoothstep(DEATH_BLEACH_WASH_START, 1.0, progress)
    vignette_t = _smoothstep(0.0, DEATH_BLEACH_VIGNETTE_END, progress)
    pullback_ratio = 1.0 - (1.0 - progress) ** 2
    camera_scale = 1.0 - (pullback_ratio * DEATH_BLEACH_CAMERA_PULLBACK_MAX)
    text_t = _smoothstep(DEATH_BLEACH_TEXT_FADE_START, DEATH_BLEACH_TEXT_FADE_END, progress)
    sub_t = _smoothstep(DEATH_BLEACH_SUBTITLE_FADE_START, DEATH_BLEACH_SUBTITLE_FADE_END, progress)

    return {
        "active": True,
        "progress": progress,
        "desaturation": desaturation,
        "wash_alpha": int(round(wash_t * DEATH_BLEACH_WASH_MAX_ALPHA)),
        "vignette_alpha": int(round(vignette_t * DEATH_BLEACH_VIGNETTE_MAX_ALPHA)),
        "pullback_ratio": pullback_ratio,
        "camera_scale": camera_scale,
        "text_alpha": int(round(text_t * 255)),
        "subtitle_alpha": int(round(sub_t * 255)),
        "text_offset_y": (1.0 - text_t) * DEATH_BLEACH_TEXT_Y_DRIFT_PX,
    }


# Respite Activation Pulse (Section 8: Localized Typographic Bloom)
RESPITE_PULSE_DURATION = 1.45
RESPITE_PULSE_RING_START_RADIUS = 16.0
RESPITE_PULSE_RING_MAX_RADIUS = 195.0
RESPITE_PULSE_RING_INNER_SCALE = 0.72
RESPITE_PULSE_RING_MAX_ALPHA = 245
RESPITE_PULSE_HALO_MAX_ALPHA = 85
RESPITE_PULSE_RING_COLOR_OUTER = (110, 232, 240)   # Soft cyan-ink shimmer
RESPITE_PULSE_RING_COLOR_INNER = (238, 228, 200)   # Warm parchment glow
RESPITE_PULSE_DARK_INK_COLOR = (14, 12, 24)        # High-contrast dark-ink backing & glyph outline
RESPITE_PULSE_GLYPH_COUNT = 20
RESPITE_PULSE_GLYPH_POOL = (
    "A", "E", "I", "O", "R", "S", "T", "V", "§", "¶", "†", "‡", "※", "ø",
)
RESPITE_PULSE_GLYPH_SPAWN_RADIUS_MIN = 10.0
RESPITE_PULSE_GLYPH_SPAWN_RADIUS_MAX = 34.0
RESPITE_PULSE_GLYPH_RISE_SPEED_MIN = 28.0
RESPITE_PULSE_GLYPH_RISE_SPEED_MAX = 58.0
RESPITE_PULSE_GLYPH_RADIAL_DRIFT_MAX = 18.0
RESPITE_PULSE_GLYPH_SWAY_AMP = 6.0
RESPITE_PULSE_GLYPH_SWAY_FREQ = 3.2
RESPITE_PULSE_GLYPH_LIFETIME_MIN = 0.95
RESPITE_PULSE_GLYPH_LIFETIME_MAX = 1.45

# Gamepad Rumble (Joystick.rumble — Section 1)
# Tuple format: (low_frequency, high_frequency, duration_ms, priority)
RUMBLE_PRESET_COMBAT_HIT = (0.25, 0.45, 70, 1)
RUMBLE_PRESET_PLAYER_DAMAGE = (0.65, 0.35, 160, 2)
RUMBLE_PRESET_PARRY = (0.45, 0.90, 140, 3)
RUMBLE_PRESET_BOSS_SUMMON = (0.85, 0.55, 420, 4)

RUMBLE_PRESETS = {
    "combat_hit": RUMBLE_PRESET_COMBAT_HIT,
    "player_damage": RUMBLE_PRESET_PLAYER_DAMAGE,
    "parry": RUMBLE_PRESET_PARRY,
    "boss_summon": RUMBLE_PRESET_BOSS_SUMMON,
}

# Tactile Menu Transitions (Parchment Unroll / Slide — Section 8)
MENU_TRANSITION_DURATION = 0.28            # Seconds for full Chronicle parchment unroll
MENU_TRANSITION_SUBVIEW_DURATION = 0.22    # Faster unroll on sub-view transitions (Controls / Confirm)
MENU_TRANSITION_SLIDE_OFFSET_PX = 28.0     # Vertical slide settle distance (px) from top
MENU_TRANSITION_MIN_REVEAL = 0.08          # Minimum reveal fraction at progress=0.0 so scroll lip stays visible
MENU_TRANSITION_ROLLER_HEIGHT_PX = 10      # Decorative rolled parchment cylinder height during unroll
MENU_TRANSITION_PARCHMENT_BG = (22, 19, 28, 224)
MENU_TRANSITION_PARCHMENT_BORDER = (164, 146, 114)
MENU_TRANSITION_PARCHMENT_RULE = (118, 102, 78, 175)
MENU_TRANSITION_ROLLER_COLOR = (138, 116, 86)
MENU_TRANSITION_ROLLER_HIGHLIGHT = (212, 192, 152)
MENU_TRANSITION_ROLLER_SHADOW = (14, 11, 18)


def ease_out_cubic(value: float) -> float:
    """Evaluate a clamped cubic ease-out curve in [0.0, 1.0]."""
    t = max(0.0, min(1.0, float(value)))
    return 1.0 - (1.0 - t) ** 3


def compute_menu_transition_state(
    progress: float,
    slide_px: float = MENU_TRANSITION_SLIDE_OFFSET_PX,
) -> dict:
    """Compute pure, dt-decoupled parchment unroll and vertical-slide metrics from progress in [0.0, 1.0]."""
    raw = max(0.0, min(1.0, float(progress)))
    if raw >= 1.0:
        return {
            "progress": 1.0,
            "eased": 1.0,
            "reveal_ratio": 1.0,
            "offset_y": 0.0,
            "alpha": 255,
            "backdrop_alpha_scale": 1.0,
            "roller_alpha": 0,
            "settled": True,
        }

    eased = ease_out_cubic(raw)
    reveal_ratio = MENU_TRANSITION_MIN_REVEAL + (1.0 - MENU_TRANSITION_MIN_REVEAL) * eased
    offset_y = -(1.0 - eased) * float(slide_px)
    alpha = int(round(255 * _smoothstep(0.0, 0.55, raw)))
    backdrop_alpha_scale = _smoothstep(0.0, 0.70, raw)
    roller_alpha = int(round(255 * (1.0 - _smoothstep(0.75, 1.0, raw))))
    return {
        "progress": raw,
        "eased": eased,
        "reveal_ratio": reveal_ratio,
        "offset_y": offset_y,
        "alpha": alpha,
        "backdrop_alpha_scale": backdrop_alpha_scale,
        "roller_alpha": roller_alpha,
        "settled": False,
    }
