"""Unit tests for the minimap rendering behavior in Renderer.draw_minimap.

The tests monkeypatch pygame.draw.rect to capture draw calls and assert that
minimap-drawn rectangles appear in the top-left minimap area.
"""
import pygame
from rendering.renderer import Renderer
from engine.game_state import GameState
from constants import MINIMAP_WIDTH, MINIMAP_HEIGHT, MINIMAP_PADDING, GRID_WIDTH, GRID_HEIGHT, TILE_SIZE


def test_minimap_draws_player_and_walls(monkeypatch):
    state = GameState()
    # Place a wall near top-left of the world and put player nearby
    state.world.grid[1][1] = 1
    state.player.x = 1 * 40 + 5
    state.player.y = 1 * 40 + 5
    # Also place a distant wall far away that should be outside the minimap viewport
    h = len(state.world.grid)
    w = len(state.world.grid[0]) if h > 0 else 0
    far_x = min( max(2, w - 3), w - 1)
    far_y = min( max(2, h - 3), h - 1)
    state.world.grid[far_y][far_x] = 1

    class DummyScreen:
        def __init__(self, w, h):
            self._w = w
            self._h = h
        def get_width(self):
            return self._w
        def get_height(self):
            return self._h
        def fill(self, color):
            pass
        def blit(self, surf, pos):
            pass

    dummy = DummyScreen(800, 600)

    recorded = []

    def fake_draw_rect(surface, color, rect, *args, **kwargs):
        # record rect tuple; surface arg comes from our dummy screen or elsewhere
        recorded.append(tuple(rect))

    monkeypatch.setattr(pygame.draw, 'rect', fake_draw_rect)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)
    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: type('F', (), {'render': lambda self, t, a, c: type('S', (), {'get_rect': lambda self, **kw: type('R', (), {'width': 40, 'height': 10})()})()})())
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)

    renderer = Renderer(dummy)
    renderer.render(state)

    # Filter recorded rects that lie within minimap area (top-left region)
    minimap_rects = [r for r in recorded if r[0] >= MINIMAP_PADDING and r[0] <= MINIMAP_PADDING + MINIMAP_WIDTH and r[1] >= MINIMAP_PADDING and r[1] <= MINIMAP_PADDING + MINIMAP_HEIGHT]
    # Expect at least one wall rect and one player rect within minimap area
    assert len(minimap_rects) >= 2
    # Optionally ensure a small player-sized rect exists
    player_marker_found = any(r[2] <= 6 and r[3] <= 6 for r in minimap_rects)
    assert player_marker_found

def test_minimap_draws_compass_indicators(monkeypatch):
    from constants import MINIMAP_WIDTH, MINIMAP_HEIGHT, MINIMAP_PADDING
    state = GameState()
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
    recorded = []
    def fake_draw_rect(surface, color, rect, *args, **kwargs):
        recorded.append((color, tuple(rect)))

    monkeypatch.setattr(pygame.draw, 'rect', fake_draw_rect)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)
    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: type('F', (), {'render': lambda self, t, a, c: type('S', (), {'get_rect': lambda self, **kw: type('R', (), {'width': 40, 'height': 10})()})()})())
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)

    renderer = Renderer(dummy)
    renderer.render(state)

    # Compass indicators are drawn with COLOR_WHITE (or (255, 255, 255))
    # and should be at the edge of the minimap.
    # The minimap bounds are [PADDING, PADDING + WIDTH] x [PADDING, PADDING + HEIGHT]
    
    def is_on_edge(rect):
        x, y, w, h = rect
        on_left = abs(x - MINIMAP_PADDING) <= 2
        on_right = abs(x + w - (MINIMAP_PADDING + MINIMAP_WIDTH)) <= 2
        on_top = abs(y - MINIMAP_PADDING) <= 2
        on_bottom = abs(y + h - (MINIMAP_PADDING + MINIMAP_HEIGHT)) <= 2
        return on_left or on_right or on_top or on_bottom

    compass_rects = [r for c, r in recorded if (c == (255, 255, 255) or c == "white") and is_on_edge(r)]
    
    # We expect at least one indicator for our objective
    assert len(compass_rects) >= 1

def test_minimap_draws_entity_markers(monkeypatch):
    from constants import MINIMAP_ENEMY_COLOR, MINIMAP_LOOT_COLOR
    state = GameState()
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
    recorded = []
    def fake_draw_rect(surface, color, rect, *args, **kwargs):
        recorded.append((color, tuple(rect)))

    monkeypatch.setattr(pygame.draw, 'rect', fake_draw_rect)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)
    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: type('F', (), {'render': lambda self, t, a, c: type('S', (), {'get_rect': lambda self, **kw: type('R', (), {'width': 40, 'height': 10})()})()})())
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)

    renderer = Renderer(dummy)
    renderer.render(state)

    # Check for enemy marker
    enemy_marker_found = any(c == MINIMAP_ENEMY_COLOR for c, r in recorded)
    assert enemy_marker_found
    
    # Check for loot marker
    loot_marker_found = any(c == MINIMAP_LOOT_COLOR for c, r in recorded)
    assert loot_marker_found
