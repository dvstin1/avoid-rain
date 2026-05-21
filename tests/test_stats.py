import json
from pathlib import Path

import pytest

from engine.stats import StatisticsTracker


def test_increment_and_save(tmp_path):
    p = tmp_path / "profile_metrics.json"
    st = StatisticsTracker()
    st.increment("runs_started", 1)
    assert st.to_dict()["lifetime_stats"]["runs_started"] == 1
    st.save(p)
    data = json.loads(p.read_text())
    assert data["lifetime_stats"]["runs_started"] == 1


def test_load_existing(tmp_path):
    p = tmp_path / "profile_metrics.json"
    payload = {
        "lifetime_stats": {
            "runs_started": 5,
            "wins_chapters_cleared": 0,
            "losses_bleed_wipes": 0,
            "deaths_standard_respawns": 0,
            "forced_quit_outs": 0,
        },
        "discovered_bestiary": {"enemy_x": True},
    }
    p.write_text(json.dumps(payload))
    st = StatisticsTracker.load(p)
    assert st.to_dict()["lifetime_stats"]["runs_started"] == 5
    assert st.to_dict()["discovered_bestiary"]["enemy_x"] is True


def test_set_bestiary_and_toggle():
    st = StatisticsTracker()
    st.set_bestiary("enemy_a", True)
    assert st.to_dict()["discovered_bestiary"]["enemy_a"] is True
    st.set_bestiary("enemy_a", False)
    assert st.to_dict()["discovered_bestiary"]["enemy_a"] is False


def test_increment_unknown_key_raises():
    st = StatisticsTracker()
    with pytest.raises(KeyError):
        st.increment("unknown_stat")
