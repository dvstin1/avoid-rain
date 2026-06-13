"""Test that the renderer displays a 'Saved' indicator when last_save_elapsed is small."""
import pygame
from rendering.renderer import Renderer
from engine.game_state import GameState
from constants import SCREEN_WIDTH, SCREEN_HEIGHT


def test_renderer_shows_saved_indicator(monkeypatch):
    state = GameState()
    state.last_save_elapsed = 0.5

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
            # capture blit of indicator by inspecting surf.render call on DummyFont
            pass

    dummy = DummyScreen(SCREEN_WIDTH, SCREEN_HEIGHT)

    recorded = []
    class DummyFont:
        def render(self, text, aa, color):
            recorded.append(text)
            class Surf:
                def get_rect(self):
                    return type('R', (), {'width': 40, 'height': 10})()
            return Surf()

    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: DummyFont())
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)
    monkeypatch.setattr(pygame.draw, 'rect', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'line', lambda *a, **k: None)

    renderer = Renderer(dummy)
    renderer.render(state)

    assert 'Saved' in recorded
