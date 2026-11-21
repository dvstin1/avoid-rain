"""Unit tests for Phase 2 playtest polish: enemy/event sprites, Torn Page illumination, and Sanctuary facades."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member

import os
from types import SimpleNamespace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.actor import ActorState
from engine.enemy import (
    BindlingEnemy,
    FinalAuthor,
    Miniboss,
    MinibossM2,
    MinibossM3,
    NightBoss,
    PunctuationWolfEnemy,
    SentryEnemy,
    SlugEnemy,
)
from engine.loot import TornPage
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize pygame in headless mode for Phase 2 graphic tests."""
    pygame.init()
    yield
    pygame.quit()


def test_phase2_png_assets_exist_and_preload():
    """All 6 new Phase 2 PNGs exist on disk at 40x40 and preload into Renderer caches."""
    expected_files = (
        "torn_page.png",
        "sentry.png",
        "punctuation_wolf.png",
        "event_champion.png",
        "sanctuary_window_wall.png",
        "sanctuary_arch_doorway.png",
    )
    for fname in expected_files:
        path = os.path.join("assets", "graphics", fname)
        assert os.path.exists(path), f"Missing generated asset: {path}"
        loaded = pygame.image.load(path)
        assert loaded.get_size() == (40, 40)

    screen = pygame.Surface((800, 600))
    renderer = Renderer(screen)
    for fname in expected_files:
        assert fname in renderer.image_cache, f"{fname} not preloaded in image_cache"
    assert "TornPage" in renderer.prop_cache
    assert "SanctuaryWindowWall" in renderer.prop_cache
    assert "SanctuaryArchDoorway" in renderer.prop_cache


def test_torn_page_renders_with_pulsing_aura_without_white_square(monkeypatch):
    """TornPage draws a pulsing golden-amber glow + torn_page.png (or parchment fallback), never a white square."""
    screen = pygame.Surface((400, 400))
    renderer = Renderer(screen)
    page = TornPage(120, 140)

    rect_calls = []
    circle_calls = []
    orig_rect = pygame.draw.rect
    orig_circle = pygame.draw.circle

    def _spy_rect(surf, col, rect, *args, **kwargs):
        if surf is screen:
            rect_calls.append((tuple(col), tuple(rect)))
        return orig_rect(surf, col, rect, *args, **kwargs)

    def _spy_circle(surf, col, pos, radius, *args, **kwargs):
        if surf is screen:
            circle_calls.append((tuple(col), tuple(pos), radius))
        return orig_circle(surf, col, pos, radius, *args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", _spy_rect)
    monkeypatch.setattr(pygame.draw, "circle", _spy_circle)

    renderer.draw_loot(page, 0, 0)
    assert not any(col[:3] == constants.COLOR_WHITE for col, _ in rect_calls)
    assert circle_calls, "Expected pulsing golden-amber aura circle around TornPage"

    # Also verify fallback when torn_page.png is absent still avoids drawing a flat white square
    rect_calls.clear()
    circle_calls.clear()
    renderer.image_cache.pop("torn_page.png", None)
    renderer.prop_cache.pop("TornPage", None)
    renderer.draw_loot(page, 0, 0)
    assert not any(col[:3] == constants.COLOR_WHITE for col, _ in rect_calls)
    assert circle_calls


def test_event_enemies_and_act1_enemies_resolve_to_sprites_without_colored_squares(monkeypatch):
    """Marginalia event enemies and Act 1 Sentry/Wolf resolve to sprites instead of flat colored squares."""
    screen = pygame.Surface((800, 600))
    renderer = Renderer(screen)
    state = SimpleNamespace(debug_text_enabled=False)

    overwritten = MinibossM2(120, 120)
    overwritten.name = "Overwritten Elite"

    emp_champ = MinibossM2(200, 120)
    emp_champ.name = "Empowered Champion"
    emp_champ.is_empowered = True

    censor = MinibossM2(280, 120)
    censor.name = "The Relentless Censor"

    slug_mimic = SlugEnemy(360, 120)
    slug_mimic.name = "Barrel Mimic"

    bindling_mimic = BindlingEnemy(420, 120)
    bindling_mimic.name = "Barrel Mimic"

    sentry = SentryEnemy(480, 120)
    wolf = PunctuationWolfEnemy(540, 120)

    rect_draws_on_screen = []
    orig_rect = pygame.draw.rect

    def _spy_rect(surf, col, rect, *args, **kwargs):
        if surf is screen:
            rect_draws_on_screen.append((tuple(col), tuple(rect), args))
        return orig_rect(surf, col, rect, *args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", _spy_rect)

    for enemy in (overwritten, emp_champ, censor, bindling_mimic, sentry, wolf):
        draw_rect = pygame.Rect(int(enemy.x), int(enemy.y), enemy.width, enemy.height)
        assert renderer.draw_procedural_enemy(enemy, draw_rect, enemy.get_visual_packet(), (200, 50, 50)) is True

    # Full draw_actor_ghost should not fall back to a flat solid rect on screen for any of these actors
    rect_draws_on_screen.clear()
    for enemy in (overwritten, emp_champ, censor, slug_mimic, bindling_mimic, sentry, wolf):
        renderer.draw_actor_ghost(enemy, 0, 0, state)
    assert not rect_draws_on_screen, f"Unexpected fallback rect draws: {rect_draws_on_screen}"


def test_boss_combat_states_draw_circular_telegraph_not_box_outline(monkeypatch):
    """Bosses in WIND_UP, STRIKE, and RECOVERY draw circular telegraph rings with zero rectangular box borders."""
    screen = pygame.Surface((800, 600))
    renderer = Renderer(screen)
    state = SimpleNamespace(debug_text_enabled=False)

    bosses = (
        Miniboss(150, 150),
        MinibossM2(250, 150),
        MinibossM3(350, 150),
        NightBoss(450, 150),
        FinalAuthor(550, 150),
    )

    rect_calls = []
    circle_calls = []
    orig_rect = pygame.draw.rect
    orig_circle = pygame.draw.circle

    def _spy_rect(surf, col, rect, *args, **kwargs):
        if surf is screen:
            rect_calls.append((tuple(col), tuple(rect), args))
        return orig_rect(surf, col, rect, *args, **kwargs)

    def _spy_circle(surf, col, pos, radius, *args, **kwargs):
        if surf is screen:
            circle_calls.append((tuple(col), tuple(pos), radius))
        return orig_circle(surf, col, pos, radius, *args, **kwargs)

    monkeypatch.setattr(pygame.draw, "rect", _spy_rect)
    monkeypatch.setattr(pygame.draw, "circle", _spy_circle)

    for boss in bosses:
        for combat_state in (ActorState.WIND_UP, ActorState.STRIKE, ActorState.RECOVERY):
            boss.state = combat_state
            boss.combat_timer = 0.15
            rect_calls.clear()
            circle_calls.clear()
            draw_rect = pygame.Rect(int(boss.x), int(boss.y), boss.width, boss.height)
            assert renderer.draw_procedural_enemy(boss, draw_rect, boss.get_visual_packet(), (200, 100, 0)) is True
            assert not rect_calls, f"Boss {boss.name} in {combat_state} drew rectangular border: {rect_calls}"
            assert circle_calls, f"Boss {boss.name} in {combat_state} missing circular telegraph ring"
            # Full ghost render (excluding debug-only boxes)
            rect_calls.clear()
            renderer.draw_actor_ghost(boss, 0, 0, state)
            # Only small weapon/cooldown bars might draw thin rects; never a boss-sized box outline
            boss_box_rects = [
                r for _, r, _ in rect_calls if r[2] >= boss.width - 2 and r[3] >= boss.height - 2
            ]
            assert not boss_box_rects, f"Boss {boss.name} drew body-sized rect box: {boss_box_rects}"
