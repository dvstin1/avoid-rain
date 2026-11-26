# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Section 8: Enhanced Death Sequence (Text Bleaching)."""
# pylint: disable=no-member,too-many-locals

import os

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from rendering.renderer import Renderer


def _ensure_pygame():
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def _pixel_chroma(color) -> int:
    """Return RGB chroma (max - min channel) as a simple saturation metric."""
    return max(color.r, color.g, color.b) - min(color.r, color.g, color.b)


def test_death_bleach_progress_saturation_and_camera_pullback_math():
    """Verify decoupled compute_death_bleach_state curves from 0.0 -> 1.0 and inactive baseline."""
    dur = constants.DEATH_SCREEN_DURATION

    # Inactive states (normal play or negative clamp)
    for rem in (0.0, -0.5):
        inactive = constants.compute_death_bleach_state(rem, dur)
        assert inactive["active"] is False
        assert inactive["progress"] == 0.0
        assert inactive["desaturation"] == 0.0
        assert inactive["wash_alpha"] == 0
        assert inactive["vignette_alpha"] == 0
        assert inactive["camera_scale"] == pytest.approx(1.0)
        assert inactive["text_alpha"] == 0
        assert inactive["subtitle_alpha"] == 0

    # Sample across 0.0 -> 1.0 normalized progress
    onset = constants.compute_death_bleach_state(dur, dur)
    early = constants.compute_death_bleach_state(dur * 0.78, dur)   # progress = 0.22
    mid = constants.compute_death_bleach_state(dur * 0.50, dur)     # progress = 0.50
    late = constants.compute_death_bleach_state(dur * 0.15, dur)    # progress = 0.85
    end = constants.compute_death_bleach_state(1e-6, dur)           # progress ~ 1.00

    assert onset["active"] is True
    assert onset["progress"] == pytest.approx(0.0, abs=1e-6)
    assert onset["desaturation"] == pytest.approx(0.0, abs=1e-6)
    assert onset["camera_scale"] == pytest.approx(1.0, abs=1e-6)
    assert onset["text_alpha"] == 0
    assert onset["subtitle_alpha"] == 0

    # Monotonic saturation drop & parchment washout
    assert 0.0 < early["desaturation"] < mid["desaturation"] < late["desaturation"] <= 1.0
    assert late["desaturation"] == pytest.approx(1.0, abs=1e-4)
    assert onset["wash_alpha"] <= early["wash_alpha"] < mid["wash_alpha"] < late["wash_alpha"]
    assert end["wash_alpha"] == constants.DEATH_BLEACH_WASH_MAX_ALPHA

    # Monotonic camera pull-back (1.0 -> 1.0 - DEATH_BLEACH_CAMERA_PULLBACK_MAX)
    min_scale = 1.0 - constants.DEATH_BLEACH_CAMERA_PULLBACK_MAX
    assert onset["camera_scale"] > early["camera_scale"] > mid["camera_scale"] > late["camera_scale"] >= min_scale
    assert end["camera_scale"] == pytest.approx(min_scale, abs=1e-4)

    # Staged typographic fade-in & upward settle drift
    assert 0 < early["text_alpha"] < 255
    assert mid["text_alpha"] == 255
    assert mid["text_offset_y"] == pytest.approx(0.0, abs=1e-4)
    assert early["text_offset_y"] > 0.0
    assert early["subtitle_alpha"] == 0
    assert 0 < mid["subtitle_alpha"] < late["subtitle_alpha"] <= 255
    assert late["subtitle_alpha"] == 255


def test_gamestate_dt_driven_death_bleach_lifecycle():
    """GameState advances death_bleach_progress smoothly via dt and resets cleanly on respawn."""
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        assert state.get_death_bleach_state()["active"] is False
        assert state.death_bleach_progress == 0.0

        # Trigger death
        state.player.hp = 0
        state.update(0.25, {"move": (0, 0)})
        b1 = state.get_death_bleach_state()
        assert b1["active"] is True
        assert 0.0 < b1["progress"] < 0.2
        assert b1["camera_scale"] < 1.0

        # Advance further by dt
        state.update(2.0, {"move": (0, 0)})
        b2 = state.get_death_bleach_state()
        assert b2["progress"] > b1["progress"]
        assert b2["desaturation"] > b1["desaturation"]
        assert b2["camera_scale"] < b1["camera_scale"]

        # Complete death sequence -> respawn resets bleaching state
        state.update(constants.DEATH_SCREEN_DURATION, {"move": (0, 0)})
        b_done = state.get_death_bleach_state()
        assert state.death_timer == 0.0
        assert b_done["active"] is False
        assert b_done["camera_scale"] == pytest.approx(1.0)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_headless_death_bleaching_rendering_saturation_drop_and_normal_play():
    """Verify headless rendering drops saturation, pulls back framing during death, and is a no-op in normal play."""
    _ensure_pygame()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        # 1. Normal play (death_timer == 0): draw_death_bleaching_sequence is a pure no-op
        vivid_color = (20, 220, 60)
        screen.fill(vivid_color)
        before_bytes = pygame.image.tobytes(screen, "RGBA")
        assert renderer.draw_death_bleaching_sequence(state) is None
        assert pygame.image.tobytes(screen, "RGBA") == before_bytes

        # 2. Direct saturation drop & camera pull-back check on a vivid surface
        state.death_timer = constants.DEATH_SCREEN_DURATION * 0.85  # early
        screen.fill(vivid_color)
        b_early = renderer.draw_death_bleaching_sequence(state)
        assert b_early is not None and b_early["active"] is True
        early_sample = screen.get_at((constants.SCREEN_WIDTH // 4, constants.SCREEN_HEIGHT // 4))

        state.death_timer = constants.DEATH_SCREEN_DURATION * 0.15  # late (full desat + strong pullback)
        screen.fill(vivid_color)
        b_late = renderer.draw_death_bleaching_sequence(state)
        assert b_late is not None and b_late["active"] is True
        late_sample = screen.get_at((constants.SCREEN_WIDTH // 4, constants.SCREEN_HEIGHT // 4))
        corner_sample = screen.get_at((2, 2))

        # Vivid green chroma (200) drops progressively toward monochrome/bleached parchment
        assert _pixel_chroma(early_sample) < 200
        assert _pixel_chroma(late_sample) < _pixel_chroma(early_sample)
        # Pulled-back outer corner is now manuscript margin + washout (not vivid green!)
        assert _pixel_chroma(corner_sample) < 40

        # 3. Full headless Renderer.render() sweep across normal play and early/mid/late death stages
        state.death_timer = 0.0
        renderer.render(state)
        normal_bytes = pygame.image.tobytes(screen, "RGBA")

        stage_bytes = []
        for frac in (0.90, 0.55, 0.12):
            state.death_timer = constants.DEATH_SCREEN_DURATION * frac
            renderer.render(state)
            stage_bytes.append(pygame.image.tobytes(screen, "RGBA"))

        assert stage_bytes[0] != normal_bytes
        assert stage_bytes[0] != stage_bytes[1]
        assert stage_bytes[1] != stage_bytes[2]
    finally:
        state.shutdown_save_worker(timeout=1.0)
