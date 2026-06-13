"""Tests for GameState auto-loading of a StatisticsTracker from disk.

This test writes a payload to a temporary path and constructs GameState with
stats_path pointing to that file to ensure GameState.load increments runs.
"""
import json
from pathlib import Path
from engine.game_state import GameState
from engine.stats import StatisticsTracker


def test_game_state_autoload_from_path(tmp_path):
    p = tmp_path / "profile_metrics.json"
    payload = {
        "lifetime_stats": {
            "runs_started": 2,
            "wins_chapters_cleared": 0,
            "losses_bleed_wipes": 0,
            "deaths_standard_respawns": 0,
            "forced_quit_outs": 0,
        },
        "discovered_bestiary": {}
    }
    p.write_text(json.dumps(payload))

    # Construct GameState with stats_path pointing to our temp file; auto_load True
    gs = GameState(stats=None, stats_path=str(p), auto_load=True)
    assert gs.stats is not None
    assert gs.stats.to_dict()["lifetime_stats"]["runs_started"] == 2


def test_game_state_does_not_auto_load_when_disabled(tmp_path):
    # When auto_load is False and no stats provided, GameState should have stats == None
    gs = GameState(stats=None, auto_load=False)
    assert gs.stats is None
