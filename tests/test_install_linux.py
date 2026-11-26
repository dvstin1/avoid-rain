# copyright 2026 Dustin Massop, License: GPLv2
"""Hermetic unit tests for install-linux.py (never touches /usr/share/applications)."""

import importlib.util
import os
import stat


def _load_installer_module():
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "install-linux.py"))
    spec = importlib.util.spec_from_file_location("install_linux", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_install_and_uninstall_desktop_entries_hermetic(tmp_path):
    """Installing to tmp_path emits both windowed and --fullscreen .desktop files, and --uninstall removes them."""
    mod = _load_installer_module()
    dest = tmp_path / "applications"

    rc = mod.main(["--dest", str(dest)])
    assert rc == 0

    windowed_path = dest / "avoid-rain.desktop"
    fullscreen_path = dest / "avoid-rain-fullscreen.desktop"
    assert windowed_path.is_file()
    assert fullscreen_path.is_file()

    # Verify permissions (0o644)
    assert stat.S_IMODE(windowed_path.stat().st_mode) == 0o644
    assert stat.S_IMODE(fullscreen_path.stat().st_mode) == 0o644

    win_text = windowed_path.read_text(encoding="utf-8")
    fs_text = fullscreen_path.read_text(encoding="utf-8")

    for text in (win_text, fs_text):
        assert "[Desktop Entry]" in text
        assert "Type=Application" in text
        assert f"Path={mod.PROJECT_DIR}" in text
        assert "Terminal=false" in text
        assert "Categories=Game;ActionGame;" in text
        assert "Icon=" in text

    assert "Name=Avoid Rain\n" in win_text
    assert "--fullscreen" not in win_text
    assert "Name=Avoid Rain (Fullscreen)\n" in fs_text
    assert "--fullscreen\n" in fs_text

    # Uninstall removes both entries cleanly and is idempotent
    assert mod.main(["--dest", str(dest), "--uninstall"]) == 0
    assert not windowed_path.exists()
    assert not fullscreen_path.exists()
    assert mod.main(["--dest", str(dest), "--uninstall"]) == 0


def test_permission_error_guidance_and_helpers(tmp_path, monkeypatch, capsys):
    """PermissionError prints sudo/--dest guidance and returns 1; quote() and find_python() behave cleanly."""
    mod = _load_installer_module()

    def _deny(*_args, **_kwargs):
        raise PermissionError("Read-only filesystem")

    monkeypatch.setattr(os, "makedirs", _deny)
    rc = mod.main(["--dest", str(tmp_path / "protected")])
    assert rc == 1
    captured = capsys.readouterr()
    assert "Permission denied" in captured.err
    assert "sudo" in captured.err
    assert "--dest" in captured.err

    # Quote escapes backslashes and double quotes for Exec fields
    assert mod.quote('/opt/My "Game"\\bin/python') == '"/opt/My \\"Game\\"\\\\bin/python"'

    # find_python prefers .venv/bin/python when present in PROJECT_DIR
    fake_proj = tmp_path / "proj"
    venv_py = fake_proj / ".venv" / "bin" / "python"
    venv_py.parent.mkdir(parents=True)
    venv_py.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_DIR", str(fake_proj))
    assert mod.find_python() == str(venv_py)

    # find_icon returns an existing asset file in this repository
    icon = mod.find_icon()
    assert icon == "applications-games" or os.path.isfile(icon)
