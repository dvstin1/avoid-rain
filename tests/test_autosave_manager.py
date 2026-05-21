"""Unit tests for the AutosaveManager."""

from engine.autosave import AutosaveManager
from engine.game_state import GameState


class FakeStats:
    def __init__(self):
        self.saved = 0
    def save(self, path=None):
        self.saved += 1

    def save_stats(self, *args, **kwargs):
        # Older code path protection; not expected to be used
        self.save(*args, **kwargs)


class FakeState(GameState):
    def __init__(self):
        super().__init__(stats=None, auto_load=False)
        self.stats = FakeStats()
    def save_stats(self, path=None):
        # Delegate to underlying stats for verification
        self.stats.save(path)


def test_autosave_triggers_save_and_resets_timer():
    s = FakeState()
    manager = AutosaveManager(interval=1.0)
    # initial last_save_elapsed is large
    assert s.last_save_elapsed > 1000
    # simulate frames adding up to >1.0s
    manager.update(0.4, s)
    manager.update(0.4, s)
    # not yet saved
    assert s.stats.saved == 0
    manager.update(0.3, s)
    # saved once and timer reset
    assert s.stats.saved == 1
    assert s.last_save_elapsed == 0.0
