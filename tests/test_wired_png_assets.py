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
    """Verify wall_tile.png is loaded and blitted replacing procedural shapes."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    assert hasattr(renderer, "wall_tile_surf")
    assert renderer.wall_tile_surf is not None
    assert renderer.wall_tile_surf.get_size() == (constants.TILE_SIZE, constants.TILE_SIZE)

    state = GameState(auto_load=False)
    state.world.load_from_prototype(["#"])

    target_surf = pygame.Surface((constants.TILE_SIZE, constants.TILE_SIZE))
    renderer._draw_connected_wall_tile(
        target_surf,
        state,
        (0, 0, 1, 1),
        (0, 0, constants.TILE_SIZE, constants.TILE_SIZE),
        ("windy_ridge", constants.BIOME_PALETTES["windy_ridge"]),
    )

    # Verify surface has the wall tile pixels blitted
    wall_bytes = pygame.image.tobytes(renderer.wall_tile_surf, "RGB")
    target_bytes = pygame.image.tobytes(target_surf, "RGB")
    assert wall_bytes == target_bytes


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
    """Verify walls in swamp_mire render using swamp_wall rather than brick masonry."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    assert hasattr(renderer, "swamp_wall_surf")
    assert renderer.swamp_wall_surf is not None

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

    swamp_wall_bytes = pygame.image.tobytes(renderer.swamp_wall_surf, "RGB")
    brick_wall_bytes = pygame.image.tobytes(renderer.wall_tile_surf, "RGB")
    target_bytes = pygame.image.tobytes(target_surf, "RGB")

    # In swamp, must match swamp wall, NOT brick masonry
    assert target_bytes == swamp_wall_bytes
    assert target_bytes != brick_wall_bytes


def test_swamp_biome_floors_use_swamp_surfaces():
    """Verify swamp floor rendering passes use swamp_water, mud_turf, and peat_bank."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    assert hasattr(renderer, "swamp_water_surf")
    assert hasattr(renderer, "mud_turf_surf")
    assert hasattr(renderer, "peat_bank_surf")

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
    """Verify wall variants (standard, cracked, mossy, webbed) are loaded and selected across grid."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)

    assert hasattr(renderer, "wall_variants")
    assert len(renderer.wall_variants) >= 4

    state = GameState(auto_load=False)
    state.world.name = "windy_ridge"
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
                ("windy_ridge", constants.BIOME_PALETTES["windy_ridge"]),
            )
            rendered_hashes.add(pygame.image.tobytes(t_surf, "RGB"))

    # Across a 5x2 wall block, multiple feature variants should be chosen
    assert len(rendered_hashes) > 1
