# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Batch 4 Pass 2: Swamp Night Boss (SlugBoss), slime pools, ground crown & dual weapon scatter."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import math
import os
from types import SimpleNamespace

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
import generate_sfx
from engine.actor import ActorState
from engine.enemy import NightBoss, SlugBoss, SlugEnemy
from engine.game_state import GameState
from engine.world import SlugBossCrown, WeaponPickup, World
from generate_assets import generate_slug_boss, generate_slug_boss_crown
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_slug_boss_assets_and_sfx_exist_and_preload():
    """Verify slug_boss.png, slug_boss_crown.png, and slug_boss_slime.ogg exist, generate cleanly, and preload."""
    boss_path = os.path.join("assets", "graphics", "slug_boss.png")
    crown_path = os.path.join("assets", "graphics", "slug_boss_crown.png")
    sfx_path = os.path.join("assets", "audio", "sfx", "slug_boss_slime.ogg")
    assert os.path.exists(boss_path), f"Missing generated asset: {boss_path}"
    assert os.path.exists(crown_path), f"Missing generated asset: {crown_path}"
    assert os.path.exists(sfx_path), f"Missing generated SFX: {sfx_path}"

    assert pygame.image.load(boss_path).get_size() == (constants.SLUG_BOSS_SIZE, constants.SLUG_BOSS_SIZE)
    assert pygame.image.load(crown_path).get_size() == (
        constants.SLUG_BOSS_CROWN_WIDTH,
        constants.SLUG_BOSS_CROWN_HEIGHT,
    )

    gen_boss = generate_slug_boss()
    gen_crown = generate_slug_boss_crown()
    assert gen_boss.get_size() == (112, 112) and gen_boss.get_at((0, 0)).a == 0
    assert gen_crown.get_size() == (44, 32) and gen_crown.get_at((0, 0)).a == 0

    sfx_len = generate_sfx.verify_ogg(sfx_path)
    assert 0.40 <= sfx_len <= 0.70

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "SlugBoss" in renderer.prop_cache
    assert renderer.prop_cache["SlugBoss"].get_size() == (112, 112)
    assert "SlugBossCrown" in renderer.prop_cache
    assert renderer.prop_cache["SlugBossCrown"].get_size() == (44, 32)


def test_slug_boss_spawns_as_swamp_mire_night_boss_and_keeps_generic_elsewhere():
    """Verify CLAMPED boss spawn creates SlugBoss in swamp_mire and regular NightBoss in other biomes."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        # 1. swamp_mire spawns SlugBoss (112x112 NightBoss subclass)
        state.world = World("swamp_mire")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.world.boss_coords_list = [{"x": 8, "y": 8}]
        state.current_act = 1
        state.run_biomes["act1"] = "swamp_mire"
        state.enemies = []
        state.player.x = 8 * constants.TILE_SIZE
        state.player.y = 8 * constants.TILE_SIZE
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)

        assert len(state.enemies) == 1
        boss = state.enemies[0]
        assert isinstance(boss, SlugBoss)
        assert isinstance(boss, NightBoss)
        assert boss.name == "Night Boss"
        assert boss.is_slug_boss is True
        assert (boss.width, boss.height) == (112, 112)

        # 2. windy_ridge spawns standard NightBoss (not SlugBoss)
        state.world = World("windy_ridge")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.world.boss_coords_list = [{"x": 8, "y": 8}]
        state.run_biomes["act1"] = "windy_ridge"
        state.enemies = []
        state.player.x = 8 * constants.TILE_SIZE
        state.player.y = 8 * constants.TILE_SIZE
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)

        assert len(state.enemies) == 1
        assert isinstance(state.enemies[0], NightBoss)
        assert not isinstance(state.enemies[0], SlugBoss)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_slug_boss_charging_movement_attack_damages_player_and_alternates_to_slime():
    """Verify SlugBoss surges forward during CHARGE STRIKE, damages player, and flips to SLIME mode."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("swamp_mire")
        state.world.load_from_prototype(["." * 20 for _ in range(20)])
        state.in_sanctuary = False
        state.player.x = 340.0
        state.player.y = 240.0
        initial_hp = float(state.player.hp)

        boss = SlugBoss(200.0, 200.0)
        boss.facing = (1.0, 0.0)
        boss.active_target = state.player.get_center()
        boss.attack_mode = "CHARGE"
        boss.state = ActorState.WIND_UP
        boss.combat_timer = 0.05
        state.enemies = [boss]

        start_x = boss.x
        observed_charge = False
        for _ in range(30):
            boss.update(0.04, state)
            if boss.state == ActorState.STRIKE and math.hypot(boss.vx, boss.vy) >= boss.speed * 2.0:
                observed_charge = True
            if boss.state == ActorState.RECOVERY:
                break

        assert observed_charge is True
        assert boss.x > start_x + 20.0, "SlugBoss should lunge forward during CHARGE attack"
        assert state.player.hp < initial_hp, "SlugBoss charge attack should damage player"
        assert boss.attack_mode == "SLIME", "SlugBoss should alternate from CHARGE to SLIME after STRIKE"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_slug_boss_stationary_slime_attack_plays_sfx_spawns_pools_damages_and_expires():
    """Verify stationary SLIME attack halts boss, plays slug_boss_slime.ogg, spawns damaging pools & clears cleanly."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
        state.world = World("swamp_mire")
        state.world.load_from_prototype(["." * 20 for _ in range(20)])
        state.in_sanctuary = False

        boss = SlugBoss(220.0, 220.0)
        boss.facing = (1.0, 0.0)
        boss.attack_mode = "SLIME"
        boss.state = ActorState.WIND_UP
        boss.combat_timer = 0.02
        state.enemies = [boss]

        pos_before = (boss.x, boss.y)
        # Transition WIND_UP -> STRIKE (stationary slime release)
        boss.update(0.05, state)
        assert boss.state == ActorState.STRIKE
        assert (boss.vx, boss.vy) == (0.0, 0.0)
        assert (boss.x, boss.y) == pos_before, "SlugBoss must stay stationary during SLIME attack"
        assert played_sfx.count(constants.SLUG_BOSS_SLIME_SFX) == 1
        assert len(state.slime_pools) == constants.SLUG_BOSS_SLIME_POOL_COUNT

        # Place player inside first slime pool -> takes periodic damage
        pool0 = state.slime_pools[0]
        state.player.x = pool0["x"] - state.player.width / 2.0
        state.player.y = pool0["y"] - state.player.height / 2.0
        hp_before = float(state.player.hp)
        state._update_slime_pools(0.05)
        assert state.player.hp < hp_before, "Player standing inside slime pool must take damage"

        # Advancing past SLUG_BOSS_SLIME_POOL_DURATION expires all pools
        state._update_slime_pools(constants.SLUG_BOSS_SLIME_POOL_DURATION + 0.5)
        assert not state.slime_pools

        # Map transitions / resets clear any active slime pools
        state.spawn_slime_pool(300.0, 300.0)
        assert len(state.slime_pools) == 1
        state.on_enter_sanctuary()
        assert not state.slime_pools

        state.spawn_slime_pool(300.0, 300.0)
        state.reset_to_new_game()
        assert not state.slime_pools

        state.spawn_slime_pool(300.0, 300.0)
        state.deallocate()
        assert not state.slime_pools
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_slug_boss_death_drops_non_interactive_crown_and_two_scattered_weapons():
    """Verify SlugBoss.on_death leaves a non-interactive SlugBossCrown and scatters 2 distinct WeaponPickups."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("swamp_mire")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.world.interactables = []

        boss = SlugBoss(240.0, 240.0)
        boss.on_death(state)

        crowns = [obj for obj in state.world.interactables if isinstance(obj, SlugBossCrown)]
        weapons = [obj for obj in state.world.interactables if isinstance(obj, WeaponPickup)]
        assert len(crowns) == 1
        crown = crowns[0]
        assert crown.is_interactive is False
        assert crown.is_solid is False
        assert crown.execute_interaction(state) is None
        # Standing directly on top of crown must NOT include it in nearby interactables / [E] prompt
        nearby = state.world.get_nearby_interactables((crown.x, crown.y, 40, 40))
        assert crown not in nearby

        assert len(weapons) == 2
        assert weapons[0].name != weapons[1].name, "Two scattered weapons should be distinct"
        assert (weapons[0].x, weapons[0].y) != (weapons[1].x, weapons[1].y), "Weapons should scatter apart"
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_slug_boss_renderer_draws_sprite_slime_pools_and_crown_without_greatblade(monkeypatch):
    """Verify Renderer draws SlugBoss without a greatblade, draws ground slime pools, and renders SlugBossCrown."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("swamp_mire")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.player.x = 120.0
        state.player.y = 120.0
        state.camera.instant_center((260.0, 260.0))

        boss = SlugBoss(220.0, 220.0)
        boss.state = ActorState.STRIKE
        boss.attack_mode = "SLIME"
        boss.combat_timer = 0.2
        state.enemies = [boss]
        state.spawn_slime_pool(280.0, 280.0)
        crown = SlugBossCrown((340.0, 260.0))
        state.world.interactables = [crown]

        blade_calls = []
        monkeypatch.setattr(renderer, "_draw_tapered_blade", lambda *a, **k: blade_calls.append(a))

        # Verify SlugBoss itself never invokes tapered greatblade rendering
        renderer.draw_actor_ghost(boss, 0, 0, state)
        renderer.draw_boss_weapon(boss, 0, 0)
        assert not blade_calls, "SlugBoss must never swing a tapered greatblade"

        # Full render draws slime pools beneath actors and SlugBossCrown on the floor
        renderer.render(state)
        assert any(k[0] == "slug_boss_slime_pool" for k in renderer._fx_surface_cache)

        # Direct crown rendering produces non-background pixels
        canvas = pygame.Surface((120, 120))
        canvas.fill((14, 10, 20))
        renderer.screen = canvas
        renderer._draw_slug_boss_crown(40, 40, renderer.prop_cache)
        assert canvas.get_at((62, 56))[:3] != (14, 10, 20)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_slug_boss_music_tracks_exist_verify_and_registered():
    """Verify slug_boss_phase1.ogg and slug_boss_phase2.ogg exist, decode cleanly (~14-16s), and are registered."""
    p1_path = os.path.join("assets", "audio", "music", constants.SLUG_BOSS_PHASE1_MUSIC)
    p2_path = os.path.join("assets", "audio", "music", constants.SLUG_BOSS_PHASE2_MUSIC)
    assert os.path.exists(p1_path), f"Missing Phase 1 boss track: {p1_path}"
    assert os.path.exists(p2_path), f"Missing Phase 2 boss track: {p2_path}"

    p1_len = generate_sfx.verify_ogg(p1_path)
    p2_len = generate_sfx.verify_ogg(p2_path)
    assert 13.5 <= p1_len <= 16.5, f"Unexpected Phase 1 length: {p1_len:.2f}s"
    assert 13.5 <= p2_len <= 16.5, f"Unexpected Phase 2 length: {p2_len:.2f}s"

    assert constants.SLUG_BOSS_PHASE1_MUSIC in constants.BOSS_COMBAT_TRACKS
    assert constants.SLUG_BOSS_PHASE2_MUSIC in constants.BOSS_COMBAT_TRACKS
    assert generate_sfx.find_missing_sfx(".") == {}


def test_slug_boss_phase2_transition_music_switch_10_slug_summon_and_client_guard():
    """Verify Phase 1 -> Phase 2 music switch, 10 walkable Act-scaled SlugEnemy summons once, and CLIENT guard."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
        # Arena with outer walls and interior wall pillars near boss to verify walkable spawn snapping
        prototype = [
            "################",
            "#..............#",
            "#..............#",
            "#.....##.......#",
            "#..............#",
            "#..............#",
            "#.........##...#",
            "#..............#",
            "#..............#",
            "#..............#",
            "#..............#",
            "################",
        ]
        state.world = World("swamp_mire")
        state.world.load_from_prototype(prototype)
        state.in_sanctuary = False
        state.current_act = 3
        state.player.x = 6.0 * constants.TILE_SIZE
        state.player.y = 5.0 * constants.TILE_SIZE

        boss = SlugBoss(7.0 * constants.TILE_SIZE, 4.0 * constants.TILE_SIZE)
        boss.network_id = 9000
        state.enemies = [boss]
        state.world.enemies = list(state.enemies)

        # 1. Above 50% HP -> Phase 1, plays slug_boss_phase1.ogg, no minions yet
        assert boss.phase == 1
        assert boss.minions_summoned is False
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.SLUG_BOSS_PHASE1_MUSIC

        boss.update(0.05, state)
        assert boss.phase == 1
        assert len(state.enemies) == 1

        # 2. Drop HP to <= 50% -> transitions to Phase 2, plays roar SFX, spawns 10 walkable Act-scaled SlugEnemies
        boss.hp = boss.max_hp * constants.SLUG_BOSS_PHASE2_HP_RATIO
        boss.update(0.05, state)
        assert boss.phase == 2
        assert boss.minions_summoned is True
        assert played_sfx.count(constants.SLUG_BOSS_SLIME_SFX) == 1

        minions = [e for e in state.enemies if isinstance(e, SlugEnemy)]
        assert len(minions) == constants.SLUG_BOSS_MINION_COUNT == 10
        assert state.world.enemies == state.enemies
        assert [m.network_id for m in minions] == list(range(9001, 9011))

        # Verify Act 3 scaling and walkable floor placement (zero wall overlap)
        sat3 = constants.get_act_saturation(3)
        base_slug = SlugEnemy(0, 0)
        for m in minions:
            assert m.max_hp == pytest.approx(base_slug.max_hp * sat3["hp_multiplier"])
            assert m.damage == pytest.approx(base_slug.damage * sat3["damage_multiplier"])
            assert m.speed == pytest.approx(base_slug.speed * sat3["speed_multiplier"])
            assert m.is_empowered is True
            tx0 = int(m.x // constants.TILE_SIZE)
            ty0 = int(m.y // constants.TILE_SIZE)
            tx1 = int((m.x + m.width - 1e-4) // constants.TILE_SIZE)
            ty1 = int((m.y + m.height - 1e-4) // constants.TILE_SIZE)
            for ty in range(ty0, ty1 + 1):
                for tx in range(tx0, tx1 + 1):
                    assert state.world.grid[ty][tx] != constants.TILE_WALL

        # 3. Subsequent updates must NOT summon a second wave
        boss.update(0.05, state)
        assert len([e for e in state.enemies if isinstance(e, SlugEnemy)]) == 10

        # 4. Audio track switches cleanly to Phase 2 Mega Man chiptune theme
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.SLUG_BOSS_PHASE2_MUSIC

        # 5. Renderer draws the Phase 2 magenta/gold surge aura around SlugBoss
        canvas = pygame.Surface((260, 260))
        canvas.fill((12, 10, 18))
        renderer = Renderer(canvas)
        rect = pygame.Rect(74, 74, constants.SLUG_BOSS_SIZE, constants.SLUG_BOSS_SIZE)
        renderer._draw_slug_boss(boss, rect, {"facing": (1.0, 0.0), "base": "IDLE", "anim_timer": 0.4})
        # Check pixel just outside the 112x112 sprite boundary where the surge aura glows
        aura_px = canvas.get_at((74 - 6, 74 + 56))[:3]
        assert aura_px != (12, 10, 18), "Phase 2 SlugBoss must render a magenta/gold surge aura"

        # 6. On CLIENT, <= 50% HP sets phase == 2 and minions_summoned == True without spawning local minions
        client_boss = SlugBoss(7.0 * constants.TILE_SIZE, 4.0 * constants.TILE_SIZE)
        client_boss.hp = client_boss.max_hp * 0.45
        state.network_manager.network_mode = "CLIENT"
        state.enemies = [client_boss]
        client_boss.update(0.05, state)
        assert client_boss.phase == 2
        assert client_boss.minions_summoned is True
        assert state.enemies == [client_boss]
    finally:
        state.shutdown_save_worker(timeout=1.0)
