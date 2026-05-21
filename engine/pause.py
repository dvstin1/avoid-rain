"""
PauseHandler: decoupled pause state manager for game update loops.

Low-coupled utility that tracks paused/unpaused state and provides helpers
for components to decide whether they should perform updates.
"""
from __future__ import annotations

from typing import Iterator
from contextlib import contextmanager


class PauseHandler:
    """Manage a global paused flag for game systems.

    Methods:
    - pause(): set paused state
    - resume(): clear paused state
    - toggle(): flip paused state
    - is_paused(): query
    - should_update(): True when not paused (for update loops)
    - temporary_pause(): context manager that pauses for a block
    """

    def __init__(self) -> None:
        self._paused = False

    def pause(self) -> None:
        """Enter paused state."""
        self._paused = True

    def resume(self) -> None:
        """Exit paused state."""
        self._paused = False

    def toggle(self) -> None:
        """Toggle paused state."""
        self._paused = not self._paused

    def is_paused(self) -> bool:
        """Return True if currently paused."""
        return bool(self._paused)

    def should_update(self) -> bool:
        """Return True if systems should run their update logic (not paused)."""
        return not self._paused

    @contextmanager
    def temporary_pause(self) -> Iterator[None]:
        """Context manager that ensures paused state for the duration of the block.

        Restores the previous paused state on exit.
        """
        prev = self._paused
        try:
            self._paused = True
            yield
        finally:
            self._paused = bool(prev)
