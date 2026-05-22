"""
Main entry point for Avoid Rain.
Handles the application lifecycle and top-level loops.
"""
import sys
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS, AUTOSAVE_INTERVAL
from engine.game_state import GameState
from engine.pause_menu import PauseMenu
from engine.title_menu import TitleMenu
from rendering.renderer import Renderer
from engine.autosave import AutosaveManager

# pylint: disable=no-member

def handle_title_events(renderer, title_menu):
    """Handle events during the title screen with a menu controller.

    This function updates menu navigation and sets the confirm flag on the
    TitleMenu when the user presses confirm. It does not perform transition
    actions which are handled in the main loop where application state is
    available.
    """
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False, False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False, False
            # Navigation
            if event.key in (pygame.K_UP, pygame.K_w):
                title_menu.navigate('up')
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                title_menu.navigate('down')
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                # Confirm selection (main handles the resulting action)
                title_menu.confirm()
    return True, True

def handle_game_events(pause_menu: PauseMenu | None = None):
    """Handle events during the main game loop.

    If a PauseMenu is provided, ESC toggles the menu instead of exiting.
    """
    running = True
    attack = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if pause_menu is not None:
                    pause_menu.toggle()
                else:
                    running = False
            if event.key == pygame.K_SPACE:
                attack = True
            # When the pause menu is open, allow navigation and confirm via arrow keys and Enter
            if pause_menu is not None and pause_menu.is_open():
                if event.key in (pygame.K_UP, pygame.K_w):
                    pause_menu.navigate('up')
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    pause_menu.navigate('down')
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    pause_menu.confirm()
    return running, attack

def get_movement_actions():
    """Poll keyboard for movement actions."""
    move_dir = [0, 0]
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        move_dir[1] -= 1
    if keys[pygame.K_s]:
        move_dir[1] += 1
    if keys[pygame.K_a]:
        move_dir[0] -= 1
    if keys[pygame.K_d]:
        move_dir[0] += 1
    return move_dir

def main():
    """Main application loop."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    renderer = Renderer(screen)
    # Create a provisional GameState so we can handle corrupt-save dialogs during startup
    # Defer auto-loading until we can present UI. Create GameState with auto_load=False first.
    provisional_state = GameState(stats=None, auto_load=False)
    # Now attempt to load stats with UI handling
    try:
        state = GameState(stats=None, stats_path=None, auto_load=True)
    except Exception:
        # Fall back to provisional if something unexpected happened
        state = provisional_state

    # If a corrupt save was detected during auto-load, present the user a choice
    if getattr(state, 'stats_corrupt', False):
        # Show loading screen explaining the issue and enforce minimum display
        msg = "Saved data appears corrupt. Start with new data? (Y/N)"
        renderer.draw_loading_screen("Save Corrupt", msg, min_time=2.0)
        # Wait for user to press Y or N
        waiting_choice = True
        choice = None
        while waiting_choice:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_y:
                        choice = 'y'
                        waiting_choice = False
                    elif event.key == pygame.K_n:
                        choice = 'n'
                        waiting_choice = False
            # small delay to avoid busy loop
            pygame.time.delay(10)
        if choice == 'y':
            # Start fresh data
            state.handle_corrupt_choice(start_new=True)
            # Immediately persist the fresh tracker
            state.save_stats()
        else:
            # User chose not to start new data: go to title instead
            in_title = True
            state = provisional_state

    # Autosave manager runs during the game loop and triggers periodic saves
    autosave = AutosaveManager(AUTOSAVE_INTERVAL)
    # PauseMenu will auto-save on open via a lightweight callback
    pause_menu = PauseMenu(on_open=lambda: state.save_stats())
    # Title menu should reflect whether a valid save exists
    has_save = getattr(state, 'stats', None) is not None and not getattr(state, 'stats_corrupt', False)
    title_menu = TitleMenu(has_save=has_save)

    in_title = True
    running = True

    try:
        while running:
            if in_title:
                in_title, running = handle_title_events(renderer, title_menu)
                renderer.draw_title_screen(title_menu.get_selected_index())
                # If the user confirmed a title selection, handle it here where we have access to `state`.
                if title_menu.was_confirmed():
                    selected = title_menu.get_selected()
                    title_menu.clear_confirm()

                    if selected == 'Continue':
                        # Start the game normally
                        renderer.fade_to_black()
                        in_title = False
                        # ensure camera centers on player immediately
                        if hasattr(state, 'camera'):
                            state.camera.instant_center(state.player.get_center())
                        continue

                    if selected == 'New Game':
                        # If valid save data exists, ask for confirmation because this
                        # will replace/erase previous save data. If no save exists,
                        # just start a new game.
                        has_save = getattr(state, 'stats', None) is not None
                        if has_save:
                            # Show confirmation screen and require Y/N
                            renderer.draw_loading_screen('Confirm New Game', 'This will permanently remove old save data. Press Y to confirm, N to cancel', min_time=2.0)
                            waiting = True
                            choice = None
                            while waiting:
                                for ev in pygame.event.get():
                                    if ev.type == pygame.QUIT:
                                        pygame.quit()
                                        sys.exit()
                                    if ev.type == pygame.KEYDOWN:
                                        if ev.key == pygame.K_y:
                                            choice = 'y'
                                            waiting = False
                                        elif ev.key == pygame.K_n:
                                            choice = 'n'
                                            waiting = False
                                pygame.time.delay(10)
                            if choice == 'y':
                                # Replace with fresh stats and persist immediately
                                try:
                                    from engine.stats import DEFAULT_PATH, StatisticsTracker
                                    # Remove existing save file if present
                                    try:
                                        import os
                                        if DEFAULT_PATH.exists():
                                            DEFAULT_PATH.unlink()
                                    except Exception:
                                        pass
                                    state.stats = StatisticsTracker()
                                    try:
                                        state.stats.increment('runs_started', 1)
                                    except Exception:
                                        pass
                                    state.save_stats()
                                except Exception:
                                    pass
                                renderer.fade_to_black()
                                in_title = False
                                if hasattr(state, 'camera'):
                                    state.camera.instant_center(state.player.get_center())
                                continue
                            else:
                                # Cancel new game; remain on title
                                pass
                        else:
                            # No save exists: start immediately
                            try:
                                from engine.stats import StatisticsTracker
                                state.stats = StatisticsTracker()
                                try:
                                    state.stats.increment('runs_started', 1)
                                except Exception:
                                    pass
                                state.save_stats()
                            except Exception:
                                pass
                            renderer.fade_to_black()
                            in_title = False
                            if hasattr(state, 'camera'):
                                state.camera.instant_center(state.player.get_center())
                            continue

                    if selected == 'Quit':
                        running = False
                clock.tick(FPS)
            else:
                dt = clock.tick(FPS) / 1000.0
                running, attack = handle_game_events(pause_menu=pause_menu)
                if pause_menu.is_open():
                    # When paused, draw the pause menu and skip updates
                    renderer.draw_pause_menu(pause_menu.get_selected_index())
                    # If the user confirmed 'Quit' in the pause menu, exit the loop
                    if pause_menu.should_quit():
                        # Auto-save before transitioning back to title screen
                        try:
                            state.save_stats()
                        except Exception:
                            pass
                        # Transition back to the title screen instead of exiting the app
                        pause_menu.clear_quit()
                        pause_menu.close()
                        in_title = True
                        # Update title menu to reflect whether a save now exists
                        try:
                            has_save_now = getattr(state, 'stats', None) is not None and not getattr(state, 'stats_corrupt', False)
                            title_menu.set_has_save(has_save_now)
                        except Exception:
                            pass
                        # skip remaining game update work and continue loop
                        continue
                else:
                    actions = {
                        'move': get_movement_actions(),
                        'attack': attack
                    }
                    state.update(dt, actions)
                    # Run the autosave manager each frame (will be tolerant if no stats)
                    try:
                        autosave.update(dt, state)
                    except Exception:
                        pass
                    renderer.render(state)

    except Exception as exc:
        print(f"An error occurred: {exc}")
        raise exc
    finally:
        # Ensure game stats are saved automatically on exit if available
        try:
            if 'state' in locals() and getattr(state, 'save_stats', None) is not None:
                state.save_stats()
            # Shutdown save worker to flush pending saves
            if 'state' in locals() and getattr(state, 'shutdown_save_worker', None) is not None:
                state.shutdown_save_worker()
        except Exception:
            pass
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
