from engine.pause import PauseHandler
from engine.pause_menu import PauseMenu


def test_open_close_and_toggle():
    ph = PauseHandler()
    pm = PauseMenu(ph)
    assert not pm.is_open()
    pm.open()
    assert pm.is_open()
    assert ph.is_paused()
    pm.close()
    assert not pm.is_open()
    assert not ph.is_paused()
    # toggle
    pm.toggle()
    assert pm.is_open()
    pm.toggle()
    assert not pm.is_open()


def test_default_pause_handler_created():
    pm = PauseMenu()
    assert not pm.is_open()
    pm.open()
    assert pm.is_open()
    assert pm.pause_handler.is_paused()
    pm.close()
    assert not pm.pause_handler.is_paused()
