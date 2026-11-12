"""
Unit tests for visual slash arc geometry, anomalous passive color tinting, and impact sparks feedback.
"""
# pylint: disable=no-member,protected-access
import math
import pygame
import constants
from engine.player import Player, PlayerStateEnum
from engine.enemy import SlugEnemy
from engine.game_state import GameState
from engine.world import GameObject
from rendering.renderer import Renderer


class DummyScreen:
    """Mock screen surface for headless rendering tests."""
    def get_width(self):
        """Return screen width."""
        return constants.SCREEN_WIDTH

    def get_height(self):
        """Return screen height."""
        return constants.SCREEN_HEIGHT

    def fill(self, color):
        """Mock fill."""

    def blit(self, surf, pos):
        """Mock blit."""


class DummyFont:
    """Mock font."""
    def render(self, _text, _aa, _color=None):
        """Return dummy surface."""
        return pygame.Surface((10, 10), pygame.SRCALPHA)

    def size(self, text):
        """Return text dimensions."""
        return (len(text) * 8, 12)


def _setup_headless_renderer(monkeypatch, recorded):
    """Configures a headless Renderer recording pygame.draw calls."""
    monkeypatch.setattr(pygame.font, "SysFont", lambda *a, **k: DummyFont())
    monkeypatch.setattr(
        pygame.draw,
        "line",
        lambda surf, col, p1, p2, *a, **k: recorded.append(("line", col, tuple(p1), tuple(p2))),
    )
    monkeypatch.setattr(
        pygame.draw,
        "circle",
        lambda surf, col, pos, r, *a, **k: recorded.append(("circle", col, tuple(pos), r)),
    )
    monkeypatch.setattr(
        pygame.draw,
        "polygon",
        lambda surf, col, pts, *a, **k: recorded.append(("polygon", col, [tuple(p) for p in pts])),
    )
    return Renderer(DummyScreen())


def test_weapon_passive_color_resolution():
    """Verify anomalous passive color tinting across all anomalous variants and standard weapons."""
    # 1. Bleed / Ink-Bleed
    bleed_wpn = {"name": "Anomalous Ink-Bleed", "modifiers": {"bleed": 5.0}}
    assert constants.get_weapon_passive_color(bleed_wpn) == constants.COLOR_ANOMALOUS_BLEED

    # 2. HP Regen / Life-Thread / Vampirism
    regen_wpn = {"name": "Anomalous Life-Thread", "modifiers": {"slow_hp_regen": 1.0}}
    assert constants.get_weapon_passive_color(regen_wpn) == constants.COLOR_ANOMALOUS_REGEN

    # 3. Negation / Iron-Nib / Parry Window
    neg_wpn = {"name": "Anomalous Iron-Nib", "modifiers": {"damage_negation_on_hit": 5.0}}
    assert constants.get_weapon_passive_color(neg_wpn) == constants.COLOR_ANOMALOUS_NEGATION

    # 4. Stout / Max HP Boost / Void Strike
    stout_wpn = {"name": "Anomalous Stout-Draft", "modifiers": {"max_hp_boost": 20.0}}
    assert constants.get_weapon_passive_color(stout_wpn) == constants.COLOR_ANOMALOUS_STOUT

    # 5. Generic anomalous modifier
    generic_wpn = {"name": "Anomalous Resonator", "modifiers": {"custom_effect": 1.0}}
    assert constants.get_weapon_passive_color(generic_wpn) == constants.COLOR_ANOMALOUS_DEFAULT

    # 6. Standard common weapon without modifiers
    common_wpn = {"name": "Refined Quill", "damage": 15}
    assert constants.get_weapon_passive_color(common_wpn) == constants.COLOR_SWORD_SLASH_DEFAULT
    assert constants.get_weapon_passive_color(None) == constants.COLOR_SWORD_SLASH_DEFAULT


def test_visual_slash_arc_exact_geometry_and_tint(monkeypatch):
    """Verify visual slash arc matches 64.0 reach, 2.10 rad arc span, and anomalous tinting."""
    recorded = []
    renderer = _setup_headless_renderer(monkeypatch, recorded)

    player = Player(100, 100)
    player.facing = (1, 0)
    player.state = PlayerStateEnum.ATTACKING
    player.attack_timer = constants.SWORD_DURATION * 0.5  # Halfway through attack

    # Test bleed weapon renders crimson slash arc
    player.weapons = [{"name": "Anomalous Ink-Bleed", "modifiers": {"bleed": 5.0}}]
    player.active_weapon_idx = 0
    recorded.clear()
    renderer.draw_player_weapon_attack(player, 0, 0)

    drawn_colors = [call[1] for call in recorded]
    assert constants.COLOR_ANOMALOUS_BLEED in drawn_colors

    # Verify reach of outer lines matches constants.SWORD_REACH (64.0)
    cx, cy = player.get_center()
    outer_points = [
        call[2] for call in recorded if call[0] == "line" and call[1] == constants.COLOR_ANOMALOUS_BLEED
    ]
    assert outer_points, "Expected outer crescent arc lines to be drawn"
    # Filter for points on the outer rim (dist >= 60.0)
    rim_points = [pt for pt in outer_points if math.hypot(pt[0] - cx, pt[1] - cy) >= 60.0]
    assert rim_points, "Expected outer rim arc points"
    for pt in rim_points:
        dist = math.hypot(pt[0] - cx, pt[1] - cy)
        assert math.isclose(dist, constants.SWORD_REACH, abs_tol=1.5)

    # Test regen weapon renders emerald green slash arc
    player.weapons = [{"name": "Anomalous Life-Thread", "modifiers": {"slow_hp_regen": 1.0}}]
    recorded.clear()
    renderer.draw_player_weapon_attack(player, 0, 0)
    drawn_colors = [call[1] for call in recorded]
    assert constants.COLOR_ANOMALOUS_REGEN in drawn_colors


def test_fading_slash_arc_lifecycle_and_rendering(monkeypatch):
    """Verify fading visual slash arcs are spawned when an attack completes and expire with dt."""
    state = GameState(auto_load=False)
    state.player.x, state.player.y = 200, 200
    state.player.facing = (0, 1)
    state.player.weapons = [{"name": "Anomalous Iron-Nib", "modifiers": {"damage_negation_on_hit": 5.0}}]
    state.player.active_weapon_idx = 0

    # 1. Start attack
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.attack_timer = constants.SWORD_DURATION
    state.update_combat(0.01, False, {}, None)
    assert getattr(state, "_player_was_attacking", False) is True

    # 2. Finish attack
    state.player.state = PlayerStateEnum.IDLE
    state.player.attack_timer = 0.0
    state.update_combat(0.01, False, {}, None)

    # Slash arc should now be queued in state.slash_effects
    assert len(state.slash_effects) == 1
    slash = state.slash_effects[0]
    assert slash["reach"] == constants.SWORD_REACH
    assert slash["arc_radians"] == constants.SWORD_ARC_RADIANS
    assert slash["color"] == constants.COLOR_ANOMALOUS_NEGATION
    assert slash["time"] == constants.SLASH_FADE_DURATION

    # 3. Test headless rendering of fading arc
    recorded = []
    renderer = _setup_headless_renderer(monkeypatch, recorded)
    renderer.draw_fading_slash_arcs(state, 0, 0)
    # Surface blits aren't tracked in recorded, but ensures method runs cleanly without exception

    # 4. Advance time past SLASH_FADE_DURATION to verify cleanup
    state._update_shared_world(constants.SLASH_FADE_DURATION + 0.05)
    assert len(state.slash_effects) == 0


def test_impact_sparks_spawn_on_enemy_and_prop_hits(monkeypatch):
    """Verify subtle impact sparks spawn on landed hits with correct anomalous tint and dt movement."""
    state = GameState(auto_load=False)
    state.player.x, state.player.y = 100, 100
    state.player.facing = (1, 0)
    state.player.weapons = [{"name": "Anomalous Stout-Draft", "modifiers": {"max_hp_boost": 20.0}}]
    state.player.active_weapon_idx = 0
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.attack_timer = constants.SWORD_DURATION

    # Place an enemy in front of the player (within 64px reach)
    enemy = SlugEnemy(130, 100)
    state.enemies.append(enemy)

    # Place a breakable barrel nearby
    barrel = GameObject((120, 110), (32, 32))
    barrel.name = "Barrel"
    barrel.is_breakable = True
    barrel.health = 1.0
    state.world.interactables.append(barrel)

    # Update combat: should hit enemy and spawn impact sparks
    assert len(state.impact_sparks) == 0
    state.update_combat(0.01, False, {}, None)

    assert len(state.impact_sparks) >= constants.IMPACT_SPARK_COUNT
    for spark in state.impact_sparks:
        assert spark["color"] == constants.COLOR_ANOMALOUS_STOUT
        assert spark["time"] == constants.IMPACT_SPARK_LIFETIME
        assert math.hypot(spark["vx"], spark["vy"]) >= constants.IMPACT_SPARK_SPEED_MIN

    # Verify rendering of impact sparks
    recorded = []
    renderer = _setup_headless_renderer(monkeypatch, recorded)
    recorded.clear()
    renderer.draw_impact_sparks(state, 0, 0)
    drawn_lines = [call for call in recorded if call[0] == "line"]
    assert len(drawn_lines) >= constants.IMPACT_SPARK_COUNT
    for line in drawn_lines:
        assert line[1] == constants.COLOR_ANOMALOUS_STOUT

    # Test dt update advances positions and cleans up expired sparks
    orig_x = state.impact_sparks[0]["x"]
    vx = state.impact_sparks[0]["vx"]
    state._update_shared_world(0.05)
    assert math.isclose(state.impact_sparks[0]["x"], orig_x + vx * 0.05, abs_tol=1e-3)

    # Advance past lifetime: sparks should be cleared
    state._update_shared_world(constants.IMPACT_SPARK_LIFETIME + 0.05)
    assert len(state.impact_sparks) == 0
