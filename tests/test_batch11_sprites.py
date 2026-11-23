"""Unit tests for Batch 11: Enemy & Boss Sprite Polish.

Covers 3-frame FlutterEnemy wing-flap animation (base & empowered frames 0..2, preloading,
ping-pong [0, 1, 2, 1] cycling across animation_timer, faster chase cadence, and hover bob)
plus organic asymmetrical SlugBoss (3 blades, curled tail, plum velvet crown trim) and
softened antique-gold crown outline contrast on both slug_boss.png and slug_boss_crown.png.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import math
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.enemy import FlutterEnemy, SlugBoss
from generate_assets import (
    generate_flutter_frame,
    generate_slug_boss,
    generate_slug_boss_crown,
)
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_flutter_three_base_and_empowered_frames_exist_distinct_and_preload():
    """Verify all 6 Flutter PNG frames (base 0..2 & empowered 0..2) are 40x40 SRCALPHA, distinct, and preloaded."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    for empowered, keys in (
        (False, ("flutter.png", "flutter_1.png", "flutter_2.png")),
        (True, ("flutter_empowered.png", "flutter_empowered_1.png", "flutter_empowered_2.png")),
    ):
        fingerprints = set()
        for f_idx, fname in enumerate(keys):
            fpath = os.path.join("assets", "graphics", fname)
            assert os.path.exists(fpath), f"Missing flutter frame: {fpath}"
            assert pygame.image.load(fpath).get_size() == (40, 40)
            assert fname in renderer.image_cache
            assert renderer.image_cache[fname].get_size() == (40, 40)

            gen = generate_flutter_frame(frame=f_idx, empowered=empowered)
            assert gen.get_size() == (40, 40)
            assert gen.get_flags() & pygame.SRCALPHA != 0
            assert gen.get_at((0, 0)).a == 0
            fingerprints.add(pygame.image.tobytes(gen, "RGBA"))
        assert len(fingerprints) == 3, f"Expected 3 distinct wing poses for empowered={empowered}"


def test_flutter_animation_cycles_frames_cadence_and_hover_bob():
    """Verify draw_procedural_enemy cycles [0, 1, 2, 1] faster when moving and applies vertical hover bob."""
    # 1. Verify ping-pong sequence [0, 1, 2, 1] and idle vs. moving cadence
    idle_seq = [Renderer._resolve_flutter_sprite_key(step / 5.5 + 0.01, "IDLE", False) for step in range(4)]
    assert idle_seq == ["flutter.png", "flutter_1.png", "flutter_2.png", "flutter_1.png"]

    chase_seq = [Renderer._resolve_flutter_sprite_key(step / 11.0 + 0.01, "CHASE", True) for step in range(4)]
    assert chase_seq == [
        "flutter_empowered.png",
        "flutter_empowered_1.png",
        "flutter_empowered_2.png",
        "flutter_empowered_1.png",
    ]

    # At t=0.12s: moving (11 Hz -> frame 1) advances ahead of idle (5.5 Hz -> frame 0)
    assert Renderer._resolve_flutter_sprite_key(0.12, "IDLE", False) == "flutter.png"
    assert Renderer._resolve_flutter_sprite_key(0.12, "RUN", False) == "flutter_1.png"

    # 2. Verify draw_procedural_enemy blits distinct sentinel colors per frame & applies sinusoidal hover bob
    screen = pygame.Surface((120, 120))
    renderer = Renderer(screen)
    sentinels = {
        "flutter.png": (235, 40, 40),
        "flutter_1.png": (40, 235, 40),
        "flutter_2.png": (40, 90, 235),
    }
    for key, rgb in sentinels.items():
        s = pygame.Surface((40, 40), pygame.SRCALPHA)
        s.fill((*rgb, 255))
        renderer.image_cache[key] = s

    flutter = FlutterEnemy(40.0, 40.0)
    rect = pygame.Rect(40, 40, 40, 40)
    observed_colors = []
    for step in range(3):
        t_val = step / 11.0 + 0.01
        screen.fill((0, 0, 0))
        packet = {"facing": (1.0, 0.0), "base": "CHASE", "posture": "NORMAL", "anim_timer": t_val}
        assert renderer.draw_procedural_enemy(flutter, rect, packet, (100, 100, 100)) is True
        observed_colors.append(screen.get_at((60, 60))[:3])
    assert observed_colors == [
        (235, 40, 40),
        (40, 235, 40),
        (40, 90, 235),
    ]

    # Verify hover bob offsets the top edge vertically between positive and negative sin(anim_t * 7.0)
    t_peak = math.pi / (2.0 * 7.0)  # sin = +1 -> bob_y = +2 -> top at y=42
    t_trough = (3.0 * math.pi) / (2.0 * 7.0)  # sin = -1 -> bob_y = -2 -> top at y=38
    screen.fill((0, 0, 0))
    renderer.draw_procedural_enemy(
        flutter,
        rect,
        {"facing": (1.0, 0.0), "base": "IDLE", "posture": "NORMAL", "anim_timer": t_peak},
        (100, 100, 100),
    )
    assert screen.get_at((60, 40))[:3] == (0, 0, 0)
    assert screen.get_at((60, 43))[:3] != (0, 0, 0)

    screen.fill((0, 0, 0))
    renderer.draw_procedural_enemy(
        flutter,
        rect,
        {"facing": (1.0, 0.0), "base": "IDLE", "posture": "NORMAL", "anim_timer": t_trough},
        (100, 100, 100),
    )
    assert screen.get_at((60, 39))[:3] != (0, 0, 0)


def test_slug_boss_organic_asymmetry_and_soft_crown_contrast():
    """Verify slug_boss.png is organic & asymmetrical with plum velvet trim and softened antique-gold crown edges."""
    boss_path = os.path.join("assets", "graphics", "slug_boss.png")
    assert os.path.exists(boss_path)
    boss = generate_slug_boss(112, 112)
    assert boss.get_size() == (112, 112)
    assert boss.get_flags() & pygame.SRCALPHA != 0
    assert boss.get_at((0, 0)).a == 0

    # Horizontal asymmetry check: comparing left half vs mirrored right half must differ substantially
    asym_pixels = 0
    opaque_pixels = 0
    for y in range(112):
        for x in range(56):
            c_left = boss.get_at((x, y))
            c_right = boss.get_at((111 - x, y))
            if c_left.a > 128 or c_right.a > 128:
                opaque_pixels += 1
                if (c_left.a > 128) != (c_right.a > 128) or (
                    abs(c_left.r - c_right.r) + abs(c_left.g - c_right.g) + abs(c_left.b - c_right.b) > 45
                ):
                    asym_pixels += 1
    assert opaque_pixels > 1000
    assert asym_pixels / opaque_pixels >= 0.30, (
        f"SlugBoss silhouette/blades should be strongly asymmetrical, got {asym_pixels / opaque_pixels:.2%}"
    )

    # Crown region (y=6..30, x=28..72): verify soft antique-gold outline, plum velvet trim, and no harsh dark brown
    soft_outline_px = 0
    plum_velvet_px = 0
    harsh_dark_outline_px = 0
    for y in range(6, 30):
        for x in range(28, 72):
            c = boss.get_at((x, y))
            if c.a < 200:
                continue
            if c[:3] == (176, 140, 56):
                soft_outline_px += 1
            if c[:3] in ((124, 42, 92), (166, 62, 122)):
                plum_velvet_px += 1
            if c[:3] in ((78, 56, 18), (132, 98, 28)):
                harsh_dark_outline_px += 1
    assert soft_outline_px >= 20
    assert plum_velvet_px >= 15
    assert harsh_dark_outline_px == 0


def test_slug_boss_crown_soft_outline_and_fallbacks():
    """Verify slug_boss_crown.png uses softened antique-gold edges and procedural fallbacks render cleanly."""
    crown_path = os.path.join("assets", "graphics", "slug_boss_crown.png")
    assert os.path.exists(crown_path)
    crown = generate_slug_boss_crown(44, 32)
    assert crown.get_size() == (44, 32)
    assert crown.get_at((0, 0)).a == 0
    assert crown.get_at((22, 16)).a == 255

    soft_edges = 0
    warm_highlights = 0
    harsh_brown = 0
    for y in range(32):
        for x in range(44):
            c = crown.get_at((x, y))
            if c.a < 200:
                continue
            if c[:3] == (176, 140, 56):
                soft_edges += 1
            elif c[:3] == (244, 222, 132):
                warm_highlights += 1
            elif c[:3] == (78, 56, 18):
                harsh_brown += 1
    assert soft_edges >= 20
    assert warm_highlights >= 10
    assert harsh_brown == 0

    # Verify procedural fallbacks render when sprites are absent from caches
    canvas = pygame.Surface((160, 160))
    canvas.fill((12, 10, 18))
    renderer = Renderer(canvas)
    renderer.prop_cache.pop("SlugBoss", None)
    renderer.image_cache.pop("slug_boss.png", None)
    renderer.prop_cache.pop("SlugBossCrown", None)
    renderer.image_cache.pop("slug_boss_crown.png", None)

    boss = SlugBoss(20.0, 20.0)
    renderer._draw_slug_boss(
        boss, pygame.Rect(20, 20, 112, 112), {"facing": (1.0, 0.0), "base": "IDLE", "anim_timer": 0.0}
    )
    assert canvas.get_at((76, 76))[:3] != (12, 10, 18)

    canvas.fill((12, 10, 18))
    renderer._draw_slug_boss_crown(40, 40, {})
    assert canvas.get_at((62, 56))[:3] != (12, 10, 18)
