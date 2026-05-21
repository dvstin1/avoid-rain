"""
PauseMenu: decoupled pause menu state machine that uses PauseHandler.

Provides open/close/toggle semantics without requiring rendering or input subsystems.
"""
from __future__ import annotations

from typing import Optional
from .pause import PauseHandler


class PauseMenu:
    """Simple pause menu controller.

    This class is intentionally UI-agnostic: it manages whether the
    menu is considered open and ensures the provided PauseHandler is
    paused while the menu is open.
    """

    def __init__(self, pause_handler: Optional[PauseHandler] = None) -> None:
        self.pause_handler = pause_handler or PauseHandler()
        self._open = False
        self._quit_requested = False
        # Menu options for navigation (UI-agnostic)
        self._options = ["Resume", "Quit"]
        self._selected = 0

    def open(self) -> None:
        """Open the pause menu and pause the game."""
        self._open = True
        self._quit_requested = False
        self._selected = 0
        self.pause_handler.pause()

    def close(self) -> None:
        """Close the pause menu and resume the game."""
        self._open = False
        self.pause_handler.resume()

    def toggle(self) -> None:
        """Toggle the menu open/closed."""
        if self._open:
            self.close()
        else:
            self.open()

    def is_open(self) -> bool:
        """Return True if the pause menu is open."""
        return bool(self._open)

    def request_quit(self) -> None:
        """Mark that the user requested to quit from the pause menu."""
        self._quit_requested = True

    def clear_quit(self) -> None:
        """Clear any pending quit request."""
        self._quit_requested = False

    def should_quit(self) -> bool:
        """Return True if quit was requested from the pause menu."""
        return bool(self._quit_requested)

    def navigate(self, direction: str) -> None:
        """Navigate the menu. direction is 'up' or 'down'."""
        if direction == "up":
            self._selected = (self._selected - 1) % len(self._options)
        elif direction == "down":
            self._selected = (self._selected + 1) % len(self._options)
        else:
            raise ValueError("direction must be 'up' or 'down'")

    def get_options(self) -> list:
        """Return the list of menu options."""
        return list(self._options)

    def get_selected_index(self) -> int:
        """Return the current selected index."""
        return int(self._selected)

    def confirm(self) -> None:
        """Confirm the currently selected option.

        If 'Quit' is selected, mark quit requested. If 'Resume', close the menu.
        """
        selected = self._options[self._selected]
        if selected == "Quit":
            self.request_quit()
        elif selected == "Resume":
            self.close()
        else:
            # Unknown option: ignore
            pass
