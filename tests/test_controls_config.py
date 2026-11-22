"""
Unit tests for Batch 7 — Interactive Remappable Controls Config Screen & Persistent Keybindings:
1. DEFAULT_KEYBINDINGS, format_key_name(), and legacy save hydration in StatisticsTracker.
2. GameState.set_keybinding() conflict swap, ESC guard, get_key_label(), reset_keybindings(),
   and persistence across save/hydrate_from_disk() and reset_to_new_game().
3. ControlsConfigMenu row ordering, navigation, capture, ESC cancel, Reset to Defaults, and Back.
4. main.py handle_game_events() / handle_title_events() reading rebound keys and routing CONTROLS state.
5. Renderer.draw_controls_overlay() rendering cleanly in normal and key-capture modes.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
import main as game_main
from engine.game_state import GameState
from engine.pause_menu import PauseMenu, PauseMenuState
from engine.stats import StatisticsTracker
from engine.title_menu import TitleMenu, TitleMenuState
from engine.world import Respite
from rendering.renderer import Renderer
from ui.menu import ControlsConfigMenu


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_keybinding_defaults_formatting_and_legacy_hydration(tmp_path):
    """Verify format_key_name labels and legacy save_data.json hydration without revision bump."""
    assert constants.format_key_name(pygame.K_SPACE) == "SPACE"
    assert constants.format_key_name(pygame.K_LSHIFT) == "LSHIFT"
    assert constants.format_key_name(pygame.K_TAB) == "TAB"
    assert constants.format_key_name(pygame.K_w) == "W"

    for action in constants.DEFAULT_KEYBINDINGS:
        assert action in constants.KEYBINDING_ACTION_LABELS

    # Legacy save missing "keybindings" hydrates full defaults cleanly and remains compatible
    legacy_path = str(tmp_path / "legacy_save.json")
    legacy_data = {
        "engine_revision": constants.ENGINE_REVISION,
        "player_name": "Archivist",
        "lifetime_stats": {"runs_started": 1, "pages_collected": 0},
    }
    tracker = StatisticsTracker(legacy_data)
    assert tracker.is_revision_compatible is True
    assert tracker.data["keybindings"] == constants.DEFAULT_KEYBINDINGS

    # Partial/corrupt keybindings fall back per-key to DEFAULT_KEYBINDINGS
    partial = StatisticsTracker(
        {
            "engine_revision": constants.ENGINE_REVISION,
            "lifetime_stats": {"runs_started": 1, "pages_collected": 0},
            "discovered_bestiary": {},
            "keybindings": {"block": pygame.K_f, "dash": "not_an_int", "attack": pygame.K_ESCAPE},
        }
    )
    assert partial.data["keybindings"]["block"] == pygame.K_f
    assert partial.data["keybindings"]["dash"] == constants.DEFAULT_KEYBINDINGS["dash"]
    assert partial.data["keybindings"]["attack"] == constants.DEFAULT_KEYBINDINGS["attack"]
    partial.save(legacy_path)
    reloaded = StatisticsTracker.load(legacy_path)
    assert reloaded.data["keybindings"]["block"] == pygame.K_f


def test_gamestate_keybinding_swap_reset_and_persistence(tmp_path):
    """Verify conflict swap keeps every action bound and persists across hydrate_from_disk & reset_to_new_game."""
    save_file = tmp_path / "save_data.json"

    gs = GameState(stats=None, stats_path=str(save_file), auto_load=True)
    gs.network_manager.stop_network()
    try:
        # ESC is reserved and rejected
        assert gs.set_keybinding("block", pygame.K_ESCAPE, save=False) is False
        assert gs.keybindings["block"] == pygame.K_k

        # Rebinding block -> K_LSHIFT (currently dash) cleanly swaps dash -> K_k
        assert gs.set_keybinding("block", pygame.K_LSHIFT, save=False) is True
        assert gs.keybindings["block"] == pygame.K_LSHIFT
        assert gs.keybindings["dash"] == pygame.K_k
        assert gs.get_key_label("block") == "LSHIFT"
        assert gs.get_key_label("dash") == "K"
        # No duplicate keys across all actions
        assert len(set(gs.keybindings.values())) == len(gs.keybindings)

        # Persist to disk, hydrate into a fresh GameState, and survive reset_to_new_game()
        gs.save_stats(str(save_file), wait=True)
        reloaded = StatisticsTracker.load(save_file)
        assert reloaded.data["keybindings"]["block"] == pygame.K_LSHIFT
        assert reloaded.data["keybindings"]["dash"] == pygame.K_k

        gs2 = GameState(stats=reloaded, auto_load=False)
        gs2.network_manager.stop_network()
        try:
            gs2.hydrate_from_disk()
            assert gs2.keybindings["block"] == pygame.K_LSHIFT
            assert gs2.keybindings["dash"] == pygame.K_k

            gs2.reset_to_new_game()
            assert gs2.keybindings["block"] == pygame.K_LSHIFT
            assert gs2.keybindings["dash"] == pygame.K_k

            # Reset to Defaults restores original map
            gs2.reset_keybindings(save=False)
            assert gs2.keybindings == constants.DEFAULT_KEYBINDINGS
        finally:
            gs2.shutdown_save_worker(timeout=1.0)
    finally:
        gs.shutdown_save_worker(timeout=1.0)


def test_controls_config_menu_navigation_capture_cancel_and_reset():
    """Verify ControlsConfigMenu row ordering, capture/cancel flow, Reset to Defaults, and Back."""
    gs = GameState(auto_load=False)
    gs.network_manager.stop_network()
    try:
        menu = ControlsConfigMenu()
        assert menu.rows == list(constants.DEFAULT_KEYBINDINGS.keys()) + ["Reset to Defaults", "Back"]
        assert menu.selected_idx == 0
        assert menu.listening_for_key is False

        # Navigate down to 'block'
        block_idx = menu.rows.index("block")
        menu.navigate(block_idx)
        assert menu.get_selected_row() == "block"

        # Confirm enters listening mode; navigation is locked while listening
        assert menu.confirm(gs, save=False) == "LISTENING"
        assert menu.listening_for_key is True
        menu.navigate(2)
        assert menu.selected_idx == block_idx

        # ESC cancels capture without modifying binding
        assert menu.capture_key(pygame.K_ESCAPE, gs, save=False) == "CANCELLED"
        assert menu.listening_for_key is False
        assert gs.keybindings["block"] == pygame.K_k

        # Re-enter capture and bind block -> J
        assert menu.confirm(gs, save=False) == "LISTENING"
        assert menu.capture_key(pygame.K_j, gs, save=False) == "BOUND"
        assert menu.listening_for_key is False
        assert gs.keybindings["block"] == pygame.K_j

        # Navigate to Reset to Defaults and confirm
        menu.selected_idx = menu.rows.index("Reset to Defaults")
        assert menu.confirm(gs, save=False) == "RESET"
        assert gs.keybindings == constants.DEFAULT_KEYBINDINGS

        # Cancel while not listening returns BACK; confirm on Back returns BACK
        assert menu.cancel() == "BACK"
        menu.selected_idx = menu.rows.index("Back")
        assert menu.confirm(gs, save=False) == "BACK"
        assert menu.selected_idx == 0
    finally:
        gs.shutdown_save_worker(timeout=1.0)


def test_main_reads_rebound_keys_and_routes_controls_menu(monkeypatch):
    """Verify handle_game_events() uses rebound keys and routes Title/Pause CONTROLS cleanly."""
    gs = GameState(auto_load=False)
    gs.network_manager.stop_network()
    try:
        gs.set_keybinding("attack", pygame.K_j, save=False)
        gs.set_keybinding("dash", pygame.K_l, save=False)
        gs.set_keybinding("flask", pygame.K_f, save=False)
        gs.set_keybinding("swap", pygame.K_e, save=False)
        gs.set_keybinding("inspect", pygame.K_i, save=False)
        gs.set_keybinding("respite_rest", pygame.K_t, save=False)

        # Old defaults must NOT trigger actions; new rebound keys MUST trigger them
        old_events = [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB),
        ]
        monkeypatch.setattr(pygame.event, "get", lambda: old_events)
        _, atk, flk, dsh, swp, insp, _, _ = game_main.handle_game_events(gs)
        assert (atk, flk, dsh, swp, insp) == (False, False, False, False, False)

        new_events = [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_i),
        ]
        monkeypatch.setattr(pygame.event, "get", lambda: new_events)
        _, atk, flk, dsh, swp, insp, _, _ = game_main.handle_game_events(gs)
        assert (atk, flk, dsh, swp, insp) == (True, True, True, True, True)

        # Rebound respite_rest executes rest when Respite menu is active
        rested = []
        respite = Respite((80, 80), (40, 40))
        monkeypatch.setattr(respite, "execute_rest", lambda *_a, **_kw: rested.append(True))
        gs.active_respite = respite
        monkeypatch.setattr(pygame.event, "get", lambda: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_t)])
        game_main.handle_game_events(gs)
        assert rested == [True]
        gs.active_respite = None

        # Pause menu CONTROLS routes capture without leaking selection to pause_menu
        pm = PauseMenu()
        pm.open()
        pm.state = PauseMenuState.CONTROLS
        cm = ControlsConfigMenu()
        cm.selected_idx = cm.rows.index("block")
        prev_pm_idx = pm.get_selected_index()

        # Enter listening mode, capture 'v', then ESC back to MAIN
        monkeypatch.setattr(
            pygame.event,
            "get",
            lambda: [
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_v),
            ],
        )
        game_main.handle_game_events(gs, pause_menu=pm, controls_menu=cm)
        assert gs.keybindings["block"] == pygame.K_v
        assert pm.state == PauseMenuState.CONTROLS
        assert pm.get_selected_index() == prev_pm_idx

        monkeypatch.setattr(pygame.event, "get", lambda: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)])
        game_main.handle_game_events(gs, pause_menu=pm, controls_menu=cm)
        assert pm.state == PauseMenuState.MAIN

        # Title menu CONTROLS routes Up/Down and ESC back to MAIN
        tm = TitleMenu(has_save=False)
        tm.state = TitleMenuState.CONTROLS
        cm.reset_view()
        monkeypatch.setattr(
            pygame.event,
            "get",
            lambda: [
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
            ],
        )
        game_main.handle_title_events(gs, None, tm, controls_menu=cm)
        assert tm.state == TitleMenuState.MAIN
    finally:
        gs.shutdown_save_worker(timeout=1.0)


def test_draw_controls_overlay_renders_normal_and_capture_modes():
    """Verify Renderer.draw_controls_overlay() renders cleanly across normal, capture, Title, and Pause flows."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    gs = GameState(auto_load=False)
    gs.network_manager.stop_network()
    try:
        cm = ControlsConfigMenu()
        # Normal controls overlay
        renderer.draw_controls_overlay(True, controls_menu=cm, keybindings=gs.keybindings, flip=False)
        # Listening capture overlay
        cm.confirm(gs, save=False)
        assert cm.listening_for_key is True
        renderer.draw_controls_overlay(False, controls_menu=cm, keybindings=gs.keybindings, flip=False)

        # Integrated Title and Pause renderers
        tm = TitleMenu(has_save=False)
        tm.state = TitleMenuState.CONTROLS
        renderer.draw_title_screen(tm, gs, controls_menu=cm)

        pm = PauseMenu()
        pm.open()
        pm.state = PauseMenuState.CONTROLS
        renderer.draw_pause_menu(pm, state=gs, controls_menu=cm)
    finally:
        gs.shutdown_save_worker(timeout=1.0)
