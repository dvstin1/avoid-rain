"""
Handles all Pygame drawing calls.
"""
import pygame
# pylint: disable=no-member
from constants import (
    COLOR_BLACK,
    COLOR_WHITE,
    COLOR_BLUE,
    COLOR_GREEN,
    TILE_SIZE,
    TILE_WALL,
    COLOR_WALL,
    COLOR_FLOOR,
    GRID_WIDTH,
    GRID_HEIGHT,
    COLOR_YELLOW,
)
from engine.player import PlayerStateEnum
from engine.combat import get_sword_hitbox
from engine.camera import Camera
from constants import AUTOSAVE_INDICATOR_DURATION

class Renderer:
    """Coordinates rendering of the game state."""
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 24)

    def render(self, state):
        """Draw the visible portion of the game state to the screen using a camera.

        The camera attempts to center on the player but is clamped to the world
        bounds so the viewport never shows outside the world.
        """
        self.screen.fill(COLOR_BLACK)

        # Use camera from the game state if available; otherwise create a transient one
        screen_w = self.screen.get_width()
        screen_h = self.screen.get_height()
        world_w = GRID_WIDTH * TILE_SIZE
        world_h = GRID_HEIGHT * TILE_SIZE

        if hasattr(state, 'camera'):
            # Ensure camera screen size matches the current screen (window resize)
            # (camera keeps its own screen_w/h so update if needed)
            if state.camera.screen_w != screen_w or state.camera.screen_h != screen_h:
                state.camera.screen_w = screen_w
                state.camera.screen_h = screen_h
            offset_x, offset_y = state.camera.get_offset()
        else:
            camera = Camera(screen_w, screen_h, world_w, world_h)
            offset_x, offset_y = camera.get_target_offset(state.player.get_center())

        # Visible tile range (add +1 to ensure partial tiles at edges are drawn)
        start_x = max(0, offset_x // TILE_SIZE)
        start_y = max(0, offset_y // TILE_SIZE)
        end_x = min(GRID_WIDTH, (offset_x + screen_w) // TILE_SIZE + 1)
        end_y = min(GRID_HEIGHT, (offset_y + screen_h) // TILE_SIZE + 1)

        # 1. Draw World Grid (only visible tiles)
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                draw_rect = (x * TILE_SIZE - offset_x, y * TILE_SIZE - offset_y, TILE_SIZE, TILE_SIZE)
                if state.world.grid[y][x] == TILE_WALL:
                    pygame.draw.rect(self.screen, COLOR_WALL, draw_rect)
                else:
                    pygame.draw.rect(self.screen, COLOR_FLOOR, draw_rect, 1)

        # 2. Draw Dummy (with camera offset)
        dummy_rect = pygame.Rect(state.dummy_rect)
        dummy_draw = pygame.Rect(dummy_rect.x - offset_x, dummy_rect.y - offset_y, dummy_rect.width, dummy_rect.height)
        pygame.draw.rect(self.screen, COLOR_GREEN, dummy_draw)
        if state.dummy_outline_timer > 0:
            pygame.draw.rect(self.screen, COLOR_WHITE, dummy_draw, 2)

        # 3. Draw Player (with camera offset)
        player = state.player
        player_draw = pygame.Rect(player.x - offset_x, player.y - offset_y, player.width, player.height)
        pygame.draw.rect(self.screen, COLOR_BLUE, player_draw)

        # 4. Draw Sword (with camera offset)
        if player.state == PlayerStateEnum.ATTACKING:
            hitbox = get_sword_hitbox(player.get_center(), player.facing)
            hitbox_draw = (hitbox[0] - offset_x, hitbox[1] - offset_y, hitbox[2], hitbox[3])
            pygame.draw.rect(self.screen, COLOR_YELLOW, hitbox_draw)

        # 5. Draw Damage Numbers (with camera offset)
        for num in state.damage_numbers:
            text_surf = self.font.render(str(num['val']), True, num['color'])
            x, y = num['pos']
            self.screen.blit(text_surf, (x - offset_x, y - offset_y))

        # 6. Draw autosave indicator if a recent autosave occurred
        try:
            if getattr(state, 'last_save_elapsed', 1e6) <= AUTOSAVE_INDICATOR_DURATION:
                indicator_surf = self.font.render("Saved", True, (200, 200, 200))
                rect = indicator_surf.get_rect()
                # Draw in top-right corner with small padding
                self.screen.blit(indicator_surf, (self.screen.get_width() - rect.width - 8, 8))
        except Exception:
            pass

        pygame.display.flip()

    def draw_title_screen(self, selected_index_or_menu=0):
        """Draw the title screen with a simple menu.

        Accepts either a selected index (int) or a menu object implementing
        get_options() and get_selected_index(). This allows TitleMenu to drive
        the displayed options (e.g., New Game / Continue / Quit).
        """
        self.screen.fill(COLOR_BLACK)
        title_surf = self.font.render("AVOID RAIN", True, COLOR_WHITE)
        instr_surf = self.font.render("Use ARROW KEYS and ENTER to choose", True, COLOR_WHITE)

        title_rect = title_surf.get_rect(center=(self.screen.get_width()//2, 220))
        instr_rect = instr_surf.get_rect(center=(self.screen.get_width()//2, 280))

        self.screen.blit(title_surf, title_rect)
        self.screen.blit(instr_surf, instr_rect)

        # Resolve options and selected index from parameter
        options = ["New Game", "Quit"]
        selected_index = 0
        try:
            # If passed an object with get_options, use it
            if hasattr(selected_index_or_menu, 'get_options'):
                options = selected_index_or_menu.get_options()
                selected_index = selected_index_or_menu.get_selected_index()
            else:
                # treat as integer index
                selected_index = int(selected_index_or_menu)
        except Exception:
            options = ["New Game", "Quit"]
            selected_index = 0

        for idx, opt in enumerate(options):
            color = COLOR_YELLOW if idx == selected_index else COLOR_WHITE
            opt_surf = self.font.render(opt, True, color)
            opt_rect = opt_surf.get_rect(center=(self.screen.get_width()//2, 340 + idx * 40))
            self.screen.blit(opt_surf, opt_rect)
        pygame.display.flip()

    def fade_to_black(self):
        """Simple fade out effect."""
        fade_surf = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        fade_surf.fill(COLOR_BLACK)
        for alpha in range(0, 300, 5):
            fade_surf.set_alpha(alpha)
            self.screen.blit(fade_surf, (0, 0))
            pygame.display.flip()
            pygame.time.delay(10)

    def draw_loading_screen(self, message: str, submessage: str | None = None, min_time: float = 2.0, sleep_func=None):
        """Draw a loading screen with a message and optional submessage.

        The function enforces a minimum display time (min_time). sleep_func
        may be injected for tests (defaults to time.sleep).
        """
        import time
        sleep = sleep_func if sleep_func is not None else time.sleep

        self.screen.fill(COLOR_BLACK)
        title_surf = self.font.render(message, True, COLOR_WHITE)
        title_rect = title_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 - 20))
        self.screen.blit(title_surf, title_rect)
        if submessage is not None:
            sub_surf = self.font.render(submessage, True, COLOR_WHITE)
            sub_rect = sub_surf.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2 + 20))
            self.screen.blit(sub_surf, sub_rect)
        pygame.display.flip()
        # Ensure the loading screen is visible for at least min_time
        sleep(min_time)

    def draw_pause_menu(self, selected_index: int = 0):
        """Draw a simple pause overlay with 'Paused' text.

        selected_index controls which menu option is highlighted.
        """
        overlay = pygame.Surface(
            (self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 180))  # semi-transparent dark overlay
        self.screen.blit(overlay, (0, 0))
        pause_surf = self.font.render("PAUSED", True, COLOR_WHITE)
        # Show instructions and menu options
        instr_surf = self.font.render("Use ARROW KEYS and ENTER to choose", True, COLOR_WHITE)
        options = ["Resume", "Quit"]
        # Draw main pause text
        pause_rect = pause_surf.get_rect(
            center=(self.screen.get_width()//2, self.screen.get_height()//2 - 50)
        )
        self.screen.blit(pause_surf, pause_rect)
        # Draw instruction
        instr_rect = instr_surf.get_rect(
            center=(self.screen.get_width()//2, self.screen.get_height()//2 - 20)
        )
        self.screen.blit(instr_surf, instr_rect)
        # Draw options with highlight based on selected_index
        for idx, opt in enumerate(options):
            color = COLOR_YELLOW if idx == selected_index else COLOR_WHITE
            opt_surf = self.font.render(opt, True, color)
            opt_rect = opt_surf.get_rect(
                center=(self.screen.get_width()//2, self.screen.get_height()//2 + 10 + idx * 30)
            )
            self.screen.blit(opt_surf, opt_rect)
        pygame.display.flip()
