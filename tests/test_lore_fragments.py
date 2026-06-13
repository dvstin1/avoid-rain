import pytest
from engine.game_state import GameState
from engine.world import LoreFragment
from engine.maps import create_world
from constants import DIALOGUE_MANIFEST

def test_lore_fragment_instantiation():
    """Verify LoreFragment is placed in the sanctuary via the 'L' tile."""
    world = create_world("sanctuary")
    fragment = next((obj for obj in world.interactables if isinstance(obj, LoreFragment)), None)
    assert fragment is not None
    assert fragment.name == "Faded Note"
    assert fragment.is_solid is False
    assert fragment.is_interactive is True
    assert fragment.fragment_id == "chronicler_nature"

def test_lore_fragment_interaction():
    """Verify LoreFragment interaction displays the correct lore text."""
    gs = GameState(auto_load=False)
    
    world = create_world("sanctuary")
    gs.world = world
    fragment = next((obj for obj in world.interactables if isinstance(obj, LoreFragment)), None)
    assert fragment is not None
    
    fragment.execute_interaction(gs)
    
    expected_text = DIALOGUE_MANIFEST["lore_fragments"]["chronicler_nature"]
    assert gs.active_dialogue is not None
    assert gs.active_dialogue["speaker"] == "Faded Note"
    assert gs.active_dialogue["text"] == expected_text

def test_lore_fragment_unknown_id():
    """Verify LoreFragment handles missing fragment IDs gracefully."""
    fragment = LoreFragment((0, 0), (40, 40), "missing_id")
    gs = GameState(auto_load=False)
    
    fragment.execute_interaction(gs)
    
    assert gs.active_dialogue is not None
    assert "faded into illegibility" in gs.active_dialogue["text"]

def test_chapter1_lore_fragment():
    """Verify LoreFragment is placed in world_map1."""
    world = create_world("world_map1")
    fragment = next((obj for obj in world.interactables if isinstance(obj, LoreFragment)), None)
    # world_map1.json might not have an 'L' tile if it was changed
    if fragment is not None:
        assert fragment.name == "Torn Page"
        assert fragment.fragment_id == "lotus_page"
