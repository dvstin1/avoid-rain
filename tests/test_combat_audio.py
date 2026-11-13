"""Unit tests for responsive melee combat audio (sword_swing.ogg & sword_hit.ogg)."""
import os
from unittest.mock import MagicMock

import pygame

from engine.player import PlayerStateEnum
from engine.audio import AudioManager
from engine.enemy import SlugEnemy
from engine.game_state import GameState


def _make_state(tmp_path):
    """Create a headless GameState with a mocked AudioManager."""
    pygame.init()
    state = GameState(auto_load=False, stats_path=str(tmp_path / "stats.json"))
    state.network_manager.stop_network()
    state.enemies = []
    state.world.interactables = []
    audio = MagicMock()
    audio.calculate_spatial_volume.return_value = 0.8
    return state, audio


def test_sword_ogg_files_load_and_play_with_pitch_variance():
    """Verify sword_swing.ogg and sword_hit.ogg load cleanly and support pitch_jitter."""
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    audio = AudioManager()

    for name in ("sword_swing.ogg", "sword_hit.ogg"):
        path = os.path.join("assets", "audio", "sfx", name)
        assert os.path.exists(path)
        snd = pygame.mixer.Sound(path)
        assert 0.10 <= snd.get_length() <= 0.22

    # Play consecutive swings with pitch_jitter and hit impact
    audio.play_sfx("sword_swing.ogg", pitch_jitter=0.06)
    audio.play_sfx("sword_swing.ogg", pitch_jitter=0.06)
    audio.play_sfx("sword_hit.ogg")
    assert "sword_swing.ogg" in audio.sfx_cache
    assert "sword_hit.ogg" in audio.sfx_cache
    assert len(audio.sfx_pitch_cache.get("sword_swing.ogg", [])) >= 1


def test_whiff_plays_only_sword_swing(tmp_path):
    """Attacking with no targets in range triggers sword_swing.ogg only."""
    state, audio = _make_state(tmp_path)
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.attack_timer = 0.2
    state.player.facing = (1.0, 0.0)

    state.update_combat(0.016, True, {"move": (0, 0)}, audio)

    played = [call.args[0] for call in audio.play_sfx.call_args_list]
    assert played == ["sword_swing.ogg"]
    assert state.local_swing_seq == 1
    assert state.local_hit_seq == 0


def test_cleave_plays_single_sword_hit_per_swing(tmp_path):
    """Cleaving 5 enemies in one swing plays sword_swing.ogg once and sword_hit.ogg once."""
    state, audio = _make_state(tmp_path)
    px, py = state.player.get_center()
    state.player.facing = (1.0, 0.0)

    for idx in range(5):
        enemy = SlugEnemy(px + 20, py - 15 + idx * 4, hp=50.0)
        enemy.network_id = 100 + idx
        state.enemies.append(enemy)

    # Frame 1: swing starts and cleaves all 5 enemies
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.attack_timer = 0.2
    state.update_combat(0.016, True, {"move": (0, 0)}, audio)

    # Frame 2: still in ATTACKING state of same swing; another enemy enters range
    late_enemy = SlugEnemy(px + 25, py, hp=50.0)
    late_enemy.network_id = 200
    state.enemies.append(late_enemy)
    state.update_combat(0.016, False, {"move": (0, 0)}, audio)

    played = [call.args[0] for call in audio.play_sfx.call_args_list]
    assert played.count("sword_swing.ogg") == 1
    assert played.count("sword_hit.ogg") == 1
    assert state.local_swing_seq == 1
    assert state.local_hit_seq == 1


def test_coop_remote_combat_audio_sync(tmp_path):
    """Remote player swing_seq and hit_seq trigger spatial sword_swing and sword_hit cues."""
    client, audio = _make_state(tmp_path)
    client.network_manager.network_mode = "CLIENT"
    client.network_manager.identity = "Client1"
    px, py = client.player.get_center()

    # Receive Host UDP snapshot showing Host swung and landed a hit
    client.apply_remote_state(("127.0.0.1", 55555), {
        "identity": "Host",
        "x": px + 50,
        "y": py,
        "hp": 100.0,
        "session_players": [
            {"identity": "Host", "x": px + 50, "y": py, "hp": 100.0, "swing_seq": 1, "hit_seq": 1},
            {"identity": "Client1", "x": px, "y": py, "hp": 100.0, "swing_seq": 0, "hit_seq": 0},
        ],
    })

    assert len(client.pending_remote_sfx) == 2
    client.update_combat(0.016, False, {"move": (0, 0)}, audio)

    played = [call.args[0] for call in audio.play_sfx.call_args_list]
    assert played == ["sword_swing.ogg", "sword_hit.ogg"]
