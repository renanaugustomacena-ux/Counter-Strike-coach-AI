"""F-0044 regression: ONE pytest config, regardless of invocation shape.

A shadow Programma_CS2_RENAN/pytest.ini used to win rootdir resolution
for any invocation scoped under Programma_CS2_RENAN/ — silently dropping
strict-markers and the full marker registry for the most common dev
invocation (single-file runs)."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_shadow_ini_exists():
    assert not (
        REPO_ROOT / "Programma_CS2_RENAN" / "pytest.ini"
    ).exists(), "shadow pytest.ini is back — scoped invocations get a different config"
    assert (REPO_ROOT / "pytest.ini").exists()


def test_scoped_invocation_resolves_root_config():
    """A single-file run under Programma_CS2_RENAN/ must use the ROOT ini."""
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "Programma_CS2_RENAN/tests/test_single_pytest_config.py::test_no_shadow_ini_exists",
            "--collect-only",
            "-p",
            "no:timeout",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    header = proc.stdout
    assert "configfile: pytest.ini" in header, header[:500]
    assert (
        "Programma_CS2_RENAN" not in header.split("configfile:")[0].split("rootdir:")[-1]
    ), "rootdir resolved inside Programma_CS2_RENAN — shadow config in effect"
