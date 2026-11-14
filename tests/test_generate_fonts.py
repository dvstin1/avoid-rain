"""Unit tests for generate_fonts.py and rendering.bitmap_font.BitmapFont."""
# pylint: disable=no-member
import json
import os
import pygame
import constants
import generate_fonts
from rendering.bitmap_font import BitmapFont, load_font_or_sysfont, normalize_text
from rendering.renderer import Renderer


def setup_module():
    """Ensure headless SDL environment for pygame."""
    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()


def test_generate_all_fonts_covers_printable_ascii_and_is_idempotent(tmp_path):
    """Verify all 3 font atlases + JSON sidecars cover ASCII 32..126 and are idempotent."""
    fonts_dir = tmp_path / "fonts"
    stats1 = {}
    results = generate_fonts.generate_all_fonts(fonts_dir=str(fonts_dir), stats_out=stats1)
    assert stats1["updated"] == 6
    assert stats1["unchanged"] == 0
    assert set(results.keys()) == {"ink_sans", "ink_mono", "manuscript_serif"}

    expected_heights = {"ink_sans": 12, "ink_mono": 14, "manuscript_serif": 18}
    for name, (png_path, json_path) in results.items():
        assert os.path.exists(png_path)
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        assert meta["base_height"] == expected_heights[name]
        for code in range(32, 127):
            ch = chr(code)
            assert ch in meta["glyphs"], f"{name} missing ASCII {code} ({ch!r})"
            assert meta["glyphs"][ch]["advance"] > 0

    mtimes_before = {
        path: os.stat(path).st_mtime_ns
        for pair in results.values()
        for path in pair
    }

    stats2 = {}
    generate_fonts.generate_all_fonts(fonts_dir=str(fonts_dir), stats_out=stats2)
    assert stats2["updated"] == 0
    assert stats2["unchanged"] == 6
    for path, old_mtime in mtimes_before.items():
        assert os.stat(path).st_mtime_ns == old_mtime


def test_bitmap_font_headless_render_unicode_and_non_ascii_fallback(tmp_path):
    """Verify BitmapFont works with pygame.font uninitialized and handles Unicode cleanly."""
    fonts_dir = tmp_path / "fonts"
    generate_fonts.generate_all_fonts(fonts_dir=str(fonts_dir))

    was_font_init = pygame.font.get_init()
    if was_font_init:
        pygame.font.quit()
    try:
        bf = BitmapFont(
            str(fonts_dir / "ink_sans.png"),
            str(fonts_dir / "ink_sans.json"),
            scale=2,
        )
        assert normalize_text("“Hold—don’t fade…”") == '"Hold--don\'t fade..."'

        w, h = bf.size("Hold—fast!")
        assert w > 0
        assert h == 24

        surf = bf.render("Hold—fast!", True, (220, 180, 90))
        assert surf.get_size() == (w, h)
        assert surf.get_flags() & pygame.SRCALPHA != 0

        # Unknown non-ASCII character must fall back cleanly without crashing
        fb_surf = bf.render("Glyph: \u2603", True, (255, 255, 255))
        assert fb_surf.get_width() > 0
        assert fb_surf.get_height() == 24
    finally:
        if was_font_init:
            pygame.font.init()


def test_renderer_wires_bitmap_fonts_and_falls_back(tmp_path):
    """Verify Renderer initializes BitmapFont instances and falls back when dir is missing."""
    screen = pygame.Surface((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
    renderer = Renderer(screen)
    for attr in (
        "font",
        "small_font",
        "large_font",
        "hud_font",
        "slot_font",
        "glyph_font",
        "bloom_font",
        "title_font",
    ):
        assert isinstance(getattr(renderer, attr), BitmapFont), f"Renderer.{attr} is not BitmapFont"

    assert renderer.slot_font.get_height() == 12
    assert renderer.font.get_height() == 24
    assert renderer.large_font.get_height() == 36
    assert renderer.small_font.get_height() == 14
    assert renderer.title_font.get_height() == 54
    assert renderer.bloom_font.get_height() == 72

    missing_dir = tmp_path / "no_fonts"
    fallback = load_font_or_sysfont("ink_sans", 2, "Arial", 24, fonts_dir=str(missing_dir))
    assert isinstance(fallback, pygame.font.Font)
