"""
TitleMenu: decoupled title screen menu state.

Provides navigation and confirmation for title screen options (Start, Quit).
"""
from __future__ import annotations

from typing import Optional


class TitleMenu:
    """Manage title screen menu state and confirmation flag."""

    def __init__(self) -> None:
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
        return int(self._selected)

    def get_options(self) -> list:
        return list(self._options)

    def confirm(self) -> None:
        self._confirmed = True

    def clear_confirm(self) -> None:
        self._confirmed = False

    def was_confirmed(self) -> bool:
        return bool(self._confirmed)

    def get_selected(self) -> str:
        return self._options[self._selected]
