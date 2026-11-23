"""
Unit tests for Batch 15 — Lore-Tied Boss Summoning Ritual (The Ink-Unsealing Rite):
1. boss_summon.ogg procedural SFX synthesis, preset/recipe parity, and Ink-Unsealing lore entry.
2. Black-from-center grey circle, 220+ shrinking typographic glyph squares, and per-boss palettes
   (SlugBoss purple/violet, RimecrestArbiterBoss cyan, MeadowCensorBoss gold/amethyst, empowered crimson).
3. Delayed boss materialization (1.55s), invulnerability/AI freeze during emergence (1.55s..2.35s),
   weather lock retention, and delayed boss music drop right at 2.35s completion.
4. Dormant map-placed Miniboss/FinalAuthor proximity trigger (360px), hostile-lock exemption,
   renderer smoke test (ground circle + rising glyph squares + emergence veil), and lifecycle cleanup.
"""
# pylint: disable=no-member,protected-access,duplicate-code,too-many-locals,too-many-statements
import os
from types import SimpleNamespace

import pygame
import pytest

import constants
import generate_sfx
from engine.enemy import (
    FinalAuthor,
    MeadowCensorBoss,
    Miniboss,
    NightBoss,
    RimecrestArbiterBoss,
    SlugBoss,
)
from engine.game_state import GameState
from engine.particles import BossSummonManager, resolve_boss_summon_palette
from engine.player import PlayerStateEnum
from engine.stats import StatisticsTracker
from engine.world import LevelLoader, Respite, World
from rendering.renderer import Renderer


def _make_state(tmp_path):
    """Create an offline GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_boss_summon_sfx_asset_and_lore_entry():
    """Verify boss_summon.ogg exists, loads cleanly (~2.2s), and Ink-Unsealing lore is registered."""
    assert "boss_summon" in generate_sfx.PRESETS
    assert "boss_summon.ogg" in generate_sfx.SOUND_RECIPES
    assert generate_sfx.find_missing_sfx(".") == {}

    sfx_path = os.path.join("assets", "audio", "sfx", "boss_summon.ogg")
    assert os.path.isfile(sfx_path)
    length = generate_sfx.verify_ogg(sfx_path)
    assert 1.8 <= length <= 2.6

    lore = constants.DIALOGUE_MANIFEST["lore_fragments"].get("ink_unsealing_rite", "")
    assert "Ink-Unsealing Rite" in lore
    assert "grey vellum" in lore.lower()
    assert "squares" in lore.lower()


def test_boss_summon_ritual_black_circle_shrinking_glyph_squares_and_palettes():
    """Verify 220+ shrinking glyph squares, expanding black center circle, and per-boss color palettes."""
    slug_boss = SlugBoss(240.0, 240.0)
    rime_boss = RimecrestArbiterBoss(240.0, 240.0)
    meadow_boss = MeadowCensorBoss(240.0, 240.0)
    emp_boss = NightBoss(240.0, 240.0)
    emp_boss.is_empowered = True
    std_boss = NightBoss(240.0, 240.0)

    slug_pal = resolve_boss_summon_palette(slug_boss)
    assert any(r > 110 and b > 170 and g < 100 for r, g, b in slug_pal), "SlugBoss needs purple/violet squares"
    rime_pal = resolve_boss_summon_palette(rime_boss)
    assert any(b > 210 and g > 170 and r < 130 for r, g, b in rime_pal), "Rimecrest needs glacial cyan squares"
    meadow_pal = resolve_boss_summon_palette(meadow_boss)
    assert any(r > 210 and g > 170 and b < 110 for r, g, b in meadow_pal), "MeadowCensor needs gold squares"
    emp_pal = resolve_boss_summon_palette(emp_boss)
    assert any(r > 200 and g < 80 for r, g, b in emp_pal), "Empowered bosses need crimson squares"
    std_pal = resolve_boss_summon_palette(std_boss)
    assert all(abs(r - g) <= 10 and abs(g - b) <= 10 for r, g, b in std_pal), "Default bosses use ash/grey squares"

    ritual = BossSummonManager.create_ritual(slug_boss, seed=42)
    assert len(ritual["squares"]) >= 220
    assert all(sq["glyph"] in constants.GLYPH_SPLATTER_POOL for sq in ritual["squares"])
    assert ritual["circle_radius"] == pytest.approx(constants.BOSS_SUMMON_CIRCLE_RADIUS)
    assert ritual["black_radius"] == pytest.approx(0.0)

    # Advance halfway through Stage 1 (~0.80s): black center expands, active squares rise & shrink
    still_active = BossSummonManager.update_ritual(ritual, 0.80)
    assert still_active is True
    assert ritual["stage"] == 1
    assert ritual["materialized"] is False
    expected_ratio = 0.80 / constants.BOSS_SUMMON_EMERGE_TIME
    assert ritual["black_radius"] == pytest.approx(constants.BOSS_SUMMON_CIRCLE_RADIUS * expected_ratio, abs=1e-2)

    active_sqs = [sq for sq in ritual["squares"] if sq["active"]]
    assert len(active_sqs) >= 40
    assert any(sq["y"] < sq["y0"] - 10.0 and sq["size"] < sq["initial_size"] for sq in active_sqs)
    assert all(
        constants.BOSS_SUMMON_SQUARE_MIN_SIZE <= sq["size"] <= constants.BOSS_SUMMON_SQUARE_MAX_SIZE
        for sq in active_sqs
    )

    # Advance into Stage 2 (1.95s): boss materializes and circle shrinks toward 0
    still_active = BossSummonManager.update_ritual(ritual, 1.15)
    assert still_active is True
    assert ritual["stage"] == 2
    assert ritual["materialized"] is True
    assert 0.0 < ritual["circle_radius"] < constants.BOSS_SUMMON_CIRCLE_RADIUS
    assert slug_boss.summoning_emerge_timer > 0.0

    # Complete ritual (>= 2.35s): circle closes and emerge timer clears
    still_active = BossSummonManager.update_ritual(ritual, 0.50)
    assert still_active is False
    assert ritual["circle_radius"] == pytest.approx(0.0)
    assert slug_boss.summoning_emerge_timer == pytest.approx(0.0)


def test_night_boss_summon_sfx_weather_lock_delayed_materialization_and_music_drop(tmp_path):
    """Verify boss_summon.ogg playback, BOSS_PHASE weather lock, invulnerability during emerge, and delayed music."""
    state = _make_state(tmp_path)
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )

    state.world = World("swamp_mire")
    state.world.load_from_prototype(["." * 16 for _ in range(16)])
    state.world.boss_coords_list = [{"x": 8, "y": 8}]
    state.in_sanctuary = False
    state.current_act = 1
    state.run_biomes["act1"] = "swamp_mire"
    state.player.x = 8 * constants.TILE_SIZE - 40.0
    state.player.y = 8 * constants.TILE_SIZE
    state.enemies = []
    state.weather_manager.set_boss_coords_list(state.world.boss_coords_list)
    state.weather_manager.bleed_state = "CLAMPED"

    # Tick 1 (0.05s): ritual begins, boss_summon.ogg plays, BOSS_PHASE locks, boss not yet in enemies, no boss music
    state._update_world_events(0.05)
    state._update_audio_track(0.05)
    assert constants.BOSS_SUMMON_SFX in played_sfx
    assert len(state.active_boss_summons) == 1
    assert state.weather_manager.bleed_state == "BOSS_PHASE"
    assert state.night_boss_spawned is True
    assert state.enemies == []
    assert state.player.active_track_name == "world_exploration.ogg"

    # Mid Stage 1 (1.00s total): weather remains locked in BOSS_PHASE (no premature dilution)
    state._update_world_events(0.95)
    state._update_audio_track(0.95)
    assert state.weather_manager.bleed_state == "BOSS_PHASE"
    assert state.enemies == []
    assert state.player.active_track_name == "world_exploration.ogg"

    # Stage 2 (1.70s total): SlugBoss materializes with summoning_emerge_timer > 0 (invulnerable, AI-frozen, music held)
    state._update_world_events(0.70)
    state._update_audio_track(0.70)
    assert len(state.enemies) == 1
    boss = state.enemies[0]
    assert isinstance(boss, SlugBoss)
    assert boss.summoning_emerge_timer > 0.0
    assert state.player.active_track_name == "world_exploration.ogg"

    # Player melee swing during emergence veil must skip / not damage the emerging boss
    full_hp = boss.hp
    boss.take_damage(50.0)
    assert boss.hp == full_hp
    state.player.x = boss.x - 24.0
    state.player.y = boss.y + 20.0
    state.player.facing = (1.0, 0.0)
    state.player.state = PlayerStateEnum.ATTACKING
    state.player.hit_entities_this_attack.clear()
    state.update_combat(0.016, False, {"move": (0, 0)}, None)
    assert boss.hp == full_hp

    # AI must stay frozen while emerging
    bx0, by0 = boss.x, boss.y
    boss.update(0.1, state)
    assert (boss.x, boss.y) == (bx0, by0)

    # Complete ritual (>= 2.35s): emerge timer clears, ritual ends, and boss music drops right as combat begins
    state._update_world_events(0.80)
    state._update_audio_track(0.016)
    assert not state.active_boss_summons
    assert boss.summoning_emerge_timer == pytest.approx(0.0)
    assert state.player.active_track_name == constants.SLUG_BOSS_PHASE1_MUSIC


def test_dormant_miniboss_and_final_author_proximity_trigger_and_renderer_smoke(tmp_path):
    """Verify map-placed Miniboss/FinalAuthor stay dormant until 360px proximity, then summon & render cleanly."""
    state = _make_state(tmp_path)
    played_sfx = []
    state.audio_manager = SimpleNamespace(
        play_sfx=lambda name, **kw: played_sfx.append(name),
        update_enemy_sounds=lambda _s: None,
        update_rain_audio=lambda *_a, **_k: None,
    )

    proto = [
        "####################",
        "#R.................#",
        "#................E.#",
        "#..................#",
        "#..................#",
        "#...............!..#",
        "####################",
    ]
    grid, interactables, warp_tiles, _p_start, enemies = LevelLoader.parse_map(proto, map_name="summon_proto")
    state.world = World("summon_proto")
    state.world.grid = grid
    state.world.interactables = interactables
    state.world.warp_tiles = warp_tiles
    state.world.enemies = enemies
    state.enemies = list(enemies)
    state.in_sanctuary = False

    miniboss = next(e for e in state.enemies if isinstance(e, Miniboss))
    author = next(e for e in state.enemies if isinstance(e, FinalAuthor))
    assert miniboss.dormant_boss_summon is True
    assert author.dormant_boss_summon is True

    # Place player near Respite at (1, 1) — far (> 360px) from dormant bosses
    respite = next(obj for obj in state.world.interactables if isinstance(obj, Respite))
    state.player.x = 60.0
    state.player.y = 60.0
    assert Respite._has_blocking_hostiles(state) is False
    assert state.is_interactable_blocked_by_hostiles(respite) is False

    # Dormant bosses are hidden by draw_actor_ghost
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    screen.fill((30, 30, 30))
    renderer.draw_actor_ghost(miniboss, 0.0, 0.0, state)
    assert screen.get_at((int(miniboss.x + 16), int(miniboss.y + 16)))[:3] == (30, 30, 30)

    # Walk within BOSS_SUMMON_TRIGGER_RADIUS (360px) of Miniboss -> triggers Ink-Unsealing ritual
    state.player.x = miniboss.x - 160.0
    state.player.y = miniboss.y
    state._update_world_events(0.45)
    assert len(state.active_boss_summons) >= 1
    assert constants.BOSS_SUMMON_SFX in played_sfx

    # Smoke-render Stage 1 (ground circle + rising glyph squares) and Stage 2 (emergence veil)
    state.camera.instant_center(miniboss.get_center())
    ox, oy = state.camera.get_offset()
    screen.fill((30, 30, 30))
    renderer.draw_boss_summon_rituals(state, ox, oy)
    center_px = screen.get_at((int(miniboss.get_center()[0] - ox), int(miniboss.get_center()[1] - oy)))[:3]
    assert center_px != (30, 30, 30), "Ground summoning circle should draw dark ink at center"

    state._update_world_events(1.30)  # Into Stage 2 (1.75s)
    renderer.draw_boss_summon_rituals(state, ox, oy)
    renderer.render(state)

    # Lifecycle cleanup: on_enter_sanctuary, reset_to_new_game, and deallocate clear active_boss_summons
    state.on_enter_sanctuary()
    assert not state.active_boss_summons
    state.start_boss_summon(Miniboss(120.0, 120.0))
    assert len(state.active_boss_summons) == 1
    state.reset_to_new_game()
    assert not state.active_boss_summons
    state.start_boss_summon(Miniboss(120.0, 120.0))
    state.deallocate()
    assert not state.active_boss_summons
