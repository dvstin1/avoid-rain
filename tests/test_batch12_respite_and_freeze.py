"""Unit tests for Batch 12: Respite Menu Ratcheting & Rimecrest Arbiter 2-Hit-in-10s Freeze Rule."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.actor import ActorState
from engine.enemy import RimecrestArbiterBoss
from engine.game_state import GameState
from engine.world import Respite, World


class _RecordingAudio:
    """Minimal audio double capturing played SFX filenames."""

    def __init__(self):
        self.sfx_played = []

    def play_sfx(self, filename, **_kwargs):
        """Record an SFX call."""
        self.sfx_played.append(filename)


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_respite_menu_press_and_release_ratcheting():
    """Verify holding Up/Down in Respite advances only 1 option until neutral release unlatches input."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    audio = _RecordingAudio()
    try:
        respite = Respite((160, 160), (40, 40))
        state.active_respite = respite
        state.player.has_rested_this_session = True
        state.respite_selection_idx = 0
        state.input_ratchet_latched = False
        state.menu_nav_cooldown = 0.0

        # Frame 1: Pressing Down advances 0 -> 1, latches ratchet, sets 0.2s cooldown, and plays navigate SFX
        state._handle_dialogue_ui({"move": (0.0, 1.0)}, False, audio)
        assert state.respite_selection_idx == 1
        assert state.input_ratchet_latched is True
        assert state.menu_nav_cooldown == pytest.approx(0.2)
        assert audio.sfx_played == ["menu_navigate.ogg"]

        # Subsequent frames while STILL holding Down (even after cooldown expires!) must NOT advance further
        for _ in range(5):
            state.menu_nav_cooldown = 0.0
            state._handle_dialogue_ui({"move": (0.0, 1.0)}, False, audio)
        assert state.respite_selection_idx == 1
        assert len(audio.sfx_played) == 1

        # Releasing to neutral unlatches input_ratchet_latched (as main.py ratchet_reset does)
        state.input_ratchet_latched = False
        state.menu_nav_cooldown = 0.0

        # Second deliberate Down press advances 1 -> 2 and re-latches
        state._handle_dialogue_ui({"move": (0.0, 1.0)}, False, audio)
        assert state.respite_selection_idx == 2
        assert state.input_ratchet_latched is True
        assert len(audio.sfx_played) == 2

        # Holding Up while still latched must not move until released
        state.menu_nav_cooldown = 0.0
        state._handle_dialogue_ui({"move": (0.0, -1.0)}, False, audio)
        assert state.respite_selection_idx == 2

        # Release to neutral, then Up moves 2 -> 1
        state.input_ratchet_latched = False
        state.menu_nav_cooldown = 0.0
        state._handle_dialogue_ui({"move": (0.0, -1.0)}, False, audio)
        assert state.respite_selection_idx == 1
        assert state.input_ratchet_latched is True
        assert len(audio.sfx_played) == 3
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_rimecrest_two_hit_in_ten_seconds_freeze_and_expiry():
    """Verify Hit 1 (HALBERD or FROST_BREATH) chills for 10s, Hit 2 freezes, and >10s clears chill."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    audio = _RecordingAudio()
    state.audio_manager = audio
    try:
        state.world = World("frozen_peaks")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.in_sanctuary = False
        state.player.x, state.player.y = 300.0, 240.0
        state.player.hp = state.player.max_hp

        boss = RimecrestArbiterBoss(200.0, 210.0)
        boss.facing = (1.0, 0.0)
        state.enemies = [boss]
        idle_actions = {
            "move": (0.0, 0.0), "attack": False, "block": False,
            "dash": False, "flask": False, "swap": False,
        }

        # 1. Hit 1 via HALBERD sweep applies 0.5 chill + 10.0s window without freezing
        boss.attack_mode = "HALBERD"
        boss.state = ActorState.STRIKE
        boss.combat_timer = 0.85
        boss.has_hit_this_attack = False
        boss._update_strike(0.1, state)
        assert state.player.frost_exposure == pytest.approx(0.5)
        assert state.player.frost_window_timer == pytest.approx(constants.RIMECREST_FREEZE_WINDOW)
        assert state.player.frozen_hits_remaining == 0

        # 2. Wait 9.0s (< 10.0s window): chill stays steady at 0.5
        state._update_player_lifecycle(9.0, idle_actions, False, audio)
        assert state.player.frost_exposure == pytest.approx(0.5)
        assert state.player.frost_window_timer == pytest.approx(1.0)

        # 3. Wait 1.2s more (total > 10.0s without a second hit): chill clears to 0.0
        state._update_player_lifecycle(1.2, idle_actions, False, audio)
        assert state.player.frost_exposure == 0.0
        assert state.player.frost_window_timer == 0.0

        # 4. Subsequent FROST_BREATH contact (even entering mid-strike!) now counts as Hit 1 again (0.5, not frozen)
        boss.attack_mode = "FROST_BREATH"
        boss.state = ActorState.STRIKE
        boss.combat_timer = 0.85
        boss._breath_hit_applied = False
        boss._breath_sfx_played = False
        # Start player outside cone on frame 1, then move into cone on frame 2
        state.player.x = 60.0
        boss._update_strike(0.1, state)
        assert state.player.frost_exposure == 0.0
        assert boss._breath_hit_applied is False

        state.player.x = 300.0
        boss._update_strike(0.1, state)
        assert state.player.frost_exposure == pytest.approx(0.5)
        assert state.player.frost_window_timer == pytest.approx(10.0)
        assert state.player.frozen_hits_remaining == 0
        assert boss._breath_hit_applied is True

        # Staying in same breath cone must NOT double-freeze on the same breath attack
        boss._update_strike(0.1, state)
        assert state.player.frost_exposure == pytest.approx(0.5)
        assert state.player.frozen_hits_remaining == 0

        # 5. Hit 2 via HALBERD within 10s immediately freezes into 3-Dash Ice Block and plays ICE_CRACK_SFX
        boss.attack_mode = "HALBERD"
        boss.state = ActorState.STRIKE
        boss.combat_timer = 0.85
        boss.has_hit_this_attack = False
        boss.cooldown_timer = 0.0
        state.player.stagger_timer = 0.0
        state.player.state = state.player.state.IDLE
        boss._update_strike(0.1, state)
        assert state.player.frozen_hits_remaining == constants.FROZEN_ICE_BLOCK_HITS
        assert state.player.frost_exposure == 0.0
        assert state.player.frost_window_timer == 0.0
        assert state.player.just_cracked_ice is True

        state._update_player_lifecycle(0.05, idle_actions, False, audio)
        assert constants.ICE_CRACK_SFX in audio.sfx_played
    finally:
        state.shutdown_save_worker(timeout=1.0)
