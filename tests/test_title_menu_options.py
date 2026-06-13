import pytest
from engine.title_menu import TitleMenu

def test_title_menu_without_save():
    tm = TitleMenu(has_save=False)
    assert tm.get_options() == ["New Draft", "Join Game", "Controls", "Quit"]
    assert tm.get_selected_index() == 0

def test_title_menu_with_save():
    tm = TitleMenu(has_save=True)
    assert tm.get_options() == ["New Draft", "Continue", "Join Game", "Controls", "Quit"]
    # Selection should default to Continue
    assert tm.get_selected_index() == 1

def test_title_menu_save_toggle():
    tm = TitleMenu(has_save=False)
    assert "Continue" not in tm.get_options()
    
    tm.set_has_save(True)
    assert "Continue" in tm.get_options()
    assert tm.get_selected_index() == 1
    
    tm.set_has_save(False)
    assert "Continue" not in tm.get_options()
    assert tm.get_selected_index() == 0
