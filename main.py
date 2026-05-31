"""
Main entry point for Avoid Rain.
Handles the application lifecycle and top-level loops.
"""
import sys
import atexit
import pygame
from constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS, AUTOSAVE_INTERVAL,
    INPUT_MODE_GAMEPAD, INPUT_MODE_KEYBOARD, JOYSTICK_DEADZONE
)
from engine.game_state import GameState
from engine.pause_menu import PauseMenu
from engine.title_menu import TitleMenu, TitleMenuState
from engine.autosave import AutosaveManager
from engine.audio import AudioManager
from rendering.renderer import Renderer

# pylint: disable=no-member

def handle_title_events(state, renderer, title_menu: TitleMenu):
    """Handle events during the title screen with a menu controller and Auto Input Mode."""
    ratchet_reset = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False, False, False
        
        # Mode Switching Rule
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            state.input_mode = INPUT_MODE_KEYBOARD
        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION):
            state.input_mode = INPUT_MODE_GAMEPAD

        if event.type == pygame.JOYBUTTONDOWN:
            state.input_mode = INPUT_MODE_GAMEPAD
            if event.button == 0: title_menu.confirm() # Cross/A
            if event.button == 1: # Circle/B (Cancel)
                if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                    title_menu.state = TitleMenuState.MAIN
                elif getattr(title_menu.state, 'name', '') == 'CONTROLS':
                    title_menu.state = TitleMenuState.MAIN
        
        if event.type == pygame.JOYBUTTONUP:
            ratchet_reset = True

        if event.type == pygame.JOYHATMOTION:
            state.input_mode = INPUT_MODE_GAMEPAD
            if event.value[1] > 0: title_menu.navigate('up')
            if event.value[1] < 0: title_menu.navigate('down')

        if event.type == pygame.JOYAXISMOTION:
            if abs(event.value) > JOYSTICK_DEADZONE:
                state.input_mode = INPUT_MODE_GAMEPAD
                # Vertical Stick Navigation
                if event.axis == 1:
                    if not state.input_ratchet_latched:
                        if event.value > 0.8:
                            title_menu.navigate('down')
                            state.input_ratchet_latched = True
                        elif event.value < -0.8:
                            title_menu.navigate('up')
                            state.input_ratchet_latched = True
            elif event.axis == 1 and abs(event.value) < 0.1:
                ratchet_reset = True

        if event.type == pygame.KEYDOWN:
            # If we are in controls state, handle SPACE/ENTER/ESCAPE as 'back'
            if getattr(title_menu.state, 'name', '') == 'CONTROLS':
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    title_menu.state = TitleMenuState.MAIN
                return True, True, False

            # If we are in confirmation state, handle ESC as 'cancel'
            if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    title_menu.state = TitleMenuState.MAIN
                    return True, True, False
                if event.key == pygame.K_y:
                    title_menu.confirm()
                    return True, True, False
                return True, True, False

            if event.key == pygame.K_ESCAPE:
                return False, False, False
            # Navigation
            if event.key in (pygame.K_UP, pygame.K_w):
                title_menu.navigate('up')
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                title_menu.navigate('down')
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                # Confirm selection (main handles the resulting action)
                title_menu.confirm()
    return True, True, ratchet_reset

def handle_game_events(state, pause_menu: PauseMenu | None = None):
    """Handle events during the main game loop with Auto Input Mode switching."""
    running = True
    attack = False
    flask = False
    dash = False
    swap = False
    mouse_click = None
    ratchet_reset = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Mode Switching Rule: KEYBOARD
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            state.input_mode = INPUT_MODE_KEYBOARD
        # Mode Switching Rule: GAMEPAD
        if event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYHATMOTION:
            state.input_mode = INPUT_MODE_GAMEPAD
        if event.type == pygame.JOYAXISMOTION:
            if abs(event.value) > JOYSTICK_DEADZONE:
                state.input_mode = INPUT_MODE_GAMEPAD

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                mouse_click = event.pos
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                ratchet_reset = True
        
        # Controller Buttons
        if event.type == pygame.JOYBUTTONDOWN:
            state.input_mode = INPUT_MODE_GAMEPAD
            # Sony PS5 / Standard Mapping
            # 0: Cross, 1: Circle, 2: Square, 3: Triangle
            
            if pause_menu and pause_menu.is_open():
                if event.button == 0: # Confirm
                    if pause_menu.get_selected() == "Controls":
                        from engine.pause_menu import PauseMenuState
                        pause_menu.state = PauseMenuState.CONTROLS
                    else:
                        pause_menu.confirm()
                elif event.button == 1: # Back / Cancel
                    from engine.pause_menu import PauseMenuState
                    if getattr(pause_menu.state, 'name', '') == 'CONTROLS':
                        pause_menu.state = PauseMenuState.MAIN
                    else:
                        pause_menu.close()
            else:
                if event.button == 0: attack = True # Confirm/Swing
                if event.button == 1: dash = True   # Cancel/Dash
                if event.button == 3: flask = True  # Flask
                if event.button == 4: swap = True   # L1 Swap
                if event.button == 6: # Options/Share
                    if pause_menu: pause_menu.toggle()

        if event.type == pygame.JOYBUTTONUP:
            ratchet_reset = True
        
        # Gamepad Stick/Hat Navigation for Menus
        if event.type == pygame.JOYHATMOTION:
            state.input_mode = INPUT_MODE_GAMEPAD
            if pause_menu and pause_menu.is_open():
                if event.value[1] > 0: pause_menu.navigate('up')
                if event.value[1] < 0: pause_menu.navigate('down')

        if event.type == pygame.JOYAXISMOTION:
            if abs(event.value) > JOYSTICK_DEADZONE:
                state.input_mode = INPUT_MODE_GAMEPAD
                # Stick Menu Navigation (Vertical)
                if pause_menu and pause_menu.is_open() and event.axis == 1:
                    if not state.input_ratchet_latched:
                        if event.value > 0.8:
                            pause_menu.navigate('down')
                            state.input_ratchet_latched = True
                        elif event.value < -0.8:
                            pause_menu.navigate('up')
                            state.input_ratchet_latched = True
            elif event.axis == 1: # Centered
                # Optional: specific axis reset logic if needed
                pass

        if event.type == pygame.KEYUP:
            ratchet_reset = True
        
        if event.type == pygame.KEYDOWN:
            if pause_menu is not None and pause_menu.is_open() and getattr(pause_menu.state, 'name', '') == 'CONTROLS':
                from engine.pause_menu import PauseMenuState
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    pause_menu.state = PauseMenuState.MAIN
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
            if event.key == pygame.K_q:
                swap = True
            if event.key == pygame.K_LSHIFT:
                dash = True
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
    return running, attack, flask, dash, swap, mouse_click, ratchet_reset


def get_movement_actions(state):
    """Poll keyboard and joysticks for movement actions."""
    from constants import JOYSTICK_DEADZONE
    move_dir = [0.0, 0.0]
    
    # 1. Keyboard Polling
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]: move_dir[1] -= 1
    if keys[pygame.K_s]: move_dir[1] += 1
    if keys[pygame.K_a]: move_dir[0] -= 1
    if keys[pygame.K_d]: move_dir[0] += 1
    
    # 2. Gamepad Polling (If active)
    if pygame.joystick.get_count() > 0:
        joy = pygame.joystick.Joystick(0)
        # Left Stick (Axes 0 and 1)
        jx = joy.get_axis(0)
        jy = joy.get_axis(1)
        
        if abs(jx) > JOYSTICK_DEADZONE: move_dir[0] += jx
        if abs(jy) > JOYSTICK_DEADZONE: move_dir[1] += jy
        
        # D-Pad (Hat 0)
        hat = joy.get_hat(0)
        move_dir[0] += hat[0]
        move_dir[1] -= hat[1] # Hat Y is inverted (1 is up)

    # Normalize if exceeding 1.0 (combined inputs)
    mag = (move_dir[0]**2 + move_dir[1]**2)**0.5
    if mag > 1.0:
        move_dir[0] /= mag
        move_dir[1] /= mag
        
    return move_dir

def main():
    """Main application loop."""
    pygame.init()
    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        j.init()
        print(f"[INPUT] Detected Gamepad: {j.get_name()}")

    # Initialize Audio
    audio = AudioManager()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()

    renderer = Renderer(screen)

    # Defer auto-loading until we can present UI. Create GameState with auto_load=False first.
    provisional_state = GameState(stats=None, auto_load=False)
    # Now attempt to load stats with UI handling
    try:
        state = GameState(stats=None, stats_path=None, auto_load=True)
    except Exception:
        # Fall back to provisional if something unexpected happened
        state = provisional_state

    # Register exit handler for Hard Persistence
    def shutdown_handler():
        """Perfectly flush save data to the hard drive on any exit event."""
        try:
            if 'state' in locals() or 'state' in globals():
                # We need to access the active 'state' object
                target_state = state if 'state' in locals() else globals().get('state')
                if target_state and hasattr(target_state, 'save_stats'):
                    print("[SHUTDOWN] Executing final synchronous save flush...")
                    target_state.save_stats(wait=True)
                    if hasattr(target_state, 'shutdown_save_worker'):
                        target_state.shutdown_save_worker()
        except Exception:
            pass
    atexit.register(shutdown_handler)

    # If a corrupt save was detected during auto-load, present the user a choice
    if getattr(state, 'stats_corrupt', False):
        # Show loading screen explaining the issue and enforce minimum display
        msg = "Saved data appears corrupt. Start with new data? (Y/N)"
        renderer.draw_loading_screen("Save Corrupt", msg, min_t=2.0)
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

    # [DISK CHECK] Explicitly verify physical save file for Title Menu detection
    from engine.stats import DEFAULT_PATH
    import json
    import os
    has_physical_run = False
    if DEFAULT_PATH.exists():
        try:
            with open(DEFAULT_PATH, 'r', encoding='utf-8') as f:
                json.load(f)
                # Physical existence of save file is enough to allow Continue
                has_physical_run = True
        except Exception:
            pass

    title_menu = TitleMenu(has_save=has_physical_run)

    in_title = True
    running = True

    # [Lifecycle] Purge runtime memory while on the title screen
    state.deallocate()

    try:
        while running:
            dt = clock.tick(FPS) / 1000.0

            if in_title:
                in_title, running, ratchet_reset = handle_title_events(state, renderer, title_menu)
                # Pass the whole TitleMenu so the renderer can render dynamic options
                renderer.draw_title_screen(title_menu)
                
                # Update Music for Title Screen
                audio.update(dt, "title_theme.ogg")

                if ratchet_reset:
                    state.input_ratchet_latched = False

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

                    if selected == 'New Draft':
                        # If we just confirmed 'New Draft' from the prompt
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

                        # If a persistent run or profile exists, ask for confirmation
                        from engine.stats import DEFAULT_PATH
                        if DEFAULT_PATH.exists():
                            # Transition to confirmation state instead of blocking
                            title_menu.state = TitleMenuState.CONFIRM_NEW_GAME
                        else:
                            # No data exists: start fresh immediately
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
            else:
                ev_res = handle_game_events(state, pause_menu=pause_menu)
                running, attack, flask, dash, swap, mouse_click, ratchet_reset = ev_res
                
                if ratchet_reset:
                    state.input_ratchet_latched = False
                
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
                            from engine.stats import DEFAULT_PATH
                            has_run_now = DEFAULT_PATH.exists()
                            title_menu.set_has_save(has_run_now)
                        except Exception:
                            pass
                        # skip remaining game update work and continue loop
                        continue
                else:
                    actions = {
                        'move': get_movement_actions(state),
                        'attack': attack,
                        'flask': flask,
                        'dash': dash,
                        'swap': swap,
                        'mouse_click': mouse_click,
                        'ratchet_reset': ratchet_reset,
                        'block': pygame.key.get_pressed()[pygame.K_k],
                        'key_r': pygame.key.get_pressed()[pygame.K_r],
                        'key_1': pygame.key.get_pressed()[pygame.K_1],
                        'key_2': pygame.key.get_pressed()[pygame.K_2],
                        'key_3': pygame.key.get_pressed()[pygame.K_3]
                    }
                    
                    # Controller Analog/Secondary buttons
                    if state.input_mode == INPUT_MODE_GAMEPAD and pygame.joystick.get_count() > 0:
                        joy = pygame.joystick.Joystick(0)
                        # Map extra actions for Gamepad
                        if joy.get_button(2): actions['attack'] = True # Square/X
                        if joy.get_button(3): actions['flask'] = True  # Triangle/Y
                        if joy.get_button(7): actions['block'] = True  # R2/RT
                        if joy.get_button(1): actions['key_r'] = True  # Circle/B (Rest)
                    
                    state.update(dt, actions)
                    
                    # Update Music
                    audio.update(dt, state.player.active_track_name)

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
