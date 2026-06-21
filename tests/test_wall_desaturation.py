"""Unit tests for the wall texture desaturation visual logic."""
# pylint: disable=no-member
import pygame
from rendering.renderer import Renderer

def test_desaturate_surface(monkeypatch):
    """Verify that _desaturate_surface converts a color surface to grayscale."""
    # Mock SysFont to run headlessly without font initialization errors
    class DummyFont:
        """Dummy font class."""
        def render(self, _text, _aa, _color=None):
            """Dummy render."""
            return pygame.Surface((1, 1))
        def size(self, _text):
            """Dummy size."""
            return (0, 0)
    monkeypatch.setattr(pygame.font, 'SysFont', lambda *a, **k: DummyFont())

    # Create a 2x2 colored test surface: (200, 100, 50, 180)
    test_surf = pygame.Surface((2, 2), pygame.SRCALPHA)
    test_surf.fill((200, 100, 50, 180))

    # Initialize a dummy screen and a Renderer instance
    dummy_screen = pygame.Surface((10, 10))
    renderer = Renderer(dummy_screen)

    # Convert the surface (pylint protected access bypass for testing internals)
    # pylint: disable=protected-access
    gray_surf = renderer._desaturate_surface(test_surf)

    # Assert dimensions match
    assert gray_surf.get_size() == (2, 2)

    # Inspect all pixels
    for x in range(2):
        for y in range(2):
            color = gray_surf.get_at((x, y))
            # Grayscale check: red, green, and blue values must be equal
            assert color.r == color.g == color.b
            # Alpha channel check: alpha must be preserved
            assert color.a == 180
            # Ensure color is not just black/white unless input demands it
            assert color.r > 0
