"""
Particle system for stylized combat effects: Glyph Splatter.
When an entity takes damage, typographical glyphs erupt outward and fade.
"""
# pylint: disable=too-few-public-methods,too-many-arguments,too-many-positional-arguments
import random
from typing import List, Tuple, Optional
from constants import (
    GLYPH_SPLATTER_POOL,
    GLYPH_MIN_COUNT,
    GLYPH_MAX_COUNT,
    GLYPH_MIN_LIFESPAN_FRAMES,
    GLYPH_MAX_LIFESPAN_FRAMES,
    GLYPH_GRAVITY_PER_FRAME,
    GLYPH_FRICTION_X,
    COLOR_INK_CHARCOAL,
)


class GlyphParticle:
    """Represents an individual scattering manuscript glyph particle."""

    def __init__(
        self,
        x: float,
        y: float,
        glyph: str,
        vx: float,
        vy: float,
        lifespan_frames: int,
        color: Tuple[int, int, int] = COLOR_INK_CHARCOAL,
    ):
        self.x = float(x)
        self.y = float(y)
        self.glyph = glyph
        self.vx = float(vx)
        self.vy = float(vy)
        self.max_lifespan = float(lifespan_frames)
        self.remaining_frames = float(lifespan_frames)
        self.color = color

    def update(self, dt: float) -> bool:
        """Advance particle physics and lifetime based on dt normalized to 60fps frames.

        Returns True if the particle is still alive, False if expired.
        """
        # Frame step factor (at 60fps, 0.0166s = 1.0 frame step)
        frame_step = dt * 60.0

        self.x += self.vx * frame_step
        self.y += self.vy * frame_step

        # Physics: air friction on horizontal velocity, small gravity downwards
        self.vx *= GLYPH_FRICTION_X ** frame_step
        self.vy += GLYPH_GRAVITY_PER_FRAME * frame_step

        self.remaining_frames -= frame_step
        return self.remaining_frames > 0

    @property
    def alpha(self) -> int:
        """Linear fade-out during the final 50% of the particle's lifespan."""
        half_life = self.max_lifespan * 0.5
        if self.remaining_frames >= half_life:
            return 255
        ratio = max(0.0, min(1.0, self.remaining_frames / half_life))
        return int(ratio * 255)


class GlyphSplatterManager:
    """Manages active glyph particles and emission bursts."""

    def __init__(self):
        self.particles: List[GlyphParticle] = []

    def spawn_burst(
        self,
        x: float,
        y: float,
        color: Optional[Tuple[int, int, int]] = None,
        count: Optional[int] = None,
    ):
        """Spawn 4 to 7 scattering typographic glyphs centered at (x, y)."""
        particle_count = count if count is not None else random.randint(GLYPH_MIN_COUNT, GLYPH_MAX_COUNT)
        particle_color = color if color is not None else COLOR_INK_CHARCOAL

        for _ in range(particle_count):
            glyph = random.choice(GLYPH_SPLATTER_POOL)
            vx = random.uniform(-2.5, 2.5)
            vy = random.uniform(-4.0, -1.5)
            lifespan = random.randint(GLYPH_MIN_LIFESPAN_FRAMES, GLYPH_MAX_LIFESPAN_FRAMES)
            self.particles.append(
                GlyphParticle(
                    x=x,
                    y=y,
                    glyph=glyph,
                    vx=vx,
                    vy=vy,
                    lifespan_frames=lifespan,
                    color=particle_color,
                )
            )

    def update(self, dt: float):
        """Update all active particles, removing expired ones."""
        self.particles = [p for p in self.particles if p.update(dt)]

    def clear(self):
        """Clear all active particles."""
        self.particles.clear()
