"""
Main entry point for Avoid Rain.
Handles the application lifecycle and top-level loops.
"""
import sys
import atexit
import argparse
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

def handle_title_events(state, renderer, title_menu: TitleMenu, audio_manager: AudioManager = None):
    """Handle events during the title screen with Auto Input Mode and Ratcheted Navigation."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False, False, False
        
        # Mode Switching Rules
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            state.input_mode = INPUT_MODE_KEYBOARD
        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
            state.input_mode = INPUT_MODE_GAMEPAD

        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0: title_menu.confirm() # Cross/A
            if event.button == 1: # Circle/B (Cancel)
                if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                    title_menu.state = TitleMenuState.MAIN
                elif getattr(title_menu.state, 'name', '') == 'CONTROLS':
                    title_menu.state = TitleMenuState.MAIN
        
        if event.type == pygame.KEYDOWN:
            if getattr(title_menu.state, 'name', '') == 'CONTROLS':
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    title_menu.state = TitleMenuState.MAIN
                return True, True, False

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
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                title_menu.confirm()

    # --- Unified Navigation Polling (Title) ---
    move_dir = get_movement_actions(state)
    ratchet_reset = False
    
    # Targeted Neutral Check: Only check vertical navigation axis
    keys = pygame.key.get_pressed()
    kb_v_neutral = not any([keys[pygame.K_w], keys[pygame.K_s], keys[pygame.K_UP], keys[pygame.K_DOWN]])
    
    gp_v_neutral = True
    if pygame.joystick.get_count() > 0:
        joy = pygame.joystick.Joystick(0)
        # Hysteresis Reset: Must return to 0.3 or less to unlatch
        if abs(joy.get_axis(1)) > 0.3 or joy.get_hat(0)[1] != 0:
            gp_v_neutral = False

    if kb_v_neutral and gp_v_neutral:
        ratchet_reset = True
    else:
        # Process Navigation if not latched and not on cooldown
        if not state.input_ratchet_latched and state.menu_nav_cooldown <= 0:
            if move_dir[1] > 0.6: # Deliberate push to move
                title_menu.navigate('down')
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")
            elif move_dir[1] < -0.6:
                title_menu.navigate('up')
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")

        
    return True, True, ratchet_reset

def handle_game_events(state, pause_menu: PauseMenu | None = None, audio_manager: AudioManager = None):
    """Handle events during the main game loop with Auto Input Mode and Ratcheted Navigation."""
    running = True
    attack = False
    flask = False
    dash = False
    swap = False
    mouse_click = None
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Mode Switching Rules
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            state.input_mode = INPUT_MODE_KEYBOARD
        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYAXISMOTION, pygame.JOYHATMOTION):
            state.input_mode = INPUT_MODE_GAMEPAD

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: mouse_click = event.pos
        
        # Controller Buttons
        if event.type == pygame.JOYBUTTONDOWN:
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

        if event.type == pygame.KEYDOWN:
            if pause_menu is not None and pause_menu.is_open() and getattr(pause_menu.state, 'name', '') == 'CONTROLS':
                from engine.pause_menu import PauseMenuState
                if event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    pause_menu.state = PauseMenuState.MAIN
                continue

            if event.key == pygame.K_ESCAPE:
                if pause_menu is not None: pause_menu.toggle()
                else: running = False
            if event.key == pygame.K_SPACE: attack = True
            if event.key == pygame.K_1: flask = True
            if event.key == pygame.K_q: swap = True
            if event.key == pygame.K_LSHIFT: dash = True
            if pause_menu is not None and pause_menu.is_open():
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if pause_menu.get_selected() == "Controls":
                        from engine.pause_menu import PauseMenuState
                        pause_menu.state = PauseMenuState.CONTROLS
                    else: pause_menu.confirm()

    # --- Unified Navigation Polling (Game/Pause) ---
    move_dir = get_movement_actions(state)
    ratchet_reset = False
    
    # Targeted Neutral Check: Only check vertical navigation axis
    keys = pygame.key.get_pressed()
    kb_v_neutral = not any([keys[pygame.K_w], keys[pygame.K_s], keys[pygame.K_UP], keys[pygame.K_DOWN]])
    
    gp_v_neutral = True
    if pygame.joystick.get_count() > 0:
        joy = pygame.joystick.Joystick(0)
        # Hysteresis Reset: Must return to 0.3 or less to unlatch
        if abs(joy.get_axis(1)) > 0.3 or joy.get_hat(0)[1] != 0:
            gp_v_neutral = False

    if kb_v_neutral and gp_v_neutral:
        ratchet_reset = True
    else:
        # Process Navigation if not latched and not on cooldown
        # ONLY if the pause menu is actually open!
        if pause_menu and pause_menu.is_open() and not state.input_ratchet_latched and state.menu_nav_cooldown <= 0:
            if move_dir[1] > 0.6: # Deliberate push to move
                pause_menu.navigate('down')
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")
            elif move_dir[1] < -0.6:
                pause_menu.navigate('up')
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")


    return running, attack, flask, dash, swap, mouse_click, ratchet_reset

def get_movement_actions(state):
    """Poll keyboard and joysticks for movement actions."""
    move_dir = [0.0, 0.0]
    
    # 1. Keyboard Polling
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w] or keys[pygame.K_UP]: move_dir[1] -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]: move_dir[1] += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]: move_dir[0] -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]: move_dir[0] += 1
    
    # 2. Gamepad Polling (If active)
    if pygame.joystick.get_count() > 0:
        joy = pygame.joystick.Joystick(0)
        jx = joy.get_axis(0)
        jy = joy.get_axis(1)
        if abs(jx) > JOYSTICK_DEADZONE: move_dir[0] += jx
        if abs(jy) > JOYSTICK_DEADZONE: move_dir[1] += jy
        hat = joy.get_hat(0)
        move_dir[0] += hat[0]
        move_dir[1] -= hat[1]

    # Normalize
    mag = (move_dir[0]**2 + move_dir[1]**2)**0.5
    if mag > 1.0:
        move_dir[0] /= mag
        move_dir[1] /= mag
    return move_dir

def main():
    """Main application loop."""
    parser = argparse.ArgumentParser(description="Avoid Rain")
    parser.add_argument("--fullscreen", action="store_true", help="Run in fullscreen mode")
    args = parser.parse_args()

    pygame.init()
    pygame.joystick.init()
    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        j.init()
        print(f"[INPUT] Detected Gamepad: {j.get_name()}")

    audio = AudioManager()
    
    if args.fullscreen:
        # Pygame 2.0+ SCALED flag handles aspect ratio and padding automatically
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        print(f"[DISPLAY] Initializing Fullscreen SCALED to native resolution")
    else:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    renderer = Renderer(screen)

    provisional_state = GameState(stats=None, auto_load=False)
    try:
        state = GameState(stats=None, stats_path=None, auto_load=True)
    except Exception:
        state = provisional_state

    def shutdown_handler():
        try:
            if 'state' in locals() and getattr(state, 'save_stats', None) is not None:
                state.save_stats(wait=True)
            if 'state' in locals() and getattr(state, 'shutdown_save_worker', None) is not None:
                state.shutdown_save_worker()
        except Exception: pass
        pygame.quit()

    atexit.register(shutdown_handler)
    pause_menu = PauseMenu()
    
    # [Initialization] Detect existing save file to enable 'Continue'
    from engine.stats import DEFAULT_PATH
    title_menu = TitleMenu(has_save=DEFAULT_PATH.exists())
    
    in_title = True
    running = True

    try:
        while running:
            dt = clock.tick(FPS) / 1000.0
            
            # Universal Cooldown Decrement
            if state.menu_nav_cooldown > 0:
                state.menu_nav_cooldown -= dt

            if in_title:
                in_title, running, ratchet_reset = handle_title_events(state, renderer, title_menu, audio_manager=audio)
                renderer.draw_title_screen(title_menu)
                audio.update(dt, "title_theme.ogg")
                if ratchet_reset: state.input_ratchet_latched = False
                
                if title_menu.was_confirmed():
                    selected = title_menu.get_selected()
                    title_menu.clear_confirm()
                    audio.play_sfx("menu_confirm.ogg")
                    if selected == 'Continue':
                        audio.play_sfx("warp_trigger.ogg")
                        renderer.fade_to_black()
                        try: state.hydrate_from_disk()
                        except Exception: state.reset_to_new_game()
                        in_title = False
                        continue
                    if selected == 'New Draft':
                        if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                            audio.play_sfx("warp_trigger.ogg")
                            try: state.reset_to_new_game(); state.save_stats(wait=True)
                            except Exception: pass
                            renderer.fade_to_black()
                            title_menu.state = TitleMenuState.MAIN
                            in_title = False
                            continue
                        from engine.stats import DEFAULT_PATH
                        if DEFAULT_PATH.exists(): title_menu.state = TitleMenuState.CONFIRM_NEW_GAME
                        else:
                            try: state.reset_to_new_game(); state.save_stats(wait=True)
                            except Exception: pass
                            renderer.fade_to_black()
                            in_title = False
                            continue
                    if selected == 'Controls':
                        title_menu.state = TitleMenuState.CONTROLS
                        continue
                    if selected == 'Quit': running = False
            else:
                ev_res = handle_game_events(state, pause_menu=pause_menu, audio_manager=audio)
                running, attack, flask, dash, swap, mouse_click, ratchet_reset = ev_res
                if ratchet_reset: state.input_ratchet_latched = False
                
                if pause_menu.is_open():
                    renderer.draw_pause_menu(pause_menu)
                    if pause_menu.should_quit():
                        try: state.save_stats(wait=True)
                        except Exception: pass
                        pause_menu.clear_quit(); pause_menu.close(); in_title = True
                        state.deallocate()
                        try:
                            from engine.stats import DEFAULT_PATH
                            title_menu.set_has_save(DEFAULT_PATH.exists())
                        except Exception: pass
                        continue
                else:
                    actions = {
                        'move': get_movement_actions(state),
                        'attack': attack, 'flask': flask, 'dash': dash, 'swap': swap,
                        'mouse_click': mouse_click, 'ratchet_reset': ratchet_reset,
                        'block': pygame.key.get_pressed()[pygame.K_k],
                        'key_r': pygame.key.get_pressed()[pygame.K_r],
                        'key_1': pygame.key.get_pressed()[pygame.K_1],
                        'key_2': pygame.key.get_pressed()[pygame.K_2],
                        'key_3': pygame.key.get_pressed()[pygame.K_3]
                    }
                    if state.input_mode == INPUT_MODE_GAMEPAD and pygame.joystick.get_count() > 0:
                        joy = pygame.joystick.Joystick(0)
                        if joy.get_button(2): actions['attack'] = True
                        if joy.get_button(3): actions['flask'] = True
                        if joy.get_button(7): actions['block'] = True
                        if joy.get_button(1): actions['key_r'] = True
                    
                    state.update(dt, actions, audio_manager=audio)
                    audio.update(dt, state.player.active_track_name)
                    try: autosave.update(dt, state)
                    except Exception: pass
                    renderer.render(state, audio_manager=audio)

    except Exception as exc:
        print(f"An error occurred: {exc}")
        raise exc
    finally:
        shutdown_handler()

if __name__ == "__main__":
    main()
