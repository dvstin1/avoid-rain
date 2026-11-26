#!/usr/bin/env python3
# copyright 2026 Dustin Massop, License: GPLv2
"""Install Avoid Rain desktop launcher entries on Linux.

Generates two freedesktop.org entries in /usr/share/applications (run with sudo):
  - avoid-rain.desktop             (windowed)
  - avoid-rain-fullscreen.desktop  (launches with --fullscreen)

Usage:
    sudo python3 install-linux.py
    python3 install-linux.py --dest ~/.local/share/applications   # per-user, no sudo
    sudo python3 install-linux.py --uninstall
"""
import argparse
import os
import sys

DEFAULT_DEST = "/usr/share/applications"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_CANDIDATES = (
    os.path.join(PROJECT_DIR, "assets", "graphics", "icon.png"),
    os.path.join(PROJECT_DIR, "assets", "graphics", "player.png"),
    os.path.join(PROJECT_DIR, "assets", "graphics", "chronicle.png"),
    os.path.join(PROJECT_DIR, "assets", "graphics", "player_hood_s_idle.png"),
)
ENTRIES = (
    ("avoid-rain.desktop", "Avoid Rain", ""),
    ("avoid-rain-fullscreen.desktop", "Avoid Rain (Fullscreen)", " --fullscreen"),
)


def find_python():
    """Prefer the project's virtual environment interpreter, falling back to the current one."""
    for rel in (".venv/bin/python", "venv/bin/python"):
        cand = os.path.join(PROJECT_DIR, rel)
        if os.path.isfile(cand):
            return cand
    return sys.executable


def find_icon():
    """Return the first existing icon path, or a generic themed icon name."""
    for cand in ICON_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    return "applications-games"


def quote(path):
    """Quote a path for a .desktop Exec field."""
    return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_entry(name, extra_args):
    """Return the text of a .desktop file."""
    main_py = os.path.join(PROJECT_DIR, "main.py")
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={name}\n"
        "Comment=Scriptorium Noir action-exploration roguelite\n"
        f"Exec={quote(find_python())} {quote(main_py)}{extra_args}\n"
        f"Path={PROJECT_DIR}\n"
        f"Icon={find_icon()}\n"
        "Terminal=false\n"
        "Categories=Game;ActionGame;\n"
    )


def main(argv=None):
    """Install or remove the desktop entries."""
    parser = argparse.ArgumentParser(description="Install Avoid Rain desktop entries.")
    parser.add_argument("--dest", default=DEFAULT_DEST, help=f"Target directory (default: {DEFAULT_DEST})")
    parser.add_argument("--uninstall", action="store_true", help="Remove the installed desktop entries.")
    args = parser.parse_args(argv)
    dest = os.path.expanduser(args.dest)

    try:
        if args.uninstall:
            for filename, _, _ in ENTRIES:
                path = os.path.join(dest, filename)
                if os.path.exists(path):
                    os.remove(path)
                    print(f"Removed {path}")
            return 0
        os.makedirs(dest, exist_ok=True)
        for filename, name, extra in ENTRIES:
            path = os.path.join(dest, filename)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(build_entry(name, extra))
            os.chmod(path, 0o644)
            print(f"Installed {path}")
    except PermissionError:
        print(f"Permission denied writing to {dest}. Re-run with sudo or use --dest.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
