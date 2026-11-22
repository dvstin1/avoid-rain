#!/usr/bin/env python3
"""Standalone offline procedural sound-effect generator for Avoid Rain.

Synthesizes game-ready Ogg Vorbis (.ogg) SFX matching the engine's audio standard
(44.1 kHz, mono, `assets/audio/sfx/<snake_case>.ogg`, loaded via `pygame.mixer.Sound`).

DSP engine (numpy-accelerated when installed, pure-Python `math` fallback otherwise):
- ADSR / exponential / swell / arch amplitude envelopes and exponential pitch sweeps & drops.
- Band-limited additive oscillators (sine, saw, square, triangle) and FM synthesis.
- White, pink (Paul Kellet) and brown noise generators plus sparse crackle impulses.
- RBJ biquad filters (low-pass, high-pass, band-pass, peak) incl. time-varying sweeps, moving average.
- Soft-clip distortion, bit-crushing, tremolo/LFO, DC blocking, click-free edge fades,
  seamless loop crossfades, and peak normalization so nothing clips.

Encoding: `soundfile` (if installed) or an `ffmpeg` libvorbis subprocess from 16-bit PCM WAV.

Usage examples:
    python generate_sfx.py                          # Fill every missing SFX referenced by the project
    python generate_sfx.py --list-missing           # Report missing SFX references and their sources
    python generate_sfx.py --list-presets           # Show available synthesis archetypes
    python generate_sfx.py --preset explosion --name big_boom --seed 7
    python generate_sfx.py --name attack_swing --variants 6   # Audition seeded variants of a game SFX
    python generate_sfx.py --name attack_swing --seed 1234 --force  # Promote a favourite seed
"""
# pylint: disable=too-many-locals,too-many-arguments,too-many-positional-arguments,too-many-lines
# pylint: disable=import-outside-toplevel,invalid-name

import argparse
import math
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
import zlib
from typing import Callable, Dict, List, Optional, Sequence, Tuple

try:
    import numpy as np
except ImportError:  # pragma: no cover - exercised via monkeypatching in tests
    np = None

try:
    from scipy.signal import lfilter as _scipy_lfilter
except ImportError:
    _scipy_lfilter = None

try:
    import soundfile as _soundfile
except ImportError:
    _soundfile = None

# ==============================================================================
# CONFIGURABLE PARAMETERS
# ==============================================================================

SAMPLE_RATE = 44100  # Matches existing assets/audio/sfx/*.ogg and pygame.mixer default
CHANNELS = 1  # Mono, matching existing enemy SFX
SAMPLE_WIDTH_BYTES = 2  # 16-bit PCM intermediate
PCM_MAX = 32767
OGG_QUALITY = 5  # libvorbis VBR quality (-1..10); 5 ~ 160 kbps
PEAK_TARGET = 0.85  # ~-1.4 dBFS, leaves headroom for Vorbis inter-sample overshoot
EDGE_FADE_SECONDS = 0.003  # Click-free start/end ramps
DC_BLOCK_HZ = 25.0
BUTTERWORTH_Q = 0.7071
NYQUIST_SAFETY = 0.45  # Highest partial allowed as a fraction of the sample rate
MIN_FILTER_HZ = 10.0
MAX_ADDITIVE_HARMONICS = 40
FALLBACK_MAX_HARMONICS = 12  # Pure-Python mode trades brightness for speed
BIQUAD_SWEEP_BLOCK = 64  # Samples per coefficient update for time-varying filters
DEFAULT_ATTACK_SECONDS = 0.0015
PITCH_BEND_TAU = 0.03
PINK_NOISE_GAIN = 0.18
BROWN_LEAK = 0.995
BROWN_STEP = 0.04
TAU = 2.0 * math.pi

DEFAULT_SEED = 1337
DEFAULT_OUTPUT_DIR = os.path.join("assets", "audio", "sfx")
DEFAULT_VARIANT_DIR = os.path.join("assets", "audio", "sfx", "variants")
MUSIC_DIR = os.path.join("assets", "audio", "music")
SCAN_DIRS = ("engine", "ui", "rendering", "tools")
SCAN_FILES = ("main.py", "constants.py")
SFX_REF_PATTERN = re.compile(r"[\"']([A-Za-z0-9_\-]+\.ogg)[\"']")
MANIFEST_SOURCE = "SOUND_RECIPES manifest (docs/visual_style_and_assets.md)"

# Inharmonic partial ratios for metallic / glass resonances
RING_RATIOS_BLADE = (1.0, 2.76, 5.40)
RING_RATIOS_ARMOR = (1.0, 1.47, 2.09, 2.56, 3.37, 4.18)
RING_RATIOS_GLASS = (1.0, 2.32, 4.25)

# ==============================================================================
# SIGNAL HELPERS (numpy arrays when available, Python lists otherwise)
# ==============================================================================


def n_samples(duration: float) -> int:
    """Convert seconds to a (non-zero) sample count."""
    return max(1, int(round(duration * SAMPLE_RATE)))


def offset_samples(seconds: float) -> int:
    """Convert a (possibly zero) time offset to samples."""
    return max(0, int(round(seconds * SAMPLE_RATE)))


def as_signal(values):
    """Convert any float sequence into the active backend's signal type."""
    if np is not None:
        return np.asarray(values, dtype=np.float64)
    return [float(v) for v in values]


def to_list(signal) -> List[float]:
    """Return a plain Python list view of a signal."""
    if np is not None and isinstance(signal, np.ndarray):
        return signal.tolist()
    return list(signal)


def silence(n: int):
    """Return n samples of silence."""
    return np.zeros(n) if np is not None else [0.0] * n


def constant(value: float, n: int):
    """Return a constant control signal."""
    return np.full(n, float(value)) if np is not None else [float(value)] * n


def scale(signal, gain: float):
    """Multiply a signal by a scalar gain."""
    if np is not None:
        return np.asarray(signal) * gain
    return [v * gain for v in signal]


def add(a, b):
    """Element-wise sum of two equal-length signals."""
    if np is not None:
        return np.asarray(a) + np.asarray(b)
    return [p + q for p, q in zip(a, b)]


def multiply(a, b):
    """Element-wise product, truncated to the shorter signal."""
    n = min(len(a), len(b))
    if np is not None:
        return np.asarray(a[:n]) * np.asarray(b[:n])
    return [a[i] * b[i] for i in range(n)]


def sin_of(phase):
    """Element-wise sine."""
    if np is not None:
        return np.sin(phase)
    return [math.sin(p) for p in phase]


def peak(signal) -> float:
    """Absolute peak amplitude."""
    if len(signal) == 0:
        return 0.0
    if np is not None:
        return float(np.max(np.abs(signal)))
    return max(abs(v) for v in signal)


def normalize(signal, target: float = 1.0):
    """Scale a signal so its absolute peak equals target (silence is left untouched)."""
    pk = peak(signal)
    if pk < 1e-12:
        return signal
    return scale(signal, target / pk)


def mix(*layers: Tuple) -> object:
    """Sum layers given as (signal, gain) or (signal, gain, offset_seconds)."""
    parsed = []
    total = 0
    for layer in layers:
        sig, gain = layer[0], float(layer[1])
        off = offset_samples(layer[2]) if len(layer) > 2 else 0
        parsed.append((sig, gain, off))
        total = max(total, off + len(sig))
    out = silence(total)
    for sig, gain, off in parsed:
        if np is not None:
            out[off:off + len(sig)] += gain * np.asarray(sig)
        else:
            for i, v in enumerate(sig):
                out[off + i] += gain * v
    return out


def jitter(rng: random.Random, value: float, spread: float) -> float:
    """Randomize a value by +/- spread (fractional) for organic seeded variance."""
    return value * (1.0 + rng.uniform(-spread, spread))


# ==============================================================================
# ENVELOPES & CONTROL CURVES
# ==============================================================================


def adsr(n: int, attack: float, decay: float, sustain: float, release: float):
    """Classic ADSR envelope stretched over n samples (sustain fills the remainder)."""
    a, d, r = n_samples(attack), n_samples(decay), n_samples(release)
    if a + d + r > n:
        factor = n / float(a + d + r)
        a, d, r = max(1, int(a * factor)), max(1, int(d * factor)), max(1, int(r * factor))
    s = max(0, n - a - d - r)
    env = [i / a for i in range(a)]
    env += [1.0 - (1.0 - sustain) * (i / d) for i in range(d)]
    env += [sustain] * s
    env += [sustain * (1.0 - i / r) for i in range(r)]
    return as_signal(env[:n] + [0.0] * max(0, n - len(env)))


def exp_decay(n: int, tau: float, attack: float = DEFAULT_ATTACK_SECONDS):
    """Fast linear attack followed by exponential decay with time constant tau (seconds)."""
    a = max(1, int(attack * SAMPLE_RATE))
    tau_s = max(1.0, tau * SAMPLE_RATE)
    return as_signal([i / a if i < a else math.exp(-(i - a) / tau_s) for i in range(n)])


def swell(n: int, peak_pos: float, rise_power: float, fall_tau: float):
    """Power-curve rise to peak_pos (fraction) then exponential fall (tau as fraction of n)."""
    pk = max(1e-6, peak_pos)
    tau = max(1e-6, fall_tau)
    out = []
    for i in range(n):
        pos = i / n
        out.append((pos / pk) ** rise_power if pos < pk else math.exp(-(pos - pk) / tau))
    return as_signal(out)


def arch(n: int, peak_pos: float, rise_power: float = 2.0, fall_power: float = 1.5):
    """Smooth rise-and-fall envelope peaking at peak_pos (fraction of n), ending at zero."""
    pk = min(max(peak_pos, 1e-6), 1.0 - 1e-6)
    out = []
    for i in range(n):
        pos = i / n
        out.append((pos / pk) ** rise_power if pos < pk else ((1.0 - pos) / (1.0 - pk)) ** fall_power)
    return as_signal(out)


def freq_curve(f0: float, f1: float, n: int, curve: str = "exp"):
    """Pitch sweep from f0 to f1 over n samples (exponential or linear)."""
    if curve == "exp" and f0 > 0 and f1 > 0:
        ratio = f1 / f0
        return as_signal([f0 * ratio ** (i / n) for i in range(n)])
    return as_signal([f0 + (f1 - f0) * (i / n) for i in range(n)])


def pitch_drop(n: int, f0: float, f1: float, tau: float):
    """Exponential pitch drop from f0 settling toward f1 (classic kick / impact thump)."""
    tau_s = max(1.0, tau * SAMPLE_RATE)
    return as_signal([f1 + (f0 - f1) * math.exp(-i / tau_s) for i in range(n)])


def peak_curve(n: int, low: float, high: float, peak_pos: float):
    """Exponential rise from low to high at peak_pos, then fall back to low."""
    pk = min(max(peak_pos, 1e-6), 1.0 - 1e-6)
    up, down = high / low, low / high
    return as_signal([low * up ** ((i / n) / pk) if i / n < pk else high * down ** ((i / n - pk) / (1.0 - pk))
                      for i in range(n)])


# ==============================================================================
# OSCILLATORS & NOISE
# ==============================================================================


def phase_from_freq(freq, phase0: float = 0.0):
    """Integrate an instantaneous frequency signal (Hz) into phase (radians)."""
    k = TAU / SAMPLE_RATE
    if np is not None:
        return phase0 + np.cumsum(np.asarray(freq, dtype=np.float64)) * k
    acc = phase0
    out = []
    for f in freq:
        acc += f * k
        out.append(acc)
    return out


def oscillator(freq, shape: str = "sine", phase0: float = 0.0):
    """Band-limited additive oscillator driven by a frequency signal."""
    phase = phase_from_freq(freq, phase0)
    if shape == "sine":
        return sin_of(phase)
    top = max(1.0, peak(freq))
    cap = MAX_ADDITIVE_HARMONICS if np is not None else FALLBACK_MAX_HARMONICS
    k_max = max(1, min(cap, int(NYQUIST_SAFETY * SAMPLE_RATE / top)))
    if shape == "saw":
        terms = [(k, (2.0 / math.pi) / k) for k in range(1, k_max + 1)]
    elif shape == "square":
        terms = [(k, (4.0 / math.pi) / k) for k in range(1, k_max + 1, 2)]
    elif shape == "triangle":
        terms = [(k, (8.0 / math.pi ** 2) * (-1) ** ((k - 1) // 2) / k ** 2) for k in range(1, k_max + 1, 2)]
    else:
        raise ValueError(f"Unknown oscillator shape: {shape}")
    out = silence(len(phase))
    for k, weight in terms:
        out = add(out, scale(sin_of(scale(phase, float(k))), weight))
    return out


def fm_tone(freq, ratio: float, index):
    """Two-operator FM: carrier phase modulated by a sine at freq * ratio with an index signal."""
    carrier = phase_from_freq(freq)
    modulator = sin_of(phase_from_freq(scale(freq, ratio)))
    return sin_of(add(carrier, multiply(index, modulator)))


def lfo(n: int, rate, depth: float):
    """Unipolar tremolo gain curve: 1 - depth * (0.5 + 0.5 * sin)."""
    rate_sig = rate if not isinstance(rate, (int, float)) else constant(rate, n)
    wave_sig = sin_of(phase_from_freq(rate_sig))
    return as_signal([1.0 - depth * (0.5 + 0.5 * v) for v in to_list(wave_sig)])


def white_noise(n: int, rng: random.Random):
    """Uniform white noise in [-1, 1] (seeded, backend-independent)."""
    return as_signal([rng.uniform(-1.0, 1.0) for _ in range(n)])


def pink_noise(n: int, rng: random.Random):
    """Pink (1/f) noise using Paul Kellet's economy filter."""
    b0 = b1 = b2 = 0.0
    out = []
    for _ in range(n):
        w = rng.uniform(-1.0, 1.0)
        b0 = 0.99765 * b0 + w * 0.0990460
        b1 = 0.96300 * b1 + w * 0.2965164
        b2 = 0.57000 * b2 + w * 1.0526913
        out.append((b0 + b1 + b2 + w * 0.1848) * PINK_NOISE_GAIN)
    return as_signal(out)


def brown_noise(n: int, rng: random.Random):
    """Brown (red) noise via a leaky integrator, normalized to unit peak."""
    y = 0.0
    out = []
    for _ in range(n):
        y = BROWN_LEAK * y + BROWN_STEP * rng.uniform(-1.0, 1.0)
        out.append(y)
    return normalize(as_signal(out))


def crackle(n: int, rng: random.Random, rate_hz: float, decay: float):
    """Sparse random decaying noise impulses (debris, sizzle pops, paper crinkles)."""
    out = [0.0] * n
    count = max(1, int(rate_hz * n / SAMPLE_RATE))
    burst = max(2, int(decay * 5 * SAMPLE_RATE))
    tau_s = max(1.0, decay * SAMPLE_RATE)
    for _ in range(count):
        start = rng.randrange(0, max(1, n - 1))
        amp = rng.uniform(0.3, 1.0)
        for j in range(min(burst, n - start)):
            out[start + j] += amp * rng.uniform(-1.0, 1.0) * math.exp(-j / tau_s)
    return as_signal(out)


# ==============================================================================
# FILTERS & EFFECTS
# ==============================================================================


def biquad_coefficients(kind: str, freq: float, q: float = BUTTERWORTH_Q, gain_db: float = 0.0):
    """RBJ Audio-EQ-Cookbook biquad coefficients normalized by a0: (b0, b1, b2, a1, a2)."""
    freq = min(max(freq, MIN_FILTER_HZ), NYQUIST_SAFETY * SAMPLE_RATE)
    w0 = TAU * freq / SAMPLE_RATE
    cos_w, sin_w = math.cos(w0), math.sin(w0)
    alpha = sin_w / (2.0 * max(q, 1e-3))
    a0, a1, a2 = 1.0 + alpha, -2.0 * cos_w, 1.0 - alpha
    if kind == "lowpass":
        b0, b1, b2 = (1.0 - cos_w) / 2.0, 1.0 - cos_w, (1.0 - cos_w) / 2.0
    elif kind == "highpass":
        b0, b1, b2 = (1.0 + cos_w) / 2.0, -(1.0 + cos_w), (1.0 + cos_w) / 2.0
    elif kind == "bandpass":
        b0, b1, b2 = alpha, 0.0, -alpha
    elif kind == "peak":
        amp = 10.0 ** (gain_db / 40.0)
        b0, b1, b2 = 1.0 + alpha * amp, -2.0 * cos_w, 1.0 - alpha * amp
        a0, a2 = 1.0 + alpha / amp, 1.0 - alpha / amp
    else:
        raise ValueError(f"Unknown biquad type: {kind}")
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def _biquad_run(xs: Sequence[float], coeffs: Tuple[float, ...], state: Tuple[float, ...]):
    """Direct Form I biquad over a block; returns (outputs, new_state)."""
    b0, b1, b2, a1, a2 = coeffs
    x1, x2, y1, y2 = state
    out = []
    append = out.append
    for x0 in xs:
        y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, x0, y1, y0
        append(y0)
    return out, (x1, x2, y1, y2)


def biquad(signal, kind: str, freq: float, q: float = BUTTERWORTH_Q, gain_db: float = 0.0, order: int = 1):
    """Static biquad filter; order > 1 cascades stages for steeper slopes."""
    coeffs = biquad_coefficients(kind, freq, q, gain_db)
    out = signal
    for _ in range(max(1, order)):
        if _scipy_lfilter is not None and np is not None:
            b0, b1, b2, a1, a2 = coeffs
            out = _scipy_lfilter([b0, b1, b2], [1.0, a1, a2], np.asarray(out, dtype=np.float64))
        else:
            ys, _ = _biquad_run(to_list(out), coeffs, (0.0, 0.0, 0.0, 0.0))
            out = as_signal(ys)
    return out


def biquad_sweep(signal, kind: str, freq_signal, q: float = BUTTERWORTH_Q):
    """Time-varying biquad whose cutoff follows freq_signal (updated every BIQUAD_SWEEP_BLOCK samples)."""
    xs = to_list(signal)
    fs = to_list(freq_signal)
    state = (0.0, 0.0, 0.0, 0.0)
    out: List[float] = []
    for start in range(0, len(xs), BIQUAD_SWEEP_BLOCK):
        coeffs = biquad_coefficients(kind, fs[min(start, len(fs) - 1)], q)
        ys, state = _biquad_run(xs[start:start + BIQUAD_SWEEP_BLOCK], coeffs, state)
        out.extend(ys)
    return as_signal(out)


def moving_average(signal, width: int):
    """Centered moving-average (boxcar) low-pass smoothing."""
    width = max(1, int(width))
    if np is not None:
        return np.convolve(np.asarray(signal, dtype=np.float64), np.ones(width) / width, mode="same")
    xs = to_list(signal)
    prefix = [0.0]
    for v in xs:
        prefix.append(prefix[-1] + v)
    half = width // 2
    n = len(xs)
    return [(prefix[min(n, i + half + 1)] - prefix[max(0, i - half)]) / width for i in range(n)]


def soft_clip(signal, drive: float):
    """tanh waveshaping distortion normalized so unit input maps to unit output."""
    norm = math.tanh(drive) if drive > 0 else 1.0
    if np is not None:
        return np.tanh(np.asarray(signal) * drive) / norm
    return [math.tanh(v * drive) / norm for v in signal]


def bitcrush(signal, bits: int, hold: int = 1):
    """Quantize amplitude to the given bit depth with optional sample-and-hold decimation."""
    levels = float(2 ** (max(1, int(bits)) - 1))
    hold = max(1, int(hold))
    if np is not None:
        crushed = np.round(np.asarray(signal) * levels) / levels
        if hold > 1:
            crushed = np.repeat(crushed[::hold], hold)[:len(crushed)]
        return crushed
    out = []
    held = 0.0
    for i, v in enumerate(signal):
        if i % hold == 0:
            held = round(v * levels) / levels
        out.append(held)
    return out


def remove_dc(signal):
    """Block DC offset / subsonic content."""
    return biquad(signal, "highpass", DC_BLOCK_HZ)


def fade_edges(signal, seconds: float = EDGE_FADE_SECONDS):
    """Apply short linear fade-in/out to prevent clicks."""
    n = len(signal)
    k = min(n // 2, max(1, int(seconds * SAMPLE_RATE)))
    env = [1.0] * n
    for i in range(k):
        env[i] = i / k
        env[n - 1 - i] = i / k
    return multiply(signal, as_signal(env))


def make_loopable(signal, seconds: float):
    """Crossfade the tail into the head so the sample loops seamlessly (output is shorter by the fade)."""
    xs = to_list(signal)
    n = len(xs)
    k = min(n // 3, max(1, int(seconds * SAMPLE_RATE)))
    out = xs[:n - k]
    for i in range(k):
        t = i / k
        out[i] = xs[i] * t + xs[n - k + i] * (1.0 - t)
    return as_signal(out)


def finalize(signal, peak_target: float = PEAK_TARGET, loopable: bool = False):
    """DC-block, de-click (unless loopable), and peak-normalize with a hard safety clamp."""
    out = remove_dc(signal)
    if not loopable:
        out = fade_edges(out)
    out = normalize(out, peak_target)
    if np is not None:
        return np.clip(np.nan_to_num(out), -1.0, 1.0)
    return [min(1.0, max(-1.0, v if v == v else 0.0)) for v in out]


def metallic_ring(n: int, base_hz: float, ratios: Sequence[float], decay: float, rng: random.Random,
                  bend: float = 0.0):
    """Inharmonic decaying partials (blades, armor, bells, glass) with optional upward pitch bend."""
    layers = []
    bend_tau = max(1.0, PITCH_BEND_TAU * SAMPLE_RATE)
    bend_curve = [1.0 + bend * (1.0 - math.exp(-i / bend_tau)) for i in range(n)] if bend else None
    for idx, ratio in enumerate(ratios):
        f = base_hz * ratio * (1.0 + rng.uniform(-0.003, 0.003))
        if f >= NYQUIST_SAFETY * SAMPLE_RATE:
            continue
        freq = as_signal([f * b for b in bend_curve]) if bend_curve else constant(f, n)
        partial = multiply(oscillator(freq, "sine", rng.uniform(0.0, TAU)), exp_decay(n, decay / (1.0 + 0.5 * idx)))
        layers.append((partial, 1.0 / (1.0 + 0.6 * idx)))
    return mix(*layers) if layers else silence(n)


# ==============================================================================
# ARCHETYPE PRESETS
# ==============================================================================

PresetFn = Callable[[random.Random, Dict], object]


def preset_slash(rng: random.Random, p: Dict):
    """Blade swing: band-pass noise sweep swell followed by a short inharmonic blade ring."""
    n = n_samples(p["duration"])
    sweep = freq_curve(jitter(rng, p["sweep_start_hz"], 0.1), jitter(rng, p["sweep_end_hz"], 0.1), n)
    body = biquad_sweep(white_noise(n, rng), "bandpass", sweep, p["sweep_q"])
    body = multiply(normalize(body), swell(n, p["peak_pos"], 2.2, 0.18))
    ring_start = p["peak_pos"] * p["duration"]
    ring = metallic_ring(n - offset_samples(ring_start), jitter(rng, p["ring_hz"], 0.06), RING_RATIOS_BLADE,
                         p["ring_decay"], rng)
    return mix((body, p["noise_level"]), (normalize(ring), p["ring_level"], ring_start))


def preset_whoosh(rng: random.Random, p: Dict):
    """Air whoosh: pink noise through a rising-then-falling band-pass with a sparkle of high air."""
    n = n_samples(p["duration"])
    env = arch(n, p["peak_pos"])
    sweep = peak_curve(n, jitter(rng, p["low_hz"], 0.1), jitter(rng, p["high_hz"], 0.1), p["peak_pos"])
    body = normalize(biquad_sweep(pink_noise(n, rng), "bandpass", sweep, p["q"]))
    air = normalize(biquad(white_noise(n, rng), "highpass", p["air_hp_hz"], order=2))
    return mix((multiply(body, env), 1.0), (multiply(air, env), p["air_level"]))


def preset_hit_flesh(rng: random.Random, p: Dict):
    """Fleshy impact: sub-bass pitch-drop thump, low-passed body thud, and transient crunch."""
    n = n_samples(p["duration"])
    thump_freq = pitch_drop(n, jitter(rng, p["thump_start_hz"], 0.08), p["thump_end_hz"], p["thump_drop_tau"])
    thump = multiply(oscillator(thump_freq), exp_decay(n, p["thump_decay"]))
    body = multiply(normalize(biquad(white_noise(n, rng), "lowpass", jitter(rng, p["body_cutoff_hz"], 0.1), order=2)),
                    exp_decay(n, p["body_decay"]))
    crunch = multiply(normalize(biquad(white_noise(n, rng), "highpass", p["crunch_hp_hz"])),
                      exp_decay(n, p["crunch_decay"], attack=0.0005))
    mixed = mix((thump, 1.0), (body, p["body_level"]), (crunch, p["crunch_level"]))
    return soft_clip(normalize(mixed), p["drive"])


def preset_hit_armor(rng: random.Random, p: Dict):
    """Armored impact / parry clang: transient click, thud, and inharmonic metallic ring."""
    n = n_samples(p["duration"])
    click = multiply(normalize(biquad(white_noise(n, rng), "highpass", p["click_hp_hz"], order=2)),
                     exp_decay(n, p["click_decay"], attack=0.0003))
    thud_freq = pitch_drop(n, p["thud_start_hz"], p["thud_end_hz"], 0.03)
    thud = multiply(oscillator(thud_freq), exp_decay(n, p["thud_decay"]))
    ring = normalize(metallic_ring(n, jitter(rng, p["ring_hz"], 0.05), RING_RATIOS_ARMOR, p["ring_decay"], rng))
    return mix((click, p["click_level"]), (thud, p["thud_level"]), (ring, p["ring_level"]))


def preset_explosion(rng: random.Random, p: Dict):
    """Explosion / crumble: sub boom pitch drop, brown-noise rumble, bit-crushed crunch, and debris."""
    n = n_samples(p["duration"])
    boom_freq = pitch_drop(n, jitter(rng, p["boom_start_hz"], 0.08), p["boom_end_hz"], p["boom_drop_tau"])
    boom = multiply(oscillator(boom_freq), exp_decay(n, p["boom_decay"], attack=0.004))
    rumble = multiply(normalize(biquad(brown_noise(n, rng), "lowpass", p["rumble_cutoff_hz"], order=2)),
                      exp_decay(n, p["rumble_decay"], attack=0.01))
    crunch_src = bitcrush(soft_clip(white_noise(n, rng), 4.0), p["crunch_bits"], hold=2)
    crunch = multiply(normalize(biquad(crunch_src, "highpass", p["crunch_hp_hz"])), exp_decay(n, p["crunch_decay"]))
    debris = multiply(normalize(biquad(crackle(n, rng, p["debris_rate_hz"], 0.006), "bandpass", 1800.0, 0.8)),
                      exp_decay(n, p["duration"] * 0.35))
    mixed = mix((boom, p["sub_level"]), (rumble, p["rumble_level"]), (crunch, p["crunch_level"]),
                (debris, p["debris_level"]))
    return soft_clip(normalize(mixed), p["drive"])


def preset_footstep(rng: random.Random, p: Dict):
    """Footstep: short low-passed noise thud with subtle organic pitch / tone variance and grit."""
    n = n_samples(p["duration"])
    var = p["variance"]
    body = multiply(normalize(biquad(white_noise(n, rng), "lowpass", jitter(rng, p["cutoff_hz"], var), order=2)),
                    exp_decay(n, jitter(rng, p["body_decay"], var), attack=0.002))
    thud = multiply(oscillator(pitch_drop(n, jitter(rng, p["thud_hz"], var) * 1.6, jitter(rng, p["thud_hz"], var),
                                          0.015)), exp_decay(n, p["thud_decay"]))
    grit = multiply(normalize(biquad(white_noise(n, rng), "bandpass", jitter(rng, p["grit_hz"], var), 1.2)),
                    exp_decay(n, 0.01))
    return mix((body, 1.0), (thud, 0.6), (grit, jitter(rng, p["grit_level"], var)))


def preset_pickup(rng: random.Random, p: Dict):
    """Item pickup: ascending FM chime notes with a high sparkle tail."""
    n = n_samples(p["duration"])
    layers = []
    for idx, note in enumerate(p["notes_hz"]):
        start = idx * p["note_gap"]
        m = n - offset_samples(start)
        index = add(scale(exp_decay(m, 0.05), p["fm_index"]), constant(0.3, m))
        tone = multiply(
            fm_tone(constant(jitter(rng, note, 0.004), m), p["fm_ratio"], index),
            exp_decay(m, p["note_decay"]),
        )
        layers.append((tone, 1.0, start))
    last = p["notes_hz"][-1] * 3.0
    sparkle_start = (len(p["notes_hz"]) - 1) * p["note_gap"]
    m = n - offset_samples(sparkle_start)
    layers.append((multiply(oscillator(constant(last, m)), exp_decay(m, 0.05)), p["sparkle_level"], sparkle_start))
    return mix(*layers)


def preset_level_up(rng: random.Random, p: Dict):
    """Level-up / rest chime: harmonic major arpeggio with shimmer, optional warmth and soft exhale."""
    n = n_samples(p["duration"])
    layers = []
    for idx, interval in enumerate(p["intervals"]):
        start = idx * p["note_gap"]
        m = n - offset_samples(start)
        f = jitter(rng, p["root_hz"] * interval, 0.002)
        tone = silence(m)
        for h, amp in enumerate(p["harmonics"], start=1):
            if f * h < NYQUIST_SAFETY * SAMPLE_RATE:
                tone = add(tone, scale(oscillator(constant(f * h, m), "sine", rng.uniform(0.0, TAU)), amp))
        layers.append((multiply(tone, exp_decay(m, p["note_decay"], attack=0.006)), 1.0, start))
    shimmer_start = 2 * p["note_gap"]
    m = n - offset_samples(shimmer_start)
    shimmer = multiply(multiply(oscillator(constant(p["root_hz"] * 4.0, m)), lfo(m, p["shimmer_rate_hz"], 0.8)),
                       exp_decay(m, p["note_decay"] * 1.2, attack=0.05))
    layers.append((shimmer, p["shimmer_level"], shimmer_start))
    out = mix(*layers)
    if p["warm"]:
        out = biquad(out, "lowpass", p["warm_cutoff_hz"])
    if p["exhale"]:
        start = n * 0.45 / SAMPLE_RATE
        m = n - offset_samples(start)
        breath = multiply(normalize(biquad(pink_noise(m, rng), "bandpass", 700.0, 0.7)), arch(m, 0.55, 2.0, 2.0))
        out = mix((normalize(out), 1.0), (breath, p["exhale_level"], start))
    return out


def preset_ui_select(rng: random.Random, p: Dict):
    """UI blip / typewriter click / ink stamp: crisp tone, transient click, knock and optional stamp thud."""
    n = n_samples(p["duration"])
    tone = multiply(oscillator(constant(jitter(rng, p["tone_hz"], 0.01), n), p["tone_shape"]),
                    exp_decay(n, p["tone_decay"], attack=0.0008))
    click = multiply(normalize(biquad(white_noise(n, rng), "highpass", p["click_hp_hz"], order=2)),
                     exp_decay(n, p["click_decay"], attack=0.0002))
    knock = multiply(normalize(biquad(white_noise(n, rng), "lowpass", 1200.0, order=2)), exp_decay(n, 0.012))
    layers = [(tone, p["tone_level"]), (click, p["click_level"]), (knock, p["knock_level"])]
    if p["stamp"]:
        stamp = multiply(oscillator(pitch_drop(n, p["stamp_start_hz"], p["stamp_end_hz"], 0.03)),
                         exp_decay(n, p["stamp_decay"], attack=0.001))
        blot = multiply(normalize(biquad(pink_noise(n, rng), "lowpass", 600.0)), exp_decay(n, 0.05))
        layers += [(stamp, p["stamp_level"]), (blot, 0.4)]
    return mix(*layers)


def preset_warp(rng: random.Random, p: Dict):
    """Warp / portal: rising detuned saw drone through a resonant sweep, vacuum noise suck, and sub hum."""
    n = n_samples(p["duration"])
    base = freq_curve(p["start_hz"], p["end_hz"], n)
    drone = silence(n)
    for detune in (-p["detune"], 0.0, p["detune"]):
        drone = add(drone, oscillator(scale(base, 1.0 + detune), "saw", rng.uniform(0.0, TAU)))
    cutoff = freq_curve(p["cutoff_start_hz"], p["cutoff_end_hz"], n)
    drone = normalize(biquad_sweep(drone, "lowpass", cutoff, p["resonance_q"]))
    drone = multiply(drone, lfo(n, freq_curve(p["lfo_start_hz"], p["lfo_end_hz"], n, "lin"), p["lfo_depth"]))
    suck_env = as_signal([(i / n) ** 3 if i / n < 0.94 else (1.0 - i / n) / 0.06 * 0.83 for i in range(n)])
    suck = biquad_sweep(pink_noise(n, rng), "bandpass", freq_curve(3200.0, 300.0, n), 1.5)
    suck = multiply(normalize(suck), suck_env)
    sub = multiply(oscillator(freq_curve(p["start_hz"] * 0.7, p["end_hz"] * 0.5, n)), adsr(n, 0.3, 0.2, 0.8, 0.3))
    out = mix((drone, 1.0), (suck, p["suck_level"]), (sub, p["sub_level"]))
    return multiply(out, adsr(n, 0.25, 0.2, 0.85, 0.35))


def preset_arcane(rng: random.Random, p: Dict):
    """Arcane spell: vibrato FM drone, resonant noise sweep, and scattered crystalline pings."""
    n = n_samples(p["duration"])
    vib = lfo(n, p["vibrato_hz"], 2.0)  # 1 - 2*(0.5+0.5 sin) spans [-1, 1]
    freq = as_signal([p["carrier_hz"] * (1.0 + p["vibrato_depth"] * v) for v in to_list(vib)])
    index = scale(adsr(n, 0.2, 0.3, 0.6, 0.4), p["fm_index"])
    drone = multiply(fm_tone(freq, p["fm_ratio"], index), adsr(n, 0.12, 0.25, 0.7, 0.4))
    sweep = peak_curve(n, p["sweep_low_hz"], p["sweep_high_hz"], 0.5)
    swirl = multiply(normalize(biquad_sweep(white_noise(n, rng), "bandpass", sweep, p["sweep_q"])), arch(n, 0.5))
    layers = [(drone, 1.0), (swirl, p["sweep_level"])]
    for _ in range(int(p["sparkle_count"])):
        start = rng.uniform(0.05, 0.8) * p["duration"]
        m = n - offset_samples(start)
        ping = multiply(oscillator(constant(rng.uniform(2000.0, 6000.0), m)), exp_decay(m, 0.06))
        layers.append((ping, p["sparkle_level"] * rng.uniform(0.5, 1.0), start))
    return mix(*layers)


def preset_boss_roar(rng: random.Random, p: Dict):
    """Boss roar: formant-filtered vibrato saw, sub-harmonic, breath noise, growl AM, and saturation."""
    n = n_samples(p["duration"])
    vib = to_list(lfo(n, p["vibrato_hz"], 2.0))
    pitch = to_list(freq_curve(jitter(rng, p["start_hz"], 0.05), p["end_hz"], n))
    freq = as_signal([f * (1.0 + p["vibrato_depth"] * v) for f, v in zip(pitch, vib)])
    source = add(oscillator(freq, "saw"), scale(white_noise(n, rng), 0.25))
    voiced = silence(n)
    for idx, formant in enumerate(p["formants_hz"]):
        band = normalize(biquad(source, "bandpass", jitter(rng, formant, 0.05), p["formant_q"]))
        voiced = add(voiced, scale(band, 1.0 / (1.0 + idx * 0.6)))
    sub = oscillator(scale(freq, 0.5))
    breath = normalize(biquad(pink_noise(n, rng), "bandpass", 1200.0, 0.8))
    out = mix((normalize(voiced), 1.0), (sub, p["subharmonic_level"]), (breath, p["breath_level"]))
    out = multiply(out, lfo(n, p["growl_hz"], p["growl_depth"]))
    out = soft_clip(normalize(out), p["drive"])
    return multiply(out, adsr(n, 0.18, 0.3, 0.8, 0.7))


def preset_glint(rng: random.Random, p: Dict):
    """Telegraph 'shink' / glint: fast high band-pass noise sweep and a bright upward-bending ring."""
    n = n_samples(p["duration"])
    m = n_samples(p["sweep_time"])
    sweep = biquad_sweep(white_noise(m, rng), "bandpass", freq_curve(p["sweep_start_hz"], p["sweep_end_hz"], m),
                         p["sweep_q"])
    sweep = multiply(normalize(sweep), arch(m, 0.6))
    ring = normalize(metallic_ring(n, jitter(rng, p["ring_hz"], 0.04), RING_RATIOS_BLADE, p["ring_decay"], rng,
                                   bend=p["ring_bend"]))
    return mix((sweep, 1.0), (ring, p["ring_level"], p["sweep_time"] * 0.4))


def preset_hiss(rng: random.Random, p: Dict):
    """Acid sizzle: band-limited noise bed with crackle pops and flutter, crossfaded to loop seamlessly."""
    n = n_samples(p["duration"] + p["loop_fade"])
    bed = add(pink_noise(n, rng), scale(white_noise(n, rng), 0.5))
    bed = normalize(biquad(biquad(bed, "highpass", p["hp_hz"], order=2), "lowpass", p["lp_hz"]))
    pops = normalize(biquad(crackle(n, rng, p["crackle_rate_hz"], 0.002), "highpass", 1500.0))
    out = multiply(mix((bed, 1.0), (pops, p["crackle_level"])), lfo(n, p["flutter_hz"], p["flutter_depth"]))
    return make_loopable(out, p["loop_fade"])


def preset_rumble(rng: random.Random, p: Dict):
    """Seismic rumble followed by a low bit-crushed mechanical grind."""
    n = n_samples(p["duration"])
    rumble = multiply(normalize(biquad(brown_noise(n, rng), "lowpass", p["cutoff_hz"], order=2)), arch(n, 0.35))
    wobble = lfo(n, p["wobble_hz"], 2.0)
    sub_freq = as_signal([p["sub_hz"] * (1.0 + p["wobble_depth"] * v) for v in to_list(wobble)])
    sub = multiply(oscillator(sub_freq), adsr(n, 0.4, 0.3, 0.7, 0.8))
    start = p["grind_start"] * p["duration"]
    m = n - offset_samples(start)
    grit = add(constant(0.5, m), scale(normalize(moving_average(white_noise(m, rng), 400)), 0.5))
    grind = multiply(oscillator(constant(p["grind_hz"], m), "saw"), grit)
    grind = bitcrush(normalize(biquad(grind, "bandpass", p["grind_band_hz"], 2.0)), p["grind_bits"], hold=3)
    grind = multiply(grind, arch(m, 0.4))
    return mix((rumble, p["rumble_level"]), (sub, 0.7), (grind, p["grind_level"], start))


def preset_rustle(rng: random.Random, p: Dict):
    """Parchment rustle: scattered band-pass crinkles over a paper drag, ending in a crisp snap."""
    n = n_samples(p["duration"])
    drag = multiply(normalize(biquad(pink_noise(n, rng), "bandpass", 1500.0, 0.8)), arch(n, 0.4))
    layers = [(drag, p["body_level"])]
    for _ in range(int(p["crinkle_count"])):
        start = rng.uniform(0.0, p["spread"])
        decay = rng.uniform(p["crinkle_decay_min"], p["crinkle_decay_max"])
        m = n_samples(decay * 6)
        band = rng.uniform(p["band_low_hz"], p["band_high_hz"])
        crinkle = multiply(normalize(biquad(white_noise(m, rng), "bandpass", band, 1.5)), exp_decay(m, decay))
        layers.append((crinkle, rng.uniform(0.4, 1.0), start))
    snap_start = p["spread"]
    m = n - offset_samples(snap_start)
    snap = multiply(normalize(biquad(white_noise(m, rng), "highpass", p["snap_hp_hz"], order=2)),
                    exp_decay(m, 0.004, attack=0.0003))
    layers.append((snap, p["snap_level"], snap_start))
    return mix(*layers)


def preset_splash(rng: random.Random, p: Dict):
    """Wet ink splash / flask slosh: noise burst, rising bubble blips, optional slosh, thump, glass tink."""
    n = n_samples(p["duration"])
    burst = multiply(normalize(biquad(white_noise(n, rng), "lowpass", p["burst_cutoff_hz"], order=2)),
                     exp_decay(n, p["burst_decay"], attack=0.002))
    layers = [(burst, p["burst_level"])]
    bubble_len = n_samples(0.06)
    for _ in range(int(p["bubble_count"])):
        start = rng.uniform(0.02, 0.55) * p["duration"]
        f0 = rng.uniform(p["bubble_low_hz"], p["bubble_high_hz"])
        bubble = multiply(oscillator(freq_curve(f0, f0 * 2.2, bubble_len)), exp_decay(bubble_len, 0.02))
        layers.append((bubble, p["bubble_level"] * rng.uniform(0.5, 1.0), start))
    if p["slosh_level"] > 0:
        m = n_samples(p["duration"] * 0.6)
        slosh = biquad_sweep(pink_noise(m, rng), "bandpass", peak_curve(m, 250.0, 900.0, 0.4), 1.2)
        layers.append((multiply(normalize(slosh), arch(m, 0.4)), p["slosh_level"]))
    if p["thump_level"] > 0:
        thump = multiply(oscillator(pitch_drop(n, 120.0, 50.0, 0.03)), exp_decay(n, 0.07))
        layers.append((thump, p["thump_level"]))
    if p["tink"]:
        m = n - offset_samples(p["tink_time"])
        tink = normalize(metallic_ring(m, jitter(rng, 3100.0, 0.03), RING_RATIOS_GLASS, 0.16, rng))
        layers.append((tink, p["tink_level"], p["tink_time"]))
    return mix(*layers)


def preset_rain(rng: random.Random, p: Dict):
    """Heavy rainfall loop: layered brown/pink/white noise with droplet patter and crossfade."""
    n = n_samples(p["duration"] + p["loop_fade"])
    downpour = normalize(biquad(brown_noise(n, rng), "lowpass", p["body_lp_hz"], q=0.9, order=2))
    sheet = normalize(biquad(pink_noise(n, rng), "bandpass", p["mid_bp_hz"], p["mid_q"]))
    gust = lfo(n, p["gust_hz"], p["gust_depth"])
    sheet = multiply(sheet, gust)
    hiss = normalize(biquad(white_noise(n, rng), "bandpass", p["high_bp_hz"], 0.9))
    patter = normalize(biquad(crackle(n, rng, p["patter_rate_hz"], 0.0025), "bandpass", p["patter_bp_hz"], 1.5))
    bed = mix(
        (downpour, p["body_level"]),
        (sheet, p["mid_level"]),
        (hiss, p["high_level"]),
        (patter, p["patter_level"]),
    )
    return make_loopable(bed, p["loop_fade"])


def preset_mumble(rng: random.Random, p: Dict):
    """Closed-mouth vocal mumble: low-passed vocal buzz formants modulated by syllabic cadence."""
    n = n_samples(p["duration"])
    f_start = jitter(rng, p["f0_hz"], 0.03)
    f_end = f_start * p["pitch_rise"]
    freq = freq_curve(f_start, f_end, n, "lin")
    buzz = mix((oscillator(freq, "saw"), 0.7), (oscillator(scale(freq, 0.5), "triangle"), 0.5))
    buzz = soft_clip(buzz, 1.6)
    vocal = biquad(buzz, "lowpass", p["lp_hz"], q=p["formant_q"], order=2)

    syllables = max(1, int(p["syllables"]))
    step = n / syllables
    env = [0.0] * n
    for idx in range(syllables):
        s0 = int(idx * step + step * 0.08)
        s1 = int((idx + 1) * step - step * 0.14)
        span = max(4, s1 - s0)
        amp = rng.uniform(0.75, 1.0)
        for j in range(span):
            if s0 + j < n:
                phase = j / (span - 1)
                env[s0 + j] = amp * (math.sin(math.pi * phase) ** 1.3)
    return multiply(normalize(vocal), as_signal(env))


def preset_storm_intro(rng: random.Random, p: Dict):
    """Cinematic storm intro: swelling rain, electric lightning crack, and rolling thunder."""
    n = n_samples(p["duration"])
    rain_bed = mix(
        (normalize(biquad(brown_noise(n, rng), "lowpass", 650.0, q=0.85, order=2)), 0.7),
        (normalize(biquad(pink_noise(n, rng), "bandpass", 1550.0, 0.8)), 0.55),
    )
    rain_env = arch(n, 0.45, 1.4, 1.8)
    rain = multiply(rain_bed, rain_env)

    # Primary lightning crack + thunder roll
    c1_len = n_samples(0.32)
    crack1 = multiply(
        normalize(biquad(white_noise(c1_len, rng), "highpass", 1600.0, order=2)),
        exp_decay(c1_len, 0.04, attack=0.001),
    )
    snap1 = multiply(
        normalize(biquad(white_noise(c1_len, rng), "bandpass", 3400.0, 1.2)),
        exp_decay(c1_len, 0.025, attack=0.0005),
    )

    t_len = n_samples(1.75)
    thunder_noise = normalize(biquad(brown_noise(t_len, rng), "lowpass", 145.0, q=0.9, order=2))
    thunder_sub = oscillator(freq_curve(52.0, 30.0, t_len), "sine")
    thunder = multiply(
        mix((thunder_noise, 0.9), (thunder_sub, 0.55)),
        multiply(exp_decay(t_len, 0.72, attack=0.02), lfo(t_len, 4.2, 0.22)),
    )

    # Secondary distant fork crack
    c2_len = n_samples(0.24)
    crack2 = multiply(
        normalize(biquad(white_noise(c2_len, rng), "bandpass", 2600.0, 1.1)),
        exp_decay(c2_len, 0.035, attack=0.001),
    )

    return mix(
        (rain, p["rain_level"]),
        (crack1, p["crack_level"], p["crack1_time"]),
        (snap1, p["crack_level"] * 0.8, p["crack1_time"]),
        (thunder, p["thunder_level"], p["crack1_time"] + 0.03),
        (crack2, p["crack_level"] * 0.55, p["crack2_time"]),
    )


def preset_door_open(rng: random.Random, p: Dict):
    """Wooden latch click + warm resonant oak hinge creak (~0.35s)."""
    dur = float(p["duration"])
    n = n_samples(dur)

    # 1. Crisp iron-and-wood latch release click at t=0.0s
    latch_len = min(n, n_samples(0.045))
    latch_click = multiply(
        normalize(biquad(white_noise(latch_len, rng), "bandpass", p["latch_hz"], 2.2)),
        exp_decay(latch_len, 0.007, attack=0.0005),
    )
    bolt_thud = multiply(
        oscillator(freq_curve(320.0, 125.0, latch_len), "sine"),
        exp_decay(latch_len, 0.018, attack=0.0008),
    )

    # 2. Low wooden hinge creak with stick-slip flutter (t=0.04s..end)
    creak_start = min(dur * 0.12, 0.045)
    creak_len = max(16, n - n_samples(creak_start))
    creak_osc = oscillator(freq_curve(p["creak_start_hz"], p["creak_end_hz"], creak_len), "saw")
    creak_band = normalize(biquad(creak_osc, "bandpass", p["creak_body_hz"], 2.4))
    stick_slip = lfo(creak_len, p["creak_flutter_hz"], 0.42)
    creak_env = multiply(arch(creak_len, 0.32, 1.3, 1.7), stick_slip)
    creak = multiply(soft_clip(creak_band, 1.6), creak_env)

    # 3. Warm low-passed oak swing wood-body air movement
    wood_body = multiply(
        normalize(biquad(pink_noise(creak_len, rng), "lowpass", 520.0, q=0.9, order=2)),
        arch(creak_len, 0.40, 1.2, 1.5),
    )

    return mix(
        (latch_click, p["latch_level"], 0.0),
        (bolt_thud, p["latch_level"] * 0.72, 0.004),
        (creak, p["creak_level"], creak_start),
        (wood_body, p["wood_level"], creak_start),
    )


def preset_slug_boss_slime(rng: random.Random, p: Dict):
    """Low resonant gastropod bellow + viscous bubbling slime squelch (~0.55s)."""
    dur = float(p["duration"])
    n = n_samples(dur)

    # 1. Low guttural gastropod bellow with warbling throat modulation
    bellow_osc = oscillator(freq_curve(p["bellow_start_hz"], p["bellow_end_hz"], n), "saw")
    bellow_sub = oscillator(freq_curve(p["bellow_start_hz"] * 0.5, p["bellow_end_hz"] * 0.5, n), "sine")
    bellow_body = normalize(biquad(mix((bellow_osc, 0.8), (bellow_sub, 0.7)), "bandpass", p["bellow_formant_hz"], 1.8))
    bellow_env = multiply(arch(n, 0.28, 1.3, 1.8), lfo(n, p["warble_hz"], 0.32))
    bellow = multiply(soft_clip(bellow_body, 1.8), bellow_env)

    # 2. Wet viscous slime secretion squelch sweep
    squelch_start = min(dur * 0.14, 0.08)
    sq_len = max(16, n - n_samples(squelch_start))
    sq_noise = normalize(biquad(pink_noise(sq_len, rng), "bandpass", p["squelch_hz"], 2.2))
    sq_high = normalize(biquad(white_noise(sq_len, rng), "bandpass", p["squelch_hz"] * 2.1, 2.8))
    sq_env = multiply(arch(sq_len, 0.35, 1.4, 1.9), lfo(sq_len, 14.0, 0.35))
    squelch = multiply(mix((sq_noise, 0.9), (sq_high, 0.55)), sq_env)

    # 3. Viscous popping slime bubbles trailing the secretion
    layers = [
        (bellow, p["bellow_level"], 0.0),
        (squelch, p["squelch_level"], squelch_start),
    ]
    b_count = max(2, int(p["bubble_count"]))
    for idx in range(b_count):
        b_len = n_samples(0.055)
        f0 = rng.uniform(260.0, 480.0)
        f1 = f0 * rng.uniform(1.6, 2.2)
        bub = multiply(oscillator(freq_curve(f0, f1, b_len), "sine"), exp_decay(b_len, 0.018, attack=0.002))
        t_off = squelch_start + (idx / max(1, b_count)) * max(0.05, dur - squelch_start - 0.06)
        layers.append((bub, p["bubble_level"], t_off))

    return mix(*layers)


def preset_meadow_censor_whistle(rng: random.Random, p: Dict):
    """Shrill carved-bone shepherd's culling whistle (~0.45s): trilled dual-pitch call + breathy air edge."""
    dur = float(p["duration"])
    n = n_samples(dur)
    f_low = float(p["base_hz"])
    f_high = float(p["high_hz"])
    trill_hz = float(p["trill_hz"])

    # Two-part shepherd command contour: rapid upward glide + trilled sustain + crisp terminal flick
    split = max(1, int(n * 0.34))
    tail_n = max(1, n - split)
    if np is not None:
        t1 = np.arange(split, dtype=np.float64) / SAMPLE_RATE
        f1 = f_low + (f_high - f_low) * (1.0 - np.exp(-t1 / 0.045))
        t2 = np.arange(tail_n, dtype=np.float64) / SAMPLE_RATE
        f2 = f_high * (1.0 + 0.055 * np.sin(TAU * trill_hz * t2)) - 140.0 * (t2 / max(0.05, dur * 0.66))
        freq_arr = np.concatenate([f1, f2])
    else:
        f1 = [f_low + (f_high - f_low) * (1.0 - math.exp(-(i / SAMPLE_RATE) / 0.045)) for i in range(split)]
        f2 = [
            f_high * (1.0 + 0.055 * math.sin(TAU * trill_hz * (i / SAMPLE_RATE)))
            - 140.0 * ((i / SAMPLE_RATE) / max(0.05, dur * 0.66))
            for i in range(tail_n)
        ]
        freq_arr = f1 + f2

    # Fundamental bone-flute pipe + subtle 2nd/3rd harmonics + pea-trill amplitude flutter
    core = oscillator(freq_arr, "sine")
    overtone = oscillator(scale(freq_arr, 2.0), "sine")
    pipe = mix((core, 0.85), (overtone, 0.28))
    pipe = multiply(pipe, multiply(adsr(n, 0.014, 0.05, 0.82, 0.08), lfo(n, trill_hz, 0.24)))

    # Breathy carved-bone air chiff around the whistle bore
    air = normalize(biquad(white_noise(n, rng), "bandpass", float(p["air_hz"]), 2.6))
    air = multiply(air, adsr(n, 0.008, 0.06, 0.48, 0.09))

    return mix((pipe, float(p["pipe_level"])), (air, float(p["air_level"])))


def preset_frost_breath(rng: random.Random, p: Dict):
    """Howling sub-zero gale + shimmering crystalline freeze chime (~0.60s)."""
    dur = float(p["duration"])
    n = n_samples(dur)

    # Howling sub-zero wind sweep (band-passed pink/white gale with airy hiss)
    gale_raw = mix((pink_noise(n, rng), 0.72), (white_noise(n, rng), 0.35))
    gale = normalize(biquad(gale_raw, "bandpass", float(p["gale_hz"]), 1.8))
    gale = multiply(gale, adsr(n, 0.05, 0.14, 0.74, 0.18))
    frost_hiss = normalize(biquad(white_noise(n, rng), "highpass", float(p["hiss_hz"]), 1.1))
    frost_hiss = multiply(frost_hiss, adsr(n, 0.03, 0.12, 0.52, 0.20))

    # Crystalline freeze chime (bell-like inharmonic ice partials with slow shimmer)
    chime_hz = float(p["chime_hz"])
    c1 = multiply(oscillator(constant(chime_hz, n), "sine"), exp_decay(n, 0.24))
    c2 = multiply(oscillator(constant(chime_hz * 1.498, n), "sine"), exp_decay(n, 0.19))
    c3 = multiply(oscillator(constant(chime_hz * 2.756, n), "sine"), exp_decay(n, 0.12))
    chime = multiply(mix((c1, 0.65), (c2, 0.48), (c3, 0.32)), lfo(n, 14.0, 0.22))

    return mix(
        (gale, float(p["gale_level"])),
        (frost_hiss, float(p["hiss_level"])),
        (chime, float(p["chime_level"])),
    )


def preset_ice_crack(rng: random.Random, p: Dict):
    """Brittle high-frequency ice fracture snap + short glassy crystal ring (~0.22s)."""
    dur = float(p["duration"])
    n = n_samples(dur)

    # Sharp brittle crack transient (2 micro-snaps offset by ~18ms)
    snap1 = normalize(biquad(white_noise(n, rng), "highpass", float(p["crack_hp_hz"]), 1.2))
    snap1 = multiply(snap1, exp_decay(n, 0.014))
    snap2_len = max(1, n - offset_samples(0.018))
    snap2 = normalize(biquad(white_noise(snap2_len, rng), "bandpass", float(p["crack_bp_hz"]), 2.8))
    snap2 = multiply(snap2, exp_decay(snap2_len, 0.018))
    layers = [
        (snap1, float(p["snap_level"])),
        (snap2, float(p["snap_level"]) * 0.72, 0.018),
    ]

    # Glassy stress fracture ping
    ring_hz = float(p["ring_hz"])
    ping_a = multiply(oscillator(constant(ring_hz, n), "sine"), exp_decay(n, 0.065))
    ping_b = multiply(oscillator(constant(ring_hz * 1.62, n), "sine"), exp_decay(n, 0.042))
    ring = mix((ping_a, 0.70), (ping_b, 0.45))
    layers.append((ring, float(p["ring_level"])))
    return mix(*layers)


def preset_ice_shatter(rng: random.Random, p: Dict):
    """Cascading multi-shard ice-crystal burst + frosty scatter tail (~0.45s)."""
    dur = float(p["duration"])
    n = n_samples(dur)

    # Initial explosive ice burst + low-mid thud
    burst = normalize(biquad(white_noise(n, rng), "highpass", 2400.0, 1.0))
    burst = multiply(burst, exp_decay(n, 0.048))
    thud = multiply(oscillator(pitch_drop(n, 210.0, 62.0, 0.03), "sine"), exp_decay(n, 0.055))
    layers = [
        (burst, float(p["burst_level"])),
        (thud, float(p["thud_level"])),
    ]

    # Cascading crystalline glass/ice shard tinkles scattered over the tail
    shard_count = int(p["shard_count"])
    for idx in range(shard_count):
        off_s = 0.012 + (idx / max(1, shard_count)) * (dur * 0.58) + rng.uniform(0.0, 0.018)
        rem = n - offset_samples(off_s)
        if rem <= 32:
            continue
        f_shard = rng.uniform(1900.0, 5400.0)
        tau = rng.uniform(0.024, 0.072)
        s_len = min(rem, n_samples(tau * 4.0))
        tone = multiply(oscillator(constant(f_shard, s_len), "sine"), exp_decay(s_len, tau))
        over = multiply(oscillator(constant(f_shard * 1.54, s_len), "sine"), exp_decay(s_len, tau * 0.7))
        shard = mix((tone, 0.72), (over, 0.38))
        layers.append((shard, float(p["shard_level"]) * rng.uniform(0.45, 0.95), off_s))

    return mix(*layers)


PRESETS: Dict[str, Tuple[PresetFn, Dict, str]] = {
    "slash": (preset_slash, {
        "duration": 0.32, "sweep_start_hz": 700.0, "sweep_end_hz": 5200.0, "sweep_q": 1.4, "peak_pos": 0.35,
        "ring_hz": 2600.0, "ring_level": 0.22, "ring_decay": 0.11, "noise_level": 1.0,
    }, "Filtered noise sweep + blade ring"),
    "whoosh": (preset_whoosh, {
        "duration": 0.42, "low_hz": 250.0, "high_hz": 1900.0, "q": 0.9, "peak_pos": 0.5,
        "air_hp_hz": 4500.0, "air_level": 0.3,
    }, "Pink-noise band-pass rise/fall air movement"),
    "hit_flesh": (preset_hit_flesh, {
        "duration": 0.36, "thump_start_hz": 150.0, "thump_end_hz": 45.0, "thump_drop_tau": 0.04,
        "thump_decay": 0.09, "body_cutoff_hz": 900.0, "body_decay": 0.045, "body_level": 0.7,
        "crunch_hp_hz": 2200.0, "crunch_decay": 0.01, "crunch_level": 0.55, "drive": 2.4,
    }, "Sub-bass pitch drop + body thud + transient crunch"),
    "hit_armor": (preset_hit_armor, {
        "duration": 0.5, "click_hp_hz": 3500.0, "click_decay": 0.004, "click_level": 0.6,
        "thud_start_hz": 190.0, "thud_end_hz": 85.0, "thud_decay": 0.05, "thud_level": 0.55,
        "ring_hz": 1150.0, "ring_decay": 0.22, "ring_level": 0.8,
    }, "Transient click + thud + inharmonic metal ring"),
    "explosion": (preset_explosion, {
        "duration": 1.3, "boom_start_hz": 95.0, "boom_end_hz": 28.0, "boom_drop_tau": 0.18, "boom_decay": 0.4,
        "sub_level": 1.0, "rumble_cutoff_hz": 380.0, "rumble_decay": 0.5, "rumble_level": 0.7,
        "crunch_hp_hz": 1100.0, "crunch_decay": 0.07, "crunch_level": 0.8, "crunch_bits": 6,
        "debris_rate_hz": 40.0, "debris_level": 0.25, "drive": 3.0,
    }, "Sub boom + brown rumble + bit-crushed crunch + debris"),
    "footstep": (preset_footstep, {
        "duration": 0.17, "cutoff_hz": 420.0, "thud_hz": 85.0, "thud_decay": 0.03, "body_decay": 0.04,
        "grit_hz": 2200.0, "grit_level": 0.18, "variance": 0.12, "peak": 0.7,
    }, "Short low-passed thud with organic variance"),
    "pickup": (preset_pickup, {
        "duration": 0.5, "notes_hz": (880.0, 1318.5), "note_gap": 0.075, "fm_ratio": 2.0, "fm_index": 2.6,
        "note_decay": 0.14, "sparkle_level": 0.15,
    }, "Ascending FM chime notes + sparkle"),
    "level_up": (preset_level_up, {
        "duration": 1.35, "root_hz": 523.25, "intervals": (1.0, 1.25, 1.5, 2.0), "note_gap": 0.085,
        "note_decay": 0.45, "harmonics": (1.0, 0.35, 0.15), "shimmer_level": 0.18, "shimmer_rate_hz": 7.0,
        "warm": False, "warm_cutoff_hz": 2200.0, "exhale": False, "exhale_level": 0.22,
    }, "Harmonic major arpeggio + shimmer (optional warmth/exhale)"),
    "ui_select": (preset_ui_select, {
        "duration": 0.09, "tone_hz": 1750.0, "tone_decay": 0.018, "tone_level": 0.8, "tone_shape": "square",
        "click_hp_hz": 4000.0, "click_decay": 0.0025, "click_level": 0.6, "knock_level": 0.0,
        "stamp": False, "stamp_start_hz": 170.0, "stamp_end_hz": 70.0, "stamp_decay": 0.07, "stamp_level": 0.9,
    }, "Crisp blip / click (optional stamp thud)"),
    "warp": (preset_warp, {
        "duration": 1.5, "start_hz": 55.0, "end_hz": 110.0, "detune": 0.012, "cutoff_start_hz": 180.0,
        "cutoff_end_hz": 2600.0, "resonance_q": 5.0, "suck_level": 0.6, "sub_level": 0.5,
        "lfo_start_hz": 5.0, "lfo_end_hz": 16.0, "lfo_depth": 0.35,
    }, "Rising resonant drone + vacuum suck + sub hum"),
    "arcane": (preset_arcane, {
        "duration": 1.2, "carrier_hz": 330.0, "fm_ratio": 1.5, "fm_index": 3.0, "vibrato_hz": 5.5,
        "vibrato_depth": 0.01, "sweep_low_hz": 600.0, "sweep_high_hz": 3800.0, "sweep_q": 8.0,
        "sweep_level": 0.4, "sparkle_count": 7, "sparkle_level": 0.25,
    }, "FM drone + resonant sweep + crystalline pings"),
    "boss_roar": (preset_boss_roar, {
        "duration": 2.1, "start_hz": 88.0, "end_hz": 52.0, "vibrato_hz": 6.0, "vibrato_depth": 0.03,
        "growl_hz": 28.0, "growl_depth": 0.45, "formants_hz": (480.0, 950.0, 2400.0), "formant_q": 4.0,
        "subharmonic_level": 0.6, "breath_level": 0.35, "drive": 3.2,
    }, "Formant saw + sub-harmonic + growl + saturation"),
    "glint": (preset_glint, {
        "duration": 0.38, "sweep_start_hz": 2800.0, "sweep_end_hz": 9500.0, "sweep_time": 0.06, "sweep_q": 2.5,
        "ring_hz": 3300.0, "ring_bend": 0.04, "ring_decay": 0.14, "ring_level": 0.75,
    }, "High noise sweep + bright bending ring (telegraph shink)"),
    "hiss": (preset_hiss, {
        "duration": 0.9, "hp_hz": 2600.0, "lp_hz": 9000.0, "crackle_rate_hz": 55.0, "crackle_level": 0.5,
        "flutter_hz": 11.0, "flutter_depth": 0.25, "loop_fade": 0.12, "loopable": True, "peak": 0.45,
    }, "Loopable acid sizzle with crackle"),
    "rumble": (preset_rumble, {
        "duration": 2.4, "cutoff_hz": 140.0, "sub_hz": 34.0, "wobble_hz": 0.7, "wobble_depth": 0.08,
        "grind_hz": 46.0, "grind_start": 0.35, "grind_band_hz": 320.0, "grind_level": 0.55, "grind_bits": 7,
        "rumble_level": 1.0,
    }, "Seismic rumble + bit-crushed mechanical grind"),
    "rustle": (preset_rustle, {
        "duration": 0.34, "crinkle_count": 6, "band_low_hz": 2200.0, "band_high_hz": 5200.0,
        "crinkle_decay_min": 0.008, "crinkle_decay_max": 0.022, "spread": 0.24, "snap_level": 0.7,
        "snap_hp_hz": 5000.0, "body_level": 0.25,
    }, "Parchment crinkles + crisp snap"),
    "splash": (preset_splash, {
        "duration": 0.6, "burst_cutoff_hz": 1600.0, "burst_decay": 0.08, "burst_level": 1.0, "bubble_count": 5,
        "bubble_low_hz": 350.0, "bubble_high_hz": 1300.0, "bubble_level": 0.45, "slosh_level": 0.0,
        "thump_level": 0.0, "tink": False, "tink_time": 0.3, "tink_level": 0.5,
    }, "Wet burst + bubbles (optional slosh/thump/glass tink)"),
    "rain": (preset_rain, {
        "duration": 3.2, "loop_fade": 0.35, "body_lp_hz": 480.0, "body_level": 0.65,
        "mid_bp_hz": 1350.0, "mid_q": 0.75, "mid_level": 0.7, "gust_hz": 0.65, "gust_depth": 0.16,
        "high_bp_hz": 4200.0, "high_level": 0.3, "patter_rate_hz": 65.0, "patter_bp_hz": 2800.0,
        "patter_level": 0.25, "loopable": True, "peak": 0.72,
    }, "Seamless looping heavy rainfall with droplet patter"),
    "mumble": (preset_mumble, {
        "duration": 0.72, "f0_hz": 135.0, "pitch_rise": 0.96, "lp_hz": 360.0,
        "formant_q": 1.8, "syllables": 4, "peak": 0.70,
    }, "Closed-mouth vocal mumble with syllabic cadence"),
    "storm_intro": (preset_storm_intro, {
        "duration": 2.5, "rain_level": 0.55, "crack_level": 1.0, "thunder_level": 0.95,
        "crack1_time": 0.35, "crack2_time": 1.25, "peak": 0.85,
    }, "Swelling rain + lightning crack + rolling thunder intro"),
    "door_open": (preset_door_open, {
        "duration": 0.35, "latch_hz": 2400.0, "latch_level": 0.85,
        "creak_start_hz": 165.0, "creak_end_hz": 215.0, "creak_body_hz": 440.0,
        "creak_flutter_hz": 24.0, "creak_level": 0.65, "wood_level": 0.45, "peak": 0.68,
    }, "Wooden latch click + low oak hinge creak"),
    "slug_boss_slime": (preset_slug_boss_slime, {
        "duration": 0.55, "bellow_start_hz": 74.0, "bellow_end_hz": 44.0,
        "bellow_formant_hz": 220.0, "warble_hz": 17.0, "bellow_level": 0.85,
        "squelch_hz": 780.0, "squelch_level": 0.75, "bubble_count": 5, "bubble_level": 0.42,
        "peak": 0.80,
    }, "Low resonant gastropod bellow + viscous slime squelch"),
    "meadow_censor_whistle": (preset_meadow_censor_whistle, {
        "duration": 0.45, "base_hz": 1820.0, "high_hz": 2540.0, "trill_hz": 26.0,
        "air_hz": 2850.0, "pipe_level": 0.88, "air_level": 0.34, "peak": 0.78,
    }, "Shrill carved-bone shepherd's culling whistle"),
    "frost_breath": (preset_frost_breath, {
        "duration": 0.60, "gale_hz": 920.0, "hiss_hz": 3600.0, "chime_hz": 1760.0,
        "gale_level": 0.78, "hiss_level": 0.42, "chime_level": 0.56, "peak": 0.80,
    }, "Howling sub-zero gale + crystalline freeze chime"),
    "ice_crack": (preset_ice_crack, {
        "duration": 0.22, "crack_hp_hz": 3200.0, "crack_bp_hz": 4800.0, "ring_hz": 2380.0,
        "snap_level": 0.92, "ring_level": 0.58, "peak": 0.82,
    }, "Brittle ice fracture snap + glassy stress ping"),
    "ice_shatter": (preset_ice_shatter, {
        "duration": 0.45, "burst_level": 0.88, "thud_level": 0.40, "shard_count": 9,
        "shard_level": 0.52, "peak": 0.84,
    }, "Cascading multi-shard ice-crystal burst"),
}

# Game SFX manifest: file name -> (preset, parameter overrides). Mirrors docs/visual_style_and_assets.md Section 6.
SOUND_RECIPES: Dict[str, Tuple[str, Dict]] = {
    "attack_swing.ogg": ("slash", {}),
    "attack_hit.ogg": ("hit_flesh", {}),
    "sword_swing.ogg": ("whoosh", {
        "duration": 0.16, "low_hz": 550.0, "high_hz": 3200.0, "q": 1.1,
        "peak_pos": 0.42, "air_hp_hz": 4200.0, "air_level": 0.35, "peak": 0.82,
    }),
    "sword_hit.ogg": ("hit_flesh", {
        "duration": 0.14, "thump_start_hz": 190.0, "thump_end_hz": 42.0,
        "thump_drop_tau": 0.028, "thump_decay": 0.065, "body_cutoff_hz": 1400.0,
        "body_decay": 0.035, "body_level": 0.75, "crunch_hp_hz": 2800.0,
        "crunch_decay": 0.014, "crunch_level": 0.85, "drive": 2.8,
    }),
    "enemy_telegraph.ogg": ("glint", {"peak": 0.7}),
    "wolf_telegraph.ogg": ("glint", {"duration": 0.24, "peak": 0.72}),
    "wolf_attack.ogg": ("whoosh", {
        "duration": 0.18, "low_hz": 380.0, "high_hz": 2900.0, "q": 1.3,
        "peak_pos": 0.30, "air_hp_hz": 3400.0, "air_level": 0.55, "peak": 0.85,
    }),
    "combat_parry.ogg": ("hit_armor", {"duration": 0.9, "ring_hz": 1420.0, "ring_decay": 0.32, "ring_level": 1.0,
                                       "thud_level": 0.3}),
    "player_hurt_rain.ogg": ("hiss", {}),
    "rain_loop.ogg": ("rain", {}),
    "bleed_start.ogg": ("rumble", {}),
    "respite_rest.ogg": ("level_up", {"duration": 2.0, "root_hz": 392.0, "warm": True, "exhale": True,
                                      "note_decay": 0.7}),
    "player_dash.ogg": ("whoosh", {"duration": 0.16, "low_hz": 520.0, "high_hz": 3600.0, "q": 1.2,
                                   "peak_pos": 0.22, "air_hp_hz": 4200.0, "air_level": 0.65, "peak": 0.82}),
    "chronicle_open.ogg": ("arcane", {"duration": 0.65, "carrier_hz": 293.66, "fm_ratio": 2.0,
                                      "fm_index": 1.8, "sweep_low_hz": 1200.0, "sweep_high_hz": 4200.0,
                                      "sparkle_count": 5, "peak": 0.78}),
    "chronicler_mumble_neutral.ogg": ("mumble", {"duration": 0.72, "f0_hz": 135.0, "pitch_rise": 0.96,
                                                 "lp_hz": 360.0, "syllables": 4, "peak": 0.70}),
    "chronicler_mumble_happy.ogg": ("mumble", {"duration": 0.68, "f0_hz": 172.0, "pitch_rise": 1.18,
                                               "lp_hz": 450.0, "syllables": 5, "peak": 0.75}),
    "chronicler_mumble_disappointed.ogg": ("mumble", {"duration": 0.88, "f0_hz": 108.0, "pitch_rise": 0.84,
                                                      "lp_hz": 280.0, "syllables": 3, "peak": 0.45}),
    "player_block.ogg": ("hit_armor", {"duration": 0.35, "thud_level": 1.0, "ring_level": 0.35, "ring_decay": 0.08,
                                       "ring_hz": 620.0}),
    "flask_use.ogg": ("splash", {"duration": 0.7, "burst_level": 0.3, "slosh_level": 0.8, "bubble_count": 3,
                                 "tink": True, "tink_time": 0.42}),
    "page_pickup.ogg": ("rustle", {"peak": 0.7}),
    "weapon_swap.ogg": ("slash", {"duration": 0.36, "sweep_start_hz": 1800.0, "sweep_end_hz": 3800.0,
                                  "sweep_q": 3.0, "peak_pos": 0.6, "ring_level": 0.4, "ring_hz": 1900.0,
                                  "peak": 0.7}),
    "warp_trigger.ogg": ("warp", {}),
    "storm_intro.ogg": ("storm_intro", {}),
    "enemy_death.ogg": ("splash", {"duration": 0.75, "thump_level": 0.7, "bubble_count": 7, "burst_decay": 0.12}),
    "prop_break.ogg": ("explosion", {"duration": 0.6, "sub_level": 0.35, "rumble_level": 0.3, "crunch_level": 1.0,
                                     "debris_level": 0.8, "crunch_decay": 0.1}),
    "menu_navigate.ogg": ("ui_select", {"duration": 0.07, "tone_hz": 2600.0, "tone_level": 0.25,
                                        "click_level": 1.0, "click_decay": 0.004, "knock_level": 0.5,
                                        "peak": 0.5}),
    "menu_confirm.ogg": ("ui_select", {"duration": 0.3, "tone_hz": 880.0, "tone_level": 0.35, "stamp": True,
                                       "peak": 0.75}),
    "door_open.ogg": ("door_open", {"duration": 0.35, "peak": 0.68}),
    "slug_boss_slime.ogg": ("slug_boss_slime", {"duration": 0.55, "peak": 0.80}),
    "meadow_censor_whistle.ogg": ("meadow_censor_whistle", {"duration": 0.45, "peak": 0.78}),
    "frost_breath.ogg": ("frost_breath", {"duration": 0.60, "peak": 0.80}),
    "ice_crack.ogg": ("ice_crack", {"duration": 0.22, "peak": 0.82}),
    "ice_shatter.ogg": ("ice_shatter", {"duration": 0.45, "peak": 0.84}),
}

# Keyword heuristics for unknown missing references (first match wins)
PRESET_KEYWORDS: Tuple[Tuple[str, str], ...] = (
    ("step", "footstep"), ("swing", "slash"), ("slash", "slash"), ("dash", "whoosh"), ("whoosh", "whoosh"),
    ("parry", "hit_armor"), ("block", "hit_armor"), ("armor", "hit_armor"), ("telegraph", "glint"),
    ("rain", "hiss"), ("sizzle", "hiss"), ("rumble", "rumble"), ("quake", "rumble"), ("hit", "hit_flesh"),
    ("hurt", "hit_flesh"), ("explo", "explosion"), ("break", "explosion"), ("pickup", "pickup"),
    ("collect", "pickup"), ("level", "level_up"), ("rest", "level_up"), ("menu", "ui_select"),
    ("ui_", "ui_select"), ("click", "ui_select"), ("warp", "warp"), ("portal", "warp"), ("roar", "boss_roar"),
    ("boss", "boss_roar"), ("arcane", "arcane"), ("spell", "arcane"), ("magic", "arcane"), ("splash", "splash"),
    ("death", "splash"), ("flask", "splash"), ("page", "rustle"), ("paper", "rustle"),
)
FALLBACK_PRESET = "ui_select"

# ==============================================================================
# RENDERING, ENCODING & VERIFICATION
# ==============================================================================


def render_preset(preset: str, seed: int = DEFAULT_SEED, overrides: Optional[Dict] = None):
    """Render a finalized, peak-normalized signal for a preset with optional parameter overrides."""
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset '{preset}'. Available: {', '.join(sorted(PRESETS))}")
    fn, defaults, _ = PRESETS[preset]
    overrides = dict(overrides or {})
    unknown = set(overrides) - set(defaults) - {"peak"}
    if unknown:
        raise ValueError(f"Unknown parameter(s) for preset '{preset}': {', '.join(sorted(unknown))}")
    params = dict(defaults)
    params.update(overrides)
    raw = fn(random.Random(seed), params)
    return finalize(raw, params.get("peak", PEAK_TARGET), params.get("loopable", False))


def to_pcm16_bytes(signal) -> bytes:
    """Convert a [-1, 1] float signal into little-endian 16-bit PCM bytes."""
    if np is not None:
        return (np.clip(np.asarray(signal), -1.0, 1.0) * PCM_MAX).round().astype("<i2").tobytes()
    ints = [int(round(min(1.0, max(-1.0, v)) * PCM_MAX)) for v in signal]
    return struct.pack(f"<{len(ints)}h", *ints)


def write_wav(signal, path: str) -> None:
    """Write a mono 16-bit PCM WAV file."""
    with wave.open(path, "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH_BYTES)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(to_pcm16_bytes(signal))


def available_encoder() -> Optional[str]:
    """Return the Ogg Vorbis encoder backend that will be used, or None."""
    if _soundfile is not None:
        return "soundfile"
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    return None


def export_ogg(signal, path: str, quality: int = OGG_QUALITY) -> str:
    """Encode a signal to Ogg Vorbis at path; returns the encoder backend name."""
    encoder = available_encoder()
    if encoder is None:
        raise RuntimeError("No Ogg Vorbis encoder found. Install ffmpeg (with libvorbis) or `pip install soundfile`.")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if encoder == "soundfile":
        data = np.asarray(signal) if np is not None else list(signal)
        _soundfile.write(path, data, SAMPLE_RATE, format="OGG", subtype="VORBIS")
        return encoder
    with tempfile.TemporaryDirectory() as tmp_dir:
        wav_path = os.path.join(tmp_dir, "render.wav")
        write_wav(signal, wav_path)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", wav_path, "-map_metadata", "-1",
            "-c:a", "libvorbis", "-q:a", str(quality), "-ar", str(SAMPLE_RATE), "-ac", str(CHANNELS), path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    return encoder


def _decode_ogg_pcm16(path: str) -> Optional[bytes]:
    """Decode an .ogg file to raw 16-bit mono PCM bytes for content comparison."""
    if _soundfile is not None:
        try:
            pcm, _ = _soundfile.read(path, dtype="int16", always_2d=False)
            return pcm.tobytes()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"[SFX] Warning: soundfile decode failed for {path}: {exc}", file=sys.stderr)
    if shutil.which("ffmpeg"):
        try:
            res = subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path,
                    "-f", "s16le", "-ac", str(CHANNELS), "-ar", str(SAMPLE_RATE), "-",
                ],
                check=True,
                capture_output=True,
            )
            return res.stdout
        except subprocess.SubprocessError as exc:
            print(f"[SFX] Warning: ffmpeg decode failed for {path}: {exc}", file=sys.stderr)
    return None


def export_ogg_if_changed(signal, path: str, quality: int = OGG_QUALITY) -> Tuple[str, bool]:
    """Encode signal to .ogg and overwrite path only when PCM waveform differs. Returns (encoder, written)."""
    if not os.path.exists(path):
        return export_ogg(signal, path, quality=quality), True

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_ogg = os.path.join(tmp_dir, "candidate.ogg")
        encoder = export_ogg(signal, tmp_ogg, quality=quality)
        with open(path, "rb") as f_old, open(tmp_ogg, "rb") as f_new:
            if f_old.read() == f_new.read():
                return encoder, False
        old_pcm = _decode_ogg_pcm16(path)
        new_pcm = _decode_ogg_pcm16(tmp_ogg)
        if old_pcm is not None and new_pcm is not None and old_pcm == new_pcm:
            return encoder, False
        shutil.move(tmp_ogg, path)
        return encoder, True


def _ensure_mixer() -> None:
    """Initialize pygame.mixer at the engine sample rate, falling back to a dummy driver when headless."""
    import pygame
    if pygame.mixer.get_init():
        return
    try:
        pygame.mixer.init(frequency=SAMPLE_RATE)
    except pygame.error:
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        pygame.mixer.init(frequency=SAMPLE_RATE)


def verify_ogg(path: str) -> float:
    """Load an .ogg through pygame.mixer.Sound exactly like AudioManager does; returns its length (seconds)."""
    import pygame
    _ensure_mixer()
    sound = pygame.mixer.Sound(path)
    length = float(sound.get_length())
    if length <= 0.0:
        raise RuntimeError(f"{path} decoded to an empty sound")
    return length


# ==============================================================================
# PROJECT SCANNING (missing SFX references)
# ==============================================================================


def find_sound_references(project_root: str = ".") -> Dict[str, List[str]]:
    """Scan engine/UI source for quoted '*.ogg' references -> {file_name: ['path:line', ...]}."""
    candidates = [os.path.join(project_root, f) for f in SCAN_FILES]
    for scan_dir in SCAN_DIRS:
        for root, dirs, files in os.walk(os.path.join(project_root, scan_dir)):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            candidates += [os.path.join(root, f) for f in files if f.endswith(".py")]
    refs: Dict[str, List[str]] = {}
    for path in sorted(candidates):
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, project_root)
        with open(path, "r", encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                for match in SFX_REF_PATTERN.findall(line):
                    refs.setdefault(match, []).append(f"{rel}:{lineno}")
    return refs


def find_missing_sfx(project_root: str = ".", sfx_dir: str = DEFAULT_OUTPUT_DIR, music_dir: str = MUSIC_DIR,
                     include_manifest: bool = True) -> Dict[str, List[str]]:
    """Return referenced (and manifest) SFX that exist in neither the SFX nor the music directory."""
    refs = find_sound_references(project_root)
    if include_manifest:
        for name in SOUND_RECIPES:
            refs.setdefault(name, []).append(MANIFEST_SOURCE)

    def exists(name: str) -> bool:
        return any(os.path.exists(os.path.join(project_root, d, name)) for d in (sfx_dir, music_dir))

    return {name: sources for name, sources in sorted(refs.items()) if not exists(name)}


def guess_preset(name: str) -> str:
    """Pick a preset for an unknown sound name via keyword heuristics."""
    lowered = name.lower()
    for keyword, preset in PRESET_KEYWORDS:
        if keyword in lowered:
            return preset
    return FALLBACK_PRESET


def resolve_recipe(name: str) -> Tuple[str, Dict]:
    """Return (preset, overrides) for a game SFX name, using the manifest or keyword heuristics."""
    file_name = output_name(name)
    if file_name in SOUND_RECIPES:
        preset, overrides = SOUND_RECIPES[file_name]
        return preset, dict(overrides)
    return guess_preset(file_name), {}


def output_name(name: str) -> str:
    """Normalize a sound name to its '.ogg' file name."""
    base = os.path.basename(name)
    return base if base.endswith(".ogg") else f"{base}.ogg"


def sound_seed(name: str, base_seed: int = DEFAULT_SEED) -> int:
    """Stable per-sound seed so each SFX differs while remaining reproducible."""
    return (base_seed + zlib.crc32(output_name(name).encode("utf-8"))) & 0x7FFFFFFF


# ==============================================================================
# GENERATION PIPELINES
# ==============================================================================


def generate_sound(name: str, preset: str, overrides: Optional[Dict], seed: int, output_dir: str,
                   verify: bool = True, force: bool = False) -> Optional[str]:
    """Render, encode and (optionally) verify one SFX file. Returns the path, or None if skipped."""
    path = os.path.join(output_dir, output_name(name))
    if os.path.exists(path) and not force:
        print(f"[SFX] Skipping existing {path} (use --force to overwrite)")
        return None
    signal = render_preset(preset, seed, overrides)
    encoder, written = export_ogg_if_changed(signal, path)
    if not written:
        print(f"[SFX] Unchanged {path} (PCM identical, skipped write)")
        return None
    length = verify_ogg(path) if verify else len(signal) / SAMPLE_RATE
    status = "verified" if verify else "unverified"
    print(f"[SFX] Wrote {path} (preset={preset}, seed={seed}, {length:.2f}s, {encoder}, {status})")
    return path


def generate_variants(name: str, preset: str, overrides: Optional[Dict], base_seed: int, variants: int,
                      output_dir: str, verify: bool = True) -> List[str]:
    """Render seeded variants `<stem>_vNN.ogg` (seed = base_seed + i) for auditioning."""
    stem = output_name(name)[:-len(".ogg")]
    paths = []
    for idx in range(variants):
        seed = base_seed + idx
        path = generate_sound(f"{stem}_v{idx + 1:02d}", preset, overrides, seed, output_dir, verify, force=True)
        if path:
            paths.append(path)
    print(f"[SFX] Promote a favourite with: python generate_sfx.py --name {stem} --seed <SEED> --force")
    return paths


def fill_missing(base_seed: int = DEFAULT_SEED, output_dir: str = DEFAULT_OUTPUT_DIR, verify: bool = True,
                 force: bool = False, project_root: str = ".") -> List[str]:
    """Generate every missing referenced/manifest SFX (or regenerate all recipes with force)."""
    names = set(find_missing_sfx(project_root, sfx_dir=output_dir))
    if force:
        names |= set(SOUND_RECIPES)
    if not names:
        print("[SFX] No missing sound effects. Everything referenced is present.")
        return []
    written = []
    for name in sorted(names):
        preset, overrides = resolve_recipe(name)
        path = generate_sound(name, preset, overrides, sound_seed(name, base_seed), output_dir, verify, force)
        if path:
            written.append(path)
    print(f"[SFX] Generated {len(written)} sound effect(s) in {output_dir}")
    return written


# ==============================================================================
# PROCEDURAL BOSS MUSIC SYNTHESIS (44.1 kHz mono, seamlessly loopable)
# ==============================================================================


def _midi_to_hz(midi_note: float) -> float:
    """Convert a MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((float(midi_note) - 69.0) / 12.0))


def _ring_add(buf, sig, start_idx: int, gain: float = 1.0) -> None:
    """Accumulate sig * gain into circular buffer buf starting at start_idx (modulo len(buf))."""
    total = len(buf)
    if total <= 0 or len(sig) == 0:
        return
    start = start_idx % total
    seg_len = len(sig)
    if np is not None:
        arr = np.asarray(sig, dtype=np.float64) * gain
        end = start + seg_len
        if end <= total:
            buf[start:end] += arr
        else:
            first = total - start
            buf[start:total] += arr[:first]
            rem = seg_len - first
            pos = first
            while rem > 0:
                chunk = min(total, rem)
                buf[0:chunk] += arr[pos:pos + chunk]
                pos += chunk
                rem -= chunk
        return
    for i, val in enumerate(sig):
        buf[(start + i) % total] += val * gain


def _synth_pulse_note(
    n: int,
    freq_hz: float,
    duty: float = 0.25,
    vibrato_hz: float = 0.0,
    vibrato_depth: float = 0.0,
    release_s: float = 0.015,
):
    """Synthesize a crisp NES-style variable-duty pulse wave note (25% or 12.5% duty)."""
    if n <= 0:
        return silence(1)
    if np is not None:
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
        if vibrato_hz > 0.0 and vibrato_depth > 0.0:
            vib_onset = np.clip((t - 0.06) / 0.08, 0.0, 1.0)
            freq_arr = freq_hz * (1.0 + vibrato_depth * vib_onset * np.sin(TAU * vibrato_hz * t))
            cycles = np.cumsum(freq_arr) / SAMPLE_RATE
        else:
            cycles = freq_hz * t
        wave_sig = np.where((cycles % 1.0) < duty, 1.0, -1.0)
        atk = max(1, min(n // 4, int(0.003 * SAMPLE_RATE)))
        rel = max(1, min(n // 2, int(release_s * SAMPLE_RATE)))
        env = np.ones(n, dtype=np.float64)
        env[:atk] = np.linspace(0.0, 1.0, atk, endpoint=False)
        env[n - rel:] *= np.linspace(1.0, 0.0, rel)
        return wave_sig * env
    out = []
    phase = 0.0
    atk = max(1, min(n // 4, int(0.003 * SAMPLE_RATE)))
    rel = max(1, min(n // 2, int(release_s * SAMPLE_RATE)))
    for i in range(n):
        f_cur = freq_hz
        if vibrato_hz > 0.0 and vibrato_depth > 0.0:
            t_cur = i / SAMPLE_RATE
            onset = min(1.0, max(0.0, (t_cur - 0.06) / 0.08))
            f_cur = freq_hz * (1.0 + vibrato_depth * onset * math.sin(TAU * vibrato_hz * t_cur))
        phase = (phase + f_cur / SAMPLE_RATE) % 1.0
        val = 1.0 if phase < duty else -1.0
        env = 1.0
        if i < atk:
            env = i / atk
        if i >= n - rel:
            env *= (n - 1 - i) / max(1, rel)
        out.append(val * env)
    return out


def _synth_nes_triangle_note(n: int, freq_hz: float):
    """Synthesize a bouncy 4-bit quantized NES triangle-wave bass note."""
    if n <= 0:
        return silence(1)
    if np is not None:
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
        frac = (freq_hz * t) % 1.0
        tri = 4.0 * np.abs(frac - 0.5) - 1.0
        # Classic NES 16-level staircase quantization
        tri = np.round(tri * 7.5) / 7.5
        atk = max(1, min(n // 6, int(0.002 * SAMPLE_RATE)))
        rel = max(1, min(n // 3, int(0.012 * SAMPLE_RATE)))
        env = np.ones(n, dtype=np.float64)
        env[:atk] = np.linspace(0.0, 1.0, atk, endpoint=False)
        env[n - rel:] *= np.linspace(1.0, 0.0, rel)
        return tri * env
    out = []
    atk = max(1, min(n // 6, int(0.002 * SAMPLE_RATE)))
    rel = max(1, min(n // 3, int(0.012 * SAMPLE_RATE)))
    for i in range(n):
        frac = (freq_hz * i / SAMPLE_RATE) % 1.0
        tri = round((4.0 * abs(frac - 0.5) - 1.0) * 7.5) / 7.5
        env = 1.0
        if i < atk:
            env = i / atk
        if i >= n - rel:
            env *= (n - 1 - i) / max(1, rel)
        out.append(tri * env)
    return out


def _synth_crunchy_saw_note(n: int, freq_hz: float, accent: float = 1.0):
    """Synthesize a thick detuned dual-sawtooth + power-fifth boss riff note."""
    if n <= 0:
        return silence(1)
    if np is not None:
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
        saw1 = 2.0 * ((freq_hz * t) % 1.0) - 1.0
        saw2 = 2.0 * (((freq_hz * 1.007) * t + 0.17) % 1.0) - 1.0
        fifth = 2.0 * (((freq_hz * 1.498) * t + 0.31) % 1.0) - 1.0
        raw = 0.52 * saw1 + 0.36 * saw2 + 0.28 * fifth
        atk = max(1, min(n // 5, int(0.004 * SAMPLE_RATE)))
        rel = max(1, min(n // 3, int(0.018 * SAMPLE_RATE)))
        decay = np.exp(-t / max(0.08, (n / SAMPLE_RATE) * 0.95))
        env = (0.45 + 0.55 * decay) * accent
        env[:atk] *= np.linspace(0.0, 1.0, atk, endpoint=False)
        env[n - rel:] *= np.linspace(1.0, 0.0, rel)
        return raw * env
    out = []
    atk = max(1, min(n // 5, int(0.004 * SAMPLE_RATE)))
    rel = max(1, min(n // 3, int(0.018 * SAMPLE_RATE)))
    dur = max(0.08, (n / SAMPLE_RATE) * 0.95)
    for i in range(n):
        t_cur = i / SAMPLE_RATE
        saw1 = 2.0 * ((freq_hz * t_cur) % 1.0) - 1.0
        saw2 = 2.0 * (((freq_hz * 1.007) * t_cur + 0.17) % 1.0) - 1.0
        fifth = 2.0 * (((freq_hz * 1.498) * t_cur + 0.31) % 1.0) - 1.0
        env = (0.45 + 0.55 * math.exp(-t_cur / dur)) * accent
        if i < atk:
            env *= i / atk
        if i >= n - rel:
            env *= (n - 1 - i) / max(1, rel)
        out.append((0.52 * saw1 + 0.36 * saw2 + 0.28 * fifth) * env)
    return out


def _synth_sub_note(n: int, freq_hz: float):
    """Synthesize a weighty low sine sub-bass note."""
    if n <= 0:
        return silence(1)
    if np is not None:
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
        sig = np.sin(TAU * freq_hz * t) + 0.22 * np.sin(TAU * freq_hz * 2.0 * t)
        atk = max(1, min(n // 5, int(0.006 * SAMPLE_RATE)))
        rel = max(1, min(n // 3, int(0.025 * SAMPLE_RATE)))
        env = np.ones(n, dtype=np.float64)
        env[:atk] = np.linspace(0.0, 1.0, atk, endpoint=False)
        env[n - rel:] *= np.linspace(1.0, 0.0, rel)
        return sig * env
    out = []
    atk = max(1, min(n // 5, int(0.006 * SAMPLE_RATE)))
    rel = max(1, min(n // 3, int(0.025 * SAMPLE_RATE)))
    for i in range(n):
        t_cur = i / SAMPLE_RATE
        sig = math.sin(TAU * freq_hz * t_cur) + 0.22 * math.sin(TAU * freq_hz * 2.0 * t_cur)
        env = 1.0
        if i < atk:
            env = i / atk
        if i >= n - rel:
            env *= (n - 1 - i) / max(1, rel)
        out.append(sig * env)
    return out


def _synth_music_kick(n: int, f0: float, f1: float, tau: float, drive: float = 2.0):
    """Synthesize a punchy pitch-dropping kick drum."""
    if np is not None:
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
        freq_arr = f1 + (f0 - f1) * np.exp(-t / max(0.005, tau))
        phase = TAU * np.cumsum(freq_arr) / SAMPLE_RATE
        body = np.sin(phase) * np.exp(-t / max(0.02, tau * 2.2))
        return soft_clip(body, drive)
    freq_arr = pitch_drop(n, f0, f1, tau)
    body = multiply(oscillator(freq_arr, "sine"), exp_decay(n, max(0.02, tau * 2.2), attack=0.001))
    return soft_clip(body, drive)


def _synth_music_noise_hit(
    n: int,
    rng: random.Random,
    hp_hz: float,
    lp_hz: float,
    tau: float,
    bits: int = 4,
    hold: int = 3,
):
    """Synthesize a crisp stepped/bit-crushed noise snare or hi-hat hit."""
    raw = white_noise(n, rng)
    crushed = bitcrush(raw, bits=bits, hold=hold)
    filtered = biquad(biquad(crushed, "highpass", hp_hz), "lowpass", lp_hz)
    return multiply(filtered, exp_decay(n, tau, attack=0.001))


def generate_slug_boss_phase1_music(seed: int = DEFAULT_SEED):
    """Synthesize ~15.0s loopable 112 BPM crunchy bit-crushed sawtooth + sub-bass Phase 1 SlugBoss theme."""
    rng = random.Random(seed ^ 0x5106B055)
    bpm = 112.0
    step_s = 60.0 / bpm / 4.0  # 16th-note duration (~0.13393s)
    total_steps = 112  # 4 bars of 7/4 (28 beats) -> 15.000s exact seamless loop
    total_samples = n_samples(total_steps * step_s)

    riff_buf = silence(total_samples)
    sub_buf = silence(total_samples)
    drum_buf = silence(total_samples)
    acid_buf = silence(total_samples)

    # Heavy D Phrygian sludge-boss riff: (step_offset, midi_note, len_steps, accent)
    bar_riffs = (
        (
            (0, 38, 3, 1.15), (3, 38, 1, 0.90), (4, 41, 2, 1.05), (6, 39, 2, 1.00),
            (8, 38, 3, 1.15), (12, 38, 2, 0.95), (14, 34, 2, 1.00), (16, 36, 2, 1.00),
            (18, 38, 2, 1.10), (20, 43, 2, 1.15), (22, 41, 2, 1.05), (24, 39, 2, 1.00),
            (26, 38, 2, 0.95),
        ),
        (
            (0, 38, 3, 1.15), (3, 38, 1, 0.90), (4, 44, 2, 1.20), (6, 43, 2, 1.05),
            (8, 41, 2, 1.00), (10, 39, 2, 1.00), (12, 38, 3, 1.15), (16, 41, 2, 1.05),
            (18, 43, 2, 1.10), (20, 39, 2, 1.05), (22, 38, 2, 1.00), (24, 36, 2, 0.95),
            (26, 34, 2, 1.00),
        ),
        (
            (0, 38, 2, 1.15), (2, 41, 2, 1.05), (4, 43, 2, 1.10), (6, 44, 2, 1.20),
            (8, 43, 2, 1.05), (10, 41, 2, 1.00), (12, 39, 2, 1.05), (14, 38, 2, 1.00),
            (16, 46, 3, 1.20), (19, 45, 1, 1.00), (20, 43, 2, 1.10), (22, 41, 2, 1.05),
            (24, 39, 2, 1.00), (26, 38, 2, 1.00),
        ),
        (
            (0, 38, 2, 1.15), (2, 38, 2, 1.00), (4, 39, 2, 1.05), (6, 41, 2, 1.10),
            (8, 43, 2, 1.15), (10, 44, 2, 1.20), (12, 43, 2, 1.10), (14, 41, 2, 1.05),
            (16, 39, 2, 1.05), (18, 38, 2, 1.00), (20, 36, 2, 1.00), (22, 34, 2, 1.05),
            (24, 33, 2, 1.10), (26, 39, 2, 1.20),
        ),
    )

    kick_sig = _synth_music_kick(n_samples(0.18), 135.0, 42.0, 0.042, drive=2.6)
    snare_noise = _synth_music_noise_hit(n_samples(0.17), rng, 550.0, 3400.0, 0.055, bits=4, hold=4)
    snare_body = _synth_music_kick(n_samples(0.11), 210.0, 125.0, 0.025, drive=1.8)
    snare_sig = mix((snare_noise, 0.85), (snare_body, 0.55))
    hat_closed = _synth_music_noise_hit(n_samples(0.045), rng, 3400.0, 9500.0, 0.015, bits=4, hold=2)
    hat_open = _synth_music_noise_hit(n_samples(0.12), rng, 3000.0, 9000.0, 0.048, bits=4, hold=3)

    for bar_idx, events in enumerate(bar_riffs):
        bar_step = bar_idx * 28
        for step_off, midi_note, dur_steps, accent in events:
            pos = offset_samples((bar_step + step_off) * step_s)
            dur_n = n_samples(dur_steps * step_s * 0.92)
            hz = _midi_to_hz(midi_note)
            _ring_add(riff_buf, _synth_crunchy_saw_note(dur_n, hz, accent=accent), pos, 0.85)
            _ring_add(sub_buf, _synth_sub_note(n_samples(dur_steps * step_s * 0.96), hz * 0.5), pos, 0.72 * accent)

        # Acidic slime-squelch accent on each bar downbeat
        downbeat_pos = offset_samples(bar_step * step_s)
        stab_n = n_samples(step_s * 5.0)
        stab_hz = _midi_to_hz(50 if bar_idx % 2 == 0 else 51)
        _ring_add(acid_buf, _synth_crunchy_saw_note(stab_n, stab_hz, accent=0.85), downbeat_pos, 0.45)

        # Gritty lo-fi percussion pattern over 28 sixteenth steps
        for s_i in range(28):
            pos = offset_samples((bar_step + s_i) * step_s)
            if s_i in (0, 6, 8, 14, 16, 22):
                _ring_add(drum_buf, kick_sig, pos, 0.95)
            if s_i in (4, 12, 20, 26) or (bar_idx == 3 and s_i in (24, 25, 27)):
                _ring_add(drum_buf, snare_sig, pos, 0.78 if s_i not in (25, 27) else 0.58)
            if s_i % 2 == 0:
                hat = hat_open if s_i in (10, 26) else hat_closed
                _ring_add(drum_buf, hat, pos, 0.34 if s_i % 4 == 0 else 0.22)

    # Crunchy bit-crushed distortion chain on the sawtooth riff bus
    crunchy_riff = biquad(bitcrush(soft_clip(riff_buf, 4.2), bits=5, hold=3), "lowpass", 1950.0, q=1.5)
    clean_sub = biquad(sub_buf, "lowpass", 145.0, order=2)
    acid_layer = biquad(soft_clip(acid_buf, 2.8), "bandpass", 920.0, q=2.2)
    gritty_drums = soft_clip(bitcrush(drum_buf, bits=6, hold=2), 1.7)

    combined = mix(
        (crunchy_riff, 0.62),
        (clean_sub, 0.55),
        (gritty_drums, 0.72),
        (acid_layer, 0.24),
    )
    return finalize(combined[:total_samples], peak_target=PEAK_TARGET, loopable=True)


def generate_slug_boss_phase2_music(seed: int = DEFAULT_SEED):
    """Synthesize ~15.8s loopable 152 BPM Mega Man / NES chiptune breakout Phase 2 SlugBoss theme."""
    rng = random.Random(seed ^ 0xAE6A8A02)
    bpm = 152.0
    step_s = 60.0 / bpm / 4.0  # 16th-note duration (~0.09868s)
    total_bars = 10  # 8-bar A+B heroic chorus + 2-bar high-energy boss turnaround -> 15.789s exact loop
    total_steps = total_bars * 16
    total_samples = n_samples(total_steps * step_s)

    lead_buf = silence(total_samples)
    arp_buf = silence(total_samples)
    bass_buf = silence(total_samples)
    drum_buf = silence(total_samples)

    # 10-bar E minor harmonic progression for rapid 16th-note NES arpeggios & triangle bass roots
    chords = (
        ((64, 67, 71, 76), 40),  # Bar 0: Em
        ((64, 67, 71, 76), 40),  # Bar 1: Em
        ((60, 64, 67, 72), 36),  # Bar 2: C
        ((62, 66, 69, 74), 38),  # Bar 3: D
        ((64, 67, 71, 76), 40),  # Bar 4: Em (B-section lift)
        ((67, 71, 74, 79), 43),  # Bar 5: G
        ((60, 64, 67, 72), 36),  # Bar 6: C
        ((59, 63, 66, 71), 35),  # Bar 7: B7
        ((57, 60, 64, 69), 33),  # Bar 8: Am turnaround
        ((59, 63, 66, 71), 35),  # Bar 9: B7 climax fill
    )

    # Driving Mega Man / NES pulse-wave lead melody per bar: (step_off, midi_note, dur_steps, duty)
    lead_bars = (
        ((0, 76, 2, 0.25), (2, 79, 2, 0.25), (4, 83, 2, 0.25), (6, 81, 2, 0.25),
         (8, 79, 2, 0.25), (10, 78, 2, 0.25), (12, 76, 4, 0.25)),
        ((0, 76, 2, 0.25), (2, 79, 2, 0.25), (4, 83, 2, 0.25), (6, 86, 2, 0.25),
         (8, 84, 2, 0.25), (10, 83, 2, 0.25), (12, 81, 4, 0.25)),
        ((0, 84, 2, 0.25), (2, 83, 2, 0.25), (4, 81, 2, 0.25), (6, 79, 2, 0.25),
         (8, 76, 2, 0.25), (10, 79, 2, 0.25), (12, 84, 4, 0.25)),
        ((0, 86, 2, 0.25), (2, 84, 2, 0.25), (4, 83, 2, 0.25), (6, 81, 2, 0.25),
         (8, 78, 2, 0.25), (10, 81, 2, 0.25), (12, 83, 4, 0.25)),
        # Bars 4..7: High-energy 12.5% nasal pulse breakout
        ((0, 88, 3, 0.125), (3, 86, 1, 0.125), (4, 83, 2, 0.125), (6, 84, 2, 0.125),
         (8, 83, 2, 0.125), (10, 79, 2, 0.125), (12, 83, 4, 0.125)),
        ((0, 86, 3, 0.125), (3, 84, 1, 0.125), (4, 83, 2, 0.125), (6, 81, 2, 0.125),
         (8, 79, 2, 0.125), (10, 83, 2, 0.125), (12, 86, 4, 0.125)),
        ((0, 84, 2, 0.125), (2, 88, 2, 0.125), (4, 86, 2, 0.125), (6, 84, 2, 0.125),
         (8, 83, 2, 0.125), (10, 81, 2, 0.125), (12, 79, 4, 0.125)),
        ((0, 83, 2, 0.125), (2, 81, 2, 0.125), (4, 79, 2, 0.125), (6, 78, 2, 0.125),
         (8, 75, 2, 0.125), (10, 78, 2, 0.125), (12, 83, 4, 0.125)),
        # Bars 8..9: Rapid 16th-note Mega Man turnaround run
        ((0, 81, 1, 0.25), (1, 83, 1, 0.25), (2, 84, 2, 0.25), (4, 88, 2, 0.25),
         (6, 86, 2, 0.25), (8, 84, 2, 0.25), (10, 83, 2, 0.25), (12, 81, 2, 0.25), (14, 79, 2, 0.25)),
        ((0, 78, 1, 0.125), (1, 81, 1, 0.125), (2, 83, 2, 0.125), (4, 87, 2, 0.125),
         (6, 83, 2, 0.125), (8, 81, 1, 0.125), (9, 83, 1, 0.125), (10, 86, 2, 0.125),
         (12, 87, 2, 0.125), (14, 88, 2, 0.125)),
    )

    nes_kick = _synth_music_kick(n_samples(0.11), 190.0, 52.0, 0.024, drive=1.5)
    nes_snare = _synth_music_noise_hit(n_samples(0.11), rng, 950.0, 6200.0, 0.036, bits=3, hold=3)
    nes_hat = _synth_music_noise_hit(n_samples(0.032), rng, 5200.0, 12000.0, 0.011, bits=3, hold=2)
    nes_tom = _synth_music_kick(n_samples(0.09), 260.0, 120.0, 0.026, drive=1.3)

    for bar_idx in range(total_bars):
        bar_step = bar_idx * 16
        chord_notes, bass_root = chords[bar_idx]

        # Ch 1: Pulse-wave lead melody
        for step_off, midi_note, dur_steps, duty in lead_bars[bar_idx]:
            pos = offset_samples((bar_step + step_off) * step_s)
            dur_n = n_samples(dur_steps * step_s * 0.90)
            vib_d = 0.008 if dur_steps >= 3 else 0.0
            note = _synth_pulse_note(dur_n, _midi_to_hz(midi_note), duty=duty, vibrato_hz=6.5, vibrato_depth=vib_d)
            _ring_add(lead_buf, note, pos, 0.62)

        # Ch 2: Rapid 16th-note pulse arpeggios
        for s_i in range(16):
            pos = offset_samples((bar_step + s_i) * step_s)
            arp_midi = chord_notes[s_i % len(chord_notes)]
            arp_note = _synth_pulse_note(n_samples(step_s * 0.78), _midi_to_hz(arp_midi), duty=0.25, release_s=0.008)
            _ring_add(arp_buf, arp_note, pos, 0.30)

        # Ch 3: Bouncy octave-jumping NES triangle bassline
        bass_pattern = (0, 12, 0, 12, 7, 12, 0, 12, 0, 12, 5, 7, 12, 7, 5, 3)
        for s_i in range(0, 16, 2):
            pos = offset_samples((bar_step + s_i) * step_s)
            b_note = bass_root + bass_pattern[s_i]
            tri = _synth_nes_triangle_note(n_samples(step_s * 1.85), _midi_to_hz(b_note))
            _ring_add(bass_buf, tri, pos, 0.85)
        # Driving 16th-note bass pickup on final beat
        pickup_pos = offset_samples((bar_step + 15) * step_s)
        _ring_add(bass_buf, _synth_nes_triangle_note(n_samples(step_s * 0.9), _midi_to_hz(bass_root + 12)),
                  pickup_pos, 0.72)

        # Ch 4: Crisp NES noise-channel percussion
        for s_i in range(16):
            pos = offset_samples((bar_step + s_i) * step_s)
            if s_i in (0, 6, 8, 10):
                _ring_add(drum_buf, nes_kick, pos, 0.88)
            if s_i in (4, 12) or (bar_idx in (3, 7, 9) and s_i in (13, 14, 15)):
                _ring_add(drum_buf, nes_snare, pos, 0.68 if s_i in (4, 12) else 0.56)
            if bar_idx == 9 and s_i in (10, 11):
                _ring_add(drum_buf, nes_tom, pos, 0.65)
            _ring_add(drum_buf, nes_hat, pos, 0.28 if s_i % 2 == 0 else 0.16)

    # Gentle anti-aliasing lowpass on pulse channels for crisp NES fidelity without harshness
    lead_clean = biquad(lead_buf, "lowpass", 8800.0)
    arp_clean = biquad(arp_buf, "lowpass", 7200.0)
    bass_clean = biquad(bass_buf, "lowpass", 1800.0)

    combined = mix(
        (lead_clean, 0.62),
        (arp_clean, 0.40),
        (bass_clean, 0.68),
        (drum_buf, 0.58),
    )
    return finalize(combined[:total_samples], peak_target=PEAK_TARGET, loopable=True)


def _synth_plucked_lute_note(n: int, freq_hz: float, brightness: float = 0.55):
    """Synthesize a crisp plucked lute/harpsichord note with fast harmonic decay."""
    if n <= 0:
        return silence(1)
    if np is not None:
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
        p1 = np.sin(TAU * freq_hz * t) * np.exp(-t / 0.32)
        p2 = np.sin(TAU * freq_hz * 2.0 * t + 0.4) * np.exp(-t / 0.16)
        p3 = np.sin(TAU * freq_hz * 3.0 * t + 0.9) * np.exp(-t / 0.085)
        p4 = np.sin(TAU * freq_hz * 4.0 * t + 1.3) * np.exp(-t / 0.045)
        raw = 0.55 * p1 + brightness * (0.34 * p2 + 0.22 * p3 + 0.14 * p4)
        atk = max(1, min(n // 8, int(0.0025 * SAMPLE_RATE)))
        rel = max(1, min(n // 4, int(0.015 * SAMPLE_RATE)))
        raw[:atk] *= np.linspace(0.0, 1.0, atk, endpoint=False)
        raw[n - rel:] *= np.linspace(1.0, 0.0, rel)
        return raw
    out = []
    atk = max(1, min(n // 8, int(0.0025 * SAMPLE_RATE)))
    rel = max(1, min(n // 4, int(0.015 * SAMPLE_RATE)))
    for i in range(n):
        t_cur = i / SAMPLE_RATE
        val = (
            0.55 * math.sin(TAU * freq_hz * t_cur) * math.exp(-t_cur / 0.32)
            + brightness * 0.34 * math.sin(TAU * freq_hz * 2.0 * t_cur + 0.4) * math.exp(-t_cur / 0.16)
            + brightness * 0.22 * math.sin(TAU * freq_hz * 3.0 * t_cur + 0.9) * math.exp(-t_cur / 0.085)
        )
        if i < atk:
            val *= i / atk
        if i >= n - rel:
            val *= (n - 1 - i) / max(1, rel)
        out.append(val)
    return out


def _synth_bowed_bass_note(n: int, freq_hz: float):
    """Synthesize a dark bowed cello/sub-bass drone with slow swell and warm low harmonics."""
    if n <= 0:
        return silence(1)
    if np is not None:
        t = np.arange(n, dtype=np.float64) / SAMPLE_RATE
        saw = 2.0 * ((freq_hz * t) % 1.0) - 1.0
        sub = np.sin(TAU * freq_hz * t)
        raw = 0.65 * sub + 0.35 * saw
        atk = max(1, min(n // 3, int(0.055 * SAMPLE_RATE)))
        rel = max(1, min(n // 3, int(0.085 * SAMPLE_RATE)))
        env = np.ones(n, dtype=np.float64)
        env[:atk] = np.linspace(0.0, 1.0, atk, endpoint=False)
        env[n - rel:] *= np.linspace(1.0, 0.0, rel)
        return raw * env
    out = []
    atk = max(1, min(n // 3, int(0.055 * SAMPLE_RATE)))
    rel = max(1, min(n // 3, int(0.085 * SAMPLE_RATE)))
    for i in range(n):
        t_cur = i / SAMPLE_RATE
        raw = 0.65 * math.sin(TAU * freq_hz * t_cur) + 0.35 * (2.0 * ((freq_hz * t_cur) % 1.0) - 1.0)
        env = 1.0
        if i < atk:
            env = i / atk
        if i >= n - rel:
            env *= (n - 1 - i) / max(1, rel)
        out.append(raw * env)
    return out


def generate_pastoral_boss_phase1_music(seed: int = DEFAULT_SEED):
    """Synthesize ~15.0s loopable 120 BPM 3/4 folk-dirge waltz (plucked lute/harpsichord & bowed sub-bass)."""
    rng = random.Random(seed ^ 0xFA570AA1)
    bpm = 120.0
    eighth_s = 60.0 / bpm / 2.0  # 0.25s per eighth note -> 6 eighths per 3/4 bar = 1.50s/bar
    total_bars = 10  # 10 bars of 3/4 = 15.000s exact seamless loop
    total_samples = n_samples(total_bars * 6 * eighth_s)

    lute_buf = silence(total_samples)
    lead_buf = silence(total_samples)
    bass_buf = silence(total_samples)
    drum_buf = silence(total_samples)

    # Haunting A minor / harmonic-minor folk-dirge progression: (arpeggio_chord_midi, bass_root_midi)
    bars = (
        ((57, 60, 64, 69, 64, 60), 33),  # Bar 0: Am
        ((57, 60, 64, 69, 64, 60), 33),  # Bar 1: Am
        ((53, 57, 60, 65, 60, 57), 29),  # Bar 2: F
        ((50, 53, 57, 62, 57, 53), 38),  # Bar 3: Dm
        ((52, 56, 59, 64, 59, 56), 28),  # Bar 4: E7
        ((57, 60, 64, 69, 64, 60), 33),  # Bar 5: Am
        ((60, 64, 67, 72, 67, 64), 36),  # Bar 6: C
        ((50, 53, 57, 62, 57, 53), 38),  # Bar 7: Dm
        ((53, 57, 60, 65, 60, 57), 29),  # Bar 8: F
        ((52, 56, 59, 64, 62, 59), 28),  # Bar 9: E7 turnaround
    )

    # Mournful high harpsichord/reed dirge melody per 3/4 bar: (eighth_off, midi_note, dur_eighths)
    melody_bars = (
        ((0, 76, 3), (3, 72, 2), (5, 71, 1)),
        ((0, 69, 4), (4, 71, 1), (5, 72, 1)),
        ((0, 77, 3), (3, 76, 2), (5, 72, 1)),
        ((0, 74, 4), (4, 72, 1), (5, 71, 1)),
        ((0, 71, 3), (3, 76, 2), (5, 75, 1)),
        ((0, 76, 3), (3, 81, 2), (5, 79, 1)),
        ((0, 76, 3), (3, 72, 2), (5, 74, 1)),
        ((0, 77, 3), (3, 74, 2), (5, 72, 1)),
        ((0, 72, 3), (3, 71, 2), (5, 69, 1)),
        ((0, 68, 3), (3, 71, 2), (5, 76, 1)),
    )

    bodhran_low = _synth_music_kick(n_samples(0.18), 108.0, 48.0, 0.048, drive=1.5)
    brush_hit = _synth_music_noise_hit(n_samples(0.065), rng, 1800.0, 6800.0, 0.022, bits=5, hold=2)

    for bar_idx, (arp_notes, bass_root) in enumerate(bars):
        bar_eighth = bar_idx * 6
        bar_pos = offset_samples(bar_eighth * eighth_s)

        # Bowed cello / sub-bass drone holding across the 3/4 measure
        _ring_add(bass_buf, _synth_bowed_bass_note(n_samples(5.8 * eighth_s), _midi_to_hz(bass_root)), bar_pos, 0.78)
        _ring_add(
            bass_buf,
            _synth_bowed_bass_note(n_samples(3.6 * eighth_s), _midi_to_hz(bass_root + 12)),
            offset_samples((bar_eighth + 2) * eighth_s),
            0.34,
        )

        # Plucked lute/harpsichord 3/4 arpeggios (6 eighth notes per bar)
        for e_i, midi_note in enumerate(arp_notes):
            pos = offset_samples((bar_eighth + e_i) * eighth_s)
            accent = 0.72 if e_i == 0 else (0.54 if e_i in (2, 4) else 0.46)
            pluck = _synth_plucked_lute_note(n_samples(eighth_s * 1.6), _midi_to_hz(midi_note), brightness=0.62)
            _ring_add(lute_buf, pluck, pos, accent)

        # Mournful high reed/plucked waltz lead
        for e_off, m_note, dur_e in melody_bars[bar_idx]:
            pos = offset_samples((bar_eighth + e_off) * eighth_s)
            dur_n = n_samples(dur_e * eighth_s * 0.94)
            reed = _synth_pulse_note(dur_n, _midi_to_hz(m_note), duty=0.25, vibrato_hz=5.2, vibrato_depth=0.007)
            chime = _synth_plucked_lute_note(dur_n, _midi_to_hz(m_note), brightness=0.72)
            _ring_add(lead_buf, mix((reed, 0.42), (chime, 0.58)), pos, 0.60)

        # 3/4 frame-drum waltz pulse (ONE - two - three)
        _ring_add(drum_buf, bodhran_low, bar_pos, 0.76)
        _ring_add(drum_buf, brush_hit, offset_samples((bar_eighth + 2) * eighth_s), 0.32)
        _ring_add(drum_buf, brush_hit, offset_samples((bar_eighth + 4) * eighth_s), 0.28)
        if bar_idx in (4, 9):
            _ring_add(drum_buf, bodhran_low, offset_samples((bar_eighth + 5) * eighth_s), 0.52)

    bass_warm = biquad(bass_buf, "lowpass", 240.0, order=2)
    lute_clean = biquad(lute_buf, "lowpass", 5200.0)
    lead_clean = biquad(lead_buf, "lowpass", 4200.0)

    combined = mix(
        (lute_clean, 0.64),
        (lead_clean, 0.56),
        (bass_warm, 0.62),
        (drum_buf, 0.46),
    )
    return finalize(combined[:total_samples], peak_target=PEAK_TARGET, loopable=True)


def generate_pastoral_boss_phase2_music(seed: int = DEFAULT_SEED):
    """Synthesize ~15.5s loopable 155 BPM frantic 16th-note tarantella / chiptune wolf-hunt Phase 2 theme."""
    rng = random.Random(seed ^ 0xFA570AA2)
    bpm = 155.0
    step_s = 60.0 / bpm / 4.0  # 16th-note duration (~0.09677s)
    total_bars = 10  # 160 16th-note steps -> 15.484s exact seamless loop
    total_samples = n_samples(total_bars * 16 * step_s)

    lead_buf = silence(total_samples)
    arp_buf = silence(total_samples)
    bass_buf = silence(total_samples)
    drum_buf = silence(total_samples)

    # Frantic A harmonic-minor tarantella chord sequence: (4-note chord, triangle bass root)
    chords = (
        ((69, 72, 76, 81), 45),  # Bar 0: Am
        ((68, 71, 76, 80), 40),  # Bar 1: E7
        ((69, 72, 76, 81), 45),  # Bar 2: Am
        ((62, 65, 69, 74), 38),  # Bar 3: Dm
        ((69, 72, 76, 81), 45),  # Bar 4: Am (wolf-hunt breakout)
        ((65, 69, 72, 77), 41),  # Bar 5: F
        ((68, 71, 74, 76), 40),  # Bar 6: E7
        ((68, 71, 76, 80), 40),  # Bar 7: E7
        ((62, 65, 69, 74), 38),  # Bar 8: Dm
        ((68, 71, 74, 80), 40),  # Bar 9: E7 diminished climb
    )

    # Blistering 16th-note tarantella lead motifs (step_off, midi_note, dur_steps, duty)
    lead_bars = (
        ((0, 81, 1, 0.25), (1, 83, 1, 0.25), (2, 84, 2, 0.25), (4, 83, 1, 0.25), (5, 81, 1, 0.25),
         (6, 80, 2, 0.25), (8, 81, 2, 0.25), (10, 76, 2, 0.25), (12, 81, 2, 0.25), (14, 84, 2, 0.25)),
        ((0, 83, 1, 0.25), (1, 84, 1, 0.25), (2, 83, 2, 0.25), (4, 81, 1, 0.25), (5, 80, 1, 0.25),
         (6, 76, 2, 0.25), (8, 80, 2, 0.25), (10, 83, 2, 0.25), (12, 86, 2, 0.25), (14, 83, 2, 0.25)),
        ((0, 84, 1, 0.25), (1, 86, 1, 0.25), (2, 88, 2, 0.25), (4, 86, 1, 0.25), (5, 84, 1, 0.25),
         (6, 83, 2, 0.25), (8, 81, 2, 0.25), (10, 84, 2, 0.25), (12, 81, 4, 0.25)),
        ((0, 86, 1, 0.25), (1, 88, 1, 0.25), (2, 89, 2, 0.25), (4, 88, 1, 0.25), (5, 86, 1, 0.25),
         (6, 84, 2, 0.25), (8, 86, 2, 0.25), (10, 81, 2, 0.25), (12, 83, 4, 0.25)),
        # Bars 4..7: 12.5% nasal chiptune wolf-chase climax
        ((0, 88, 1, 0.125), (1, 89, 1, 0.125), (2, 88, 1, 0.125), (3, 86, 1, 0.125), (4, 84, 2, 0.125),
         (6, 81, 2, 0.125), (8, 84, 1, 0.125), (9, 86, 1, 0.125), (10, 88, 2, 0.125), (12, 89, 2, 0.125),
         (14, 88, 2, 0.125)),
        ((0, 89, 1, 0.125), (1, 91, 1, 0.125), (2, 89, 1, 0.125), (3, 88, 1, 0.125), (4, 86, 2, 0.125),
         (6, 84, 2, 0.125), (8, 81, 2, 0.125), (10, 84, 2, 0.125), (12, 86, 4, 0.125)),
        ((0, 88, 1, 0.125), (1, 86, 1, 0.125), (2, 84, 1, 0.125), (3, 83, 1, 0.125), (4, 80, 2, 0.125),
         (6, 83, 2, 0.125), (8, 86, 2, 0.125), (10, 84, 2, 0.125), (12, 83, 4, 0.125)),
        ((0, 80, 1, 0.125), (1, 83, 1, 0.125), (2, 86, 1, 0.125), (3, 88, 1, 0.125), (4, 89, 2, 0.125),
         (6, 88, 2, 0.125), (8, 86, 2, 0.125), (10, 83, 2, 0.125), (12, 80, 4, 0.125)),
        # Bars 8..9: Rapid tarantella spiral back into bar 0
        ((0, 86, 1, 0.25), (1, 84, 1, 0.25), (2, 81, 1, 0.25), (3, 84, 1, 0.25), (4, 86, 2, 0.25),
         (6, 89, 2, 0.25), (8, 88, 1, 0.25), (9, 86, 1, 0.25), (10, 84, 2, 0.25), (12, 83, 2, 0.25),
         (14, 81, 2, 0.25)),
        ((0, 80, 1, 0.125), (1, 83, 1, 0.125), (2, 80, 1, 0.125), (3, 83, 1, 0.125), (4, 86, 2, 0.125),
         (6, 83, 2, 0.125), (8, 80, 1, 0.125), (9, 83, 1, 0.125), (10, 86, 1, 0.125), (11, 88, 1, 0.125),
         (12, 89, 2, 0.125), (14, 88, 2, 0.125)),
    )

    kick_sig = _synth_music_kick(n_samples(0.10), 195.0, 54.0, 0.022, drive=1.6)
    snare_sig = _synth_music_noise_hit(n_samples(0.10), rng, 1050.0, 6800.0, 0.032, bits=3, hold=3)
    tamb_sig = _synth_music_noise_hit(n_samples(0.036), rng, 5800.0, 12500.0, 0.012, bits=4, hold=2)

    for bar_idx in range(total_bars):
        bar_step = bar_idx * 16
        chord_notes, bass_root = chords[bar_idx]

        # Ch 1: Frantic tarantella pulse lead
        for step_off, m_note, dur_steps, duty in lead_bars[bar_idx]:
            pos = offset_samples((bar_step + step_off) * step_s)
            dur_n = n_samples(dur_steps * step_s * 0.88)
            vib_d = 0.008 if dur_steps >= 3 else 0.0
            sig = _synth_pulse_note(dur_n, _midi_to_hz(m_note), duty=duty, vibrato_hz=7.0, vibrato_depth=vib_d)
            _ring_add(lead_buf, sig, pos, 0.62)

        # Ch 2: Nonstop 16th-note plucked harpsichord/pulse tarantella arpeggio
        for s_i in range(16):
            pos = offset_samples((bar_step + s_i) * step_s)
            arp_m = chord_notes[(s_i + (s_i // 4)) % len(chord_notes)]
            arp_n = n_samples(step_s * 0.82)
            arp_sig = _synth_plucked_lute_note(arp_n, _midi_to_hz(arp_m), brightness=0.72)
            _ring_add(arp_buf, arp_sig, pos, 0.36)

        # Ch 3: Galloping NES triangle wolf-hunt bassline
        gallop = (0, 12, 7, 12, 0, 12, 7, 12, 0, 12, 5, 7, 12, 7, 5, 4)
        for s_i in range(0, 16, 2):
            pos = offset_samples((bar_step + s_i) * step_s)
            tri = _synth_nes_triangle_note(n_samples(step_s * 1.75), _midi_to_hz(bass_root + gallop[s_i]))
            _ring_add(bass_buf, tri, pos, 0.84)
        # Gallop 16th-note pickups on steps 7 and 15
        for p_step in (7, 15):
            pos = offset_samples((bar_step + p_step) * step_s)
            tri = _synth_nes_triangle_note(n_samples(step_s * 0.9), _midi_to_hz(bass_root + 12))
            _ring_add(bass_buf, tri, pos, 0.70)

        # Ch 4: Rapid tambourine + tarantella kick/snare drive
        for s_i in range(16):
            pos = offset_samples((bar_step + s_i) * step_s)
            if s_i in (0, 3, 6, 8, 11, 14):
                _ring_add(drum_buf, kick_sig, pos, 0.84)
            if s_i in (4, 12) or (bar_idx in (3, 7, 9) and s_i in (13, 14, 15)):
                _ring_add(drum_buf, snare_sig, pos, 0.66 if s_i in (4, 12) else 0.56)
            _ring_add(drum_buf, tamb_sig, pos, 0.32 if s_i % 2 == 0 else 0.18)

    lead_clean = biquad(lead_buf, "lowpass", 8800.0)
    arp_clean = biquad(arp_buf, "lowpass", 7400.0)
    bass_clean = biquad(bass_buf, "lowpass", 1900.0)

    combined = mix(
        (lead_clean, 0.62),
        (arp_clean, 0.44),
        (bass_clean, 0.66),
        (drum_buf, 0.56),
    )
    return finalize(combined[:total_samples], peak_target=PEAK_TARGET, loopable=True)


def _synth_ice_chime_note(n: int, freq_hz: float, decay_s: float = 0.42):
    """Crystalline glacial chime bell with frosty inharmonic overtone."""
    f1 = multiply(oscillator(constant(freq_hz, n), "sine"), exp_decay(n, decay_s))
    f2 = multiply(oscillator(constant(freq_hz * 2.0, n), "sine"), exp_decay(n, decay_s * 0.65))
    f3 = multiply(oscillator(constant(freq_hz * 3.01, n), "sine"), exp_decay(n, decay_s * 0.35))
    return multiply(mix((f1, 0.76), (f2, 0.34), (f3, 0.18)), adsr(n, 0.004, 0.03, 0.85, 0.05))


def generate_frozen_boss_phase1_music(seed: int = DEFAULT_SEED):
    """Synthesize ~15.0s loopable austere crystalline chime & glacier sub-drone dirge for Rimecrest Arbiter Phase 1."""
    rng = random.Random(seed ^ 0xF02E0001)
    bpm = 96.0
    eighth_s = 60.0 / bpm / 2.0  # 0.3125s per 8th -> 8 eighths = 2.50s/bar
    total_bars = 6  # 6 bars = 15.000s exact seamless loop
    total_samples = n_samples(total_bars * 8 * eighth_s)

    chime_buf = silence(total_samples)
    pad_buf = silence(total_samples)
    bass_buf = silence(total_samples)
    perc_buf = silence(total_samples)

    # Austere D-minor / Dorian glacial progression: (chime_arp_midi, bass_root_midi)
    bars = (
        ((74, 77, 81, 86, 81, 77, 74, 72), 38),  # Dm
        ((72, 76, 79, 84, 79, 76, 72, 74), 36),  # C
        ((70, 74, 77, 82, 77, 74, 70, 72), 34),  # Bb
        ((69, 72, 76, 81, 76, 72, 69, 71), 33),  # Am
        ((70, 74, 77, 81, 77, 74, 70, 72), 34),  # Bbmaj7
        ((69, 73, 76, 81, 79, 76, 73, 69), 33),  # A7 glacial turnaround
    )

    cavern_kick = _synth_music_kick(n_samples(0.24), 92.0, 40.0, 0.065, drive=1.4)
    ice_tick = _synth_music_noise_hit(n_samples(0.055), rng, 3400.0, 8200.0, 0.018, bits=6, hold=1)

    for bar_idx, (chime_notes, bass_root) in enumerate(bars):
        bar_eighth = bar_idx * 8
        bar_pos = offset_samples(bar_eighth * eighth_s)

        # Deep glacier sub-drone + fifth harmonic pad sustaining across the bar
        bar_n = n_samples(7.8 * eighth_s)
        _ring_add(bass_buf, _synth_bowed_bass_note(bar_n, _midi_to_hz(bass_root)), bar_pos, 0.84)
        _ring_add(pad_buf, _synth_bowed_bass_note(bar_n, _midi_to_hz(bass_root + 19)), bar_pos, 0.28)

        # Austere crystalline chime arpeggios
        for e_i, midi_note in enumerate(chime_notes):
            pos = offset_samples((bar_eighth + e_i) * eighth_s)
            accent = 0.72 if e_i in (0, 3) else 0.50
            chime = _synth_ice_chime_note(n_samples(eighth_s * 2.2), _midi_to_hz(midi_note), decay_s=0.44)
            _ring_add(chime_buf, chime, pos, accent)

        # Slow resonant cavern pulse
        _ring_add(perc_buf, cavern_kick, bar_pos, 0.78)
        _ring_add(perc_buf, cavern_kick, offset_samples((bar_eighth + 4) * eighth_s), 0.54)
        for t_i in (2, 6):
            _ring_add(perc_buf, ice_tick, offset_samples((bar_eighth + t_i) * eighth_s), 0.34)

    bass_deep = biquad(bass_buf, "lowpass", 220.0, order=2)
    pad_frost = biquad(pad_buf, "bandpass", 640.0, 1.2)
    chime_crisp = biquad(chime_buf, "lowpass", 7800.0)
    combined = mix(
        (chime_crisp, 0.64),
        (pad_frost, 0.42),
        (bass_deep, 0.66),
        (perc_buf, 0.48),
    )
    return finalize(combined[:total_samples], peak_target=PEAK_TARGET, loopable=True)


def generate_frozen_boss_phase2_music(seed: int = DEFAULT_SEED):
    """Synthesize ~15.2s loopable 158 BPM high-tempo crystalline frost-shatter arpeggio & percussion breakout."""
    rng = random.Random(seed ^ 0xF02E0002)
    bpm = 158.0
    step_s = 60.0 / bpm / 4.0  # 16th note (~0.09494s) -> 1.519s/bar
    total_bars = 10  # 10 bars = ~15.19s exact seamless loop
    total_samples = n_samples(total_bars * 16 * step_s)

    lead_buf = silence(total_samples)
    arp_buf = silence(total_samples)
    bass_buf = silence(total_samples)
    drum_buf = silence(total_samples)

    # Driving D-minor frost-shatter progression: (chord_arp_4, bass_root)
    prog = (
        ((62, 65, 69, 74), 38),  # Dm
        ((62, 65, 69, 74), 38),  # Dm
        ((58, 62, 65, 70), 34),  # Bb
        ((60, 64, 67, 72), 36),  # C
        ((57, 61, 64, 69), 33),  # A7
        ((62, 65, 69, 74), 38),  # Dm
        ((65, 69, 72, 77), 41),  # F
        ((58, 62, 65, 70), 34),  # Bb
        ((60, 64, 67, 72), 36),  # C
        ((57, 61, 64, 69), 33),  # A7 turnaround
    )

    lead_phrases = (
        ((0, 74, 2), (2, 77, 2), (4, 81, 2), (6, 86, 2), (8, 84, 2), (10, 81, 2), (12, 79, 2), (14, 77, 2)),
        ((0, 81, 3), (3, 79, 1), (4, 77, 2), (6, 74, 2), (8, 76, 2), (10, 77, 2), (12, 81, 4)),
        ((0, 82, 2), (2, 81, 2), (4, 77, 2), (6, 74, 2), (8, 77, 2), (10, 81, 2), (12, 82, 4)),
        ((0, 84, 2), (2, 82, 2), (4, 79, 2), (6, 76, 2), (8, 79, 2), (10, 84, 2), (12, 86, 4)),
        ((0, 85, 2), (2, 81, 2), (4, 79, 2), (6, 76, 2), (8, 81, 2), (10, 85, 2), (12, 88, 4)),
        ((0, 86, 2), (2, 84, 2), (4, 81, 2), (6, 77, 2), (8, 81, 2), (10, 84, 2), (12, 86, 4)),
        ((0, 89, 2), (2, 86, 2), (4, 84, 2), (6, 81, 2), (8, 84, 2), (10, 86, 2), (12, 89, 4)),
        ((0, 86, 2), (2, 82, 2), (4, 81, 2), (6, 77, 2), (8, 74, 2), (10, 77, 2), (12, 82, 4)),
        ((0, 84, 2), (2, 81, 2), (4, 79, 2), (6, 76, 2), (8, 79, 2), (10, 82, 2), (12, 84, 4)),
        ((0, 85, 2), (2, 81, 2), (4, 76, 2), (6, 81, 2), (8, 85, 2), (10, 88, 2), (12, 85, 2), (14, 81, 2)),
    )

    kick_sig = _synth_music_kick(n_samples(0.14), 152.0, 44.0, 0.032, drive=1.9)
    snare_sig = _synth_music_noise_hit(n_samples(0.11), rng, 1900.0, 7400.0, 0.032, bits=5, hold=1)
    shard_hat = _synth_music_noise_hit(n_samples(0.042), rng, 5200.0, 10400.0, 0.012, bits=6, hold=1)

    for bar_idx, (chord, bass_root) in enumerate(prog):
        bar_step = bar_idx * 16

        # Ch 1: Shimmering ice-pulse lead doubled with crystalline chime attack
        for s_off, midi_n, dur_steps in lead_phrases[bar_idx]:
            pos = offset_samples((bar_step + s_off) * step_s)
            dur_n = n_samples(dur_steps * step_s * 0.92)
            pulse_n = _synth_pulse_note(dur_n, _midi_to_hz(midi_n), duty=0.125)
            bell_n = _synth_ice_chime_note(dur_n, _midi_to_hz(midi_n), decay_s=0.18)
            _ring_add(lead_buf, mix((pulse_n, 0.56), (bell_n, 0.54)), pos, 0.70)

        # Ch 2: Rapid 16th-note frost-shatter crystalline arpeggio
        for s_i in range(16):
            pos = offset_samples((bar_step + s_i) * step_s)
            midi_a = chord[s_i % 4] + (12 if (s_i // 4) % 2 == 1 else 0)
            arp_n = _synth_ice_chime_note(n_samples(step_s * 1.15), _midi_to_hz(midi_a), decay_s=0.095)
            _ring_add(arp_buf, arp_n, pos, 0.44 if s_i % 4 == 0 else 0.30)

        # Ch 3: Driving octave-pumping triangle bass
        for s_i in range(0, 16, 2):
            pos = offset_samples((bar_step + s_i) * step_s)
            b_midi = bass_root + (12 if (s_i % 4 == 2) else 0)
            tri = _synth_nes_triangle_note(n_samples(step_s * 1.8), _midi_to_hz(b_midi))
            _ring_add(bass_buf, tri, pos, 0.84)

        # Ch 4: Crisp frost-shatter percussion breakout
        for s_i in range(16):
            pos = offset_samples((bar_step + s_i) * step_s)
            if s_i in (0, 6, 8, 14):
                _ring_add(drum_buf, kick_sig, pos, 0.86)
            if s_i in (4, 12) or (bar_idx in (4, 9) and s_i in (13, 14, 15)):
                _ring_add(drum_buf, snare_sig, pos, 0.68 if s_i in (4, 12) else 0.56)
            _ring_add(drum_buf, shard_hat, pos, 0.34 if s_i % 2 == 0 else 0.18)

    lead_clean = biquad(lead_buf, "lowpass", 9200.0)
    arp_clean = biquad(arp_buf, "lowpass", 8400.0)
    bass_clean = biquad(bass_buf, "lowpass", 1800.0)
    combined = mix(
        (lead_clean, 0.62),
        (arp_clean, 0.46),
        (bass_clean, 0.66),
        (drum_buf, 0.56),
    )
    return finalize(combined[:total_samples], peak_target=PEAK_TARGET, loopable=True)


MUSIC_GENERATORS: Dict[str, Callable[[int], object]] = {
    "slug_boss_phase1.ogg": generate_slug_boss_phase1_music,
    "slug_boss_phase2.ogg": generate_slug_boss_phase2_music,
    "pastoral_boss_phase1.ogg": generate_pastoral_boss_phase1_music,
    "pastoral_boss_phase2.ogg": generate_pastoral_boss_phase2_music,
    "frozen_boss_phase1.ogg": generate_frozen_boss_phase1_music,
    "frozen_boss_phase2.ogg": generate_frozen_boss_phase2_music,
}


def generate_music(
    base_seed: int = DEFAULT_SEED,
    output_dir: str = MUSIC_DIR,
    verify: bool = True,
    force: bool = False,
) -> List[str]:
    """Synthesize and export all procedural boss music tracks into output_dir (default: assets/audio/music/)."""
    written = []
    for name, gen_fn in sorted(MUSIC_GENERATORS.items()):
        path = os.path.join(output_dir, output_name(name))
        if os.path.exists(path) and not force:
            print(f"[MUSIC] Skipping existing {path} (use --force to overwrite)")
            continue
        signal = gen_fn(sound_seed(name, base_seed))
        encoder, did_write = export_ogg_if_changed(signal, path)
        if not did_write:
            print(f"[MUSIC] Unchanged {path} (PCM identical, skipped write)")
            continue
        length = verify_ogg(path) if verify else len(signal) / SAMPLE_RATE
        status = "verified" if verify else "unverified"
        print(f"[MUSIC] Wrote {path} ({length:.2f}s, {encoder}, {status})")
        written.append(path)
    return written


# ==============================================================================
# CLI
# ==============================================================================


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Offline procedural Ogg Vorbis SFX generator for Avoid Rain (44.1 kHz mono)."
    )
    parser.add_argument("--preset", choices=sorted(PRESETS), help="Synthesis archetype to render.")
    parser.add_argument("--name", help="Output file stem (e.g. attack_swing). Without --preset, uses its recipe.")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (default: stable per-sound seed).")
    parser.add_argument("--variants", type=int, default=1, help="Number of seeded variants to render.")
    parser.add_argument("--output-dir", default=None,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}; variants: {DEFAULT_VARIANT_DIR}).")
    parser.add_argument("--duration", type=float, default=None, help="Override the preset duration in seconds.")
    parser.add_argument("--list-missing", action="store_true", help="List missing SFX references and exit.")
    parser.add_argument("--list-presets", action="store_true", help="List available presets and exit.")
    parser.add_argument("--fill-missing", action="store_true",
                        help="Generate all missing SFX (default action when no --preset/--name is given).")
    parser.add_argument("--music", action="store_true",
                        help=f"Generate procedural boss music tracks into {MUSIC_DIR}.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    parser.add_argument("--no-verify", action="store_true", help="Skip pygame.mixer.Sound load verification.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""
    args = parse_arguments(argv)
    verify = not args.no_verify

    if args.list_presets:
        for name in sorted(PRESETS):
            print(f"  {name:<10} {PRESETS[name][2]}")
        return 0

    if args.list_missing:
        missing = find_missing_sfx(sfx_dir=args.output_dir or DEFAULT_OUTPUT_DIR)
        if not missing:
            print("[SFX] No missing sound effects.")
        for name, sources in missing.items():
            preset = resolve_recipe(name)[0]
            print(f"  {name:<24} preset={preset:<10} <- {', '.join(sources)}")
        return 0

    if args.variants < 1:
        print("[SFX] --variants must be >= 1", file=sys.stderr)
        return 2

    overrides = {"duration": args.duration} if args.duration else {}
    try:
        if args.music:
            base_seed = args.seed if args.seed is not None else DEFAULT_SEED
            generate_music(base_seed, args.output_dir or MUSIC_DIR, verify=verify, force=args.force)
            return 0
        if args.preset or args.name:
            name = args.name or args.preset
            preset, recipe_overrides = (args.preset, {}) if args.preset else resolve_recipe(name)
            merged = {**recipe_overrides, **overrides}
            seed = args.seed if args.seed is not None else sound_seed(name)
            if args.variants > 1:
                generate_variants(name, preset, merged, seed, args.variants, args.output_dir or DEFAULT_VARIANT_DIR,
                                  verify)
            else:
                generate_sound(name, preset, merged, seed, args.output_dir or DEFAULT_OUTPUT_DIR, verify, args.force)
            return 0
        base_seed = args.seed if args.seed is not None else DEFAULT_SEED
        fill_missing(base_seed, args.output_dir or DEFAULT_OUTPUT_DIR, verify, args.force)
    except (RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"[SFX] Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
