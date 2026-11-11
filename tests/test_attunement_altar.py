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


def test_audio_debug_map_filename_rendering():
    """Verify map filename is rendered under audio OSD when debug is enabled and not in bloom banner."""
    screen = pygame.Surface((800, 600))
    renderer = Renderer(screen)

    gs = GameState(auto_load=False)
    gs.world = create_world("sanctuary_geometric.txt")
    gs.bloom_timer = 2.0
    gs.bloom_text = "THE SANCTUARY"

    rendered_hud_strings = []
    rendered_bloom_strings = []

    class RecordingFont:
        """Mock font recording rendered text strings."""
        def __init__(self, record_list):
            self.record_list = record_list

        def render(self, text, *_args, **_kwargs):
            """Record rendered string and return mock surface."""
            self.record_list.append(str(text))
            return pygame.Surface((max(1, len(str(text)) * 8), 16), pygame.SRCALPHA)

        def size(self, text):
            """Return mock font size."""
            return (len(str(text)) * 8, 16)

    renderer.hud_font = RecordingFont(rendered_hud_strings)
    renderer.bloom_font = RecordingFont(rendered_bloom_strings)

    # 1. Bloom overlay only renders room title, not map filename
    renderer.draw_bloom_overlay(gs)
    assert any("THE SANCTUARY" in s for s in rendered_bloom_strings)
    assert not any("sanctuary_geometric" in s for s in rendered_bloom_strings)

    # 2. When debug_text_enabled is False, render() does not draw audio/map OSD
    gs.debug_text_enabled = False
    rendered_hud_strings.clear()
    renderer.render(gs)
    assert not any("[ AUDIO_OSD ]" in s for s in rendered_hud_strings)
    assert not any("sanctuary_geometric" in s for s in rendered_hud_strings)

    # 3. When debug_text_enabled is True, render() draws map filename under audio OSD
    gs.debug_text_enabled = True
    rendered_hud_strings.clear()
    renderer.render(gs)
    assert any("[ AUDIO_OSD ]" in s for s in rendered_hud_strings)
    assert any("Map: sanctuary_geometric.txt" in s for s in rendered_hud_strings)
