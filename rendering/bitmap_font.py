"""Drop-in bitmap font runtime wrapper matching the pygame.font.Font interface."""
# pylint: disable=no-member,too-many-arguments,too-many-positional-arguments,too-many-instance-attributes

from collections import OrderedDict
import json
import os
from typing import Dict, Optional, Tuple
import pygame

UNICODE_PUNCTUATION_MAP = str.maketrans(
    {
        "\u2014": "--",  # em-dash
        "\u2013": "-",   # en-dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # horizontal ellipsis
    }
)


def normalize_text(text: str) -> str:
    """Normalize common Unicode punctuation into printable ASCII equivalents."""
    if not text:
        return ""
    return str(text).translate(UNICODE_PUNCTUATION_MAP)


class BitmapFont:
    """Custom pixel/manuscript bitmap font matching pygame.font.Font's size() and render()."""

    MAX_CACHE_ENTRIES = 512

    def __init__(
        self,
        atlas_path: str,
        metrics_path: str,
        scale: int = 1,
        bold: bool = False,
        fallback_font_name: str = "Arial",
        fallback_size: Optional[int] = None,
    ) -> None:
        self.atlas_path = str(atlas_path)
        self.metrics_path = str(metrics_path)
        self.scale = max(1, int(scale))
        self.bold = bool(bold)
        self.fallback_font_name = fallback_font_name

        with open(self.metrics_path, "r", encoding="utf-8") as handle:
            meta = json.load(handle)

        self.name: str = meta.get("name", "bitmap_font")
        self.base_height: int = int(meta.get("base_height", 12))
        self.line_height: int = int(meta.get("line_height", self.base_height)) * self.scale
        self.default_advance: int = int(meta.get("default_advance", 6))
        self.glyphs: Dict[str, dict] = meta.get("glyphs", {})
        self.fallback_size = int(fallback_size or (self.base_height * self.scale))

        atlas = pygame.image.load(self.atlas_path)
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            atlas = atlas.convert_alpha()
        self.atlas = atlas

        self._glyph_cache: Dict[str, pygame.Surface] = {}
        self._line_cache: OrderedDict[Tuple[str, Tuple[int, ...]], pygame.Surface] = OrderedDict()
        self._sysfont_fallback = None
        self._sysfont_failed = False

    def _get_scaled_glyph(self, ch: str) -> Optional[pygame.Surface]:
        """Return the pre-sliced, integer-scaled white-on-alpha glyph surface."""
        if ch in self._glyph_cache:
            return self._glyph_cache[ch]
        g = self.glyphs.get(ch)
        if g is None:
            return None
        w, h = int(g["w"]), int(g["h"])
        sub = self.atlas.subsurface(pygame.Rect(int(g["x"]), int(g["y"]), w, h))
        if self.scale > 1:
            sub = pygame.transform.scale(sub, (w * self.scale, h * self.scale))
        else:
            sub = sub.copy()
        self._glyph_cache[ch] = sub
        return sub

    def _get_sysfont_fallback(self):
        """Lazily initialize a SysFont fallback for non-ASCII characters if available."""
        if self._sysfont_fallback is not None or self._sysfont_failed:
            return self._sysfont_fallback
        if not pygame.font.get_init():
            self._sysfont_failed = True
            return None
        try:
            self._sysfont_fallback = pygame.font.SysFont(
                self.fallback_font_name, self.fallback_size, bold=self.bold
            )
        except pygame.error:
            self._sysfont_failed = True
            return None
        return self._sysfont_fallback

    def _char_advance(self, ch: str) -> int:
        """Return the scaled horizontal advance width in pixels for a single character."""
        g = self.glyphs.get(ch)
        if g is not None:
            return int(g["advance"]) * self.scale
        sysfont = self._get_sysfont_fallback()
        if sysfont is not None:
            try:
                return int(sysfont.size(ch)[0])
            except pygame.error:
                pass
        q_meta = self.glyphs.get("?")
        if q_meta is not None:
            return int(q_meta["advance"]) * self.scale
        return self.default_advance * self.scale

    def size(self, text: str) -> Tuple[int, int]:
        """Compute exact pixel (width, height) for text using atlas glyph advances."""
        norm = normalize_text(text)
        if not norm:
            return (0, self.line_height)
        total_w = sum(self._char_advance(ch) for ch in norm)
        return (total_w, self.line_height)

    def get_height(self) -> int:
        """Return line height in pixels, matching pygame.font.Font.get_height()."""
        return self.line_height

    def render(self, text: str, antialias: bool, color: Tuple[int, ...]) -> pygame.Surface:
        """Render normalized text tinted to color onto a transparent RGBA Surface."""
        del antialias  # Crisp pixel-art atlas rendering
        norm = normalize_text(text)
        rgb = tuple(int(c) for c in color[:3])
        alpha = int(color[3]) if len(color) > 3 else 255
        rgba_key = (norm, rgb + (alpha,))

        cached = self._line_cache.get(rgba_key)
        if cached is not None:
            self._line_cache.move_to_end(rgba_key)
            return cached

        width, height = self.size(norm)
        surf = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        cursor_x = 0
        for ch in norm:
            g_meta = self.glyphs.get(ch)
            if g_meta is not None:
                g_surf = self._get_scaled_glyph(ch)
                if g_surf is not None and ch != " ":
                    x_off = int(g_meta.get("x_offset", 0)) * self.scale
                    y_off = int(g_meta.get("y_offset", 0)) * self.scale
                    surf.blit(g_surf, (cursor_x + x_off, y_off))
                    if self.bold:
                        surf.blit(g_surf, (cursor_x + x_off + 1, y_off))
                cursor_x += int(g_meta["advance"]) * self.scale
            else:
                sysfont = self._get_sysfont_fallback()
                if sysfont is not None:
                    try:
                        fb_surf = sysfont.render(ch, True, (255, 255, 255))
                        surf.blit(fb_surf, (cursor_x, 0))
                        cursor_x += fb_surf.get_width()
                        continue
                    except pygame.error:
                        pass
                q_surf = self._get_scaled_glyph("?")
                if q_surf is not None:
                    surf.blit(q_surf, (cursor_x, 0))
                cursor_x += self._char_advance("?")

        if width > 0 and (rgb != (255, 255, 255) or alpha != 255):
            tint = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            tint.fill(rgb + (alpha,))
            surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self._line_cache[rgba_key] = surf
        if len(self._line_cache) > self.MAX_CACHE_ENTRIES:
            self._line_cache.popitem(last=False)
        return surf


def load_font_or_sysfont(
    font_name: str,
    scale: int,
    sysfont_name: str,
    sysfont_size: int,
    bold: bool = False,
    italic: bool = False,
    fonts_dir: str = os.path.join("assets", "fonts"),
):
    """Load BitmapFont from fonts_dir, falling back gracefully to pygame.font.SysFont."""
    atlas_path = os.path.join(fonts_dir, f"{font_name}.png")
    metrics_path = os.path.join(fonts_dir, f"{font_name}.json")
    if os.path.exists(atlas_path) and os.path.exists(metrics_path):
        try:
            return BitmapFont(
                atlas_path,
                metrics_path,
                scale=scale,
                bold=bold,
                fallback_font_name=sysfont_name,
                fallback_size=sysfont_size,
            )
        except (OSError, json.JSONDecodeError, pygame.error):
            pass
    return pygame.font.SysFont(sysfont_name, sysfont_size, bold=bold, italic=italic)
