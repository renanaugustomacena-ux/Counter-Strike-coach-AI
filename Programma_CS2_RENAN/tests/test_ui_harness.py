"""Tests for the offscreen UI screenshot harness (tools/ui_screenshot.py)."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_harness_renders_home_and_history(tmp_path):
    out = tmp_path / "renders"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools" / "ui_screenshot.py"),
            "--screens", "home,match_history",
            "--themes", "CS2",
            "--out", str(out),
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
