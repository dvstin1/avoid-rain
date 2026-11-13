"""Unit tests for PauseMenu navigation, Debug Text toggle, and persistence."""
# pylint: disable=no-member,too-few-public-methods
import pygame
from engine.pause import PauseHandler
from engine.pause_menu import PauseMenu
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from rendering.renderer import Renderer
from constants import SCREEN_WIDTH, SCREEN_HEIGHT


def test_open_close_and_toggle():
    """Verify PauseMenu open, close, and toggle synchronize with PauseHandler."""
    ph = PauseHandler()
    pm = PauseMenu(ph)
    assert not pm.is_open()
    pm.open()
    assert pm.is_open()
    assert ph.is_paused()
    pm.close()
    assert not pm.is_open()
    assert not ph.is_paused()
    # toggle
    pm.toggle()
    assert pm.is_open()
    pm.toggle()
    assert not pm.is_open()


def test_default_pause_handler_created():
    """Verify default PauseHandler is created when omitted."""
    pm = PauseMenu()
    assert not pm.is_open()
    pm.open()
    assert pm.is_open()
    assert pm.pause_handler.is_paused()
    pm.close()
    assert not pm.pause_handler.is_paused()


def test_request_quit_flag():
    """Verify navigating to Quit and confirming sets the quit request flag."""
    pm = PauseMenu()
    assert not pm.should_quit()
    pm.open()
    # Options: ["Resume", "Controls", "Debug Text: OFF", "Screen Shake: ON", "Quit"] -> index 4 is Quit
    for _ in range(4):
        pm.navigate('down')
    assert pm.get_selected_index() == 4
    pm.confirm()
    assert pm.should_quit()
    pm.clear_quit()
    assert not pm.should_quit()


def test_confirm_resume_closes_menu():
    """Verify confirming Resume closes the pause menu."""
    pm = PauseMenu()
    pm.open()
    assert pm.is_open()
    # Confirm resume (default selected)
    pm.confirm()
    assert not pm.is_open()


def test_debug_text_toggle_and_persistence(tmp_path):
    """Verify Debug Text defaults to OFF, toggles in PauseMenu, and persists in save_data.json."""
    save_file = tmp_path / "save_data.json"
    gs = GameState(stats=None, stats_path=str(save_file), auto_load=True)
    try:
        assert gs.debug_text_enabled is False
        assert gs.stats.data["debug_text_enabled"] is False

        pm = PauseMenu(
            debug_text_enabled=gs.debug_text_enabled,
            on_toggle_debug=lambda val: gs.set_debug_text_enabled(val, save=True),
        )
        assert "Debug Text: OFF" in pm.get_options()

        pm.open()
        # Navigate to index 2 ("Debug Text: OFF")
        pm.navigate('down')
        pm.navigate('down')
        assert pm.get_selected_index() == 2
        pm.confirm()

        assert pm.debug_text_enabled is True
        assert "Debug Text: ON" in pm.get_options()
        assert gs.debug_text_enabled is True
        assert gs.stats.data["debug_text_enabled"] is True

        # Wait for background save and reload from disk
        gs.save_stats(str(save_file), wait=True)
        reloaded = StatisticsTracker.load(save_file)
        assert reloaded.data["debug_text_enabled"] is True
    finally:
        gs.shutdown_save_worker(timeout=1.0)


def test_renderer_gates_debug_text_until_enabled(monkeypatch):
    """Verify Renderer hides audio/input debug text when debug_text_enabled is False."""
    state = GameState(auto_load=False)
    rendered_strings = []

    class DummyScreen:
        """Mock screen for headless rendering."""
        def get_width(self):
            """Return width."""
            return SCREEN_WIDTH

        def get_height(self):
            """Return height."""
            return SCREEN_HEIGHT

        def fill(self, _color):
            """Mock fill."""

        def blit(self, _surf, _pos):
            """Mock blit."""

        def get_rect(self):
            """Return mock rect."""
            return pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

    class DummyFont:
        """Mock font recording rendered text strings."""
        def render(self, text, _aa, _color=None):
            """Record rendered string and return surface."""
            rendered_strings.append(str(text))
            return pygame.Surface((40, 10), pygame.SRCALPHA)

        def size(self, text):
            """Return size tuple."""
            return (len(str(text)) * 8, 12)

    class DummyAudio:
        """Mock audio manager with debug status."""
        current_track = "ambient_sanctuary.ogg"
        recent_sfx = [{"name": "quill_swipe.ogg", "time": 1.5}]

    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: DummyFont())
    monkeypatch.setattr(pygame.display, 'flip', lambda: None)
    monkeypatch.setattr(pygame.draw, 'rect', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'circle', lambda *a, **k: None)
    monkeypatch.setattr(pygame.draw, 'line', lambda *a, **k: None)

    renderer = Renderer(DummyScreen())
    audio = DummyAudio()

    # 1. Default (debug_text_enabled = False): no audio or input debug strings
    state.set_debug_text_enabled(False, save=False)
    rendered_strings.clear()
    renderer.render(state, audio_manager=audio)
    renderer.draw_title_screen(menu=0, state=state)
    assert not any("AUDIO_OSD" in s for s in rendered_strings)
    assert not any("DEBUG_AUDIO" in s for s in rendered_strings)
    assert not any("[ Input:" in s for s in rendered_strings)

    # 2. Enabled (debug_text_enabled = True): audio and input debug strings are rendered
    state.set_debug_text_enabled(True, save=False)
    rendered_strings.clear()
    renderer.render(state, audio_manager=audio)
    renderer.draw_title_screen(menu=0, state=state)
    assert any("AUDIO_OSD" in s for s in rendered_strings)
    assert any("DEBUG_AUDIO" in s for s in rendered_strings)
    assert any("[ Input:" in s for s in rendered_strings)


def test_screen_shake_toggle_and_suppression(tmp_path, monkeypatch):
    """Verify Screen Shake defaults to ON, toggles in PauseMenu, and gates shake impulses."""
    save_file = tmp_path / "save_data.json"
    gs = GameState(stats=None, stats_path=str(save_file), auto_load=True)
    try:
        assert gs.screen_shake_enabled is True
        assert gs.stats.data["screen_shake_enabled"] is True

        pm = PauseMenu(
            screen_shake_enabled=gs.screen_shake_enabled,
            on_toggle_screen_shake=lambda val: gs.set_screen_shake_enabled(val, save=True),
        )
        assert "Screen Shake: ON" in pm.get_options()

        # Navigate to index 3 ("Screen Shake: ON") and toggle OFF
        pm.open()
        pm.navigate('down')
        pm.navigate('down')
        pm.navigate('down')
        assert pm.get_selected_index() == 3
        pm.confirm()

        assert pm.screen_shake_enabled is False
        assert "Screen Shake: OFF" in pm.get_options()
        assert gs.screen_shake_enabled is False
        assert gs.stats.data["screen_shake_enabled"] is False

        # Triggering shake while disabled must keep shake_timer at 0.0
        gs.trigger_shake(0.25)
        assert gs.shake_timer == 0.0

        # Renderer must not apply random shake offset when screen_shake_enabled is False
        pygame.init()
        called_uniform = []
        monkeypatch.setattr("rendering.renderer.random.uniform", lambda a, b: called_uniform.append((a, b)) or 0.0)
        screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        renderer = Renderer(screen)
        gs.shake_timer = 0.25
        renderer.render(gs)
        assert not called_uniform

        # Re-enabling allows shake impulses and renderer shake offset
        pm.confirm()
        assert gs.screen_shake_enabled is True
        gs.trigger_shake(0.25)
        assert gs.shake_timer == 0.25
        renderer.render(gs)
        assert len(called_uniform) == 2
    finally:
        gs.shutdown_save_worker(timeout=1.0)

