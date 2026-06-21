"""Unit tests for the Overgrown Thicket Tile (G) visual decoration logic."""
# pylint: disable=no-member
import pygame
from engine.world import World
from engine.game_state import GameState
from rendering.renderer import Renderer
from constants import TILE_THICKET, SCREEN_WIDTH, SCREEN_HEIGHT

def test_thicket_tile_parsing_and_generation():
    """Verify that 'G' tile parses to TILE_THICKET and spawns a heavy decoration cluster."""
    world = World(name="test_thicket_world")
    prototype = [
        "#####",
        "#G..#",
        "#...#",
        "#####"
    ]
    world.load_from_prototype(prototype)

    # 1. Verify grid cell type is TILE_THICKET
    assert world.grid[1][1] == TILE_THICKET

    # 2. Verify grass decorations generated
    assert (1, 1) in world.grass_decorations
    instances = world.grass_decorations[(1, 1)]

    # 3. Verify cluster size for thicket is 5 to 10
    assert 5 <= len(instances) <= 10

    # 4. Verify each instance attributes
    for pool_key, variant, dx, dy in instances:
        assert pool_key in ("small", "medium", "tall")
        assert variant in (0, 1, 2)
        assert -12 <= dx <= 12
        assert -12 <= dy <= 12

def test_thicket_tile_rendering(monkeypatch):
    """Verify that rendering TILE_THICKET executes without exceptions and pools are properly set."""
    state = GameState(auto_load=False)
    # Set a custom map containing a thicket tile
    prototype = [
        "#####",
        "#G..#",
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
    # Verify that self.grass_pools is initialized with all three sizes
    assert "small" in renderer.grass_pools
    assert "medium" in renderer.grass_pools
    assert "tall" in renderer.grass_pools

    # Run rendering step - should complete without crash
    renderer.render(state)
