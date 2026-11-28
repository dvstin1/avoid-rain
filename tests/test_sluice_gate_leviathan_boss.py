# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for The Sunlit Aqueducts Night Boss: The Sluice-Gate Leviathan (Step 5)."""
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
    GlassKilnBasiliskBoss,
    MeadowCensorBoss,
    NightBoss,
    RimecrestArbiterBoss,
    SlugBoss,
    SluiceGateLeviathanBoss,
    TypesetterAutomatonBoss,
)
from engine.game_state import GameState
from engine.player import PlayerStateEnum
from engine.world import Respite, World
from rendering.renderer import Renderer


BIOME_NIGHT_BOSS_CLASSES = {
    "windy_ridge": GaleVaneRaptorBoss,
    "pastoral_valley": MeadowCensorBoss,
    "swamp_mire": SlugBoss,
    "frozen_peaks": RimecrestArbiterBoss,
    "tech_tower": TypesetterAutomatonBoss,
    "vitreous_basin": GlassKilnBasiliskBoss,
    "sunlit_aqueducts": SluiceGateLeviathanBoss,
}


def _make_state(biome="sunlit_aqueducts"):
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


def test_sunlit_aqueducts_spawns_sluice_gate_leviathan_and_metadata():
    """Sunlit Aqueducts Night Boss spawn instantiates SluiceGateLeviathanBoss, preserved on Respite rest."""
    state = _make_state("sunlit_aqueducts")
    try:
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)

        assert len(state.enemies) == 1
        boss = state.enemies[0]
        assert isinstance(boss, SluiceGateLeviathanBoss)
        assert isinstance(boss, NightBoss)
        assert (boss.width, boss.height) == (constants.SLUICE_LEVIATHAN_SIZE, constants.SLUICE_LEVIATHAN_SIZE)
        assert boss.hp == pytest.approx(constants.NIGHT_BOSS_MAX_HP)
        assert boss.name == "Night Boss"
        assert boss.display_name == "The Sluice-Gate Leviathan"
        assert boss.get_display_name() == "The Sluice-Gate Leviathan"
        assert boss.is_sluice_leviathan is True
        assert boss.armor_front_only is True
        assert boss.armor_damage_mult == pytest.approx(constants.SLUICE_LEVIATHAN_ARMOR_DAMAGE_MULT)
        assert boss.weakpoint_damage_mult == pytest.approx(constants.SLUICE_LEVIATHAN_WEAKPOINT_DAMAGE_MULT)
        assert constants.BOSS_HUD_DISPLAY_NAMES["SluiceGateLeviathanBoss"] == "The Sluice-Gate Leviathan"
        assert ENEMY_REGISTRY["SluiceGateLeviathanBoss"] is SluiceGateLeviathanBoss
        assert boss.is_within_active_simulation(state) is True
        assert World.build_initial_enemy_spawns([boss]) == []

        hud_info = state.get_active_boss_hud_info()
        assert hud_info is not None
        assert hud_info["name"] == "The Sluice-Gate Leviathan"

        # Respite rest must preserve live SluiceGateLeviathanBoss
        respite = Respite((40.0, 40.0), (40, 40))
        respite.execute_rest(state)
        assert any(isinstance(e, SluiceGateLeviathanBoss) for e in state.enemies)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_all_seven_chronicle_biomes_resolve_dedicated_night_bosses():
    """All 7 biomes in CHRONICLE_BIOME_ROSTER resolve dedicated Night Bosses on Host & LAN Client."""
    assert set(constants.CHRONICLE_BIOME_ROSTER) == set(BIOME_NIGHT_BOSS_CLASSES)
    assert len(constants.CHRONICLE_BIOME_ROSTER) == 7

    for biome in constants.CHRONICLE_BIOME_ROSTER:
        expected_cls = BIOME_NIGHT_BOSS_CLASSES[biome]
        state = _make_state(biome)
        try:
            # 1. Host world-event spawn resolves dedicated biome boss (never generic NightBoss)
            state.weather_manager.bleed_state = "CLAMPED"
            state.weather_manager.current_boss_idx = 0
            state._update_world_events(0.016)
            state._update_world_events(constants.BOSS_SUMMON_DURATION)
            assert len(state.enemies) == 1
            assert type(state.enemies[0]) is expected_cls
            assert type(state.enemies[0]) is not NightBoss

            # 2. LAN Client sync resolves "Night Boss" to the exact same dedicated biome boss
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
            assert type(state.enemies[0]) is expected_cls
        finally:
            state.shutdown_save_worker(timeout=1.0)


def test_sluice_guard_frontal_shield_deflect_vs_flank_and_water_jets():
    """Sluice Guard deflects frontal hits (0.25x), takes full flank hits, and fires 3 (P1) / 5 (P2) jets."""
    state = _make_state("sunlit_aqueducts")
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
        boss = SluiceGateLeviathanBoss(300.0, 300.0)
        boss.facing = (1.0, 0.0)
        boss.attack_mode = "sluice_guard"
        boss.armor_active = True
        boss.weakpoint_exposed_timer = 0.0
        state.enemies = [boss]

        bcx, bcy = boss.get_center()
        assert boss.check_gimmick_hit(bcx + 80.0, bcy) == "armor"
        assert boss.check_gimmick_hit(bcx - 80.0, bcy) == "normal"

        # Frontal sluice-gate shield melee hit deflects at 0.25x with armor_deflect SFX
        base_dmg = float(state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE))
        hp_before = boss.hp
        state.player.x = bcx + 50.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (-1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)
        assert hp_before - boss.hp == pytest.approx(base_dmg * constants.SLUICE_LEVIATHAN_ARMOR_DAMAGE_MULT)
        assert constants.ARMOR_DEFLECT_SFX in played_sfx

        # Flanking behind/around its unarmored siphon flank deals full 1.0x damage
        hp_mid = boss.hp
        state.player.x = bcx - 50.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)
        assert hp_mid - boss.hp == pytest.approx(base_dmg)

        # Phase 1 fires 3 fan water-ink jet bolts
        boss.stagger_timer = 0.0
        boss.phase = 1
        boss.ink_bolts.clear()
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert len(boss.ink_bolts) == constants.SLUICE_LEVIATHAN_BOLT_COUNT_P1
        assert all(b.get("style") == "water_jet" and b.get("pattern") == "fan" for b in boss.ink_bolts)

        # Phase 2 escalation at <= 50% HP fires 5 cascading water-ink jet bolts
        boss.stagger_timer = 0.0
        boss.ink_bolts.clear()
        boss.hp = boss.max_hp * 0.50
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert boss.phase == 2
        assert len(boss.ink_bolts) == constants.SLUICE_LEVIATHAN_BOLT_COUNT_P2
        assert all(b.get("pattern") == "cascade" for b in boss.ink_bolts)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_tidal_surge_to_siphon_breach_crit_and_phase2_three_slams():
    """Tidal Surge runs 2 (P1) / 3 (P2) slams into 1.50s Siphon Breach; striking deals 2.5x crit & resets."""
    state = _make_state("sunlit_aqueducts")
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    state.network_manager.network_mode = "HOST"
    try:
        boss = SluiceGateLeviathanBoss(320.0, 320.0)
        state.enemies = [boss]
        state.player.x = 640.0
        state.player.y = 320.0

        # Transition sluice_guard -> tidal_surge
        boss.mode_timer = 0.01
        boss.update(0.05, state)
        assert boss.attack_mode == "tidal_surge"

        p1_max_slams = 0
        saw_wave_arc = False
        saw_tidal_spray = False
        for _ in range(120):
            boss.update(0.05, state)
            p1_max_slams = max(p1_max_slams, boss.slam_count)
            if boss.wave_arcs:
                saw_wave_arc = True
            if any(b.get("style") == "tidal_spray" for b in boss.ink_bolts):
                saw_tidal_spray = True
            if boss.attack_mode == "siphon_breach":
                break

        assert p1_max_slams == constants.SLUICE_LEVIATHAN_SLAM_COUNT_P1
        assert saw_wave_arc is True
        assert saw_tidal_spray is True
        assert boss.attack_mode == "siphon_breach"
        assert boss.armor_active is False
        assert boss.weakpoint_exposed_timer == pytest.approx(constants.SLUICE_LEVIATHAN_BREACH_DURATION)
        assert constants.BOSS_EXPOSE_SFX in played_sfx
        assert any(entry[0] == constants.BOSS_EXPOSE_SFX for entry in state.pending_remote_sfx)

        # Visual packet exposes required telemetry keys
        pkt = boss.get_visual_packet()
        for req_key in (
            "attack_mode",
            "phase",
            "slam_count",
            "shield_angle_deg",
            "leg_phase",
            "armor_active",
            "weakpoint_exposed_timer",
        ):
            assert req_key in pkt
        assert pkt["attack_mode"] == "siphon_breach"
        assert pkt["armor_active"] is False
        assert pkt["weakpoint_exposed_timer"] > 0.0

        # Strike exposed turquoise siphon core -> 2.5x crit, sparks, stun, and reset to sluice_guard
        bcx, bcy = boss.get_center()
        base_dmg = float(state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE))
        hp_before = boss.hp
        boss.water_sparks.clear()
        state.player.x = bcx - 46.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)

        assert hp_before - boss.hp == pytest.approx(base_dmg * constants.SLUICE_LEVIATHAN_WEAKPOINT_DAMAGE_MULT)
        assert constants.WEAKPOINT_CRIT_SFX in played_sfx
        assert len(boss.water_sparks) > 0
        assert boss.stagger_timer >= constants.SLUICE_LEVIATHAN_BREACH_STUN_DURATION
        assert boss.attack_mode == "sluice_guard"
        assert boss.armor_active is True
        assert boss.weakpoint_exposed_timer == 0.0

        # Phase 2 promotes Tidal Surge to 3 advancing hydraulic slams
        boss.stagger_timer = 0.0
        boss.hp = boss.max_hp * 0.45
        boss._check_phase2_transition(state)
        assert boss.phase == 2
        boss._enter_tidal_surge(state)
        p2_max_slams = 0
        for _ in range(160):
            boss.update(0.05, state)
            p2_max_slams = max(p2_max_slams, boss.slam_count)
            if boss.attack_mode == "siphon_breach":
                break
        assert boss.attack_mode == "siphon_breach"
        assert p2_max_slams == constants.SLUICE_LEVIATHAN_SLAM_COUNT_P2
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_sluice_leviathan_music_selection_and_generated_assets():
    """Audio selector plays boss_sluice_leviathan.ogg and generated PNG/OGG assets verify cleanly."""
    assert constants.SLUICE_LEVIATHAN_MUSIC == "boss_sluice_leviathan.ogg"
    assert constants.SLUICE_LEVIATHAN_MUSIC in constants.BOSS_COMBAT_TRACKS

    state = _make_state("sunlit_aqueducts")
    try:
        boss = SluiceGateLeviathanBoss(state.player.x + 80.0, state.player.y)
        state.enemies = [boss]
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.SLUICE_LEVIATHAN_MUSIC
    finally:
        state.shutdown_save_worker(timeout=1.0)

    # Verify generated OGG boss theme
    music_path = os.path.join("assets", "audio", "music", constants.SLUICE_LEVIATHAN_MUSIC)
    assert os.path.exists(music_path)
    assert generate_sfx.verify_ogg(music_path) > 10.0

    # Verify all 4 modular articulated PNG parts exist with expected dimensions & SRCALPHA
    if not pygame.get_init():
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
    expected_parts = {
        "sluice_leviathan_shell.png": (64, 56),
        "sluice_leviathan_shield_claw.png": (44, 48),
        "sluice_leviathan_pincer.png": (36, 36),
        "sluice_leviathan_leg.png": (40, 22),
    }
    for fname, dims in expected_parts.items():
        path = os.path.join("assets", "graphics", fname)
        assert os.path.exists(path), f"Missing {path}"
        surf = pygame.image.load(path)
        assert surf.get_size() == dims
        assert surf.get_at((0, 0))[3] == 0


def test_sluice_leviathan_articulated_rig_rendering_and_fallback():
    """Renderer draws The Sluice-Gate Leviathan via articulated rig in all 3 modes & falls back cleanly."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if not pygame.display.get_init():
        pygame.init()
    screen = pygame.Surface((360, 360), pygame.SRCALPHA)
    renderer = Renderer(screen)

    part_keys = (
        "sluice_leviathan_shell.png",
        "sluice_leviathan_shield_claw.png",
        "sluice_leviathan_pincer.png",
        "sluice_leviathan_leg.png",
    )
    for key in part_keys:
        assert key in renderer.image_cache

    boss = SluiceGateLeviathanBoss(120.0, 120.0)
    draw_rect = pygame.Rect(124, 124, boss.width, boss.height)

    for mode, substate, sh_deg, weak_t in (
        ("sluice_guard", "telegraph", constants.SLUICE_LEVIATHAN_SHIELD_GUARD_DEG, 0.0),
        ("tidal_surge", "telegraph", constants.SLUICE_LEVIATHAN_SHIELD_RAISE_DEG, 0.0),
        ("tidal_surge", "impact", constants.SLUICE_LEVIATHAN_SHIELD_SLAM_DEG, 0.0),
        ("siphon_breach", "telegraph", constants.SLUICE_LEVIATHAN_SHIELD_EMBED_DEG, 1.3),
    ):
        screen.fill((0, 0, 0, 0))
        boss.attack_mode = mode
        boss.surge_substate = substate
        boss.shield_angle_deg = sh_deg
        boss.weakpoint_exposed_timer = weak_t
        boss.armor_active = mode != "siphon_breach"
        boss.leg_phase = 1.6
        boss.wave_arcs = [
            {
                "x": boss.x + boss.width * 0.5,
                "y": boss.y + boss.height * 0.5,
                "angle": 0.4,
                "radius": 72.0,
                "max_radius": 150.0,
                "life": 0.28,
                "max_life": 0.50,
            }
        ]
        boss.water_sparks = [
            {"x": boss.x + 30.0, "y": boss.y + 30.0, "vx": 10.0, "vy": -15.0, "life": 0.3, "max_life": 0.55}
        ]
        pkt = boss.get_visual_packet()
        assert renderer.draw_procedural_enemy(boss, draw_rect, pkt, constants.COLOR_WHITE) is True
        non_empty = any(
            screen.get_at((x, y))[3] > 0
            for x in range(80, 280, 8)
            for y in range(80, 280, 8)
        )
        assert non_empty is True

    # Ensure draw_boss_weapon skips SluiceGateLeviathanBoss cleanly
    screen.fill((0, 0, 0, 0))
    renderer.draw_boss_weapon(boss, 0.0, 0.0)
    assert not any(screen.get_at((x, y))[3] > 0 for x in range(80, 280, 8) for y in range(80, 280, 8))

    # Strip PNGs to verify procedural fallback renders cleanly
    for key in part_keys:
        renderer.image_cache.pop(key, None)
    screen.fill((0, 0, 0, 0))
    boss.attack_mode = "sluice_guard"
    boss.armor_active = True
    assert renderer.draw_procedural_enemy(boss, draw_rect, boss.get_visual_packet(), constants.COLOR_WHITE) is True
    assert any(screen.get_at((x, y))[3] > 0 for x in range(100, 260, 8) for y in range(100, 260, 8))
