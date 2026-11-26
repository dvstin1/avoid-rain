# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Section 8 Tactile Menu Transitions (Parchment Unroll / Slide)."""
# pylint: disable=no-member,protected-access
import pytest
import pygame

import constants
from engine.game_state import GameState
from engine.pause_menu import PauseMenu, PauseMenuState
from engine.title_menu import TitleMenu, TitleMenuState
from rendering.renderer import Renderer
from ui.menu import ControlsConfigMenu


def test_ease_out_cubic_and_transition_state_math():
    """Verify pure easing and parchment unroll metrics clamp cleanly across 0.0 -> 1.0."""
    assert constants.ease_out_cubic(-0.5) == 0.0
    assert constants.ease_out_cubic(0.0) == 0.0
    assert constants.ease_out_cubic(1.0) == 1.0
    assert constants.ease_out_cubic(1.5) == 1.0
    assert constants.ease_out_cubic(0.5) == pytest.approx(0.875)

    start = constants.compute_menu_transition_state(0.0)
    mid = constants.compute_menu_transition_state(0.4)
    late = constants.compute_menu_transition_state(0.85)
    settled = constants.compute_menu_transition_state(1.0)

    assert start["settled"] is False
    assert start["reveal_ratio"] == pytest.approx(constants.MENU_TRANSITION_MIN_REVEAL)
    assert start["offset_y"] == pytest.approx(-constants.MENU_TRANSITION_SLIDE_OFFSET_PX)
    assert start["roller_alpha"] == 255
    assert start["backdrop_alpha_scale"] == pytest.approx(0.0)

    assert start["reveal_ratio"] < mid["reveal_ratio"] < late["reveal_ratio"] < settled["reveal_ratio"]
    assert start["offset_y"] < mid["offset_y"] < late["offset_y"] < settled["offset_y"]
    assert mid["roller_alpha"] > late["roller_alpha"] > settled["roller_alpha"]

    assert settled == {
        "progress": 1.0,
        "eased": 1.0,
        "reveal_ratio": 1.0,
        "offset_y": 0.0,
        "alpha": 255,
        "backdrop_alpha_scale": 1.0,
        "roller_alpha": 0,
        "settled": True,
    }
    assert constants.compute_menu_transition_state(2.5) == settled


def test_menu_dt_scaling_reopen_subview_reset_and_nonblocking_input():
    """Verify dt-scaled progression, reopen/sub-view resets, and non-blocking input at progress=0."""
    # 1. Frame-rate independent equivalence on TitleMenu
    tm_fine = TitleMenu(has_save=True)
    tm_coarse = TitleMenu(has_save=True)
    assert tm_fine.transition_progress == 0.0

    # Input remains immediately responsive at progress=0.0
    initial_idx = tm_fine.get_selected_index()
    tm_fine.navigate("down")
    assert tm_fine.get_selected_index() != initial_idx
    tm_fine.confirm()
    assert tm_fine.was_confirmed() is True
    tm_fine.clear_confirm()

    half_dur = constants.MENU_TRANSITION_DURATION * 0.5
    for _ in range(10):
        tm_fine.update_transition(half_dur / 10.0)
    tm_coarse.update_transition(half_dur)
    assert tm_fine.transition_progress == pytest.approx(0.5, abs=1e-6)
    assert tm_fine.transition_progress == pytest.approx(tm_coarse.transition_progress, abs=1e-6)

    # Negative dt never rewinds progress; large dt clamps at 1.0
    tm_fine.update_transition(-0.1)
    assert tm_fine.transition_progress == pytest.approx(0.5, abs=1e-6)
    tm_fine.update_transition(5.0)
    assert tm_fine.transition_progress == 1.0
    assert tm_fine.get_transition_state()["settled"] is True

    # Switching TitleMenu sub-views resets transition cleanly
    tm_fine.state = TitleMenuState.CONTROLS
    assert tm_fine.transition_progress == 0.0
    tm_fine.update_transition(constants.MENU_TRANSITION_SUBVIEW_DURATION)
    assert tm_fine.transition_progress == 1.0

    tm_fine.state = TitleMenuState.CONFIRM_NEW_GAME
    assert tm_fine.transition_progress == 0.0
    # Re-assigning the same state does not spuriously reset progress
    tm_fine.update_transition(constants.MENU_TRANSITION_SUBVIEW_DURATION * 0.5)
    mid_prog = tm_fine.transition_progress
    tm_fine.state = TitleMenuState.CONFIRM_NEW_GAME
    assert tm_fine.transition_progress == pytest.approx(mid_prog)

    # 2. PauseMenu open/close/reopen and sub-view transitions
    pm = PauseMenu()
    pm.open()
    assert pm.transition_progress == 0.0
    # Navigation/confirm are responsive immediately on open
    pm.navigate("down")
    assert pm.get_selected() == "Controls"
    pm.update_transition(constants.MENU_TRANSITION_DURATION)
    assert pm.transition_progress == 1.0

    # Entering Controls sub-view restarts transition with subview duration
    pm.state = PauseMenuState.CONTROLS
    assert pm.transition_progress == 0.0
    pm.update_transition(constants.MENU_TRANSITION_SUBVIEW_DURATION)
    assert pm.transition_progress == 1.0

    # Returning to MAIN restarts transition
    pm.state = PauseMenuState.MAIN
    assert pm.transition_progress == 0.0
    pm.finish_transition()
    assert pm.transition_progress == 1.0

    # Closing and reopening restarts from 0.0
    pm.close()
    pm.open()
    assert pm.transition_progress == 0.0


def test_headless_parchment_unroll_rendering_partial_and_settled(monkeypatch):
    """Verify Title, Pause, and Controls overlays render cleanly at partial and settled unroll states."""
    pygame.init()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    gs = GameState(auto_load=False)
    gs.network_manager.stop_network()
    cm = ControlsConfigMenu()

    recorded_rects = []
    orig_unroll = renderer._draw_parchment_unroll

    def spy_unroll(content_surf, dest_topleft, t_state, draw_roller=True):
        rect = orig_unroll(content_surf, dest_topleft, t_state, draw_roller=draw_roller)
        recorded_rects.append((rect, content_surf.get_size(), dict(t_state)))
        return rect

    monkeypatch.setattr(renderer, "_draw_parchment_unroll", spy_unroll)

    try:
        # 1. Title screen MAIN: partial unroll vs settled
        tm = TitleMenu(has_save=True)
        recorded_rects.clear()
        renderer.draw_title_screen(tm, gs, controls_menu=cm)
        rect_start, full_size, state_start = recorded_rects[-1]
        assert state_start["settled"] is False
        assert rect_start.height < full_size[1]

        tm.update_transition(constants.MENU_TRANSITION_DURATION * 0.4)
        renderer.draw_title_screen(tm, gs, controls_menu=cm)
        rect_mid, _, state_mid = recorded_rects[-1]
        assert rect_start.height < rect_mid.height < full_size[1]
        assert rect_mid.y < int(258)

        tm.finish_transition()
        renderer.draw_title_screen(tm, gs, controls_menu=cm)
        rect_full, _, state_full = recorded_rects[-1]
        assert state_full["settled"] is True
        assert rect_full.height == full_size[1]
        assert rect_full.y == 258
        assert state_mid["progress"] < state_full["progress"]

        # 2. Title screen CONFIRM_NEW_GAME & CONTROLS sub-views
        tm.state = TitleMenuState.CONFIRM_NEW_GAME
        renderer.draw_title_screen(tm, gs, controls_menu=cm)
        confirm_partial, confirm_full_sz, _ = recorded_rects[-1]
        assert confirm_partial.height < confirm_full_sz[1]

        tm.finish_transition()
        renderer.draw_title_screen(tm, gs, controls_menu=cm)
        confirm_settled, _, _ = recorded_rects[-1]
        assert confirm_settled.size == (600, 150)

        tm.state = TitleMenuState.CONTROLS
        renderer.draw_title_screen(tm, gs, controls_menu=cm)
        ctrl_partial, ctrl_full_sz, _ = recorded_rects[-1]
        assert ctrl_partial.height < ctrl_full_sz[1]

        # 3. Pause menu MAIN & CONTROLS: partial unroll vs settled
        pm = PauseMenu()
        pm.open()
        renderer.draw_pause_menu(pm, state=gs, controls_menu=cm)
        pause_partial, pause_full_sz, pause_st_partial = recorded_rects[-1]
        assert pause_st_partial["settled"] is False
        assert pause_partial.height < pause_full_sz[1]

        pm.update_transition(constants.MENU_TRANSITION_DURATION)
        renderer.draw_pause_menu(pm, state=gs, controls_menu=cm)
        pause_settled, _, pause_st_settled = recorded_rects[-1]
        assert pause_st_settled["settled"] is True
        assert pause_settled.height == pause_full_sz[1]
        assert pause_settled.y == constants.SCREEN_HEIGHT // 2 - 78

        pm.state = PauseMenuState.CONTROLS
        renderer.draw_pause_menu(pm, state=gs, controls_menu=cm)
        pctrl_partial, pctrl_full_sz, _ = recorded_rects[-1]
        assert pctrl_partial.height < pctrl_full_sz[1]

        # 4. Backward-compatible bare integer menu calls default to settled (progress=1.0)
        renderer.draw_title_screen(menu=0, state=gs)
        _, _, legacy_title_st = recorded_rects[-1]
        assert legacy_title_st["settled"] is True

        renderer.draw_pause_menu(menu=0, state=gs)
        _, _, legacy_pause_st = recorded_rects[-1]
        assert legacy_pause_st["settled"] is True
    finally:
        gs.shutdown_save_worker(timeout=1.0)
