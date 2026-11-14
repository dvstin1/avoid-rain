"""Unit tests for procedural basic-shape enemy, player, and weapon graphics in the Renderer."""
# pylint: disable=no-member
import pygame
import constants
from rendering.renderer import Renderer
from engine.enemy import (
    BatEnemy,
    FlutterEnemy,
    BindlingEnemy,
    SmearEnemy,
    Miniboss,
    NightBoss,
    FinalAuthor,
    SentryEnemy,
)
from engine.actor import Actor, ActorState
from engine.player import Player, PlayerStateEnum
from engine.maps import create_world


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
    """Verify Act 1 base enemy PNGs and Act 2 empowered PNGs render cleanly with distinct sprites."""
    recorded = []
    renderer = _create_headless_renderer(monkeypatch, recorded)

    act1_expected = [
        (BatEnemy(100, 100), "bat.png", (40, 40)),
        (FlutterEnemy(150, 100), "flutter.png", (40, 40)),
        (BindlingEnemy(200, 100), "bindling.png", (40, 40)),
        (SmearEnemy(250, 100), "smear.png", (40, 40)),
        (Miniboss(300, 100), "miniboss.png", (40, 40)),
        (NightBoss(350, 100), "night_boss.png", (64, 64)),
        (FinalAuthor(400, 100), "final_author.png", (80, 80)),
    ]

    for enemy, expected_key, expected_size in act1_expected:
        assert expected_key in renderer.image_cache, f"{expected_key} missing from image_cache"
        assert renderer.image_cache[expected_key].get_size() == expected_size
        rect = pygame.Rect(int(enemy.x), int(enemy.y), enemy.width, enemy.height)
        handled = renderer.draw_procedural_enemy(enemy, rect, enemy.get_visual_packet(), (100, 100, 100))
        assert handled is True

    # Act 2 empowered variants remain distinct from Act 1 base sprites
    act2_bat = BatEnemy(100, 100)
    act2_bat.is_empowered = True
    assert pygame.image.tobytes(renderer.image_cache["bat.png"], "RGBA") != pygame.image.tobytes(
        renderer.image_cache["bat_empowered.png"], "RGBA"
    )
    assert renderer.draw_procedural_enemy(
        act2_bat, pygame.Rect(100, 100, 40, 40), act2_bat.get_visual_packet(), (100, 100, 100)
    )

    # Sentry remains procedural in Act 1
    recorded.clear()
    sentry = SentryEnemy(450, 100)
    renderer.draw_actor_ghost(sentry, 0, 0, None)
    colors_drawn = [call[1] for call in recorded]
    assert constants.COLOR_SENTRY_CHASSIS in colors_drawn


def test_procedural_enemy_telegraph_color_override(monkeypatch):
    """Verify WIND_UP and STRIKE states draw telegraph highlight borders over enemy sprites."""
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


def test_biome_tile_generation_and_new_maps(monkeypatch):
    """Verify procedural biome wall/floor surfaces and new level-design maps."""
    recorded = []
    renderer = _create_headless_renderer(monkeypatch, recorded)

    for biome in ("windy_ridge", "pastoral_valley", "swamp_mire", "frozen_peaks", "tech_tower", "sanctuary"):
        assert biome in renderer.biome_tiles
        pack = renderer.biome_tiles[biome]
        assert len(pack["floors"]) == 4
        assert len(pack["strata_floors"]) == 3
        # Verify the 3 strata have distinct base colors so floors are non-uniform
        s0_col = pack["strata_floors"][0][0].get_at((1, 1))[:3]
        s1_col = pack["strata_floors"][1][0].get_at((1, 1))[:3]
        s2_col = pack["strata_floors"][2][0].get_at((1, 1))[:3]
        assert len({s0_col, s1_col, s2_col}) == 3
        assert pack["wall_cap"].get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)
        assert pack["wall_front"].get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)
        assert s1_col == constants.BIOME_PALETTES[biome]["floor_base"]

    for map_name in ("windy_ridge", "pastoral_valley", "swamp_mire", "frozen_peaks", "tech_tower"):
        world = create_world(map_name)
        assert len(world.grid) == 120
        assert len(world.grid[0]) == 120
        assert len(world.enemies) >= 12
        assert any(isinstance(e, SentryEnemy) for e in world.enemies)
        respites = [obj for obj in world.interactables if "Respite" in obj.name]
        assert len(respites) == 1 and respites[0].gated_by_miniboss_id is not None


def test_sentry_enemy_behavior_and_graphics(monkeypatch):
    """Verify SentryEnemy artillery spacing, beam hitbox, and procedural rendering."""
    recorded = []
    renderer = _create_headless_renderer(monkeypatch, recorded)

    sentry = SentryEnemy(200, 200)
    sentry.facing = (1.0, 0.0)
    hb = sentry.get_attack_hitbox()
    assert hb[2] == constants.SENTRY_BEAM_RANGE
    assert hb[3] == constants.SENTRY_BEAM_WIDTH

    draw_rect = pygame.Rect(200, 200, sentry.width, sentry.height)
    packet = sentry.get_visual_packet()
    assert renderer.draw_procedural_enemy(sentry, draw_rect, packet, (48, 62, 88)) is True
    colors = [call[1] for call in recorded]
    assert constants.COLOR_SENTRY_CHASSIS in colors
    assert constants.COLOR_SENTRY_RING in colors
    assert constants.COLOR_SENTRY_EYE in colors

    recorded.clear()
    sentry.state = ActorState.STRIKE
    sentry.combat_timer = 0.1
    renderer.draw_boss_weapon(sentry, 0, 0)
    beam_colors = [call[1] for call in recorded]
    assert constants.COLOR_SENTRY_BEAM in beam_colors
    assert constants.COLOR_WHITE in beam_colors

