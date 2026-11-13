"""Unit tests for dash SFX, Chronicle tome prop/audio, and Chronicler mumbles."""
import random
from unittest.mock import MagicMock
import pygame

import generate_assets
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import Chronicler


def test_dash_sfx_and_coop_seq():
    """Verify dashing triggers player_dash.ogg with jitter and increments local_dash_seq."""
    gs = GameState(auto_load=False)
    mock_audio = MagicMock()
    prev_seq = gs.local_dash_seq

    actions = {
        "move": (1, 0),
        "attack": False,
        "flask": False,
        "dash": True,
        "block": False,
        "swap": False,
    }
    gs.update(0.016, actions, audio_manager=mock_audio)

    assert gs.local_dash_seq == prev_seq + 1
    mock_audio.play_sfx.assert_any_call("player_dash.ogg", pitch_jitter=0.06)


def test_remote_dash_seq_queues_sfx():
    """Verify host queues player_dash.ogg when a co-op client's dash_seq advances."""
    gs = GameState(auto_load=False)
    gs.network_manager.network_mode = "HOST"
    gs.network_manager.identity = "Host"

    gs.apply_remote_state(("127.0.0.1", 50000), {
        "identity": "Client1",
        "x": 200.0,
        "y": 300.0,
        "hp": 100.0,
        "dash_seq": 1,
    })
    assert ("player_dash.ogg", 200.0, 300.0) in gs.pending_remote_sfx


def test_chronicle_audio_hooks_and_sprite():
    """Verify chronicle_open.ogg plays on open/confirm and generate_chronicle builds 40x40 PNG."""
    gs = GameState(auto_load=False)
    mock_audio = MagicMock()
    gs.audio_manager = mock_audio

    gs.open_chronicle_biome_dialog(portal=None)
    mock_audio.play_sfx.assert_called_with("chronicle_open.ogg")

    mock_audio.reset_mock()
    gs.start_two_act_run = MagicMock()
    gs.start_warp = MagicMock(return_value=False)
    gs.confirm_chronicle_run("windy_ridge", "swamp_mire", portal=None)
    mock_audio.play_sfx.assert_called_with("chronicle_open.ogg")

    surf = generate_assets.generate_chronicle(40, 40, rng=random.Random(42))
    assert surf.get_size() == (40, 40)
    assert surf.get_flags() & pygame.SRCALPHA != 0


def test_chronicler_emotion_mumble_sfx():
    """Verify Chronicler selects emotion-appropriate mumble SFX for VICTORY/DEFEAT/INIT."""
    cases = [
        ("VICTORY", "happy", "chronicler_mumble_happy.ogg"),
        ("DEFEAT", "disappointed", "chronicler_mumble_disappointed.ogg"),
        ("INIT", "neutral", "chronicler_mumble_neutral.ogg"),
    ]
    for last_result, expected_emotion, expected_sfx in cases:
        gs = GameState(auto_load=False, stats=StatisticsTracker())
        mock_audio = MagicMock()
        gs.audio_manager = mock_audio
        gs.stats.data["last_run_result"] = last_result

        chronicler = Chronicler((100, 100))
        chronicler.execute_interaction(gs)

        assert gs.active_dialogue is not None
        assert gs.active_dialogue["emotion"] == expected_emotion
        mock_audio.play_sfx.assert_called_with(expected_sfx)
