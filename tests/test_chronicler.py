import pytest
from engine.game_state import GameState
from engine.world import Chronicler
from constants import TILE_SIZE

def test_chronicler_instantiation():
    """Verify Chronicler is placed in the sanctuary."""
    from engine.maps import create_world
    world = create_world("sanctuary")
    chronicler = next((obj for obj in world.interactables if isinstance(obj, Chronicler)), None)
    assert chronicler is not None
    assert chronicler.name == "The Chronicler"
    assert chronicler.is_solid is True
    assert chronicler.is_interactive is True

def test_chronicler_dialogue_init():
    """Verify Chronicler shows INIT dialogue by default."""
    gs = GameState(auto_load=False)
    # Ensure stats are initialized with INIT
    from engine.stats import StatisticsTracker
    gs.stats = StatisticsTracker()
    
    chronicler = next((obj for obj in gs.world.interactables if isinstance(obj, Chronicler)), None)
    assert chronicler is not None
    
    # Interaction
    chronicler.execute_interaction(gs)
    assert gs.active_dialogue is not None
    assert "Welcome back to the Scriptorium" in gs.active_dialogue["text"]

def test_chronicler_dialogue_defeat():
    """Verify Chronicler shows DEFEAT dialogue after player respawn."""
    gs = GameState(auto_load=False)
    from engine.stats import StatisticsTracker
    gs.stats = StatisticsTracker()
    
    # Trigger death/respawn
    gs.player.hp = 0
    gs.respawn_player()
    
    assert gs.stats.data["last_run_result"] == "DEFEAT"
    
    chronicler = next((obj for obj in gs.world.interactables if isinstance(obj, Chronicler)), None)
    chronicler.execute_interaction(gs)
    assert gs.active_dialogue is not None
    assert "You return... cold" in gs.active_dialogue["text"]

def test_chronicler_state_reset_on_warp():
    """Verify last_run_result resets to INIT when leaving sanctuary."""
    gs = GameState(auto_load=False)
    from engine.stats import StatisticsTracker
    gs.stats = StatisticsTracker()
    gs.stats.data["last_run_result"] = "DEFEAT"
    
    # Find the warp portal to chapter1
    from engine.world import WarpPortal
    warp = next((obj for obj in gs.world.interactables if isinstance(obj, WarpPortal) and obj.target_name == "chapter1"), None)
    assert warp is not None
    
    warp.execute_interaction(gs)
    assert gs.stats.data["last_run_result"] == "INIT"
    assert gs.world.name == "chapter1"

def test_dialogue_stasis_blocks_movement():
    """Verify that active dialogue blocks game updates."""
    gs = GameState(auto_load=False)
    gs.active_dialogue = {"speaker": "Test", "text": "Hello"}
    
    initial_x = gs.player.x
    # Try to move
    actions = {'move': (1, 0), 'attack': False, 'flask': False}
    gs.update(0.1, actions)
    
    # Player should not have moved
    assert gs.player.x == initial_x
    assert gs.active_dialogue is not None
    
    # Press attack to clear dialogue
    actions = {'move': (1, 0), 'attack': True, 'flask': False}
    gs.update(0.1, actions)
    
    assert gs.active_dialogue is None
    # Player still hasn't moved in THIS frame because update returned early
    assert gs.player.x == initial_x
    
    # Next frame player moves
    actions = {'move': (1, 0), 'attack': False, 'flask': False}
    gs.update(0.1, actions)
    assert gs.player.x > initial_x
