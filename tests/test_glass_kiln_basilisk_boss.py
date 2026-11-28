# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for The Vitreous Basin Night Boss: The Glass-Kiln Basilisk (Step 4)."""
# pylint: disable=no-member,protected-access
import math
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
    TypesetterAutomatonBoss,
)
from engine.game_state import GameState
from engine.player import PlayerStateEnum
from engine.world import Respite, World
from rendering.renderer import Renderer


def _make_state(biome="vitreous_basin"):
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


def test_vitreous_basin_spawns_glass_kiln_basilisk_and_metadata():
    """Vitreous Basin Night Boss spawn instantiates GlassKilnBasiliskBoss, preserved on Respite rest."""
    state = _make_state("vitreous_basin")
    try:
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)

        assert len(state.enemies) == 1
        boss = state.enemies[0]
        assert isinstance(boss, GlassKilnBasiliskBoss)
        assert isinstance(boss, NightBoss)
        assert (boss.width, boss.height) == (constants.GLASS_BASILISK_SIZE, constants.GLASS_BASILISK_SIZE)
        assert boss.hp == pytest.approx(constants.NIGHT_BOSS_MAX_HP)
        assert boss.name == "Night Boss"
        assert boss.display_name == "The Glass-Kiln Basilisk"
        assert boss.get_display_name() == "The Glass-Kiln Basilisk"
        assert boss.is_glass_basilisk is True
        assert boss.armor_front_only is False
        assert boss.armor_damage_mult == pytest.approx(constants.GLASS_BASILISK_ARMOR_DAMAGE_MULT)
        assert boss.weakpoint_damage_mult == pytest.approx(constants.GLASS_BASILISK_WEAKPOINT_DAMAGE_MULT)
        assert constants.BOSS_HUD_DISPLAY_NAMES["GlassKilnBasiliskBoss"] == "The Glass-Kiln Basilisk"
        assert ENEMY_REGISTRY["GlassKilnBasiliskBoss"] is GlassKilnBasiliskBoss
        assert boss.is_within_active_simulation(state) is True

        # Respite rest must preserve live GlassKilnBasiliskBoss
        respite = Respite((40.0, 40.0), (40, 40))
        respite.execute_rest(state)
        assert any(isinstance(e, GlassKilnBasiliskBoss) for e in state.enemies)
    finally:
        state.shutdown_save_worker(timeout=1.0)


@pytest.mark.parametrize(
    ("biome", "expected_cls"),
    [
        ("vitreous_basin", GlassKilnBasiliskBoss),
        ("tech_tower", TypesetterAutomatonBoss),
        ("windy_ridge", GaleVaneRaptorBoss),
        ("swamp_mire", SlugBoss),
        ("pastoral_valley", MeadowCensorBoss),
        ("frozen_peaks", RimecrestArbiterBoss),
    ],
)
def test_lan_client_resolves_vitreous_basin_night_boss_by_biome(biome, expected_cls):
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


def test_salt_slither_full_body_armor_deflect_and_prism_bolts():
    """Salt Slither deflects hits from all angles (0.25x) and fires 3 spread (P1) / 5 alternating (P2) bolts."""
    state = _make_state("vitreous_basin")
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
        boss = GlassKilnBasiliskBoss(300.0, 300.0)
        boss.facing = (1.0, 0.0)
        boss.attack_mode = "salt_slither"
        boss.armor_active = True
        boss.weakpoint_exposed_timer = 0.0
        state.enemies = [boss]

        bcx, bcy = boss.get_center()
        # Full-body fused-salt shell: both front and rear hits classify as armor
        assert boss.check_gimmick_hit(bcx + 80.0, bcy) == "armor"
        assert boss.check_gimmick_hit(bcx - 80.0, bcy) == "armor"

        base_dmg = float(state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE))

        # Frontal strike glances off at 0.25x with armor_deflect SFX
        hp_before = boss.hp
        state.player.x = bcx + 50.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (-1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)
        assert hp_before - boss.hp == pytest.approx(base_dmg * constants.GLASS_BASILISK_ARMOR_DAMAGE_MULT)
        assert constants.ARMOR_DEFLECT_SFX in played_sfx

        # Rear strike ALSO glances off at 0.25x (full-body shell)
        played_sfx.clear()
        hp_mid = boss.hp
        state.player.x = bcx - 50.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)
        assert hp_mid - boss.hp == pytest.approx(base_dmg * constants.GLASS_BASILISK_ARMOR_DAMAGE_MULT)
        assert constants.ARMOR_DEFLECT_SFX in played_sfx

        # Phase 1 fires 3 spread prism ink bolts while advancing slither_phase
        boss.stagger_timer = 0.0
        boss.phase = 1
        boss.ink_bolts.clear()
        slither_before = boss.slither_phase
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert boss.slither_phase > slither_before
        assert len(boss.ink_bolts) == constants.GLASS_BASILISK_BOLT_COUNT_P1
        assert all(b.get("style") == "prism_bolt" for b in boss.ink_bolts)

        # Phase 2 escalation at <= 50% HP fires 5 alternating prism ink bolts
        boss.stagger_timer = 0.0
        boss.ink_bolts.clear()
        boss.hp = boss.max_hp * 0.50
        boss.volley_alt = 0
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert boss.phase == 2
        assert len(boss.ink_bolts) == constants.GLASS_BASILISK_BOLT_COUNT_P2
        first_pattern = boss.ink_bolts[0]["pattern"]

        boss.ink_bolts.clear()
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert len(boss.ink_bolts) == constants.GLASS_BASILISK_BOLT_COUNT_P2
        assert boss.ink_bolts[0]["pattern"] != first_pattern
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_solar_refraction_beam_sweep_to_kiln_crack_crit_and_phase2_fan():
    """Solar Refraction sweeps beam(s), damages player in ray, opens 1.55s Kiln Crack, and takes 2.5x crit."""
    state = _make_state("vitreous_basin")
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    state.network_manager.network_mode = "HOST"
    try:
        boss = GlassKilnBasiliskBoss(360.0, 360.0)
        state.enemies = [boss]
        bcx, bcy = boss.get_center()
        # Stand along the +X axis within beam sweep range so the sweeping ray hits the player
        state.player.x = bcx + 160.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        player_hp_before = state.player.hp

        # Force transition salt_slither -> solar_refraction
        boss.mode_timer = 0.01
        boss.update(0.05, state)
        assert boss.attack_mode == "solar_refraction"
        assert boss.beam_active is False
        assert len(boss.get_active_beam_angles()) == constants.GLASS_BASILISK_BEAM_FAN_COUNT_P1

        saw_active_beam = False
        beam_angles_seen = []
        for _ in range(120):
            boss.update(0.05, state)
            if boss.beam_active:
                saw_active_beam = True
                beam_angles_seen.append(boss.beam_angle_rad)
            if boss.attack_mode == "kiln_crack":
                break

        assert saw_active_beam is True
        assert len(beam_angles_seen) >= 4
        assert abs(beam_angles_seen[-1] - beam_angles_seen[0]) > 0.5
        assert state.player.hp < player_hp_before

        # Thermal shock immediately opens 1.55s kiln_crack weakpoint window + queues Host SFX
        assert boss.attack_mode == "kiln_crack"
        assert boss.armor_active is False
        assert boss.beam_active is False
        assert boss.weakpoint_exposed_timer == pytest.approx(constants.GLASS_BASILISK_KILN_CRACK_DURATION)
        assert constants.BOSS_EXPOSE_SFX in played_sfx
        assert any(entry[0] == constants.BOSS_EXPOSE_SFX for entry in state.pending_remote_sfx)

        # Visual packet exposes all required telemetry keys
        pkt = boss.get_visual_packet()
        for req_key in (
            "attack_mode",
            "phase",
            "slither_phase",
            "beam_angle_rad",
            "beam_active",
            "armor_active",
            "weakpoint_exposed_timer",
        ):
            assert req_key in pkt
        assert pkt["attack_mode"] == "kiln_crack"
        assert pkt["armor_active"] is False
        assert pkt["beam_active"] is False
        assert pkt["weakpoint_exposed_timer"] > 0.0

        # Striking cracked molten core deals 2.5x crit, bursts sparks, stuns wyrm & resets to salt_slither
        base_dmg = float(state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE))
        hp_before = boss.hp
        boss.glass_sparks.clear()
        state.player.x = bcx - 46.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)

        assert hp_before - boss.hp == pytest.approx(base_dmg * constants.GLASS_BASILISK_WEAKPOINT_DAMAGE_MULT)
        assert constants.WEAKPOINT_CRIT_SFX in played_sfx
        assert len(boss.glass_sparks) > 0
        assert boss.stagger_timer >= constants.GLASS_BASILISK_CRACK_STUN_DURATION
        assert boss.attack_mode == "salt_slither"
        assert boss.armor_active is True
        assert boss.weakpoint_exposed_timer == 0.0

        # Phase 2 promotes solar_refraction to 3 sweeping fan beams
        boss.stagger_timer = 0.0
        boss.hp = boss.max_hp * 0.45
        boss._check_phase2_transition(state)
        assert boss.phase == 2
        boss._enter_solar_refraction(bcx + 160.0, bcy, state)
        p2_angles = boss.get_active_beam_angles()
        assert len(p2_angles) == constants.GLASS_BASILISK_BEAM_FAN_COUNT_P2
        assert math.isclose(p2_angles[2] - p2_angles[1], constants.GLASS_BASILISK_BEAM_FAN_SPREAD_RAD, rel_tol=1e-4)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_glass_basilisk_music_selection_and_generated_assets():
    """Audio selector plays boss_glass_basilisk.ogg and generated PNG/OGG assets verify cleanly."""
    assert constants.GLASS_BASILISK_MUSIC == "boss_glass_basilisk.ogg"
    assert constants.GLASS_BASILISK_MUSIC in constants.BOSS_COMBAT_TRACKS

    state = _make_state("vitreous_basin")
    try:
        boss = GlassKilnBasiliskBoss(state.player.x + 80.0, state.player.y)
        state.enemies = [boss]
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.GLASS_BASILISK_MUSIC
    finally:
        state.shutdown_save_worker(timeout=1.0)

    # Verify generated OGG boss theme
    music_path = os.path.join("assets", "audio", "music", constants.GLASS_BASILISK_MUSIC)
    assert os.path.exists(music_path)
    assert generate_sfx.verify_ogg(music_path) > 10.0

    # Verify all 3 modular articulated PNG parts exist with expected dimensions & SRCALPHA
    if not pygame.get_init():
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
    expected_parts = {
        "glass_basilisk_head.png": (48, 44),
        "glass_basilisk_segment.png": (44, 40),
        "glass_basilisk_tail.png": (44, 32),
    }
    for fname, dims in expected_parts.items():
        path = os.path.join("assets", "graphics", fname)
        assert os.path.exists(path), f"Missing {path}"
        surf = pygame.image.load(path)
        assert surf.get_size() == dims
        assert surf.get_at((0, 0))[3] == 0


def test_glass_basilisk_articulated_rig_rendering_and_fallback():
    """Renderer draws The Glass-Kiln Basilisk via articulated rig in all 3 states and falls back cleanly."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if not pygame.display.get_init():
        pygame.init()
    screen = pygame.Surface((360, 360), pygame.SRCALPHA)
    renderer = Renderer(screen)

    part_keys = (
        "glass_basilisk_head.png",
        "glass_basilisk_segment.png",
        "glass_basilisk_tail.png",
    )
    for key in part_keys:
        assert key in renderer.image_cache

    boss = GlassKilnBasiliskBoss(120.0, 120.0)
    draw_rect = pygame.Rect(124, 124, boss.width, boss.height)

    for mode, substate, beam_on, phase, weak_t in (
        ("salt_slither", "charge", False, 1, 0.0),
        ("solar_refraction", "charge", False, 1, 0.0),
        ("solar_refraction", "sweep", True, 2, 0.0),
        ("kiln_crack", "charge", False, 2, 1.35),
    ):
        screen.fill((0, 0, 0, 0))
        boss.attack_mode = mode
        boss.refraction_substate = substate
        boss.beam_active = beam_on
        boss.phase = phase
        boss.beam_angle_rad = 0.35
        boss.slither_phase = 1.6
        boss.weakpoint_exposed_timer = weak_t
        boss.armor_active = mode != "kiln_crack"
        boss.glass_sparks = [
            {"x": boss.x + 40.0, "y": boss.y + 40.0, "vx": 15.0, "vy": -15.0, "life": 0.35, "max_life": 0.55}
        ]
        pkt = boss.get_visual_packet()
        assert renderer.draw_procedural_enemy(boss, draw_rect, pkt, constants.COLOR_WHITE) is True
        non_empty = any(
            screen.get_at((x, y))[3] > 0
            for x in range(80, 280, 8)
            for y in range(80, 280, 8)
        )
        assert non_empty is True

    # Ensure draw_boss_weapon skips GlassKilnBasiliskBoss cleanly
    screen.fill((0, 0, 0, 0))
    renderer.draw_boss_weapon(boss, 0.0, 0.0)
    assert not any(screen.get_at((x, y))[3] > 0 for x in range(80, 280, 8) for y in range(80, 280, 8))

    # Strip PNGs to verify procedural fallback renders cleanly
    for key in part_keys:
        renderer.image_cache.pop(key, None)
    screen.fill((0, 0, 0, 0))
    boss.attack_mode = "salt_slither"
    boss.armor_active = True
    assert renderer.draw_procedural_enemy(boss, draw_rect, boss.get_visual_packet(), constants.COLOR_WHITE) is True
    assert any(screen.get_at((x, y))[3] > 0 for x in range(100, 260, 8) for y in range(100, 260, 8))
