# copyright 2026 Dustin Massop, License: GPLv2
"""Unit tests for Post-Night-Boss Warp Full Heal behavior and regular warp preservation."""
# pylint: disable=protected-access
import constants
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import WarpPortal


def _make_headless_state():
    """Create a headless offline GameState with disk writes stubbed out."""
    stats = StatisticsTracker()
    state = GameState(stats=stats, auto_load=False, offline_only=True)
    state.network_manager.stop_network()
    state.save_stats = lambda wait=False: None
    return state


def _complete_warp(state):
    """Advance InkWarpController through Departure, The Veil, and Arrival until idle."""
    for _ in range(400):
        if not state.warp_controller.is_active():
            break
        state.warp_controller.update(0.05, state)
    assert not state.warp_controller.is_active()


def test_post_night_boss_act_warp_restores_full_hp(tmp_path, monkeypatch):
    """Defeating a Night Boss and warping to the next Act restores player HP to max_hp."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    state = _make_headless_state()
    state.start_chronicle_run(
        ["pastoral_valley", "swamp_mire", "windy_ridge", "frozen_peaks", "tech_tower"]
    )

    # Boost max_hp and wound player before Night Boss defeat
    state.player.stats["max_hp_modifier"] = 30
    expected_max_hp = float(state.player.max_hp)
    assert expected_max_hp == float(constants.PLAYER_MAX_HP + 30)
    state.player.hp = 27.5
    state.player.is_exposed = True

    # Simulate Night Boss defeated -> DILUTION -> APPENDIX -> Act 2 warp
    state.enemies = []
    state.night_boss_spawned = True
    state.weather_manager.bleed_state = "BOSS_PHASE"
    state._update_world_events(0.016)
    assert state.weather_manager.bleed_state == "DILUTION"

    state.weather_manager.timer = 0.0
    state.weather_manager.update(0.016, state.player, state.world)
    assert state.weather_manager.bleed_state == "APPENDIX"

    state._update_world_events(0.016)
    assert state.act_warp_target == "act2"
    assert state.warp_controller.is_active()
    assert state.warp_controller.full_heal_on_transfer is True

    _complete_warp(state)
    assert state.current_act == 2
    assert state.player.hp == expected_max_hp
    assert state.player.is_exposed is False
    assert state.warp_controller.full_heal_on_transfer is False


def test_post_night_boss_final_act_arena_warp_restores_full_hp(tmp_path, monkeypatch):
    """Warping into night_boss_arena after the final Act Night Boss restores player HP to max_hp."""
    gen_path = str(tmp_path / "generated_world.json")
    monkeypatch.setattr(constants, "get_generated_world_path", lambda: gen_path)
    monkeypatch.setattr("engine.world_generator.get_generated_world_path", lambda: gen_path)

    state = _make_headless_state()
    state.start_chronicle_run(
        ["windy_ridge", "pastoral_valley", "swamp_mire", "frozen_peaks", "tech_tower"]
    )
    state.current_act = constants.MAX_ACTS
    state.player.stats["max_hp_modifier"] = 20
    expected_max_hp = float(state.player.max_hp)
    state.player.hp = 19.0
    state.weather_manager.bleed_state = "APPENDIX"

    state._update_world_events(0.016)
    assert state.act_warp_target == "night_boss_arena"
    assert state.warp_controller.is_active()
    assert state.warp_controller.full_heal_on_transfer is True

    _complete_warp(state)
    assert state.world.name == "night_boss_arena"
    assert state.player.hp == expected_max_hp
    assert state.warp_controller.full_heal_on_transfer is False


def test_legacy_appendix_warp_portal_restores_full_hp():
    """Legacy 1-Act Appendix Warp spawned after Night Boss defeat restores player HP on warp."""
    state = _make_headless_state()
    state.current_act = 1
    state.act_worlds = {}
    state.act2_world_data = None
    state.world.boss_coords_list = [{"x": 10, "y": 10}]
    state.weather_manager.set_boss_coords_list(state.world.boss_coords_list)
    state.weather_manager.bleed_state = "APPENDIX"

    state._update_world_events(0.016)
    portal = next((obj for obj in state.world.interactables if obj.name == "Appendix Warp"), None)
    assert portal is not None
    assert getattr(portal, "full_heal_on_warp", False) is True

    state.player.hp = 35.0
    assert state.start_warp(portal) is True
    assert state.warp_controller.full_heal_on_transfer is True
    _complete_warp(state)
    assert state.player.hp == float(state.player.max_hp)


def test_regular_warps_do_not_full_heal():
    """Normal non-Night-Boss warps must preserve wounded player HP without full-healing."""
    state = _make_headless_state()
    state.player.hp = 42.0

    # 1. Regular WarpPortal via InkWarpController
    portal = WarpPortal("ruins", 10, 10, (0, 0, 40, 40), name="Ruins Gate")
    assert getattr(portal, "full_heal_on_warp", False) is False
    assert state.start_warp(portal) is True
    assert state.warp_controller.full_heal_on_transfer is False
    _complete_warp(state)
    assert state.player.hp == 42.0

    # 2. Direct string-target regular warp
    assert state.start_warp("forest") is True
    assert state.warp_controller.full_heal_on_transfer is False
    _complete_warp(state)
    assert state.player.hp == 42.0

    # 3. Direct instant WarpPortal transfer
    instant_portal = WarpPortal("smallcave", 8, 8, (0, 0, 40, 40), name="Cave Entrance")
    instant_portal.execute_interaction(state, instant=True)
    assert state.player.hp == 42.0


def test_lan_coop_post_night_boss_warp_heals_active_runners_and_client():
    """Host heals active runners (excluding Waiting Scholars) and Client heals on post-boss warp."""
    host = _make_headless_state()
    host.network_manager.network_mode = "HOST"
    host.player.hp = 30.0
    host.network_manager.remote_players = {
        "peer-runner": {
            "peer_id": "peer-runner",
            "identity": "Runner",
            "hp": 40.0,
            "x": 100.0,
            "y": 100.0,
            "in_sanctuary": False,
        },
        "peer-waiting": {
            "peer_id": "peer-waiting",
            "identity": "Waiter",
            "hp": 50.0,
            "x": 200.0,
            "y": 200.0,
            "in_sanctuary": True,
        },
    }
    host.cached_client_states["peer-runner"] = {"max_hp": 120.0}
    host.cached_client_states["peer-waiting"] = {"max_hp": 100.0}

    host.restore_post_night_boss_hp()
    assert host.player.hp == float(host.player.max_hp)
    assert host.network_manager.remote_players["peer-runner"]["hp"] == 120.0
    assert host.network_manager.remote_players["peer-waiting"]["hp"] == 50.0

    # Client receiving remote post-Night-Boss night_boss_arena warp full-heals on transfer
    client = _make_headless_state()
    client.network_manager.network_mode = "CLIENT"
    client.in_sanctuary = False
    client.waiting_for_host_run = False
    client.player.hp = 22.0
    client.apply_remote_state(("127.0.0.1", 55557), {"act_warp_target": "night_boss_arena"})
    assert client.warp_controller.is_active()
    assert client.warp_controller.full_heal_on_transfer is True
    _complete_warp(client)
    assert client.world.name == "night_boss_arena"
    assert client.player.hp == float(client.player.max_hp)
