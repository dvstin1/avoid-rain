# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit tests for Playtest Polish Batch 3 Pass 2A:
1. Three-mode Binder dialog tree ('prompt' -> 'consult' / 'weave') and state transitions.
2. Gamepad Circle (JOYBUTTONDOWN button=1) modal cancel wiring across interactive modals without triggering dash.
3. Compact, uncluttered rendering in draw_binder_weave_menu() for 'prompt' (540x220),
   'consult' (720x260), and 'weave' (780x490 without dialogue paragraph or 'Consult The Binder').
"""
# pylint: disable=no-member,protected-access,duplicate-code
import pygame

import constants
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import Respite
from main import handle_game_events
from rendering.bitmap_font import load_font_or_sysfont
from ui.menu import draw_binder_weave_menu


def _make_state(tmp_path):
    """Create an offline GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_binder_dialog_prompt_to_consult_and_dismiss(tmp_path):
    """Verify open_binder_dialog starts in 'prompt', enters 'consult', and closes on X or Circle."""
    state = _make_state(tmp_path)
    state.open_binder_dialog()
    assert state.binder_dialog is not None
    assert state.binder_dialog["mode"] == "prompt"
    assert state.binder_dialog["prompt_selection"] == 0
    assert state.binder_dialog["status_msg"]

    # Confirm option 0 ('Consult') -> transitions to 'consult' mode
    state.input_ratchet_latched = False
    state._handle_binder_dialog_ui({"move": (0, 0)}, attack_pressed=True)
    assert state.binder_dialog is not None
    assert state.binder_dialog["mode"] == "consult"

    # Pressing Confirm ('X' / Enter) inside 'consult' closes the modal
    state.input_ratchet_latched = False
    state._handle_binder_dialog_ui({"move": (0, 0)}, attack_pressed=True)
    assert state.binder_dialog is None

    # Re-open, enter 'consult', and dismiss via Gamepad Circle (JOYBUTTONDOWN button=1)
    state.open_binder_dialog()
    state.input_ratchet_latched = False
    state._handle_binder_dialog_ui({"move": (0, 0)}, attack_pressed=True)
    assert state.binder_dialog is not None
    assert state.binder_dialog["mode"] == "consult"

    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 1}))
    result = handle_game_events(state)
    assert len(result) == 8
    _, _attack, _flask, dash, _swap, _inspect, _mouse, _audio = result
    assert dash is False
    assert state.binder_dialog is None


def test_binder_dialog_prompt_to_weave_and_compact_options(tmp_path):
    """Verify navigating to 'Present margin scraps' enters 'weave' mode with 10 scripts + Close Loom."""
    state = _make_state(tmp_path)
    state.stats.add_margin_scraps(10)
    state.open_binder_dialog()
    assert state.binder_dialog["mode"] == "prompt"

    # Navigate Down in 'prompt' to select option 1 ('Present margin scraps')
    state.input_ratchet_latched = False
    state.menu_nav_cooldown = 0.0
    state._handle_binder_dialog_ui({"move": (0, 1)}, attack_pressed=False)
    assert state.binder_dialog["prompt_selection"] == 1

    # Confirm option 1 -> transitions to 'weave' mode
    state.input_ratchet_latched = False
    state._handle_binder_dialog_ui({"move": (0, 0)}, attack_pressed=True)
    assert state.binder_dialog["mode"] == "weave"
    assert state.binder_dialog["selection"] == 0
    assert state.binder_dialog["weave_feedback"] == ""

    options = state.get_binder_dialog_options()
    assert len(options) == len(constants.BINDER_SCRIPT_CATALOG) + 1
    assert all(opt["action"] != "speak" for opt in options)
    assert options[-1]["action"] == "close"
    assert options[-1]["name"] == "Close Loom"

    # Weave the first script and verify weave_feedback is populated
    state.input_ratchet_latched = False
    state._handle_binder_dialog_ui({"move": (0, 0)}, attack_pressed=True)
    assert state.binder_dialog["weave_feedback"] != ""

    # Select 'Close Loom' at index len(BINDER_SCRIPT_CATALOG) and confirm
    state.binder_dialog["selection"] = len(constants.BINDER_SCRIPT_CATALOG)
    state.input_ratchet_latched = False
    state._handle_binder_dialog_ui({"move": (0, 0)}, attack_pressed=True)
    assert state.binder_dialog is None


def test_gamepad_circle_cancels_all_interactive_modals_without_dash(tmp_path):
    """Verify Gamepad Circle (button=1) closes chronicle_dialog, active_respite, and active_dialogue."""
    state = _make_state(tmp_path)

    # 1. chronicle_dialog
    state.open_chronicle_biome_dialog()
    assert state.chronicle_dialog is not None
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 1}))
    res1 = handle_game_events(state)
    assert res1[3] is False
    assert state.chronicle_dialog is None

    # 2. active_respite
    respite = Respite((200, 200), (40, 40))
    state.active_respite = respite
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 1}))
    res2 = handle_game_events(state)
    assert res2[3] is False
    assert state.active_respite is None

    # 3. active_dialogue
    state.active_dialogue = {"speaker": "The Chronicler", "text": "Testing modal cancel."}
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.JOYBUTTONDOWN, {"button": 1}))
    res3 = handle_game_events(state)
    assert res3[3] is False
    assert state.active_dialogue is None


def test_draw_binder_weave_menu_all_three_modes_compact_dimensions(tmp_path):
    """Verify draw_binder_weave_menu renders compact 540x220 prompt, 720x260 consult, and 780x490 weave modals."""
    state = _make_state(tmp_path)
    screen = pygame.Surface((1280, 720))
    font = load_font_or_sysfont("ink_sans", 2, "Arial", 24)

    state.open_binder_dialog()
    panel_prompt = draw_binder_weave_menu(screen, font, state)
    assert panel_prompt is not None
    assert (panel_prompt.width, panel_prompt.height) == (540, 220)

    state.binder_dialog["mode"] = "consult"
    panel_consult = draw_binder_weave_menu(screen, font, state)
    assert panel_consult is not None
    assert (panel_consult.width, panel_consult.height) == (720, 260)

    state.binder_dialog["mode"] = "weave"
    state.binder_dialog["weave_feedback"] = "Wove Hemming Script (Minor)."
    panel_weave = draw_binder_weave_menu(screen, font, state)
    assert panel_weave is not None
    assert (panel_weave.width, panel_weave.height) == (780, 490)
