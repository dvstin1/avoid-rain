import pytest
from engine.game_state import GameState
from engine.world import Wellspring
from engine.stats import StatisticsTracker

def test_wellspring_instantiation():
    """Verify Wellspring is placed in the sanctuary."""
    from engine.maps import create_world
    world = create_world("sanctuary")
    wellspring = next((obj for obj in world.interactables if isinstance(obj, Wellspring)), None)
    assert wellspring is not None
    assert wellspring.name == "The Wellspring"
    assert wellspring.is_solid is True
    assert wellspring.is_interactive is True

def test_wellspring_interaction_shows_stats():
    """Verify Wellspring interaction displays multiline stats."""
    gs = GameState(auto_load=False)
    gs.stats = StatisticsTracker()
    
    # Set some dummy stats
    gs.stats.data["lifetime_stats"]["wins_chapters_cleared"] = 5
    gs.stats.data["lifetime_stats"]["pages_collected"] = 100
    gs.stats.set_bestiary("slug_enemy", True)
    
    wellspring = next((obj for obj in gs.world.interactables if isinstance(obj, Wellspring)), None)
    assert wellspring is not None
    
    wellspring.execute_interaction(gs)
    
    assert gs.active_dialogue is not None
    assert gs.active_dialogue["speaker"] == "The Wellspring"
    text = gs.active_dialogue["text"]
    assert "Timeline Reflection:" in text
    assert "Chapters Cleared: 5" in text
    assert "Torn Pages: 100" in text
    assert "Syntax Blocks: 1" in text
    assert "\n" in text # Verify it's multiline

def test_wellspring_interaction_no_stats():
    """Verify Wellspring handles missing stats gracefully."""
    gs = GameState(auto_load=False)
    gs.stats = None
    
    wellspring = next((obj for obj in gs.world.interactables if isinstance(obj, Wellspring)), None)
    wellspring.execute_interaction(gs)
    
    assert gs.active_dialogue is not None
    assert "water is still" in gs.active_dialogue["text"]
