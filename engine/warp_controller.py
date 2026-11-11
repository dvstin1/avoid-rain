"""
Transition controller for "The Ink & Fog Warp".
Handles cinematic map teleports in three non-blocking phases:
Departure (fog bloom & glyph scatter), The Veil (fade to black & map transfer),
and Arrival (fade in, lingering fog evaporation & player restore).
"""
# pylint: disable=too-few-public-methods,too-many-arguments,too-many-positional-arguments,too-many-instance-attributes,too-many-locals,import-outside-toplevel
import math
import random
from typing import List, Tuple, Optional, Callable, Any
from constants import (
    WARP_STAGE_IDLE,
    WARP_STAGE_DEPARTURE,
    WARP_STAGE_THE_VEIL,
    WARP_STAGE_ARRIVAL,
    WARP_DEPARTURE_FRAMES,
    WARP_VEIL_FRAMES,
    WARP_ARRIVAL_FRAMES,
    WARP_FOG_PUFF_COUNT,
    WARP_GLYPH_COUNT,
    WARP_GLYPH_POOL,
    COLOR_WARP_FOG_INK,
    COLOR_WARP_FOG_PARCHMENT,
    COLOR_WARP_GLYPH_MUTED,
    WARP_PUFF_MIN_RADIUS,
    WARP_PUFF_MAX_RADIUS,
    WARP_PUFF_MIN_ALPHA,
    WARP_PUFF_MAX_ALPHA,
    GLYPH_GRAVITY_PER_FRAME,
    GLYPH_FRICTION_X,
)


class WarpFogPuff:
    """An individual translucent circular/elliptical puff of ink or parchment fog."""

    def __init__(
        self,
        x: float,
        y: float,
        base_radius: float,
        color: Tuple[int, int, int],
        max_alpha: int,
    ):
        self.x = float(x)
        self.y = float(y)
        self.base_radius = float(base_radius)
        self.radius = float(base_radius * 0.2)
        self.color = color
        self.max_alpha = max_alpha
        self.alpha = 0
        self.vx = random.uniform(-0.6, 0.6)
        self.vy = random.uniform(-0.9, -0.2)
        self.growth_rate = random.uniform(1.3, 1.8)


class WarpGlyph:
    """An individual manuscript glyph drifting or scattering within the fog cloud."""

    def __init__(
        self,
        x: float,
        y: float,
        glyph: str,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
    ):
        self.x = float(x)
        self.y = float(y)
        self.glyph = glyph
        self.vx = float(vx)
        self.vy = float(vy)
        self.color = color
        self.alpha = 255


class InkWarpController:
    """State machine controller for cinematic Ink & Fog warping transitions."""

    def __init__(self):
        self.stage: str = WARP_STAGE_IDLE
        self.stage_timer: float = 0.0
        self.fog_puffs: List[WarpFogPuff] = []
        self.glyph_particles: List[WarpGlyph] = []
        self.target: Any = None
        self.callback: Optional[Callable[[Any], None]] = None
        self.veil_alpha: int = 0
        self.transfer_executed: bool = False

    def is_active(self) -> bool:
        """Check if a warp sequence is currently executing."""
        return self.stage != WARP_STAGE_IDLE

    def blocks_input(self) -> bool:
        """Check if player input must remain locked during the current phase."""
        return self.stage != WARP_STAGE_IDLE

    def blocks_enemy_updates(self) -> bool:
        """Check if enemy updates and hazards should pause."""
        return self.stage in (WARP_STAGE_DEPARTURE, WARP_STAGE_THE_VEIL)

    def start_warp(
        self,
        player: Any,
        target: Any,
        callback: Optional[Callable[[Any], None]] = None,
    ) -> bool:
        """Initiate the three-stage transit sequence centered around player."""
        if self.is_active():
            return False

        self.stage = WARP_STAGE_DEPARTURE
        self.stage_timer = 0.0
        self.target = target
        self.callback = callback
        self.transfer_executed = False
        self.veil_alpha = 0

        px, py = player.get_center()

        # 1. Spawn Fog Cloud Puffs
        self.fog_puffs.clear()
        for _ in range(WARP_FOG_PUFF_COUNT):
            ang = random.uniform(0.0, math.tau)
            dist = random.uniform(4.0, 24.0)
            offset_x = math.cos(ang) * dist
            offset_y = math.sin(ang) * dist * 0.8
            color = COLOR_WARP_FOG_INK if random.random() < 0.7 else COLOR_WARP_FOG_PARCHMENT
            base_r = random.uniform(WARP_PUFF_MIN_RADIUS, WARP_PUFF_MAX_RADIUS)
            max_a = random.randint(WARP_PUFF_MIN_ALPHA, WARP_PUFF_MAX_ALPHA)
            self.fog_puffs.append(WarpFogPuff(px + offset_x, py + offset_y, base_r, color, max_a))

        # 2. Spawn Glyph Swirl Particles
        self.glyph_particles.clear()
        for _ in range(WARP_GLYPH_COUNT):
            ang = random.uniform(0.0, math.tau)
            dist = random.uniform(6.0, 28.0)
            gx = px + math.cos(ang) * dist
            gy = py + math.sin(ang) * dist
            glyph_char = random.choice(WARP_GLYPH_POOL)
            vx = random.uniform(-2.2, 2.2)
            vy = random.uniform(-3.8, -1.2)
            col_choice = random.choice([COLOR_WARP_FOG_INK, COLOR_WARP_FOG_PARCHMENT, COLOR_WARP_GLYPH_MUTED])
            self.glyph_particles.append(WarpGlyph(gx, gy, glyph_char, vx, vy, col_choice))

        player.alpha = 255
        return True

    def _execute_transfer(self, game_state: Any):
        """Execute physical map / coordinate transition and re-center camera."""
        if self.callback:
            self.callback(game_state)
        elif hasattr(self.target, 'apply_transfer'):
            self.target.apply_transfer(game_state)
        elif hasattr(self.target, 'execute_interaction'):
            self.target.execute_interaction(game_state)
        elif isinstance(self.target, str):
            from engine.world import WarpPortal
            portal = WarpPortal(self.target, 0, 0, (0, 0, 0, 0))
            if hasattr(portal, 'apply_transfer'):
                portal.apply_transfer(game_state)
            else:
                portal.execute_interaction(game_state)

        # Snap camera to new player location immediately under the veil
        if hasattr(game_state, 'camera') and game_state.player:
            game_state.camera.instant_center(game_state.player.get_center())

    def update(self, dt: float, game_state: Any):
        """Advance transition state machine and particle physics."""
        if not self.is_active():
            return

        frame_step = dt * 60.0
        self.stage_timer += frame_step

        if self.stage == WARP_STAGE_DEPARTURE:
            self._update_departure(frame_step, game_state)
        elif self.stage == WARP_STAGE_THE_VEIL:
            self._update_veil(frame_step, game_state)
        elif self.stage == WARP_STAGE_ARRIVAL:
            self._update_arrival(frame_step, game_state)

    def _update_departure(self, frame_step: float, game_state: Any):
        """Stage 1: Fog blooms around player, glyphs scatter upward, player fades to 0."""
        p = min(1.0, self.stage_timer / WARP_DEPARTURE_FRAMES)
        game_state.player.alpha = max(0, int(255 * (1.0 - p)))
        self.veil_alpha = 0

        for puff in self.fog_puffs:
            puff.x += puff.vx * frame_step
            puff.y += puff.vy * frame_step
            puff.radius = puff.base_radius * (0.2 + (puff.growth_rate - 0.2) * (p ** 0.8))
            puff.alpha = int(puff.max_alpha * min(1.0, p * 1.5))

        for glyph in self.glyph_particles:
            glyph.vy += -0.05 * frame_step
            glyph.vx *= GLYPH_FRICTION_X ** frame_step
            glyph.x += glyph.vx * frame_step
            glyph.y += glyph.vy * frame_step
            glyph.alpha = 255

        if self.stage_timer >= WARP_DEPARTURE_FRAMES:
            game_state.player.alpha = 0
            self.stage = WARP_STAGE_THE_VEIL
            self.stage_timer = 0.0
            self.transfer_executed = False

    def _update_veil(self, _frame_step: float, game_state: Any):
        """Stage 2: Full-screen black overlay fades to 100%, execute transfer, snap camera."""
        p = min(1.0, self.stage_timer / WARP_VEIL_FRAMES)
        fade_ratio = min(1.0, p * 2.0)
        self.veil_alpha = int(255 * fade_ratio)

        # Mid-veil transfer execution
        if not self.transfer_executed and (p >= 0.5 or self.stage_timer >= WARP_VEIL_FRAMES * 0.5):
            old_cx, old_cy = game_state.player.get_center()
            self._execute_transfer(game_state)
            new_cx, new_cy = game_state.player.get_center()
            dx = new_cx - old_cx
            dy = new_cy - old_cy

            # Re-anchor particles to new player coordinates
            for puff in self.fog_puffs:
                puff.x += dx
                puff.y += dy
            for glyph in self.glyph_particles:
                glyph.x += dx
                glyph.y += dy
            self.transfer_executed = True

        if self.stage_timer >= WARP_VEIL_FRAMES:
            if not self.transfer_executed:
                old_cx, old_cy = game_state.player.get_center()
                self._execute_transfer(game_state)
                new_cx, new_cy = game_state.player.get_center()
                dx = new_cx - old_cx
                dy = new_cy - old_cy
                for puff in self.fog_puffs:
                    puff.x += dx
                    puff.y += dy
                for glyph in self.glyph_particles:
                    glyph.x += dx
                    glyph.y += dy
                self.transfer_executed = True

            self.stage = WARP_STAGE_ARRIVAL
            self.stage_timer = 0.0
            # Re-seed dispersal velocity for Stage 3
            for glyph in self.glyph_particles:
                glyph.vx = random.uniform(-1.8, 1.8)
                glyph.vy = random.uniform(-1.0, 1.0)

    def _update_arrival(self, frame_step: float, game_state: Any):
        """Stage 3: Fade veil to 0, player enveloped in lingering fog, glyphs disperse and fall."""
        p = min(1.0, self.stage_timer / WARP_ARRIVAL_FRAMES)
        self.veil_alpha = max(0, int(255 * (1.0 - min(1.0, p * 2.0))))
        game_state.player.alpha = min(255, int(255 * min(1.0, p * 1.5)))

        shrink = max(0.0, 1.0 - p)
        for puff in self.fog_puffs:
            puff.x += puff.vx * 0.4 * frame_step
            puff.y += puff.vy * 0.4 * frame_step
            puff.radius = puff.base_radius * (0.3 + 0.7 * shrink)
            puff.alpha = int(puff.max_alpha * shrink)

        for glyph in self.glyph_particles:
            glyph.vy += GLYPH_GRAVITY_PER_FRAME * frame_step
            glyph.vx *= GLYPH_FRICTION_X ** frame_step
            glyph.x += glyph.vx * frame_step
            glyph.y += glyph.vy * frame_step
            glyph.alpha = int(255 * (1.0 - p))

        if self.stage_timer >= WARP_ARRIVAL_FRAMES:
            game_state.player.alpha = 255
            self.stage = WARP_STAGE_IDLE
            self.fog_puffs.clear()
            self.glyph_particles.clear()
            self.veil_alpha = 0
            self.target = None
            self.callback = None
