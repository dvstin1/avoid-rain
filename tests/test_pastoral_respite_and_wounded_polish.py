# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Respite VFX/SFX, Anomalous Weapon Fanfare, Wellspring Volume, Wounded Cues & Pastoral Valley."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

from types import SimpleNamespace

import pygame
import pytest

import constants
import generate_sfx
from engine.audio import AudioManager
from engine.enemy import BatEnemy, GlassKilnBasiliskBoss, SlugEnemy
from engine.game_state import GameState
from engine.particles import RespitePulseManager
from engine.stats import StatisticsTracker
from engine.world import WeaponPickup, Wellspring, World
from rendering.renderer import Renderer


def test_respite_hearth_sfx_and_expanded_pulse_vfx():
    """Verify regenerated respite_rest.ogg, anomalous_weapon_discovery.ogg, and expanded Respite pulse rendering."""
    respite_path = os.path.join("assets", "audio", "sfx", "respite_rest.ogg")
    anom_path = os.path.join("assets", "audio", "sfx", constants.ANOMALOUS_WEAPON_DISCOVERY_SFX)
    assert os.path.exists(respite_path)
    assert os.path.exists(anom_path)
    assert generate_sfx.verify_ogg(respite_path) >= 1.2
    assert generate_sfx.verify_ogg(anom_path) >= 1.5
    assert generate_sfx.find_missing_sfx(".") == {}

    # Expanded radius clears the 620x290 Respite UI menu card (half-width 310px)
    assert constants.RESPITE_PULSE_RING_MAX_RADIUS >= 340.0

    if not pygame.get_init():
        pygame.init()
    screen = pygame.Surface((800, 600), pygame.SRCALPHA)
    renderer = Renderer(screen)
    mgr = RespitePulseManager()
    mgr.spawn_pulse(400.0, 300.0, seed=7)
    mgr.update(0.45)
    assert renderer.draw_respite_pulses(SimpleNamespace(respite_pulses=mgr), 0, 0) == 1
    assert any(screen.get_at((x, y))[3] > 0 for x in range(180, 620, 12) for y in range(120, 480, 12))


def test_first_anomalous_weapon_discovery_fanfare_and_null_safe_stats():
    """First Anomalous weapon pickup sets story_flag, plays fanfare SFX & bloom once; handles stats=None."""
    state = GameState(auto_load=False, stats=StatisticsTracker())
    state.network_manager.stop_network()
    played = []
    state.audio_manager = SimpleNamespace(play_sfx=lambda name, **kw: played.append(name))
    saved_calls = []
    state.save_stats = lambda *a, **kw: saved_calls.append(True)

    try:
        assert state.stats.data["story_flags"]["anomalous_weapon_discovered"] is False

        # Non-anomalous weapon does not trigger discovery fanfare
        normal_wpn = {"name": "Refined Quill", "damage": 24, "modifiers": {}}
        pickup_norm = WeaponPickup((100.0, 100.0), normal_wpn)
        state.world.interactables.append(pickup_norm)
        pickup_norm.execute_interaction(state)
        assert state.stats.data["story_flags"]["anomalous_weapon_discovered"] is False
        assert not played

        # First Anomalous (purple) weapon triggers SFX, banner, and persists story flag
        purple_wpn = {"name": "Anomalous Ink-Nib", "damage": 32, "modifiers": {"bleed": 4.0}}
        pickup_anom1 = WeaponPickup((120.0, 100.0), purple_wpn)
        state.world.interactables.append(pickup_anom1)
        pickup_anom1.execute_interaction(state)
        assert state.stats.data["story_flags"]["anomalous_weapon_discovered"] is True
        assert played == [constants.ANOMALOUS_WEAPON_DISCOVERY_SFX]
        assert state.bloom_text == constants.ANOMALOUS_WEAPON_DISCOVERY_BANNER
        assert len(saved_calls) == 1

        # Second Anomalous weapon does NOT repeat the first-discovery fanfare
        played.clear()
        state.bloom_text = None
        purple_wpn2 = {"name": "Anomalous Void Quill", "damage": 35, "modifiers": {"void_strike": True}}
        pickup_anom2 = WeaponPickup((140.0, 100.0), purple_wpn2)
        state.world.interactables.append(pickup_anom2)
        pickup_anom2.execute_interaction(state)
        assert not played
        assert state.bloom_text is None

        # Null-safe handling when game_state.stats is None
        state.stats = None
        played.clear()
        pickup_null = WeaponPickup((160.0, 100.0), {"name": "Anomalous Edge", "damage": 30, "modifiers": {"bleed": 2}})
        state.world.interactables.append(pickup_null)
        pickup_null.execute_interaction(state)
        assert played == [constants.ANOMALOUS_WEAPON_DISCOVERY_SFX]
        assert state.bloom_text == constants.ANOMALOUS_WEAPON_DISCOVERY_BANNER
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_wellspring_ambient_volume_scaled_by_0_25():
    """AudioManager._compute_environment_targets() scales Wellspring to 0.25x while keeping pond/channels intact."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init()

    assert constants.ENV_AUDIO_WELLSPRING_VOL_MULT == pytest.approx(0.25)

    am = AudioManager()
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("sanctuary")
        state.world.load_from_prototype(["." * 12 for _ in range(12)])
        state.world.sanctuary_zones = {}
        state.in_sanctuary = True
        state.player.x = 200.0
        state.player.y = 200.0

        ws = Wellspring((200.0, 200.0), (40, 40))
        state.world.interactables = [ws]
        targets = am._compute_environment_targets(state)
        expected = constants.ENV_AUDIO_WATER_BASE_VOL * constants.ENV_AUDIO_WELLSPRING_VOL_MULT
        assert expected == pytest.approx(0.075)
        assert targets["water"][0] == pytest.approx(expected)
        assert targets["water"][1] == pytest.approx(expected)

        # Sanctuary pond scales by ENV_AUDIO_POND_VOL_MULT (0.20 -> 0.06 base)
        assert constants.ENV_AUDIO_POND_VOL_MULT == pytest.approx(0.20)
        state.world.interactables = []
        state.world.sanctuary_zones = {"pond_water": [(5, 5)]}
        pond_targets = am._compute_environment_targets(state)
        expected_pond = constants.ENV_AUDIO_WATER_BASE_VOL * constants.ENV_AUDIO_POND_VOL_MULT
        assert expected_pond == pytest.approx(0.06)
        assert pond_targets["water"][0] == pytest.approx(expected_pond)
        assert pond_targets["water"][1] == pytest.approx(expected_pond)
    finally:
        am.stop_environment_audio()
        state.shutdown_save_worker(timeout=1.0)


def test_wounded_enemy_and_boss_preserve_height_and_render_diegetic_cues(monkeypatch):
    """WOUNDED enemies & bosses never shrink vertically, render micro HP bar / aura, and pulse Boss HUD."""
    if not pygame.get_init():
        pygame.init()
    screen = pygame.Surface((800, 600), pygame.SRCALPHA)
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    state.debug_text_enabled = False

    recorded_draw_heights = []
    orig_proc = renderer.draw_procedural_enemy

    def spy_proc(actor, draw_rect, packet, state_color):
        recorded_draw_heights.append((actor.__class__.__name__, draw_rect.height))
        return orig_proc(actor, draw_rect, packet, state_color)

    monkeypatch.setattr(renderer, "draw_procedural_enemy", spy_proc)

    try:
        # 1. WOUNDED procedural non-boss enemy (BatEnemy) keeps 100% height & renders micro HP bar
        bat = BatEnemy(200.0, 200.0)
        bat.hp = max(1.0, bat.max_hp * 0.20)
        assert bat.get_visual_packet()["posture"] == "WOUNDED"
        screen.fill((0, 0, 0, 0))
        renderer.draw_actor_ghost(bat, 0, 0, state)
        assert ("BatEnemy", bat.height) in recorded_draw_heights
        # Micro HP bar rendered just above the enemy top edge
        bar_band_y = int(bat.y - constants.ENEMY_MICRO_HP_BAR_OFFSET_Y - 2)
        assert any(screen.get_at((x, bar_band_y))[3] > 0 for x in range(195, 235))

        # 2. WOUNDED sprite-path SlugEnemy keeps full un-squashed sprite height
        slug = SlugEnemy(300.0, 200.0)
        slug.hp = max(1.0, slug.max_hp * 0.15)
        assert slug.get_visual_packet()["posture"] == "WOUNDED"
        full_slug_surf = pygame.Surface((48, 48), pygame.SRCALPHA)
        full_slug_surf.fill((120, 120, 120, 255))
        renderer.image_cache["slug_1.png"] = full_slug_surf
        scale_calls = []
        orig_scale = pygame.transform.scale

        def spy_scale(surf, size, *args, **kwargs):
            scale_calls.append(size)
            return orig_scale(surf, size, *args, **kwargs)

        monkeypatch.setattr(pygame.transform, "scale", spy_scale)
        renderer.draw_actor_ghost(slug, 0, 0, state)
        assert not scale_calls

        # 3. WOUNDED articulated boss keeps full height (112px) and pulses crimson Boss HUD border
        boss = GlassKilnBasiliskBoss(420.0, 220.0)
        boss.hp = boss.max_hp * 0.20
        assert boss.get_visual_packet()["posture"] == "WOUNDED"
        state.enemies = [boss]
        state.in_sanctuary = False
        recorded_draw_heights.clear()
        screen.fill((0, 0, 0, 0))
        renderer.draw_actor_ghost(boss, 0, 0, state)
        assert ("GlassKilnBasiliskBoss", boss.height) in recorded_draw_heights

        screen.fill((0, 0, 0, 0))
        renderer.draw_boss_hud(state)
        # Low-HP boss HUD border renders warm crimson tones near bottom center
        hud_y = 600 - int(constants.BOSS_HUD_BOTTOM_MARGIN) - int(constants.BOSS_HUD_BAR_HEIGHT)
        has_warm_crimson = any(
            screen.get_at((x, hud_y))[0] > 160 and screen.get_at((x, hud_y))[0] > screen.get_at((x, hud_y))[2] + 60
            for x in range(200, 600, 4)
        )
        assert has_warm_crimson is True
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_pastoral_valley_organic_floors_and_plateau_rooftops():
    """Pastoral Valley s_idx 1/2 floors & wall_s plateau rooftops render fine organic multi-tone details."""
    if not pygame.get_init():
        pygame.init()
    screen = pygame.Surface((240, 240))
    renderer = Renderer(screen)
    pal = constants.BIOME_PALETTES["pastoral_valley"]
    ts = constants.TILE_SIZE

    # 1. Meadow (s_idx == 1) and Pathway (s_idx == 2) organic floor rendering
    for s_idx in (1, 2):
        floor_surf = pygame.Surface((ts * 3, ts * 3))
        base_col, alt_col = pal["strata"][s_idx]
        for gy in range(3):
            for gx in range(3):
                sx, sy = gx * ts, gy * ts
                floor_surf.fill(base_col, (sx, sy, ts, ts))
                renderer._draw_connected_floor_patterns(
                    floor_surf,
                    ("pastoral_valley", pal, s_idx, alt_col),
                    (gx, gy, 3, 3),
                    (sx, sy, ts, ts),
                )
        unique_cols = {
            tuple(floor_surf.get_at((px, py))[:3])
            for px in range(0, ts * 3, 2)
            for py in range(0, ts * 3, 2)
        }
        assert len(unique_cols) >= 4

    # 2. Pastoral Valley plateau rooftop (wall_s=True) and south facade (wall_s=False)
    grid = [
        [constants.TILE_EMPTY, constants.TILE_EMPTY, constants.TILE_EMPTY, constants.TILE_EMPTY],
        [constants.TILE_EMPTY, constants.TILE_WALL, constants.TILE_WALL, constants.TILE_EMPTY],
        [constants.TILE_EMPTY, constants.TILE_WALL, constants.TILE_WALL, constants.TILE_EMPTY],
        [constants.TILE_EMPTY, constants.TILE_EMPTY, constants.TILE_EMPTY, constants.TILE_EMPTY],
    ]
    dummy_state = SimpleNamespace(world=SimpleNamespace(grid=grid, name="pastoral_valley"))
    wall_surf = pygame.Surface((ts * 4, ts * 4))
    wall_surf.fill((0, 0, 0))
    renderer._draw_connected_wall_tile(
        wall_surf, dummy_state, (1, 1, 4, 4), (ts, ts, ts, ts), ("pastoral_valley", pal)
    )
    renderer._draw_connected_wall_tile(
        wall_surf, dummy_state, (2, 1, 4, 4), (ts * 2, ts, ts, ts), ("pastoral_valley", pal)
    )
    renderer._draw_connected_wall_tile(
        wall_surf, dummy_state, (1, 2, 4, 4), (ts, ts * 2, ts, ts), ("pastoral_valley", pal)
    )
    roof_cols = {
        tuple(wall_surf.get_at((px, py))[:3])
        for px in range(ts, ts * 3, 2)
        for py in range(ts, ts * 2, 2)
    }
    assert len(roof_cols) >= 4
    assert tuple(wall_surf.get_at((ts + 10, ts))[:3]) == pal["wall_mortar"]
