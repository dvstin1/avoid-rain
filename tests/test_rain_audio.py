"""Headless unit tests for dynamic distance-based ambient rain audio."""
from types import SimpleNamespace
import pygame

import constants
from engine.audio import AudioManager
from engine.weather import WeatherManager


class _DummyPlayer:
    def __init__(self, x, y, active_track_name="world_exploration.ogg"):
        self.x = x
        self.y = y
        self.active_track_name = active_track_name
        self.is_exposed = False

    def get_center(self):
        return (self.x, self.y)

    def take_damage(self, amount, bypass_stagger=False):
        pass


def _make_world(name="macro_world"):
    return SimpleNamespace(name=name, grid=[["."]])


def test_rain_audio_distance_curve():
    """Verify silent core, early-warning ramp before camera edge, and sharp spike in rain."""
    wm = WeatherManager(boss_coords_list=[{"x": 100, "y": 100}])
    wm.active_safe_radius = 2000.0
    wm.bleed_state = "SHRINKING"
    wm.timer = 30.0
    wm.damage_enabled = False
    world = _make_world("macro_world")

    bcx = 100 * constants.TILE_SIZE

    # 1. Far inside safe zone (beyond 1.5x camera view radius from edge) -> 0.0
    far_dist = wm.active_safe_radius - (constants.RAIN_AUDIO_WARNING_BUFFER + 100.0)
    far_player = _DummyPlayer(bcx + far_dist, 100 * constants.TILE_SIZE)
    wm.update(0.1, far_player, world)
    assert wm.rain_audio_intensity == 0.0

    # 2. Approaching edge, still outside camera view (1.2x camera radius from edge) -> audible
    early_dist = wm.active_safe_radius - (1.2 * constants.RAIN_CAMERA_VIEW_RADIUS)
    early_player = _DummyPlayer(bcx + early_dist, 100 * constants.TILE_SIZE)
    wm.update(0.1, early_player, world)
    assert 0.0 < wm.rain_audio_intensity < constants.RAIN_AUDIO_APPROACH_MAX

    # 3. Right at the inner edge -> approaches RAIN_AUDIO_APPROACH_MAX (~0.45)
    edge_player = _DummyPlayer(bcx + wm.active_safe_radius, 100 * constants.TILE_SIZE)
    wm.update(0.1, edge_player, world)
    assert abs(wm.rain_audio_intensity - constants.RAIN_AUDIO_APPROACH_MAX) < 1e-5

    # 4. Just outside safe circle (inside the rain) -> sharp spike to >= 0.85
    in_rain_player = _DummyPlayer(bcx + wm.active_safe_radius + 10.0, 100 * constants.TILE_SIZE)
    wm.update(0.1, in_rain_player, world)
    assert wm.rain_audio_intensity >= constants.RAIN_AUDIO_INSIDE_MIN
    assert wm.rain_audio_intensity < constants.RAIN_AUDIO_INSIDE_MAX

    # 5. Deep in the rain -> saturates at 1.0
    deep_player = _DummyPlayer(
        bcx + wm.active_safe_radius + constants.RAIN_AUDIO_INSIDE_RAMP_DIST + 50.0,
        100 * constants.TILE_SIZE,
    )
    wm.update(0.1, deep_player, world)
    assert wm.rain_audio_intensity == 1.0


def test_rain_audio_boss_fadeout_and_sanctuary_silence():
    """Verify smooth fade-out during boss combat and silence in Sanctuary / arenas."""
    wm = WeatherManager(boss_coords_list=[{"x": 100, "y": 100}])
    wm.active_safe_radius = 1000.0
    wm.bleed_state = "CLAMPED"
    wm.damage_enabled = False
    world = _make_world("macro_world")

    bcx = 100 * constants.TILE_SIZE
    player = _DummyPlayer(bcx + wm.active_safe_radius + 300.0, 100 * constants.TILE_SIZE)

    # Full intensity in rain before boss music starts
    wm.update(0.1, player, world, boss_combat_active=False)
    assert wm.rain_audio_intensity == 1.0

    # Boss music triggers: smoothly fades over ~1.25s
    wm.update(0.5, player, world, boss_combat_active=True)
    mid_intensity = wm.rain_audio_intensity
    assert 0.0 < mid_intensity < 1.0

    wm.update(1.0, player, world, boss_combat_active=True)
    assert wm.rain_audio_intensity == 0.0

    # Sanctuary is always silent
    wm.rain_boss_fade = 1.0
    wm.update(0.1, player, _make_world("sanctuary"), boss_combat_active=False)
    assert wm.rain_audio_intensity == 0.0

    # Final boss arena is silent
    wm.update(0.1, player, _make_world("night_boss_arena"), boss_combat_active=False)
    assert wm.rain_audio_intensity == 0.0


def test_audio_manager_rain_channel_pause_and_volume():
    """Verify AudioManager drives rain_channel, respects volume, and stops when paused."""
    pygame.mixer.init()
    am = AudioManager()
    am.volume = 0.5

    am.update_rain_audio(0.8, paused=False)
    assert am.rain_channel.get_busy()
    assert abs(am.rain_channel.get_volume() - 0.4) < 0.05

    am.update_rain_audio(0.8, paused=True)
    assert not am.rain_channel.get_busy()
