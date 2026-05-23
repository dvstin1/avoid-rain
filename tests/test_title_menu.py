from engine.title_menu import TitleMenu, TitleMenuState


def test_navigation_and_confirm():
    tm = TitleMenu()
    assert tm.get_selected_index() == 0
    tm.navigate('down')
    assert tm.get_selected_index() == 1
    tm.navigate('down')
    assert tm.get_selected_index() == 2
    tm.navigate('down')
    assert tm.get_selected_index() == 0
    tm.navigate('up')
    assert tm.get_selected_index() == 2
    assert not tm.was_confirmed()
    tm.confirm()
    assert tm.was_confirmed()
    tm.clear_confirm()
    assert not tm.was_confirmed()


def test_title_menu_states():
    tm = TitleMenu()
    assert tm.state == TitleMenuState.MAIN
    tm.state = TitleMenuState.CONFIRM_NEW_GAME
    assert tm.state == TitleMenuState.CONFIRM_NEW_GAME
    
    # Test that set_has_save preserves state
    tm.set_has_save(True)
    assert tm.state == TitleMenuState.CONFIRM_NEW_GAME
    
    # Test reset to MAIN
    tm.state = TitleMenuState.MAIN
    assert tm.state == TitleMenuState.MAIN
