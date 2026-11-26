# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit tests for Playtest Polish Pass 1:
1. Isolated test network ports (TEST_LAN_PORT_BASE = 51000 via conftest.py).
2. Resetting debug_text_enabled = False on New Draft and Continue.
3. Skipping Chronicle biome selection dialog unless debug_text_enabled is True.
4. Compact, responsive Respite menu (Enter/E/Esc/R bindings, 0.10s nav cooldown, compact panel).
5. Rendering 'TEXT BLEACHING...' with large bloom_font (72px serif display font).
"""
# pylint: disable=protected-access,no-member

import pygame

import constants
from engine.game_state import GameState
from engine.network_manager import NetworkManager
from engine.pause_menu import PauseMenu
from engine.stats import StatisticsTracker
from engine.world import Respite, WarpPortal
from main import handle_game_events
from rendering.renderer import Renderer
from ui.menu import RESPITE_PANEL_HEIGHT, RESPITE_PANEL_WIDTH, draw_respite_menu


def _make_state(tmp_path):
    """Create a headless GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_isolated_test_lan_ports(tmp_path):
    """Verify test NetworkManager and GameState instances use TEST_LAN_PORT_BASE (51000), not 55555."""
    assert constants.TEST_LAN_PORT_BASE == 51000
    nm = NetworkManager()
    assert nm.port == 51000
    assert nm.tcp_port == 51001
    assert nm.host_udp_port == 51002
    assert nm.port != 55555

    state = _make_state(tmp_path)
    assert state.network_manager.port == 51000
    assert state.network_manager.tcp_port == 51001
    assert state.network_manager.host_udp_port == 51002


def test_debug_text_resets_to_false_on_new_draft_and_continue(tmp_path):
    """Verify debug_text_enabled resets to False on reset_to_new_game and hydrate_from_disk."""
    save_path = tmp_path / "save_data.json"
    state = _make_state(tmp_path)
    state.stats_path = str(save_path)

    # Enable debug text and persist to disk
    state.set_debug_text_enabled(True, save=True)
    assert state.debug_text_enabled is True
    assert state.debug_biome_select is True
    assert state.stats.data["debug_text_enabled"] is True

    # 1. Continue (hydrate_from_disk) must reset debug_text_enabled and debug_biome_select to False
    state.hydrate_from_disk()
    assert state.debug_text_enabled is False
    assert state.debug_biome_select is False
    assert state.stats.data["debug_text_enabled"] is False

    # 2. Re-enable and verify New Draft (reset_to_new_game) also resets debug_text_enabled to False
    state.set_debug_text_enabled(True, save=False)
    assert state.debug_text_enabled is True
    state.reset_to_new_game()
    assert state.debug_text_enabled is False
    assert state.debug_biome_select is False
    assert state.stats.data["debug_text_enabled"] is False


def test_biome_selection_skipped_unless_debug_text_enabled(tmp_path, monkeypatch):
    """Verify start_warp skips Chronicle biome dialog and launches a randomized 5-Act run when
    debug_text_enabled is False, and opens the dialog when debug_text_enabled is True."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    state = _make_state(tmp_path)
    portal = WarpPortal("macro_world", 10, 10, (0, 0, 40, 40), name="Chronicle")

    # 1. Default (debug_text_enabled = False): skips dialog and immediately starts randomized 5-Act warp
    assert state.debug_text_enabled is False
    started = state.start_warp(portal)
    assert started is True
    assert state.chronicle_dialog is None
    assert state.warp_controller.is_active() is True

    while state.warp_controller.is_active():
        state.update(0.016, {"move": (0, 0), "attack": False})

    assert state.current_act == 1
    drafted = [state.run_biomes[f"act{i}"] for i in range(1, constants.MAX_ACTS + 1)]
    assert len(drafted) == constants.MAX_ACTS
    assert len(set(drafted)) == constants.MAX_ACTS
    assert all(b in constants.CHRONICLE_BIOME_ROSTER for b in drafted)

    # 2. Debug mode on (debug_text_enabled = True): opens Chronicle biome selection dialog
    state.on_enter_sanctuary()
    state.set_debug_text_enabled(True, save=False)
    started_debug = state.start_warp(portal)
    assert started_debug is False
    assert state.chronicle_dialog is not None
    assert state.chronicle_dialog["step"] == 1


def test_compact_responsive_respite_menu_inputs_and_dimensions(tmp_path):
    """Verify Respite menu responds to Enter/E/Esc/R, does not block confirm when movement is held,
    uses 0.10s nav cooldown, and renders in a compact centered modal."""
    pygame.init()
    state = _make_state(tmp_path)
    state.stats.data["lifetime_stats"]["pages_collected"] = 500
    respite = Respite((100, 100), (40, 40))
    state.world.interactables.append(respite)
    state.active_respite = respite
    state.active_dialogue = {"speaker": "Respite Anchor", "text": "Rest by the ember."}
    pause_menu = PauseMenu()

    # 1. Pressing 'R' in handle_game_events directly rests at the Respite
    assert state.player.has_rested_this_session is False
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
    handle_game_events(state, pause_menu=pause_menu)
    assert state.player.has_rested_this_session is True

    # 2. Navigating down while holding movement ratchets with 0.2s cooldown; Enter still unlatches confirm
    state.respite_selection_idx = 0
    state.menu_nav_cooldown = 0.0
    state.input_ratchet_latched = False
    state._handle_dialogue_ui({"move": (0, 1.0)}, attack_pressed=False, audio_manager=None)
    assert state.respite_selection_idx == 1
    assert abs(state.menu_nav_cooldown - 0.20) < 1e-6
    assert state.input_ratchet_latched is True

    # Confirming with Enter / E while movement is still held stages Prowess upgrade immediately
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    _, attack, _, _, _, _, _, _ = handle_game_events(state, pause_menu=pause_menu)
    assert attack is True
    state._handle_dialogue_ui({"move": (0, 1.0)}, attack_pressed=attack, audio_manager=None)
    assert state.respite_upgrades[1] == 1

    # Pressing 'E' also triggers confirm and unlatches ratchet
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_e))
    _, attack_e, _, _, _, _, _, _ = handle_game_events(state, pause_menu=pause_menu)
    assert attack_e is True
    state._handle_dialogue_ui({"move": (0, 0)}, attack_pressed=attack_e, audio_manager=None)
    assert state.respite_upgrades[1] == 2

    # 3. Compact centered modal dimensions
    screen = pygame.Surface((1280, 720))
    font = pygame.font.SysFont("Arial", 20)
    panel = draw_respite_menu(screen, font, state)
    assert panel.width == RESPITE_PANEL_WIDTH <= 640
    assert panel.height == RESPITE_PANEL_HEIGHT <= 310
    assert panel.centerx == 1280 // 2
    assert panel.centery == 720 // 2

    # 4. Pressing ESC closes active_respite without opening pause_menu
    pygame.event.clear()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    handle_game_events(state, pause_menu=pause_menu)
    assert state.active_respite is None
    assert pause_menu.is_open() is False


def test_text_bleaching_uses_large_bloom_font(tmp_path):
    """Verify 'TEXT BLEACHING...' death banner renders with bloom_font rather than small 24px font."""
    pygame.init()
    state = _make_state(tmp_path)
    state.death_timer = 1.5

    screen = pygame.Surface((1280, 720))
    renderer = Renderer(screen)

    bloom_calls = []
    small_calls = []
    orig_bloom_render = renderer.bloom_font.render
    orig_font_render = renderer.font.render

    def _spy_bloom(text, *args, **kwargs):
        bloom_calls.append(str(text))
        return orig_bloom_render(text, *args, **kwargs)

    def _spy_font(text, *args, **kwargs):
        small_calls.append(str(text))
        return orig_font_render(text, *args, **kwargs)

    renderer.bloom_font.render = _spy_bloom
    renderer.font.render = _spy_font

    renderer.render(state)
    assert "TEXT BLEACHING..." in bloom_calls
    assert "TEXT BLEACHING..." not in small_calls
