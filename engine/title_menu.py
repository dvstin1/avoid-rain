"""
TitleMenu: decoupled title screen menu state.

Provides navigation and confirmation for title screen options (Start, Quit).
"""
from __future__ import annotations



class TitleMenu:
    """Manage title screen menu state and confirmation flag.

    Methods are intentionally small and documented to satisfy linting.
    """

    def __init__(self) -> None:
        """Initialize title menu with default options and selection."""
        self._options = ["Start", "Quit"]
        self._selected = 0
        self._confirmed = False

    def navigate(self, direction: str) -> None:
        """Navigate menu; direction is 'up' or 'down'."""
        if direction == "up":
            self._selected = (self._selected - 1) % len(self._options)
        elif direction == "down":
            self._selected = (self._selected + 1) % len(self._options)
        else:
            raise ValueError("direction must be 'up' or 'down'")

    def get_selected_index(self) -> int:
        """Return the currently selected index."""
        return int(self._selected)

    def get_options(self) -> list:
        """Return a copy of the options list."""
        return list(self._options)

    def confirm(self) -> None:
        """Mark that the current selection was confirmed."""
        self._confirmed = True

    def clear_confirm(self) -> None:
        """Clear the confirmation flag."""
        self._confirmed = False

    def was_confirmed(self) -> bool:
        """Return True if selection was confirmed."""
        return bool(self._confirmed)

    def get_selected(self) -> str:
        """Return the currently selected option string."""
        return self._options[self._selected]
