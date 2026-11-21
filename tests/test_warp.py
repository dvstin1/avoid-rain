"""Unit tests for warping interactions and state reset logic."""
from engine.game_state import GameState
from engine.world import WarpPortal

def test_warp_interaction_required():
    """Verify player must attack to execute portal warping."""
    gs = GameState(auto_load=False)
    gs.debug_text_enabled = True
    gs.debug_biome_select = True
    # Find warp interactable in the sanctuary
    warp_obj = None
    for obj in gs.world.interactables:
        if hasattr(obj, 'target_name'):
            warp_obj = obj
            break
    assert warp_obj is not None, "No warp portal found in sanctuary"

    # Move player to warp portal
    gs.player.x, gs.player.y = warp_obj.x, warp_obj.y

    # Call update without attack: should NOT warp
    gs.update(0.016, {'move': (0, 0), 'attack': False})
    assert gs.world.name == "sanctuary"

    # Call update WITH attack: opens 5-step Unbound Chronicle biome dialog
    gs.update(0.016, {'move': (0, 0), 'attack': True})
    assert gs.chronicle_dialog is not None
    assert gs.chronicle_dialog["step"] == 1

    # Confirm Steps 1..5 (Random) to initiate cinematic warp
    for next_step in range(2, 6):
        gs.update(0.25, {'move': (0, 0), 'attack': False})
        gs.input_ratchet_latched = False
        gs.update(0.016, {'move': (0, 0), 'attack': True})
        assert gs.chronicle_dialog["step"] == next_step
    gs.update(0.25, {'move': (0, 0), 'attack': False})
    gs.input_ratchet_latched = False
    gs.update(0.016, {'move': (0, 0), 'attack': True})
    assert gs.chronicle_dialog is None
    assert gs.warp_controller.is_active()

    # Step through transit stages to arrival
    while gs.warp_controller.is_active():
        gs.update(0.016, {'move': (0, 0), 'attack': False})
    assert gs.world.name == "generated_world"
    gs.network_manager.stop_network()

def test_warp_persistence():
    """Verify that warping to sanctuary clears session state."""
    from engine.stats import StatisticsTracker
    gs = GameState(auto_load=False)
    gs.stats = StatisticsTracker()
    gs.stats.data["active_session_in_progress"] = True

    warp = WarpPortal("sanctuary", 100, 100, (0, 0, 0, 0))
    warp.execute_interaction(gs)

    assert gs.world.name == "sanctuary"
    assert gs.stats.data["active_session_in_progress"] is False
    assert gs.stats.data["run_state"] is None

def test_warp_level_reset():
    """Verify that warping to sanctuary resets player stats and level to 1."""
    gs = GameState(auto_load=False)
    # Set upgraded stats
    gs.player.stats = {
        "attack_modifier": 10,
        "max_hp_modifier": 20,
        "edification": 4
    }
    # Update current and max HP
    gs.player.hp = 120.0
    assert gs.player.max_hp == 120.0

    warp = WarpPortal("sanctuary", 100, 100, (0, 0, 0, 0))
    warp.execute_interaction(gs)

    assert gs.world.name == "sanctuary"
    assert gs.player.stats["edification"] == 1
    assert gs.player.stats["attack_modifier"] == 0
    assert gs.player.stats["max_hp_modifier"] == 0
    assert gs.player.max_hp == 100.0
    assert gs.player.hp == 100.0
