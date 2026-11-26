# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Section 1: Gamepad Rumble (Joystick.rumble())."""
# pylint: disable=no-member,protected-access,too-many-locals

import os

import pygame
import pytest

import constants
import main as main_mod
from engine.enemy import Miniboss, SlugEnemy
from engine.game_state import GameState
from engine.pause_menu import PauseMenu
from engine.stats import StatisticsTracker


def _ensure_pygame():
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def test_rumble_impulse_queue_priority_and_clamping():
    """Verify rumble presets queue cleanly, clamp invalid bounds, and drain highest-priority impulse."""
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        assert state.rumble_enabled is True
        assert state.consume_rumble_impulse() is None

        # Queue multiple impulses in one frame -> highest priority (boss_summon > parry > player_damage > combat_hit)
        assert state.trigger_rumble("combat_hit") is True
        assert state.trigger_rumble("parry") is True
        assert state.trigger_rumble("player_damage") is True
        picked = state.consume_rumble_impulse()
        assert picked is not None
        assert picked["preset"] == "parry"
        low, high, dur, prio = constants.RUMBLE_PRESET_PARRY
        assert picked["low_frequency"] == pytest.approx(low)
        assert picked["high_frequency"] == pytest.approx(high)
        assert picked["duration_ms"] == dur
        assert picked["priority"] == prio
        # Queue is drained after consume
        assert state.consume_rumble_impulse() is None

        # Boss summon outranks parry
        state.trigger_rumble("parry")
        state.trigger_rumble("boss_summon")
        boss_imp = state.consume_rumble_impulse()
        assert boss_imp["preset"] == "boss_summon"
        assert boss_imp["duration_ms"] == constants.RUMBLE_PRESET_BOSS_SUMMON[2]

        # Custom impulse clamps [0.0, 1.0]; zero duration / zero intensity rejected
        assert state.trigger_rumble(low_frequency=2.5, high_frequency=-0.5, duration_ms=100, priority=1) is True
        clamped = state.consume_rumble_impulse()
        assert clamped["low_frequency"] == pytest.approx(1.0)
        assert clamped["high_frequency"] == pytest.approx(0.0)
        assert state.trigger_rumble(low_frequency=0.0, high_frequency=0.0, duration_ms=100) is False
        assert state.trigger_rumble(low_frequency=0.5, high_frequency=0.5, duration_ms=0) is False
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_rumble_gameplay_triggers_combat_damage_parry_and_boss_summon():
    """Verify combat hits, player damage (not rain ticks), parries, and boss summon eruptions queue rumble."""
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        # 1. Player takes discrete combat damage -> queues player_damage; rain tick (bypass_stagger=True) does not
        state.player.take_damage(5.0, bypass_stagger=True, game_state=state)
        assert state.consume_rumble_impulse() is None
        state.player.take_damage(10.0, bypass_stagger=False, game_state=state)
        dmg_imp = state.consume_rumble_impulse()
        assert dmg_imp is not None and dmg_imp["preset"] == "player_damage"

        # 2. Enemy parry -> queues parry
        slug = SlugEnemy(state.player.x + 20, state.player.y)
        slug._handle_parry(state)
        parry_imp = state.consume_rumble_impulse()
        assert parry_imp is not None and parry_imp["preset"] == "parry"

        # 3. Armed boss summon (awaiting_proximity=True) does NOT rumble until trigger_boss_summon_eruption()
        boss = Miniboss(state.player.x + 300, state.player.y)
        ritual = state.start_boss_summon(boss, awaiting_proximity=True)
        assert state.consume_rumble_impulse() is None
        assert state.trigger_boss_summon_eruption(ritual) is True
        summon_imp = state.consume_rumble_impulse()
        assert summon_imp is not None and summon_imp["preset"] == "boss_summon"

        # 4. Immediate boss summon eruption queues boss_summon once
        boss2 = Miniboss(state.player.x + 320, state.player.y)
        state.start_boss_summon(boss2, awaiting_proximity=False)
        summon_imp2 = state.consume_rumble_impulse()
        assert summon_imp2 is not None and summon_imp2["preset"] == "boss_summon"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_rumble_pause_menu_toggle_gating_and_persistence(tmp_path, monkeypatch):
    """Verify Gamepad Rumble defaults ON, toggles in PauseMenu, gates impulses, and persists in save_data.json."""
    save_file = tmp_path / "save_data.json"
    monkeypatch.setattr("engine.stats.DEFAULT_PATH", save_file)
    gs = GameState(stats=None, stats_path=str(save_file), auto_load=True)
    try:
        assert gs.rumble_enabled is True
        assert gs.stats.data["rumble_enabled"] is True

        pm = PauseMenu(
            rumble_enabled=gs.rumble_enabled,
            on_toggle_rumble=lambda val: gs.set_rumble_enabled(val, save=True),
        )
        assert "Gamepad Rumble: ON" in pm.get_options()

        # Navigate to "Gamepad Rumble: ON" (index 4) and toggle OFF
        pm.open()
        for _ in range(4):
            pm.navigate("down")
        assert pm.get_selected() == "Gamepad Rumble: ON"
        pm.confirm()

        assert pm.rumble_enabled is False
        assert "Gamepad Rumble: OFF" in pm.get_options()
        assert gs.rumble_enabled is False
        assert gs.stats.data["rumble_enabled"] is False

        # Triggering rumble while disabled must be suppressed
        assert gs.trigger_rumble("parry") is False
        assert gs.consume_rumble_impulse() is None

        # Persist and reload from disk
        gs.save_stats(str(save_file), wait=True)
        reloaded = StatisticsTracker.load(save_file)
        assert reloaded.data["rumble_enabled"] is False

        # Hydrating a fresh GameState restores rumble_enabled=False and syncs PauseMenu
        gs_reader = GameState(stats=None, stats_path=str(save_file), auto_load=False)
        try:
            gs_reader.hydrate_from_disk()
            assert gs_reader.rumble_enabled is False
            pm2 = PauseMenu()
            pm2.set_rumble_enabled(gs_reader.rumble_enabled)
            assert "Gamepad Rumble: OFF" in pm2.get_options()
        finally:
            gs_reader.shutdown_save_worker(timeout=1.0)
    finally:
        gs.shutdown_save_worker(timeout=1.0)


def test_dispatch_and_stop_gamepad_rumble_mocked_and_headless(monkeypatch):
    """Verify safe Joystick.rumble() dispatch with mocked, unsupported, raising, and missing controllers."""
    _ensure_pygame()
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        # 1. Mocked healthy joystick receives exact (low, high, duration_ms)
        calls = []
        stopped = []

        class MockJoystick:
            """Mock controller supporting rumble and stop_rumble."""

            def rumble(self, low, high, duration):
                """Record rumble parameters and return True."""
                calls.append((low, high, duration))
                return True

            def stop_rumble(self):
                """Record stop_rumble call."""
                stopped.append(True)

        mock_joy = MockJoystick()
        state.trigger_rumble("combat_hit")
        assert main_mod.dispatch_gamepad_rumble(state, joystick=mock_joy) is True
        low, high, dur, _prio = constants.RUMBLE_PRESET_COMBAT_HIT
        assert calls == [(low, high, dur)]
        # Subsequent frame with empty queue is a clean no-op
        assert main_mod.dispatch_gamepad_rumble(state, joystick=mock_joy) is False
        assert main_mod.stop_gamepad_rumble(joystick=mock_joy) is True
        assert stopped == [True]

        # 2. Unsupported driver (no rumble method) or raising driver never crashes
        class BrokenJoystick:
            """Mock controller whose rumble() raises a pygame.error."""

            def rumble(self, _low, _high, _duration):
                """Simulate driver rumble failure."""
                raise pygame.error("Haptic not supported")

            def stop_rumble(self):
                """Simulate driver stop_rumble failure."""
                raise pygame.error("Haptic not supported")

        state.trigger_rumble("parry")
        assert main_mod.dispatch_gamepad_rumble(state, joystick=object()) is False
        state.trigger_rumble("parry")
        assert main_mod.dispatch_gamepad_rumble(state, joystick=BrokenJoystick()) is False
        assert main_mod.stop_gamepad_rumble(joystick=BrokenJoystick()) is False

        # 3. Hermetic headless / no controller connected or uninitialized joystick returns False safely
        monkeypatch.setattr(pygame.joystick, "get_count", lambda: 0)
        state.trigger_rumble("boss_summon")
        assert main_mod.dispatch_gamepad_rumble(state) is False
        assert main_mod.stop_gamepad_rumble() is False

        monkeypatch.setattr(pygame.joystick, "get_init", lambda: False)
        state.trigger_rumble("boss_summon")
        assert main_mod.dispatch_gamepad_rumble(state) is False
        assert main_mod.stop_gamepad_rumble() is False
    finally:
        state.shutdown_save_worker(timeout=1.0)
