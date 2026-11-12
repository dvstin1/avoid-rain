"""
Unit tests for combat, visual-aligned hitboxes, and diagonal attack resolution.
"""
from engine.combat import get_sword_hitbox, check_sword_hit
from engine.game_state import GameState
from engine.enemy import SlugEnemy
from engine.player import PlayerStateEnum
from constants import SWORD_REACH, SWORD_DAMAGE


def test_sword_hitbox_cardinal_directions():
    """Verify sword bounding boxes for cardinal directions match the visual 120-degree sweep."""
    center = (100, 100)

    # Right: spans x from 100 to 164, y from 44 to 155
    hb_right = get_sword_hitbox(center, (1, 0))
    assert hb_right == (100, 44, 64, 111)

    # Left: spans x from 36 to 100, y from 44 to 155
    hb_left = get_sword_hitbox(center, (-1, 0))
    assert hb_left == (36, 44, 64, 111)

    # Down: spans x from 44 to 155, y from 100 to 164
    hb_down = get_sword_hitbox(center, (0, 1))
    assert hb_down == (44, 100, 111, 64)

    # Up: spans x from 44 to 155, y from 36 to 100
    hb_up = get_sword_hitbox(center, (0, -1))
    assert hb_up == (44, 36, 111, 64)


def test_sword_hitbox_diagonal_directions():
    """Verify sword bounding boxes for all 4 diagonal facings correctly cover diagonal quadrants."""
    center = (100, 100)

    # Down-Right (1, 1)
    hb_dr = get_sword_hitbox(center, (1, 1))
    assert hb_dr == (83, 83, 81, 81)

    # Up-Right (1, -1)
    hb_ur = get_sword_hitbox(center, (1, -1))
    assert hb_ur == (83, 36, 81, 81)

    # Down-Left (-1, 1)
    hb_dl = get_sword_hitbox(center, (-1, 1))
    assert hb_dl == (36, 83, 81, 81)

    # Up-Left (-1, -1)
    hb_ul = get_sword_hitbox(center, (-1, -1))
    assert hb_ul == (36, 36, 81, 81)


def test_check_sword_hit_accuracy():
    """Verify check_sword_hit accurately detects diagonal, off-axis, and point-blank targets."""
    player = (100, 100)

    # 1. Facing right: hits directly in front (dx=30, dy=0)
    assert check_sword_hit(player, (1, 0), (130, 90, 20, 20)) is True

    # 2. Facing right: hits off-axis / diagonal enemy within the 120-degree crescent arc
    assert check_sword_hit(player, (1, 0), (125, 120, 20, 20)) is True
    assert check_sword_hit(player, (1, 0), (125, 60, 20, 20)) is True

    # 3. Facing diagonally down-right (1, 1): hits enemy placed diagonally
    assert check_sword_hit(player, (1, 1), (125, 125, 20, 20)) is True

    # 4. Facing diagonally down-right: hits enemy along adjacent cardinal directions in the sweep
    assert check_sword_hit(player, (1, 1), (135, 95, 20, 20)) is True
    assert check_sword_hit(player, (1, 1), (95, 135, 20, 20)) is True

    # 5. Point-blank target overlapping the player center
    assert check_sword_hit(player, (1, 0), (95, 95, 20, 20)) is True

    # 6. Does NOT hit enemy behind player
    assert check_sword_hit(player, (1, 0), (60, 90, 20, 20)) is False
    assert check_sword_hit(player, (1, 1), (60, 60, 20, 20)) is False

    # 7. Does NOT hit enemy out of reach (> SWORD_REACH)
    assert check_sword_hit(player, (1, 0), (100 + int(SWORD_REACH) + 20, 90, 20, 20)) is False


def test_combat_resolution_hits_diagonal_enemy():
    """Verify that PlayerStateEnum.ATTACKING damages enemies positioned diagonally."""
    state = GameState(auto_load=False)
    state.player.x = 100.0
    state.player.y = 100.0
    state.player.state = PlayerStateEnum.ATTACKING
    # Player aims down-right
    state.player.facing = (1.0, 1.0)

    # Place enemy in the down-right diagonal sweep (center at ~132, 132; distance ~45px)
    enemy = SlugEnemy(122.0, 122.0)
    initial_hp = enemy.hp
    state.enemies = [enemy]

    state.update_combat(0.016, attack_pressed=False, actions={}, audio_manager=None)

    # Enemy must take damage from diagonal strike
    assert enemy.hp == initial_hp - SWORD_DAMAGE
    assert getattr(enemy, 'network_id', id(enemy)) in state.player.hit_entities_this_attack
    # Glyph particles spawned at hit position
    assert len(state.glyph_particles.particles) > 0

    state.shutdown_save_worker(timeout=1.0)
