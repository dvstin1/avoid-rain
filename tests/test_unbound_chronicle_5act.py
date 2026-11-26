# copyright 2026 Dustin Massop, License: GPLv2
"""
Unit and integration tests for Pass 1 of Section 12:
5-Act Unbound Chronicle Progression, 5-of-7 Biome Draft & Ordering,
Act Saturation Matrix, Act-Keyed Segment Pool Fallback Loader, and 5-Act LAN Co-op Sync.
"""
# pylint: disable=protected-access,no-member,import-outside-toplevel,too-many-locals,too-many-statements
import json
from unittest.mock import MagicMock

import pygame

import constants
from engine.game_state import GameState
from engine.loot import roll_drop
from engine.stats import StatisticsTracker
from engine.world import WarpPortal
from engine.world_generator import resolve_five_act_biomes, resolve_segment_pool
from ui.menu import draw_chronicle_biome_menu


def _make_state(tmp_path):
    """Create a headless GameState backed by a temporary stats path."""
    pygame.init()
    stats_path = str(tmp_path / "stats.json")
    stats = StatisticsTracker()
    state = GameState(auto_load=False, stats=stats, stats_path=stats_path)
    state.online_mode = False
    state.network_manager.stop_network()
    return state


def test_5_of_7_biome_draft_dialog_and_ordering(tmp_path, monkeypatch):
    """Verify 5-of-7 Unbound Chronicle draft UI selects and orders 5 distinct biomes from the 7-biome roster."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    assert len(constants.CHRONICLE_BIOME_ROSTER) == 7
    assert "vitreous_basin" in constants.CHRONICLE_BIOME_ROSTER
    assert "sunlit_aqueducts" in constants.CHRONICLE_BIOME_ROSTER

    state = _make_state(tmp_path)
    state.debug_text_enabled = True
    state.debug_biome_select = True
    portal = WarpPortal("macro_world", 10, 10, (0, 0, 40, 40), name="Chronicle")
    assert state.start_warp(portal) is False
    assert state.chronicle_dialog is not None
    assert state.chronicle_dialog["max_steps"] == 5

    desired_order = [
        "vitreous_basin",
        "sunlit_aqueducts",
        "swamp_mire",
        "frozen_peaks",
        "tech_tower",
    ]
    screen = pygame.Surface((1280, 720))
    from rendering.bitmap_font import load_font_or_sysfont

    font = load_font_or_sysfont("ink_sans", 2, "Arial", 24)

    for step_idx, biome_id in enumerate(desired_order, start=1):
        assert state.chronicle_dialog["step"] == step_idx
        opts = state.get_chronicle_dialog_options()
        # Previously picked biomes must be disabled with selected_act metadata
        for prev_act, prev_b in enumerate(desired_order[: step_idx - 1], start=1):
            prev_opt = next(o for o in opts if o["value"] == prev_b)
            assert prev_opt["enabled"] is False
            assert prev_opt["selected_act"] == prev_act

        draw_chronicle_biome_menu(screen, font, state)

        pick_idx = next(i for i, o in enumerate(opts) if o["value"] == biome_id)
        state.chronicle_dialog["selection"] = pick_idx
        state.input_ratchet_latched = False
        state._handle_chronicle_dialog_ui({"move": (0, 0)}, attack_pressed=True)

    assert state.chronicle_dialog is None
    while state.warp_controller.is_active():
        state.update(0.016, {"move": (0, 0), "attack": False})

    assert state.current_act == 1
    assert [state.run_biomes[f"act{i}"] for i in range(1, 6)] == desired_order
    assert len(set(state.run_biomes.values())) == 5


def test_resolve_segment_pool_lower_act_and_pass2_fallbacks(monkeypatch):
    """Verify resolve_segment_pool checks (biome, act), walks down act-1..1, and falls back safely for Pass 2."""
    custom_act2 = {
        "rooms": ["maps/segments/windy_ridge/windy_ridge_room_2.json"],
        "corridors": ["maps/segments/windy_ridge/windy_ridge_corridor_2.json"],
    }
    monkeypatch.setitem(constants.BIOME_ACT_SEGMENT_POOLS, ("windy_ridge", 2), custom_act2)

    # Act 4 walks down 4 -> 3 -> 2 and finds the authored Act 2 pool
    resolved_a4 = resolve_segment_pool("windy_ridge", 4)
    assert resolved_a4["resolved_biome"] == "windy_ridge"
    assert resolved_a4["resolved_act"] == 2
    assert resolved_a4["rooms"] == custom_act2["rooms"]

    # Act 1 resolves directly to (windy_ridge, 1)
    resolved_a1 = resolve_segment_pool("windy_ridge", 1)
    assert resolved_a1["resolved_act"] == 1

    # Pass 2 biomes now resolve natively to their on-disk segment pools
    for pass2_biome in ("vitreous_basin", "sunlit_aqueducts"):
        pool = resolve_segment_pool(pass2_biome, 3)
        assert len(pool["rooms"]) >= 4
        assert len(pool["corridors"]) >= 4
        assert pool["resolved_biome"] == pass2_biome
        assert pool["resolved_act"] == 1


def test_pass2_biome_assets_and_renderer_integration(tmp_path):
    """Verify Pass 2 procedural PNGs load in Renderer, sockets resolve, and Act 1-5 empowerment works."""
    from rendering.renderer import Renderer

    pygame.init()
    screen = pygame.Surface((640, 360))
    renderer = Renderer(screen)
    for prop_key in (
        "VitreousSaltFloor",
        "VitreousGlassFlat",
        "VitreousSaltSpire",
        "AqueductTerracottaFloor",
        "AqueductMossWall",
        "AqueductPillar",
    ):
        assert prop_key in renderer.prop_cache, f"Missing Pass 2 asset in Renderer.prop_cache: {prop_key}"

    mock_state = _make_state(tmp_path)
    mock_state.world.name = "generated_world"
    mock_state.world.module_sockets = [
        {
            "bounds": {"x": 0, "y": 0, "width": 40, "height": 40},
            "active_plug": "maps/segments/vitreous_basin/vitreous_basin_room_1.json",
        },
        {
            "bounds": {"x": 40, "y": 0, "width": 40, "height": 40},
            "active_plug": "maps/segments/sunlit_aqueducts/sunlit_aqueducts_room_1.json",
        },
    ]
    assert renderer._resolve_tile_biome(mock_state, 10, 10) == "vitreous_basin"
    assert renderer._resolve_tile_biome(mock_state, 50, 10) == "sunlit_aqueducts"

    # Act 4 run starting in vitreous_basin / sunlit_aqueducts empowers enemies properly
    mock_state.start_chronicle_run(
        ["vitreous_basin", "sunlit_aqueducts", "windy_ridge", "swamp_mire", "tech_tower"]
    )
    assert mock_state.transition_to_act(4) is True
    assert mock_state.empowered_act is True
    assert all(e.is_empowered for e in mock_state.enemies)


def test_5act_progression_saturation_matrix_and_marginalia(tmp_path, monkeypatch):
    """Verify Act 1 -> 2 -> 3 -> 4 -> 5 -> night_boss_arena progression, Act 1-5 saturation scaling,
    and MarginaliaEventEngine support across all 5 Acts."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    state = _make_state(tmp_path)
    state.start_chronicle_run(
        ["windy_ridge", "pastoral_valley", "swamp_mire", "frozen_peaks", "tech_tower"]
    )

    for expected_act in range(1, 6):
        assert state.current_act == expected_act
        sat = constants.get_act_saturation(expected_act)
        assert state.empowered_act is bool(sat["empowered"])
        assert (expected_act >= 3) is state.empowered_act
        assert state.weather_manager.rain_dps == sat["rain_dps"]
        for enemy in state.enemies:
            assert enemy.is_empowered is bool(sat["empowered"])

        # MarginaliaEventEngine supports rolling/starting 1 event per Act across Acts 1..5
        ev = state.marginalia_engine.start_event(state, "unblotted_margin", act_variant=expected_act)
        assert ev is not None
        assert ev.act_number == expected_act
        assert ev.act_variant == (1 if expected_act == 1 else 2)
        assert expected_act in state.marginalia_engine.triggered_acts
        assert state.marginalia_engine.try_roll_for_act(state) is None

        # Advance via APPENDIX to next Act (or night_boss_arena after Act 5)
        state.weather_manager.bleed_state = "APPENDIX"
        state._update_world_events(0.016)
        if expected_act < 5:
            assert state.act_warp_target == f"act{expected_act + 1}"
            assert state.transition_to_act(expected_act + 1) is True
        else:
            assert state.act_warp_target == "night_boss_arena"

    # Verify Torn Page yield scaling across Acts 1..5
    assert constants.scale_pages_for_act(20, 1) == 20
    assert constants.scale_pages_for_act(20, 3) == 30
    assert constants.scale_pages_for_act(20, 5) == 40

    state.loot.clear()
    state.current_act = 5
    roll_drop(2, (100, 100), state)
    assert len(state.loot) == 1
    assert state.loot[0].amount >= 40  # 20..50 scaled by 2.0x in Act 5

    # Returning to Sanctuary resets Torn Pages to 0 and clears 5-Act state
    state.stats.data["lifetime_stats"]["pages_collected"] = 75
    state.on_enter_sanctuary()
    assert state.stats.data["lifetime_stats"]["pages_collected"] == 0
    assert state.current_act == 0
    assert state.act_worlds == {}


def test_5act_lan_coop_replication_and_backward_compatible_hydration(tmp_path, monkeypatch):
    """Verify Host->Client 5-Act MAP_RESPONSE & warp sync and backward-compatible 2-Act save hydration."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    host = _make_state(tmp_path)
    host.network_manager.network_mode = "HOST"
    draft = ["windy_ridge", "vitreous_basin", "swamp_mire", "sunlit_aqueducts", "tech_tower"]
    host.start_chronicle_run(draft)

    payload = host.get_host_map_payload()
    assert payload is not None
    assert set(payload["act_worlds"].keys()) == {"2", "3", "4", "5"}
    assert [payload["run_biomes"][f"act{i}"] for i in range(1, 6)] == draft

    client = _make_state(tmp_path)
    client.network_manager.is_connected = True
    client.network_manager.network_mode = "CLIENT"
    client.network_manager.request_map = MagicMock(return_value=json.loads(json.dumps(payload)))
    assert client.fetch_host_map() is True
    assert set(client.act_worlds.keys()) == {1, 2, 3, 4, 5}
    assert client.run_biomes == host.run_biomes

    # Simulate Host advancing to Act 3 and broadcasting act_warp_target="act3"
    host.transition_to_act(2)
    host.act_warp_target = "act3"
    snap = host.get_local_state()

    client.in_sanctuary = False
    client.waiting_for_host_run = False
    client.apply_remote_state(("127.0.0.1", 55557), snap)
    assert client.warp_controller.is_active()
    assert client.transition_to_act(3) is True
    assert client.current_act == 3
    assert client.empowered_act is True

    # Verify legacy 2-Act save_data.json run_state hydrates cleanly into 5-Act schema
    legacy_stats = StatisticsTracker()
    legacy_stats.data["run_state"] = {
        "world_name": "chapter1",
        "current_act": 2,
        "run_biomes": {"act1": "windy_ridge", "act2": "frozen_peaks"},
        "player": {"x": 200.0, "y": 240.0, "hp": 80.0, "flask_charges": 2},
        "weather": {"bleed_state": "WAIT", "active_safe_radius": 800.0},
    }
    hydrated = GameState(stats=legacy_stats, auto_load=True)
    hydrated.network_manager.stop_network()
    assert hydrated.current_act == 2
    assert hydrated.run_biomes["act1"] == "windy_ridge"
    assert hydrated.run_biomes["act2"] == "frozen_peaks"
    assert "act5" in hydrated.run_biomes

    # Also verify resolve_five_act_biomes never duplicates across random permutations
    for _ in range(20):
        biomes = resolve_five_act_biomes(["random"] * 5)
        assert len(biomes) == 5
        assert len(set(biomes)) == 5
