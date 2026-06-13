import pytest
from engine.game_state import GameState

def test_warp_interaction_required():
    gs = GameState(auto_load=False)
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

    # Call update WITH attack: should warp
    gs.update(0.016, {'move': (0, 0), 'attack': True})
    assert gs.world.name == "generated_world"

def test_warp_persistence():
    """Verify that warping to sanctuary clears session state."""
    from engine.stats import StatisticsTracker
    gs = GameState(auto_load=False)
    gs.stats = StatisticsTracker()
    gs.stats.data["active_session_in_progress"] = True
    
    from engine.world import WarpPortal
    warp = WarpPortal("sanctuary", 100, 100, (0,0,0,0))
    warp.execute_interaction(gs)
    
    assert gs.world.name == "sanctuary"
    assert gs.stats.data["active_session_in_progress"] is False
    assert gs.stats.data["run_state"] is None
