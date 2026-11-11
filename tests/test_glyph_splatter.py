"""Unit tests for the Glyph Splatter particle system."""
# pylint: disable=no-member,too-few-public-methods,missing-function-docstring,missing-class-docstring
import pygame
from constants import (
    GLYPH_SPLATTER_POOL,
    GLYPH_MIN_COUNT,
    GLYPH_MAX_COUNT,
    GLYPH_MIN_LIFESPAN_FRAMES,
    GLYPH_MAX_LIFESPAN_FRAMES,
    COLOR_PARCHMENT_WHITE,
    COLOR_INK_CHARCOAL,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)
from engine.particles import GlyphSplatterManager, GlyphParticle
from engine.game_state import GameState
from engine.enemy import SlugEnemy
from engine.player import PlayerStateEnum
from rendering.renderer import Renderer


def test_glyph_particle_physics_and_fade():
    """Verify GlyphParticle updates position, applies gravity/friction, and fades alpha."""
    p = GlyphParticle(
        x=100.0,
        y=100.0,
        glyph="†",
        vx=2.0,
        vy=-3.0,
        lifespan_frames=20,
        color=COLOR_INK_CHARCOAL,
    )
    assert p.glyph in GLYPH_SPLATTER_POOL
    assert p.alpha == 255  # Full alpha during first 50%

    # Advance 10 frames (50% lifespan at 60fps: dt = 10/60)
    alive = p.update(10.0 / 60.0)
    assert alive is True
    assert p.vx < 2.0  # Slowed down by air friction
    assert p.vy > -3.0  # Pulled down by gravity
    assert p.alpha == 255

    # Advance 5 frames (remaining 5 frames -> 50% of the second half, alpha ~ 127)
    alive = p.update(5.0 / 60.0)
    assert alive is True
    assert 110 <= p.alpha <= 140

    # Advance beyond max lifespan
    alive = p.update(10.0 / 60.0)
    assert alive is False
    assert p.alpha == 0


def test_glyph_splatter_manager_burst():
    """Verify manager emits between 4 and 7 particles with appropriate bounds."""
    manager = GlyphSplatterManager()
    manager.spawn_burst(200.0, 150.0)
    assert GLYPH_MIN_COUNT <= len(manager.particles) <= GLYPH_MAX_COUNT

    for p in manager.particles:
        assert p.glyph in GLYPH_SPLATTER_POOL
        assert -2.5 <= p.vx <= 2.5
        assert -4.0 <= p.vy <= -1.5
        assert GLYPH_MIN_LIFESPAN_FRAMES <= p.max_lifespan <= GLYPH_MAX_LIFESPAN_FRAMES

    # After running for 1.0 second, all particles should expire
    manager.update(1.0)
    assert len(manager.particles) == 0


def test_glyph_splatter_triggered_on_combat_hit():
    """Verify glyph particles spawn when hitting an enemy and when player takes damage."""
    state = GameState(auto_load=False)
    # Position enemy within the sword hitbox (sword reaches cx + SWORD_OFFSET to cx + SWORD_OFFSET + SWORD_WIDTH)
    slug = SlugEnemy(state.player.x + 50, state.player.y)
    state.enemies = [slug]

    assert len(state.glyph_particles.particles) == 0

    # 1. Player attacks and hits slug
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.facing = (1, 0)
    state.update_combat(0.016, attack_pressed=False, actions={}, audio_manager=None)

    assert len(state.glyph_particles.particles) >= GLYPH_MIN_COUNT
    enemy_particles = list(state.glyph_particles.particles)
    for p in enemy_particles:
        assert p.color == COLOR_INK_CHARCOAL

    state.glyph_particles.clear()

    # 2. Player takes damage from enemy attack
    state.player.take_damage(10.0, bypass_stagger=False, audio_manager=None, game_state=state)
    assert len(state.glyph_particles.particles) >= GLYPH_MIN_COUNT
    for p in state.glyph_particles.particles:
        assert p.color == COLOR_PARCHMENT_WHITE

    state.shutdown_save_worker(timeout=1.0)


def test_renderer_draw_glyph_splatter(monkeypatch):
    """Verify Renderer renders glyph particles without errors."""
    state = GameState(auto_load=False)
    state.glyph_particles.spawn_burst(400.0, 300.0)

    class DummyScreen:
        def get_width(self):
            return SCREEN_WIDTH
        def get_height(self):
            return SCREEN_HEIGHT
        def fill(self, _color):
            pass
        def blit(self, _surf, _pos):
            pass

    class DummyFont:
        def render(self, _text, _aa, _color=None):
            return pygame.Surface((12, 12), pygame.SRCALPHA)

    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: DummyFont())
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)

    renderer = Renderer(DummyScreen())
    renderer.draw_glyph_splatter(state, ox=0, oy=0)
    state.shutdown_save_worker(timeout=1.0)
