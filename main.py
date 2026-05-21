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
    """Handle events during the title screen with a menu controller."""
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
                # Confirm selection
                title_menu.confirm()
                selected = title_menu.get_selected()
                if selected == 'Start':
                    renderer.fade_to_black()
                    title_menu.clear_confirm()
                    return False, True
                if selected == 'Quit':
                    return False, False
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
    title_menu = TitleMenu()

    in_title = True
    running = True

    try:
        while running:
            if in_title:
                in_title, running = handle_title_events(renderer, title_menu)
                renderer.draw_title_screen(title_menu.get_selected_index())
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
        except Exception:
            pass
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
