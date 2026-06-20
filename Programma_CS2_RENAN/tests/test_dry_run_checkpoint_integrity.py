"""B4: `--dry-run` must not overwrite model checkpoints (real, mock-free).

These tests run the actual training entry point (`run_full_training_cycle.py`)
as a subprocess against the real in-project monolith ``database.db`` (429M
``PlayerTickState`` rows — the JEPA source). The real ``models/`` directory is
never touched: ``BRAIN_DATA_ROOT`` is redirected to a temp dir, so every
checkpoint write lands in ``tmp_path`` instead of the production checkpoints.

Both directions are asserted so neither can silently regress:
  * ``--dry-run``  → **no** checkpoint ``.pt`` appears (the Law-7 guard).
  * real ``--epochs 1`` → a checkpoint ``.pt`` **does** appear (guards the
    inverse: an edit that disabled saving for real runs would otherwise train
    for GPU-days writing nothing and still pass the dry-run assertion).

No mocks: the real entry point, real orchestrator, real ``save_nn``, real
filesystem. Gated behind ``CS2_INTEGRATION_TESTS=1`` (see ``conftest.py``)
because it reads the production monolith DB.

Scope note: a dry-run still commits dataset-split labels to the monolith via
``assign_dataset_splits`` — these tests assert only that *model checkpoints*
are not written, which is exactly the guarantee the code makes.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# .../Counter-Strike-coach-AI-main (where run_full_training_cycle.py lives)
REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRY = "run_full_training_cycle.py"


def _run_training(tmp_models_root: Path, *extra_args: str) -> subprocess.CompletedProcess:
    """Invoke the real training entry with checkpoints redirected to a temp dir."""
    env = dict(os.environ)
    # BRAIN_DATA_ROOT is one of the four env-overridable path keys (core/config.py);
    # it relocates USER_DATA_ROOT → MODELS_DIR so save_nn never touches ./models.
    # The monolith database.db stays in-project (CORE_DB_DIR), so JEPA keeps its data.
    env["BRAIN_DATA_ROOT"] = str(tmp_models_root)
    env["CUDA_VISIBLE_DEVICES"] = ""  # force CPU: tiny subsample, avoid 4GB GPU contention
    cmd = [
        sys.executable,
        ENTRY,
        "--model-type",
        "jepa",
        "--no-tensorboard",
        "--train-samples",
        "128",
        "--val-samples",
        "64",
        *extra_args,
    ]
    return subprocess.run(cmd, cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=900)


def _checkpoints(models_root: Path) -> list:
    return sorted(models_root.glob("**/*.pt"))


@pytest.mark.integration
@pytest.mark.timeout(1000)
def test_dry_run_writes_no_checkpoint(tmp_path):
    models_root = tmp_path / "brain"
    models_root.mkdir()

    proc = _run_training(models_root, "--dry-run")

    assert proc.returncode == 0, (
        f"dry-run exited {proc.returncode}\n--- stdout ---\n{proc.stdout[-3000:]}\n"
        f"--- stderr ---\n{proc.stderr[-3000:]}"
    )
    found = _checkpoints(models_root)
    assert found == [], f"--dry-run must not write any model checkpoint; found: {found}"


@pytest.mark.integration
@pytest.mark.timeout(1000)
def test_real_run_writes_checkpoint(tmp_path):
    models_root = tmp_path / "brain"
    models_root.mkdir()

    proc = _run_training(models_root, "--epochs", "1")

    assert proc.returncode == 0, (
        f"real run exited {proc.returncode}\n--- stdout ---\n{proc.stdout[-3000:]}\n"
        f"--- stderr ---\n{proc.stderr[-3000:]}"
    )
    found = _checkpoints(models_root)
    assert found, "a real --epochs 1 run must write at least one checkpoint (inverse guard)"
