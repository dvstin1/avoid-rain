"""Tests for TitleMenu options when save exists or not."""
from engine.title_menu import TitleMenu


def test_title_menu_without_save():
    tm = TitleMenu(has_save=False)
    assert tm.get_options() == ["New Game", "Quit"]
    assert tm.get_selected_index() == 0


def test_title_menu_with_save():
    tm = TitleMenu(has_save=True)
    assert tm.get_options() == ["New Game", "Continue", "Quit"]
    assert tm.get_selected_index() == 1
