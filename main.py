"""
Main entry point for Avoid Rain.
Handles the application lifecycle and top-level loops.
"""
import sys
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS, AUTOSAVE_INTERVAL
from engine.game_state import GameState
from engine.pause_menu import PauseMenu
from engine.title_menu import TitleMenu, TitleMenuState
from engine.autosave import AutosaveManager
from rendering.renderer import Renderer

# pylint: disable=no-member

def handle_title_events(renderer, title_menu: TitleMenu):
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
            # If we are in controls state, handle SPACE/ENTER/ESCAPE as 'back'
            if getattr(title_menu.state, 'name', '') == 'CONTROLS':
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    title_menu.state = TitleMenuState.MAIN
                return True, True

            # If we are in confirmation state, handle ESC as 'cancel'
            if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    title_menu.state = TitleMenuState.MAIN
                    return True, True
                if event.key == pygame.K_y:
                    title_menu.confirm()
                    return True, True
                return True, True

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
    flask = False
    dash = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            # If we are in controls state in the pause menu, SPACE/ENTER/ESCAPE returns to MAIN
            if pause_menu is not None and pause_menu.is_open() and getattr(pause_menu.state, 'name', '') == 'CONTROLS':
                from engine.pause_menu import PauseMenuState
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    pause_menu.state = PauseMenuState.MAIN
                # Swallow all other keys while in controls modal
                continue

            if event.key == pygame.K_ESCAPE:
                if pause_menu is not None:
                    pause_menu.toggle()
                else:
                    running = False
            if event.key == pygame.K_SPACE:
                attack = True
            if event.key == pygame.K_1:
                flask = True
            if event.key == pygame.K_LSHIFT:
                dash = True
            # When the pause menu is open, allow navigation and confirm via arrow keys and Enter
            if pause_menu is not None and pause_menu.is_open():
                if event.key in (pygame.K_UP, pygame.K_w):
                    pause_menu.navigate('up')
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    pause_menu.navigate('down')
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if pause_menu.get_selected() == "Controls":
                        from engine.pause_menu import PauseMenuState
                        pause_menu.state = PauseMenuState.CONTROLS
                    else:
                        pause_menu.confirm()
    return running, attack, flask, dash


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
    # Title menu should reflect whether a resume-able save exists
    has_run = (getattr(state, 'stats', None) is not None and 
               state.stats.data.get("run_state") is not None)
    title_menu = TitleMenu(has_save=has_run)

    in_title = True
    running = True

    # [Lifecycle] Purge runtime memory while on the title screen
    state.deallocate()

    try:
        while running:
            if in_title:
                in_title, running = handle_title_events(renderer, title_menu)
                # Pass the whole TitleMenu so the renderer can render dynamic options
                renderer.draw_title_screen(title_menu)
                # If the user confirmed a title selection, handle it here
                if title_menu.was_confirmed():
                    selected = title_menu.get_selected()
                    title_menu.clear_confirm()

                    if selected == 'Continue':
                        # [Lifecycle] Re-hydrate clean player and environment session from disk file
                        renderer.fade_to_black()
                        try:
                            state.hydrate_from_disk()
                        except Exception as exc:
                            print(f"[ERROR] Failed to hydrate state: {exc}")
                            # fallback if hydration fails for some reason
                            state.reset_to_new_game()
                        
                        in_title = False
                        continue

                    if selected == 'New Game':
                        # If we just confirmed 'New Game' from the prompt
                        if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                            # User pressed Y (confirmed in handle_title_events)
                            try:
                                state.reset_to_new_game()
                                state.save_stats(wait=True)
                            except Exception:
                                pass
                            renderer.fade_to_black()
                            title_menu.state = TitleMenuState.MAIN
                            in_title = False
                            continue
                        
                        # If a persistent run exists, ask for confirmation
                        has_run = (getattr(state, 'stats', None) is not None and 
                                   state.stats.data.get("run_state") is not None)
                        if has_run:
                            # Transition to confirmation state instead of blocking
                            title_menu.state = TitleMenuState.CONFIRM_NEW_GAME
                        else:
                            # No run exists: start fresh immediately
                            try:
                                state.reset_to_new_game()
                                state.save_stats(wait=True) # Synchronous flush for first-run
                            except Exception:
                                pass
                            renderer.fade_to_black()
                            in_title = False
                            continue

                    if selected == 'Controls':
                        title_menu.state = TitleMenuState.CONTROLS
                        continue

                    if selected == 'Quit':
                        running = False
                clock.tick(FPS)
            else:
                dt = clock.tick(FPS) / 1000.0
                running, attack, flask, dash = handle_game_events(pause_menu=pause_menu)
                if pause_menu.is_open():
                    # When paused, draw the pause menu and skip updates
                    renderer.draw_pause_menu(pause_menu)
                    # If the user confirmed 'Quit' in the pause menu, exit the loop
                    if pause_menu.should_quit():
                        # [Milestone] Auto-save synchronously before transitioning
                        try:
                            state.save_stats(wait=True)
                        except Exception:
                            pass
                        # Transition back to the title screen instead of exiting the app
                        pause_menu.clear_quit()
                        pause_menu.close()
                        in_title = True
                        
                        # [Lifecycle] Purge all runtime gameplay memory
                        state.deallocate()
                        
                        # Update title menu
                        try:
                            has_run_now = (getattr(state, 'stats', None) is not None and 
                                           state.stats.data.get("run_state") is not None)
                            title_menu.set_has_save(has_run_now)
                        except Exception:
                            pass
                        # skip remaining game update work and continue loop
                        continue
                else:
                    actions = {
                        'move': get_movement_actions(),
                        'attack': attack,
                        'flask': flask,
                        'dash': dash,
                        'block': pygame.key.get_pressed()[pygame.K_k]
                    }
                    state.update(dt, actions)

                    # Run the autosave manager each frame
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
                state.save_stats(wait=True) # Synchronous flush on exit
            # Shutdown save worker to flush pending saves
            if 'state' in locals() and getattr(state, 'shutdown_save_worker', None) is not None:
                state.shutdown_save_worker()
        except Exception:
            pass
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
