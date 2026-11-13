"""Unit and integration tests for Two-Act Progression, Chronicle Biome Dialog,
Upfront Dual-World LAN Sync, and Expanded Final Boss Arena."""
import json
import os
from unittest.mock import MagicMock

import pygame

import constants
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import LevelLoader, WarpPortal
from engine.world_generator import resolve_run_biomes, generate_dual_worlds


def _make_headless_state(tmp_path):
    """Create a headless GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.network_manager.stop_network()
    return state


def test_chronicle_dialog_two_step_and_debug_toggle(tmp_path):
    """Verify Chronicle opens two-step modal, greys out Act 1 pick in Step 2, and respects debug_biome_select."""
    state = _make_headless_state(tmp_path)
    portal = WarpPortal("macro_world", 10, 10, (0, 0, 40, 40), name="Chronicle")

    # Intercepting macro_world warp opens the Chronicle dialog instead of warping immediately
    started = state.start_warp(portal)
    assert started is False
    assert state.chronicle_dialog is not None
    assert state.chronicle_dialog["step"] == 1

    opts_step1 = state.get_chronicle_dialog_options()
    assert opts_step1[0]["value"] == "random"
    assert opts_step1[-1]["value"] == "cancel"
    assert len(opts_step1) == 2 + len(constants.BIOME_SEGMENT_POOLS)

    # Select 'swamp_mire' in Step 1
    swamp_idx = next(i for i, o in enumerate(opts_step1) if o["value"] == "swamp_mire")
    state.chronicle_dialog["selection"] = swamp_idx
    state.input_ratchet_latched = False
    state._handle_chronicle_dialog_ui({"move": (0, 0)}, attack_pressed=True)

    assert state.chronicle_dialog["step"] == 2
    assert state.chronicle_dialog["act1_choice"] == "swamp_mire"

    opts_step2 = state.get_chronicle_dialog_options()
    swamp_step2 = next(o for o in opts_step2 if o["value"] == "swamp_mire")
    assert swamp_step2["enabled"] is False
    assert opts_step2[-1]["value"] == "back"

    # Back to Step 1 via cancel_chronicle_dialog
    state.cancel_chronicle_dialog()
    assert state.chronicle_dialog["step"] == 1
    state.cancel_chronicle_dialog()
    assert state.chronicle_dialog is None

    # Debug toggle off hides specific biomes while keeping Random
    state.debug_biome_select = False
    state.open_chronicle_biome_dialog(portal)
    opts_no_debug = state.get_chronicle_dialog_options()
    assert [o["value"] for o in opts_no_debug] == ["random", "cancel"]


def test_resolve_run_biomes_never_duplicates():
    """Random/Random and specific/Random always produce distinct Act 1 and Act 2 biomes."""
    for _ in range(25):
        b1, b2 = resolve_run_biomes("random", "random")
        assert b1 != b2
        assert b1 in constants.BIOME_SEGMENT_POOLS
        assert b2 in constants.BIOME_SEGMENT_POOLS

    for chosen in constants.BIOME_SEGMENT_POOLS:
        b1, b2 = resolve_run_biomes(chosen, "random")
        assert b1 == chosen
        assert b2 != chosen

        b1_dup, b2_dup = resolve_run_biomes(chosen, chosen)
        assert b1_dup == chosen
        assert b2_dup != chosen


def test_dual_world_generation_and_lan_coop_payload(tmp_path, monkeypatch):
    """Verify upfront dual-world generation and TCP MAP_RESPONSE bundling + client extraction."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    bundle = generate_dual_worlds("windy_ridge", "frozen_peaks")
    assert bundle["act1_biome"] == "windy_ridge"
    assert bundle["act2_biome"] == "frozen_peaks"
    assert len(bundle["act1_data"]["grid"]) > 0
    assert len(bundle["act2_data"]["grid"]) > 0

    host = _make_headless_state(tmp_path)
    host.start_two_act_run("windy_ridge", "frozen_peaks")
    assert host.current_act == 1
    assert host.run_biomes == {"act1": "windy_ridge", "act2": "frozen_peaks"}
    assert os.path.exists(gen_path)

    payload = host.get_host_map_payload()
    assert payload is not None
    assert "act2_world" in payload
    assert payload["run_biomes"] == {"act1": "windy_ridge", "act2": "frozen_peaks"}

    # Simulate client fetching host map payload
    client = _make_headless_state(tmp_path)
    client.network_manager.is_connected = True
    client.network_manager.network_mode = "CLIENT"
    client.network_manager.request_map = MagicMock(return_value=json.loads(json.dumps(payload)))

    assert client.fetch_host_map() is True
    assert client.current_act == 1
    assert client.run_biomes == {"act1": "windy_ridge", "act2": "frozen_peaks"}
    assert client.act2_world_data is not None
    assert len(client.world.grid) > 0


def test_act1_to_act2_transition_preserves_player_and_resets_world(tmp_path, monkeypatch):
    """Verify Act 1 -> Act 2 transition preserves player stats/gear while resetting weather & world."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)

    state = _make_headless_state(tmp_path)
    state.start_two_act_run("pastoral_valley", "swamp_mire")

    # Mutate player progression during Act 1
    state.player.hp = 63.0
    state.player.flask_charges = 1
    state.player.stats["attack_modifier"] = 15
    state.player.stats["max_hp_modifier"] = 20
    state.player.weapons.append({"name": "Anomalous Blade", "damage": 35, "passive": "bleed"})
    state.player.active_weapon_idx = 1
    state.stats.data["lifetime_stats"]["pages_collected"] = 42
    state.destroyed_prop_ids.add("prop_123")
    state.weather_manager.bleed_state = "APPENDIX"

    # Trigger Act 1 -> Act 2 warp via _update_world_events
    state._update_world_events(0.016)
    assert state.act_warp_target == "act2"
    assert state.warp_controller.is_active()

    # Complete transition directly and verify persistence vs resets
    assert state.transition_to_act2() is True
    assert state.current_act == 2
    assert state.player.hp == 63.0
    assert state.player.flask_charges == 1
    assert state.player.stats["attack_modifier"] == 15
    assert state.player.stats["max_hp_modifier"] == 20
    assert len(state.player.weapons) == 2
    assert state.player.active_weapon_idx == 1
    assert state.stats.data["lifetime_stats"]["pages_collected"] == 42
    assert len(state.destroyed_prop_ids) == 0
    assert state.weather_manager.bleed_state == "GRACE_PERIOD"


def test_expanded_final_boss_arena_and_victory_return(tmp_path):
    """Verify expanded 72x72 night_boss_arena.json loads cleanly and victory returns to sanctuary."""
    arena_path = os.path.join("maps", "night_boss_arena.json")
    assert os.path.exists(arena_path)

    grid, interactables, _, player_start, enemies, _, _ = LevelLoader.load_json_map(arena_path)
    assert len(grid) == 72
    assert len(grid[0]) == 72
    assert player_start == (36 * constants.TILE_SIZE, 60 * constants.TILE_SIZE)
    assert any(getattr(e, "name", "") == "The Final Author" for e in enemies)
    assert len(interactables) > 0

    state = _make_headless_state(tmp_path)
    state.world.name = "night_boss_arena"
    state.enemies = []  # Final Author defeated
    state._handle_victory_conditions(0.016)
    assert state.stats.data.get("last_run_result") == "VICTORY"
    assert state.weather_manager.bleed_state == "DILUTION"

    state.weather_manager.timer = 0.0
    state.bleed_state = "DILUTION"
    state._handle_victory_conditions(0.016)
    assert state.warp_controller.is_active()
