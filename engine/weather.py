"""
Weather System: The Bleed (The Redacting Circle).
Handles the spatial contraction logic and exposure damage.
"""
from constants import (
    TILE_SIZE, WEATHER_MIN_RADIUS, 
    WEATHER_WAIT_DURATION, WEATHER_SHRINK_DURATION, 
    WEATHER_DAMAGE_PER_SECOND, TILE_STRUCTURE, TILE_RESPITE
)

class WeatherManager:
    def __init__(self, boss_coords=None):
        self.boss_coords = boss_coords
        self.bleed_state = "GRACE_PERIOD"
        self.grace_timer = 60.0  # 1-minute testing buffer
        
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
                self.target_radius = max(WEATHER_MIN_RADIUS, self.active_safe_radius * 0.75)
                print("[THE BLEED] The circle is closing.")
            return # No rain particles calculated or damage checked during grace

        elif self.bleed_state == "WAIT":
            self.timer -= dt
            if self.timer <= 0:
                self.bleed_state = "SHRINKING"
                self.timer = WEATHER_SHRINK_DURATION
                self.target_radius = max(WEATHER_MIN_RADIUS, self.active_safe_radius * 0.75)
                print(f"[THE BLEED] The circle is closing. Target radius: {self.target_radius}")
        
        elif self.bleed_state == "SHRINKING":
            if self.timer > 0:
                shrink_speed = (self.active_safe_radius - self.target_radius) / self.timer
                self.active_safe_radius -= shrink_speed * dt
                self.timer -= dt
            
            if self.timer <= 0:
                self.active_safe_radius = self.target_radius
                if self.active_safe_radius <= WEATHER_MIN_RADIUS:
                    self.bleed_state = "CLAMPED"
                    print("[THE BLEED] The circle has reached finality.")
                else:
                    self.bleed_state = "WAIT"
                    self.timer = WEATHER_WAIT_DURATION
                    print("[THE BLEED] The circle has paused.")

        # 2. Exposure Damage Logic
        px, py = player.get_center()
        dist_sq = (px - bcx)**2 + (py - bcy)**2
        is_outside = dist_sq > self.active_safe_radius**2
        
        if is_outside:
            # Check for shelter override
            tx, ty = int(px // TILE_SIZE), int(py // TILE_SIZE)
            is_sheltered = False
            if 0 <= ty < len(world.grid) and 0 <= tx < len(world.grid[0]):
                tile_type = world.grid[ty][tx]
                if tile_type in (TILE_STRUCTURE, TILE_RESPITE):
                    is_sheltered = True
            
            if not is_sheltered:
                damage = WEATHER_DAMAGE_PER_SECOND * dt
                player.take_damage(damage)
