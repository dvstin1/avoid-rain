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


def test_generate_wall_variants_distinct():
    """Verify standard, cracked, mossy, and webbed wall variants produce distinct pixel outputs."""
    seed = 42
    std = generate_assets.generate_wall_tile(40, 40, rng=random.Random(seed), variant="standard")
    cracked = generate_assets.generate_wall_tile(40, 40, rng=random.Random(seed), variant="cracked")
    mossy = generate_assets.generate_wall_tile(40, 40, rng=random.Random(seed), variant="mossy")
    webbed = generate_assets.generate_wall_tile(40, 40, rng=random.Random(seed), variant="webbed")

    b_std = pygame.image.tobytes(std, "RGB")
    b_cracked = pygame.image.tobytes(cracked, "RGB")
    b_mossy = pygame.image.tobytes(mossy, "RGB")
    b_webbed = pygame.image.tobytes(webbed, "RGB")

    assert b_std != b_cracked
    assert b_std != b_mossy
    assert b_std != b_webbed
    assert b_cracked != b_mossy


def test_swamp_biome_surfaces_opaque():
    """Verify swamp water, mud turf, peat bank, and swamp wall export as 100% opaque surfaces."""
    rng = random.Random(77)
    water = generate_assets.generate_swamp_water_tile(40, 40, rng=rng)
    mud = generate_assets.generate_mud_turf_tile(40, 40, rng=rng)
    peat = generate_assets.generate_peat_bank_tile(40, 40, rng=rng)
    swall = generate_assets.generate_swamp_wall_tile(40, 40, rng=rng)

    for name, surf in [
        ("water", water),
        ("mud", mud),
        ("peat", peat),
        ("swamp_wall", swall),
    ]:
        assert surf.get_size() == (40, 40), f"{name} invalid size"
        # Check all pixels have alpha 255 (100% opaque)
        for y in range(40):
            for x in range(40):
                px = surf.get_at((x, y))
                assert len(px) < 4 or px[3] == 255, f"{name} has non-opaque pixel at ({x}, {y}): {px}"


def test_generate_attunement_altar():
    """Verify procedural Biome Attunement Altar generation, stepped plinth, and glowing core."""
    rng = random.Random(999)
    altar = generate_assets.generate_attunement_altar(40, 40, rng=rng)

    assert altar.get_size() == (40, 40)
    assert altar.get_flags() & pygame.SRCALPHA != 0

    # Corner background is transparent
    assert altar.get_at((0, 0))[3] == 0
    assert altar.get_at((39, 0))[3] == 0

    # Stepped base is opaque dark slate stone
    base_pixel = altar.get_at((20, 28))
    assert base_pixel[3] == 255
    assert base_pixel[0] < 70 and base_pixel[1] < 70 and base_pixel[2] < 70

    # Bottom ambient drop shadow is translucent
    shadow_pixel = altar.get_at((5, 33))
    assert 0 < shadow_pixel[3] < 255

    # Glowing runic core contains vibrant cyan / bright glyph
    core_pixel = altar.get_at((20, 13))
    assert core_pixel[3] > 200
    assert core_pixel[1] >= 180 and core_pixel[2] >= 200  # Strong cyan/blue-green highlight

