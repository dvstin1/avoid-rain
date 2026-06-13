"""Tests for threaded save behavior via GameState.save_stats()."""
import time
import os
import json
from engine.game_state import GameState
from engine.stats import StatisticsTracker

def test_threaded_save_writes_file(tmp_path):
    st = StatisticsTracker()
    st.data["player_name"] = "ThreadedScholar"
    gs = GameState(stats=st, auto_load=False)
    
    save_path = str(tmp_path / 'profile_metrics.json')
    
    # Call save_stats which enqueues a save for the worker
    gs.save_stats(save_path)
    
    # Wait until the file exists and is populated
    timeout = 2.0
    waited = 0.0
    interval = 0.05
    while not os.path.exists(save_path) and waited < timeout:
        time.sleep(interval)
        waited += interval
        
    assert os.path.exists(save_path)
    
    # Verify content
    with open(save_path, 'r') as f:
        data = json.load(f)
    assert data["player_name"] == "ThreadedScholar"
    
    # Shutdown worker
    gs.shutdown_save_worker()
