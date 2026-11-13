"""Unit tests for the procedural Ogg Vorbis SFX generator (generate_sfx.py)."""
import os
import subprocess

import pytest

import generate_sfx


def test_all_presets_render_normalized_and_finite():
    """Every registered preset renders a non-empty, non-clipping, finite signal."""
    for preset_name in generate_sfx.PRESETS:
        sig = generate_sfx.render_preset(preset_name, seed=42)
        assert len(sig) > 0, f"{preset_name} produced empty signal"
        pk = generate_sfx.peak(sig)
        assert 0.01 < pk <= 1.0, f"{preset_name} peak {pk} out of bounds"


def test_pure_python_fallback_when_numpy_absent(monkeypatch):
    """DSP synthesis and normalization work cleanly without numpy."""
    monkeypatch.setattr(generate_sfx, "np", None)
    monkeypatch.setattr(generate_sfx, "_scipy_lfilter", None)

    for preset_name in ("slash", "hit_flesh", "footstep", "pickup", "ui_select", "warp"):
        sig = generate_sfx.render_preset(preset_name, seed=99, overrides={"duration": 0.08})
        assert isinstance(sig, list)
        assert len(sig) == generate_sfx.n_samples(0.08)
        pk = generate_sfx.peak(sig)
        assert 0.01 < pk <= 1.0


def test_dsp_filters_and_envelopes():
    """Verify biquad, moving_average, soft_clip, bitcrush, and ADSR primitives."""
    n = generate_sfx.n_samples(0.1)
    env = generate_sfx.adsr(n, 0.01, 0.02, 0.5, 0.02)
    assert len(env) == n
    assert generate_sfx.peak(env) <= 1.0 + 1e-6

    noise = generate_sfx.pink_noise(n, generate_sfx.random.Random(7))
    lp = generate_sfx.biquad(noise, "lowpass", 500.0, order=2)
    hp = generate_sfx.biquad(noise, "highpass", 2000.0)
    ma = generate_sfx.moving_average(noise, 5)
    crushed = generate_sfx.bitcrush(generate_sfx.soft_clip(noise, 2.0), bits=4, hold=2)
    assert len(lp) == len(hp) == len(ma) == len(crushed) == n


def test_export_ogg_and_verify_with_pygame(tmp_path):
    """Exported .ogg files are 44.1 kHz mono Vorbis and load cleanly in pygame.mixer.Sound."""
    if generate_sfx.available_encoder() is None:
        pytest.skip("No Ogg Vorbis encoder installed")

    out_path = str(tmp_path / "test_slash.ogg")
    sig = generate_sfx.render_preset("slash", seed=123)
    generate_sfx.export_ogg(sig, out_path)
    assert os.path.exists(out_path)

    length = generate_sfx.verify_ogg(out_path)
    assert length > 0.1

    if subprocess.run(["which", "ffprobe"], capture_output=True, check=False).returncode == 0:
        probe = subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_name,sample_rate,channels", "-of", "csv=p=0", out_path,
            ],
            text=True,
        ).strip()
        assert probe == f"vorbis,{generate_sfx.SAMPLE_RATE},{generate_sfx.CHANNELS}"


def test_variants_and_missing_scan(tmp_path):
    """Verify seeded variant generation and project missing-SFX scanning."""
    if generate_sfx.available_encoder() is None:
        pytest.skip("No Ogg Vorbis encoder installed")

    paths = generate_sfx.generate_variants(
        "test_step", "footstep", {"duration": 0.08}, base_seed=10, variants=3,
        output_dir=str(tmp_path), verify=True,
    )
    assert len(paths) == 3
    for p in paths:
        assert os.path.exists(p)

    # Project currently has all manifest & referenced SFX filled
    missing = generate_sfx.find_missing_sfx(".")
    assert missing == {}
