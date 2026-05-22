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

def test_hydrate_from_disk_restores_active_session():
    """Verify that hydrate_from_disk restores exact health and position from run_state."""
    # Create a temporary save file
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # 1. Setup a persistent file with a mid-run snapshot
        stats = StatisticsTracker()
        stats.data["run_state"] = {
            "world_name": "chapter1",
            "player": {
                "x": 500.0,
                "y": 600.0,
                "hp": 42.0,
                "flask_charges": 2
            }
        }
        stats.save(tmp_path)
        
        # Monkeypatch DEFAULT_PATH
        import engine.stats
        original_default = engine.stats.DEFAULT_PATH
        engine.stats.DEFAULT_PATH = Path(tmp_path)
        
        try:
            # 2. Hydrate
            gs = GameState(auto_load=False)
            gs.deallocate()
            gs.hydrate_from_disk()
            
            # 3. Verify exact restoration
            assert gs.world.name == "chapter1"
            assert gs.player.x == 500.0
            assert gs.player.y == 600.0
            assert gs.player.hp == 42.0
            assert gs.player.flask_charges == 2
            
        finally:
            engine.stats.DEFAULT_PATH = original_default
            
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_save_stats_guards_deallocated_state():
    """Verify that save_stats does not overwrite run_state when deallocated."""
    gs = GameState(auto_load=False)
    gs.stats = StatisticsTracker()
    gs.stats.data["run_state"] = {"preserved": True}
    
    gs.deallocate()
    gs.save_stats()
    
    assert gs.stats.data["run_state"] == {"preserved": True}

def test_reset_to_new_game_after_deallocate():
    """Verify that reset_to_new_game works even if state is deallocated."""
    gs = GameState(auto_load=False)
    gs.deallocate()
    
    gs.reset_to_new_game()
    
    assert gs.player is not None
    assert gs.player.hp == float(PLAYER_MAX_HP)
    assert gs.world.name == "sanctuary"
