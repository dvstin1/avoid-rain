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


def test_request_quit_flag():
    pm = PauseMenu()
    assert not pm.should_quit()
    pm.open()
    # Navigate to Quit and confirm
    pm.navigate('down')
    assert pm.get_selected_index() == 1
    pm.confirm()
    assert pm.should_quit()
    pm.clear_quit()
    assert not pm.should_quit()


def test_confirm_resume_closes_menu():
    pm = PauseMenu()
    pm.open()
    assert pm.is_open()
    # Confirm resume (default selected)
    pm.confirm()
    assert not pm.is_open()
