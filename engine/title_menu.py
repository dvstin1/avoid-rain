"""
TitleMenu: decoupled title screen menu state.

Provides navigation and confirmation for title screen options (Start, Quit).
"""
from __future__ import annotations
from enum import Enum, auto

from .menu import MenuBase

class TitleMenuState(Enum):
    """States for the title menu."""
    MAIN = auto()
    CONFIRM_NEW_GAME = auto()
    CONTROLS = auto()
    LOBBY = auto()

class TitleMenu(MenuBase):
    """Manage title screen menu state and confirmation flag.

    The menu adjusts options depending on whether save data exists.
    If has_save is False (default): options = ["New Draft", "Join Game", "Controls", "Quit"]
    If has_save is True: options = ["New Draft", "Continue", "Join Game", "Controls", "Quit"] with
    "Continue" selected by default.
    """

    def __init__(self, has_save: bool = False) -> None:
        self._has_save = bool(has_save)
        options = ["New Draft", "Join Game", "Controls", "Quit"] if not self._has_save else ["New Draft", "Continue", "Join Game", "Controls", "Quit"]
        super().__init__(options)
        # Set default selection: when a save exists, default to Continue
        if self._has_save:
            # index 1 = Continue
            self._selected = 1
        self._confirmed = False
        self.state = TitleMenuState.MAIN

    def set_has_save(self, has_save: bool) -> None:
        """Update menu options based on presence of save data.

        Calling this will reset the options list and selection appropriately.
        """
        # Update internal state and options without dunder __init__ call
        self._has_save = bool(has_save)
        self._options = ["New Draft", "Join Game", "Controls", "Quit"] if not self._has_save else ["New Draft", "Continue", "Join Game", "Controls", "Quit"]
        if self._has_save:
            self._selected = 1
        else:
            self._selected = 0

    def confirm(self) -> None:
        """Mark that the current selection was confirmed."""
        self._confirmed = True

    def clear_confirm(self) -> None:
        """Clear the confirmation flag."""
        self._confirmed = False

    def was_confirmed(self) -> bool:
        """Return True if selection was confirmed."""
        return bool(self._confirmed)
