"""
PauseMenu: decoupled pause menu state machine that uses PauseHandler.

Provides open/close/toggle semantics without requiring rendering or input subsystems.
"""
from __future__ import annotations

from typing import Optional, Callable
from enum import Enum, auto
from .pause import PauseHandler
from .menu import MenuBase


class PauseMenuState(Enum):
    """States for the pause menu."""
    MAIN = auto()
    CONTROLS = auto()


class PauseMenu(MenuBase):
    """Simple pause menu controller.

    This class is intentionally UI-agnostic: it manages whether the
    menu is considered open and ensures the provided PauseHandler is
    paused while the menu is open.
    """

    def __init__(self, pause_handler: Optional[PauseHandler] = None, on_open: Optional[Callable[[], None]] = None) -> None:
        MenuBase.__init__(self, ["Resume", "Controls", "Quit"])
        self.pause_handler = pause_handler or PauseHandler()
        self._open = False
        self._quit_requested = False
        self.state = PauseMenuState.MAIN
        # Optional callback invoked when the pause menu is opened (e.g., to auto-save)
        self.on_open = on_open

    def open(self) -> None:
        """Open the pause menu and pause the game."""
        self._open = True
        self._quit_requested = False
        self.state = PauseMenuState.MAIN
        # reset selection to default
        self._selected = 0
        self.pause_handler.pause()
        # Call the optional on_open hook (used for autosave) without raising
        if self.on_open is not None:
            try:
                self.on_open()
            except Exception:
                # Keep pause behavior robust: do not let save errors break the menu
                pass

    def close(self) -> None:
        """Close the pause menu and resume the game."""
        self._open = False
        self.state = PauseMenuState.MAIN
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
