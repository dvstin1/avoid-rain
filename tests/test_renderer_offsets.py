"""Tests that the Renderer applies camera offsets when drawing entities.

Uses a fake surface and monkeypatches pygame drawing primitives to capture
rectangle draw calls and assert the player rectangle is shifted by the
camera offset.
"""
import pygame
from rendering.renderer import Renderer
from engine.game_state import GameState
from constants import SCREEN_WIDTH, SCREEN_HEIGHT


def test_renderer_uses_camera_offset(monkeypatch):
    # Prepare a game state with player far from origin
    state = GameState()
    state.player.x = 1000
    state.player.y = 800
    # Center camera on player instantly to set internal offset
    state.camera.instant_center(state.player.get_center())
    offset_x, offset_y = state.camera.get_offset()

    # Dummy screen that exposes only the used API
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

    dummy = DummyScreen(SCREEN_WIDTH, SCREEN_HEIGHT)

    # Replace font creation and drawing primitives to avoid initializing SDL
    class DummyFont:
        def render(self, text, aa, color):
            class Surf:
                def get_rect(self, **kwargs):
                    return type('R', (), {'x': 0, 'y': 0, 'width': 0, 'height': 0})()
            return Surf()

    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: DummyFont())

    recorded = []

    def fake_draw_rect(surface, color, rect, *args, **kwargs):
        # Record the rect argument for later inspection
        recorded.append(tuple(rect))
        return None

    monkeypatch.setattr(pygame.draw, 'rect', fake_draw_rect)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'line', lambda *a, **k: None)
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)

    renderer = Renderer(dummy)
    # Render the current state
    renderer.render(state)

    # Compute expected player draw rect
    player = state.player
    expected = (int(player.x - offset_x), int(player.y - offset_y), player.width, player.height)

    assert expected in recorded, f"Expected player rect {expected} in recorded draws: {recorded}"
