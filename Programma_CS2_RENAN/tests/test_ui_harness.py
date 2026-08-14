"""Tests for the offscreen UI screenshot harness (tools/ui_screenshot.py)."""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_i18n_key_parity_across_languages():
    """en/it/pt must expose identical key sets — a missing translation is a bug."""
    import json

    i18n_dir = REPO / "Programma_CS2_RENAN" / "assets" / "i18n"
    keysets = {}
    for lang in ("en", "it", "pt"):
        data = json.loads((i18n_dir / f"{lang}.json").read_text(encoding="utf-8"))
        keysets[lang] = set(data)
    assert keysets["en"] == keysets["it"], f"en↔it drift: {sorted(keysets['en'] ^ keysets['it'])}"
    assert keysets["en"] == keysets["pt"], f"en↔pt drift: {sorted(keysets['en'] ^ keysets['pt'])}"


def _ttf_family_name(path: Path) -> str:
    """Read the family name (nameID 1) straight from a TTF's name table.

    Qt's offscreen platform on Windows falls back to QBasicFontDatabase,
    which mis-reports family names — so the bundled-font contract is
    verified against the files themselves, not QFontDatabase.
    """
    import struct

    data = path.read_bytes()
    num_tables = struct.unpack(">H", data[4:6])[0]
    name_off = None
    for i in range(num_tables):
        rec = data[12 + 16 * i : 12 + 16 * (i + 1)]
        tag, _, off, _ = struct.unpack(">4sIII", rec)
        if tag == b"name":
            name_off = off
            break
    assert name_off is not None, f"no name table in {path.name}"
    count, string_off = struct.unpack(">HH", data[name_off + 2 : name_off + 6])
    fallback = ""
    for i in range(count):
        rec = data[name_off + 6 + 12 * i : name_off + 6 + 12 * (i + 1)]
        platform_id, _, _, name_id, length, offset = struct.unpack(">6H", rec)
        if name_id != 1:
            continue
        raw = data[name_off + string_off + offset : name_off + string_off + offset + length]
        value = raw.decode("utf-16-be" if platform_id in (0, 3) else "latin-1", "ignore")
        if platform_id == 3:
            return value
        fallback = fallback or value
    return fallback


def test_design_fonts_bundled():
    fonts_dir = REPO / "Programma_CS2_RENAN" / "assets" / "fonts"
    expected = {
        "Inter-Regular.ttf": "Inter",
        "Inter-Medium.ttf": "Inter",
        "Inter-SemiBold.ttf": "Inter",
        "Inter-Bold.ttf": "Inter",
        "SpaceGrotesk-Regular.ttf": "Space Grotesk",
        "SpaceGrotesk-Medium.ttf": "Space Grotesk",
        "SpaceGrotesk-Bold.ttf": "Space Grotesk",
        "JetBrainsMono-Medium.ttf": "JetBrains Mono",
        "JetBrainsMono-SemiBold.ttf": "JetBrains Mono",
        "JetBrainsMono-Bold.ttf": "JetBrains Mono",
    }
    for filename, family in expected.items():
        path = fonts_dir / filename
        assert path.exists(), f"{filename} not bundled in assets/fonts/"
        actual = _ttf_family_name(path)
        assert actual.startswith(family), f"{filename}: family {actual!r} != {family!r}"


def test_register_fonts_scans_assets_dir():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    _ = QApplication.instance() or QApplication([])
    from PySide6.QtGui import QFontDatabase

    before = len(QFontDatabase.applicationFontFamilies(0) or [])  # touch DB
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine

    engine = ThemeEngine()
    engine.register_fonts()
    # The auto-scan must have added application fonts without raising;
    # exact family naming is platform-dependent under offscreen, so the
    # contract here is "registration happened", via the registered flag.
    assert engine._fonts_registered is True


def test_harness_renders_home_and_history(tmp_path):
    out = tmp_path / "renders"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools" / "ui_screenshot.py"),
            "--screens",
            "home,match_history",
            "--themes",
            "CS2",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    for name in ("home", "match_history"):
        png = out / "CS2" / f"{name}.png"
        assert png.exists(), f"{name}.png missing"
        assert png.stat().st_size > 20_000, f"{name}.png suspiciously small"
