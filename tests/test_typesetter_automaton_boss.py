# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Tech Tower Night Boss: The Typesetter Automaton (Step 3)."""
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
    TypesetterAutomatonBoss,
)
from engine.game_state import GameState
from engine.player import PlayerStateEnum
from engine.world import Respite, World
from rendering.renderer import Renderer


def _make_state(biome="tech_tower"):
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


def test_tech_tower_spawns_typesetter_automaton_and_metadata():
    """Tech Tower Night Boss spawn instantiates TypesetterAutomatonBoss, preserved on Respite rest."""
    state = _make_state("tech_tower")
    try:
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)

        assert len(state.enemies) == 1
        boss = state.enemies[0]
        assert isinstance(boss, TypesetterAutomatonBoss)
        assert isinstance(boss, NightBoss)
        assert (boss.width, boss.height) == (constants.TYPESETTER_SIZE, constants.TYPESETTER_SIZE)
        assert boss.hp == pytest.approx(constants.NIGHT_BOSS_MAX_HP)
        assert boss.name == "Night Boss"
        assert boss.display_name == "The Typesetter Automaton"
        assert boss.get_display_name() == "The Typesetter Automaton"
        assert boss.is_typesetter_boss is True
        assert constants.BOSS_HUD_DISPLAY_NAMES["TypesetterAutomatonBoss"] == "The Typesetter Automaton"
        assert ENEMY_REGISTRY["TypesetterAutomatonBoss"] is TypesetterAutomatonBoss
        assert boss.is_within_active_simulation(state) is True

        # Respite rest must preserve live TypesetterAutomatonBoss
        respite = Respite((40.0, 40.0), (40, 40))
        respite.execute_rest(state)
        assert any(isinstance(e, TypesetterAutomatonBoss) for e in state.enemies)
    finally:
        state.shutdown_save_worker(timeout=1.0)


@pytest.mark.parametrize(
    ("biome", "expected_cls"),
    [
        ("tech_tower", TypesetterAutomatonBoss),
        ("windy_ridge", GaleVaneRaptorBoss),
        ("swamp_mire", SlugBoss),
        ("pastoral_valley", MeadowCensorBoss),
        ("frozen_peaks", RimecrestArbiterBoss),
    ],
)
def test_lan_client_resolves_tech_tower_night_boss_by_biome(biome, expected_cls):
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


def test_platen_march_frontal_armor_vs_flank_and_alternating_slugs():
    """Platen March deflects frontal hits (0.25x), takes full flank hits, and fires alternating 3/5 slugs."""
    state = _make_state("tech_tower")
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
        boss = TypesetterAutomatonBoss(300.0, 300.0)
        boss.facing = (1.0, 0.0)
        boss.attack_mode = "platen_march"
        boss.armor_active = True
        boss.weakpoint_exposed_timer = 0.0
        state.enemies = [boss]

        bcx, bcy = boss.get_center()
        assert boss.check_gimmick_hit(bcx + 80.0, bcy) == "armor"
        assert boss.check_gimmick_hit(bcx - 80.0, bcy) == "normal"

        # Frontal carapace melee hit deflects at 0.25x with armor_deflect SFX
        base_dmg = float(state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE))
        hp_before = boss.hp
        state.player.x = bcx + 50.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (-1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)
        assert hp_before - boss.hp == pytest.approx(base_dmg * constants.TYPESETTER_ARMOR_DAMAGE_MULT)
        assert constants.ARMOR_DEFLECT_SFX in played_sfx

        # Flanking behind the carriage deals full 1.0x damage
        hp_mid = boss.hp
        state.player.x = bcx - 50.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)
        assert hp_mid - boss.hp == pytest.approx(base_dmg)

        # Phase 1 fires 3 alternating horizontal/diagonal ink-slug bolts
        boss.stagger_timer = 0.0
        boss.phase = 1
        boss.volley_alt = 0
        boss.ink_bolts.clear()
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert len(boss.ink_bolts) == constants.TYPESETTER_SLUG_COUNT_P1
        assert all(b["pattern"] == "horizontal" for b in boss.ink_bolts)

        boss.ink_bolts.clear()
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert len(boss.ink_bolts) == constants.TYPESETTER_SLUG_COUNT_P1
        assert all(b["pattern"] == "diagonal" for b in boss.ink_bolts)

        # Phase 2 escalation at <= 50% HP fires 5 bolts
        boss.stagger_timer = 0.0
        boss.ink_bolts.clear()
        boss.hp = boss.max_hp * 0.50
        boss.volley_timer = 0.01
        boss.mode_timer = 5.0
        boss.update(0.05, state)
        assert boss.phase == 2
        assert len(boss.ink_bolts) == constants.TYPESETTER_SLUG_COUNT_P2
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_type_stamp_three_stamps_to_boiler_vent_crit_and_phase2_cadence():
    """3 rhythmic ground stamps open 1.50s Boiler Vent; striking deals 2.5x crit, steam sparks, stun & reset."""
    state = _make_state("tech_tower")
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        calculate_spatial_volume=lambda _d: 1.0,
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    state.network_manager.network_mode = "HOST"
    try:
        boss = TypesetterAutomatonBoss(360.0, 360.0)
        state.enemies = [boss]
        state.player.x = 640.0
        state.player.y = 360.0

        # Force transition from platen_march -> type_stamp
        boss.mode_timer = 0.01
        boss.update(0.05, state)
        assert boss.attack_mode == "type_stamp"
        assert boss.stamp_count == 0

        # Step through all 3 stamps and verify shockwave rings + radial bolts + boiler_vent transition
        max_stamps_seen = 0
        p1_steps = 0
        p1_ring_max_r = 0.0
        saw_radial_bolts = False
        for _ in range(120):
            p1_steps += 1
            boss.update(0.05, state)
            max_stamps_seen = max(max_stamps_seen, boss.stamp_count)
            for ring in boss.shockwave_rings:
                p1_ring_max_r = max(p1_ring_max_r, float(ring["max_radius"]))
            if any(b.get("style") == "type_stamp_bolt" for b in boss.ink_bolts):
                saw_radial_bolts = True
            if boss.attack_mode == "boiler_vent":
                break

        assert max_stamps_seen == constants.TYPESETTER_STAMP_COUNT
        assert saw_radial_bolts is True
        assert p1_ring_max_r == pytest.approx(constants.TYPESETTER_STAMP_RING_RADIUS_P1)
        assert boss.attack_mode == "boiler_vent"
        assert boss.armor_active is False
        assert boss.weakpoint_exposed_timer == pytest.approx(constants.TYPESETTER_BOILER_VENT_DURATION)
        assert constants.BOSS_EXPOSE_SFX in played_sfx
        assert any(entry[0] == constants.BOSS_EXPOSE_SFX for entry in state.pending_remote_sfx)

        # Visual packet exposes required telemetry keys
        pkt = boss.get_visual_packet()
        for req_key in (
            "attack_mode",
            "phase",
            "stamp_count",
            "platen_offset_y",
            "leg_phase",
            "armor_active",
            "weakpoint_exposed_timer",
        ):
            assert req_key in pkt
        assert pkt["attack_mode"] == "boiler_vent"
        assert pkt["armor_active"] is False
        assert pkt["weakpoint_exposed_timer"] > 0.0

        # Dash inside final ring and strike exposed boiler: 2.5x crit, steam sparks, stun & reset to platen_march
        bcx, bcy = boss.get_center()
        base_dmg = float(state.player.get_active_weapon().get("damage", constants.SWORD_DAMAGE))
        hp_before = boss.hp
        boss.steam_sparks.clear()
        state.player.x = bcx - 46.0 - state.player.width * 0.5
        state.player.y = bcy - state.player.height * 0.5
        state.player.facing = (1.0, 0.0)
        state.player.state = PlayerStateEnum.ATTACKING
        state.player.hit_entities_this_attack = set()
        state.update_combat(0.016, False, {}, state.audio_manager)

        assert hp_before - boss.hp == pytest.approx(base_dmg * constants.TYPESETTER_WEAKPOINT_DAMAGE_MULT)
        assert constants.WEAKPOINT_CRIT_SFX in played_sfx
        assert len(boss.steam_sparks) > 0
        assert boss.stagger_timer >= constants.TYPESETTER_VENT_STUN_DURATION
        assert boss.attack_mode == "platen_march"
        assert boss.armor_active is True
        assert boss.weakpoint_exposed_timer == 0.0

        # Verify Phase 2 stamps faster and produces wider shockwave rings
        boss.stagger_timer = 0.0
        boss.hp = boss.max_hp * 0.40
        boss._check_phase2_transition(state)
        assert boss.phase == 2
        boss.shockwave_rings.clear()
        boss._enter_type_stamp(state)
        p2_steps = 0
        p2_ring_max_r = 0.0
        for _ in range(120):
            p2_steps += 1
            boss.update(0.05, state)
            for ring in boss.shockwave_rings:
                p2_ring_max_r = max(p2_ring_max_r, float(ring["max_radius"]))
            if boss.attack_mode == "boiler_vent":
                break
        assert boss.attack_mode == "boiler_vent"
        assert p2_steps < p1_steps
        assert p2_ring_max_r == pytest.approx(constants.TYPESETTER_STAMP_RING_RADIUS_P2)
        assert p2_ring_max_r > p1_ring_max_r
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_typesetter_music_selection_and_generated_assets():
    """Audio selector plays boss_typesetter.ogg and generated PNG/OGG assets verify cleanly."""
    assert constants.TYPESETTER_MUSIC == "boss_typesetter.ogg"
    assert constants.TYPESETTER_MUSIC in constants.BOSS_COMBAT_TRACKS

    state = _make_state("tech_tower")
    try:
        boss = TypesetterAutomatonBoss(state.player.x + 80.0, state.player.y)
        state.enemies = [boss]
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.TYPESETTER_MUSIC
    finally:
        state.shutdown_save_worker(timeout=1.0)

    # Verify generated OGG boss theme
    music_path = os.path.join("assets", "audio", "music", constants.TYPESETTER_MUSIC)
    assert os.path.exists(music_path)
    assert generate_sfx.verify_ogg(music_path) > 10.0

    # Verify all 4 modular articulated PNG parts exist with expected dimensions & SRCALPHA
    if not pygame.get_init():
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.init()
    expected_parts = {
        "typesetter_chassis.png": (64, 56),
        "typesetter_turret.png": (36, 36),
        "typesetter_leg.png": (44, 24),
        "typesetter_platen.png": (48, 32),
    }
    for fname, dims in expected_parts.items():
        path = os.path.join("assets", "graphics", fname)
        assert os.path.exists(path), f"Missing {path}"
        surf = pygame.image.load(path)
        assert surf.get_size() == dims
        assert surf.get_at((0, 0))[3] == 0


def test_typesetter_articulated_rig_rendering_and_fallback():
    """Renderer draws The Typesetter Automaton via articulated rig in all 3 modes and gracefully falls back."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    if not pygame.display.get_init():
        pygame.init()
    screen = pygame.Surface((320, 320), pygame.SRCALPHA)
    renderer = Renderer(screen)

    part_keys = (
        "typesetter_chassis.png",
        "typesetter_turret.png",
        "typesetter_leg.png",
        "typesetter_platen.png",
    )
    for key in part_keys:
        assert key in renderer.image_cache

    boss = TypesetterAutomatonBoss(100.0, 100.0)
    draw_rect = pygame.Rect(104, 104, boss.width, boss.height)

    for mode, substate, platen_y, weak_t in (
        ("platen_march", "lift", 0.0, 0.0),
        ("type_stamp", "lift", -24.0, 0.0),
        ("type_stamp", "impact", 14.0, 0.0),
        ("boiler_vent", "impact", -10.0, 1.3),
    ):
        screen.fill((0, 0, 0, 0))
        boss.attack_mode = mode
        boss.stamp_substate = substate
        boss.platen_offset_y = platen_y
        boss.weakpoint_exposed_timer = weak_t
        boss.armor_active = mode != "boiler_vent"
        boss.leg_phase = 1.4
        boss.shockwave_rings = [
            {
                "x": boss.x + boss.width * 0.5,
                "y": boss.y + boss.height * 0.5,
                "radius": 68.0,
                "max_radius": 155.0,
                "life": 0.30,
                "max_life": 0.52,
            }
        ]
        boss.steam_sparks = [
            {"x": boss.x + 20.0, "y": boss.y + 20.0, "vx": 0.0, "vy": -20.0, "life": 0.3, "max_life": 0.55}
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
    for key in part_keys:
        renderer.image_cache.pop(key, None)
    screen.fill((0, 0, 0, 0))
    boss.attack_mode = "platen_march"
    assert renderer.draw_procedural_enemy(boss, draw_rect, boss.get_visual_packet(), constants.COLOR_WHITE) is True
    assert any(screen.get_at((x, y))[3] > 0 for x in range(100, 220, 8) for y in range(100, 220, 8))
