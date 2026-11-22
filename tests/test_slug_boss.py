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
from engine.enemy import NightBoss, SlugBoss
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
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)

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
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)

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
