"""Unit tests for the Grass Floor Tile data-driven decoration logic."""
# pylint: disable=no-member,protected-access
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
        assert pool_key in ("small", "medium", "tall")
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


def test_connected_floor_blending_and_multi_tile_patterns(monkeypatch):
    """Verify connected floor tiles blend without 1x1 borders and form varied multi-tile patterns."""
    state = GameState(auto_load=False)
    prototype = ["." * 16 for _ in range(16)]
    state.world.name = "pastoral_valley"
    state.world.load_from_prototype(prototype)

    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: None)
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    renderer = Renderer(screen)
    chunk_surf, _ = renderer._get_world_chunk(state, 0, 0, 16, 16)

    # 1. Verify different 1x1 tiles inside the same stratum do NOT repeat an identical 40x40 image
    stratum_buckets = {0: set(), 1: set(), 2: set()}
    for ty in range(0, 16):
        for tx in range(0, 16):
            s_val = renderer._get_tile_stratum(state, tx, ty)
            sub = chunk_surf.subsurface((tx * 40, ty * 40, 40, 40))
            stratum_buckets[s_val].add(pygame.image.tostring(sub, "RGB"))
    assert max(len(v) for v in stratum_buckets.values()) >= 8

    # 2. Verify an interior tile completely surrounded by the same stratum has no mortar border at (0, 20)
    found_interior = False
    for ty in range(2, 14):
        for tx in range(2, 14):
            s_here = renderer._get_tile_stratum(state, tx, ty)
            if all(
                renderer._get_tile_stratum(state, tx + dx, ty + dy) == s_here
                for dx in (-1, 0, 1)
                for dy in (-1, 0, 1)
            ):
                found_interior = True
                edge_col = chunk_surf.get_at((tx * 40, ty * 40 + 20))[:3]
                assert edge_col not in ((16, 8, 24), (156, 118, 68))
    assert found_interior
    state.shutdown_save_worker(timeout=1.0)
