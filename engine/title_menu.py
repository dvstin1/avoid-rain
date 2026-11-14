"""
TitleMenu: decoupled title screen menu state.

Provides navigation and confirmation for title screen options (Start, Quit).
"""
from __future__ import annotations
from enum import Enum, auto

from constants import (
    STORM_INTRO_SFX,
    TITLE_LIGHTNING_BOLTS,
    TITLE_TRANSITION_FADE_IN_DURATION,
    TITLE_TRANSITION_FADE_OUT_DURATION,
    TITLE_TRANSITION_STORM_DURATION,
)
from .menu import MenuBase

class TitleMenuState(Enum):
    """States for the title menu."""
    MAIN = auto()
    CONFIRM_NEW_GAME = auto()
    CONTROLS = auto()


class TitleMenu(MenuBase):
    """Manage title screen menu state, Online/Offline mode toggle, and confirmation flag.

    The menu adjusts options depending on whether save data exists.
    If has_save is False (default): options = ["New Draft", "Mode: Online", "Controls", "Quit"]
    If has_save is True: options = ["New Draft", "Continue", "Mode: Online", "Controls", "Quit"] with
    "Continue" selected by default.
    """

    def __init__(self, has_save: bool = False, online_mode: bool = True) -> None:
        self._has_save = bool(has_save)
        self.online_mode = bool(online_mode)
        super().__init__(self._build_options())
        # Set default selection: when a save exists, default to Continue
        if self._has_save:
            # index 1 = Continue
            self._selected = 1
        self._confirmed = False
        self.state = TitleMenuState.MAIN

    def _build_options(self) -> list[str]:
        """Return title menu options reflecting save presence and Online/Offline mode."""
        mode_label = f"Mode: {'Online' if self.online_mode else 'Offline'}"
        if not self._has_save:
            return ["New Draft", mode_label, "Controls", "Quit"]
        return ["New Draft", "Continue", mode_label, "Controls", "Quit"]

    def set_has_save(self, has_save: bool) -> None:
        """Update menu options based on presence of save data.

        Calling this will reset the options list and selection appropriately.
        """
        self._has_save = bool(has_save)
        self._options = self._build_options()
        if self._has_save:
            self._selected = 1
        else:
            self._selected = 0

    def set_online_mode(self, online_mode: bool) -> None:
        """Synchronize the Online/Offline mode state and update its option label."""
        self.online_mode = bool(online_mode)
        self._options = self._build_options()

    def toggle_online_mode(self) -> bool:
        """Toggle between Online and Offline modes and return the new boolean value."""
        self.set_online_mode(not self.online_mode)
        return self.online_mode

    def confirm(self) -> None:
        """Mark that the current selection was confirmed."""
        self._confirmed = True

    def clear_confirm(self) -> None:
        """Clear the confirmation flag."""
        self._confirmed = False

    def was_confirmed(self) -> bool:
        """Return True if selection was confirmed."""
        return bool(self._confirmed)


class TitleTransitionPhase(Enum):
    """Phases for the title-to-Sanctuary storm-and-lightning transition."""
    IDLE = auto()
    FADE_TO_BLACK = auto()
    STORM_VIGNETTE = auto()
    FADE_OUT_AND_WARP = auto()
    COMPLETE = auto()


class TitleTransition:
    """Headless multi-phase transition controller from Title Screen to Sanctuary."""

    def __init__(self) -> None:
        self.phase = TitleTransitionPhase.IDLE
        self.timer = 0.0
        self.mode: str | None = None
        self.audio_triggered = False
        self.skipped = False

    def start(self, mode: str) -> None:
        """Begin Phase 1 (Fade to Black) for the given start mode."""
        self.mode = mode
        self.phase = TitleTransitionPhase.FADE_TO_BLACK
        self.timer = 0.0
        self.audio_triggered = False
        self.skipped = False

    def reset(self) -> None:
        """Reset transition back to IDLE."""
        self.phase = TitleTransitionPhase.IDLE
        self.timer = 0.0
        self.mode = None
        self.audio_triggered = False
        self.skipped = False

    def is_active(self) -> bool:
        """Return True while the transition is actively playing."""
        return self.phase not in (TitleTransitionPhase.IDLE, TitleTransitionPhase.COMPLETE)

    def skip(self) -> None:
        """Immediately skip to COMPLETE when active."""
        if self.is_active():
            self.skipped = True
            self.phase = TitleTransitionPhase.COMPLETE

    def update(self, dt: float, audio_manager=None) -> bool:
        """Advance transition timers; returns True when COMPLETE."""
        if self.phase == TitleTransitionPhase.IDLE:
            return False
        if self.phase == TitleTransitionPhase.COMPLETE:
            return True

        self.timer += max(0.0, float(dt))

        if self.phase == TitleTransitionPhase.FADE_TO_BLACK:
            if self.timer >= TITLE_TRANSITION_FADE_IN_DURATION:
                self.phase = TitleTransitionPhase.STORM_VIGNETTE
                self.timer = 0.0
                if not self.audio_triggered:
                    self.audio_triggered = True
                    if audio_manager is not None:
                        audio_manager.play_sfx(STORM_INTRO_SFX)
        elif self.phase == TitleTransitionPhase.STORM_VIGNETTE:
            if not self.audio_triggered:
                self.audio_triggered = True
                if audio_manager is not None:
                    audio_manager.play_sfx(STORM_INTRO_SFX)
            if self.timer >= TITLE_TRANSITION_STORM_DURATION:
                self.phase = TitleTransitionPhase.FADE_OUT_AND_WARP
                self.timer = 0.0
        elif self.phase == TitleTransitionPhase.FADE_OUT_AND_WARP:
            if self.timer >= TITLE_TRANSITION_FADE_OUT_DURATION:
                self.phase = TitleTransitionPhase.COMPLETE
                return True

        return self.phase == TitleTransitionPhase.COMPLETE

    def get_fade_alpha(self) -> int:
        """Return black overlay alpha (0..255) for fade phases."""
        if self.phase == TitleTransitionPhase.FADE_TO_BLACK:
            frac = min(1.0, self.timer / max(1e-6, TITLE_TRANSITION_FADE_IN_DURATION))
            return int(round(255 * frac))
        if self.phase == TitleTransitionPhase.FADE_OUT_AND_WARP:
            frac = min(1.0, self.timer / max(1e-6, TITLE_TRANSITION_FADE_OUT_DURATION))
            return int(round(255 * frac))
        if self.phase == TitleTransitionPhase.COMPLETE:
            return 255
        return 0

    def get_lightning_flash(self) -> float:
        """Return normalized [0.0, 1.0] lightning sky-illumination intensity."""
        if self.phase != TitleTransitionPhase.STORM_VIGNETTE:
            return 0.0
        peak = 0.0
        for start_t, dur in TITLE_LIGHTNING_BOLTS:
            if start_t <= self.timer <= start_t + dur:
                local = (self.timer - start_t) / max(1e-6, dur)
                intensity = max(0.0, 1.0 - local) ** 1.6
                peak = max(peak, intensity)
        return peak

    def get_active_bolt_index(self) -> int | None:
        """Return the index of the currently flashing lightning bolt, if any."""
        if self.phase != TitleTransitionPhase.STORM_VIGNETTE:
            return None
        for idx, (start_t, dur) in enumerate(TITLE_LIGHTNING_BOLTS):
            if start_t <= self.timer <= start_t + dur:
                return idx
        return None
