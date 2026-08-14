"""W3 (CP0 #6) regression: reset_pro_data is DRY-RUN by default — bare
invocation prints the plan and deletes NOTHING (it destroys more than
the gold-standard wipe, so it now shares its safety generation)."""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_bare_invocation_is_dry_run():
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "reset_pro_data.py")],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 0
    assert "DRY-RUN" in proc.stdout
    assert "--execute" in proc.stdout


def test_execute_flag_exists_and_gates():
    src = (REPO_ROOT / "tools" / "reset_pro_data.py").read_text(encoding="utf-8")
    assert '"--execute"' in src
    assert "_backup_main_db_first" in src
