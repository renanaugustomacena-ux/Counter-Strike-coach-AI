"""Packaging round (WP4c) — the build script, the build pipeline and the CI
distribution stage build the Qt app, run the packaged selftest, and never
mention the retired Kivy shell.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _read(rel: str) -> str:
    return (PROJECT_ROOT / rel).read_text(encoding="utf-8", errors="replace")


def test_build_script_builds_the_spec_directly_and_runs_the_selftest():
    bat = _read("scripts/build_production.bat")
    assert "kivymd" not in bat and "kivy" not in bat.lower()
    assert "build_tools.py build" not in bat
    assert "PyInstaller --noconfirm packaging\\cs2_analyzer_win.spec" in bat
    assert "gen_version_iss.py" in bat
    assert "--selftest" in bat
    assert "LOCALAPPDATA" in bat
    assert "icacls" in bat
    assert "windows_installer.iss" in bat


def test_build_pipeline_looks_for_the_spec_under_packaging():
    text = _read("tools/build_pipeline.py")
    assert 'self.project_root / "packaging" / "cs2_analyzer_win.spec"' in text


def test_ci_runs_the_packaged_selftest_after_the_build():
    text = _read(".github/workflows/build.yml")
    build_at = text.index("- name: Build executable")
    selftest_at = text.index("--selftest")
    assert selftest_at > build_at, "the selftest must run after the build"
    assert "selftest_report.json" in text
    upload_at = text.index("- name: Upload distribution artifact")
    assert selftest_at < upload_at, "a failed selftest must stop the artifact upload"


def test_build_checklist_describes_the_qt_build():
    text = _read("packaging/BUILD_CHECKLIST.md")
    assert "layout.kv" not in text
    assert "version.iss" in text
    assert "models/global" in text
    assert "--selftest" in text
    assert re.search(r"Current: \*\*1\.0\.0\*\*", text)


def test_factory_models_folder_says_what_ships():
    text = _read("Programma_CS2_RENAN/models/global/README.txt")
    assert "jepa_v2_encoder.pt" in text
    assert ".pt.meta.json" in text
    assert "ships" in text.lower() or "bundled" in text.lower()
