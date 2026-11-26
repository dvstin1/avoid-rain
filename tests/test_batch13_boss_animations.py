# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Batch 13: Boss Sprite Redesign & 3-Frame Directional Boss Animations.

Covers the 4 redesigned canonical boss sprites (night_boss, boss_empowered, miniboss,
final_author), 3-frame down/up/side directional sprites & preloading across all 7 bosses,
Renderer._resolve_boss_directional_sprite() facing/cadence selection, and zero double-flip
on left-facing bosses across draw_procedural_enemy() and specialized boss renderers.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.enemy import (
    FinalAuthor,
    MeadowCensorBoss,
    Miniboss,
    NightBoss,
    RimecrestArbiterBoss,
    SlugBoss,
)
from generate_assets import (
    generate_boss_empowered_sprite,
    generate_final_author_sprite,
    generate_miniboss_sprite,
    generate_night_boss_sprite,
)
from rendering.renderer import Renderer


BOSS_SPECS = (
    ("miniboss", (40, 40)),
    ("night_boss", (64, 64)),
    ("final_author", (80, 80)),
    ("boss_empowered", (64, 64)),
    ("slug_boss", (112, 112)),
    ("meadow_censor_boss", (104, 104)),
    ("rimecrest_arbiter_boss", (104, 104)),
)


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_redesigned_primitive_bosses_have_rich_non_primitive_detail():
    """Verify redesigned night_boss, boss_empowered, miniboss, and final_author match sizes & rich detail."""
    generators = (
        ("miniboss.png", generate_miniboss_sprite, (40, 40)),
        ("night_boss.png", generate_night_boss_sprite, (64, 64)),
        ("final_author.png", generate_final_author_sprite, (80, 80)),
        ("boss_empowered.png", generate_boss_empowered_sprite, (64, 64)),
    )
    for fname, gen_fn, expected_size in generators:
        fpath = os.path.join("assets", "graphics", fname)
        assert os.path.exists(fpath), f"Missing redesigned boss sprite: {fpath}"
        disk_surf = pygame.image.load(fpath)
        assert disk_surf.get_size() == expected_size

        surf = gen_fn(*expected_size, direction="down", frame=0)
        assert surf.get_size() == expected_size
        assert surf.get_flags() & pygame.SRCALPHA != 0
        assert surf.get_at((0, 0)).a == 0

        opaque_colors = {
            surf.get_at((x, y))[:3]
            for y in range(expected_size[1])
            for x in range(expected_size[0])
            if surf.get_at((x, y)).a > 200
        }
        assert len(opaque_colors) >= 12, f"{fname} expected rich color palette, got {len(opaque_colors)}"


def test_all_seven_bosses_have_nine_distinct_directional_frames_and_preload():
    """Verify all 7 bosses emit down(0..2)/up(0..2)/side(0..2) PNGs at exact sizes and preload in Renderer."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    for stem, expected_size in BOSS_SPECS:
        expected_files = (
            f"{stem}.png",
            f"{stem}_1.png",
            f"{stem}_2.png",
            f"{stem}_up_0.png",
            f"{stem}_up_1.png",
            f"{stem}_up_2.png",
            f"{stem}_side_0.png",
            f"{stem}_side_1.png",
            f"{stem}_side_2.png",
        )
        fingerprints = set()
        for fname in expected_files:
            fpath = os.path.join("assets", "graphics", fname)
            assert os.path.exists(fpath), f"Missing directional boss sprite: {fpath}"
            surf = pygame.image.load(fpath)
            assert surf.get_size() == expected_size, f"{fname} size {surf.get_size()} != {expected_size}"
            assert fname in renderer.image_cache, f"{fname} not preloaded in image_cache"
            assert renderer.image_cache[fname].get_size() == expected_size
            fingerprints.add(pygame.image.tobytes(renderer.image_cache[fname], "RGBA"))

        # All 3 directions and 3 stride frames should produce distinct visuals
        assert len(fingerprints) == 9, f"Expected 9 unique frames for {stem}, got {len(fingerprints)}"


def test_resolve_boss_directional_sprite_directions_cadence_and_flip():
    """Verify _resolve_boss_directional_sprite selects up/down/side, flips left, and cycles [0,1,2,1]."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    s_down = renderer._resolve_boss_directional_sprite("night_boss", (0.0, 1.0), 0.01, False)
    s_up = renderer._resolve_boss_directional_sprite("night_boss", (0.0, -1.0), 0.01, False)
    s_right = renderer._resolve_boss_directional_sprite("night_boss", (1.0, 0.0), 0.01, False)
    s_left = renderer._resolve_boss_directional_sprite("night_boss", (-1.0, 0.0), 0.01, False)

    assert s_down is renderer.image_cache["night_boss.png"]
    assert s_up is renderer.image_cache["night_boss_up_0.png"]
    assert s_right is renderer.image_cache["night_boss_side_0.png"]
    assert s_left is not None and s_left is not s_right
    assert pygame.image.tobytes(s_left, "RGBA") == pygame.image.tobytes(
        pygame.transform.flip(s_right, True, False), "RGBA"
    )

    # Ping-pong [0, 1, 2, 1] cycle when moving (6.5 Hz) vs slower idle (2.5 Hz)
    move_seq = [
        renderer._resolve_boss_directional_sprite("final_author", (0.0, 1.0), step / 6.5 + 0.01, True)
        for step in range(4)
    ]
    assert move_seq == [
        renderer.image_cache["final_author.png"],
        renderer.image_cache["final_author_1.png"],
        renderer.image_cache["final_author_2.png"],
        renderer.image_cache["final_author_1.png"],
    ]

    # At t=0.20s: moving (6.5 Hz -> step 1 -> frame 1) advances ahead of idle (2.5 Hz -> step 0 -> frame 0)
    assert renderer._resolve_boss_directional_sprite("final_author", (0.0, 1.0), 0.20, False) is renderer.image_cache[
        "final_author.png"
    ]
    assert renderer._resolve_boss_directional_sprite("final_author", (0.0, 1.0), 0.20, True) is renderer.image_cache[
        "final_author_1.png"
    ]


def test_boss_callers_render_left_facing_without_double_flip():
    """Verify draw_procedural_enemy and specialized boss renderers do not double-flip left-facing side sprites."""
    canvas = pygame.Surface((200, 200))
    renderer = Renderer(canvas)

    def _make_marker_side(size):
        """Asymmetrical sentinel: bright red block on RIGHT half (x >= w/2), blue block on LEFT half."""
        w, h = size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (30, 80, 240, 255), (0, 0, w // 2, h))
        pygame.draw.rect(s, (240, 30, 40, 255), (w // 2, 0, w - w // 2, h))
        return s

    cases = [
        ("miniboss", (40, 40), Miniboss(40, 40), False),
        ("night_boss", (64, 64), NightBoss(40, 40), False),
        ("final_author", (80, 80), FinalAuthor(40, 40), False),
        ("boss_empowered", (64, 64), NightBoss(40, 40), True),
        ("slug_boss", (112, 112), SlugBoss(40, 40), False),
        ("meadow_censor_boss", (104, 104), MeadowCensorBoss(40, 40), False),
        ("rimecrest_arbiter_boss", (104, 104), RimecrestArbiterBoss(40, 40), False),
    ]

    for stem, size, actor, is_emp in cases:
        actor.is_empowered = is_emp
        renderer.image_cache[f"{stem}_side_0.png"] = _make_marker_side(size)
        renderer._fx_surface_cache.clear()
        w, h = size
        rect = pygame.Rect(40, 40, w, h)
        packet = {"facing": (-1.0, 0.0), "base": "IDLE", "posture": "NORMAL", "anim_timer": 0.01}

        canvas.fill((0, 0, 0))
        handled = renderer.draw_procedural_enemy(actor, rect, packet, (120, 120, 120))
        assert handled is True

        # Because fx=-1 flips side_0 ONCE, the red half (originally right) must now appear on the LEFT side!
        left_px = canvas.get_at((40 + w // 4, 40 + h // 2))[:3]
        right_px = canvas.get_at((40 + (3 * w) // 4, 40 + h // 2))[:3]
        assert left_px[0] > 200 and left_px[2] < 80, f"{stem} left half should be red (flipped once), got {left_px}"
        assert right_px[2] > 200 and right_px[0] < 80, f"{stem} right half should be blue (flipped once), got {right_px}"
