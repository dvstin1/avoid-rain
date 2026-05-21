"""
Handles all Pygame drawing calls.
"""
import pygame
from constants import (
    COLOR_BLACK, COLOR_WHITE, COLOR_BLUE, COLOR_GREEN,
    TILE_SIZE, TILE_WALL, COLOR_WALL, COLOR_FLOOR,
    GRID_WIDTH, GRID_HEIGHT, COLOR_YELLOW
)
from engine.player import PlayerStateEnum
from engine.combat import get_sword_hitbox

class Renderer:
    """Coordinates rendering of the game state."""
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 24)

    def render(self, state):
        """Draw the entire game state to the screen."""
        self.screen.fill(COLOR_BLACK)

        # 1. Draw World Grid
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                rect = (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if state.world.grid[y][x] == TILE_WALL:
                    pygame.draw.rect(self.screen, COLOR_WALL, rect)
                else:
                    pygame.draw.rect(self.screen, COLOR_FLOOR, rect, 1)

        # 2. Draw Dummy
        dummy_rect = pygame.Rect(state.dummy_rect)
        pygame.draw.rect(self.screen, COLOR_GREEN, dummy_rect)
        if state.dummy_outline_timer > 0:
            pygame.draw.rect(self.screen, COLOR_WHITE, dummy_rect, 2)

        # 3. Draw Player
        player = state.player
        player_rect = pygame.Rect(player.x, player.y, player.width, player.height)
        pygame.draw.rect(self.screen, COLOR_BLUE, player_rect)

        # 4. Draw Sword
        if player.state == PlayerStateEnum.ATTACKING:
            hitbox = get_sword_hitbox(player.get_center(), player.facing)
            pygame.draw.rect(self.screen, COLOR_YELLOW, hitbox)

        # 5. Draw Damage Numbers
        for num in state.damage_numbers:
            text_surf = self.font.render(str(num['val']), True, num['color'])
            self.screen.blit(text_surf, num['pos'])

        pygame.display.flip()

    def draw_title_screen(self):
        """Draw the simple title screen."""
        self.screen.fill(COLOR_BLACK)
        title_surf = self.font.render("AVOID RAIN", True, COLOR_WHITE)
        prompt_surf = self.font.render("Press SPACE to Start", True, COLOR_WHITE)

        title_rect = title_surf.get_rect(center=(self.screen.get_width()//2, 300))
        prompt_rect = prompt_surf.get_rect(center=(self.screen.get_width()//2, 400))

        self.screen.blit(title_surf, title_rect)
        self.screen.blit(prompt_surf, prompt_rect)
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
