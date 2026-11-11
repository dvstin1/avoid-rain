"""Unit tests for procedural basic-shape enemy, player, and weapon graphics in the Renderer."""
# pylint: disable=no-member
import pygame
import constants
from rendering.renderer import Renderer
from engine.enemy import BatEnemy, FlutterEnemy, BindlingEnemy, SmearEnemy, Miniboss
from engine.actor import Actor, ActorState
from engine.player import Player, PlayerStateEnum


def _create_headless_renderer(monkeypatch, recorded_draws):
    """Create a headless Renderer that records pygame.draw calls."""
    class DummyScreen:
        """Mock screen surface."""
        def get_width(self):
            """Return width."""
            return constants.SCREEN_WIDTH

        def get_height(self):
            """Return height."""
            return constants.SCREEN_HEIGHT

        def fill(self, color):
            """No-op fill."""

        def blit(self, surf, pos):
            """No-op blit."""

    class DummyFont:
        """Mock font."""
        def render(self, _text, _aa, _color=None):
            """Return dummy surface."""
            return pygame.Surface((10, 10), pygame.SRCALPHA)

        def size(self, text):
            """Return dummy text size."""
            return (len(text) * 8, 12)

    monkeypatch.setattr(pygame.font, "SysFont", lambda *a, **k: DummyFont())
    monkeypatch.setattr(
        pygame.draw,
        "rect",
        lambda surf, col, rect, *a, **k: recorded_draws.append(("rect", col, tuple(rect))),
    )
    monkeypatch.setattr(
        pygame.draw,
        "circle",
        lambda surf, col, pos, r, *a, **k: recorded_draws.append(("circle", col, tuple(pos), r)),
    )
    monkeypatch.setattr(
        pygame.draw,
        "line",
        lambda surf, col, p1, p2, *a, **k: recorded_draws.append(("line", col, tuple(p1), tuple(p2))),
    )
    return Renderer(DummyScreen())


def test_procedural_enemies_render_distinct_shapes(monkeypatch):
    """Verify Bat, Flutter, Bindling, Smear, and Miniboss render procedural geometric shapes."""
    recorded = []
    renderer = _create_headless_renderer(monkeypatch, recorded)

    enemies = [
        (BatEnemy(100, 100), constants.COLOR_BAT_BODY),
        (FlutterEnemy(150, 100), constants.COLOR_FLUTTER_BODY),
        (BindlingEnemy(200, 100), constants.COLOR_BINDLING_PARCHMENT),
        (SmearEnemy(250, 100), constants.COLOR_SMEAR_BLOB),
        (Miniboss(300, 100), constants.COLOR_BOSS_ARMOR),
    ]

    for enemy, expected_color in enemies:
        recorded.clear()
        renderer.draw_actor_ghost(enemy, 0, 0, None)
        colors_drawn = [call[1] for call in recorded]
        assert expected_color in colors_drawn, f"Expected {expected_color} for {enemy.name}"
        assert len(recorded) >= 4


def test_procedural_enemy_telegraph_color_override(monkeypatch):
    """Verify WIND_UP and STRIKE states override procedural enemy primary colors."""
    recorded = []
    renderer = _create_headless_renderer(monkeypatch, recorded)

    bat = BatEnemy(100, 100)
    bat.state = ActorState.STRIKE
    bat.combat_timer = 0.1

    renderer.draw_actor_ghost(bat, 0, 0, None)
    colors_drawn = [call[1] for call in recorded]
    assert constants.COLOR_MARGIN_RED in colors_drawn


def test_procedural_enemy_unknown_fallback(monkeypatch):
    """Verify unknown actors return False from draw_procedural_enemy and fall back to rect."""
    recorded = []
    renderer = _create_headless_renderer(monkeypatch, recorded)

    unknown = Actor(50, 50, 32, 32, 10, name="MysteryCube")
    rect = pygame.Rect(50, 50, 32, 32)
    handled = renderer.draw_procedural_enemy(unknown, rect, unknown.get_visual_packet(), (100, 100, 100))
    assert handled is False


def test_procedural_player_and_weapons(monkeypatch):
    """Verify Scholar player rendering, attack slash arc, and boss tapered greatblade."""
    recorded = []
    renderer = _create_headless_renderer(monkeypatch, recorded)

    player = Player(200, 200)
    # 1. Idle Scholar renders cloak, mantle, hood, eyes, and side-carried sword
    renderer.draw_actor_ghost(player, 0, 0, None)
    colors_drawn = [call[1] for call in recorded]
    assert constants.COLOR_PLAYER_CLOAK in colors_drawn
    assert constants.COLOR_PLAYER_MANTLE in colors_drawn
    assert constants.COLOR_PLAYER_HOOD in colors_drawn
    assert constants.COLOR_PLAYER_EYE in colors_drawn
    assert constants.COLOR_WEAPON_BLADE in colors_drawn
    assert constants.COLOR_WEAPON_GUARD in colors_drawn

    # 2. Blocking Scholar raises ward shield
    recorded.clear()
    player.state = PlayerStateEnum.BLOCKING
    renderer.draw_actor_ghost(player, 0, 0, None)
    colors_drawn = [call[1] for call in recorded]
    assert constants.COLOR_PLAYER_SHIELD in colors_drawn

    # 3. Player sword slash attack renders slash trail and tapered blade
    recorded.clear()
    player.state = PlayerStateEnum.ATTACKING
    player.attack_timer = constants.SWORD_DURATION * 0.5
    renderer.draw_player_weapon_attack(player, 0, 0)
    colors_drawn = [call[1] for call in recorded]
    assert constants.COLOR_CYAN in colors_drawn
    assert constants.COLOR_WEAPON_BLADE in colors_drawn
    assert constants.COLOR_WEAPON_GUARD in colors_drawn

    # 4. Boss weapon renders tapered steel greatblade with crossguard and fuller
    recorded.clear()
    boss = Miniboss(300, 300)
    boss.state = ActorState.STRIKE
    boss.combat_timer = 0.1
    boss.attack_type = "THRUST"
    renderer.draw_boss_weapon(boss, 0, 0)
    colors_drawn = [call[1] for call in recorded]
    assert constants.COLOR_WEAPON_BLADE in colors_drawn
    assert constants.COLOR_WEAPON_GUARD in colors_drawn
    assert constants.COLOR_WEAPON_FULLER in colors_drawn
