from engine.title_menu import TitleMenu


def test_navigation_and_confirm():
    tm = TitleMenu()
    assert tm.get_selected_index() == 0
    tm.navigate('down')
    assert tm.get_selected_index() == 1
    tm.navigate('down')
    assert tm.get_selected_index() == 0
    tm.navigate('up')
    assert tm.get_selected_index() == 1
    assert not tm.was_confirmed()
    tm.confirm()
    assert tm.was_confirmed()
    tm.clear_confirm()
    assert not tm.was_confirmed()
