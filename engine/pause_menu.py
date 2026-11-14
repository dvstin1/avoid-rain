"""
PauseMenu: decoupled pause menu state machine that uses PauseHandler.

Provides open/close/toggle semantics without requiring rendering or input subsystems.
"""
from __future__ import annotations

from typing import Optional, Callable
from enum import Enum, auto
from .pause import PauseHandler
from .menu import MenuBase


class PauseMenuState(Enum):
    """States for the pause menu."""
    MAIN = auto()
    CONTROLS = auto()


class PauseMenu(MenuBase):
    """Simple pause menu controller.

    This class is intentionally UI-agnostic: it manages whether the
    menu is considered open and ensures the provided PauseHandler is
    paused while the menu is open.
    """

    def __init__(
        self,
        pause_handler: Optional[PauseHandler] = None,
        on_open: Optional[Callable[[], None]] = None,
        debug_text_enabled: bool = False,
        on_toggle_debug: Optional[Callable[[bool], None]] = None,
        screen_shake_enabled: bool = True,
        on_toggle_screen_shake: Optional[Callable[[bool], None]] = None,
        waiting_scholars: int = 0,
        return_to_sanctuary_visible: bool = False,
        on_return_to_sanctuary: Optional[Callable[[], None]] = None,
    ) -> None:
        self.debug_text_enabled = bool(debug_text_enabled)
        self.on_toggle_debug = on_toggle_debug
        self.screen_shake_enabled = bool(screen_shake_enabled)
        self.on_toggle_screen_shake = on_toggle_screen_shake
        self.waiting_scholars = max(0, int(waiting_scholars))
        self.return_to_sanctuary_visible = bool(return_to_sanctuary_visible or self.waiting_scholars > 0)
        self.on_return_to_sanctuary = on_return_to_sanctuary
        MenuBase.__init__(self, self._build_options())
        self.pause_handler = pause_handler or PauseHandler()
        self._open = False
        self._quit_requested = False
        self._return_to_sanctuary_requested = False
        self.state = PauseMenuState.MAIN
        # Optional callback invoked when the pause menu is opened (e.g., to auto-save)
        self.on_open = on_open

    def _build_options(self) -> list[str]:
        """Return pause menu options reflecting current toggle and Waiting Scholars states."""
        dbg_label = f"Debug Text: {'ON' if self.debug_text_enabled else 'OFF'}"
        shake_label = f"Screen Shake: {'ON' if self.screen_shake_enabled else 'OFF'}"
        options = ["Resume"]
        if self.return_to_sanctuary_visible:
            options.append("Return to Sanctuary")
        options.extend(["Controls", dbg_label, shake_label, "Quit"])
        return options

    def set_debug_text_enabled(self, enabled: bool) -> None:
        """Synchronize the pause menu's debug text state and option label."""
        self.debug_text_enabled = bool(enabled)
        self._options = self._build_options()

    def set_screen_shake_enabled(self, enabled: bool) -> None:
        """Synchronize the pause menu's screen shake state and option label."""
        self.screen_shake_enabled = bool(enabled)
        self._options = self._build_options()

    def set_waiting_scholars(self, count: int) -> None:
        """Update waiting scholar count and dynamically toggle Return to Sanctuary visibility."""
        new_count = max(0, int(count))
        if new_count == self.waiting_scholars:
            return
        self.waiting_scholars = new_count
        self.set_return_to_sanctuary_visible(self.waiting_scholars > 0)

    def set_return_to_sanctuary_visible(self, visible: bool) -> None:
        """Explicitly show or hide the 'Return to Sanctuary' option in the pause menu."""
        new_vis = bool(visible)
        if new_vis == self.return_to_sanctuary_visible:
            return
        self.return_to_sanctuary_visible = new_vis
        self._options = self._build_options()
        if self._selected >= len(self._options):
            self._selected = max(0, len(self._options) - 1)

    def open(self) -> None:
        """Open the pause menu and pause the game."""
        self._open = True
        self._quit_requested = False
        self._return_to_sanctuary_requested = False
        self.state = PauseMenuState.MAIN
        # reset selection to default
        self._selected = 0
        self.pause_handler.pause()
        # Call the optional on_open hook (used for autosave) without raising
        if self.on_open is not None:
            try:
                self.on_open()
            except Exception:
                # Keep pause behavior robust: do not let save errors break the menu
                pass

    def close(self) -> None:
        """Close the pause menu and resume the game."""
        self._open = False
        self.state = PauseMenuState.MAIN
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

    def request_quit(self) -> None:
        """Mark that the user requested to quit from the pause menu."""
        self._quit_requested = True

    def clear_quit(self) -> None:
        """Clear any pending quit request."""
        self._quit_requested = False

    def should_quit(self) -> bool:
        """Return True if quit was requested from the pause menu."""
        return bool(self._quit_requested)

    def request_return_to_sanctuary(self) -> None:
        """Mark that the user requested to return the party to Sanctuary."""
        self._return_to_sanctuary_requested = True

    def clear_return_to_sanctuary(self) -> None:
        """Clear any pending return-to-Sanctuary request."""
        self._return_to_sanctuary_requested = False

    def should_return_to_sanctuary(self) -> bool:
        """Return True if Return to Sanctuary was confirmed from the pause menu."""
        return bool(self._return_to_sanctuary_requested)

    def confirm(self) -> None:
        """Confirm the currently selected option.

        If 'Quit' is selected, mark quit requested. If 'Resume', close the menu.
        If 'Return to Sanctuary' is selected, request party return and close the menu.
        If 'Debug Text: ...' is selected, toggle debug text and invoke callback.
        """
        selected = self._options[self._selected]
        if selected == "Quit":
            self.request_quit()
        elif selected == "Resume":
            self.close()
        elif selected == "Return to Sanctuary":
            self.request_return_to_sanctuary()
            if self.on_return_to_sanctuary is not None:
                try:
                    self.on_return_to_sanctuary()
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
            self.close()
        elif selected.startswith("Debug Text:"):
            self.set_debug_text_enabled(not self.debug_text_enabled)
            if self.on_toggle_debug is not None:
                try:
                    self.on_toggle_debug(self.debug_text_enabled)
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
        elif selected.startswith("Screen Shake:"):
            self.set_screen_shake_enabled(not self.screen_shake_enabled)
            if self.on_toggle_screen_shake is not None:
                try:
                    self.on_toggle_screen_shake(self.screen_shake_enabled)
                except Exception:  # pylint: disable=broad-exception-caught
                    pass
