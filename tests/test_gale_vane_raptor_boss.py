# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Windy Ridge Night Boss: The Gale-Vane Raptor (Step 2)."""
# pylint: disable=no-member,protected-access
import os
from types import SimpleNamespace

import pygame
import pytest

import constants
import generate_sfx
from engine.enemy import (
    ENEMY_REGISTRY,
    GaleVaneRaptorBoss,
    MeadowCensorBoss,
    NightBoss,
    RimecrestArbiterBoss,
    SlugBoss,
)
from engine.game_state import GameState
from engine.player import PlayerStateEnum
from engine.world import Respite, World
from rendering.renderer import Renderer


def _make_state(biome="windy_ridge"):
    """Build a clean offline GameState on an open prototype map."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    state.world = World(biome)
    state.world.load_from_prototype(["." * 24 for _ in range(24)])
    state.world.boss_coords_list = [{"x": 12, "y": 12}]
    state.run_biomes["act1"] = biome
    state.in_sanctuary = False
    state.enemies = []
    state.player.x = 12 * constants.TILE_SIZE
    state.player.y = 12 * constants.TILE_SIZE
    return state


def test_windy_ridge_spawns_gale_vane_raptor_and_metadata():
    """Windy Ridge Night Boss spawn instantiates GaleVaneRaptorBoss, preserved on Respite rest."""
    state = _make_state("windy_ridge")
    try:
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)

        assert len(state.enemies) == 1
        boss = state.enemies[0]
        assert isinstance(boss, GaleVaneRaptorBoss)
        assert isinstance(boss, NightBoss)
        assert (boss.width, boss.height) == (constants.GALE_RAPTOR_SIZE, constants.GALE_RAPTOR_SIZE)
        assert boss.name == "Night Boss"
        assert boss.display_name == "The Gale-Vane Raptor"
        assert boss.get_display_name() == "The Gale-Vane Raptor"
        assert ENEMY_REGISTRY["GaleVaneRaptorBoss"] is GaleVaneRaptorBoss
        assert boss.is_within_active_simulation(state) is True

        # Respite rest must preserve live GaleVaneRaptorBoss
        respite = Respite((40.0, 40.0), (40, 40))
        respite.execute_rest(state)
        assert any(isinstance(e, GaleVaneRaptorBoss) for e in state.enemies)
    finally:
        state.shutdown_save_worker(timeout=1.0)


@pytest.mark.parametrize(
    ("biome", "expected_cls"),
    [
        ("windy_ridge", GaleVaneRaptorBoss),
        ("swamp_mire", SlugBoss),
        ("pastoral_valley", MeadowCensorBoss),
        ("frozen_peaks", RimecrestArbiterBoss),
    ],
)
def test_lan_client_resolves_night_boss_by_biome(biome, expected_cls):
    """LAN Client _sync_enemies_from_host resolves 'Night Boss' into the active biome boss class."""
    state = _make_state(biome)
    try:
        state.enemies = []
        state._sync_enemies_from_host(
            [
                {
                    "id": 9000,
                    "name": "Night Boss",
                    "x": 240.0,
                    "y": 240.0,
                    "hp": 500.0,
                    "state": "CHASE",
                    "empowered": False,
                }
            ]
        )
        assert len(state.enemies) == 1
        assert isinstance(state.enemies[0], expected_cls)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_gale_guard_frontal_armor_vs_flank_and_phase_volleys():
    """Gale Guard deflects frontal attacks (0.25x), yields full damage from behind, and fires 3/5-bolt fans."""
    state = _make_state("windy_ridge")
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
        boss = GaleVaneRaptorBoss(300.0, 300.0)
        boss.facing = (1.0, 0.0)
        boss.attack_mode = "gale_guard"
        boss.armor_active = True
        boss.weakpoint_exposed_timer = 0.0
        state.enemies = [boss]

        bcx, bcy = boss.get_center()
        assert boss.check_gimmick_hit(bcx + 80.0, bcy) == "armor"
        assert boss.check_gimmick_hit(bcx - 80.0, bcy) == "normal"

        # Verify frontal melee hit applies 0.25x armor multiplier and armor_deflect SFX
        base_dmg = float(state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE))
        hp_before = boss.hp
        state.player.x = bcx + 48.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (-1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)
        assert hp_before - boss.hp == pytest.approx(base_dmg * constants.GALE_RAPTOR_ARMOR_DAMAGE_MULT)
        assert constants.ARMOR_DEFLECT_SFX in played_sfx

        # Verify flanking behind the tail-rudder bypasses frontal armor for 1.0x damage
        hp_mid = boss.hp
        state.player.x = bcx - 48.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)
        assert hp_mid - boss.hp == pytest.approx(base_dmg)

        # Phase 1 fires 3-bolt wind-shear fan; Phase 2 fires 5-bolt fan
        boss.stagger_timer = 0.0
        boss.ink_bolts.clear()
        boss.phase = 1
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert len(boss.ink_bolts) == constants.GALE_RAPTOR_BOLT_COUNT_P1

        boss.stagger_timer = 0.0
        boss.ink_bolts.clear()
        boss.hp = boss.max_hp * 0.45
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert boss.phase == 2
        assert len(boss.ink_bolts) == constants.GALE_RAPTOR_BOLT_COUNT_P2
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_crosswind_dive_to_stall_shatter_crit_and_knockdown():
    """Completing Crosswind Dive opens 1.45s Stall Shatter (LAN Host SFX queued); hitting deals 2.25x + knocks out."""
    state = _make_state("windy_ridge")
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    state.network_manager.network_mode = "HOST"
    try:
        boss = GaleVaneRaptorBoss(360.0, 360.0)
        state.enemies = [boss]
        state.player.x = 560.0
        state.player.y = 360.0

        # Force transition from gale_guard -> crosswind_dive (Phase 1 = 2 dashes)
        boss.mode_timer = 0.01
        boss.update(0.05, state)
        assert boss.attack_mode == "crosswind_dive"
        assert boss.dashes_remaining == constants.GALE_RAPTOR_DASH_COUNT_P1

        # Step through both dashes until stall_shatter triggers
        saw_trails = False
        for _ in range(80):
            boss.update(0.05, state)
            if boss.wind_gust_trails:
                saw_trails = True
            if boss.attack_mode == "stall_shatter":
                break

        assert saw_trails is True
        assert boss.attack_mode == "stall_shatter"
        assert boss.armor_active is False
        assert boss.weakpoint_exposed_timer == pytest.approx(constants.GALE_RAPTOR_STALL_DURATION)
        assert constants.BOSS_EXPOSE_SFX in played_sfx
        assert any(entry[0] == constants.BOSS_EXPOSE_SFX for entry in state.pending_remote_sfx)

        # Visual packet exposes articulation and gimmick telemetry
        pkt = boss.get_visual_packet()
        assert pkt["attack_mode"] == "stall_shatter"
        assert pkt["armor_active"] is False
        assert pkt["weakpoint_exposed_timer"] > 0.0
        assert "wing_angle_deg" in pkt and "phase" in pkt

        # Landing a hit during stall_shatter deals 2.25x crit, stuns, and knocks boss back to gale_guard
        bcx, bcy = boss.get_center()
        base_dmg = float(state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE))
        hp_before = boss.hp
        state.player.x = bcx + 44.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (-1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)

        assert hp_before - boss.hp == pytest.approx(base_dmg * constants.GALE_RAPTOR_WEAKPOINT_DAMAGE_MULT)
        assert constants.WEAKPOINT_CRIT_SFX in played_sfx
        assert boss.stagger_timer >= constants.GALE_RAPTOR_STALL_STUN_DURATION
        assert boss.attack_mode == "gale_guard"
        assert boss.armor_active is True
        assert boss.weakpoint_exposed_timer == 0.0
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_gale_raptor_music_selection_and_generated_assets():
    """Audio track selector plays boss_gale_raptor.ogg and generated PNG/OGG assets verify cleanly."""
    assert constants.GALE_RAPTOR_MUSIC == "boss_gale_raptor.ogg"
    assert constants.GALE_RAPTOR_MUSIC in constants.BOSS_COMBAT_TRACKS

    state = _make_state("windy_ridge")
    try:
        boss = GaleVaneRaptorBoss(state.player.x + 80.0, state.player.y)
        state.enemies = [boss]
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.GALE_RAPTOR_MUSIC
    finally:
        state.shutdown_save_worker(timeout=1.0)

    # Verify generated OGG boss theme
    music_path = os.path.join("assets", "audio", "music", constants.GALE_RAPTOR_MUSIC)
    assert os.path.exists(music_path)
    assert generate_sfx.verify_ogg(music_path) > 10.0

    # Verify all 4 modular articulated PNG parts exist with expected dimensions & SRCALPHA
    if not pygame.get_init():
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
    expected_parts = {
        "gale_raptor_torso.png": (56, 64),
        "gale_raptor_head.png": (36, 36),
        "gale_raptor_wing.png": (64, 40),
        "gale_raptor_tail.png": (36, 44),
    }
    for fname, dims in expected_parts.items():
        path = os.path.join("assets", "graphics", fname)
        assert os.path.exists(path), f"Missing {path}"
        surf = pygame.image.load(path)
        assert surf.get_size() == dims
        assert surf.get_at((0, 0))[3] == 0


def test_gale_vane_raptor_articulated_rig_rendering_and_fallback():
    """Renderer draws The Gale-Vane Raptor via articulated rig in all 3 modes and gracefully falls back."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if not pygame.display.get_init():
        pygame.init()
    screen = pygame.Surface((320, 320), pygame.SRCALPHA)
    renderer = Renderer(screen)

    for key in ("gale_raptor_torso.png", "gale_raptor_head.png", "gale_raptor_wing.png", "gale_raptor_tail.png"):
        assert key in renderer.image_cache

    boss = GaleVaneRaptorBoss(100.0, 100.0)
    draw_rect = pygame.Rect(106, 106, boss.width, boss.height)

    for mode, substate, weak_t in (
        ("gale_guard", "telegraph", 0.0),
        ("crosswind_dive", "telegraph", 0.0),
        ("crosswind_dive", "dash", 0.0),
        ("stall_shatter", "dash", 1.2),
    ):
        screen.fill((0, 0, 0, 0))
        boss.attack_mode = mode
        boss.dive_substate = substate
        boss.weakpoint_exposed_timer = weak_t
        boss.armor_active = mode != "stall_shatter"
        boss.wind_gust_trails = [
            {"x": boss.x + 20.0, "y": boss.y + 20.0, "dx": 1.0, "dy": 0.0, "life": 0.4, "max_life": 0.55}
        ]
        pkt = boss.get_visual_packet()
        assert renderer.draw_procedural_enemy(boss, draw_rect, pkt, constants.COLOR_WHITE) is True
        non_empty = any(
            screen.get_at((x, y))[3] > 0
            for x in range(80, 240, 8)
            for y in range(80, 240, 8)
        )
        assert non_empty is True

    # Strip PNGs to verify procedural fallback renders cleanly
    for key in ("gale_raptor_torso.png", "gale_raptor_head.png", "gale_raptor_wing.png", "gale_raptor_tail.png"):
        renderer.image_cache.pop(key, None)
    screen.fill((0, 0, 0, 0))
    boss.attack_mode = "gale_guard"
    assert renderer.draw_procedural_enemy(boss, draw_rect, boss.get_visual_packet(), constants.COLOR_WHITE) is True
    assert any(screen.get_at((x, y))[3] > 0 for x in range(100, 220, 8) for y in range(100, 220, 8))
