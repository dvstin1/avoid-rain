# copyright 2026 Dustin Massop, License: GPLv2
"""Regression test ensuring all tracked *.py files start with a valid GPLv2 copyright header."""

import os
import re
import subprocess

COPYRIGHT_RE = re.compile(r"^# copyright \d{4} Dustin Massop, License: GPLv2$")
EXCLUDED_PREFIXES = (".venv/", "__pycache__/", "assets/")


def _get_tracked_python_files():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out = subprocess.check_output(["git", "ls-files", "*.py"], cwd=repo_root, text=True)
    files = []
    for rel in out.splitlines():
        norm = rel.replace("\\", "/")
        if norm.startswith(EXCLUDED_PREFIXES) or "/__pycache__/" in norm:
            continue
        full = os.path.join(repo_root, rel)
        if os.path.isfile(full):
            files.append((norm, full))
    return sorted(files)


def test_all_tracked_python_files_have_gplv2_copyright_header():
    """Every tracked *.py file must have a GPLv2 copyright header on line 1 (or line 2 below a shebang)."""
    tracked = _get_tracked_python_files()
    assert tracked, "Expected tracked *.py files in repository"

    failures = []
    for rel, full_path in tracked:
        with open(full_path, "r", encoding="utf-8") as handle:
            lines = [line.rstrip("\r\n") for line in handle.readlines()[:3]]
        if not lines:
            failures.append(f"{rel}: file is empty (missing copyright header)")
            continue
        if lines[0].startswith("#!"):
            if len(lines) < 2 or not COPYRIGHT_RE.match(lines[1]):
                found = lines[1] if len(lines) >= 2 else "<EOF>"
                failures.append(f"{rel}: expected GPLv2 header on line 2 below shebang, found {found!r}")
        else:
            if not COPYRIGHT_RE.match(lines[0]):
                failures.append(f"{rel}: expected GPLv2 header on line 1, found {lines[0]!r}")

    assert not failures, "Missing or malformed GPLv2 copyright headers:\n" + "\n".join(failures)
