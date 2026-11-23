"""Unit tests for Batch 14: Respite Close Menu Default/Styling, requirements.txt, and README.md."""
# pylint: disable=wrong-import-position,wrong-import-order,no-member,protected-access

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import pytest

import constants
from engine.game_state import GameState
from engine.world import Respite, World
from ui.menu import draw_respite_menu


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize and cleanly tear down pygame in headless dummy mode."""
    pygame.init()
    yield
    pygame.quit()


def test_respite_defaults_to_close_menu_wraps_cleanly_and_styles_active():
    """Verify Respite opens on Close Menu (idx 5), wraps cleanly to Rest (idx 0), and styles Close Menu legibly."""
    state = GameState(auto_load=False)
    state.network_manager.stop_network()
    try:
        state.world = World("sanctuary")
        state.world.load_from_prototype(["." * 8 for _ in range(8)])
        respite = Respite((160, 160), (40, 40))
        state.world.interactables = [respite]

        # Fresh GameState and opening Respite both default to index 5 ([ CLOSE MENU ])
        assert state.respite_selection_idx == 5
        respite.execute_interaction(state)
        assert state.active_respite is respite
        assert state.respite_selection_idx == 5

        # Navigating down from 5 wraps cleanly to 0 (REST); up from 0 wraps cleanly back to 5
        state.input_ratchet_latched = False
        state.menu_nav_cooldown = 0.0
        state._handle_dialogue_ui({"move": (0.0, 1.0)}, False, None)
        assert state.respite_selection_idx == 0

        state.input_ratchet_latched = False
        state.menu_nav_cooldown = 0.0
        state._handle_dialogue_ui({"move": (0.0, -1.0)}, False, None)
        assert state.respite_selection_idx == 5

        # Pressing confirm immediately on default index 5 closes the Respite cleanly
        state.input_ratchet_latched = False
        state._handle_dialogue_ui({"move": (0.0, 0.0)}, True, None)
        assert state.active_respite is None
        assert state.respite_selection_idx == 5

        # Verify draw_respite_menu colors [ CLOSE MENU ] COLOR_SELECTION when focused & COLOR_WHITE when unselected
        respite.execute_interaction(state)
        screen = pygame.Surface((1280, 720))
        real_font = pygame.font.SysFont("Arial", 18)

        rendered = []

        class _TrackingFont:
            """Font proxy capturing rendered text strings and colors."""

            def render(self, text, antialias, color):
                """Record (text, color) and delegate to real pygame font."""
                rendered.append((text, color))
                return real_font.render(text, antialias, color)

        # Focused (idx 5)
        state.respite_selection_idx = 5
        draw_respite_menu(screen, _TrackingFont(), state)
        close_focused = [col for txt, col in rendered if "CLOSE MENU" in txt]
        assert close_focused == [constants.COLOR_SELECTION]
        assert not any("[UP/DOWN]" in txt for txt, _ in rendered), "Obsolete Respite shortcut footer must be removed"

        # Unselected (idx 0)
        rendered.clear()
        state.respite_selection_idx = 0
        draw_respite_menu(screen, _TrackingFont(), state)
        close_unselected = [col for txt, col in rendered if "CLOSE MENU" in txt]
        assert close_unselected == [constants.COLOR_WHITE]
    finally:
        state.shutdown_save_worker(timeout=1.0)


def test_requirements_txt_and_readme_setup_instructions():
    """Verify requirements.txt pins pygame==2.6.1 and README.md documents Python 3.13 + Pygame 2.6.1 setup."""
    assert os.path.exists("requirements.txt")
    with open("requirements.txt", "r", encoding="utf-8") as req_f:
        req_lines = [line.strip() for line in req_f if line.strip() and not line.strip().startswith("#")]
    assert "pygame==2.6.1" in req_lines

    assert os.path.exists("README.md")
    with open("README.md", "r", encoding="utf-8") as doc_f:
        readme = doc_f.read()
    for expected in (
        "## Requirements",
        "Python 3.13",
        "Pygame 2.6.1",
        "## Windows",
        "py -3.13 -m venv .venv",
        "Python 3.14+ is currently not supported due to pygame installation issues.",
        "## Linux/macOS",
        "python3.13 -m venv .venv",
        "pip install -r requirements.txt",
        "--max-line-length=120",
    ):
        assert expected in readme, f"Missing expected setup text in README.md: {expected!r}"
