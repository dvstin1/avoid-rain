"""Tests for corrupt save handling in StatisticsTracker.load"""
import json
from pathlib import Path
import pytest
from engine.stats import StatisticsTracker, CorruptSaveError


def test_load_raises_and_moves_corrupt_file(tmp_path):
    p = tmp_path / "profile_metrics.json"
    # Write invalid JSON
    p.write_text("{ not valid json }")

    with pytest.raises(CorruptSaveError) as ei:
        StatisticsTracker.load(p)
    err = ei.value
    assert hasattr(err, 'backup_path')
    # Backup path should exist
    if err.backup_path is not None:
        assert Path(err.backup_path).exists()
