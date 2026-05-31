"""
AudioManager: Handles cross-platform audio initialization, asset loading,
and smooth crossfading between music tracks.
"""
import os
import pygame
from constants import FPS

class AudioManager:
    """Manages music and sound effect playback with smooth transitions."""
    def __init__(self):
        pygame.mixer.init()
        self.music_dir = os.path.join("assets", "audio", "music")
        self.current_track = None
        self.target_track = None
        self.fade_speed = 1.0 # Vol units per second
        self.volume = 1.0

    def update(self, dt, target_track_name):
        """Update music state, handling transitions to target_track_name."""
        if target_track_name != self.target_track:
            self.target_track = target_track_name
            self._start_fade_transition(target_track_name)

    def _start_fade_transition(self, track_name):
        """Start playing a new track with a crossfade."""
        path = os.path.join(self.music_dir, track_name)
        if not os.path.exists(path):
            # If track doesn't exist, just stop music
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1000)
            self.current_track = None
            return

        if self.current_track == track_name:
            return

        # Play new track with 2-second fade-in
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops=-1, fade_ms=2000)
            self.current_track = track_name
            print(f"[AUDIO] Now playing: {track_name}")
        except Exception as e:
            print(f"[AUDIO] Failed to play {track_name}: {e}")
