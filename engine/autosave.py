"""Autosave manager that triggers periodic persistence of GameState statistics.

This lives as a separate low-coupled utility and calls GameState.save_stats()
when the configured interval elapses. It also manages a small state flag on
GameState (last_save_elapsed) that renderers can use to show visual feedback.
"""
from __future__ import annotations

from typing import Optional


class AutosaveManager:
    def __init__(self, interval: float = 30.0) -> None:
        self.interval = float(interval)
        self._acc = 0.0

    def update(self, dt: float, state: Optional[object]) -> None:
        """Advance internal timer by dt and trigger a save when interval reached.

        The state object is expected to implement save_stats() and have a
        last_save_elapsed attribute (which we reset to 0.0 on save). If those
        don't exist, the manager will still attempt to call save_stats() but
        will otherwise be tolerant and non-throwing.
        """
        if state is None:
            return

        self._acc += float(dt)

        # Update last_save_elapsed on state if present
        try:
            if getattr(state, 'last_save_elapsed', None) is not None:
                state.last_save_elapsed += float(dt)
        except Exception:
            # Keep robust: ignore increment failures
            pass

        if self._acc >= self.interval:
            # Trigger save
            try:
                if getattr(state, 'save_stats', None) is not None:
                    state.save_stats()
            except Exception:
                # Do not propagate save failures; autosave must be non-fatal
                pass

            # Reset accumulators and state timer
            self._acc = 0.0
            try:
                state.last_save_elapsed = 0.0
            except Exception:
                pass
