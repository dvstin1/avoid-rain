import pytest
import os
import json
import tempfile
from pathlib import Path
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.player import Player
from constants import PLAYER_START_X, PLAYER_START_Y, PLAYER_MAX_HP

def test_deallocate_purges_memory():
    """Verify that deallocate clears runtime gameplay objects."""
    gs = GameState(auto_load=False)
    assert gs.player is not None
    assert gs.world is not None
    
    gs.deallocate()
    
    assert gs.player is None
    assert gs.world is None
    assert gs.enemies == []
    assert gs.loot == []

def test_hydrate_from_disk_reloads_and_resets():
    """Verify that hydrate_from_disk reloads persistent state and resets player."""
    # Create a temporary save file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # 1. Setup a "dirty" state
        gs = GameState(auto_load=False)
        gs.player.hp = 10.0
        gs.player.x = 999.0
        
        # 2. Setup a "clean" persistent file
        stats = StatisticsTracker()
        stats.data["last_run_result"] = "VICTORY"
        stats.save(tmp_path)
        
        # Monkeypatch DEFAULT_PATH for StatisticsTracker to use our tmp file
        import engine.stats
        original_default = engine.stats.DEFAULT_PATH
        engine.stats.DEFAULT_PATH = Path(tmp_path)
        
        try:
            # 3. Hydrate
            gs.hydrate_from_disk()
            
            # 4. Verify
            assert gs.stats.data["last_run_result"] == "VICTORY"
            assert gs.player is not None
            assert gs.player.hp == float(PLAYER_MAX_HP)
            # Should be at sanctuary spawn, not 999
            assert gs.player.x != 999.0
            assert gs.world.name == "sanctuary"
            
        finally:
            engine.stats.DEFAULT_PATH = original_default
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_reset_to_new_game_after_deallocate():
    """Verify that reset_to_new_game works even if state is deallocated."""
    gs = GameState(auto_load=False)
    gs.deallocate()
    
    gs.reset_to_new_game()
    
    assert gs.player is not None
    assert gs.player.hp == float(PLAYER_MAX_HP)
    assert gs.world.name == "sanctuary"
