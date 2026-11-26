# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Pass 1: Sanctuary Visual Assets & Ground Texture Polish.

Verifies the 12 low-contrast Sanctuary floor tile variants (flagstone, dirt path, wood floor),
the 7 Sanctuary courtyard/pond/roof/prop sprites, Renderer preloading & graceful fallback, and
deterministic coordinate-hashed Sanctuary floor rendering.
"""
# pylint: disable=no-member,protected-access

import os

import pygame

import constants
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from rendering.renderer import Renderer


FLOOR_FAMILIES = (
    ("sanctuary_flagstone", "sanctuary_flagstone_variants", (66, 61, 55)),
    ("sanctuary_dirt_path", "sanctuary_dirt_path_variants", (82, 66, 50)),
    ("sanctuary_wood_floor", "sanctuary_wood_floor_variants", (78, 57, 41)),
)

SANCTUARY_PROP_SPECS = (
    ("sanctuary_roof_tile.png", "SanctuaryRoofTile", (40, 40), False),
    ("sanctuary_chimney.png", "SanctuaryChimney", (40, 80), True),
    ("sanctuary_tree_canopy.png", "SanctuaryTreeCanopy", (80, 100), True),
    ("pond_lily_reeds.png", "PondLilyReeds", (40, 40), True),
    ("garden_flora.png", "GardenFlora", (40, 40), True),
    ("locked_shed_door.png", "LockedShedDoor", (40, 40), True),
    ("mossy_gravestone.png", "MossyGravestone", (40, 40), True),
)


def test_sanctuary_low_contrast_floor_variants_exist_and_bounded():
    """Verify all 12 Sanctuary floor variant PNGs exist, are 40x40 opaque, distinct, and <= +-12 RGB delta."""
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    for prefix, attr_name, base_rgb in FLOOR_FAMILIES:
        loaded = getattr(renderer, attr_name)
        assert len(loaded) == 4, f"Expected 4 preloaded variants in renderer.{attr_name}"
        fingerprints = set()

        for idx in range(4):
            fpath = os.path.join("assets", "graphics", f"{prefix}_{idx}.png")
            assert os.path.exists(fpath), f"Missing Sanctuary floor variant: {fpath}"
            surf = loaded[idx]
            assert surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)

            # Check opacity and <= +-12 RGB contrast delta across the tile
            for py in range(0, constants.TILE_SIZE, 2):
                for px in range(0, constants.TILE_SIZE, 2):
                    col = surf.get_at((px, py))
                    assert col.a == 255, f"{fpath} has non-opaque pixel at ({px},{py})"
                    for ch_i in range(3):
                        assert abs(col[ch_i] - base_rgb[ch_i]) <= 12, (
                            f"{fpath} exceeded +-12 RGB contrast at ({px},{py}): {col[:3]} vs {base_rgb}"
                        )
            fingerprints.add(pygame.image.tobytes(surf, "RGBA"))

        assert len(fingerprints) == 4, f"Expected 4 visually distinct variants for {prefix}"


def test_sanctuary_courtyard_roof_and_prop_assets_preloaded():
    """Verify all 7 Sanctuary courtyard/pond/roof/prop PNGs exist with expected dimensions and alpha."""
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    for fname, cache_key, expected_size, expect_alpha in SANCTUARY_PROP_SPECS:
        fpath = os.path.join("assets", "graphics", fname)
        assert os.path.exists(fpath), f"Missing Sanctuary asset: {fpath}"
        assert cache_key in renderer.prop_cache, f"Renderer missing prop_cache[{cache_key!r}]"
        surf = renderer.prop_cache[cache_key]
        assert surf.get_size() == expected_size, f"{fname} size {surf.get_size()} != {expected_size}"

        raw_rgba = pygame.image.tobytes(surf, "RGBA")
        alphas = raw_rgba[3::4]
        assert any(a > 0 for a in alphas), f"{fname} has no visible pixels"
        if expect_alpha:
            assert any(a == 0 for a in alphas), f"{fname} expected transparent background pixels"
        else:
            assert all(a == 255 for a in alphas), f"{fname} expected 100% opaque tile"


def test_sanctuary_deterministic_floor_hash_and_render_fallback():
    """Verify deterministic coordinate hash selects all 4 variants and renders with graceful fallback."""
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    seen_indices = set()
    for y in range(6):
        for x in range(6):
            idx = Renderer._sanctuary_floor_variant_index(x, y, 4)
            expected = (((x * 73856093) ^ (y * 19349663)) & 0x7FFFFFFF) % 4
            assert idx == expected
            assert 0 <= idx < 4
            seen_indices.add(idx)
    assert seen_indices == {0, 1, 2, 3}

    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        state.world.name = "sanctuary"
        renderer.render(state)

        # Graceful fallback when sanctuary_flagstone_variants is absent
        renderer.sanctuary_flagstone_variants = []
        renderer._chunk_cache.clear()
        renderer.render(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)
