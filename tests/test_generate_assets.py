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
        rubble_dest = os.path.join(tmpdir, "nested", "sub", "test_rubble.png")
        flora_dest = os.path.join(tmpdir, "nested", "sub", "test_flora.png")
        crypt_dest = os.path.join(tmpdir, "nested", "sub", "test_crypt.png")

        results = generate_assets.generate_all_assets(
            floor_path=floor_dest,
            wall_path=wall_dest,
            grass_path=grass_dest,
            rock_path=rock_dest,
            ruins_rubble_path=rubble_dest,
            swamp_flora_path=flora_dest,
            crypt_clutter_path=crypt_dest,
            seed=123,
        )

        assert results["floor_tile"] == floor_dest
        assert results["wall_tile"] == wall_dest
        assert results["grass_natural"] == grass_dest
        assert results["rock_cluster"] == rock_dest
        assert results["ruins_rubble"] == rubble_dest
        assert results["swamp_flora"] == flora_dest
        assert results["crypt_clutter"] == crypt_dest

        for path in [floor_dest, wall_dest, grass_dest, rock_dest, rubble_dest, flora_dest, crypt_dest]:
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


def test_generate_swamp_props():
    """Verify procedural generation of swamp fungus, gas vent, and skeletal thorns."""
    rng = random.Random(404)
    fungus = generate_assets.generate_swamp_fungus(40, 40, rng=rng)
    vent = generate_assets.generate_swamp_gas_vent(40, 40, rng=rng)
    thorns = generate_assets.generate_swamp_thorns(40, 40, rng=rng)

    for prop_name, surf in [("fungus", fungus), ("vent", vent), ("thorns", thorns)]:
        assert surf.get_size() == (40, 40), f"{prop_name} invalid dimensions"
        assert surf.get_flags() & pygame.SRCALPHA != 0, f"{prop_name} missing SRCALPHA"
        # Background corners are transparent
        assert surf.get_at((0, 0))[3] == 0, f"{prop_name} top-left corner not transparent"
        assert surf.get_at((39, 0))[3] == 0, f"{prop_name} top-right corner not transparent"

    # Fungus has violet/maroon cap and yellow-green spots
    alphas = [fungus.get_at((x, y))[3] for x in range(40) for y in range(40)]
    assert alphas.count(0) > 100
    assert alphas.count(255) > 100

    # Gas vent has dark pore and pea-green spore glow
    pore_pixels = [vent.get_at((x, y)) for x in range(12, 28) for y in range(12, 28)]
    assert any(p[1] > 180 and p[0] > 100 for p in pore_pixels)  # Pea-green spore glow

    # Thorns have calcified pale ash/bone stalks
    thorn_pixels = [thorns.get_at((x, y)) for x in range(40) for y in range(40) if thorns.get_at((x, y))[3] == 255]
    avg_bone_r = sum(p[0] for p in thorn_pixels) / len(thorn_pixels)
    assert avg_bone_r > 100, "Thorn color too dark for calcified briar"


def test_generate_environmental_clutter_sprites():
    """Verify procedural generation of ruins rubble, swamp flora, and crypt clutter sprites."""
    rng = random.Random(505)
    rubble = generate_assets.generate_ruins_rubble(40, 40, rng=rng)
    flora = generate_assets.generate_swamp_flora(40, 40, rng=rng)
    crypt = generate_assets.generate_crypt_clutter(40, 40, rng=rng)

    for clutter_name, surf in [("rubble", rubble), ("flora", flora), ("crypt", crypt)]:
        assert surf.get_size() == (40, 40), f"{clutter_name} invalid dimensions"
        assert surf.get_flags() & pygame.SRCALPHA != 0, f"{clutter_name} missing SRCALPHA"
        assert surf.get_at((0, 0))[3] == 0, f"{clutter_name} top-left corner not transparent"
        assert surf.get_at((39, 0))[3] == 0, f"{clutter_name} top-right corner not transparent"

    # 1. Ruins Rubble: fluted pillar stump, highlights, and chipped masonry
    rubble_alphas = [rubble.get_at((x, y))[3] for x in range(40) for y in range(40)]
    assert rubble_alphas.count(0) > 80
    assert rubble_alphas.count(255) > 80
    pillar_pixels = [
        rubble.get_at((x, y)) for x in range(9, 24) for y in range(16, 28) if rubble.get_at((x, y))[3] == 255
    ]
    assert len(pillar_pixels) > 50
    # Has highlights
    assert any(p[0] > 115 and p[1] > 125 and p[2] > 135 for p in pillar_pixels)

    # 2. Swamp Flora: reeds, spore glow halo, and luminous fungal caps
    flora_alphas = [flora.get_at((x, y))[3] for x in range(40) for y in range(40)]
    assert flora_alphas.count(0) > 80
    # Has translucent spore glow halos
    assert sum(1 for a in flora_alphas if 0 < a < 255) > 15
    # Has bright luminous green caps / motes
    all_flora_pixels = [flora.get_at((x, y)) for x in range(40) for y in range(40)]
    assert any(p[1] >= 200 and p[0] >= 140 for p in all_flora_pixels)

    # 3. Crypt Clutter: ancient unrolled parchment scroll with script and bone fragments
    crypt_alphas = [crypt.get_at((x, y))[3] for x in range(40) for y in range(40)]
    assert crypt_alphas.count(0) > 80
    assert crypt_alphas.count(255) > 80
    # Parchment sheet exists with warm sepia tones
    parchment_pixels = [crypt.get_at((x, y)) for x in range(6, 21) for y in range(20, 31)]
    assert any(160 <= p[0] <= 210 and 140 <= p[1] <= 190 and 100 <= p[2] <= 150 for p in parchment_pixels)
    # Ink script marks exist
    assert any(p[0] <= 70 and p[1] <= 60 and p[2] <= 55 for p in parchment_pixels)


def test_generate_wall_top_cap_vs_front_face():
    """Verify wall top cap is lighter than south-facing vertical wall front face."""
    rng = random.Random(606)
    cap = generate_assets.generate_wall_top_cap(40, 40, rng=rng)
    face = generate_assets.generate_wall_front_face(40, 40, rng=rng)

    assert cap.get_size() == (40, 40)
    assert face.get_size() == (40, 40)

    cap_lum = sum(sum(cap.get_at((x, y))[:3]) for x in range(10, 30) for y in range(10, 30)) / 400
    face_lum = sum(sum(face.get_at((x, y))[:3]) for x in range(10, 30) for y in range(10, 30)) / 400
    assert cap_lum > face_lum + 30

    # Front face darkens toward the ground-contact bottom edge
    face_top_lum = sum(sum(face.get_at((x, 4))[:3]) for x in range(10, 30)) / 20
    face_bot_lum = sum(sum(face.get_at((x, 38))[:3]) for x in range(10, 30)) / 20
    assert face_top_lum > face_bot_lum


def test_generate_floor_shadow_overlays():
    """Verify south, east, and corner drop-shadow overlays have smooth alpha gradients."""
    rng = random.Random(707)
    south = generate_assets.generate_floor_shadow_overlay(40, 40, direction="south", rng=rng)
    east = generate_assets.generate_floor_shadow_overlay(40, 40, direction="east", rng=rng)
    corner = generate_assets.generate_floor_shadow_overlay(40, 40, direction="corner", rng=rng)

    for surf in (south, east, corner):
        assert surf.get_size() == (40, 40)
        assert surf.get_flags() & pygame.SRCALPHA != 0

    # South shadow is opaque/semi-transparent near y=0 and fades to 0 near y=35
    assert south.get_at((20, 1))[3] > 80
    assert south.get_at((20, 35))[3] == 0

    # East shadow is semi-transparent near x=0 and fades to 0 near x=35
    assert east.get_at((1, 20))[3] > 70
    assert east.get_at((35, 20))[3] == 0

    # Corner shadow is concentrated near (0, 0) and fades out
    assert corner.get_at((1, 1))[3] > 80
    assert corner.get_at((35, 35))[3] == 0


def test_generate_cliff_stairs_and_pit_rim():
    """Verify cliff edge, staircase, and pit rim tiles render distinct elevation features."""
    rng = random.Random(808)
    cliff = generate_assets.generate_cliff_edge_tile(40, 40, rng=rng)
    stairs = generate_assets.generate_staircase_tile(40, 40, rng=rng)
    pit = generate_assets.generate_pit_rim_tile(40, 40, rng=rng)

    for surf in (cliff, stairs, pit):
        assert surf.get_size() == (40, 40)

    # Cliff top ledge is brighter than lower cliff face
    cliff_top = sum(sum(cliff.get_at((x, 5))[:3]) for x in range(10, 30)) / 20
    cliff_bot = sum(sum(cliff.get_at((x, 34))[:3]) for x in range(10, 30)) / 20
    assert cliff_top > cliff_bot

    # Staircase has alternating bright step lip (y=0) and dark riser shadow (y=6)
    step_lip = sum(stairs.get_at((20, 0))[:3])
    step_riser = sum(stairs.get_at((20, 6))[:3])
    assert step_lip > step_riser + 50

    # Pit rim has lit floor lip near top and near-black abyssal void at bottom
    pit_lip = sum(pit.get_at((20, 5))[:3])
    pit_abyss = sum(pit.get_at((20, 34))[:3])
    assert pit_lip > 90
    assert pit_abyss < 45


def test_generate_all_assets_includes_verticality():
    """Verify generate_all_assets creates all 8 new 2.5D verticality PNG files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = generate_assets.generate_all_assets(
            floor_path=os.path.join(tmpdir, "floor.png"),
            wall_path=os.path.join(tmpdir, "wall.png"),
            grass_path=os.path.join(tmpdir, "grass.png"),
            rock_path=os.path.join(tmpdir, "rock.png"),
            altar_path=os.path.join(tmpdir, "altar.png"),
            wall_cracked_path=os.path.join(tmpdir, "wall_cracked.png"),
            wall_mossy_path=os.path.join(tmpdir, "wall_mossy.png"),
            wall_webbed_path=os.path.join(tmpdir, "wall_webbed.png"),
            swamp_water_path=os.path.join(tmpdir, "swamp_water.png"),
            mud_turf_path=os.path.join(tmpdir, "mud_turf.png"),
            peat_bank_path=os.path.join(tmpdir, "peat_bank.png"),
            swamp_wall_path=os.path.join(tmpdir, "swamp_wall.png"),
            swamp_fungus_path=os.path.join(tmpdir, "swamp_fungus.png"),
            swamp_vent_path=os.path.join(tmpdir, "swamp_vent.png"),
            swamp_thorns_path=os.path.join(tmpdir, "swamp_thorns.png"),
            ruins_rubble_path=os.path.join(tmpdir, "ruins_rubble.png"),
            swamp_flora_path=os.path.join(tmpdir, "swamp_flora.png"),
            crypt_clutter_path=os.path.join(tmpdir, "crypt_clutter.png"),
            wall_top_cap_path=os.path.join(tmpdir, "wall_top_cap.png"),
            wall_front_face_path=os.path.join(tmpdir, "wall_front_face.png"),
            shadow_south_path=os.path.join(tmpdir, "shadow_south.png"),
            shadow_east_path=os.path.join(tmpdir, "shadow_east.png"),
            shadow_corner_path=os.path.join(tmpdir, "shadow_corner.png"),
            cliff_edge_path=os.path.join(tmpdir, "cliff_edge.png"),
            staircase_path=os.path.join(tmpdir, "staircase_tile.png"),
            pit_rim_path=os.path.join(tmpdir, "pit_rim.png"),
            seed=42,
        )
        for key in (
            "wall_top_cap", "wall_front_face", "shadow_south", "shadow_east",
            "shadow_corner", "cliff_edge", "staircase_tile", "pit_rim",
        ):
            assert key in paths
            assert os.path.exists(paths[key])
            assert os.path.getsize(paths[key]) > 100


