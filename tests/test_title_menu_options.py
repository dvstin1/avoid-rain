import pytest
from engine.title_menu import TitleMenu

def test_title_menu_without_save():
    tm = TitleMenu(has_save=False)
    assert tm.get_options() == ["New Draft", "Mode: Online", "Controls", "Quit"]
    assert tm.get_selected_index() == 0

def test_title_menu_with_save():
    tm = TitleMenu(has_save=True)
    assert tm.get_options() == ["New Draft", "Continue", "Mode: Online", "Controls", "Quit"]
    # Selection should default to Continue
    assert tm.get_selected_index() == 1

def test_title_menu_online_mode_toggle():
    tm = TitleMenu(has_save=False, online_mode=True)
    assert "Mode: Online" in tm.get_options()
    assert tm.toggle_online_mode() is False
    assert tm.online_mode is False
    assert tm.get_options() == ["New Draft", "Mode: Offline", "Controls", "Quit"]
    assert tm.toggle_online_mode() is True
    assert tm.online_mode is True
    assert tm.get_options() == ["New Draft", "Mode: Online", "Controls", "Quit"]

def test_title_menu_save_toggle():
    tm = TitleMenu(has_save=False)
    assert "Continue" not in tm.get_options()
    
    tm.set_has_save(True)
    assert "Continue" in tm.get_options()
    assert tm.get_selected_index() == 1
    
    tm.set_has_save(False)
    assert "Continue" not in tm.get_options()
    assert tm.get_selected_index() == 0
