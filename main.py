# copyright 2026 Dustin Massop, License: GPLv2
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
    INPUT_MODE_GAMEPAD, INPUT_MODE_KEYBOARD, JOYSTICK_DEADZONE,
    DEFAULT_KEYBINDINGS,
)
from engine.game_state import GameState
from engine.pause_menu import PauseMenu
from engine.title_menu import TitleMenu, TitleMenuState
from engine.autosave import AutosaveManager
from engine.audio import AudioManager
from rendering.renderer import Renderer
from ui.menu import ControlsConfigMenu

# pylint: disable=no-member,too-many-locals,too-many-branches,too-many-statements,broad-exception-caught
# pylint: disable=multiple-statements,import-outside-toplevel,trailing-whitespace,line-too-long
# pylint: disable=unused-import,unused-argument,redefined-outer-name,reimported


def _get_keybindings(state) -> dict:
    """Return the active action -> pygame key code map for state, falling back to DEFAULT_KEYBINDINGS."""
    raw = getattr(state, "keybindings", None) if state is not None else None
    if isinstance(raw, dict):
        return {k: raw.get(k, v) for k, v in DEFAULT_KEYBINDINGS.items()}
    return dict(DEFAULT_KEYBINDINGS)


def _handle_controls_keydown(event_key, state, controls_menu: ControlsConfigMenu, audio_manager=None) -> bool:
    """Process a KEYDOWN event inside ControlsConfigMenu. Returns True if user exits back to parent menu."""
    if controls_menu.listening_for_key:
        res = controls_menu.capture_key(event_key, state)
        if audio_manager and res == "BOUND":
            audio_manager.play_sfx("menu_confirm.ogg")
        return False

    kb = _get_keybindings(state)
    if event_key == pygame.K_ESCAPE:
        return controls_menu.cancel() == "BACK"
    if event_key in (pygame.K_UP, kb["move_up"]):
        controls_menu.navigate(-1)
        if audio_manager:
            audio_manager.play_sfx("menu_navigate.ogg")
        return False
    if event_key in (pygame.K_DOWN, kb["move_down"]):
        controls_menu.navigate(1)
        if audio_manager:
            audio_manager.play_sfx("menu_navigate.ogg")
        return False
    if event_key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        res = controls_menu.confirm(state)
        if audio_manager and res in ("LISTENING", "RESET", "BACK"):
            audio_manager.play_sfx("menu_confirm.ogg")
        return res == "BACK"
    return False


def _handle_controls_joybutton(button, state, controls_menu: ControlsConfigMenu, audio_manager=None) -> bool:
    """Process a JOYBUTTONDOWN event inside ControlsConfigMenu. Returns True if user exits back to parent menu."""
    if button == 1:
        return controls_menu.cancel() == "BACK"
    if button == 0 and not controls_menu.listening_for_key:
        res = controls_menu.confirm(state)
        if audio_manager and res in ("LISTENING", "RESET", "BACK"):
            audio_manager.play_sfx("menu_confirm.ogg")
        return res == "BACK"
    return False


def _poll_gamepad_vertical() -> float:
    """Return vertical gamepad menu navigation input in [-1.0, 1.0]."""
    if pygame.joystick.get_count() <= 0:
        return 0.0
    joy = pygame.joystick.Joystick(0)
    ay = joy.get_axis(1)
    hy = -joy.get_hat(0)[1]
    if abs(hy) > 0:
        return float(hy)
    return float(ay) if abs(ay) > 0.3 else 0.0


def _resolve_active_joystick(joystick=None):
    """Return an explicit or primary initialized pygame Joystick, or None if unavailable."""
    if joystick is not None:
        return joystick
    try:
        if not pygame.joystick.get_init() or pygame.joystick.get_count() <= 0:
            return None
        return pygame.joystick.Joystick(0)
    except Exception:
        return None


def stop_gamepad_rumble(joystick=None) -> bool:
    """Safely stop any active rumble motor vibration on the connected gamepad."""
    joy = _resolve_active_joystick(joystick)
    if joy is None or not callable(getattr(joy, "stop_rumble", None)):
        return False
    try:
        joy.stop_rumble()
        return True
    except Exception:
        return False


def dispatch_gamepad_rumble(state, joystick=None) -> bool:
    """Drain pending GameState rumble impulses and dispatch safely to Joystick.rumble()."""
    if state is None or not hasattr(state, "consume_rumble_impulse"):
        return False
    impulse = state.consume_rumble_impulse()
    if not impulse or not getattr(state, "rumble_enabled", True):
        return False
    joy = _resolve_active_joystick(joystick)
    if joy is None or not callable(getattr(joy, "rumble", None)):
        return False
    try:
        return bool(
            joy.rumble(
                float(impulse["low_frequency"]),
                float(impulse["high_frequency"]),
                int(impulse["duration_ms"]),
            )
        )
    except Exception:
        return False


def handle_title_events(
    state,
    renderer,
    title_menu: TitleMenu,
    audio_manager: AudioManager = None,
    controls_menu: ControlsConfigMenu | None = None,
):
    """Handle events during the title screen with Auto Input Mode and Ratcheted Navigation."""
    in_controls = getattr(title_menu.state, 'name', '') == 'CONTROLS'
    revealed_this_frame = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False, False, False
        
        # Mode Switching Rules
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
            state.input_mode = INPUT_MODE_KEYBOARD
        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION, pygame.JOYAXISMOTION):
            state.input_mode = INPUT_MODE_GAMEPAD

        # Two-Stage Attract Gate: First button/key/click reveals menu without triggering selection
        if not getattr(title_menu, "menu_revealed", True):
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.JOYBUTTONDOWN):
                title_menu.reveal_menu()
                revealed_this_frame = True
                if audio_manager:
                    audio_manager.play_sfx("menu_confirm.ogg")
            continue

        in_controls = getattr(title_menu.state, 'name', '') == 'CONTROLS'
        if event.type == pygame.JOYBUTTONDOWN:
            if in_controls:
                if controls_menu is not None:
                    if _handle_controls_joybutton(event.button, state, controls_menu, audio_manager):
                        title_menu.state = TitleMenuState.MAIN
                elif event.button == 1:
                    title_menu.state = TitleMenuState.MAIN
                continue
            if event.button == 0: # Cross/A
                title_menu.confirm()
            if event.button == 1: # Circle/B (Cancel)
                if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                    title_menu.state = TitleMenuState.MAIN
        
        if event.type == pygame.KEYDOWN:
            if in_controls:
                if controls_menu is not None:
                    if _handle_controls_keydown(event.key, state, controls_menu, audio_manager):
                        title_menu.state = TitleMenuState.MAIN
                elif event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    title_menu.state = TitleMenuState.MAIN
                continue

            if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                if event.key in (pygame.K_ESCAPE, pygame.K_n):
                    title_menu.state = TitleMenuState.MAIN
                    return True, True, False
                if event.key == pygame.K_y:
                    title_menu.confirm()
                    return True, True, False
                return True, True, False

            if getattr(state, 'lobby_editing_name', False):
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                    state.lobby_editing_name = False
                    if not state.network_manager.identity.strip():
                        state.network_manager.identity = "Scholar"
                    if state.stats is None:
                        from engine.stats import StatisticsTracker
                        state.stats = StatisticsTracker()
                    state.stats.data["player_name"] = state.network_manager.identity
                    state.save_stats(wait=True, allow_incompatible=True)
                    print(f"[NETWORK] Identity updated to: {state.network_manager.identity}")
                    return True, True, False
                if event.key == pygame.K_BACKSPACE:
                    state.network_manager.identity = state.network_manager.identity[:-1]
                    return True, True, False
                if event.unicode and event.unicode.isprintable() and len(state.network_manager.identity) < 15:
                    state.network_manager.identity += event.unicode
                    return True, True, False
                return True, True, False

            if title_menu.state == TitleMenuState.MAIN and event.key == pygame.K_n:
                state.lobby_editing_name = True
                return True, True, False

            if event.key == pygame.K_ESCAPE:
                return False, False, False
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                title_menu.confirm()

    # --- Unified Navigation Polling (Title) ---
    if revealed_this_frame or not getattr(title_menu, "menu_revealed", True):
        return True, True, False
    if getattr(state, 'lobby_editing_name', False):
        return True, True, False
    in_controls = getattr(title_menu.state, 'name', '') == 'CONTROLS'
    if in_controls:
        gp_y = _poll_gamepad_vertical()
        if abs(gp_y) <= 0.3:
            return True, True, True
        if (
            controls_menu is not None
            and not controls_menu.listening_for_key
            and not state.input_ratchet_latched
            and state.menu_nav_cooldown <= 0
        ):
            if gp_y > 0.6:
                controls_menu.navigate(1)
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")
            elif gp_y < -0.6:
                controls_menu.navigate(-1)
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")
        return True, True, False

    kb = _get_keybindings(state)
    move_dir = get_movement_actions(state)
    ratchet_reset = False
    
    # Targeted Neutral Check
    keys = pygame.key.get_pressed()
    kb_v_neutral = not any([keys[kb["move_up"]], keys[kb["move_down"]], keys[pygame.K_UP], keys[pygame.K_DOWN]])
    
    gp_v_neutral = True
    if pygame.joystick.get_count() > 0:
        joy = pygame.joystick.Joystick(0)
        if abs(joy.get_axis(1)) > 0.3 or joy.get_hat(0)[1] != 0:
            gp_v_neutral = False

    if kb_v_neutral and gp_v_neutral:
        ratchet_reset = True
    else:
        # Process Navigation if not latched and not on cooldown
        if not state.input_ratchet_latched and state.menu_nav_cooldown <= 0:
            if move_dir[1] > 0.6: # Down
                title_menu.navigate('down')
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")
            elif move_dir[1] < -0.6: # Up
                title_menu.navigate('up')
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")

    return True, True, ratchet_reset


def handle_game_events(
    state,
    pause_menu: PauseMenu | None = None,
    audio_manager: AudioManager = None,
    controls_menu: ControlsConfigMenu | None = None,
):
    """Handle events during the main game loop with Auto Input Mode and Ratcheted Navigation."""
    running = True
    attack = False
    flask = False
    dash = False
    swap = False
    inspect = False
    mouse_click = None
    kb = _get_keybindings(state)
    
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
        
        in_pause_controls = (
            pause_menu is not None
            and pause_menu.is_open()
            and getattr(pause_menu.state, 'name', '') == 'CONTROLS'
        )
        # Controller Buttons
        if event.type == pygame.JOYBUTTONDOWN:
            if pause_menu and pause_menu.is_open():
                from engine.pause_menu import PauseMenuState
                if in_pause_controls:
                    if controls_menu is not None:
                        if _handle_controls_joybutton(event.button, state, controls_menu, audio_manager):
                            pause_menu.state = PauseMenuState.MAIN
                    elif event.button == 1:
                        pause_menu.state = PauseMenuState.MAIN
                    continue
                if event.button == 0: # Confirm
                    if pause_menu.get_selected() == "Controls":
                        if controls_menu is not None:
                            controls_menu.reset_view()
                        pause_menu.state = PauseMenuState.CONTROLS
                    else:
                        pause_menu.confirm()
                elif event.button == 1: # Back / Cancel
                    pause_menu.close()
            else:
                if event.button == 0:
                    if getattr(state, 'active_respite', None) or getattr(state, 'binder_dialog', None):
                        state.input_ratchet_latched = False
                    attack = True # Confirm/Swing
                if event.button == 1:
                    if getattr(state, 'chronicle_dialog', None):
                        state.cancel_chronicle_dialog()
                        continue
                    if getattr(state, 'binder_dialog', None):
                        state.close_binder_dialog()
                        continue
                    if getattr(state, 'active_respite', None):
                        state.close_respite_menu()
                        state.save_stats(wait=True)
                        continue
                    if getattr(state, 'active_dialogue', None):
                        state.active_dialogue = None
                        continue
                    dash = True   # Cancel/Dash
                if event.button == 3: flask = True  # Flask
                if event.button == 4: swap = True   # L1 Swap
                if event.button == 5: inspect = True # R1 Inspect
                if event.button == 6: # Options/Share
                    if pause_menu: pause_menu.toggle()

        if event.type == pygame.KEYDOWN:
            if in_pause_controls:
                from engine.pause_menu import PauseMenuState
                if controls_menu is not None:
                    if _handle_controls_keydown(event.key, state, controls_menu, audio_manager):
                        pause_menu.state = PauseMenuState.MAIN
                elif event.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    pause_menu.state = PauseMenuState.MAIN
                continue

            if event.key == pygame.K_ESCAPE:
                if getattr(state, 'chronicle_dialog', None):
                    state.cancel_chronicle_dialog()
                    continue
                if getattr(state, 'binder_dialog', None):
                    state.close_binder_dialog()
                    continue
                if getattr(state, 'active_respite', None):
                    state.close_respite_menu()
                    state.save_stats(wait=True)
                    continue
                if pause_menu is not None: pause_menu.toggle()
                else: running = False
                continue

            if pause_menu is not None and pause_menu.is_open():
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    if pause_menu.get_selected() == "Controls":
                        from engine.pause_menu import PauseMenuState
                        if controls_menu is not None:
                            controls_menu.reset_view()
                        pause_menu.state = PauseMenuState.CONTROLS
                    else:
                        pause_menu.confirm()
                        if audio_manager:
                            audio_manager.play_sfx("menu_confirm.ogg")
                continue

            if getattr(state, 'active_respite', None) and event.key == kb["respite_rest"]:
                state.active_respite.execute_rest(state, audio_manager=audio_manager)
                continue
            if (
                getattr(state, 'chronicle_dialog', None)
                or getattr(state, 'binder_dialog', None)
                or getattr(state, 'active_respite', None)
            ) and event.key in (
                pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_e
            ):
                if getattr(state, 'active_respite', None) or getattr(state, 'binder_dialog', None):
                    state.input_ratchet_latched = False
                attack = True
            if event.key == kb["attack"]:
                if getattr(state, 'active_respite', None) or getattr(state, 'binder_dialog', None):
                    state.input_ratchet_latched = False
                attack = True
            if event.key == kb["flask"]: flask = True
            if event.key == kb["swap"]: swap = True
            if event.key == kb["inspect"]: inspect = True
            if event.key == kb["dash"]: dash = True

    # --- Unified Navigation Polling (Game/Pause) ---
    in_pause_controls = (
        pause_menu is not None
        and pause_menu.is_open()
        and getattr(pause_menu.state, 'name', '') == 'CONTROLS'
    )
    if in_pause_controls:
        gp_y = _poll_gamepad_vertical()
        if abs(gp_y) <= 0.3:
            return running, attack, flask, dash, swap, inspect, mouse_click, True
        if (
            controls_menu is not None
            and not controls_menu.listening_for_key
            and not state.input_ratchet_latched
            and state.menu_nav_cooldown <= 0
        ):
            if gp_y > 0.6:
                controls_menu.navigate(1)
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")
            elif gp_y < -0.6:
                controls_menu.navigate(-1)
                state.input_ratchet_latched = True
                state.menu_nav_cooldown = 0.2
                if audio_manager: audio_manager.play_sfx("menu_navigate.ogg")
        return running, attack, flask, dash, swap, inspect, mouse_click, False

    move_dir = get_movement_actions(state)
    ratchet_reset = False
    
    # Targeted Neutral Check: Only check vertical navigation axis
    keys = pygame.key.get_pressed()
    kb_v_neutral = not any([keys[kb["move_up"]], keys[kb["move_down"]], keys[pygame.K_UP], keys[pygame.K_DOWN]])
    
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


    return running, attack, flask, dash, swap, inspect, mouse_click, ratchet_reset

def get_movement_actions(state):
    """Poll keyboard and joysticks for movement actions."""
    move_dir = [0.0, 0.0]
    kb = _get_keybindings(state)
    
    # 1. Keyboard Polling (remappable WASD + always-available Arrow keys)
    keys = pygame.key.get_pressed()
    if keys[kb["move_up"]] or keys[pygame.K_UP]: move_dir[1] -= 1
    if keys[kb["move_down"]] or keys[pygame.K_DOWN]: move_dir[1] += 1
    if keys[kb["move_left"]] or keys[pygame.K_LEFT]: move_dir[0] -= 1
    if keys[kb["move_right"]] or keys[pygame.K_RIGHT]: move_dir[0] += 1
    
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

def parse_args(argv=None) -> argparse.Namespace:
    """Parse CLI flags for Avoid Rain."""
    parser = argparse.ArgumentParser(description="Avoid Rain")
    parser.add_argument("--fullscreen", action="store_true", help="Run in fullscreen mode")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip opening all LAN/co-op network sockets (avoids Windows Firewall prompts)",
    )
    return parser.parse_args(argv)


def main():
    """Main application loop."""
    args = parse_args()
    if args.offline:
        print("[NETWORK] Offline mode forced via --offline: LAN/co-op sockets disabled.")

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

    provisional_state = None
    try:
        state = GameState(stats=None, stats_path=None, auto_load=True, offline_only=args.offline)
    except Exception:
        from engine.stats import StatisticsTracker
        state = GameState(stats=StatisticsTracker(), auto_load=False, offline_only=args.offline)

    def shutdown_handler():
        try:
            # Use the 'state' and 'provisional_state' objects from the main() scope
            target_state = state if 'state' in locals() else provisional_state
            
            if target_state:
                # 1. Stop Network (sends DISCONNECT signal)
                if hasattr(target_state, 'network_manager'):
                    target_state.network_manager.stop_network()
                
                # 2. Final Stat Flush (MUST happen before worker shutdown)
                if hasattr(target_state, 'save_stats'):
                    target_state.save_stats(wait=True)

                # 3. Stop Autosave Worker
                if hasattr(target_state, 'shutdown_save_worker'):
                    target_state.shutdown_save_worker(timeout=0.5)
                    
        except Exception as e:
            print(f"[SHUTDOWN] Error during cleanup: {e}")
        finally:
            pygame.quit()

    pause_menu = PauseMenu(
        debug_text_enabled=getattr(state, "debug_text_enabled", False),
        on_toggle_debug=lambda val: state.set_debug_text_enabled(val, save=True),
        screen_shake_enabled=getattr(state, "screen_shake_enabled", True),
        on_toggle_screen_shake=lambda val: state.set_screen_shake_enabled(val, save=True),
        rumble_enabled=getattr(state, "rumble_enabled", True),
        on_toggle_rumble=lambda val: (
            state.set_rumble_enabled(val, save=True),
            stop_gamepad_rumble() if not val else None,
        ),
        forced_marginalia_event_id=getattr(state, "forced_marginalia_event_id", None),
        on_select_forced_event=state.set_forced_marginalia_event_id,
        on_reset_margin_scraps=lambda: state.reset_margin_scraps(save=True),
    )
    
    # [Initialization] Detect existing compatible save file to enable 'Continue'
    from engine.title_menu import TitleMenu, TitleMenuState, TitleTransition, TitleTransitionPhase
    from engine.stats import StatisticsTracker
    title_menu = TitleMenu(
        has_save=StatisticsTracker.has_compatible_save(),
        online_mode=getattr(state, "online_mode", True),
        offline_locked=bool(args.offline),
    )
    controls_menu = ControlsConfigMenu()
    title_transition = TitleTransition()
    
    in_title = True
    running = True

    try:
        while running:
            dt = clock.tick(FPS) / 1000.0
            
            # Universal Cooldown Decrement
            if state.menu_nav_cooldown > 0:
                state.menu_nav_cooldown -= dt

            if in_title:
                if title_transition.is_active():
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            running = False
                        elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                            title_transition.skip()
                        elif ev.type == pygame.JOYBUTTONDOWN:
                            title_transition.skip()
                    completed = title_transition.update(dt, audio_manager=audio)
                    if title_transition.phase == TitleTransitionPhase.FADE_TO_BLACK:
                        renderer.draw_title_screen(title_menu, state)
                    renderer.draw_title_transition(title_transition)
                    pygame.display.flip()
                    if completed:
                        mode = title_transition.mode
                        title_transition.reset()
                        if mode == "continue":
                            state.hydrate_from_disk()
                            state.set_debug_text_enabled(False, save=True)
                            renderer.invalidate_static_world()
                            if not getattr(state, "offline_only", False):
                                state.start_seamless_lan(background=True)
                        elif mode == "new_draft":
                            state.reset_to_new_game()
                            state.set_debug_text_enabled(False, save=False)
                            state.save_stats(wait=True)
                            renderer.invalidate_static_world()
                            title_menu.state = TitleMenuState.MAIN
                            if not getattr(state, "offline_only", False):
                                state.start_seamless_lan(background=True)
                        pause_menu.set_debug_text_enabled(False)
                        pause_menu.set_screen_shake_enabled(getattr(state, "screen_shake_enabled", True))
                        pause_menu.set_rumble_enabled(getattr(state, "rumble_enabled", True))
                        pause_menu.set_forced_marginalia_event_id(
                            getattr(state, "forced_marginalia_event_id", None)
                        )
                        in_title = False
                    continue

                in_title, running, ratchet_reset = handle_title_events(
                    state, renderer, title_menu, audio_manager=audio, controls_menu=controls_menu
                )
                if getattr(title_menu, "menu_revealed", True):
                    title_menu.update_transition(dt)
                renderer.draw_title_screen(title_menu, state, controls_menu=controls_menu)
                audio.stop_environment_audio()
                audio.update(dt, "title_theme.ogg")
                if ratchet_reset: state.input_ratchet_latched = False
                
                if title_menu.was_confirmed():
                    selected = title_menu.get_selected()
                    title_menu.clear_confirm()
                    audio.play_sfx("menu_confirm.ogg")
                    
                    if selected.startswith('Mode:'):
                        if getattr(state, "offline_only", False):
                            continue
                        new_mode = title_menu.toggle_online_mode()
                        state.set_online_mode(new_mode, save=True)
                        continue
                        
                    if selected == 'Continue':
                        title_transition.start("continue")
                        continue
                    if selected == 'New Draft':
                        if title_menu.state == TitleMenuState.CONFIRM_NEW_GAME:
                            title_transition.start("new_draft")
                            continue
                        if StatisticsTracker.has_compatible_save(): title_menu.state = TitleMenuState.CONFIRM_NEW_GAME
                        else:
                            title_transition.start("new_draft")
                            continue
                    if selected == 'Controls':
                        controls_menu.reset_view()
                        title_menu.state = TitleMenuState.CONTROLS
                        continue
                    if selected == 'Quit': running = False
            else:
                waiting_cnt = getattr(state, "waiting_scholars", 0)
                if waiting_cnt != pause_menu.waiting_scholars:
                    pause_menu.set_waiting_scholars(waiting_cnt)
                forced_ev = getattr(state, "forced_marginalia_event_id", None)
                if forced_ev != pause_menu.forced_marginalia_event_id:
                    pause_menu.set_forced_marginalia_event_id(forced_ev)
                ev_res = handle_game_events(
                    state, pause_menu=pause_menu, audio_manager=audio, controls_menu=controls_menu
                )
                running, attack, flask, dash, swap, inspect, mouse_click, ratchet_reset = ev_res
                if ratchet_reset: state.input_ratchet_latched = False
                
                if pause_menu.is_open():
                    pause_menu.update_transition(dt)
                    audio.update_rain_audio(0.0, paused=True)
                    audio.update_environment_audio(state, paused=True)
                    audio.stop_enemy_move_sounds()
                    renderer.draw_pause_menu(pause_menu, state=state, controls_menu=controls_menu)
                    if pause_menu.should_return_to_sanctuary():
                        audio.stop_enemy_move_sounds()
                        audio.stop_environment_audio()
                        pause_menu.clear_return_to_sanctuary()
                        pause_menu.close()
                        state.return_party_to_sanctuary()
                        renderer.invalidate_static_world()
                        continue
                    if pause_menu.should_quit():
                        audio.update_rain_audio(0.0, paused=True)
                        audio.stop_environment_audio()
                        audio.stop_enemy_move_sounds()
                        try: state.save_stats(wait=True)
                        except Exception: pass
                        pause_menu.clear_quit(); pause_menu.close(); in_title = True
                        title_menu.menu_revealed = False
                        title_menu.reset_transition()
                        state.deallocate()
                        try:
                            title_menu.set_has_save(StatisticsTracker.has_compatible_save())
                        except Exception: pass
                        continue
                else:
                    kb = _get_keybindings(state)
                    pressed = pygame.key.get_pressed()
                    actions = {
                        'move': get_movement_actions(state),
                        'attack': attack, 'flask': flask, 'dash': dash, 'swap': swap,
                        'inspect': inspect,
                        'mouse_click': mouse_click, 'ratchet_reset': ratchet_reset,
                        'block': pressed[kb["block"]],
                        'key_r': pressed[kb["respite_rest"]],
                        'key_1': pressed[pygame.K_1],
                        'key_2': pressed[pygame.K_2],
                        'key_3': pressed[pygame.K_3]
                    }
                    if state.input_mode == INPUT_MODE_GAMEPAD and pygame.joystick.get_count() > 0:
                        joy = pygame.joystick.Joystick(0)
                        if joy.get_button(2): actions['attack'] = True
                        if joy.get_button(3): actions['flask'] = True
                        if joy.get_button(7): actions['block'] = True
                        if joy.get_button(1): actions['key_r'] = True
                        if joy.get_button(5): actions['inspect'] = True
                    
                    state.update(dt, actions, audio_manager=audio)
                    dispatch_gamepad_rumble(state)
                    audio.update(dt, state.player.active_track_name)
                    renderer.render(state, audio_manager=audio)

    except Exception as exc:
        print(f"An error occurred: {exc}")
        raise exc
    finally:
        shutdown_handler()

if __name__ == "__main__":
    main()
