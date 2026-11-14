#!/usr/bin/env python3
"""Standalone procedural pixel/manuscript bitmap font atlas generator for Avoid Rain.

Generates white-on-transparent RGBA glyph sprite sheets and JSON metric sidecars
under `assets/fonts/` for three distinct styles:
1. `ink_sans` (12px base): Clean proportional pixel font (1x=12px, 2x=24px, 3x=36px).
2. `ink_mono` (14px base): Fixed-cell monospace pixel font (1x=14px).
3. `manuscript_serif` (18px base): Calligraphic ink-serif display font (3x=54px, 4x=72px).

Reuses `write_surface_if_changed` from `generate_assets.py` so unchanged PNGs are
never rewritten on disk.
"""
# pylint: disable=no-member,too-many-locals,too-many-arguments,too-many-branches

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import pygame

from generate_assets import write_surface_if_changed

DEFAULT_FONTS_DIR = os.path.join("assets", "fonts")
DEFAULT_SPECIMEN_PATH = os.path.join("/tmp", "avoid_rain_font_specimen.png")
PRINTABLE_ASCII = [chr(code) for code in range(32, 127)]

# Compact 7-row core pixel glyphs ('.' = transparent, '#' = opaque white).
# Uppercase & digits sit on rows 0..6; lowercase uses rows 1..6 (x-height 5px)
# with ascenders at row 0 and descenders marked in DESCENDER_GLYPHS (shifted +2px).
BASE_GLYPHS_7: Dict[str, List[str]] = {
    " ": ["..."],
    "!": ["#", "#", "#", "#", "#", ".", "#"],
    '"': ["#.#", "#.#", "#.#", "...", "...", "...", "..."],
    "#": [".#.#.", "#####", ".#.#.", ".#.#.", "#####", ".#.#.", "....."],
    "$": ["..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."],
    "%": ["##..#", "##.#.", "..#..", ".#...", "#.##.", "..##.", "....."],
    "&": [".##..", "#..#.", ".##..", "#.#.#", "#..#.", ".##.#", "....."],
    "'": ["#", "#", "#", ".", ".", ".", "."],
    "(": [".#", "#.", "#.", "#.", "#.", "#.", ".#"],
    ")": ["#.", ".#", ".#", ".#", ".#", ".#", "#."],
    "*": [".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    ",": ["..", "..", "..", "..", "..", ".#", "#."],
    "-": ["....", "....", "....", "####", "....", "....", "...."],
    ".": [".", ".", ".", ".", ".", ".", "#"],
    "/": ["....#", "...#.", "..#..", "..#..", ".#...", "#....", "....."],
    "0": [".###.", "#..##", "#.#.#", "#.#.#", "##..#", ".###.", "....."],
    "1": [".#.", "##.", ".#.", ".#.", ".#.", "###", "..."],
    "2": [".###.", "#...#", "...#.", "..#..", ".#...", "#####", "....."],
    "3": ["####.", "....#", "..##.", "....#", "#...#", ".###.", "....."],
    "4": ["#...#", "#...#", "#####", "....#", "....#", "....#", "....."],
    "5": ["#####", "#....", "####.", "....#", "#...#", ".###.", "....."],
    "6": [".###.", "#....", "####.", "#...#", "#...#", ".###.", "....."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", "....."],
    "8": [".###.", "#...#", ".###.", "#...#", "#...#", ".###.", "....."],
    "9": [".###.", "#...#", ".####", "....#", "...#.", ".##..", "....."],
    ":": [".", ".", "#", ".", ".", "#", "."],
    ";": ["..", "..", ".#", "..", "..", ".#", "#."],
    "<": ["...#", "..#.", ".#..", "#...", ".#..", "..#.", "...#"],
    "=": ["....", "....", "####", "....", "####", "....", "...."],
    ">": ["#...", ".#..", "..#.", "...#", "..#.", ".#..", "#..."],
    "?": [".###.", "#...#", "...#.", "..#..", "..#..", ".....", "..#.."],
    "@": [".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "....."],
    "B": ["####.", "#...#", "####.", "#...#", "#...#", "####.", "....."],
    "C": [".###.", "#...#", "#....", "#....", "#...#", ".###.", "....."],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "####.", "....."],
    "E": ["#####", "#....", "####.", "#....", "#....", "#####", "....."],
    "F": ["#####", "#....", "####.", "#....", "#....", "#....", "....."],
    "G": [".###.", "#....", "#..##", "#...#", "#...#", ".###.", "....."],
    "H": ["#...#", "#...#", "#####", "#...#", "#...#", "#...#", "....."],
    "I": ["###", ".#.", ".#.", ".#.", ".#.", "###", "..."],
    "J": ["..###", "...#.", "...#.", "#..#.", "#..#.", ".##..", "....."],
    "K": ["#...#", "#..#.", "###..", "#..#.", "#...#", "#...#", "....."],
    "L": ["#....", "#....", "#....", "#....", "#....", "#####", "....."],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#", "#...#", "....."],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "....."],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", ".###.", "....."],
    "P": ["####.", "#...#", "####.", "#....", "#....", "#....", "....."],
    "Q": [".###.", "#...#", "#...#", "#.#.#", "#..#.", ".##.#", "....."],
    "R": ["####.", "#...#", "####.", "#.#..", "#..#.", "#...#", "....."],
    "S": [".####", "#....", ".###.", "....#", "....#", "####.", "....."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "....."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", ".###.", "....."],
    "V": ["#...#", "#...#", "#...#", ".#.#.", ".#.#.", "..#..", "....."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "##.##", "#...#", "....."],
    "X": ["#...#", ".#.#.", "..#..", "..#..", ".#.#.", "#...#", "....."],
    "Y": ["#...#", ".#.#.", "..#..", "..#..", "..#..", "..#..", "....."],
    "Z": ["#####", "...#.", "..#..", ".#...", "#....", "#####", "....."],
    "[": ["##", "#.", "#.", "#.", "#.", "#.", "##"],
    "\\": ["#....", ".#...", "..#..", "..#..", "...#.", "....#", "....."],
    "]": ["##", ".#", ".#", ".#", ".#", ".#", "##"],
    "^": ["..#..", ".#.#.", "#...#", ".....", ".....", ".....", "....."],
    "_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    "`": ["#.", ".#", "..", "..", "..", "..", ".."],
    "a": [".....", ".....", ".###.", "....#", ".####", ".###.", "....."],
    "b": ["#....", "#....", "####.", "#...#", "#...#", "####.", "....."],
    "c": [".....", ".....", ".###.", "#....", "#....", ".###.", "....."],
    "d": ["....#", "....#", ".####", "#...#", "#...#", ".####", "....."],
    "e": [".....", ".....", ".###.", "#.###", "#....", ".###.", "....."],
    "f": ["..##.", ".#...", "###..", ".#...", ".#...", ".#...", "....."],
    "g": [".....", ".####", "#...#", ".####", "....#", ".###.", "....."],
    "h": ["#....", "#....", "####.", "#...#", "#...#", "#...#", "....."],
    "i": [".", "#", ".", "#", "#", "#", "."],
    "j": ["..#", "...", "..#", "..#", "..#", "#.#", ".#."],
    "k": ["#...", "#...", "#.#.", "##..", "#.#.", "#..#", "...."],
    "l": ["#", "#", "#", "#", "#", "#", "."],
    "m": [".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "....."],
    "n": [".....", ".....", "####.", "#...#", "#...#", "#...#", "....."],
    "o": [".....", ".....", ".###.", "#...#", "#...#", ".###.", "....."],
    "p": [".....", "####.", "#...#", "####.", "#....", "#....", "....."],
    "q": [".....", ".####", "#...#", ".####", "....#", "....#", "....."],
    "r": ["....", "....", "#.##", "##..", "#...", "#...", "...."],
    "s": ["....", "....", ".###", "##..", "..##", "###.", "...."],
    "t": [".#..", ".#..", "###.", ".#..", ".#..", "..##", "...."],
    "u": [".....", ".....", "#...#", "#...#", "#...#", ".####", "....."],
    "v": [".....", ".....", "#...#", "#...#", ".#.#.", "..#..", "....."],
    "w": [".....", ".....", "#...#", "#.#.#", "#.#.#", ".#.#.", "....."],
    "x": ["....", "....", "#..#", ".##.", ".##.", "#..#", "...."],
    "y": [".....", "#...#", "#...#", ".####", "....#", ".###.", "....."],
    "z": ["....", "....", "####", "..#.", ".#..", "####", "...."],
    "{": [".##", ".#.", "#..", ".#.", ".#.", ".#.", ".##"],
    "|": ["#", "#", "#", "#", "#", "#", "#"],
    "}": ["##.", ".#.", "..#", ".#.", ".#.", ".#.", "##."],
    "~": [".....", ".#.#.", "#.#..", ".....", ".....", ".....", "....."],
}

DESCENDER_GLYPHS = set("gjpqy,;")


def _grid_to_points(rows: List[str]) -> Tuple[int, int, List[Tuple[int, int]]]:
    """Convert an ASCII glyph pattern into (width, height, [(x, y), ...])."""
    h = len(rows)
    w = max((len(r) for r in rows), default=1)
    pts: List[Tuple[int, int]] = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                pts.append((x, y))
    return w, h, pts


def _render_ink_sans_glyph(ch: str) -> Tuple[pygame.Surface, int]:
    """Render a 12px-tall proportional pixel glyph and return (surface, advance)."""
    rows = BASE_GLYPHS_7[ch]
    gw, gh, pts = _grid_to_points(rows)
    if ch == " ":
        surf = pygame.Surface((3, 12), pygame.SRCALPHA)
        return surf, 4
    y_shift = 3 if ch in DESCENDER_GLYPHS else 2
    surf = pygame.Surface((gw, 12), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    for px, py in pts:
        ty = py + y_shift
        if 0 <= ty < 12:
            surf.set_at((px, ty), (255, 255, 255, 255))
            # Subtle vertical reinforcement on tall stems for crisp 1x/2x legibility
            if gh >= 6 and ty + 1 < 12 and ch not in (".", ",", ":", ";", "-", "_", "="):
                surf.set_at((px, ty + 1), (255, 255, 255, 215))
    advance = max(2, gw + 1)
    return surf, advance


def _render_ink_mono_glyph(ch: str) -> Tuple[pygame.Surface, int]:
    """Render a 14px-tall fixed-cell (8px advance) monospace pixel glyph."""
    rows = BASE_GLYPHS_7[ch]
    gw, _, pts = _grid_to_points(rows)
    cell_w = 8
    surf = pygame.Surface((cell_w, 14), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    if ch == " ":
        return surf, cell_w
    x_pad = max(0, (cell_w - 1 - gw) // 2)
    y_shift = 4 if ch in DESCENDER_GLYPHS else 2
    for px, py in pts:
        tx = px + x_pad
        ty = py + y_shift
        if 0 <= tx < cell_w and 0 <= ty < 14:
            surf.set_at((tx, ty), (255, 255, 255, 255))
            if ty + 1 < 14 and ch not in (".", ",", ":", ";", "-", "_", "="):
                surf.set_at((tx, ty + 1), (255, 255, 255, 200))
    return surf, cell_w


def _render_manuscript_serif_glyph(ch: str) -> Tuple[pygame.Surface, int]:
    """Render an 18px-tall calligraphic/ink-serif display glyph with quill-nib serifs."""
    rows = BASE_GLYPHS_7[ch]
    gw, _, pts = _grid_to_points(rows)
    if ch == " ":
        return pygame.Surface((5, 18), pygame.SRCALPHA), 6

    # Scale 7px core vertically (~2x) and add thick vertical stems + quill-nib serifs
    scale_x = 2 if gw >= 4 else 1
    out_w = gw * scale_x + 2
    surf = pygame.Surface((out_w, 18), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    y_shift = 3 if ch in DESCENDER_GLYPHS else 1
    pt_set = set(pts)

    for px, py in pts:
        tx = 1 + px * scale_x
        ty = y_shift + py * 2
        for dx in range(scale_x):
            for dy in range(2):
                if 0 <= tx + dx < out_w and 0 <= ty + dy < 18:
                    surf.set_at((tx + dx, ty + dy), (255, 255, 255, 255))
        # Subtle calligraphic serif flicks on top/bottom terminals
        if ch.isalpha() and (px, py - 1) not in pt_set and (px - 1, py) not in pt_set:
            if tx - 1 >= 0 and 0 <= ty < 18:
                surf.set_at((tx - 1, ty), (255, 255, 255, 220))
        if ch.isalpha() and (px, py + 1) not in pt_set and py >= 4:
            if tx + scale_x < out_w and 0 <= ty + 1 < 18:
                surf.set_at((tx + scale_x, ty + 1), (255, 255, 255, 220))
    return surf, out_w + 1


FONT_SPEC_BUILDERS = {
    "ink_sans": (12, 9, 6, _render_ink_sans_glyph),
    "ink_mono": (14, 11, 8, _render_ink_mono_glyph),
    "manuscript_serif": (18, 14, 10, _render_manuscript_serif_glyph),
}


def write_json_if_changed(data: dict, output_path: str | Path) -> bool:
    """Write formatted JSON to output_path only if missing or content changed."""
    target = str(output_path)
    payload = json.dumps(data, indent=2, sort_keys=False) + "\n"
    if os.path.exists(target):
        try:
            with open(target, "r", encoding="utf-8") as handle:
                if handle.read() == payload:
                    return False
        except OSError:
            pass
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(payload)
    return True


def build_font_atlas(name: str) -> Tuple[pygame.Surface, dict]:
    """Build the RGBA glyph sprite sheet and metric metadata dict for a named font."""
    base_height, baseline, default_advance, glyph_fn = FONT_SPEC_BUILDERS[name]
    cols = 16
    pad = 2
    rendered: List[Tuple[str, pygame.Surface, int]] = []
    max_cell_w = 1
    for ch in PRINTABLE_ASCII:
        g_surf, adv = glyph_fn(ch)
        rendered.append((ch, g_surf, adv))
        max_cell_w = max(max_cell_w, g_surf.get_width())

    cell_w = max_cell_w + pad
    cell_h = base_height + pad
    rows = (len(rendered) + cols - 1) // cols
    atlas = pygame.Surface((cols * cell_w, rows * cell_h), pygame.SRCALPHA)
    atlas.fill((0, 0, 0, 0))

    glyph_meta: Dict[str, dict] = {}
    for idx, (ch, g_surf, adv) in enumerate(rendered):
        col_i = idx % cols
        row_i = idx // cols
        ax = col_i * cell_w
        ay = row_i * cell_h
        atlas.blit(g_surf, (ax, ay))
        glyph_meta[ch] = {
            "x": ax,
            "y": ay,
            "w": g_surf.get_width(),
            "h": g_surf.get_height(),
            "advance": adv,
            "x_offset": 0,
            "y_offset": 0,
        }

    metadata = {
        "name": name,
        "base_height": base_height,
        "baseline": baseline,
        "line_height": base_height,
        "default_advance": default_advance,
        "glyphs": glyph_meta,
    }
    return atlas, metadata


def generate_all_fonts(
    fonts_dir: str = DEFAULT_FONTS_DIR,
    stats_out: Dict[str, int] | None = None,
) -> Dict[str, Tuple[str, str]]:
    """Generate all 3 bitmap font PNG+JSON pairs in fonts_dir using diff guards."""
    os.makedirs(fonts_dir, exist_ok=True)
    results: Dict[str, Tuple[str, str]] = {}
    updated = 0
    unchanged = 0

    for name in FONT_SPEC_BUILDERS:
        atlas, metadata = build_font_atlas(name)
        png_path = os.path.join(fonts_dir, f"{name}.png")
        json_path = os.path.join(fonts_dir, f"{name}.json")
        if write_surface_if_changed(atlas, png_path):
            updated += 1
        else:
            unchanged += 1
        if write_json_if_changed(metadata, json_path):
            updated += 1
        else:
            unchanged += 1
        results[name] = (png_path, json_path)

    if stats_out is not None:
        stats_out["updated"] = updated
        stats_out["unchanged"] = unchanged
    return results


def render_specimen_sheet(fonts_dir: str, output_path: str = DEFAULT_SPECIMEN_PATH) -> str:
    """Render a visual contact sheet showing all 95 ASCII glyphs and 1x/2x/3x sample lines."""
    from rendering.bitmap_font import BitmapFont

    width, height = 960, 760
    sheet = pygame.Surface((width, height))
    sheet.fill((18, 16, 22))
    y_cursor = 16

    sample_ascii_1 = "".join(PRINTABLE_ASCII[:48])
    sample_ascii_2 = "".join(PRINTABLE_ASCII[48:])
    sample_lore = "The Bleed encroaches -- Hold the margin! HP: 85/100 [1x/2x/3x]"

    for font_name in ("ink_sans", "ink_mono", "manuscript_serif"):
        png_p = os.path.join(fonts_dir, f"{font_name}.png")
        json_p = os.path.join(fonts_dir, f"{font_name}.json")
        header = BitmapFont(png_p, json_p, scale=1)
        lbl = header.render(f"=== {font_name} ===", True, (220, 195, 130))
        sheet.blit(lbl, (16, y_cursor))
        y_cursor += lbl.get_height() + 6

        for scale in (1, 2, 3):
            if font_name == "manuscript_serif" and scale == 3:
                line_text = "THE BLEED"
            else:
                line_text = sample_lore if scale > 1 else sample_ascii_1
            bf = BitmapFont(png_p, json_p, scale=scale)
            s_lbl = bf.render(f"{scale}x: {line_text}", True, (235, 232, 224))
            sheet.blit(s_lbl, (20, y_cursor))
            y_cursor += s_lbl.get_height() + 4
            if scale == 1:
                s_ascii2 = bf.render(f"    {sample_ascii_2}", True, (195, 205, 220))
                sheet.blit(s_ascii2, (20, y_cursor))
                y_cursor += s_ascii2.get_height() + 6
        y_cursor += 12

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pygame.image.save(sheet, output_path)
    return output_path


def main() -> None:
    """CLI entry point for bitmap font generation and optional specimen preview."""
    parser = argparse.ArgumentParser(description="Generate procedural bitmap font atlases.")
    parser.add_argument("--fonts-dir", default=DEFAULT_FONTS_DIR, help="Output font directory.")
    parser.add_argument(
        "--specimen",
        nargs="?",
        const=DEFAULT_SPECIMEN_PATH,
        default=None,
        help="Optional path to save a visual contact sheet (defaults to /tmp preview).",
    )
    args = parser.parse_args()

    if "SDL_VIDEODRIVER" not in os.environ and not pygame.display.get_init():
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()

    stats: Dict[str, int] = {}
    results = generate_all_fonts(fonts_dir=args.fonts_dir, stats_out=stats)
    for name, (png_p, json_p) in results.items():
        print(f"  [+] {name:<18} -> {png_p} + {json_p}")
    print(f"Font generation complete: {stats['updated']} updated, {stats['unchanged']} unchanged.")

    if args.specimen is not None:
        out_spec = render_specimen_sheet(args.fonts_dir, args.specimen)
        print(f"Specimen contact sheet saved to {out_spec}")


if __name__ == "__main__":
    main()
