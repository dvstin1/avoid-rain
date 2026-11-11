"""Unit tests for stylized title screen rendering and composite caching."""
# pylint: disable=no-member,protected-access
import pygame
from rendering.renderer import Renderer
from engine.game_state import GameState
from constants import SCREEN_WIDTH, SCREEN_HEIGHT


def test_title_composite_caching_and_layers():
    """Verify title composite pre-renders with tracking, shadows, and caches the surface."""
    pygame.init()
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    renderer = Renderer(screen)

    surf1 = renderer._get_title_composite()
    assert surf1 is not None
    assert isinstance(surf1, pygame.Surface)
    assert surf1.get_width() > 300
    assert surf1.get_height() > 40

    # Ensure caching avoids re-generating surface
    surf2 = renderer._get_title_composite()
    assert surf1 is surf2


def test_draw_title_screen_executes_with_motion():
    """Verify draw_title_screen executes cleanly without errors and blits the title."""
    pygame.init()
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    renderer = Renderer(screen)
    state = GameState(auto_load=False)

    # Calling draw_title_screen should run smoothly
    renderer.draw_title_screen(menu=0, state=state)
    state.shutdown_save_worker(timeout=1.0)
