
import pytest
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.world import WarpPortal
from engine.title_menu import TitleMenu

class MockWorld:
    def __init__(self, name="outside"):
        self.name = name
        self.grid = [[0]]
        self.player_start = (0, 0)
    def get_nearby_interactables(self, rect): return []
    def get_nearby_walls(self, rect): return []

def test_session_flag_management():
    """Verify active_session_in_progress is set/cleared correctly."""
    state = GameState(auto_load=False)
    state.stats = StatisticsTracker()
    
    # 1. Outside Sanctuary -> In Progress
    state.world = MockWorld("chapter1")
    state.save_stats(wait=True)
    assert state.stats.data["active_session_in_progress"] is True
    assert state.stats.data["run_state"] is not None
    
    # 2. In Sanctuary -> NOT In Progress
    state.world = MockWorld("sanctuary")
    state.save_stats(wait=True)
    assert state.stats.data["active_session_in_progress"] is False
    assert state.stats.data["run_state"] is None

def test_death_clears_persistence():
    """Verify that player death clears the resume-able session."""
    state = GameState(auto_load=False)
    state.stats = StatisticsTracker()
    state.world = MockWorld("chapter1")
    state.save_stats(wait=True)
    assert state.stats.data["active_session_in_progress"] is True
    
    # Trigger death/respawn
    state.player.hp = 0
    state.respawn_player()
    
    assert state.stats.data["active_session_in_progress"] is False
    assert state.stats.data["run_state"] is None

def test_title_menu_detection():
    """Verify that TitleMenu options respond to the session flag."""
    # Case 1: No session
    menu_none = TitleMenu(has_save=False)
    assert "Continue" not in menu_none.get_options()
    
    # Case 2: Session exists
    menu_active = TitleMenu(has_save=True)
    assert "Continue" in menu_active.get_options()
    assert menu_active.get_selected() == "Continue"
