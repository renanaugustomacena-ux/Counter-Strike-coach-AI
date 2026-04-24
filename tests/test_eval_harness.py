"""GAP-04 tests for tools/eval_harness.py pure helpers + CLI entrypoint.

Integration smoke against the live DB is optional (CS2_INTEGRATION_TESTS=1).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from tools.eval_harness import brier_score
from tools.eval_harness import main as eval_main


def test_brier_perfect_prediction_is_zero():
    y = np.array([1, 0, 1, 0])
    p = np.array([1.0, 0.0, 1.0, 0.0])
    assert brier_score(y, p) == 0.0


def test_brier_random_half_is_quarter():
    y = np.array([1, 0, 1, 0])
    p = np.array([0.5, 0.5, 0.5, 0.5])
    # MSE = mean((0.5-y)^2) = 0.25
    assert brier_score(y, p) == pytest.approx(0.25)


def test_brier_shape_mismatch_raises():
    with pytest.raises(ValueError, match="shape mismatch"):
        brier_score(np.array([1, 0]), np.array([0.5, 0.5, 0.5]))


def test_cli_dry_run_no_demo_produces_valid_json(capsys):
    rc = eval_main(["--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert "meta" in payload and "sections" in payload
    assert payload["sections"]["feature_drift"]["status"] == "SKIPPED"
    # rag_and_purity may be OK or NOT_AVAILABLE depending on DB state; both are valid
    assert payload["sections"]["rag_and_purity"]["status"] in ("OK", "NOT_AVAILABLE", "ERROR")
    assert payload["sections"]["win_prob_calibration"]["status"] == "NOT_AVAILABLE"
    assert payload["sections"]["llm_baseline"]["status"] == "NOT_IMPLEMENTED"


def test_cli_writes_file_when_not_dry_run(tmp_path):
    rc = eval_main(["--report-dir", str(tmp_path)])
    assert rc == 0
    files = list(tmp_path.glob("eval_*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text())
    assert payload["meta"]["baseline"] is False


def test_cli_baseline_flag_persisted(tmp_path):
    rc = eval_main(["--baseline", "--report-dir", str(tmp_path)])
    assert rc == 0
    files = list(tmp_path.glob("eval_*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text())
    assert payload["meta"]["baseline"] is True


def test_cli_custom_k_parsed(tmp_path):
    rc = eval_main(["--k", "1,3,7", "--report-dir", str(tmp_path)])
    assert rc == 0
    files = list(tmp_path.glob("eval_*.json"))
    payload = json.loads(files[0].read_text())
    section = payload["sections"]["rag_and_purity"]
    if section["status"] == "OK":
        assert set(int(k) for k in section["recall_at_k"].keys()) == {1, 3, 7}


@pytest.mark.integration
def test_integration_live_db_produces_report(tmp_path):
    if os.environ.get("CS2_INTEGRATION_TESTS") != "1":
        pytest.skip("Requires CS2_INTEGRATION_TESTS=1 and the real DB")
    rc = eval_main(
        [
            "--demo",
            "astralis-vs-furia-m1-overpass",
            "--baseline",
            "--report-dir",
            str(tmp_path),
        ]
    )
    assert rc == 0
    files = list(tmp_path.glob("eval_*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text())
    for section in ("feature_drift", "rag_and_purity", "win_prob_calibration", "llm_baseline"):
        assert section in payload["sections"]
        assert "status" in payload["sections"][section]
