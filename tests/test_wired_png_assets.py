"""Unit tests verifying wiring of the 4 procedural PNG assets into the tile/map renderer."""
# pylint: disable=no-member,protected-access
import os
import pygame
import constants
from engine.world import World
from engine.game_state import GameState
from rendering.renderer import Renderer


def setup_module():
    """Ensure headless SDL environment for pygame."""
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def test_floor_tile_variants_prebaked_on_startup():
    """Verify 4 subtle variants of floor_tile.png are pre-baked in RAM on startup."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    # 1. Variants list populated and stored in RAM
    assert hasattr(renderer, "floor_variants")
    assert len(renderer.floor_variants) == 4

    # 2. Each variant is 40x40
    for var in renderer.floor_variants:
        assert isinstance(var, pygame.Surface)
        assert var.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)

    # 3. Variants are not identical due to rotations and brightness shifts
    unique_variant_bytes = {pygame.image.tobytes(v, "RGBA") for v in renderer.floor_variants}
    assert len(unique_variant_bytes) >= 3


def test_wall_tile_asset_loaded_and_blitted():
    """Verify wall_tile.png is loaded and blitted in Sanctuary, while other biomes use procedural walls."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    assert hasattr(renderer, "wall_tile_surf")
    assert renderer.wall_tile_surf is not None
    assert renderer.wall_tile_surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)

    state = GameState(auto_load=False)
    state.world.name = "sanctuary"
    state.world.load_from_prototype(["#"])

    target_surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    renderer._draw_connected_wall_tile(
        target_surf,
        state,
        (0, 0, 1, 1),
        (0, 0, constants.TILE_SIZE, constants.TILE_SIZE),
        ("sanctuary", constants.BIOME_PALETTES["sanctuary"]),
    )

    # In sanctuary sandbox, verify surface has the wall tile pixels blitted
    wall_bytes = pygame.image.tobytes(renderer.wall_tile_surf, "RGB")
    target_bytes = pygame.image.tobytes(target_surf, "RGB")
    assert wall_bytes == target_bytes

    # In non-sanctuary biomes, legacy procedural wall rendering is preserved
    non_sanc_surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    renderer._draw_connected_wall_tile(
        non_sanc_surf,
        state,
        (0, 0, 1, 1),
        (0, 0, constants.TILE_SIZE, constants.TILE_SIZE),
        ("windy_ridge", constants.BIOME_PALETTES["windy_ridge"]),
    )
    non_sanc_bytes = pygame.image.tobytes(non_sanc_surf, "RGB")
    assert non_sanc_bytes != wall_bytes


def test_decorative_grass_and_rock_assets_and_offsets():
    """Verify grass and rock assets layer on top with slight positional offsets within tile bounds."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    assert hasattr(renderer, "grass_natural_surf")
    assert renderer.grass_natural_surf is not None
    assert renderer.grass_natural_surf.get_flags() & pygame.SRCALPHA != 0

    assert "Rock" in renderer.prop_cache
    rock_surf = renderer.prop_cache["Rock"]
    assert rock_surf.get_flags() & pygame.SRCALPHA != 0

    # Test map with grass ('g'), thicket ('G'), and floor ('.')
    state = GameState(auto_load=False)
    state.world.name = "sanctuary"
    state.world.load_from_prototype(["gG."])

    chunk_surf = pygame.Surface((constants.TILE_SIZE * 3, constants.TILE_SIZE))
    for tx in range(3):
        dr = (tx * constants.TILE_SIZE, 0, constants.TILE_SIZE, constants.TILE_SIZE)
        renderer._draw_static_tile_to_surface(chunk_surf, state, (tx, 0, 3, 1), dr)

    # Subsurfaces for grass and floor should not be identical because grass layers on top
    grass_sub = chunk_surf.subsurface((0, 0, constants.TILE_SIZE, constants.TILE_SIZE))
    floor_sub = chunk_surf.subsurface((constants.TILE_SIZE * 2, 0, constants.TILE_SIZE, constants.TILE_SIZE))

    assert pygame.image.tobytes(grass_sub, "RGB") != pygame.image.tobytes(floor_sub, "RGB")


def test_legend_walkability_and_wall_collision():
    """Verify floors and decorative elements remain walkable while walls block collision."""
    world = World(name="test_legend_world")
    prototype = [
        "###",
        "#gK",
        "#.#"
    ]
    world.load_from_prototype(prototype)

    # Walls block collision
    assert world.grid[0][0] == constants.TILE_WALL
    assert world.grid[0][1] == constants.TILE_WALL
    assert world.grid[0][2] == constants.TILE_WALL
    assert world.grid[1][0] == constants.TILE_WALL
    assert world.grid[2][0] == constants.TILE_WALL
    assert world.grid[2][2] == constants.TILE_WALL

    walls = world.get_nearby_walls((0, 0, 120, 120))
    assert len(walls) == 6

    # Floor ('.') and grass ('g') are walkable
    assert world.grid[2][1] == constants.TILE_EMPTY
    assert world.grid[1][1] == constants.TILE_GRASS

    # Rock ('K') is a decorative element (is_solid=False)
    rocks = [obj for obj in world.interactables if getattr(obj, "name", "") == "Rock"]
    assert len(rocks) == 1
    assert rocks[0].is_solid is False


def test_swamp_biome_wall_organic_not_brick():
    """Verify walls in swamp_mire render using procedural cliff facades rather than brick masonry."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    state = GameState(auto_load=False)
    state.world.name = "swamp_mire"
    state.world.load_from_prototype(["#"])

    target_surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    renderer._draw_connected_wall_tile(
        target_surf,
        state,
        (0, 0, 1, 1),
        (0, 0, constants.TILE_SIZE, constants.TILE_SIZE),
        ("swamp_mire", constants.BIOME_PALETTES["swamp_mire"]),
    )

    brick_wall_bytes = pygame.image.tobytes(renderer.wall_tile_surf, "RGB")
    target_bytes = pygame.image.tobytes(target_surf, "RGB")

    # In swamp, must match procedural cliff facade, NOT brick masonry
    assert target_bytes != brick_wall_bytes


def test_swamp_biome_floors_use_swamp_surfaces():
    """Verify swamp floor rendering passes use legacy procedural swamp strata floors."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    state = GameState(auto_load=False)
    state.world.name = "swamp_mire"
    state.world.load_from_prototype(["..."])

    chunk_surf = pygame.Surface((constants.TILE_SIZE * 3, constants.TILE_SIZE))
    # Render static tiles
    for tx in range(3):
        dr = (tx * constants.TILE_SIZE, 0, constants.TILE_SIZE, constants.TILE_SIZE)
        renderer._draw_static_tile_to_surface(chunk_surf, state, (tx, 0, 3, 1), dr)

    # Subsurfaces are non-empty and non-black
    for tx in range(3):
        sub = chunk_surf.subsurface((tx * constants.TILE_SIZE, 0, constants.TILE_SIZE, constants.TILE_SIZE))
        colors = [sub.get_at((px, py))[:3] for px in range(10, 30) for py in range(10, 30)]
        avg_brightness = sum(sum(c) for c in colors) / (len(colors) * 3)
        assert avg_brightness > 15, "Swamp floor rendered pure black"


def test_wall_feature_variants_available_and_selected():
    """Verify wall variants (standard, cracked, mossy, webbed) are loaded and selected across Sanctuary grid."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    assert hasattr(renderer, "wall_variants")
    assert len(renderer.wall_variants) >= 4

    state = GameState(auto_load=False)
    state.world.name = "sanctuary"
    state.world.load_from_prototype(["#####", "#####"])

    rendered_hashes = set()
    for ty in range(2):
        for tx in range(5):
            t_surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
            renderer._draw_connected_wall_tile(
                t_surf,
                state,
                (tx, ty, 5, 2),
                (0, 0, constants.TILE_SIZE, constants.TILE_SIZE),
                ("sanctuary", constants.BIOME_PALETTES["sanctuary"]),
            )
            rendered_hashes.add(pygame.image.tobytes(t_surf, "RGB"))

    # Across a 5x2 wall block in Sanctuary, multiple feature variants should be chosen
    assert len(rendered_hashes) > 1


def test_legacy_procedural_biome_floor_rendering_preserved():
    """Verify non-sanctuary biomes render using legacy procedural geometric shapes."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    biomes = ["windy_ridge", "pastoral_valley", "tech_tower", "swamp_mire", "frozen_peaks"]
    for b_name in biomes:
        state = GameState(auto_load=False)
        state.world.name = b_name
        state.world.load_from_prototype(["....", "....", "....", "...."])

        chunk_surf = pygame.Surface((constants.TILE_SIZE * 4, constants.TILE_SIZE * 4))
        for ty in range(4):
            for tx in range(4):
                dr = (tx * constants.TILE_SIZE, ty * constants.TILE_SIZE, constants.TILE_SIZE, constants.TILE_SIZE)
                renderer._draw_static_tile_to_surface(chunk_surf, state, (tx, ty, 4, 4), dr)

        # Ensure rendered surface is valid, colorful, and non-empty
        colors = [chunk_surf.get_at((px, py))[:3] for px in range(10, 150, 10) for py in range(10, 150, 10)]
        avg_brightness = sum(sum(c) for c in colors) / (len(colors) * 3)
        assert avg_brightness > 10, f"Biome {b_name} rendered pure black"


def test_sanctuary_floor_100_percent_opaque_no_white_bleed():
    """Verify base floor tiles render 100% opaque and screen buffer clears to solid dark tone."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    # 1. Floor variants in RAM are 100% opaque
    for var in renderer.floor_variants:
        for py in range(0, constants.TILE_SIZE, 5):
            for px in range(0, constants.TILE_SIZE, 5):
                color = var.get_at((px, py))
                assert color.a == 255, f"Floor variant has transparent alpha at ({px}, {py}): {color.a}"

    # 2. Render pass in Sanctuary has no white bleed
    state = GameState(auto_load=False)
    state.world.name = "sanctuary"
    state.world.load_from_prototype(["....", "...."])
    renderer.render(state)

    # 3. Check screen buffer pixels
    sw, sh = screen.get_size()
    for py in range(0, min(sh, 80), 10):
        for px in range(0, min(sw, 160), 10):
            pixel = screen.get_at((px, py))
            # No pure white bleed (255, 255, 255)
            assert pixel[:3] != (255, 255, 255), f"White bleed detected at ({px}, {py})"
            # Sepia / dark tones
            assert pixel[0] <= 120 and pixel[1] <= 120 and pixel[2] <= 120


def test_swamp_biome_props_cached_and_rendered():
    """Verify SwampFungus, SwampVent, and SwampThorns are cached and rendered in swamp_mire."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    # 1. Props in prop_cache
    for prop_key in ("SwampFungus", "SwampVent", "SwampThorns"):
        assert prop_key in renderer.prop_cache, f"{prop_key} missing from prop_cache"
        surf = renderer.prop_cache[prop_key]
        assert surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)
        assert surf.get_flags() & pygame.SRCALPHA != 0

    # 2. Render pass in swamp_mire with Structure and Rock interactables
    state = GameState(auto_load=False)
    state.world.name = "swamp_mire"
    state.world.load_from_prototype(["gG."])

    chunk_surf = pygame.Surface((constants.TILE_SIZE * 3, constants.TILE_SIZE))
    for tx in range(3):
        dr = (tx * constants.TILE_SIZE, 0, constants.TILE_SIZE, constants.TILE_SIZE)
        renderer._draw_static_tile_to_surface(chunk_surf, state, (tx, 0, 3, 1), dr)

    # Swamp thorns blitted on grass ('g') and thicket ('G')
    sub_grass = chunk_surf.subsurface((0, 0, constants.TILE_SIZE, constants.TILE_SIZE))
    sub_floor = chunk_surf.subsurface((constants.TILE_SIZE * 2, 0, constants.TILE_SIZE, constants.TILE_SIZE))
    assert pygame.image.tobytes(sub_grass, "RGB") != pygame.image.tobytes(sub_floor, "RGB")


def test_swamp_organic_wall_plateau_and_facade():
    """Verify swamp_mire walls render organic mounded plateaus and 2.5D cliff facades with highlights."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    state = GameState(auto_load=False)
    state.world.name = "swamp_mire"
    state.world.load_from_prototype(["#", "#"])

    # Top wall (has wall_s == True): Rooftop plateau
    top_surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    renderer._draw_connected_wall_tile(
        top_surf,
        state,
        (0, 0, 1, 2),
        (0, 0, constants.TILE_SIZE, constants.TILE_SIZE),
        ("swamp_mire", constants.BIOME_PALETTES["swamp_mire"]),
    )

    # Bottom wall (has wall_s == False): 2.5D cliff facade
    bot_surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    renderer._draw_connected_wall_tile(
        bot_surf,
        state,
        (0, 1, 1, 2),
        (0, 0, constants.TILE_SIZE, constants.TILE_SIZE),
        ("swamp_mire", constants.BIOME_PALETTES["swamp_mire"]),
    )

    # Both are non-empty and distinct
    top_bytes = pygame.image.tobytes(top_surf, "RGB")
    bot_bytes = pygame.image.tobytes(bot_surf, "RGB")
    assert top_bytes != bot_bytes

    # Bottom facade has deep maroon undercut shadow near the bottom
    bot_shadow = bot_surf.get_at((20, constants.TILE_SIZE - 2))[:3]
    assert bot_shadow == constants.BIOME_PALETTES["swamp_mire"]["wall_mortar"]


def test_environmental_clutter_cached_and_wired_to_biomes():
    """Verify ruins_rubble, swamp_flora, and crypt_clutter are cached and wired to their biomes."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    # 1. Clutter surfaces cached in prop_cache
    for clutter_key in ("RuinsRubble", "SwampFlora", "CryptClutter"):
        assert clutter_key in renderer.prop_cache, f"{clutter_key} missing from prop_cache"
        surf = renderer.prop_cache[clutter_key]
        assert surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)
        assert surf.get_flags() & pygame.SRCALPHA != 0

    # 2. Wire Ruins Rubble to ruins/tech_tower obstacle tiles
    state_ruins = GameState(auto_load=False)
    state_ruins.world.name = "tech_tower"
    state_ruins.world.load_from_prototype(["K."])
    surf_ruins = pygame.Surface((constants.TILE_SIZE * 2, constants.TILE_SIZE))
    renderer._draw_static_tile_to_surface(surf_ruins, state_ruins, (0, 0, 2, 1), (0, 0, 40, 40))
    renderer._draw_static_tile_to_surface(surf_ruins, state_ruins, (1, 0, 2, 1), (40, 0, 40, 40))
    # Obstacle with RuinsRubble is visually distinct from bare floor
    sub_k = surf_ruins.subsurface((0, 0, 40, 40))
    sub_floor = surf_ruins.subsurface((40, 0, 40, 40))
    assert pygame.image.tobytes(sub_k, "RGB") != pygame.image.tobytes(sub_floor, "RGB")

    # 3. Wire Swamp Flora & Thorns to swamp_mire grass and thicket tiles
    state_swamp = GameState(auto_load=False)
    state_swamp.world.name = "swamp_mire"
    state_swamp.world.load_from_prototype(["gG."])
    surf_swamp = pygame.Surface((constants.TILE_SIZE * 3, constants.TILE_SIZE))
    for tx in range(3):
        dr = (tx * constants.TILE_SIZE, 0, constants.TILE_SIZE, constants.TILE_SIZE)
        renderer._draw_static_tile_to_surface(surf_swamp, state_swamp, (tx, 0, 3, 1), dr)
    sub_g = surf_swamp.subsurface((0, 0, 40, 40))
    sub_g_thicket = surf_swamp.subsurface((40, 0, 40, 40))
    sub_swamp_floor = surf_swamp.subsurface((80, 0, 40, 40))
    assert pygame.image.tobytes(sub_g, "RGB") != pygame.image.tobytes(sub_swamp_floor, "RGB")
    assert pygame.image.tobytes(sub_g_thicket, "RGB") != pygame.image.tobytes(sub_swamp_floor, "RGB")

    # 4. Wire Crypt Clutter to the_colophon obstacle tiles
    state_crypt = GameState(auto_load=False)
    state_crypt.world.name = "the_colophon"
    state_crypt.world.load_from_prototype(["K."])
    surf_crypt = pygame.Surface((constants.TILE_SIZE * 2, constants.TILE_SIZE))
    renderer._draw_static_tile_to_surface(surf_crypt, state_crypt, (0, 0, 2, 1), (0, 0, 40, 40))
    renderer._draw_static_tile_to_surface(surf_crypt, state_crypt, (1, 0, 2, 1), (40, 0, 40, 40))
    sub_crypt_k = surf_crypt.subsurface((0, 0, 40, 40))
    sub_crypt_floor = surf_crypt.subsurface((40, 0, 40, 40))
    assert pygame.image.tobytes(sub_crypt_k, "RGB") != pygame.image.tobytes(sub_crypt_floor, "RGB")


def test_respite_and_chronicler_sprites_cached_and_rendered(monkeypatch):
    """Verify Respite, RespiteCorrupted, and Chronicler sprites load into Renderer and render cleanly."""
    from engine.world import Chronicler, Respite

    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 0)
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    for key in ("Respite", "RespiteCorrupted", "Chronicler"):
        assert key in renderer.prop_cache, f"{key} missing from prop_cache"
        surf = renderer.prop_cache[key]
        assert surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)

    state = GameState(auto_load=False)
    state.world.load_from_prototype(["........"])
    state.player.x = 100.0
    state.player.y = 40.0
    respite = Respite((40, 40), (40, 40))
    chronicler = Chronicler((200, 40))
    state.world.interactables = [respite, chronicler]
    state.camera.x = 0.0
    state.camera.y = 0.0

    # Render with Respite inside safe zone
    state.weather_manager.bleed_state = "BLEED"
    state.weather_manager.boss_coords_list = [{"x": 1.5, "y": 1.5}]
    state.weather_manager.current_boss_idx = 0
    state.weather_manager.active_safe_radius = 500.0
    renderer.render(state)
    safe_bytes = pygame.image.tobytes(screen, "RGB")

    # Render with Respite outside safe zone (Rain Inversion -> RespiteCorrupted)
    state.weather_manager.boss_coords_list = [{"x": 100, "y": 100}]
    state.weather_manager.active_safe_radius = 10.0
    renderer.render(state)
    corrupted_bytes = pygame.image.tobytes(screen, "RGB")

    assert safe_bytes != corrupted_bytes

    # Verify Chronicler flips toward player during dict-based active_dialogue
    state.active_dialogue = {"speaker": "The Chronicler", "text": "Stay inside the margin."}
    state.player.x = 100.0
    renderer.render(state)
    left_facing_bytes = pygame.image.tobytes(screen.subsurface((200, 40, 40, 40)), "RGB")

    state.player.x = 300.0
    renderer.render(state)
    right_facing_bytes = pygame.image.tobytes(screen.subsurface((200, 40, 40, 40)), "RGB")

    assert left_facing_bytes != right_facing_bytes



