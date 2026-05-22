"""
Tests for game state persistence (save/load).
"""
import os
import tempfile
from pathlib import Path
from engine.game_state import GameState
from engine.stats import StatisticsTracker
from engine.maps import OutsideWorld
from constants import PLAYER_START_X, PLAYER_START_Y

def test_save_and_load_state():
    # Use a temporary file for stats
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        # 1. Create a state and modify it
        stats = StatisticsTracker()
        gs = GameState(stats=stats, auto_load=False)
        
        # Warp to outside and move player
        from engine.maps import create_world
        gs.world = create_world('outside')
        gs.player.x = 123.0
        gs.player.y = 456.0
        gs.player.hp = 77.0
        gs.player.flask_charges = 1
        
        # 2. Save state
        # We need to call save_stats and wait for it
        gs.save_stats(tmp_path)
        gs.shutdown_save_worker(timeout=2.0)
        
        # 3. Create a new GameState and load from the same file
        stats2 = StatisticsTracker.load(tmp_path)
        gs2 = GameState(stats=stats2, auto_load=False)
        
        # 4. Verify state restored
        assert gs2.world.name == 'outside'
        assert isinstance(gs2.world, OutsideWorld)
        assert gs2.player.x == 123.0
        assert gs2.player.y == 456.0
        assert gs2.player.hp == 77.0
        assert gs2.player.flask_charges == 1
        
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_new_game_clears_state():
    # Verify that creating a fresh StatisticsTracker has no run_state
    stats = StatisticsTracker()
    assert stats.data["run_state"] is None
    
    gs = GameState(stats=stats, auto_load=False)
    assert gs.world.name == 'sanctuary'
    assert gs.player.x == PLAYER_START_X
    assert gs.player.y == PLAYER_START_Y
