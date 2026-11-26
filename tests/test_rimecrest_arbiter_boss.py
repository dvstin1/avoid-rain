# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit tests for Batch 6 Pass 2 — RimecrestArbiterBoss (Frozen Peaks Night Boss):
1. Procedural sprites, frost/ice SFX, two-phase glacial music & Renderer preloading.
2. Frozen Peaks Night Boss spawn routing, ENEMY_REGISTRY, and simulation/Respite exemptions.
3. Frost Breath cone exposure -> Ice Block encasement, full damage vulnerability while frozen,
   edge-triggered 3-Dash breakout across stages 0/1/2 + ICE_CRACK_SFX / ICE_SHATTER_SFX + 5.0s fading IceRubble,
   and Sanctuary/respawn frost state reset.
4. Halberd cleave (+0.35 exposure) & mode alternation, Phase 2 transition + 3 walkable minions,
   and dynamic Phase 1 -> Phase 2 music switching (including CLIENT HP-ratio parity).
5. Non-interactive persistent RimecrestHalberd floor prop, 2-weapon scatter & ChoiceOfFates on death.
"""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
import generate_sfx
from engine.actor import ActorState
from engine.enemy import (
    ENEMY_REGISTRY,
    FlutterEnemy,
    RimecrestArbiterBoss,
    SmearEnemy,
)
from engine.game_state import GameState
from engine.loot import ChoiceOfFates
from engine.player import PlayerStateEnum
from engine.world import Respite, RimecrestHalberd, WeaponPickup, World
from generate_assets import (
    generate_frozen_ice_block_stage,
    generate_ice_rubble_pile,
    generate_rimecrest_arbiter_boss,
    generate_rimecrest_halberd,
)
from rendering.renderer import Renderer


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


class _RecordingAudio:
    """Minimal mock audio manager capturing played SFX filenames."""

    def __init__(self):
        self.sfx_played = []

    def play_sfx(self, filename, **_kwargs):
        """Record an SFX playback call."""
        self.sfx_played.append(filename)


def test_rimecrest_assets_sfx_music_and_preload():
    """Verify all sprites, SFX, and glacial boss music tracks exist, load cleanly, and preload in Renderer."""
    sprite_specs = (
        ("rimecrest_arbiter_boss.png", "RimecrestArbiterBoss", (104, 104)),
        ("rimecrest_halberd.png", "RimecrestHalberd", (48, 56)),
        ("frozen_ice_block_0.png", "FrozenIceBlock0", (64, 64)),
        ("frozen_ice_block_1.png", "FrozenIceBlock1", (64, 64)),
        ("frozen_ice_block_2.png", "FrozenIceBlock2", (64, 64)),
        ("ice_rubble_pile.png", "IceRubblePile", (48, 36)),
    )
    for fname, _key, expected_size in sprite_specs:
        path = os.path.join("assets", "graphics", fname)
        assert os.path.exists(path), f"Missing generated sprite: {path}"
        surf = pygame.image.load(path)
        assert surf.get_size() == expected_size

    assert generate_rimecrest_arbiter_boss().get_size() == (104, 104)
    assert generate_rimecrest_halberd().get_size() == (48, 56)
    for stage in (0, 1, 2):
        blk = generate_frozen_ice_block_stage(stage)
        assert blk.get_size() == (64, 64) and blk.get_at((0, 0)).a == 0
    rubble = generate_ice_rubble_pile()
    assert rubble.get_size() == (48, 36) and rubble.get_at((0, 0)).a == 0

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    for _fname, cache_key, expected_size in sprite_specs:
        assert cache_key in renderer.prop_cache
        assert renderer.prop_cache[cache_key].get_size() == expected_size

    for sfx_name in (constants.FROST_BREATH_SFX, constants.ICE_CRACK_SFX, constants.ICE_SHATTER_SFX):
        sfx_path = os.path.join("assets", "audio", "sfx", sfx_name)
        assert os.path.exists(sfx_path), f"Missing generated SFX: {sfx_path}"
        assert os.path.getsize(sfx_path) > 512

    for track_name in (constants.RIMECREST_ARBITER_PHASE1_MUSIC, constants.RIMECREST_ARBITER_PHASE2_MUSIC):
        track_path = os.path.join("assets", "audio", "music", track_name)
        assert os.path.exists(track_path), f"Missing generated music track: {track_path}"
        assert os.path.getsize(track_path) > 4096
        assert track_name in constants.BOSS_COMBAT_TRACKS

    assert generate_sfx.find_missing_sfx(".") == {}


def test_frozen_peaks_spawns_rimecrest_arbiter_and_exemptions():
    """Verify frozen_peaks spawns RimecrestArbiterBoss on CLAMPED circle and preserves it across simulation/Respite."""
    assert ENEMY_REGISTRY["RimecrestArbiterBoss"] is RimecrestArbiterBoss

    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("frozen_peaks")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.world.boss_coords_list = [{"x": 8, "y": 8}]
        state.weather_manager.set_boss_coords_list([{"x": 8, "y": 8}])
        state.weather_manager.bleed_state = "CLAMPED"
        state.weather_manager.boss_spawn_ready = True
        state.enemies = []
        state.player.x = 8 * constants.TILE_SIZE
        state.player.y = 8 * constants.TILE_SIZE

        state._update_world_events(0.016)
        state._update_world_events(constants.BOSS_SUMMON_DURATION)
        bosses = [e for e in state.enemies if isinstance(e, RimecrestArbiterBoss)]
        assert len(bosses) == 1
        boss = bosses[0]
        assert boss.name == "Night Boss"
        assert boss.is_rimecrest_arbiter is True
        assert (boss.width, boss.height) == (constants.RIMECREST_ARBITER_SIZE, constants.RIMECREST_ARBITER_SIZE)

        # Exempt from active-simulation sleep even when active_respite is open
        state.active_respite = Respite((120, 120), (40, 40))
        assert boss.is_within_active_simulation(state) is True

        # Preserved alive across Respite.execute_rest()
        respite = state.active_respite
        respite.execute_rest(state)
        assert boss in state.enemies
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_frost_breath_encasement_vulnerability_3_dash_breakout_and_ice_rubble():
    """Verify Frost Breath -> Ice Block encasement, full vulnerability, 3-Dash breakout, SFX, and 5.0s IceRubble."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    audio = _RecordingAudio()
    state.audio_manager = audio
    try:
        state.world = World("frozen_peaks")
        state.world.load_from_prototype(["." * 16 for _ in range(16)])
        state.in_sanctuary = False
        state.player.x, state.player.y = 320.0, 240.0
        state.player.hp = state.player.max_hp
        state.camera.instant_center(state.player.get_center())

        boss = RimecrestArbiterBoss(200.0, 210.0)
        boss.facing = (1.0, 0.0)
        boss.attack_mode = "FROST_BREATH"
        boss.state = ActorState.STRIKE
        boss.combat_timer = 1.5
        state.enemies = [boss]

        # Hit 1 via Frost Breath applies 0.5 chill once per breath attack and starts the 10.0s window
        boss._update_strike(0.1, state)
        boss._update_strike(0.1, state)
        assert constants.FROST_BREATH_SFX in audio.sfx_played
        assert state.player.frost_exposure == pytest.approx(constants.RIMECREST_CHILL_HIT_AMOUNT)
        assert state.player.frost_window_timer == pytest.approx(constants.RIMECREST_FREEZE_WINDOW)
        assert state.player.frozen_hits_remaining == 0
        assert state.player.hp < state.player.max_hp  # Light chill damage applied

        # Complete breath strike so per-attack hit flag resets, then Hit 2 within 10s freezes the player
        boss._update_strike(1.5, state)
        assert boss.state != ActorState.STRIKE
        boss.attack_mode = "FROST_BREATH"
        boss.state = ActorState.STRIKE
        boss.combat_timer = 1.5
        boss._update_strike(0.1, state)
        assert state.player.frozen_hits_remaining == constants.FROZEN_ICE_BLOCK_HITS
        assert state.player.frost_exposure == 0.0
        assert state.player.frost_window_timer == 0.0
        assert state.player.just_cracked_ice is True

        # Encased player cannot move, attack, block, or dash away, AND remains fully vulnerable to consecutive hits
        start_x, start_y = state.player.x, state.player.y
        hp_before_hit1 = state.player.hp
        state.player.take_damage(10.0, bypass_stagger=False)
        hp_after_hit1 = state.player.hp
        assert hp_after_hit1 < hp_before_hit1
        assert state.player.state == PlayerStateEnum.IDLE

        # Second immediate discrete hit must NOT be blocked by stagger i-frames!
        state.player.take_damage(10.0, bypass_stagger=False)
        assert state.player.hp < hp_after_hit1
        assert state.player.state == PlayerStateEnum.IDLE

        # Render frozen stage 0 + HUD FROZEN badge cleanly
        renderer.render(state)

        # Press 1 (held across 2 frames): edge-triggered -> only 1 decrement (3 -> 2), plays ICE_CRACK_SFX
        base_actions = {"move": (1.0, 0.0), "attack": True, "block": True, "dash": True, "flask": False, "swap": False}
        state._update_player_lifecycle(0.05, base_actions, True, audio)
        assert state.player.frozen_hits_remaining == 2
        assert (state.player.x, state.player.y) == (start_x, start_y)
        assert constants.ICE_CRACK_SFX in audio.sfx_played
        assert "player_dash.ogg" not in audio.sfx_played

        # Holding dash on next frame must NOT decrement again
        state._update_player_lifecycle(0.05, base_actions, False, audio)
        assert state.player.frozen_hits_remaining == 2
        renderer.render(state)  # stage 1

        # Release dash, then Press 2 (2 -> 1)
        state._update_player_lifecycle(0.05, {**base_actions, "dash": False}, False, audio)
        state._update_player_lifecycle(0.05, {**base_actions, "dash": True}, False, audio)
        assert state.player.frozen_hits_remaining == 1
        renderer.render(state)  # stage 2

        # Release dash, then Press 3 (1 -> 0): shatters free, plays ICE_SHATTER_SFX, spawns 5.0s IceRubble
        state._update_player_lifecycle(0.05, {**base_actions, "dash": False}, False, audio)
        state._update_player_lifecycle(0.05, {**base_actions, "dash": True}, False, audio)
        assert state.player.frozen_hits_remaining == 0
        assert constants.ICE_SHATTER_SFX in audio.sfx_played
        assert "player_dash.ogg" not in audio.sfx_played

        rubble_entries = [d for d in state.world_debris if d.get("name") == "IceRubble"]
        assert len(rubble_entries) == 1
        assert rubble_entries[0]["time"] == pytest.approx(constants.ICE_RUBBLE_DURATION)
        assert rubble_entries[0]["max_time"] == pytest.approx(constants.ICE_RUBBLE_DURATION)

        # Advance 2.5s -> rubble still present and renders faded alpha; advance 2.6s more -> expires
        state._update_shared_world(2.5)
        assert any(d.get("name") == "IceRubble" for d in state.world_debris)
        renderer._fx_surface_cache.clear()
        renderer.render(state)
        assert any(k[0] == "ice_rubble_fade" for k in renderer._fx_surface_cache)

        state._update_shared_world(2.6)
        assert not any(d.get("name") == "IceRubble" for d in state.world_debris)

        # Chill mark holds steady at 0.5 across the 10.0s window, clears after 10.0s, and resets in Sanctuary
        idle_actions = {**base_actions, "move": (0.0, 0.0), "dash": False, "attack": False, "block": False}
        state.player.apply_frost_exposure(constants.RIMECREST_CHILL_HIT_AMOUNT)
        assert state.player.frost_exposure == pytest.approx(0.5)
        assert state.player.frost_window_timer == pytest.approx(constants.RIMECREST_FREEZE_WINDOW)
        state._update_player_lifecycle(4.0, idle_actions, False, audio)
        assert state.player.frost_exposure == pytest.approx(0.5)
        assert state.player.frost_window_timer == pytest.approx(6.0)
        state._update_player_lifecycle(6.1, idle_actions, False, audio)
        assert state.player.frost_exposure == 0.0
        assert state.player.frost_window_timer == 0.0

        state.player.apply_frost_exposure(1.0)
        assert state.player.frozen_hits_remaining == 3
        state.on_enter_sanctuary()
        assert state.player.frozen_hits_remaining == 0
        assert state.player.frost_exposure == 0.0
        assert state.player.frost_window_timer == 0.0
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_rimecrest_phase2_minions_music_and_persistent_halberd_death():
    """Verify Phase 2 3-minion summon, Phase 1->2 music switching, halberd cleave exposure, and death drops."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    audio = _RecordingAudio()
    state.audio_manager = audio
    try:
        state.world = World("frozen_peaks")
        state.world.load_from_prototype(["." * 18 for _ in range(18)])
        state.in_sanctuary = False
        state.player.x, state.player.y = 320.0, 320.0
        state.camera.instant_center(state.player.get_center())

        boss = RimecrestArbiterBoss(280.0, 280.0)
        boss.network_id = 9001
        state.enemies = [boss]

        # Phase 1 boss music
        state._update_audio_track(0.1)
        assert state.player.active_track_name == constants.RIMECREST_ARBITER_PHASE1_MUSIC

        # Halberd cleave deals damage + 0.35 frost exposure and alternates to FROST_BREATH
        boss.attack_mode = "HALBERD"
        boss.facing = (1.0, 0.0)
        boss.state = ActorState.STRIKE
        boss.combat_timer = 0.05
        state.player.x, state.player.y = 360.0, 320.0
        boss._update_strike(0.1, state)
        assert boss.attack_mode == "FROST_BREATH"
        assert state.player.frost_exposure == pytest.approx(constants.RIMECREST_ARBITER_HALBERD_EXPOSURE)

        # Drop boss to 50% HP -> triggers Phase 2, plays FROST_BREATH_SFX, summons 3 walkable vanguard minions
        boss.hp = boss.max_hp * constants.RIMECREST_ARBITER_PHASE2_HP_RATIO
        boss.update(0.05, state)
        assert boss.phase == 2
        assert boss.minions_summoned is True
        assert constants.FROST_BREATH_SFX in audio.sfx_played

        summoned = [e for e in state.enemies if e is not boss]
        assert len(summoned) == constants.RIMECREST_ARBITER_MINION_COUNT
        assert all(isinstance(m, (SmearEnemy, FlutterEnemy)) for m in summoned)
        net_ids = [m.network_id for m in summoned]
        assert net_ids == [9002, 9003, 9004]
        assert len(state.world._enemies) == len(state.enemies)

        # Phase 2 music (also verify CLIENT parity when phase attribute is still 1 but hp <= 50%)
        boss.phase = 1
        state._update_audio_track(0.1)
        assert state.player.active_track_name == constants.RIMECREST_ARBITER_PHASE2_MUSIC
        boss.phase = 2

        # Render boss in Phase 2 + FROST_BREATH strike (and confirm draw_boss_weapon skips it)
        boss.attack_mode = "FROST_BREATH"
        boss.state = ActorState.STRIKE
        renderer.render(state)
        renderer.draw_boss_weapon(boss, 0.0, 0.0)

        # Death plants non-interactive RimecrestHalberd, scatters 2 distinct weapons, and drops ChoiceOfFates
        boss.on_death(state)
        halberds = [o for o in state.world.interactables if isinstance(o, RimecrestHalberd)]
        assert len(halberds) == 1
        assert halberds[0].is_interactive is False
        assert halberds[0].is_solid is False
        assert halberds[0].execute_interaction(state) is None

        weapons = [o for o in state.world.interactables if isinstance(o, WeaponPickup)]
        assert len(weapons) == 2
        assert weapons[0].weapon_data["name"] != weapons[1].weapon_data["name"]
        assert any(isinstance(i, ChoiceOfFates) for i in state.loot)

        # Render floor RimecrestHalberd prop cleanly
        state.enemies = []
        renderer.render(state)
    finally:
        state.shutdown_save_worker(timeout=1.0)
