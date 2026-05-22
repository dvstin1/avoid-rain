"""
TitleMenu: decoupled title screen menu state.

Provides navigation and confirmation for title screen options (Start, Quit).
"""
from __future__ import annotations



from .menu import MenuBase


class TitleMenu(MenuBase):
    """Manage title screen menu state and confirmation flag.

    The menu adjusts options depending on whether save data exists.
    If has_save is False (default): options = ["New Game", "Quit"]
    If has_save is True: options = ["New Game", "Continue", "Quit"] with
    "Continue" selected by default.
    """

    def __init__(self, has_save: bool = False) -> None:
        self._has_save = bool(has_save)
        options = ["New Game", "Quit"] if not self._has_save else ["New Game", "Continue", "Quit"]
        super().__init__(options)
        # Set default selection: when a save exists, default to Continue
        if self._has_save:
            # index 1 = Continue
            self._selected = 1
        self._confirmed = False

    def set_has_save(self, has_save: bool) -> None:
        """Update menu options based on presence of save data.

        Calling this will reset the options list and selection appropriately.
        """
        # Reinitialize options and selection while preserving the confirm flag
        self.__init__(has_save=has_save)

    def confirm(self) -> None:
        """Mark that the current selection was confirmed."""
        self._confirmed = True

    def clear_confirm(self) -> None:
        """Clear the confirmation flag."""
        self._confirmed = False

    def was_confirmed(self) -> bool:
        """Return True if selection was confirmed."""
        return bool(self._confirmed)
