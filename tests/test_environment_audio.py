# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Section 2 Environment Audio (directional stereo ambient loops & Ogg verification)."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
import generate_sfx
from engine.audio import AudioManager
from engine.enemy import FinalAuthor, NightBoss
from engine.game_state import GameState
from engine.world import GameObject, Wellspring, World


@pytest.fixture(scope="module", autouse=True)
def init_pygame_audio():
    """Initialize pygame and mixer in headless dummy mode."""
    pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    yield
    pygame.quit()


class _SpyChannel:
    """Thin proxy around a real pygame.mixer.Channel recording stereo set_volume calls."""

    def __init__(self, real_channel):
        self._ch = real_channel
        self.volume_calls = []

    def play(self, *args, **kwargs):
        """Delegate play() to the underlying pygame mixer Channel."""
        return self._ch.play(*args, **kwargs)

    def stop(self):
        """Delegate stop() to the underlying pygame mixer Channel."""
        return self._ch.stop()

    def get_busy(self):
        """Delegate get_busy() to the underlying pygame mixer Channel."""
        return self._ch.get_busy()

    def set_volume(self, *args):
        """Record stereo volume arguments and forward to the underlying Channel."""
        self.volume_calls.append(args)
        return self._ch.set_volume(*args)


def test_stereo_panning_and_distance_attenuation_math():
    """Verify pure compute_stereo_volumes() L/R balance, symmetry, attenuation, and cutoff."""
    # 1. Centered source at distance 0 -> equal full left/right volume
    l0, r0 = constants.compute_stereo_volumes(0.0, 0.0, max_dist=400.0, full_dist=80.0, base_volume=0.5)
    assert l0 == pytest.approx(0.5)
    assert r0 == pytest.approx(0.5)

    # 2. Source to the right (dx > 0) pans louder in right ear; left (dx < 0) mirrors symmetrically
    lr, rr = constants.compute_stereo_volumes(200.0, 0.0, max_dist=500.0, full_dist=80.0, base_volume=0.8)
    ll, rl = constants.compute_stereo_volumes(-200.0, 0.0, max_dist=500.0, full_dist=80.0, base_volume=0.8)
    assert rr > lr > 0.0
    assert ll > rl > 0.0
    assert ll == pytest.approx(rr)
    assert rl == pytest.approx(lr)

    # 3. Monotonic distance attenuation and clean silence at/beyond max_dist
    near_l, near_r = constants.compute_stereo_volumes(0.0, 120.0, max_dist=400.0, full_dist=80.0, base_volume=0.8)
    far_l, far_r = constants.compute_stereo_volumes(0.0, 320.0, max_dist=400.0, full_dist=80.0, base_volume=0.8)
    out_l, out_r = constants.compute_stereo_volumes(0.0, 420.0, max_dist=400.0, full_dist=80.0, base_volume=0.8)
    assert near_l == pytest.approx(near_r)
    assert far_l == pytest.approx(far_r)
    assert 0.0 < far_l < near_l < 0.8
    assert (out_l, out_r) == (0.0, 0.0)

    # 4. Floor attenuation preserves directional pan even past max_dist (late storm / boss rumble)
    fl_l, fl_r = constants.compute_stereo_volumes(
        400.0, 0.0, max_dist=300.0, full_dist=80.0, base_volume=0.4, min_attenuation=0.35
    )
    assert fl_r > fl_l > 0.0


def test_generated_ambient_ogg_assets_verify_and_zero_missing():
    """Verify ambient_flame, ambient_water, and ambient_author_rumble Ogg files decode cleanly with 0 missing SFX."""
    for fname in (
        constants.AMBIENT_FLAME_SFX,
        constants.AMBIENT_WATER_SFX,
        constants.AMBIENT_AUTHOR_RUMBLE_SFX,
    ):
        path = os.path.join("assets", "audio", "sfx", fname)
        assert os.path.exists(path), f"Missing generated environment audio asset: {path}"
        duration = generate_sfx.verify_ogg(path)
        assert duration >= 2.5, f"Ambient loop {fname} unexpectedly short: {duration:.2f}s"

    assert generate_sfx.find_missing_sfx(".") == {}


def test_environment_audio_directional_panning_and_channel_cap():
    """Verify directional stereo updates for flames, Wellsprings, and Author rumble within the 3-channel budget."""
    am = AudioManager()
    assert len(am.env_channels) == constants.ENV_AUDIO_MAX_CHANNELS == 3
    spies = {slot: _SpyChannel(ch) for slot, ch in am.env_channels.items()}
    am.env_channels = spies

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("vitreous_basin")
        state.world.load_from_prototype(["." * 20 for _ in range(20)])
        state.in_sanctuary = False
        state.player.x = 300.0
        state.player.y = 300.0

        # Place Fire Chalice + extra Candelabra to the right, and Wellspring to the left
        chalice = GameObject((460.0, 280.0), (80, 80))
        chalice.name = "Fire Chalice"
        candelabra_far = GameObject((580.0, 300.0), (40, 40))
        candelabra_far.name = "Candelabra"
        wellspring = Wellspring((120.0, 300.0), (40, 40))
        state.world.interactables = [chalice, candelabra_far, wellspring]

        # Late-storm Author madness rumble anchored to the right (+600, 0)
        state.weather_manager.bleed_state = "BOSS_PHASE"
        state.weather_manager.current_step_idx = 2
        state.enemies = [NightBoss(900.0, 300.0)]

        levels = {}
        for _ in range(25):
            levels = am.update_environment_audio(state, dt=0.1, paused=False)

        assert levels["flame"][1] > levels["flame"][0] > 0.0
        assert levels["water"][0] > levels["water"][1] > 0.0
        assert levels["author_rumble"][1] > levels["author_rumble"][0] > 0.0

        for slot in constants.ENV_AUDIO_SLOTS:
            assert spies[slot].get_busy() is True
            assert spies[slot].volume_calls and len(spies[slot].volume_calls[-1]) == 2

        # Moving far out of flame & water range fades them to silence and stops their channels
        state.player.x = 2400.0
        state.player.y = 2400.0
        for _ in range(40):
            levels = am.update_environment_audio(state, dt=0.1, paused=False)
        assert levels["flame"] == (0.0, 0.0)
        assert levels["water"] == (0.0, 0.0)
        assert spies["flame"].get_busy() is False
        assert spies["water"].get_busy() is False
        assert max(levels["author_rumble"]) > 0.0
    finally:
        am.stop_environment_audio()
        state.shutdown_save_worker(timeout=1.0)


def test_environment_audio_final_author_pause_and_sanctuary_cleanup():
    """Verify FinalAuthor rumble, pause silence, and Sanctuary suppression with pond/candelabra ambience."""
    am = AudioManager()
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        # 1. FinalAuthor arena swells Author rumble directionally
        arena_world = World("night_boss_arena")
        arena_world.load_from_prototype(["." * 16 for _ in range(16)])
        state.world = arena_world
        state.in_sanctuary = False
        state.player.x = 200.0
        state.player.y = 200.0
        state.enemies = [FinalAuthor(440.0, 200.0)]

        levels = am.update_environment_audio(state, dt=0.5, paused=False)
        assert levels["author_rumble"][1] > levels["author_rumble"][0] > 0.0
        assert am.env_channels["author_rumble"].get_busy() is True

        # 2. Pausing stops all environment loops immediately
        levels = am.update_environment_audio(state, dt=0.016, paused=True)
        for slot in constants.ENV_AUDIO_SLOTS:
            assert levels[slot] == (0.0, 0.0)
            assert am.env_channels[slot].get_busy() is False

        # 3. Transitioning to Sanctuary suppresses Author rumble while playing pond & candelabra loops
        sanctuary = World("sanctuary")
        sanctuary.load_from_prototype(["." * 12 for _ in range(12)])
        sanctuary.sanctuary_zones = {"pond_water": [(2, 5)]}
        s_candle = GameObject((320.0, 200.0), (40, 40))
        s_candle.name = "Candelabra"
        sanctuary.interactables = [s_candle]
        state.world = sanctuary
        state.in_sanctuary = True
        state.player.x = 200.0
        state.player.y = 200.0

        levels = am.update_environment_audio(state, dt=0.5, paused=False)
        assert levels["flame"][1] > levels["flame"][0] > 0.0
        assert levels["water"][0] > levels["water"][1] > 0.0
        assert levels["author_rumble"] == (0.0, 0.0)
        assert am.env_channels["author_rumble"].get_busy() is False
    finally:
        am.stop_environment_audio()
        state.shutdown_save_worker(timeout=1.0)
