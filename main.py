"""
Main entry point for Avoid Rain.
Handles the application lifecycle and top-level loops.
"""
import sys
import pygame
from constants import SCREEN_WIDTH, SCREEN_HEIGHT, TITLE, FPS
from engine.game_state import GameState
from rendering.renderer import Renderer

# pylint: disable=no-member

def handle_title_events(renderer):
    """Handle events during the title screen."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False, False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False, False
            if event.key == pygame.K_SPACE:
                renderer.fade_to_black()
                return False, True
    return True, True

def handle_game_events():
    """Handle events during the main game loop."""
    running = True
    attack = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_SPACE:
                attack = True
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
    state = GameState()

    in_title = True
    running = True

    try:
        while running:
            if in_title:
                in_title, running = handle_title_events(renderer)
                renderer.draw_title_screen()
                clock.tick(FPS)
            else:
                dt = clock.tick(FPS) / 1000.0
                running, attack = handle_game_events()
                actions = {
                    'move': get_movement_actions(),
                    'attack': attack
                }
                state.update(dt, actions)
                renderer.render(state)

    except Exception as exc:
        print(f"An error occurred: {exc}")
        raise exc
    finally:
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
