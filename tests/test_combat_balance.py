"""Unit tests for Section 14: Combat & Progression Balance.

Verifies rebalanced flat attack-up scaling (Respite Prowess, Choice of Fates, Binder Scripts),
increased standard enemy and boss HP pools, and normalized mid-run miniboss distribution across
all 7 biome segment pools and stitched Act macro-worlds.
"""
# pylint: disable=no-member

import json

import pygame

import constants
from engine.enemy import (
    BatEnemy,
    BindlingEnemy,
    FinalAuthor,
    FlutterEnemy,
    Miniboss,
    NightBoss,
    PunctuationWolfEnemy,
    SentryEnemy,
    SlugEnemy,
    SmearEnemy,
)
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import Respite
from engine.world_generator import WorldGenerator
from ui.menu import draw_respite_menu


def test_prowess_attack_step_respite_ui_and_edification_parity():
    """Verify PROWESS_ATTACK_STEP drives Respite finalization, _handle_upgrade, and Respite menu labels."""
    pygame.init()
    state = GameState(auto_load=False, stats=StatisticsTracker())
    state.stats.data["lifetime_stats"]["pages_collected"] = 500
    respite = Respite((0, 0), (40, 40))
    state.world.interactables.append(respite)
    state.active_respite = respite
    respite.execute_rest(state)

    # Render Respite menu and assert dynamic "+N Attack" label reflects PROWESS_ATTACK_STEP
    captured = []

    class _SpyFont:
        def render(self, text, _aa, _color):
            captured.append(str(text))
            return pygame.Surface((40, 12), pygame.SRCALPHA)

    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    draw_respite_menu(screen, _SpyFont(), state)
    expected_label = f"Level Up Prowess (+{constants.PROWESS_ATTACK_STEP} Attack)"
    assert any(expected_label in line for line in captured), f"Expected '{expected_label}' in {captured}"

    # Stage 3 Prowess upgrades and finalize
    state.respite_upgrades = {1: 3, 2: 0}
    assert respite.execute_finalize_upgrades(state) is True
    assert state.player.stats["attack_modifier"] == 3 * constants.PROWESS_ATTACK_STEP
    assert state.player.stats["edification"] == 4
    info = state.get_staged_respite_info()
    assert info["prowess_lvl"] == 4


def test_choice_of_fates_and_binder_scripts_rebalanced_attack():
    """Verify Choice of Fates offense/defense boons and Binder Scripts attack values are rebalanced."""
    state = GameState(auto_load=False, stats=StatisticsTracker())

    # Level 1 Choice of Fates
    state.stats.data["lifetime_stats"]["pages_collected"] = 0
    state.trigger_choice_of_fates()
    quill, binding = state.active_choice["options"]
    assert quill["modifiers"]["attack_modifier"] == constants.CHOICE_OF_FATES_ATTACK_BASE
    assert quill["modifiers"]["attack_modifier"] < 5
    assert binding["modifiers"]["max_hp_modifier"] == constants.CHOICE_OF_FATES_HP_BASE
    assert binding["modifiers"]["attack_modifier"] == 1

    # Level 2 Choice of Fates (100+ pages)
    state.stats.data["lifetime_stats"]["pages_collected"] = 100
    state.trigger_choice_of_fates()
    quill_l2, binding_l2 = state.active_choice["options"]
    assert quill_l2["modifiers"]["attack_modifier"] == 2 * constants.CHOICE_OF_FATES_ATTACK_BASE
    assert binding_l2["modifiers"]["max_hp_modifier"] == 2 * constants.CHOICE_OF_FATES_HP_BASE

    # Binder Scripts serif_minor / serif_major
    serif_minor = constants.BINDER_SCRIPTS_BY_ID["serif_minor"]
    serif_major = constants.BINDER_SCRIPTS_BY_ID["serif_major"]
    assert serif_minor["value"] == 2.0
    assert serif_minor["summary"] == "+2 Attack"
    assert serif_major["value"] == 5.0
    assert serif_major["summary"] == "+5 Attack"


def test_increased_enemy_and_boss_hp_pools():
    """Verify bumped HP constants across all standard enemies and explicit boss HP constants."""
    assert SlugEnemy(0, 0).max_hp == constants.SLUG_MAX_HP >= 60
    assert BatEnemy(0, 0).max_hp == constants.BAT_MAX_HP >= 30
    assert FlutterEnemy(0, 0).max_hp == constants.FLUTTER_MAX_HP >= 12
    assert BindlingEnemy(0, 0).max_hp == constants.BINDLING_MAX_HP >= 75
    assert SmearEnemy(0, 0).max_hp == constants.SMEAR_MAX_HP >= 90
    assert SentryEnemy(0, 0).max_hp == constants.SENTRY_MAX_HP >= 65
    assert PunctuationWolfEnemy(0, 0).max_hp == constants.WOLF_MAX_HP >= 55

    assert Miniboss(0, 0).max_hp == constants.MINIBOSS_MAX_HP >= 400
    assert NightBoss(0, 0).max_hp == constants.NIGHT_BOSS_MAX_HP >= 900
    assert FinalAuthor(0, 0).max_hp == constants.FINAL_AUTHOR_MAX_HP >= 1500
    assert constants.MINIBOSS_MAX_HP < constants.NIGHT_BOSS_MAX_HP < constants.FINAL_AUTHOR_MAX_HP


def test_normalized_miniboss_distribution_across_all_7_biomes():
    """Verify all 7 biomes have identical segment miniboss quotas and exact per-Act miniboss budgets."""
    assert len(constants.BIOME_SEGMENT_POOLS) == 7

    for biome, pool in constants.BIOME_SEGMENT_POOLS.items():
        room_counts = []
        for path in pool["rooms"]:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            room_counts.append(sum(row.count("E") for row in data["grid"]))

        corridor_counts = []
        for path in pool["corridors"]:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            corridor_counts.append(sum(row.count("E") for row in data["grid"]))

        assert room_counts == [1, 0, 1, 0], f"Unexpected room miniboss quota for {biome}: {room_counts}"
        assert corridor_counts == [0, 0, 0, 0], f"Unexpected corridor minibosses in {biome}: {corridor_counts}"

        gen = WorldGenerator(world_id=f"balance_test_{biome}", biome=biome)
        gen.generate_layout()
        act_minibosses = 0
        for socket in gen.sockets:
            with open(socket["active_plug"], "r", encoding="utf-8") as handle:
                plug_data = json.load(handle)
            act_minibosses += sum(row.count("E") for row in plug_data["grid"])
        assert act_minibosses == constants.ACT_MINIBOSS_BUDGET, (
            f"Expected {constants.ACT_MINIBOSS_BUDGET} minibosses in {biome} Act, got {act_minibosses}"
        )
