# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit tests for Batch 4 Pass 1:
1. Warding rain damage balance (30% WARD_BUFF_RAIN_REDUCTION on active ward, no flat -5.0 or refresh on rain ticks).
2. 2-second enemy stuck / out-of-bounds nearest-floor recovery.
3. Steeper later-Act enemy difficulty curve (Acts 1-5 HP, damage, speed, and cooldown scaling end-to-end).
4. Biome & Biome-Boss Chronicle lore pools (all 7 biomes, crowned sword-pierced Slug Night Boss, ~15-20% faded entries).
"""
# pylint: disable=no-member,protected-access,duplicate-code,too-many-locals,unsubscriptable-object
import pytest
import pygame

import constants
from engine.enemy import NightBoss, SlugEnemy
from engine.game_state import GameState
from engine.player import Player, PlayerStateEnum
from engine.stats import StatisticsTracker
from engine.world import LoreFragment, Respite, World


def _make_state(tmp_path):
    """Create an offline GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_warding_rain_balance_no_flat_negation_immunity():
    """Verify rain DoT ticks do not trigger/refresh flat -5.0 negation and instead take 30% ward reduction."""
    player = Player(100, 100)
    player.hp = 60.0
    player.weapons = [
        {
            "name": "Iron-Nib Quill",
            "damage": 12,
            "modifiers": {"damage_negation_on_hit": 5.0},
        }
    ]
    player.active_weapon_idx = 0

    # 1. Rain tick (bypass_stagger=True) when negation_timer == 0 deals full tick and does NOT start negation_timer
    player.take_damage(0.05, bypass_stagger=True)
    assert player.hp == pytest.approx(59.95, abs=1e-4)
    assert player.negation_timer == 0.0

    # 2. Discrete combat hit (bypass_stagger=False) activates negation_timer = 3.0 and negation_amount = 5.0
    player.hp = 60.0
    player.take_damage(10.0, bypass_stagger=False)
    assert player.hp == pytest.approx(50.0, abs=1e-4)
    assert player.negation_timer == pytest.approx(3.0, abs=1e-4)
    assert player.negation_amount == pytest.approx(5.0, abs=1e-4)

    # 3. Subsequent discrete combat hit (bypass_stagger=False) subtracts flat 5.0 (12.0 - 5.0 = 7.0)
    player.state = PlayerStateEnum.IDLE
    player.stagger_timer = 0.0
    player.take_damage(12.0, bypass_stagger=False)
    assert player.hp == pytest.approx(43.0, abs=1e-4)

    # 4. Rain tick while WARD buff is active applies 30% fractional reduction (not flat -5.0)
    player.hp = 60.0
    player.state = PlayerStateEnum.IDLE
    player.negation_timer = 2.0
    player.take_damage(1.0, bypass_stagger=True)
    expected_ward_rain = 1.0 * (1.0 - constants.WARD_BUFF_RAIN_REDUCTION)
    assert player.hp == pytest.approx(60.0 - expected_ward_rain, abs=1e-4)
    assert player.negation_timer == pytest.approx(2.0, abs=1e-4)

    # 5. Rain tick while BOTH WARD buff and active BLOCKING stacks multiplicatively (0.70 * 0.80 = 0.56)
    player.hp = 60.0
    player.state = PlayerStateEnum.BLOCKING
    player.negation_timer = 2.0
    player.take_damage(10.0, bypass_stagger=True)
    expected_stacked = (
        10.0
        * (1.0 - constants.WARD_BUFF_RAIN_REDUCTION)
        * (1.0 - constants.WARDING_RAIN_DAMAGE_REDUCTION)
    )
    assert player.hp == pytest.approx(60.0 - expected_stacked, abs=1e-4)


def test_respite_enemy_respawn_walkability_verification(tmp_path):
    """Verify Respite.execute_rest() respawns enemies on valid walkable floor tiles outside walls."""
    state = _make_state(tmp_path)
    prototype = [
        "########",
        "#R....Z#",
        "#..##..#",
        "#..##..#",
        "#Z.....#",
        "########",
    ]
    state.world = World("respite_walkability_test")
    state.world.load_from_prototype(prototype)
    state.enemies = list(state.world.enemies)
    state.in_sanctuary = False

    # Also inject a corrupted spawn entry inside an interior wall block (3*40, 2*40)
    state.world.initial_enemy_spawns.append(
        {
            "cls": SlugEnemy,
            "type": "SlugEnemy",
            "x": 3.0 * constants.TILE_SIZE,
            "y": 2.0 * constants.TILE_SIZE,
            "id": "wall_spawn_test",
            "is_miniboss": False,
            "is_stationary": False,
        }
    )

    state.enemies.clear()
    respite = next(obj for obj in state.world.interactables if isinstance(obj, Respite))
    respite.execute_rest(state)

    assert len(state.enemies) == 3
    for enemy in state.enemies:
        tx0 = int(enemy.x // constants.TILE_SIZE)
        ty0 = int(enemy.y // constants.TILE_SIZE)
        tx1 = int((enemy.x + enemy.width - 1e-4) // constants.TILE_SIZE)
        ty1 = int((enemy.y + enemy.height - 1e-4) // constants.TILE_SIZE)
        for ty in range(ty0, ty1 + 1):
            for tx in range(tx0, tx1 + 1):
                assert state.world.grid[ty][tx] != constants.TILE_WALL


def test_steeper_later_act_difficulty_curve_end_to_end(tmp_path, monkeypatch):
    """Verify Acts 1-5 saturation multipliers and Enemy.apply_act_scaling speed/cooldown/HP/damage scaling."""
    expected = {
        1: (1.0, 1.0, 1.0, 1.0, False),
        2: (1.4, 1.35, 1.08, 0.92, False),
        3: (2.0, 1.8, 1.15, 0.85, True),
        4: (2.8, 2.35, 1.22, 0.78, True),
        5: (3.8, 3.0, 1.28, 0.72, True),
    }
    for act_num, (hp_m, dmg_m, spd_m, cd_m, emp) in expected.items():
        sat = constants.get_act_saturation(act_num)
        assert sat["hp_multiplier"] == pytest.approx(hp_m)
        assert sat["damage_multiplier"] == pytest.approx(dmg_m)
        assert sat["speed_multiplier"] == pytest.approx(spd_m)
        assert sat["cooldown_multiplier"] == pytest.approx(cd_m)
        assert sat["empowered"] is emp

    base_slug = SlugEnemy(0, 0)
    scaled_slug = SlugEnemy(0, 0)
    sat5 = constants.get_act_saturation(5)
    scaled_slug.apply_act_scaling(
        sat5["hp_multiplier"],
        sat5["damage_multiplier"],
        empowered=sat5["empowered"],
        speed_multiplier=sat5["speed_multiplier"],
        cooldown_multiplier=sat5["cooldown_multiplier"],
    )
    assert scaled_slug.max_hp == pytest.approx(base_slug.max_hp * 3.8)
    assert scaled_slug.damage == pytest.approx(base_slug.damage * 3.0)
    assert scaled_slug.speed == pytest.approx(base_slug.speed * 1.28)
    assert scaled_slug.attack_cooldown == pytest.approx(base_slug.attack_cooldown * 0.72)
    assert scaled_slug.wind_up_duration < base_slug.wind_up_duration
    assert scaled_slug.recovery_duration < base_slug.recovery_duration
    assert scaled_slug.is_empowered is True

    # End-to-end transition_to_act(4) and NightBoss spawn scaling
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    state = _make_state(tmp_path)
    state.start_chronicle_run(
        ["windy_ridge", "pastoral_valley", "swamp_mire", "frozen_peaks", "tech_tower"]
    )
    assert state.transition_to_act(4) is True
    sat4 = constants.get_act_saturation(4)
    sample_slug = next((e for e in state.enemies if isinstance(e, SlugEnemy)), None)
    if sample_slug is not None:
        assert sample_slug.max_hp == pytest.approx(base_slug.max_hp * sat4["hp_multiplier"])
        assert sample_slug.speed == pytest.approx(base_slug.speed * sat4["speed_multiplier"])

    state.enemies.clear()
    state.weather_manager.bleed_state = "CLAMPED"
    state._update_world_events(0.016)
    if state.active_boss_summons:
        state.player.x = state.active_boss_summons[0]["cx"]
        state.player.y = state.active_boss_summons[0]["cy"]
    state._update_world_events(0.016)
    state._update_world_events(constants.BOSS_SUMMON_DURATION)
    nb = next(e for e in state.enemies if isinstance(e, NightBoss))
    base_nb = nb.__class__(0, 0)
    assert nb.max_hp == pytest.approx(base_nb.max_hp * sat4["hp_multiplier"])
    assert nb.damage == pytest.approx(base_nb.damage * sat4["damage_multiplier"])
    assert nb.speed == pytest.approx(base_nb.speed * sat4["speed_multiplier"])
    assert nb.attack_cooldown == pytest.approx(base_nb.attack_cooldown * sat4["cooldown_multiplier"])


def test_biome_and_boss_chronicle_lore_and_unknown_id_fallback(tmp_path):
    """Verify all 7 biome Chronicle lore pools, crowned Slug Night Boss lore, and 'unknown' vs 'missing_id'."""
    lore_manifest = constants.DIALOGUE_MANIFEST["lore_fragments"]
    for biome in constants.CHRONICLE_BIOME_ROSTER:
        key = f"{biome}_chronicle"
        assert key in lore_manifest
        entries = lore_manifest[key]
        assert isinstance(entries, list) and len(entries) >= 5
        faded_count = sum(1 for item in entries if item == "The text has faded into illegibility.")
        ratio = faded_count / len(entries)
        assert 0.14 <= ratio <= 0.22

    # Verify swamp_mire_chronicle includes the crowned, sword-pierced Slug Night Boss lore
    swamp_entries = " ".join(lore_manifest["swamp_mire_chronicle"]).lower()
    assert "crown" in swamp_entries
    assert "sword" in swamp_entries or "blade" in swamp_entries
    assert "slug" in swamp_entries

    # Verify LoreFragment with fragment_id='unknown' resolves to active biome's <biome>_chronicle pool
    state = _make_state(tmp_path)
    state.world = World("macro_world")
    state.in_sanctuary = False
    state.current_act = 1
    state.run_biomes["act1"] = "swamp_mire"

    seen_lines = set()
    for idx in range(6):
        frag = LoreFragment((idx * 40, 0), (40, 40), "unknown", name="Weathered Parchment")
        frag.execute_interaction(state)
        assert state.active_dialogue is not None
        assert state.active_dialogue["text"] in lore_manifest["swamp_mire_chronicle"]
        seen_lines.add(state.active_dialogue["text"])
    assert len(seen_lines) >= 4

    # Explicit non-existent ID like 'missing_id' must still fall back to 'faded into illegibility'
    missing_frag = LoreFragment((0, 0), (40, 40), "missing_id")
    missing_frag.execute_interaction(state)
    assert "faded into illegibility" in state.active_dialogue["text"]
