"""
Unit tests for the Boss attack hitboxes and damage resolution logic.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member

import os
# Ensure pygame headless mode
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pytest
import pygame

from engine.game_state import GameState
from engine.enemy import Miniboss
from engine.actor import ActorState


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initializes pygame in headless mode for the test suite."""
    pygame.init()
    yield
    pygame.quit()


def test_boss_attack_hitbox_dimensions():
    """
    Verifies that the Boss class get_attack_hitbox method returns the correct
    hitbox dimensions for THRUST and SWING attacks based on facing direction.
    """
    # 1. Spawn a Miniboss (subclass of Boss) at (100, 100)
    # Size is 64x64, center is (132, 132)
    boss = Miniboss(100, 100, hp=100)
    boss.facing = (1, 0)  # Facing Right

    # 2. Test THRUST attack type
    boss.attack_type = "THRUST"
    hb_thrust_right = boss.get_attack_hitbox()
    # Center = 132, base_offset = 32, offset = 42
    # Thrust length = 100, thickness = 30
    # Expected x = 132 + 42 = 174
    # Expected y = 132 - 15 = 117
    assert hb_thrust_right == (174, 117, 100, 30)

    # 3. Facing Left
    boss.facing = (-1, 0)
    hb_thrust_left = boss.get_attack_hitbox()
    # Expected x = 132 - 42 - 100 = -10
    # Expected y = 132 - 15 = 117
    assert hb_thrust_left == (-10, 117, 100, 30)

    # 4. Test SWING attack type facing Right
    boss.facing = (1, 0)
    boss.attack_type = "SWING"
    hb_swing_right = boss.get_attack_hitbox()
    # Center = 132, base_offset = 32, offset = 37
    # Swing length = 50, thickness = 120
    # Expected x = 132 + 37 = 169
    # Expected y = 132 - 60 = 72
    assert hb_swing_right == (169, 72, 50, 120)


def test_boss_damage_resolution_by_hitbox():
    """
    Verifies that during strike frames, the Boss uses its custom attack hitbox
    to deal damage, hitting players in front of the attack but sparing players
    behind the attack.
    """
    state = GameState(auto_load=False)

    # Spawn boss at (200, 200), facing Right. Center is (232, 232)
    boss = Miniboss(200, 200, hp=100)
    boss.facing = (1, 0)
    boss.attack_type = "THRUST"  # Gated hitbox is (274, 217, 100, 30)
    boss.state = ActorState.STRIKE
    boss.damage = 10.0
    state.enemies = [boss]

    # Player 1 is positioned in front of the boss, inside the thrust hitbox
    # Player rect is 40x40. Placing center at (300, 225) -> top-left at (280, 205)
    state.player.x = 280
    state.player.y = 205
    state.player.hp = 100.0

    # attempt_damage_player should hit the player
    hit = boss.attempt_damage_player(state)
    assert hit is True, "Boss should hit the player standing in the attack zone."
    assert state.player.hp == 90.05, "Player should take reduced damage (9.95) due to Edification passive."

    # Reset player hp and move player behind the boss
    # Placing player at (100, 200) - completely behind the attack direction
    state.player.x = 100
    state.player.y = 200
    state.player.hp = 100.0

    # attempt_damage_player should not hit the player
    hit_behind = boss.attempt_damage_player(state)
    assert hit_behind is False, "Boss should not hit the player standing behind the attack."
    assert state.player.hp == 100.0, "Player behind the boss should not take damage."
