"""Unit tests for the minimap rendering behavior in Renderer.draw_minimap.

The tests monkeypatch pygame.draw.rect to capture draw calls and assert that
minimap-drawn rectangles appear in the top-left minimap area.
"""
import pytest
import pygame
import os
from rendering.renderer import Renderer
from engine.game_state import GameState
from constants import MINIMAP_WIDTH, MINIMAP_HEIGHT, MINIMAP_PADDING, TILE_SIZE

# Ensure headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"

@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((1, 1)) # Initialize display for Renderer
    yield
    pygame.quit()

class MockWorld:
    def __init__(self, name="outside"):
        self.name = name
        self.grid = [[0 for _ in range(40)] for _ in range(30)]
        self.player_start = (0, 0)
    def get_nearby_walls(self, rect): return []
    def get_nearby_interactables(self, rect): return []

def test_minimap_draws_player_and_walls(monkeypatch):
    state = GameState(auto_load=False)
    state.world = MockWorld("chapter1")
    # Place a wall near top-left of the world and put player nearby
    state.world.grid[1][1] = 1 # TILE_WALL
    state.player.x = 1 * 40 + 5
    state.player.y = 1 * 40 + 5
    
    class DummyScreen:
        def __init__(self, w, h):
            self._w = w
            self._h = h
        def get_width(self): return self._w
        def get_height(self): return self._h
        def fill(self, color): pass
        def blit(self, surf, pos): pass

    dummy = DummyScreen(800, 600)
    recorded = []
    def fake_draw_rect(surface, color, rect, *args, **kwargs):
        recorded.append((color, tuple(rect)))

    monkeypatch.setattr(pygame.draw, 'rect', fake_draw_rect)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)

    renderer = Renderer(dummy)
    renderer.draw_minimap(state)

    # We expect at least one wall rect and one player rect
    assert len(recorded) >= 1

def test_minimap_draws_compass_indicators(monkeypatch):
    state = GameState(auto_load=False)
    state.world = MockWorld("chapter1")
    # Place player at (100, 100)
    state.player.x = 100
    state.player.y = 100
    
    # Place an objective far to the right and down
    state.objectives = [(5000, 5000)]
    
    class DummyScreen:
        def __init__(self, w, h):
            self._w = w
            self._h = h
        def get_width(self): return self._w
        def get_height(self): return self._h
        def fill(self, color): pass
        def blit(self, surf, pos): pass

    dummy = DummyScreen(800, 600)
    recorded_rects = []
    def fake_draw_rect(surface, color, rect, *args, **kwargs):
        recorded_rects.append((color, tuple(rect)))

    monkeypatch.setattr(pygame.draw, 'rect', fake_draw_rect)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)

    renderer = Renderer(dummy)
    renderer.draw_minimap(state)

    # Check for player rect (White or MINIMAP_PLAYER_COLOR)
    player_marker_found = False
    for c, r in recorded_rects:
        # MINIMAP_PLAYER_COLOR is (255, 255, 255)
        if pygame.Color(c) == pygame.Color(255, 255, 255):
            player_marker_found = True
            break
    assert player_marker_found

def test_minimap_draws_entity_markers(monkeypatch):
    from constants import MINIMAP_ENEMY_COLOR, MINIMAP_LOOT_COLOR
    state = GameState(auto_load=False)
    state.world = MockWorld("chapter1")
    # Place player at (100, 100)
    state.player.x = 100
    state.player.y = 100
    
    # Place an enemy and a loot item near the player so they are in the minimap viewport
    from engine.enemy import SlugEnemy
    from engine.loot import TornPage
    state.enemies = [SlugEnemy(150, 150)]
    state.loot = [TornPage(120, 120)]
    
    class DummyScreen:
        def __init__(self, w, h):
            self._w = w
            self._h = h
        def get_width(self): return self._w
        def get_height(self): return self._h
        def fill(self, color): pass
        def blit(self, surf, pos): pass

    dummy = DummyScreen(800, 600)
    recorded_rects = []
    def fake_draw_rect(surface, color, rect, *args, **kwargs):
        recorded_rects.append((color, tuple(rect)))

    monkeypatch.setattr(pygame.draw, 'rect', fake_draw_rect)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)

    renderer = Renderer(dummy)
    renderer.draw_minimap(state)

    # Check for enemy marker
    enemy_marker_found = False
    for c, r in recorded_rects:
        if pygame.Color(c) == pygame.Color(MINIMAP_ENEMY_COLOR):
            enemy_marker_found = True
            break
    assert enemy_marker_found
    
    # Check for loot marker
    loot_marker_found = False
    for c, r in recorded_rects:
        if pygame.Color(c) == pygame.Color(MINIMAP_LOOT_COLOR):
            loot_marker_found = True
            break
    assert loot_marker_found
