"""Unit tests for the Grass Floor Tile data-driven decoration logic."""
# pylint: disable=no-member
import pygame
from engine.world import World
from engine.game_state import GameState
from rendering.renderer import Renderer
from constants import TILE_GRASS, SCREEN_WIDTH, SCREEN_HEIGHT

def test_grass_tile_parsing_and_generation():
    """Verify that 'g' tile parses to TILE_GRASS and spawns a decoration cluster."""
    world = World(name="test_grass_world")
    prototype = [
        "#####",
        "#g..#",
        "#...#",
        "#####"
    ]
    world.load_from_prototype(prototype)

    # 1. Verify grid cell type
    assert world.grid[1][1] == TILE_GRASS

    # 2. Verify grass decorations generated
    assert (1, 1) in world.grass_decorations
    instances = world.grass_decorations[(1, 1)]

    # 3. Verify cluster size
    assert 2 <= len(instances) <= 6

    # 4. Verify each instance attributes
    for pool_key, variant, dx, dy in instances:
        assert pool_key == "small"
        assert variant in (0, 1, 2)
        assert -12 <= dx <= 12
        assert -12 <= dy <= 12

def test_grass_tile_rendering(monkeypatch):
    """Verify that rendering TILE_GRASS executes without exceptions."""
    state = GameState(auto_load=False)
    # Set a custom map containing a grass tile
    prototype = [
        "#####",
        "#g..#",
        "#####"
    ]
    state.world.load_from_prototype(prototype)

    class DummyScreen:
        """A mock screen to receive surface blits."""
        def __init__(self, w, h):
            self._w = w
            self._h = h
        def get_width(self):
            """Return mock screen width."""
            return self._w
        def get_height(self):
            """Return mock screen height."""
            return self._h
        def fill(self, color):
            """Mock fill operation."""
        def blit(self, surf, pos):
            """Mock blit operation."""

    dummy = DummyScreen(SCREEN_WIDTH, SCREEN_HEIGHT)

    class DummyFont:
        """A mock font for rendering."""
        def render(self, _text, _aa, _color=None):
            """Record and render dummy surface."""
            return pygame.Surface((40, 10), pygame.SRCALPHA)
        def size(self, text):
            """Return mock size of text."""
            return (len(text) * 8, 12)

    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: DummyFont())
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)
    monkeypatch.setattr(pygame.draw, 'rect', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'line', lambda *a, **k: None)

    # Instantiate renderer and call render
    renderer = Renderer(dummy)
    # Verify that self.grass_pools is initialized
    assert "small" in renderer.grass_pools

    # Run rendering step - should complete without crash
    renderer.render(state)
