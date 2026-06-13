"""Tests for GameState integration with the StatisticsTracker.

Verifies that GameState integration works and
that save_stats writes the file to disk.
"""
import json
from engine.game_state import GameState
from engine.stats import StatisticsTracker


def test_game_state_integration_with_tracker(tmp_path):
    st = StatisticsTracker()
    assert st.to_dict()["lifetime_stats"]["runs_started"] == 0
    gs = GameState(stats=st)
    assert gs.stats.to_dict()["lifetime_stats"]["runs_started"] == 0


def test_game_state_save_stats_writes_file(tmp_path):
    st = StatisticsTracker()
    gs = GameState(stats=st)
    p = tmp_path / "profile_metrics.json"
    assert not p.exists()
    gs.save_stats(p)
    # save_stats is performed on a background thread; wait briefly for it to complete
    import time
    timeout = 1.0
    waited = 0.0
    interval = 0.01
    while not p.exists() and waited < timeout:
        time.sleep(interval)
        waited += interval
    assert p.exists()
    data = json.loads(p.read_text(encoding='utf-8'))
    assert data["lifetime_stats"]["runs_started"] == 0
