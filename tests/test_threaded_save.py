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
    # Call save_stats which starts a background thread
    gs.save_stats(str(tmp_path / 'profile_metrics.json'))
    # Immediately after calling, saving_in_progress should be True
    assert getattr(gs, 'saving_in_progress', False)
    # Wait for background save to complete
    time.sleep(0.2)
    assert not getattr(gs, 'saving_in_progress', False)
    assert st.saved == 1
