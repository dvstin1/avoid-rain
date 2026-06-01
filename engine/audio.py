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
        self.sfx_dir = os.path.join("assets", "audio", "sfx")
        
        self.current_track = None
        self.target_track = None
        self.volume = 1.0
        
        # SFX Registry
        self.sfx_cache = {}
        self.recent_sfx = [] # List of {'name': str, 'time': float} for debug OSD

    def update(self, dt, target_track_name):
        """Update music state and age out recent SFX for debug."""
        if target_track_name != self.target_track:
            self.target_track = target_track_name
            self._start_fade_transition(target_track_name)
            
        # Age out debug SFX info (show for 2 seconds)
        for item in self.recent_sfx[:]:
            item['time'] -= dt
            if item['time'] <= 0:
                self.recent_sfx.remove(item)

    def play_sfx(self, sfx_name):
        """Load and trigger an SFX file, with debug tracking."""
        # 1. Track for Debug OSD (even if file is missing)
        self.recent_sfx.append({'name': sfx_name, 'time': 2.0})
        
        path = os.path.join(self.sfx_dir, sfx_name)
        if not os.path.exists(path):
            return

        # 2. Play Audio
        try:
            if sfx_name not in self.sfx_cache:
                self.sfx_cache[sfx_name] = pygame.mixer.Sound(path)
            
            self.sfx_cache[sfx_name].play()
        except Exception as e:
            print(f"[AUDIO] SFX Playback Error ({sfx_name}): {e}")

    def _start_fade_transition(self, track_name):
        """Start playing a new track with an intelligent sequential fade."""
        path = os.path.join(self.music_dir, track_name)
        
        # Stability Check: If track doesn't exist, fade out and stop
        if not os.path.exists(path):
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(1500)
            self.current_track = None
            return

        if self.current_track == track_name:
            return

        # Seamless Transition: 
        # Immediate load and fade-in (zero-latency end of old track)
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(loops=-1, fade_ms=2000)
            self.current_track = track_name
            print(f"[AUDIO] Transition to: {track_name}")
        except Exception as e:
            print(f"[AUDIO] Playback Error for {track_name}: {e}")
