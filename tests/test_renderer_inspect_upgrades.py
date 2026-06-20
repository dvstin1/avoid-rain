"""Test that the renderer displays character upgrades in the inspect HUD panel."""
# pylint: disable=no-member
import pygame
from rendering.renderer import Renderer
from engine.game_state import GameState
from constants import SCREEN_WIDTH, SCREEN_HEIGHT

def test_renderer_shows_inspect_upgrades(monkeypatch):
    """Verify that player level, modifiers, and passive effects render in the inspect HUD."""
    state = GameState(auto_load=False)
    state.inspect_active = True

    # Customize player upgrades and modifiers
    state.player.stats = {
        "attack_modifier": 15,  # level 4
        "max_hp_modifier": 20,  # level 3
        "edification": 6
    }
    # Add a passive weapon modifier to check passive effects list
    state.player.weapons = [
        {
            "name": "Anomalous Quill",
            "damage": 12,
            "modifiers": {
                "slow_hp_regen": 2
            }
        }
    ]

    class DummyScreen:
        """A mock screen class to capture blits and retrieve size."""
        def __init__(self, w, h):
            self._w = w
            self._h = h
        def get_width(self):
            """Return screen width."""
            return self._w
        def get_height(self):
            """Return screen height."""
            return self._h
        def fill(self, color):
            """Mock fill operation."""
        def blit(self, surf, pos):
            """Mock blit operation."""

    dummy = DummyScreen(SCREEN_WIDTH, SCREEN_HEIGHT)

    recorded = []
    class DummyFont:
        """A mock font class to capture rendered text."""
        def render(self, text, _aa, _color=None):
            """Record and render dummy surface."""
            recorded.append(text)
            return pygame.Surface((40, 10), pygame.SRCALPHA)
        def size(self, text):
            """Return mock size of text."""
            return (len(text) * 8, 12)

    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: DummyFont())
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)
    monkeypatch.setattr(pygame.draw, 'rect', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'line', lambda *a, **k: None)

    renderer = Renderer(dummy)
    renderer.render(state)

    # Assert that our upgrades are displayed in the inspect HUD panel
    assert 'CHARACTER' in recorded
    assert 'Understanding: Lvl 6' in recorded
    assert 'Prowess: Lvl 4 (+15 Atk)' in recorded
    assert 'Fortification: Lvl 3 (+20 HP)' in recorded
    assert 'Slow regen: +2.0/s' in recorded
