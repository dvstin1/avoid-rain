"""
Weather System: The Bleed (The Redacting Circle).
Handles the spatial contraction logic and exposure damage.
Supports multiple boss phases (Night 1, Night 2) and The Dilution.
"""
from constants import (
    TILE_SIZE, WEATHER_WAIT_DURATION, WEATHER_SHRINK_DURATION, 
    TILE_STRUCTURE, TILE_RESPITE
)

class WeatherManager:
    def __init__(self, boss_coords_list=None):
        self.reset(boss_coords_list)

    def reset(self, boss_coords_list=None):
        """Restore weather system to initial run-start parameters."""
        self.boss_coords_list = boss_coords_list or []
        self.current_boss_idx = 0
        
        self.bleed_state = "GRACE_PERIOD"
        self.grace_timer = 60.0  # 1-minute initial grace period
        self.timer = 0.0 # Reset per-phase timer
        
        # Sizing Steps (in Tiles)
        self.steps = [300.0, 120.0, 40.0]
        self.current_step_idx = 0
        self.pending_milestone_text = None
        
        # Bugfix: Initialize at massive 620.0 units (tiles)
        # 620 * 40 = 24800 pixels, covers the 17600px map
        self.active_safe_radius = 620.0 * TILE_SIZE 
        self.target_radius = self.active_safe_radius
        self.damage_enabled = True

    def set_boss_coords_list(self, coords_list):
        """Update the list of potential boss centers."""
        self.boss_coords_list = coords_list
        self.current_boss_idx = 0

    def is_pos_safe(self, x, y):
        """Check if a world coordinate is currently inside the safe zone."""
        if self.bleed_state == "DILUTION" or not self.boss_coords_list:
            return True
            
        coords = self.boss_coords_list[self.current_boss_idx]
        bcx, bcy = coords['x'] * TILE_SIZE, coords['y'] * TILE_SIZE
        dist_sq = (x - bcx)**2 + (y - bcy)**2
        return dist_sq <= self.active_safe_radius**2

    def get_current_boss_coords(self):
        """Return the center point for the currently targeted boss arena."""
        if not self.boss_coords_list or self.current_boss_idx >= len(self.boss_coords_list):
            return None
        return self.boss_coords_list[self.current_boss_idx]

    def update(self, dt, player, world, audio_manager=None):
        # Hub Isolation Rule: Weather system completely freezes in the Sanctuary
        if getattr(world, 'name', '') == "sanctuary":
            return
            
        # Final Boss Arena Isolation: Weather remains dormant until victory
        if getattr(world, 'name', '') == "final_boss" and self.bleed_state != "DILUTION":
            self.active_safe_radius = 1000000.0
            return

        if self.bleed_state == "DILUTION":
            # Temporary safety interlude
            self.active_safe_radius = 1000000.0
            self.timer -= dt
            if self.timer <= 0:
                # Progress to next boss if available
                if self.current_boss_idx + 1 < len(self.boss_coords_list):
                    self.current_boss_idx += 1
                    # Full Reset for Night 2
                    self.bleed_state = "GRACE_PERIOD"
                    self.grace_timer = 60.0
                    self.current_step_idx = 0
                    self.active_safe_radius = 620.0 * TILE_SIZE
                    self.target_radius = self.active_safe_radius
                    self.pending_milestone_text = "THE SECOND DRAFT"
                else:
                    # Final Boss Phase (Appendix)
                    self.bleed_state = "APPENDIX"
            return

        if self.bleed_state == "APPENDIX":
            # Weather is permanently clear while in the appendix portal phase
            self.active_safe_radius = 1000000.0
            return

        if not self.boss_coords_list or self.current_boss_idx >= len(self.boss_coords_list):
            return

        coords = self.boss_coords_list[self.current_boss_idx]
        bcx, bcy = coords['x'] * TILE_SIZE, coords['y'] * TILE_SIZE

        # 1. Lifecycle State Machine
        if self.bleed_state == "GRACE_PERIOD":
            self.grace_timer -= dt
            if self.grace_timer <= 0:
                self.bleed_state = "SHRINKING"
                self.timer = WEATHER_SHRINK_DURATION
                if self.current_step_idx < len(self.steps):
                    self.target_radius = self.steps[self.current_step_idx] * TILE_SIZE
                self.pending_milestone_text = "THE INK BEGINS TO RUN"
                if audio_manager:
                    audio_manager.play_sfx("bleed_start.ogg")
                print(f"[THE BLEED] Night {self.current_boss_idx + 1}: The circle is closing.")
            return

        elif self.bleed_state == "WAIT":
            self.timer -= dt
            if self.timer <= 0:
                self.bleed_state = "SHRINKING"
                self.timer = WEATHER_SHRINK_DURATION
                if self.current_step_idx < len(self.steps):
                    self.target_radius = self.steps[self.current_step_idx] * TILE_SIZE
                if audio_manager:
                    audio_manager.play_sfx("bleed_start.ogg")
                if self.current_step_idx < len(self.steps):
                    print(f"[THE BLEED] The circle is closing. Target radius: {self.steps[self.current_step_idx]} units")
        
        elif self.bleed_state == "SHRINKING":
            if self.timer > 0:
                shrink_speed = (self.active_safe_radius - self.target_radius) / self.timer
                self.active_safe_radius -= shrink_speed * dt
                self.timer -= dt
            
            if self.timer <= 0:
                self.active_safe_radius = self.target_radius
                self.current_step_idx += 1
                
                if self.current_step_idx >= len(self.steps):
                    self.bleed_state = "CLAMPED"
                    self.pending_milestone_text = "THE FINAL PARAGRAPH LOCKS"
                    print("[THE BLEED] The circle has reached finality.")
                else:
                    self.bleed_state = "WAIT"
                    self.timer = 40.0 
                    print("[THE BLEED] The circle has paused.")

        # 2. Exposure Damage Logic
        px, py = player.get_center()
        dist_sq = (px - bcx)**2 + (py - bcy)**2
        is_outside = dist_sq > self.active_safe_radius**2
        
        player.is_exposed = False
        if is_outside and self.damage_enabled:
            tx, ty = int(px // TILE_SIZE), int(py // TILE_SIZE)
            is_sheltered = False
            if 0 <= ty < len(world.grid) and 0 <= tx < len(world.grid[0]):
                tile_type = world.grid[ty][tx]
                if tile_type in (TILE_STRUCTURE, TILE_RESPITE):
                    is_sheltered = True
            
            if not is_sheltered:
                player.is_exposed = True
                damage = 2.0 * dt
                player.take_damage(damage, bypass_stagger=True)

    def is_boss_spawn_ready(self):
        """Rule: Night Boss doesn't spawn until the circle is closed."""
        return self.bleed_state in ("CLAMPED", "BOSS_PHASE")

    def lock_circle_for_boss(self, boss_alive):
        """Rule: Lock the circle in closed position until Night Boss is defeated."""
        if boss_alive and self.bleed_state == "CLAMPED":
            self.bleed_state = "BOSS_PHASE"
        elif not boss_alive and self.bleed_state == "BOSS_PHASE":
            self.trigger_dilution()

    def trigger_dilution(self):
        """Transition into Act III: The Dilution (Temporary interlude)."""
        self.bleed_state = "DILUTION"
        self.timer = 10.0 # 10 seconds of safe blue rain
        self.pending_milestone_text = "THE MARGINS CLEAR"
        print("[THE BLEED] The ink has been diluted. The margins clear.")

    def to_dict(self):
        """Serialize weather state for saving."""
        return {
            "bleed_state": self.bleed_state,
            "grace_timer": self.grace_timer,
            "timer": getattr(self, 'timer', 0.0),
            "active_safe_radius": self.active_safe_radius,
            "target_radius": self.target_radius,
            "current_step_idx": self.current_step_idx,
            "current_boss_idx": self.current_boss_idx
        }

    def from_dict(self, data):
        """Restore weather state from dictionary."""
        if not data: return
        self.bleed_state = data.get("bleed_state", "GRACE_PERIOD")
        self.grace_timer = data.get("grace_timer", 60.0)
        self.timer = data.get("timer", 0.0)
        self.active_safe_radius = data.get("active_safe_radius", self.active_safe_radius)
        self.target_radius = data.get("target_radius", self.target_radius)
        self.current_step_idx = data.get("current_step_idx", self.current_step_idx)
        self.current_boss_idx = data.get("current_boss_idx", 0)
