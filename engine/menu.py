# copyright 2026 Dustin Massop, License: GPLv2
"""
MenuBase: shared navigation helpers for simple menu controllers.

Provides navigate/get_selected_index/get_options/get_selected to avoid duplicated
implementations across small UI-agnostic menu controllers.
"""
from __future__ import annotations

from constants import MENU_TRANSITION_DURATION, compute_menu_transition_state


class MenuBase:
    """Simple reusable menu helper for small UI controllers."""

    def __init__(self, options: list[str], transition_duration: float = MENU_TRANSITION_DURATION) -> None:
        self._options = list(options)
        self._selected = 0
        self._transition_duration = max(1e-4, float(transition_duration))
        self._transition_elapsed = 0.0
        self._transition_progress = 0.0

    @property
    def transition_progress(self) -> float:
        """Return normalized [0.0, 1.0] parchment unroll transition progress."""
        return float(self._transition_progress)

    def reset_transition(self, duration: float | None = None) -> None:
        """Restart the parchment unroll transition from 0.0."""
        if duration is not None:
            self._transition_duration = max(1e-4, float(duration))
        self._transition_elapsed = 0.0
        self._transition_progress = 0.0

    def finish_transition(self) -> None:
        """Immediately snap the menu transition to its settled 1.0 state."""
        self._transition_elapsed = self._transition_duration
        self._transition_progress = 1.0

    def update_transition(self, dt: float) -> float:
        """Advance dt-driven menu transition progress in [0.0, 1.0] without blocking input."""
        step = max(0.0, float(dt))
        self._transition_elapsed = min(self._transition_duration, self._transition_elapsed + step)
        self._transition_progress = min(1.0, self._transition_elapsed / self._transition_duration)
        return self._transition_progress

    def get_transition_state(self) -> dict:
        """Return computed easing, reveal ratio, slide offset, and alpha metrics."""
        return compute_menu_transition_state(self._transition_progress)

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
