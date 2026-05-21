"""
MenuBase: shared navigation helpers for simple menu controllers.

Provides navigate/get_selected_index/get_options/get_selected to avoid duplicated
implementations across small UI-agnostic menu controllers.
"""
from __future__ import annotations


class MenuBase:
    """Simple reusable menu helper for small UI controllers."""

    def __init__(self, options: list[str]) -> None:
        self._options = list(options)
        self._selected = 0

    def navigate(self, direction: str) -> None:
        """Navigate the menu; direction is 'up' or 'down'."""
        if direction == "up":
            self._selected = (self._selected - 1) % len(self._options)
        elif direction == "down":
            self._selected = (self._selected + 1) % len(self._options)
        else:
            raise ValueError("direction must be 'up' or 'down'")

    def get_options(self) -> list:
        """Return a copy of the options list."""
        return list(self._options)

    def get_selected_index(self) -> int:
        """Return the currently selected index."""
        return int(self._selected)

    def get_selected(self) -> str:
        """Return the currently selected option string."""
        return self._options[self._selected]
