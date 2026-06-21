"""Unit tests for the Map Editor sidebar interaction logic."""
# pylint: disable=no-member,redefined-outer-name,unused-argument
from unittest import mock
import pygame
import pytest
from tools.edit_map import MapEditor
from constants import SCREEN_WIDTH

@pytest.fixture
def mock_pygame(monkeypatch):
    """Fixture to mock pygame display and font calls for headless MapEditor testing."""
    monkeypatch.setattr(pygame.display, 'set_mode', pygame.Surface)
    monkeypatch.setattr(pygame.display, 'set_caption', lambda text: None)

    class DummyFont:
        """Mock font to return dummy render dimensions."""
        def render(self, text, antialias, color=None):
            """Render dummy surface."""
            return pygame.Surface((40, 10), pygame.SRCALPHA)
        def size(self, text):
            """Size of dummy font text."""
            return (len(text) * 8, 12)

    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: DummyFont())

def test_map_editor_sidebar_click_interaction(mock_pygame):
    """Verify that MapEditor handles sidebar clicks correctly without offset mismatch crashes."""
    editor = MapEditor(width=10, height=10)

    # Run a render/draw pass to populate the interaction rects dynamically
    editor.draw_sidebar(SCREEN_WIDTH)

    assert editor.sidebar_size_rect is not None
    assert editor.sidebar_help_rect is not None
    assert len(editor.sidebar_hotbar_rects) == 10

    # 1. Test clicking the Size Button
    size_btn_x = editor.sidebar_size_rect.centerx
    size_btn_y = editor.sidebar_size_rect.centery

    # pylint: disable=too-few-public-methods
    class MockEvent:
        """Mock pygame mouse button event."""
        def __init__(self, event_type, button):
            self.type = event_type
            self.button = button

    # Mock mouse position
    with mock.patch('pygame.mouse.get_pos', return_value=(size_btn_x, size_btn_y)):
        event = MockEvent(pygame.MOUSEBUTTONDOWN, 1)
        editor.handle_mouse_event(event)
        # Should switch to RESIZE_W mode
        assert editor.input_mode == 'RESIZE_W'

    # Reset input mode
    editor.input_mode = None

    # 2. Test clicking a hotbar slot
    slot_idx = 3
    _, _, left_part, _ = editor.sidebar_hotbar_rects[slot_idx]
    click_x = left_part.centerx
    click_y = left_part.centery

    with mock.patch('pygame.mouse.get_pos', return_value=(click_x, click_y)):
        event = MockEvent(pygame.MOUSEBUTTONDOWN, 1)
        editor.handle_mouse_event(event)
        assert editor.selected_slot == slot_idx
