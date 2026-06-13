import pytest
from engine.title_menu import TitleMenu

def test_navigation_and_confirm():
    # Options: ["New Draft", "Join Game", "Controls", "Quit"] (has_save=False)
    tm = TitleMenu(has_save=False)
    assert tm.get_selected_index() == 0
    tm.navigate('down')
    assert tm.get_selected_index() == 1
    tm.navigate('down')
    assert tm.get_selected_index() == 2
    tm.navigate('down')
    assert tm.get_selected_index() == 3
    tm.navigate('down')
    assert tm.get_selected_index() == 0

def test_confirm_state():
    tm = TitleMenu()
    assert not tm.was_confirmed()
    tm.confirm()
    assert tm.was_confirmed()
    tm.clear_confirm()
    assert not tm.was_confirmed()
