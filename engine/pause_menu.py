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

    def open(self) -> None:
        """Open the pause menu and pause the game."""
        self._open = True
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
