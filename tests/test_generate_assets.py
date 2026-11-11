"""Unit tests for procedural asset generator script (generate_assets.py)."""
# pylint: disable=no-member
import os
import random
import tempfile
import pygame
import generate_assets


def setup_module():
    """Ensure headless SDL environment for pygame."""
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def test_generate_floor_tile_dimensions_and_grit():
    """Verify floor tile generation dimensions, base tone, and grit noise."""
    rng = random.Random(42)
    surf = generate_assets.generate_floor_tile(40, 40, rng=rng)

    assert surf.get_size() == (40, 40)

    # Check color channels are within expected dark slate-brown ranges
    center_colors = [surf.get_at((x, y))[:3] for x in range(10, 30) for y in range(10, 30)]
    avg_r = sum(c[0] for c in center_colors) / len(center_colors)
    avg_g = sum(c[1] for c in center_colors) / len(center_colors)
    avg_b = sum(c[2] for c in center_colors) / len(center_colors)

    assert 35 <= avg_r <= 65
    assert 30 <= avg_g <= 60
    assert 25 <= avg_b <= 55

    # Check grit noise has variation (not a flat single color)
    unique_colors = {surf.get_at((x, y))[:3] for x in range(40) for y in range(40)}
    assert len(unique_colors) > 20


def test_generate_floor_tile_vignette():
    """Verify floor tile has darker edges than center due to perimeter vignette."""
    rng = random.Random(1337)
    surf = generate_assets.generate_floor_tile(40, 40, rng=rng)

    edge_luminance = [sum(surf.get_at((x, 0))[:3]) for x in range(40)]
    center_luminance = [sum(surf.get_at((x, 20))[:3]) for x in range(15, 25)]

    avg_edge = sum(edge_luminance) / len(edge_luminance)
    avg_center = sum(center_luminance) / len(center_luminance)

    assert avg_edge < avg_center


def test_generate_wall_tile_masonry_and_highlights():
    """Verify wall tile has courses, dark joints, and highlights."""
    rng = random.Random(99)
    surf = generate_assets.generate_wall_tile(40, 40, rng=rng)

    assert surf.get_size() == (40, 40)

    # Wall base tone is desaturated slate-blue/grey
    px_samples = [surf.get_at((x, y))[:3] for x in range(40) for y in range(40)]
    avg_r = sum(c[0] for c in px_samples) / len(px_samples)
    avg_b = sum(c[2] for c in px_samples) / len(px_samples)
    # Slate blue has blue channel comparable to or higher than red
    assert avg_b >= avg_r - 5

    # Verify dark masonry joints exist (near y=10, 20, 30)
    dark_joints_found = any(
        generate_assets.WALL_JOINT_COLOR in (surf.get_at((x, 10))[:3], surf.get_at((x, 20))[:3])
        for x in range(40)
    )
    assert dark_joints_found

    # Verify top/left highlights exist
    highlights_found = any(
        surf.get_at((x, y))[:3] == generate_assets.WALL_HIGHLIGHT_COLOR
        for x in range(40)
        for y in range(40)
    )
    assert highlights_found


def test_generate_grass_tile_alpha_and_organic_foliage():
    """Verify moss/grass patch generates organic shape with alpha transparency."""
    rng = random.Random(777)
    surf = generate_assets.generate_grass_tile(40, 40, rng=rng)

    assert surf.get_size() == (40, 40)
    assert surf.get_flags() & pygame.SRCALPHA != 0

    alphas = [surf.get_at((x, y))[3] for x in range(40) for y in range(40)]
    transparent_count = alphas.count(0)
    semi_trans_count = sum(1 for a in alphas if 0 < a < 255)
    opaque_count = alphas.count(255)

    # Must have negative space (transparent)
    assert transparent_count > 100
    # Must have translucent feathered edges
    assert semi_trans_count > 20
    # Must have dense foliage core
    assert opaque_count > 100

    # Foliage colors must be green dominant (G > R and G > B)
    active_foliage = [surf.get_at((x, y))[:3] for x in range(40) for y in range(40) if surf.get_at((x, y))[3] > 0]
    green_dominant = sum(1 for r, g, b in active_foliage if g > r and g > b)
    assert green_dominant / len(active_foliage) > 0.85


def test_generate_rock_cluster_properties():
    """Verify rock cluster has transparent background, grey stone bodies, shadows, and highlights."""
    rng = random.Random(101)
    surf = generate_assets.generate_rock_cluster(40, 40, rng=rng)

    assert surf.get_size() == (40, 40)
    assert surf.get_flags() & pygame.SRCALPHA != 0

    alphas = [surf.get_at((x, y))[3] for x in range(40) for y in range(40)]
    transparent_count = alphas.count(0)
    shadow_count = sum(1 for a in alphas if 0 < a < 255)
    opaque_count = alphas.count(255)

    assert transparent_count > 500
    assert shadow_count > 10
    assert opaque_count > 100

    # Verify stones have desaturated grey tones (R, G, B are close in value)
    opaque_pixels = [surf.get_at((x, y))[:3] for x in range(40) for y in range(40) if surf.get_at((x, y))[3] == 255]
    desaturated_count = sum(1 for r, g, b in opaque_pixels if abs(r - g) <= 12 and abs(g - b) <= 12)
    assert desaturated_count / len(opaque_pixels) > 0.85

    # Verify highlights exist along top/left stone bevels
    highlights_found = any(
        110 <= r <= 150 and 115 <= g <= 155 and 120 <= b <= 160
        for r, g, b in opaque_pixels
    )
    assert highlights_found


def test_generate_all_assets_creates_files_and_directories():
    """Verify generate_all_assets creates missing directories and valid PNG files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        floor_dest = os.path.join(tmpdir, "nested", "sub", "test_floor.png")
        wall_dest = os.path.join(tmpdir, "nested", "sub", "test_wall.png")
        grass_dest = os.path.join(tmpdir, "nested", "sub", "test_grass.png")
        rock_dest = os.path.join(tmpdir, "nested", "sub", "test_rock.png")

        results = generate_assets.generate_all_assets(
            floor_path=floor_dest,
            wall_path=wall_dest,
            grass_path=grass_dest,
            rock_path=rock_dest,
            seed=123,
        )

        assert results["floor_tile"] == floor_dest
        assert results["wall_tile"] == wall_dest
        assert results["grass_natural"] == grass_dest
        assert results["rock_cluster"] == rock_dest

        for path in [floor_dest, wall_dest, grass_dest, rock_dest]:
            assert os.path.exists(path)
            assert os.path.getsize(path) > 200
            loaded = pygame.image.load(path)
            assert loaded.get_size() == (40, 40)


def test_procedural_generation_seed_reproducibility():
    """Verify providing an explicit seed yields identical pixel data."""
    surf1 = generate_assets.generate_floor_tile(40, 40, rng=random.Random(54321))
    surf2 = generate_assets.generate_floor_tile(40, 40, rng=random.Random(54321))

    bytes1 = pygame.image.tobytes(surf1, "RGBA")
    bytes2 = pygame.image.tobytes(surf2, "RGBA")
    assert bytes1 == bytes2

    rock1 = generate_assets.generate_rock_cluster(40, 40, rng=random.Random(9876))
    rock2 = generate_assets.generate_rock_cluster(40, 40, rng=random.Random(9876))

    assert pygame.image.tobytes(rock1, "RGBA") == pygame.image.tobytes(rock2, "RGBA")
