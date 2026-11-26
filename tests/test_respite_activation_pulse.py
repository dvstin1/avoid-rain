# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Section 8: Respite Activation Pulse (localized typographic bloom)."""
# pylint: disable=no-member,too-many-locals

import os

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.particles import RespiteActivationPulse, RespitePulseManager
from engine.stats import StatisticsTracker
from engine.world import Respite, WarpPortal
from rendering.renderer import Renderer


def _ensure_pygame():
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def test_respite_pulse_dt_lifecycle_drift_framerate_independence_and_expiry():
    """Verify ring expansion, upward glyph drift, alpha curves, dt independence, and auto-expiry."""
    mgr = RespitePulseManager()
    assert mgr.is_active() is False

    pulse = mgr.spawn_pulse(320.0, 240.0, seed=42)
    assert mgr.is_active() is True
    assert len(pulse.glyphs) == constants.RESPITE_PULSE_GLYPH_COUNT
    assert all(g.glyph in constants.RESPITE_PULSE_GLYPH_POOL for g in pulse.glyphs)
    assert pulse.ring_radius == pytest.approx(constants.RESPITE_PULSE_RING_START_RADIUS)
    assert pulse.ring_alpha == constants.RESPITE_PULSE_RING_MAX_ALPHA

    initial_ys = [g.y for g in pulse.glyphs]
    mgr.update(0.25)
    r_early = pulse.ring_radius
    a_early = pulse.ring_alpha
    assert r_early > constants.RESPITE_PULSE_RING_START_RADIUS
    assert pulse.inner_ring_radius < r_early
    assert 0 < a_early < constants.RESPITE_PULSE_RING_MAX_ALPHA
    # All drifting letters rise gently upward
    assert all(g.y < y0 for g, y0 in zip(pulse.glyphs, initial_ys))
    assert any(g.alpha > 0 for g in pulse.glyphs)

    mgr.update(0.50)
    assert pulse.ring_radius > r_early
    assert pulse.ring_alpha < a_early

    # Advancing past max duration + glyph lifetime automatically cleans up the pulse
    mgr.update(constants.RESPITE_PULSE_DURATION + 0.5)
    assert mgr.is_active() is False
    assert not mgr.pulses

    # Frame-rate independence: 10 x 0.05s matches 1 x 0.50s for ring & glyph positions
    p_fine = RespiteActivationPulse(100.0, 100.0, seed=99)
    p_coarse = RespiteActivationPulse(100.0, 100.0, seed=99)
    for _ in range(10):
        p_fine.update(0.05)
    p_coarse.update(0.50)
    assert p_fine.progress == pytest.approx(p_coarse.progress, abs=1e-6)
    assert p_fine.ring_radius == pytest.approx(p_coarse.ring_radius, abs=1e-5)
    assert len(p_fine.glyphs) == len(p_coarse.glyphs)
    for gf, gc in zip(p_fine.glyphs, p_coarse.glyphs):
        assert gf.x == pytest.approx(gc.x, abs=1e-4)
        assert gf.y == pytest.approx(gc.y, abs=1e-4)


def test_respite_rest_spawns_pulse_offline_client_and_lan_host():
    """Resting at a Respite spawns a pulse centered on the anchor across offline, Client, and LAN Host."""
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        respite_a = Respite((200, 160), (constants.TILE_SIZE, constants.TILE_SIZE))
        respite_b = Respite((520, 400), (constants.TILE_SIZE, constants.TILE_SIZE))
        state.world.interactables.extend([respite_a, respite_b])

        # 1. Offline / Host local rest
        respite_a.execute_rest(state)
        assert len(state.respite_pulses.pulses) == 1
        p0 = state.respite_pulses.pulses[0]
        assert (p0.cx, p0.cy) == pytest.approx((220.0, 180.0))

        # GameState.update(dt) ticks and expires the pulse cleanly
        state.update(constants.RESPITE_PULSE_DURATION + 0.2, {"move": (0, 0)})
        assert state.respite_pulses.is_active() is False

        # 2. Client local rest spawns the pulse before returning early for network sync
        state.network_manager.network_mode = "CLIENT"
        state.network_manager.server_address = "127.0.0.1"
        respite_b.execute_rest(state)
        assert len(state.respite_pulses.pulses) == 1
        assert (state.respite_pulses.pulses[0].cx, state.respite_pulses.pulses[0].cy) == pytest.approx((540.0, 420.0))
        state.respite_pulses.clear()

        # 3. Host receiving remote RESPITE_ACTION('REST') triggers pulse at nearest Respite to the guest
        state.network_manager.network_mode = "HOST"
        state.network_manager.remote_players["guest_peer"] = {
            "peer_id": "guest_peer",
            "identity": "GuestScholar",
            "x": 515.0,
            "y": 395.0,
            "hp": 50.0,
            "in_sanctuary": False,
        }
        state.handle_remote_respite("guest_peer", "REST", -1, {"max_hp": 100.0})
        state.drain_network_events()
        assert len(state.respite_pulses.pulses) == 1
        assert (state.respite_pulses.pulses[0].cx, state.respite_pulses.pulses[0].cy) == pytest.approx((540.0, 420.0))
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_respite_pulses_clear_on_warp_sanctuary_and_new_game():
    """Active Respite Activation Pulses clear automatically on warp, Sanctuary entry, and new-game reset."""
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        # 1. Cleared on start_warp
        state.spawn_respite_pulse(300.0, 300.0, seed=1)
        assert state.respite_pulses.is_active() is True
        portal = WarpPortal("sanctuary", 100, 100, (0, 0, 40, 40))
        state.start_warp(portal, confirmed=True)
        assert state.respite_pulses.is_active() is False

        # 2. Cleared on on_enter_sanctuary
        state.spawn_respite_pulse(300.0, 300.0, seed=2)
        assert state.respite_pulses.is_active() is True
        state.on_enter_sanctuary()
        assert state.respite_pulses.is_active() is False

        # 3. Cleared on reset_to_new_game
        state.spawn_respite_pulse(300.0, 300.0, seed=3)
        assert state.respite_pulses.is_active() is True
        state.reset_to_new_game()
        assert state.respite_pulses.is_active() is False
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_headless_respite_pulse_rendering():
    """Verify Renderer.draw_respite_pulses() is a no-op when empty and draws visible ring/glyphs when active."""
    _ensure_pygame()
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False, stats=StatisticsTracker())
    try:
        # Empty state -> returns 0 and leaves pixels untouched
        screen.fill((10, 10, 12))
        empty_bytes = pygame.image.tobytes(screen, "RGBA")
        assert renderer.draw_respite_pulses(state, 0.0, 0.0) == 0
        assert pygame.image.tobytes(screen, "RGBA") == empty_bytes

        # Spawn pulse in viewport, step slightly so glyphs fade in and ring expands
        px, py = state.player.get_center()
        state.spawn_respite_pulse(px, py, seed=7)
        state.respite_pulses.update(0.35)

        ox, oy = state.camera.get_offset()
        screen.fill((10, 10, 12))
        rendered = renderer.draw_respite_pulses(state, ox, oy)
        assert rendered == 1
        assert pygame.image.tobytes(screen, "RGBA") != empty_bytes

        # Full headless Renderer.render() sweep during active pulse and after expiry
        renderer.render(state)
        state.respite_pulses.update(constants.RESPITE_PULSE_DURATION + 0.5)
        assert state.respite_pulses.is_active() is False
        renderer.render(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)
