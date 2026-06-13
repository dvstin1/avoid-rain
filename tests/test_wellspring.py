import pytest
from engine.world import Wellspring
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from constants import FLASK_MAX_CHARGES

def test_wellspring_refills_flasks():
    """Verify Wellspring interaction resets flask charges."""
    gs = GameState(auto_load=False)
    gs.player.flask_charges = 0
    
    wellspring = next((obj for obj in gs.world.interactables if isinstance(obj, Wellspring)), None)
    assert wellspring is not None
    
    wellspring.execute_interaction(gs)
    assert gs.player.flask_charges == FLASK_MAX_CHARGES

def test_wellspring_already_full():
    """Verify Wellspring interaction when flasks are already full."""
    gs = GameState(auto_load=False)
    gs.player.flask_charges = FLASK_MAX_CHARGES
    
    wellspring = next((obj for obj in gs.world.interactables if isinstance(obj, Wellspring)), None)
    assert wellspring is not None
    
    # This should not crash and should trigger a bloom (visual only)
    wellspring.execute_interaction(gs)
    assert gs.player.flask_charges == FLASK_MAX_CHARGES
