"""
Unit tests for Batch 5 Pass 2: Pastoral Valley Night Boss (MeadowCensorBoss — The Meadow Censor),
hooked scythe pull-cleave, boiling plum tar geysers, Phase 2 culling whistle + 4 Punctuation Wolves,
persistent planted scythe prop, and two-phase folk-dirge / tarantella boss themes.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access
# pylint: disable=too-many-locals,too-many-statements

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
from engine.enemy import ENEMY_REGISTRY, MeadowCensorBoss, NightBoss, PunctuationWolfEnemy
from engine.game_state import GameState
from engine.loot import ChoiceOfFates
from engine.world import MeadowCensorScythe, WeaponPickup, World
from generate_assets import generate_meadow_censor_boss, generate_meadow_censor_scythe
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_meadow_censor_assets_sfx_and_two_phase_music_exist_and_preload():
    """Verify Meadow Censor sprites, whistle SFX, and two-phase boss music exist, decode cleanly, and preload."""
    boss_path = os.path.join("assets", "graphics", "meadow_censor_boss.png")
    scythe_path = os.path.join("assets", "graphics", "meadow_censor_scythe.png")
    sfx_path = os.path.join("assets", "audio", "sfx", constants.MEADOW_CENSOR_WHISTLE_SFX)
    p1_path = os.path.join("assets", "audio", "music", constants.MEADOW_CENSOR_PHASE1_MUSIC)
    p2_path = os.path.join("assets", "audio", "music", constants.MEADOW_CENSOR_PHASE2_MUSIC)

    for path in (boss_path, scythe_path, sfx_path, p1_path, p2_path):
        assert os.path.exists(path), f"Missing generated Meadow Censor asset: {path}"

    assert pygame.image.load(boss_path).get_size() == (constants.MEADOW_CENSOR_SIZE, constants.MEADOW_CENSOR_SIZE)
    assert pygame.image.load(scythe_path).get_size() == (
        constants.MEADOW_CENSOR_SCYTHE_WIDTH,
        constants.MEADOW_CENSOR_SCYTHE_HEIGHT,
    )

    gen_boss = generate_meadow_censor_boss()
    gen_scythe = generate_meadow_censor_scythe()
    assert gen_boss.get_size() == (104, 104) and gen_boss.get_at((0, 0)).a == 0
    assert gen_scythe.get_size() == (48, 56) and gen_scythe.get_at((0, 0)).a == 0

    whistle_len = generate_sfx.verify_ogg(sfx_path)
    p1_len = generate_sfx.verify_ogg(p1_path)
    p2_len = generate_sfx.verify_ogg(p2_path)
    assert 0.35 <= whistle_len <= 0.60
    assert 13.5 <= p1_len <= 16.5
    assert 13.5 <= p2_len <= 16.5

    assert constants.MEADOW_CENSOR_PHASE1_MUSIC in constants.BOSS_COMBAT_TRACKS
    assert constants.MEADOW_CENSOR_PHASE2_MUSIC in constants.BOSS_COMBAT_TRACKS
    assert generate_sfx.find_missing_sfx(".") == {}
    assert ENEMY_REGISTRY.get("MeadowCensorBoss") is MeadowCensorBoss

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    assert "MeadowCensorBoss" in renderer.prop_cache
    assert renderer.prop_cache["MeadowCensorBoss"].get_size() == (104, 104)
    assert "MeadowCensorScythe" in renderer.prop_cache
    assert renderer.prop_cache["MeadowCensorScythe"].get_size() == (48, 56)


def test_meadow_censor_spawns_as_pastoral_valley_night_boss():
    """Verify CLAMPED boss spawn creates MeadowCensorBoss on pastoral_valley and NightBoss on windy_ridge."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("pastoral_valley")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.world.boss_coords_list = [{"x": 8, "y": 8}]
        state.current_act = 1
        state.run_biomes["act1"] = "pastoral_valley"
        state.enemies = []
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)

        assert len(state.enemies) == 1
        boss = state.enemies[0]
        assert isinstance(boss, MeadowCensorBoss)
        assert isinstance(boss, NightBoss)
        assert boss.name == "Night Boss"
        assert boss.is_meadow_censor is True
        assert (boss.width, boss.height) == (104, 104)
        assert boss.max_hp == pytest.approx(constants.MEADOW_CENSOR_HP)

        # Windy Ridge still spawns standard NightBoss
        state.world = World("windy_ridge")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.world.boss_coords_list = [{"x": 8, "y": 8}]
        state.run_biomes["act1"] = "windy_ridge"
        state.enemies = []
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.current_boss_idx = 0
        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)

        assert len(state.enemies) == 1
        assert isinstance(state.enemies[0], NightBoss)
        assert not isinstance(state.enemies[0], MeadowCensorBoss)
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_meadow_censor_hooked_scythe_pull_cleave_and_tar_geysers():
    """Verify SCYTHE STRIKE damages & pulls player inward (respecting walls), then alternates to TAR_GEYSER."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
        state.world = World("pastoral_valley")
        state.world.load_from_prototype(["." * 20 for _ in range(20)])
        state.in_sanctuary = False

        # Place player within the wide 144x144 scythe cleave rect, offset 120px to the right of boss center
        boss = MeadowCensorBoss(200.0, 200.0)
        boss.facing = (1.0, 0.0)
        boss.attack_mode = "SCYTHE"
        boss.state = ActorState.WIND_UP
        boss.combat_timer = 0.02
        state.enemies = [boss]

        bcx, bcy = boss.get_center()
        state.player.x = bcx + 88.0
        state.player.y = bcy - state.player.height / 2.0
        start_dist = math.hypot(state.player.get_center()[0] - bcx, state.player.get_center()[1] - bcy)
        initial_hp = float(state.player.hp)

        for _ in range(20):
            boss.update(0.04, state)
            if boss.state == ActorState.RECOVERY:
                break

        end_dist = math.hypot(state.player.get_center()[0] - bcx, state.player.get_center()[1] - bcy)
        assert state.player.hp < initial_hp, "Hooked scythe cleave must damage player"
        assert end_dist < start_dist - 10.0, "Hooked scythe cleave must pull player inward toward boss"
        assert boss.attack_mode == "TAR_GEYSER", "MeadowCensorBoss should alternate from SCYTHE to TAR_GEYSER"

        # Now trigger TAR_GEYSER STRIKE -> halts boss, plays whistle SFX, spawns 3 style='tar' pools
        boss.state = ActorState.WIND_UP
        boss.combat_timer = 0.02
        pos_before = (boss.x, boss.y)
        boss.update(0.05, state)

        assert boss.state == ActorState.STRIKE
        assert (boss.vx, boss.vy) == (0.0, 0.0)
        assert (boss.x, boss.y) == pos_before
        assert played_sfx.count(constants.MEADOW_CENSOR_WHISTLE_SFX) == 1
        assert len(state.slime_pools) == constants.MEADOW_CENSOR_TAR_POOL_COUNT
        assert all(p.get("style") == "tar" for p in state.slime_pools)

        # Standing in a boiling tar pool deals periodic damage
        tar0 = state.slime_pools[0]
        state.player.x = tar0["x"] - state.player.width / 2.0
        state.player.y = tar0["y"] - state.player.height / 2.0
        hp_before_tar = float(state.player.hp)
        state._update_slime_pools(0.05)
        assert state.player.hp < hp_before_tar
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_meadow_censor_phase2_whistle_4_wolves_music_switch_and_client_guard():
    """Verify <=50% HP triggers Phase 2 whistle, 4 walkable Act-scaled wolves once, music switch, and CLIENT guard."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )
    try:
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
        state.world = World("pastoral_valley")
        state.world.load_from_prototype(prototype)
        state.in_sanctuary = False
        state.current_act = 3
        state.player.x = 6.0 * constants.TILE_SIZE
        state.player.y = 5.0 * constants.TILE_SIZE

        boss = MeadowCensorBoss(7.0 * constants.TILE_SIZE, 4.0 * constants.TILE_SIZE)
        boss.network_id = 9000
        state.enemies = [boss]
        state.world.enemies = list(state.enemies)

        # 1. Phase 1 above 50% HP plays pastoral_boss_phase1.ogg
        assert boss.phase == 1
        assert boss.minions_summoned is False
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.MEADOW_CENSOR_PHASE1_MUSIC

        boss.update(0.05, state)
        assert boss.phase == 1
        assert len(state.enemies) == 1

        # 2. Drop HP to <= 50% -> Phase 2, plays whistle, summons 4 walkable Act-scaled PunctuationWolfEnemies
        boss.hp = boss.max_hp * constants.MEADOW_CENSOR_PHASE2_HP_RATIO
        boss.update(0.05, state)
        assert boss.phase == 2
        assert boss.minions_summoned is True
        assert played_sfx.count(constants.MEADOW_CENSOR_WHISTLE_SFX) == 1

        wolves = [e for e in state.enemies if isinstance(e, PunctuationWolfEnemy)]
        assert len(wolves) == constants.MEADOW_CENSOR_MINION_COUNT == 4
        assert state.world.enemies == state.enemies
        assert [w.network_id for w in wolves] == [9001, 9002, 9003, 9004]

        sat3 = constants.get_act_saturation(3)
        base_wolf = PunctuationWolfEnemy(0, 0)
        for wolf in wolves:
            assert wolf.max_hp == pytest.approx(base_wolf.max_hp * sat3["hp_multiplier"])
            assert wolf.damage == pytest.approx(base_wolf.damage * sat3["damage_multiplier"])
            assert wolf.speed == pytest.approx(base_wolf.speed * sat3["speed_multiplier"])
            assert wolf.is_empowered is True
            tx0 = int(wolf.x // constants.TILE_SIZE)
            ty0 = int(wolf.y // constants.TILE_SIZE)
            tx1 = int((wolf.x + wolf.width - 1e-4) // constants.TILE_SIZE)
            ty1 = int((wolf.y + wolf.height - 1e-4) // constants.TILE_SIZE)
            for ty in range(ty0, ty1 + 1):
                for tx in range(tx0, tx1 + 1):
                    assert state.world.grid[ty][tx] != constants.TILE_WALL

        # 3. Single-trigger: subsequent update must not summon a second pack
        boss.update(0.05, state)
        assert len([e for e in state.enemies if isinstance(e, PunctuationWolfEnemy)]) == 4

        # 4. Audio switches cleanly to Phase 2 tarantella theme
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.MEADOW_CENSOR_PHASE2_MUSIC

        # 5. CLIENT guard: <= 50% HP sets phase == 2 without spawning local wolves and still switches music
        client_boss = MeadowCensorBoss(7.0 * constants.TILE_SIZE, 4.0 * constants.TILE_SIZE)
        client_boss.hp = client_boss.max_hp * 0.45
        state.network_manager.network_mode = "CLIENT"
        state.enemies = [client_boss]
        state._update_audio_track(0.016)
        assert state.player.active_track_name == constants.MEADOW_CENSOR_PHASE2_MUSIC
        client_boss.update(0.05, state)
        assert client_boss.phase == 2
        assert client_boss.minions_summoned is True
        assert state.enemies == [client_boss]
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_meadow_censor_death_plants_scythe_and_renderer_draws_boss_aura_and_tar(monkeypatch):
    """Verify on_death plants non-interactive MeadowCensorScythe + weapons + ChoiceOfFates, and Renderer draws all."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("pastoral_valley")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.world.interactables = []
        state.loot = []
        state.player.x = 120.0
        state.player.y = 120.0
        state.camera.instant_center((260.0, 260.0))

        boss = MeadowCensorBoss(220.0, 220.0)
        boss.phase = 2
        boss.hp = boss.max_hp * 0.4
        boss.state = ActorState.STRIKE
        boss.attack_mode = "SCYTHE"
        boss.combat_timer = 0.2
        state.enemies = [boss]
        state.spawn_slime_pool(280.0, 280.0, style="tar")

        blade_calls = []
        monkeypatch.setattr(renderer, "_draw_tapered_blade", lambda *a, **k: blade_calls.append(a))

        # Verify MeadowCensorBoss never draws a generic straight tapered greatblade
        renderer.draw_actor_ghost(boss, 0, 0, state)
        renderer.draw_boss_weapon(boss, 0, 0)
        assert not blade_calls, "MeadowCensorBoss must not invoke generic straight greatblade rendering"

        # Full render draws boiling tar pools using dedicated meadow_censor_tar_pool cache key
        renderer.render(state)
        assert any(k[0] == "meadow_censor_tar_pool" for k in renderer._fx_surface_cache)

        # Phase 2 aura renders visible glow outside the 104x104 sprite boundary
        aura_canvas = pygame.Surface((260, 260))
        aura_canvas.fill((12, 10, 18))
        renderer.screen = aura_canvas
        rect = pygame.Rect(78, 78, constants.MEADOW_CENSOR_SIZE, constants.MEADOW_CENSOR_SIZE)
        renderer._draw_meadow_censor_boss(boss, rect, {"facing": (1.0, 0.0), "base": "IDLE", "anim_timer": 0.4})
        assert aura_canvas.get_at((78 - 6, 78 + 52))[:3] != (12, 10, 18)

        # Death plants non-interactive MeadowCensorScythe, scatters 2 distinct weapons, and drops ChoiceOfFates
        boss.on_death(state)
        scythes = [obj for obj in state.world.interactables if isinstance(obj, MeadowCensorScythe)]
        weapons = [obj for obj in state.world.interactables if isinstance(obj, WeaponPickup)]
        choices = [item for item in state.loot if isinstance(item, ChoiceOfFates)]
        assert len(scythes) == 1
        scythe = scythes[0]
        assert scythe.is_interactive is False
        assert scythe.is_solid is False
        assert scythe.execute_interaction(state) is None
        assert scythe not in state.world.get_nearby_interactables((scythe.x, scythe.y, 40, 40))
        assert len(weapons) == 2
        assert weapons[0].name != weapons[1].name
        assert len(choices) == 1

        # Direct planted scythe rendering produces visible pixels
        scythe_canvas = pygame.Surface((120, 120))
        scythe_canvas.fill((14, 10, 20))
        renderer.screen = scythe_canvas
        renderer._draw_meadow_censor_scythe(36, 32, renderer.prop_cache)
        assert scythe_canvas.get_at((60, 60))[:3] != (14, 10, 20)
    finally:
        state.shutdown_save_worker(timeout=1.0)
