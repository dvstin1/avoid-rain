"""
Weather System: The Bleed (The Redacting Circle).
Handles the spatial contraction logic and exposure damage.
"""
from constants import (
    TILE_SIZE, WEATHER_WAIT_DURATION, WEATHER_SHRINK_DURATION, 
    TILE_STRUCTURE, TILE_RESPITE
)

class WeatherManager:
    def __init__(self, boss_coords=None):
        self.boss_coords = boss_coords
        self.bleed_state = "GRACE_PERIOD"
        self.grace_timer = 60.0  # 1-minute initial grace period
        
        # Sizing Steps (in Tiles)
        self.steps = [300.0, 120.0, 40.0]
        self.current_step_idx = 0
        self.pending_milestone_text = None
        
        # Bugfix: Initialize at massive 620.0 units (tiles)
        # 620 * 40 = 24800 pixels, covers the 17600px map
        self.active_safe_radius = 620.0 * TILE_SIZE 
        self.target_radius = self.active_safe_radius

    def update(self, dt, player, world):
        if not self.boss_coords:
            return

        bcx, bcy = self.boss_coords['x'] * TILE_SIZE, self.boss_coords['y'] * TILE_SIZE

        # 1. Lifecycle State Machine
        if self.bleed_state == "GRACE_PERIOD":
            self.grace_timer -= dt
            if self.grace_timer <= 0:
                self.bleed_state = "SHRINKING"
                self.timer = WEATHER_SHRINK_DURATION
                self.target_radius = self.steps[self.current_step_idx] * TILE_SIZE
                self.pending_milestone_text = "THE INK BEGINS TO RUN"
                print("[THE BLEED] The circle is closing.")
            return # No rain visuals or damage during grace

        elif self.bleed_state == "WAIT":
            self.timer -= dt
            if self.timer <= 0:
                self.bleed_state = "SHRINKING"
                self.timer = WEATHER_SHRINK_DURATION
                self.target_radius = self.steps[self.current_step_idx] * TILE_SIZE
                print(f"[THE BLEED] The circle is closing. Target radius: {self.steps[self.current_step_idx]} units")
        
        elif self.bleed_state == "SHRINKING":
            if self.timer > 0:
                shrink_speed = (self.active_safe_radius - self.target_radius) / self.timer
                self.active_safe_radius -= shrink_speed * dt
                self.timer -= dt
            
            if self.timer <= 0:
                self.active_safe_radius = self.target_radius
                self.current_step_idx += 1
                
                # Check if we reached the final step
                if self.current_step_idx >= len(self.steps):
                    self.bleed_state = "CLAMPED"
                    self.pending_milestone_text = "THE FINAL PARAGRAPH LOCKS"
                    print("[THE BLEED] The circle has reached finality.")
                else:
                    self.bleed_state = "WAIT"
                    self.timer = 40.0 # 40-second pause between steps
                    print("[THE BLEED] The circle has paused.")

        # 2. Exposure Damage Logic
        px, py = player.get_center()
        dist_sq = (px - bcx)**2 + (py - bcy)**2
        is_outside = dist_sq > self.active_safe_radius**2
        
        player.is_exposed = False # Reset every frame before check
        if is_outside:
            # Check for shelter override
            tx, ty = int(px // TILE_SIZE), int(py // TILE_SIZE)
            is_sheltered = False
            if 0 <= ty < len(world.grid) and 0 <= tx < len(world.grid[0]):
                tile_type = world.grid[ty][tx]
                if tile_type in (TILE_STRUCTURE, TILE_RESPITE):
                    is_sheltered = True
            
            if not is_sheltered:
                player.is_exposed = True
                # Fix: subtraction must be exactly 2 HP per second
                # Bypassing combat stagger for environmental damage
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
            self.bleed_state = "VICTORY"
