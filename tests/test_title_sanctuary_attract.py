# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Title Screen 2.5D Sanctuary Dusk Diorama & Two-Stage Attract Flow."""
# pylint: disable=no-member,protected-access
import os
from types import SimpleNamespace

import pygame
import pytest

import constants
import main as game_main
from engine.game_state import GameState
from engine.title_menu import TitleMenu, TitleMenuState
from rendering.renderer import Renderer


def _make_state():
    """Create a clean offline GameState for title event and render tests."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    return state


def test_title_menu_attract_state_defaults_reveal_and_auto_reveal():
    """TitleMenu defaults to menu_revealed=False, reveal_menu() restarts unroll, and sub-views auto-reveal."""
    tm = TitleMenu(has_save=True)
    assert tm.menu_revealed is False
    assert tm.transition_progress == 0.0

    # MenuBase.update_transition(dt) itself remains unblocked
    tm.update_transition(constants.MENU_TRANSITION_DURATION * 0.5)
    assert tm.transition_progress == pytest.approx(0.5, abs=1e-6)

    # reveal_menu() sets menu_revealed=True and resets parchment unroll to 0.0
    tm.reveal_menu()
    assert tm.menu_revealed is True
    assert tm.transition_progress == 0.0
    tm.update_transition(constants.MENU_TRANSITION_DURATION)
    assert tm.transition_progress == 1.0

    # Explicit menu_revealed=True constructor option
    tm_open = TitleMenu(has_save=False, menu_revealed=True)
    assert tm_open.menu_revealed is True

    # Leaving TitleMenuState.MAIN automatically reveals the menu
    tm_sub = TitleMenu(has_save=True)
    assert tm_sub.menu_revealed is False
    tm_sub.state = TitleMenuState.CONTROLS
    assert tm_sub.menu_revealed is True

    tm_confirm = TitleMenu(has_save=True)
    assert tm_confirm.menu_revealed is False
    tm_confirm.state = TitleMenuState.CONFIRM_NEW_GAME
    assert tm_confirm.menu_revealed is True


def test_handle_title_events_first_press_attract_gate_keyboard_mouse_gamepad(monkeypatch):
    """First keypress/click/gamepad button switches input mode, plays confirm SFX, and reveals without confirming."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if not pygame.get_init():
        pygame.init()
    state = _make_state()
    played_sfx = []
    audio = SimpleNamespace(play_sfx=lambda name, **kw: played_sfx.append(name))

    try:
        # 1. Keyboard K_RETURN on attract screen reveals menu without confirming Continue/New Draft
        state.input_mode = constants.INPUT_MODE_GAMEPAD
        tm = TitleMenu(has_save=True)
        monkeypatch.setattr(
            pygame.event,
            "get",
            lambda: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")],
        )
        in_title, running, _ = game_main.handle_title_events(state, None, tm, audio_manager=audio)
        assert (in_title, running) == (True, True)
        assert state.input_mode == constants.INPUT_MODE_KEYBOARD
        assert tm.menu_revealed is True
        assert tm.was_confirmed() is False
        assert played_sfx == ["menu_confirm.ogg"]

        # Second K_RETURN now confirms the selected option normally
        monkeypatch.setattr(
            pygame.event,
            "get",
            lambda: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r")],
        )
        game_main.handle_title_events(state, None, tm, audio_manager=audio)
        assert tm.was_confirmed() is True

        # 2. Gamepad JOYBUTTONDOWN on attract screen switches to GAMEPAD, plays SFX, reveals without confirming
        played_sfx.clear()
        state.input_mode = constants.INPUT_MODE_KEYBOARD
        tm_gp = TitleMenu(has_save=True)
        monkeypatch.setattr(
            pygame.event,
            "get",
            lambda: [pygame.event.Event(pygame.JOYBUTTONDOWN, button=0)],
        )
        game_main.handle_title_events(state, None, tm_gp, audio_manager=audio)
        assert state.input_mode == constants.INPUT_MODE_GAMEPAD
        assert tm_gp.menu_revealed is True
        assert tm_gp.was_confirmed() is False
        assert played_sfx == ["menu_confirm.ogg"]

        # 3. Mouse click on attract screen reveals menu without confirming
        played_sfx.clear()
        tm_mouse = TitleMenu(has_save=False)
        monkeypatch.setattr(
            pygame.event,
            "get",
            lambda: [pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(200, 200))],
        )
        game_main.handle_title_events(state, None, tm_mouse, audio_manager=audio)
        assert tm_mouse.menu_revealed is True
        assert tm_mouse.was_confirmed() is False
        assert played_sfx == ["menu_confirm.ogg"]

        # 4. pygame.QUIT still exits immediately even while menu_revealed is False
        tm_quit = TitleMenu(has_save=False)
        monkeypatch.setattr(pygame.event, "get", lambda: [pygame.event.Event(pygame.QUIT)])
        in_title, running, _ = game_main.handle_title_events(state, None, tm_quit, audio_manager=audio)
        assert (in_title, running) == (False, False)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_title_sanctuary_diorama_caching_attract_and_revealed_rendering(monkeypatch):
    """Verify 2.5D Sanctuary backdrop caching, attract vs revealed rendering, and legacy menu=0 compatibility."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if not pygame.get_init():
        pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = _make_state()

    unroll_calls = []
    orig_unroll = renderer._draw_parchment_unroll

    def spy_unroll(content_surf, dest_topleft, t_state, draw_roller=True):
        unroll_calls.append((dest_topleft, dict(t_state)))
        return orig_unroll(content_surf, dest_topleft, t_state, draw_roller=draw_roller)

    monkeypatch.setattr(renderer, "_draw_parchment_unroll", spy_unroll)

    try:
        # 1. _get_title_sanctuary_backdrop() builds crisp scaled backdrop and caches by (sw, sh)
        bg_a = renderer._get_title_sanctuary_backdrop(constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        bg_b = renderer._get_title_sanctuary_backdrop(constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        assert bg_a is bg_b
        assert bg_a.get_size() == (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)

        bg_small = renderer._get_title_sanctuary_backdrop(640, 360)
        assert bg_small is not bg_a
        assert bg_small.get_size() == (640, 360)

        # Verify twilight sky + reflecting pond diorama pixels are distinct from solid black
        sky_px = bg_a.get_at((16, 16))
        pond_px = bg_a.get_at((constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT - 24))
        assert (sky_px.r, sky_px.g, sky_px.b) != (0, 0, 0)
        assert (pond_px.r, pond_px.g, pond_px.b) != (0, 0, 0)

        # 2. Attract mode (menu_revealed=False): skips parchment unroll & incompatible-save warning
        state.stats = SimpleNamespace(is_revision_compatible=False)
        tm = TitleMenu(has_save=True)
        assert tm.menu_revealed is False
        unroll_calls.clear()
        rendered_texts = []
        orig_render = renderer.small_font.render

        def spy_small_render(text, antialias, color, *args, **kwargs):
            rendered_texts.append(str(text))
            return orig_render(text, antialias, color, *args, **kwargs)

        monkeypatch.setattr(renderer.small_font, "render", spy_small_render)

        renderer.draw_title_screen(tm, state)
        assert not unroll_calls
        assert not any("Incompatible older save" in txt for txt in rendered_texts)

        # Verify attract prompt area around (sw // 2, int(sh * 0.72)) has drawn prompt pixels
        prompt_y = int(constants.SCREEN_HEIGHT * constants.TITLE_ATTRACT_PROMPT_Y_RATIO)
        prompt_band_diff = False
        for x in range(constants.SCREEN_WIDTH // 2 - 120, constants.SCREEN_WIDTH // 2 + 120, 6):
            if screen.get_at((x, prompt_y)) != bg_a.get_at((x, prompt_y)):
                prompt_band_diff = True
                break
        assert prompt_band_diff is True

        # 3. Revealed mode (menu_revealed=True): draws parchment unroll & incompatible-save warning
        tm.reveal_menu()
        tm.finish_transition()
        unroll_calls.clear()
        rendered_texts.clear()
        renderer.draw_title_screen(tm, state)
        assert len(unroll_calls) == 1
        assert unroll_calls[0][1]["settled"] is True
        assert any("Incompatible older save" in txt for txt in rendered_texts)

        # 4. Legacy menu=0 call defaults to revealed & settled
        unroll_calls.clear()
        renderer.draw_title_screen(menu=0, state=state)
        assert len(unroll_calls) == 1
        assert unroll_calls[0][1]["settled"] is True
    finally:
        state.shutdown_save_worker(timeout=1.0)
