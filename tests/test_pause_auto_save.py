"""Tests that PauseMenu's on_open hook is invoked and can be used for autosave."""

from engine.pause_menu import PauseMenu


def test_pause_menu_calls_on_open():
    called = []
    pm = PauseMenu(on_open=lambda: called.append(True))
    assert not pm.is_open()
    pm.open()
    assert pm.is_open()
    assert called == [True]


def test_pause_menu_open_does_not_raise_if_hook_raises():
    def bad_hook():
        raise RuntimeError("boom")
    pm = PauseMenu(on_open=bad_hook)
    # Opening should not raise despite the hook failing
    pm.open()
    assert pm.is_open()
