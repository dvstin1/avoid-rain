"""
TitleMenu: decoupled title screen menu state.

Provides navigation and confirmation for title screen options (Start, Quit).
"""
from __future__ import annotations



from .menu import MenuBase


class TitleMenu(MenuBase):
    """Manage title screen menu state and confirmation flag.

    Uses MenuBase for navigation helpers.
    """

    def __init__(self) -> None:
        super().__init__(["Start", "Quit"])
        self._confirmed = False

    def confirm(self) -> None:
        """Mark that the current selection was confirmed."""
        self._confirmed = True

    def clear_confirm(self) -> None:
        """Clear the confirmation flag."""
        self._confirmed = False

    def was_confirmed(self) -> bool:
        """Return True if selection was confirmed."""
        return bool(self._confirmed)
