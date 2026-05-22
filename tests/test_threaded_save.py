"""Tests for threaded save behavior via GameState.save_stats()."""
import time
from engine.game_state import GameState
from engine.stats import StatisticsTracker


class SlowStats(StatisticsTracker):
    def __init__(self):
        super().__init__()
        self.saved = 0
    def save(self, path=None):
        # Simulate a slow save
        time.sleep(0.1)
        self.saved += 1


def test_threaded_save_sets_flags(tmp_path):
    st = SlowStats()
    gs = GameState(stats=st, auto_load=False)
    # Ensure not saving initially
    assert not getattr(gs, 'saving_in_progress', False)
    # Call save_stats which enqueues a save for the worker
    gs.save_stats(str(tmp_path / 'profile_metrics.json'))
    # Wait until the save is processed (poll with timeout)
    timeout = 1.0
    waited = 0.0
    interval = 0.01
    while st.saved == 0 and waited < timeout:
        time.sleep(interval)
        waited += interval
    assert st.saved == 1
    # Shutdown worker for cleanliness
    gs.shutdown_save_worker()
