"""Install round (WP4a) — importing observability.rasp never raises in a
frozen build.  The CS2_MANIFEST_KEY fail-closed rule (RP-01) is enforced by
run_rasp_audit, so bundling the module cannot brick startup on its own.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_frozen_import_without_a_manifest_key_succeeds(tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "CS2_MANIFEST_KEY"}
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    code = (
        "import sys; sys.frozen = True; sys._MEIPASS = sys.argv[1]; "
        "import Programma_CS2_RENAN.observability.rasp as r; "
        "print('imported', r._KEY_FROM_ENV)"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip() == "imported False"


def _stub_guard(monkeypatch, rasp, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(rasp.RASPGuard, "check_frozen_binary", lambda self: True)
    monkeypatch.setattr(rasp.RASPGuard, "verify_runtime_integrity", lambda self: (True, []))


def test_audit_fails_closed_in_a_frozen_build_without_the_key(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.observability import rasp

    _stub_guard(monkeypatch, rasp, tmp_path)
    monkeypatch.setattr(rasp, "_KEY_FROM_ENV", False)
    assert rasp.run_rasp_audit(tmp_path) is False


def test_audit_proceeds_when_the_key_came_from_the_environment(monkeypatch, tmp_path):
    from Programma_CS2_RENAN.observability import rasp

    _stub_guard(monkeypatch, rasp, tmp_path)
    monkeypatch.setattr(rasp, "_KEY_FROM_ENV", True)
    assert rasp.run_rasp_audit(tmp_path) is True


def test_dev_import_keeps_the_fallback_key():
    from Programma_CS2_RENAN.observability import rasp

    assert isinstance(rasp._MANIFEST_HMAC_KEY, bytes) and rasp._MANIFEST_HMAC_KEY
