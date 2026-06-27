# pylint: disable=too-many-instance-attributes,too-many-locals,too-many-branches,too-many-statements,broad-exception-caught,chained-comparison
"""
AudioManager: Handles cross-platform audio initialization, asset loading,
and smooth crossfading between music tracks.
"""
import os
import math
import pygame
from constants import SFX_FULL_VOLUME_DIST, SFX_MIN_VOLUME_DIST, SFX_MIN_VOLUME

class AudioManager:
    """Manages music and sound effect playback with smooth transitions."""
    def __init__(self):
        pygame.mixer.init()
        pygame.mixer.set_num_channels(32)
        self.music_dir = os.path.join("assets", "audio", "music")
        self.sfx_dir = os.path.join("assets", "audio", "sfx")

        self.current_track = None
        self.target_track = None
        self.volume = 1.0

        # SFX Registry
        self.sfx_cache = {}
        self.recent_sfx = [] # List of {'name': str, 'time': float} for debug OSD
        self.active_move_sounds = {} # Maps enemy_id -> pygame.mixer.Channel

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

    def calculate_spatial_volume(self, dist):
        """Calculate spatial volume based on distance to player."""
        if dist <= SFX_FULL_VOLUME_DIST:
            return 1.0
        if dist >= SFX_MIN_VOLUME_DIST:
            return SFX_MIN_VOLUME
        # Linear interpolation from 1.0 to SFX_MIN_VOLUME
        frac = (dist - SFX_FULL_VOLUME_DIST) / (SFX_MIN_VOLUME_DIST - SFX_FULL_VOLUME_DIST)
        return 1.0 - frac * (1.0 - SFX_MIN_VOLUME)

    def update_enemy_sounds(self, state):
        """Update continuous movement sounds for slugs and bats."""
        if not state.player:
            for channel in self.active_move_sounds.values():
                if channel:
                    try:
                        channel.stop()
                    except Exception:
                        pass
            self.active_move_sounds.clear()
            return

        player_cx, player_cy = state.player.get_center()

        slugs = []
        bats = []
        for enemy in state.enemies:
            if enemy.name == "Slug":
                slugs.append(enemy)
            elif enemy.name == "Bat":
                bats.append(enemy)

        def process_type(enemies):
            moving = [
                e for e in enemies
                if e.hp > 0 and e.stagger_timer <= 0 and (abs(e.vx) > 1.0 or abs(e.vy) > 1.0)
            ]
            with_dist = []
            for e in moving:
                ecx, ecy = e.get_center()
                d = math.hypot(ecx - player_cx, ecy - player_cy)
                with_dist.append((e, d))
            with_dist.sort(key=lambda item: item[1])
            return with_dist[:2]

        top_slugs = process_type(slugs)
        top_bats = process_type(bats)

        allowed_ids = set()

        for e, d in top_slugs + top_bats:
            enemy_id = id(e)
            allowed_ids.add(enemy_id)
            sfx_name = "slug_move.ogg" if e.name == "Slug" else "bat_move.ogg"
            vol = self.calculate_spatial_volume(d)

            if enemy_id in self.active_move_sounds:
                channel = self.active_move_sounds[enemy_id]
                if channel and channel.get_busy():
                    channel.set_volume(vol)
                else:
                    self.active_move_sounds.pop(enemy_id, None)

            if enemy_id not in self.active_move_sounds:
                sound = self.sfx_cache.get(sfx_name)
                if not sound:
                    path = os.path.join(self.sfx_dir, sfx_name)
                    if os.path.exists(path):
                        try:
                            sound = pygame.mixer.Sound(path)
                            self.sfx_cache[sfx_name] = sound
                        except Exception as exc:
                            print(f"[AUDIO] Error loading move SFX {sfx_name}: {exc}")

                if sound:
                    try:
                        channel = sound.play(loops=-1)
                        if channel:
                            channel.set_volume(vol)
                            self.active_move_sounds[enemy_id] = channel
                    except Exception as exc:
                        print(f"[AUDIO] Error playing looped SFX {sfx_name}: {exc}")

        # Stop sounds that are no longer allowed
        for enemy_id in list(self.active_move_sounds.keys()):
            if enemy_id not in allowed_ids:
                channel = self.active_move_sounds[enemy_id]
                if channel:
                    try:
                        channel.stop()
                    except Exception:
                        pass
                self.active_move_sounds.pop(enemy_id, None)

    def play_sfx(self, sfx_name, volume=1.0):
        """Load and trigger an SFX file, with debug tracking and volume."""
        self.recent_sfx.append({'name': sfx_name, 'time': 2.0})

        path = os.path.join(self.sfx_dir, sfx_name)
        if not os.path.exists(path):
            return

        try:
            if sfx_name not in self.sfx_cache:
                self.sfx_cache[sfx_name] = pygame.mixer.Sound(path)

            sound = self.sfx_cache[sfx_name]

            if sfx_name in ("slug_attack.ogg", "bat_attack.ogg"):
                if sound.get_num_channels() >= 4:
                    return

            channel = sound.play()
            if channel:
                channel.set_volume(volume)
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
