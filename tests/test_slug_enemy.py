import math
from engine.game_state import GameState
from engine.maps import create_world
from constants import TILE_SIZE, SLUG_MAX_HP, SWORD_DAMAGE, PLAYER_MAX_HP, PLAYER_START_X, PLAYER_START_Y
from engine.player import PlayerStateEnum


def distance(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def test_slug_spawns_and_moves_toward_player():
    gs = GameState(auto_load=False)
    gs.world = create_world('outside')
    gs.enemies = getattr(gs.world, 'enemies', [])
    assert len(gs.enemies) >= 1
    e = gs.enemies[0]
    # Move the slug to within detection radius so it will approach
    # Place it 100 pixels to the right of the player (within 5*TILE_SIZE=200)
    e.x = gs.player.x + 100
    e.y = gs.player.y
    before = distance((e.x, e.y), gs.player.get_center())
    # Run updates to let slug approach
    for _ in range(10):
        gs.update(0.1, {})
    after = distance((e.x, e.y), gs.player.get_center())
    assert after < before


def test_slug_damage_player_and_respawn_on_death():
    gs = GameState(auto_load=False)
    gs.world = create_world('outside')
    gs.enemies = getattr(gs.world, 'enemies', [])
    # Place an enemy directly on top of the player to force contact
    if not gs.enemies:
        assert False, "No enemies spawned"
    e = gs.enemies[0]
    e.x = gs.player.x
    e.y = gs.player.y
    # Ensure player's HP exists
    gs.player.hp = PLAYER_MAX_HP
    # Run update to apply contact damage
    gs.update(0.1, {})
    assert gs.player.hp < PLAYER_MAX_HP
    # Reduce player's HP to 0 and ensure respawn occurs
    gs.player.hp = 1
    # Force contact and update
    e.x = gs.player.x
    e.y = gs.player.y
    gs.update(0.5, {})
    # After death, world should be reset to sanctuary and player at start
    assert gs.player.x == float(PLAYER_START_X)
    assert gs.player.y == float(PLAYER_START_Y)


def test_player_attack_hurts_slug_and_kills():
    gs = GameState(auto_load=False)
    gs.world = create_world('outside')
    gs.enemies = getattr(gs.world, 'enemies', [])
    assert gs.enemies
    e = gs.enemies[0]
    # Place slug so that it intersects the sword hitbox
    from engine.combat import get_sword_hitbox
    cx, cy = gs.player.get_center()
    # Compute a hitbox for a right-facing attack
    gs.player.facing = (1, 0)
    hitbox = get_sword_hitbox((cx, cy), gs.player.facing)
    # Place enemy overlapping the hitbox
    e.x = hitbox[0] + 1
    e.y = hitbox[1] + 1
    initial_hp = e.hp
    # Put player into attacking state so update applies sword hit
    gs.player.state = PlayerStateEnum.ATTACKING
    gs.player.attack_timer = 0.5
    gs.update(0.1, {})
    assert e.hp == initial_hp - SWORD_DAMAGE
    # Kill the slug with repeated attacks
    while not e.is_dead():
        gs.player.state = PlayerStateEnum.ATTACKING
        gs.player.attack_timer = 0.5
        gs.update(0.1, {})
    assert e.is_dead()
    # Enemy should be removed from game state's enemies
    assert e not in gs.enemies
