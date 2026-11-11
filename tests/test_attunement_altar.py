"""Unit tests for Biome Attunement Altar and Sanctuary variant maps."""
# pylint: disable=no-member,protected-access
import os
import pygame
import pytest
from engine.game_state import GameState
from engine.maps import create_world
from engine.world import AttunementAltar
from rendering.renderer import Renderer


@pytest.fixture(autouse=True)
def init_pygame():
    """Ensure pygame display and font modules are initialized headlessly."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    yield
    pygame.quit()


def test_altar_presence_in_sanctuary_json():
    """Verify that Attunement Altar is parsed from sanctuary.json at expected coordinates."""
    world = create_world("sanctuary")
    altars = [obj for obj in world.interactables if isinstance(obj, AttunementAltar)]
    assert len(altars) == 1
    altar = altars[0]
    assert altar.name == "Attunement Altar"
    assert int(altar.x // 40) == 15
    assert int(altar.y // 40) == 5


def test_expanded_sanctuary_variant_maps():
    """Verify all four expanded Sanctuary variant files have 36x26 dimensions and contain the altar."""
    variants = [
        "sanctuary_paved.txt",
        "sanctuary_geometric.txt",
        "sanctuary_swamp.txt",
        "sanctuary_ruins.txt",
    ]
    for filename in variants:
        world = create_world(filename)
        assert len(world.grid[0]) == 36, f"{filename} width != 36"
        assert len(world.grid) == 26, f"{filename} height != 26"
        assert world.map_filename == filename

        altars = [obj for obj in world.interactables if isinstance(obj, AttunementAltar)]
        assert len(altars) == 1, f"Missing altar in {filename}"
        altar = altars[0]
        assert int(altar.x // 40) == 17
        assert int(altar.y // 40) == 7
        assert world.player_start == (800, 360)


def test_altar_sequential_cycling():
    """Verify that AttunementAltar cycles through variants sequentially and wraps around."""
    altar_paved = AttunementAltar((680, 280), (40, 40), current_map="sanctuary_paved.txt")
    assert altar_paved.get_next_variant() == "sanctuary_geometric.txt"

    altar_geom = AttunementAltar((680, 280), (40, 40), current_map="sanctuary_geometric.txt")
    assert altar_geom.get_next_variant() == "sanctuary_swamp.txt"

    altar_swamp = AttunementAltar((680, 280), (40, 40), current_map="sanctuary_swamp.txt")
    assert altar_swamp.get_next_variant() == "sanctuary_ruins.txt"

    altar_ruins = AttunementAltar((680, 280), (40, 40), current_map="sanctuary_ruins.txt")
    assert altar_ruins.get_next_variant() == "sanctuary_paved.txt"

    altar_base = AttunementAltar((600, 200), (40, 40), current_map="sanctuary.json")
    assert altar_base.get_next_variant() == "sanctuary_paved.txt"


def test_altar_warp_interaction_and_transfer():
    """Verify interacting with altar initiates warp and smoothly transfers to the next variant."""
    gs = GameState(auto_load=False)
    gs.world = create_world("sanctuary_paved.txt")

    altar = next(obj for obj in gs.world.interactables if isinstance(obj, AttunementAltar))
    gs.player.x, gs.player.y = altar.x, altar.y

    # Execute interaction
    altar.execute_interaction(gs)
    assert gs.warp_controller.is_active()

    # Step through transit stages to arrival
    while gs.warp_controller.is_active():
        gs.update(0.016, {"move": (0, 0), "attack": False})

    assert gs.world.map_filename == "sanctuary_geometric.txt"
    assert gs.player.x == float(gs.world.player_start[0])
    assert gs.player.y == float(gs.world.player_start[1])


def test_biome_resolution_for_variants():
    """Verify _resolve_tile_biome correctly maps each variant to its designated biome type."""
    screen = pygame.Surface((800, 600))
    renderer = Renderer(screen)
    gs = GameState(auto_load=False)

    mappings = [
        ("sanctuary_paved.txt", "sanctuary"),
        ("sanctuary_geometric.txt", "windy_ridge"),
        ("sanctuary_swamp.txt", "swamp_mire"),
        ("sanctuary_ruins.txt", "tech_tower"),
    ]

    for map_file, expected_biome in mappings:
        gs.world = create_world(map_file)
        biome = renderer._resolve_tile_biome(gs, 10, 10)
        assert biome == expected_biome, f"{map_file} resolved to {biome}, expected {expected_biome}"


def test_hud_and_bloom_map_filename_rendering():
    """Verify debug HUD and room title bloom banner render current map filename."""
    screen = pygame.Surface((800, 600))
    renderer = Renderer(screen)

    gs = GameState(auto_load=False)
    gs.world = create_world("sanctuary_geometric.txt")
    gs.debug_text_enabled = True
    gs.bloom_timer = 2.0
    gs.bloom_text = "THE SANCTUARY"

    # Test HUD rendering with debug enabled
    renderer.draw_hud(gs)
    assert renderer._hud_surf is not None

    # Test bloom banner rendering
    renderer.draw_bloom_overlay(gs)
