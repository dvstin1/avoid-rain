# copyright 2026 Dustin Massop, License: GPLv2
# pylint: disable=too-many-instance-attributes,too-many-locals,too-many-branches,too-many-statements,broad-exception-caught,chained-comparison
"""
AudioManager: Handles cross-platform audio initialization, asset loading,
and smooth crossfading between music tracks.
"""
import os
import math
import random
import pygame
from constants import (
    AMBIENT_AUTHOR_RUMBLE_SFX,
    AMBIENT_FLAME_SFX,
    AMBIENT_WATER_SFX,
    ENV_AUDIO_CANDELABRA_VOL_MULT,
    ENV_AUDIO_CHALICE_VOL_MULT,
    ENV_AUDIO_FADE_RATE,
    ENV_AUDIO_FLAME_BASE_VOL,
    ENV_AUDIO_FLAME_FULL_DIST,
    ENV_AUDIO_FLAME_MAX_DIST,
    ENV_AUDIO_MAX_CHANNELS,
    ENV_AUDIO_MAX_PAN_BIAS,
    ENV_AUDIO_PAN_RANGE,
    ENV_AUDIO_RUMBLE_BASE_VOL,
    ENV_AUDIO_RUMBLE_FULL_DIST,
    ENV_AUDIO_RUMBLE_MAX_DIST,
    ENV_AUDIO_RUMBLE_MIN_LATE_STORM,
    ENV_AUDIO_SLOTS,
    ENV_AUDIO_STOP_EPSILON,
    ENV_AUDIO_WATER_BASE_VOL,
    ENV_AUDIO_WATER_FULL_DIST,
    ENV_AUDIO_WATER_MAX_DIST,
    ENV_AUDIO_POND_VOL_MULT,
    ENV_AUDIO_WELLSPRING_VOL_MULT,
    RAIN_LOOP_SFX,
    SFX_FULL_VOLUME_DIST,
    SFX_MIN_VOLUME,
    SFX_MIN_VOLUME_DIST,
    SFX_VOLUME_SCALE,
    TILE_SIZE,
    compute_stereo_volumes,
)

ENV_AUDIO_SLOT_FILES = {
    "flame": AMBIENT_FLAME_SFX,
    "water": AMBIENT_WATER_SFX,
    "author_rumble": AMBIENT_AUTHOR_RUMBLE_SFX,
}


class AudioManager:
    """Manages music and sound effect playback with smooth transitions."""
    def __init__(self):
        pygame.mixer.init()
        pygame.mixer.set_num_channels(32)
        self.rain_channel = None
        self.env_channels = {}
        self.env_levels = {slot: (0.0, 0.0) for slot in ENV_AUDIO_SLOTS}
        self._env_world_sig = None
        try:
            pygame.mixer.set_reserved(1 + ENV_AUDIO_MAX_CHANNELS)
            self.rain_channel = pygame.mixer.Channel(0)
            for idx, slot in enumerate(ENV_AUDIO_SLOTS, start=1):
                self.env_channels[slot] = pygame.mixer.Channel(idx)
        except Exception:
            self.rain_channel = None
            self.env_channels = {}
        self.music_dir = os.path.join("assets", "audio", "music")
        self.sfx_dir = os.path.join("assets", "audio", "sfx")

        self.current_track = None
        self.target_track = None
        self.volume = 1.0

        # SFX Registry
        self.sfx_cache = {}
        self.sfx_pitch_cache = {}
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

    def calculate_stereo_volumes(
        self,
        dx: float,
        dy: float,
        max_dist: float = SFX_MIN_VOLUME_DIST,
        full_dist: float = SFX_FULL_VOLUME_DIST,
        base_volume: float = 1.0,
        min_attenuation: float = 0.0,
    ) -> tuple:
        """Compute stereo (left, right) gains scaled by master volume for a relative offset (dx, dy)."""
        master = max(0.0, min(1.0, float(self.volume)))
        return compute_stereo_volumes(
            dx,
            dy,
            max_dist=max_dist,
            full_dist=full_dist,
            base_volume=float(base_volume) * master,
            pan_range=ENV_AUDIO_PAN_RANGE,
            max_pan_bias=ENV_AUDIO_MAX_PAN_BIAS,
            min_attenuation=min_attenuation,
        )

    def _load_sfx_cached(self, sfx_name: str):
        """Load and cache a Sound object from sfx_dir, returning None if unavailable."""
        sound = self.sfx_cache.get(sfx_name)
        if sound is not None:
            return sound
        path = os.path.join(self.sfx_dir, sfx_name)
        if not os.path.exists(path):
            return None
        try:
            sound = pygame.mixer.Sound(path)
            self.sfx_cache[sfx_name] = sound
            return sound
        except Exception as exc:
            print(f"[AUDIO] Error loading SFX {sfx_name}: {exc}")
            return None

    def stop_environment_audio(self):
        """Stop and clear all actively looping directional environment audio channels."""
        for slot in ENV_AUDIO_SLOTS:
            channel = self.env_channels.get(slot)
            if channel is not None:
                try:
                    if channel.get_busy():
                        channel.stop()
                except Exception:
                    pass
            self.env_levels[slot] = (0.0, 0.0)

    def _compute_environment_targets(self, state) -> dict:
        """Evaluate directional stereo (left, right) targets for flame, water, and Author rumble."""
        targets = {slot: (0.0, 0.0) for slot in ENV_AUDIO_SLOTS}
        player = getattr(state, "player", None)
        world = getattr(state, "world", None)
        if player is None or world is None or not hasattr(player, "get_center"):
            return targets

        px, py = player.get_center()
        best_flame = (0.0, 0.0)
        best_water = (0.0, 0.0)

        for obj in getattr(world, "interactables", None) or ():
            obj_name = str(getattr(obj, "name", "") or "")
            ox = float(getattr(obj, "x", 0.0)) + float(getattr(obj, "width", TILE_SIZE)) * 0.5
            oy = float(getattr(obj, "y", 0.0)) + float(getattr(obj, "height", TILE_SIZE)) * 0.5
            dx, dy = ox - px, oy - py

            if obj_name in ("Candelabra", "Fire Chalice"):
                mult = ENV_AUDIO_CHALICE_VOL_MULT if obj_name == "Fire Chalice" else ENV_AUDIO_CANDELABRA_VOL_MULT
                cand = self.calculate_stereo_volumes(
                    dx,
                    dy,
                    max_dist=ENV_AUDIO_FLAME_MAX_DIST,
                    full_dist=ENV_AUDIO_FLAME_FULL_DIST,
                    base_volume=min(1.0, ENV_AUDIO_FLAME_BASE_VOL * mult),
                )
                if max(cand) > max(best_flame):
                    best_flame = cand
            elif obj_name == "The Wellspring" or obj.__class__.__name__ == "Wellspring":
                cand = self.calculate_stereo_volumes(
                    dx,
                    dy,
                    max_dist=ENV_AUDIO_WATER_MAX_DIST,
                    full_dist=ENV_AUDIO_WATER_FULL_DIST,
                    base_volume=ENV_AUDIO_WATER_BASE_VOL * ENV_AUDIO_WELLSPRING_VOL_MULT,
                )
                if max(cand) > max(best_water):
                    best_water = cand

        # Optional nearby Sanctuary pond or Sunlit Aqueducts channel water hum
        world_name = str(getattr(world, "name", "") or "")
        if world_name == "sanctuary":
            zones = getattr(world, "sanctuary_zones", None)
            pond_tiles = zones.get("pond_water", ()) if isinstance(zones, dict) else ()
            if pond_tiles:
                nearest_sq = float("inf")
                best_dx, best_dy = 0.0, 0.0
                for entry in pond_tiles:
                    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                        tx_c = entry[0] * TILE_SIZE + TILE_SIZE * 0.5
                        ty_c = entry[1] * TILE_SIZE + TILE_SIZE * 0.5
                        ddx, ddy = tx_c - px, ty_c - py
                        d_sq = ddx * ddx + ddy * ddy
                        if d_sq < nearest_sq:
                            nearest_sq = d_sq
                            best_dx, best_dy = ddx, ddy
                if nearest_sq < ENV_AUDIO_WATER_MAX_DIST ** 2:
                    cand = self.calculate_stereo_volumes(
                        best_dx,
                        best_dy,
                        max_dist=ENV_AUDIO_WATER_MAX_DIST,
                        full_dist=ENV_AUDIO_WATER_FULL_DIST,
                        base_volume=ENV_AUDIO_WATER_BASE_VOL * ENV_AUDIO_POND_VOL_MULT,
                    )
                    if max(cand) > max(best_water):
                        best_water = cand
        elif world_name == "sunlit_aqueducts" and hasattr(world, "is_in_shallow_water"):
            # Lightweight local probe around player for adjacent sunlit aqueduct channels
            p_rect = getattr(player, "rect", None)
            if p_rect is not None and world.is_in_shallow_water(p_rect):
                cand = self.calculate_stereo_volumes(
                    0.0,
                    0.0,
                    max_dist=ENV_AUDIO_WATER_MAX_DIST,
                    full_dist=ENV_AUDIO_WATER_FULL_DIST,
                    base_volume=ENV_AUDIO_WATER_BASE_VOL * 0.70,
                )
                if max(cand) > max(best_water):
                    best_water = cand

        targets["flame"] = best_flame
        targets["water"] = best_water

        # Distant subterranean rumble of the Author's madness (suppressed in Sanctuary)
        in_sanctuary = bool(getattr(state, "in_sanctuary", False)) or world_name == "sanctuary"
        if not in_sanctuary:
            targets["author_rumble"] = self._compute_author_rumble_target(state, world, px, py)

        return targets

    def _compute_author_rumble_target(self, state, world, px: float, py: float) -> tuple:
        """Compute directional stereo target for the Author's distant madness rumble."""
        world_name = str(getattr(world, "name", "") or "")
        enemies = getattr(state, "enemies", None) or ()
        final_author = None
        night_boss = None
        for enemy in enemies:
            if getattr(enemy, "hp", 0) <= 0:
                continue
            cls_name = enemy.__class__.__name__
            if cls_name == "FinalAuthor" or getattr(enemy, "name", "") == "The Final Author":
                final_author = enemy
                break
            if cls_name in ("NightBoss", "SlugBoss", "MeadowCensorBoss", "RimecrestArbiterBoss"):
                night_boss = enemy

        wm = getattr(state, "weather_manager", None)
        bleed_state = str(getattr(wm, "bleed_state", "") or "") if wm is not None else ""
        step_idx = int(getattr(wm, "current_step_idx", 0) or 0) if wm is not None else 0

        if final_author is not None or world_name in ("night_boss_arena", "final_boss"):
            if final_author is not None and hasattr(final_author, "get_center"):
                ax, ay = final_author.get_center()
            else:
                grid = getattr(world, "grid", None) or []
                ax = (len(grid[0]) * TILE_SIZE * 0.5) if grid and grid[0] else px
                ay = (len(grid) * TILE_SIZE * 0.5) if grid else py
            return self.calculate_stereo_volumes(
                ax - px,
                ay - py,
                max_dist=ENV_AUDIO_RUMBLE_MAX_DIST,
                full_dist=ENV_AUDIO_RUMBLE_FULL_DIST,
                base_volume=ENV_AUDIO_RUMBLE_BASE_VOL,
                min_attenuation=ENV_AUDIO_RUMBLE_MIN_LATE_STORM,
            )

        if bleed_state in ("GRACE_PERIOD", "DILUTION", "") and night_boss is None:
            return (0.0, 0.0)

        anchor_x, anchor_y = px, py
        if night_boss is not None and hasattr(night_boss, "get_center"):
            anchor_x, anchor_y = night_boss.get_center()
        elif wm is not None and hasattr(wm, "get_current_boss_coords"):
            coords = wm.get_current_boss_coords()
            if isinstance(coords, dict) and "x" in coords and "y" in coords:
                anchor_x = float(coords["x"]) * TILE_SIZE + TILE_SIZE * 0.5
                anchor_y = float(coords["y"]) * TILE_SIZE + TILE_SIZE * 0.5

        if night_boss is not None or bleed_state in ("BOSS_PHASE", "CLAMPED"):
            intensity = 1.0
            floor_atten = ENV_AUDIO_RUMBLE_MIN_LATE_STORM
        elif step_idx >= 2:
            intensity = 0.82
            floor_atten = ENV_AUDIO_RUMBLE_MIN_LATE_STORM * 0.75
        elif step_idx == 1:
            intensity = 0.50
            floor_atten = 0.0
        else:
            intensity = 0.28
            floor_atten = 0.0

        return self.calculate_stereo_volumes(
            anchor_x - px,
            anchor_y - py,
            max_dist=ENV_AUDIO_RUMBLE_MAX_DIST,
            full_dist=ENV_AUDIO_RUMBLE_FULL_DIST,
            base_volume=ENV_AUDIO_RUMBLE_BASE_VOL * intensity,
            min_attenuation=floor_atten,
        )

    def update_environment_audio(self, state, dt: float = 0.016, paused: bool = False) -> dict:
        """Update capped, directional stereo ambient loops for flames, water, and the Author's rumble."""
        if paused or state is None or getattr(state, "player", None) is None or getattr(state, "world", None) is None:
            self.stop_environment_audio()
            return dict(self.env_levels)

        world = state.world
        world_sig = (id(world), getattr(world, "name", ""))
        if self._env_world_sig is not None and world_sig != self._env_world_sig:
            self.stop_environment_audio()
        self._env_world_sig = world_sig

        targets = self._compute_environment_targets(state)
        step = max(0.0, float(dt))
        ramp = 1.0 if step <= 0.0 else min(1.0, step * ENV_AUDIO_FADE_RATE)

        for slot in ENV_AUDIO_SLOTS:
            cur_l, cur_r = self.env_levels.get(slot, (0.0, 0.0))
            tgt_l, tgt_r = targets.get(slot, (0.0, 0.0))
            new_l = cur_l + (tgt_l - cur_l) * ramp
            new_r = cur_r + (tgt_r - cur_r) * ramp
            if max(new_l, new_r) <= ENV_AUDIO_STOP_EPSILON and max(tgt_l, tgt_r) <= ENV_AUDIO_STOP_EPSILON:
                new_l, new_r = 0.0, 0.0
            self.env_levels[slot] = (new_l, new_r)

            channel = self.env_channels.get(slot)
            if channel is None:
                continue

            if max(new_l, new_r) <= ENV_AUDIO_STOP_EPSILON:
                try:
                    if channel.get_busy():
                        channel.stop()
                except Exception:
                    pass
                continue

            sfx_name = ENV_AUDIO_SLOT_FILES[slot]
            sound = self._load_sfx_cached(sfx_name)
            if sound is None:
                continue
            try:
                if not channel.get_busy():
                    channel.play(sound, loops=-1)
                channel.set_volume(new_l, new_r)
            except Exception as exc:
                print(f"[AUDIO] Error updating environment loop {sfx_name}: {exc}")

        return dict(self.env_levels)

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

    def stop_enemy_move_sounds(self):
        """Stop and clear all actively looping enemy movement SFX channels."""
        for channel in list(self.active_move_sounds.values()):
            if channel:
                try:
                    channel.stop()
                except Exception:
                    pass
        self.active_move_sounds.clear()

    def update_rain_audio(self, intensity: float, paused: bool = False):
        """Play or adjust the looping ambient rain channel based on intensity and pause state."""
        if not self.rain_channel:
            return
        effective_vol = 0.0 if paused else max(0.0, min(1.0, float(intensity))) * self.volume
        if effective_vol <= 0.001:
            try:
                if self.rain_channel.get_busy():
                    self.rain_channel.stop()
            except Exception:
                pass
            return

        sound = self.sfx_cache.get(RAIN_LOOP_SFX)
        if not sound:
            path = os.path.join(self.sfx_dir, RAIN_LOOP_SFX)
            if os.path.exists(path):
                try:
                    sound = pygame.mixer.Sound(path)
                    self.sfx_cache[RAIN_LOOP_SFX] = sound
                except Exception as exc:
                    print(f"[AUDIO] Error loading rain SFX {RAIN_LOOP_SFX}: {exc}")
                    return
            else:
                return

        try:
            if not self.rain_channel.get_busy():
                self.rain_channel.play(sound, loops=-1)
            self.rain_channel.set_volume(effective_vol)
        except Exception as exc:
            print(f"[AUDIO] Error updating rain loop: {exc}")

    def _get_pitch_variant(self, sfx_name, base_sound, pitch_jitter):
        """Return a cached pitch-shifted Sound variant when numpy/sndarray is available."""
        if pitch_jitter <= 0.0:
            return base_sound
        variants = self.sfx_pitch_cache.get(sfx_name)
        if variants is None:
            variants = [base_sound]
            try:
                import numpy as np
                arr = pygame.sndarray.array(base_sound)
                n_frames = arr.shape[0]
                if n_frames > 16:
                    built = []
                    for factor in (-1.0, -0.5, 0.0, 0.5, 1.0):
                        ratio = 1.0 + factor * pitch_jitter
                        if abs(ratio - 1.0) < 1e-4:
                            built.append(base_sound)
                            continue
                        new_len = max(8, int(round(n_frames / ratio)))
                        src_x = np.linspace(0, n_frames - 1, new_len)
                        if arr.ndim == 2:
                            cols = [
                                np.interp(src_x, np.arange(n_frames), arr[:, c])
                                for c in range(arr.shape[1])
                            ]
                            resampled = np.column_stack(cols)
                        else:
                            resampled = np.interp(src_x, np.arange(n_frames), arr)
                        resampled = np.ascontiguousarray(resampled.round().astype(arr.dtype))
                        built.append(pygame.sndarray.make_sound(resampled))
                    variants = built
            except Exception:
                variants = [base_sound]
            self.sfx_pitch_cache[sfx_name] = variants
        return random.choice(variants)

    def play_sfx(self, sfx_name, volume=1.0, pitch_jitter=0.0):
        """Load and trigger an SFX file, with debug tracking, volume, and optional pitch variance."""
        self.recent_sfx.append({'name': sfx_name, 'time': 2.0})

        path = os.path.join(self.sfx_dir, sfx_name)
        if not os.path.exists(path):
            return

        try:
            if sfx_name not in self.sfx_cache:
                self.sfx_cache[sfx_name] = pygame.mixer.Sound(path)

            sound = self._get_pitch_variant(sfx_name, self.sfx_cache[sfx_name], pitch_jitter)

            if sfx_name in ("slug_attack.ogg", "bat_attack.ogg"):
                if sound.get_num_channels() >= 4:
                    return

            channel = sound.play()
            if channel:
                scaled_volume = max(0.0, min(1.0, float(volume) * float(SFX_VOLUME_SCALE.get(sfx_name, 1.0))))
                channel.set_volume(scaled_volume)
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
            if track_name == "death_theme.ogg":
                pygame.mixer.music.play(loops=0, fade_ms=250)
            else:
                pygame.mixer.music.play(loops=-1, fade_ms=2000)
            self.current_track = track_name
            print(f"[AUDIO] Transition to: {track_name}")
        except Exception as e:
            print(f"[AUDIO] Playback Error for {track_name}: {e}")
