"""
Unit tests for the Respite multi-upgrade and staging system.
"""
from engine.game_state import GameState
from engine.world import Respite
from engine.stats import StatisticsTracker

# pylint: disable=protected-access
def test_respite_multi_upgrade_staging_and_finalize():
    """
    Verifies that we can stage multiple upgrades for prowess and fortification,
    that costs and levels update virtually, and that finalization correctly
    applies all staged changes at once.
    """
    # 1. Initialize GameState with a clean statistics tracker
    state = GameState(auto_load=False, stats=StatisticsTracker())

    # 2. Give the player some pages to afford multiple upgrades
    state.stats.data["lifetime_stats"]["pages_collected"] = 1500

    # Verify initial levels and stats
    prowess = state.player.stats.get("attack_modifier", 0)
    fort = state.player.stats.get("max_hp_modifier", 0)
    assert prowess == 0
    assert fort == 0
    assert state.player.stats.get("edification", 1) == 1

    # Create the respite anchor
    respite = Respite((0, 0), (40, 40))
    state.world.interactables.append(respite)
    state.active_respite = respite

    # Upgrades should be locked until rested
    assert state.player.has_rested_this_session is False

    # Rest to unlock upgrades
    respite.execute_rest(state)
    assert state.player.has_rested_this_session is True

    # 3. Verify get_staged_respite_info initial state
    info = state.get_staged_respite_info()
    assert info["prowess_lvl"] == 1
    assert info["staged_prowess"] == 0
    assert info["fort_lvl"] == 1
    assert info["staged_fort"] == 0
    assert info["total_staged_cost"] == 0

    # 4. Stage prowess upgrade (Selection index 1)
    # Simulate attack pressed on option 1 in the UI dialogue handling
    state.respite_selection_idx = 1
    state.input_ratchet_latched = False
    state._handle_dialogue_ui(actions={}, attack_pressed=True, audio_manager=None)

    info = state.get_staged_respite_info()
    assert state.respite_upgrades[1] == 1
    assert info["staged_prowess"] == 1
    assert info["total_staged_cost"] > 0

    # Stage prowess upgrade a second time
    state.input_ratchet_latched = False
    state._handle_dialogue_ui(actions={}, attack_pressed=True, audio_manager=None)
    info = state.get_staged_respite_info()
    assert state.respite_upgrades[1] == 2
    assert info["staged_prowess"] == 2

    # 5. Stage fortification upgrade (Selection index 2)
    state.respite_selection_idx = 2
    state.input_ratchet_latched = False
    state._handle_dialogue_ui(actions={}, attack_pressed=True, audio_manager=None)
    info = state.get_staged_respite_info()
    assert state.respite_upgrades[2] == 1
    assert info["staged_staged_fort" if "staged_staged_fort" in info else "staged_fort"] == 1

    # 6. Verify that no attributes have actually been modified yet
    assert state.player.stats.get("attack_modifier", 0) == 0
    assert state.player.stats.get("max_hp_modifier", 0) == 0

    # 7. Finalize upgrades (Selection index 4)
    state.respite_selection_idx = 4
    state.input_ratchet_latched = False
    state._handle_dialogue_ui(actions={}, attack_pressed=True, audio_manager=None)

    # 8. Verify upgrades are applied
    # Prowess was staged 2 times (2 * +5 = +10 Attack)
    assert state.player.stats.get("attack_modifier", 0) == 10
    # Fortification was staged 1 time (1 * +10 = +10 Max HP)
    assert state.player.stats.get("max_hp_modifier", 0) == 10
    # Edification recalculated: (10 // 5) + (10 // 10) + 1 = 2 + 1 + 1 = 4
    assert state.player.stats.get("edification", 1) == 4

    # Pages deducted correctly
    expected_pages = 1500 - info["total_staged_cost"]
    assert state.stats.data["lifetime_stats"]["pages_collected"] == expected_pages

    # Upgrades locked again, staging cleared
    assert state.player.has_rested_this_session is False
    assert state.respite_upgrades == {1: 0, 2: 0}
