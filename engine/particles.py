# copyright 2026 Dustin Massop, License: GPLv2
"""
Particle system for stylized combat effects: Glyph Splatter.
When an entity takes damage, typographical glyphs erupt outward and fade.
"""
# pylint: disable=too-few-public-methods,too-many-arguments,too-many-positional-arguments
import math
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
    RESPITE_PULSE_DURATION,
    RESPITE_PULSE_RING_START_RADIUS,
    RESPITE_PULSE_RING_MAX_RADIUS,
    RESPITE_PULSE_RING_INNER_SCALE,
    RESPITE_PULSE_RING_MAX_ALPHA,
    RESPITE_PULSE_HALO_MAX_ALPHA,
    RESPITE_PULSE_RING_COLOR_OUTER,
    RESPITE_PULSE_RING_COLOR_INNER,
    RESPITE_PULSE_GLYPH_COUNT,
    RESPITE_PULSE_GLYPH_POOL,
    RESPITE_PULSE_GLYPH_SPAWN_RADIUS_MIN,
    RESPITE_PULSE_GLYPH_SPAWN_RADIUS_MAX,
    RESPITE_PULSE_GLYPH_RISE_SPEED_MIN,
    RESPITE_PULSE_GLYPH_RISE_SPEED_MAX,
    RESPITE_PULSE_GLYPH_RADIAL_DRIFT_MAX,
    RESPITE_PULSE_GLYPH_SWAY_AMP,
    RESPITE_PULSE_GLYPH_SWAY_FREQ,
    RESPITE_PULSE_GLYPH_LIFETIME_MIN,
    RESPITE_PULSE_GLYPH_LIFETIME_MAX,
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


class RespitePulseGlyph:
    """Single rising, gently drifting manuscript letter/glyph emitted by a Respite Activation Pulse."""

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        x: float,
        y: float,
        glyph: str,
        vx: float,
        vy: float,
        lifetime: float,
        color: Tuple[int, int, int],
        sway_amp: float = RESPITE_PULSE_GLYPH_SWAY_AMP,
        sway_freq: float = RESPITE_PULSE_GLYPH_SWAY_FREQ,
        sway_phase: float = 0.0,
    ):
        self.x0 = float(x)
        self.y0 = float(y)
        self.x = float(x)
        self.y = float(y)
        self.glyph = str(glyph)
        self.vx = float(vx)
        self.vy = float(vy)
        self.lifetime = max(0.05, float(lifetime))
        self.age = 0.0
        self.color = color
        self.sway_amp = float(sway_amp)
        self.sway_freq = float(sway_freq)
        self.sway_phase = float(sway_phase)

    def update(self, dt: float) -> bool:
        """Advance dt-scaled upward drift and gentle horizontal sway. Returns False when expired."""
        step = max(0.0, float(dt))
        self.age += step
        if self.age >= self.lifetime:
            return False
        self.x = self.x0 + self.vx * self.age + math.sin(self.age * self.sway_freq + self.sway_phase) * self.sway_amp
        self.y = self.y0 + self.vy * self.age
        return True

    @property
    def alpha(self) -> int:
        """Quick fade-in over first 15% and smooth fade-out over the final 55% of lifetime."""
        ratio = max(0.0, min(1.0, self.age / self.lifetime))
        if ratio < 0.15:
            return int(round((ratio / 0.15) * 255))
        if ratio <= 0.45:
            return 255
        fade = max(0.0, 1.0 - ((ratio - 0.45) / 0.55))
        return int(round(fade * fade * 255))


class RespiteActivationPulse:
    """Localized dt-driven typographic bloom (expanding parchment/cyan ring + drifting letters)."""

    def __init__(
        self,
        cx: float,
        cy: float,
        duration: float = RESPITE_PULSE_DURATION,
        glyph_count: int = RESPITE_PULSE_GLYPH_COUNT,
        seed: Optional[int] = None,
    ):
        self.cx = float(cx)
        self.cy = float(cy)
        self.duration = max(0.1, float(duration))
        self.elapsed = 0.0
        self.glyphs: List[RespitePulseGlyph] = []

        rng = random.Random(seed) if seed is not None else random
        count = max(0, int(glyph_count))
        for idx in range(count):
            base_angle = (2.0 * math.pi * idx) / max(1, count)
            angle = base_angle + rng.uniform(-0.28, 0.28)
            spawn_r = rng.uniform(RESPITE_PULSE_GLYPH_SPAWN_RADIUS_MIN, RESPITE_PULSE_GLYPH_SPAWN_RADIUS_MAX)
            gx = self.cx + math.cos(angle) * spawn_r
            gy = self.cy + math.sin(angle) * spawn_r * 0.72
            radial_spd = rng.uniform(4.0, RESPITE_PULSE_GLYPH_RADIAL_DRIFT_MAX)
            vx = math.cos(angle) * radial_spd
            vy = -rng.uniform(RESPITE_PULSE_GLYPH_RISE_SPEED_MIN, RESPITE_PULSE_GLYPH_RISE_SPEED_MAX)
            life = rng.uniform(RESPITE_PULSE_GLYPH_LIFETIME_MIN, RESPITE_PULSE_GLYPH_LIFETIME_MAX)
            col = RESPITE_PULSE_RING_COLOR_INNER if idx % 2 == 0 else RESPITE_PULSE_RING_COLOR_OUTER
            self.glyphs.append(
                RespitePulseGlyph(
                    x=gx,
                    y=gy,
                    glyph=rng.choice(RESPITE_PULSE_GLYPH_POOL),
                    vx=vx,
                    vy=vy,
                    lifetime=life,
                    color=col,
                    sway_amp=rng.uniform(RESPITE_PULSE_GLYPH_SWAY_AMP * 0.6, RESPITE_PULSE_GLYPH_SWAY_AMP),
                    sway_freq=RESPITE_PULSE_GLYPH_SWAY_FREQ,
                    sway_phase=rng.uniform(0.0, 2.0 * math.pi),
                )
            )

    @property
    def progress(self) -> float:
        """Normalized [0.0, 1.0] progress across the pulse ring expansion."""
        return max(0.0, min(1.0, self.elapsed / self.duration))

    @property
    def ring_radius(self) -> float:
        """Ease-out expanding outer cyan-ink ring radius in pixels."""
        eased = 1.0 - (1.0 - self.progress) ** 2
        span = RESPITE_PULSE_RING_MAX_RADIUS - RESPITE_PULSE_RING_START_RADIUS
        return RESPITE_PULSE_RING_START_RADIUS + span * eased

    @property
    def inner_ring_radius(self) -> float:
        """Trailing inner warm parchment echo ring radius in pixels."""
        eased = 1.0 - (1.0 - self.progress) ** 2
        span = (RESPITE_PULSE_RING_MAX_RADIUS - RESPITE_PULSE_RING_START_RADIUS) * RESPITE_PULSE_RING_INNER_SCALE
        return RESPITE_PULSE_RING_START_RADIUS + span * eased

    @property
    def ring_alpha(self) -> int:
        """Translucent ring alpha fading smoothly to 0 at pulse completion."""
        if self.elapsed >= self.duration:
            return 0
        rem = max(0.0, 1.0 - self.progress)
        return int(round((rem ** 1.4) * RESPITE_PULSE_RING_MAX_ALPHA))

    @property
    def halo_alpha(self) -> int:
        """Soft parchment fill wash alpha inside the expanding ring."""
        if self.elapsed >= self.duration:
            return 0
        rem = max(0.0, 1.0 - self.progress)
        return int(round((rem ** 1.6) * RESPITE_PULSE_HALO_MAX_ALPHA))

    def update(self, dt: float) -> bool:
        """Advance the ring expansion and all drifting letters by dt seconds."""
        step = max(0.0, float(dt))
        self.elapsed += step
        self.glyphs = [g for g in self.glyphs if g.update(step)]
        return self.elapsed < self.duration or bool(self.glyphs)


class RespitePulseManager:
    """Manages active localized Respite Activation Pulses and automatic cleanup."""

    def __init__(self):
        self.pulses: List[RespiteActivationPulse] = []

    def spawn_pulse(
        self,
        x: float,
        y: float,
        glyph_count: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> RespiteActivationPulse:
        """Spawn a new localized typographic bloom pulse centered at (x, y)."""
        pulse = RespiteActivationPulse(
            cx=x,
            cy=y,
            glyph_count=RESPITE_PULSE_GLYPH_COUNT if glyph_count is None else glyph_count,
            seed=seed,
        )
        self.pulses.append(pulse)
        return pulse

    def update(self, dt: float) -> None:
        """Tick all active pulses by dt seconds and drop completed ones."""
        self.pulses = [p for p in self.pulses if p.update(dt)]

    def clear(self) -> None:
        """Immediately remove all active Respite pulses (e.g., on warp or map transition)."""
        self.pulses.clear()

    def is_active(self) -> bool:
        """Return True while at least one Respite Activation Pulse is active."""
        return bool(self.pulses)


def resolve_boss_summon_palette(boss) -> Tuple[Tuple[int, int, int], ...]:
    """Return the typographic square color palette for the given boss archetype."""
    from constants import BOSS_SUMMON_PALETTES

    cls_name = boss.__class__.__name__ if boss is not None else ""
    if getattr(boss, "is_slug_boss", False) or cls_name == "SlugBoss":
        return BOSS_SUMMON_PALETTES["SlugBoss"]
    if getattr(boss, "is_rimecrest_arbiter", False) or cls_name == "RimecrestArbiterBoss":
        return BOSS_SUMMON_PALETTES["RimecrestArbiterBoss"]
    if getattr(boss, "is_meadow_censor", False) or cls_name == "MeadowCensorBoss":
        return BOSS_SUMMON_PALETTES["MeadowCensorBoss"]
    if getattr(boss, "is_empowered", False):
        return BOSS_SUMMON_PALETTES["empowered"]
    return BOSS_SUMMON_PALETTES["default"]


class BossSummonManager:
    """Manages Ink-Unsealing boss summoning circles and 220+ rising typographic ash-squares."""

    @staticmethod
    def create_ritual(boss, seed: Optional[int] = None, awaiting_proximity: bool = False) -> dict:
        """Create a 2.35s Ink-Unsealing ritual state dict (idle ground circle if awaiting_proximity)."""
        import math
        from constants import (
            BOSS_SUMMON_CIRCLE_RADIUS,
            BOSS_SUMMON_DURATION,
            BOSS_SUMMON_EMERGE_TIME,
            BOSS_SUMMON_GLYPH_COLOR,
            BOSS_SUMMON_SQUARE_COUNT,
            BOSS_SUMMON_SQUARE_MAX_SIZE,
            BOSS_SUMMON_SQUARE_MIN_SIZE,
            BOSS_SUMMON_SQUARE_RISE_HEIGHT,
        )

        cx, cy = boss.get_center() if hasattr(boss, "get_center") else (
            float(getattr(boss, "x", 0.0)) + float(getattr(boss, "width", 64.0)) * 0.5,
            float(getattr(boss, "y", 0.0)) + float(getattr(boss, "height", 64.0)) * 0.5,
        )
        rng_seed = seed if seed is not None else (int(cx * 13 + cy * 31) ^ hash(getattr(boss, "name", "Boss")))
        rng = random.Random(rng_seed)
        palette = resolve_boss_summon_palette(boss)
        radius = float(BOSS_SUMMON_CIRCLE_RADIUS)
        total_squares = int(BOSS_SUMMON_SQUARE_COUNT)

        squares = []
        for idx in range(total_squares):
            frac = idx / float(max(1, total_squares - 1))
            in_emerge_veil = 0.55 <= frac <= 0.86
            angle = rng.uniform(0.0, 2.0 * math.pi)
            dist = radius * (math.sqrt(rng.random()) * (0.65 if in_emerge_veil else 0.96))
            x0 = cx + math.cos(angle) * dist
            y0 = cy + math.sin(angle) * dist * 0.68
            if in_emerge_veil and idx % 2 == 0:
                color = palette[0]  # Dense white-square emergence veil
                spawn_delay = rng.uniform(BOSS_SUMMON_EMERGE_TIME - 0.22, BOSS_SUMMON_EMERGE_TIME + 0.28)
            else:
                color = palette[idx % len(palette)]
                spawn_delay = frac * (BOSS_SUMMON_DURATION * 0.76)
            lifetime = rng.uniform(0.68, 1.12)
            rise_dist = rng.uniform(BOSS_SUMMON_SQUARE_RISE_HEIGHT * 0.65, BOSS_SUMMON_SQUARE_RISE_HEIGHT * 1.15)
            vy = -rise_dist / lifetime
            vx = rng.uniform(-14.0, 14.0)
            squares.append(
                {
                    "x0": float(x0),
                    "y0": float(y0),
                    "x": float(x0),
                    "y": float(y0),
                    "vx": float(vx),
                    "vy": float(vy),
                    "spawn_delay": float(max(0.0, spawn_delay)),
                    "lifetime": float(lifetime),
                    "age": 0.0,
                    "active": False,
                    "completed": False,
                    "initial_size": float(BOSS_SUMMON_SQUARE_MAX_SIZE),
                    "min_size": float(BOSS_SUMMON_SQUARE_MIN_SIZE),
                    "size": float(BOSS_SUMMON_SQUARE_MAX_SIZE),
                    "rise_span": float(rise_dist),
                    "color": color,
                    "glyph": GLYPH_SPLATTER_POOL[idx % len(GLYPH_SPLATTER_POOL)],
                    "glyph_color": BOSS_SUMMON_GLYPH_COLOR,
                    "alpha": 255,
                    "is_veil": bool(in_emerge_veil),
                }
            )

        return {
            "boss": boss,
            "cx": float(cx),
            "cy": float(cy),
            "elapsed": 0.0,
            "idle_time": 0.0,
            "duration": float(BOSS_SUMMON_DURATION),
            "emerge_time": float(BOSS_SUMMON_EMERGE_TIME),
            "base_radius": radius,
            "circle_radius": radius,
            "black_fill_ratio": 0.0,
            "black_radius": 0.0,
            "erupting": not bool(awaiting_proximity),
            "stage": 0 if awaiting_proximity else 1,
            "materialized": False,
            "palette": palette,
            "squares": squares,
        }

    @staticmethod
    def trigger_eruption(ritual: dict) -> bool:
        """Transition an idle ground-circle ritual into active eruption & boss emergence."""
        if not ritual or ritual.get("erupting", True):
            return False
        ritual["erupting"] = True
        ritual["stage"] = 1
        ritual["elapsed"] = 0.0
        return True

    @staticmethod
    def update_ritual(ritual: dict, dt: float, game_state=None) -> bool:
        """Advance a summoning ritual by dt seconds. Returns True while active, False when complete."""
        base_r = float(ritual.get("base_radius", 52.0))
        if not ritual.get("erupting", True):
            ritual["idle_time"] = float(ritual.get("idle_time", 0.0)) + float(dt)
            ritual["elapsed"] = 0.0
            ritual["stage"] = 0
            ritual["circle_radius"] = base_r
            ritual["black_fill_ratio"] = 0.0
            ritual["black_radius"] = 0.0
            return True

        elapsed = float(ritual.get("elapsed", 0.0)) + float(dt)
        ritual["elapsed"] = elapsed
        duration = float(ritual.get("duration", 2.35))
        emerge_time = float(ritual.get("emerge_time", 1.55))
        boss = ritual.get("boss")

        if elapsed < emerge_time:
            ritual["stage"] = 1
            fill_ratio = max(0.0, min(1.0, elapsed / max(1e-4, emerge_time)))
            ritual["circle_radius"] = base_r
            ritual["black_fill_ratio"] = fill_ratio
            ritual["black_radius"] = base_r * fill_ratio
        else:
            ritual["stage"] = 2
            if not ritual.get("materialized", False):
                ritual["materialized"] = True
                if boss is not None:
                    boss.dormant_boss_summon = False
                    boss.summoning_emerge_timer = max(0.01, duration - elapsed)
                    if game_state is not None and hasattr(game_state, "enemies"):
                        if boss not in game_state.enemies:
                            game_state.enemies.append(boss)
            elif boss is not None:
                boss.summoning_emerge_timer = max(0.0, duration - elapsed)

            close_span = max(1e-4, duration - emerge_time)
            close_prog = max(0.0, min(1.0, (elapsed - emerge_time) / close_span))
            cur_r = base_r * (1.0 - close_prog)
            ritual["circle_radius"] = cur_r
            ritual["black_fill_ratio"] = 1.0
            ritual["black_radius"] = cur_r

        for sq in ritual.get("squares", ()):
            if sq.get("completed", False):
                continue
            delay = float(sq.get("spawn_delay", 0.0))
            if elapsed < delay:
                continue
            active_time = min(float(dt), elapsed - delay) if not sq.get("active", False) else float(dt)
            sq["active"] = True
            sq["age"] = float(sq.get("age", 0.0)) + active_time
            life = max(1e-4, float(sq.get("lifetime", 0.8)))
            if sq["age"] >= life:
                sq["completed"] = True
                sq["active"] = False
                sq["alpha"] = 0
                continue
            sq["x"] = float(sq["x0"]) + float(sq["vx"]) * sq["age"]
            sq["y"] = float(sq["y0"]) + float(sq["vy"]) * sq["age"]
            risen = max(0.0, float(sq["y0"]) - float(sq["y"]))
            rise_ratio = max(0.0, min(1.0, risen / max(1.0, float(sq.get("rise_span", 80.0)))))
            max_sz = float(sq.get("initial_size", 8.0))
            min_sz = float(sq.get("min_size", 2.0))
            sq["size"] = max(min_sz, max_sz - (max_sz - min_sz) * rise_ratio)
            age_ratio = sq["age"] / life
            if age_ratio > 0.65:
                fade = max(0.0, 1.0 - (age_ratio - 0.65) / 0.35)
                sq["alpha"] = int(round(255 * fade))
            else:
                sq["alpha"] = 255

        if elapsed >= duration:
            if boss is not None:
                boss.dormant_boss_summon = False
                boss.summoning_emerge_timer = 0.0
                if game_state is not None and hasattr(game_state, "enemies"):
                    if boss not in game_state.enemies:
                        game_state.enemies.append(boss)
            ritual["circle_radius"] = 0.0
            ritual["black_radius"] = 0.0
            return False
        return True
