import pytest

from engine.pause import PauseHandler


def test_default_unpaused():
    ph = PauseHandler()
    assert ph.is_paused() is False
    assert ph.should_update() is True


def test_pause_and_resume():
    ph = PauseHandler()
    ph.pause()
    assert ph.is_paused() is True
    assert ph.should_update() is False
    ph.resume()
    assert ph.is_paused() is False


def test_toggle():
    ph = PauseHandler()
    ph.toggle()
    assert ph.is_paused() is True
    ph.toggle()
    assert ph.is_paused() is False


def test_temporary_pause_context_manager():
    ph = PauseHandler()
    assert not ph.is_paused()
    with ph.temporary_pause():
        assert ph.is_paused()
    assert not ph.is_paused()


def test_context_manager_restores_previous_state():
    ph = PauseHandler()
    ph.pause()
    assert ph.is_paused()
    with ph.temporary_pause():
        assert ph.is_paused()
    # previous paused state should be restored
    assert ph.is_paused()
