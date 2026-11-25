# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for the --offline CLI flag, socket-free offline mode, and README documentation."""
import os
import socket
import pytest

from engine.game_state import GameState
from engine.network_manager import NetworkManager
from engine.stats import StatisticsTracker
from engine.title_menu import TitleMenu
from engine.world import WarpPortal
import main as app_main


def _forbid_sockets(monkeypatch):
    """Fail immediately if any code attempts to create a network socket."""

    def _blocked_socket(*args, **kwargs):
        raise AssertionError(f"Unexpected socket.socket call in --offline mode: args={args}, kwargs={kwargs}")

    monkeypatch.setattr(socket, "socket", _blocked_socket)


def test_parse_args_offline_flag():
    """Verify main.parse_args() parses --offline alone and combined with --fullscreen."""
    default_args = app_main.parse_args([])
    assert default_args.offline is False
    assert default_args.fullscreen is False

    offline_args = app_main.parse_args(["--offline"])
    assert offline_args.offline is True
    assert offline_args.fullscreen is False

    combined = app_main.parse_args(["--fullscreen", "--offline"])
    assert combined.offline is True
    assert combined.fullscreen is True


def test_network_manager_offline_only_never_opens_sockets(monkeypatch):
    """NetworkManager(offline_only=True) must never open sockets or spawn threads across all LAN entry points."""
    _forbid_sockets(monkeypatch)

    mgr = NetworkManager(identity="SoloScholar", offline_only=True)
    assert mgr.offline_only is True
    assert mgr.network_mode == "OFFLINE"

    mgr.start_hosting()
    assert mgr.is_hosting is False
    assert mgr.network_mode == "OFFLINE"
    assert not mgr.threads

    mgr.start_searching()
    assert mgr.is_searching is False
    assert not mgr.threads

    assert mgr.connect_to_host("127.0.0.1") is False
    assert mgr.is_connected is False
    assert mgr.request_map() is None

    mgr.send_full_state({"hp": 100})
    mgr.send_damage_event("enemy", 1, 10.0)
    mgr.send_heal_event(15.0)
    mgr.send_respite_event("REST")
    mgr.send_return_to_sanctuary_event()
    mgr.stop_network()

    assert mgr.network_mode == "OFFLINE"
    assert not mgr.threads


def test_stop_network_when_idle_offline_never_opens_socket(monkeypatch):
    """Even without offline_only, calling stop_network() while OFFLINE must not create a UDP socket."""
    _forbid_sockets(monkeypatch)

    mgr = NetworkManager(identity="IdleScholar", offline_only=False)
    assert mgr.network_mode == "OFFLINE"
    mgr.stop_network()
    assert mgr.network_mode == "OFFLINE"


def test_game_state_offline_only_blocks_all_lan_and_preserves_saved_preference(monkeypatch, tmp_path):
    """GameState(offline_only=True) blocks all sockets across init, LAN probe, hydrate, warp, and shutdown."""
    _forbid_sockets(monkeypatch)

    save_path = os.path.join(tmp_path, "save_data.json")
    seed_stats = StatisticsTracker()
    seed_stats.data["online_mode"] = True
    seed_stats.data["run_state"] = {
        "world_name": "ruins",
        "player": {"x": 120.0, "y": 120.0, "hp": 100.0},
    }
    seed_stats.save(save_path)

    state = GameState(stats=None, stats_path=save_path, auto_load=True, offline_only=True)
    try:
        assert state.offline_only is True
        assert state.online_mode is False
        assert state.network_manager.offline_only is True
        assert state.network_manager.network_mode == "OFFLINE"

        # Attempting to toggle online_mode via API is ignored in --offline mode
        state.set_online_mode(True, save=True)
        assert state.online_mode is False
        assert state.network_manager.network_mode == "OFFLINE"

        # Seamless LAN entry points stay OFFLINE without opening sockets or spawning threads
        assert state.start_seamless_lan(background=False) == "OFFLINE"
        assert state.start_seamless_lan(background=True) == "OFFLINE"
        assert not state.network_manager.threads

        # Hydrating a save that had online_mode=True and a non-sanctuary run_state must NOT auto-host
        state.hydrate_from_disk()
        assert state.online_mode is False
        assert state.network_manager.network_mode == "OFFLINE"
        assert state.network_manager.is_hosting is False

        # Warping out of Sanctuary must NOT auto-host
        portal = WarpPortal("ruins", 120, 120, (0, 0, 40, 40))
        portal.apply_transfer(state)
        assert state.network_manager.network_mode == "OFFLINE"
        assert state.network_manager.is_hosting is False

        # Saving stats during an --offline session preserves the user's saved online_mode preference
        state.save_stats(wait=True)
        reloaded = StatisticsTracker.load(save_path)
        assert reloaded.data["online_mode"] is True

        state.network_manager.stop_network()
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_title_menu_offline_locked_prevents_toggle():
    """TitleMenu with offline_locked=True labels offline lock clearly and refuses toggling to Online."""
    menu = TitleMenu(has_save=True, online_mode=True, offline_locked=True)
    assert menu.online_mode is False
    assert "Mode: Offline (--offline)" in menu.get_options()

    assert menu.toggle_online_mode() is False
    assert menu.online_mode is False
    menu.set_online_mode(True)
    assert menu.online_mode is False
    assert "Mode: Offline (--offline)" in menu.get_options()


def test_readme_documents_offline_flag():
    """README.md documents --offline and explains socket skipping / Windows Firewall avoidance."""
    with open("README.md", "r", encoding="utf-8") as handle:
        readme_text = handle.read()

    assert "--offline" in readme_text
    assert "socket" in readme_text.lower()
    assert "windows firewall" in readme_text.lower()


@pytest.mark.parametrize("flag_set", [["--offline"], ["--offline", "--fullscreen"]])
def test_network_manager_set_offline_only_blocks_subsequent_hosting(monkeypatch, flag_set):
    """Switching a NetworkManager into offline_only mode blocks future socket creation."""
    _forbid_sockets(monkeypatch)
    parsed = app_main.parse_args(flag_set)
    mgr = NetworkManager(identity="GuardCheck", offline_only=False)
    mgr.set_offline_only(parsed.offline)
    assert mgr.offline_only is True
    mgr.start_hosting()
    mgr.start_searching()
    assert mgr.network_mode == "OFFLINE"
    assert not mgr.threads
