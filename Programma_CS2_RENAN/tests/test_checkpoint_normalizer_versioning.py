"""GAP-07 regression tests for persistence sidecar versioning.

Covers:
- save_nn writes `.pt.meta.json` with schema_version, metadata_dim, feature_names, heuristic_config.
- Round-trip: save + load succeeds when sidecar matches current schema.
- Drift: edited metadata_dim in sidecar → StaleCheckpointError on load.
- Drift: edited feature_names in sidecar → StaleCheckpointError on load.
- Legacy: .pt without sidecar → WARN, still loads (backward-compat).
- Corrupt sidecar JSON → StaleCheckpointError (fail-loud, never silent).
- extra_meta round-trips unchanged.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.persistence import (
    StaleCheckpointError,
    _sidecar_path,
    load_nn,
    save_nn,
)


class _Tiny(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(4, 2)


@pytest.fixture
def isolated_models_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("Programma_CS2_RENAN.backend.nn.persistence.BASE_NN_DIR", tmp_path)
    return tmp_path


def test_save_creates_sidecar_with_required_fields(isolated_models_dir):
    model = _Tiny()
    save_nn(model, "tiny-roundtrip")

    pt = isolated_models_dir / "global" / "tiny-roundtrip.pt"
    sidecar = _sidecar_path(pt)
    assert pt.exists()
    assert sidecar.exists(), "GAP-07: .pt.meta.json sidecar missing after save_nn"

    meta = json.loads(sidecar.read_text())
    assert meta["schema_version"] == "v1"
    assert meta["metadata_dim"] == 25
    assert isinstance(meta["feature_names"], list)
    assert len(meta["feature_names"]) == 25
    assert "health_max" in meta["heuristic_config"]


def test_roundtrip_save_then_load_ok(isolated_models_dir):
    save_model = _Tiny()
    save_nn(save_model, "tiny-ok")

    load_model = _Tiny()
    load_nn("tiny-ok", load_model)

    # Weights transferred
    assert torch.equal(save_model.fc.weight, load_model.fc.weight)


def test_load_raises_on_metadata_dim_mismatch(isolated_models_dir):
    save_nn(_Tiny(), "tiny-dim-drift")
    sidecar = _sidecar_path(isolated_models_dir / "global" / "tiny-dim-drift.pt")
    meta = json.loads(sidecar.read_text())
    meta["metadata_dim"] = 26  # tampered
    sidecar.write_text(json.dumps(meta))

    with pytest.raises(StaleCheckpointError, match="metadata_dim"):
        load_nn("tiny-dim-drift", _Tiny())


def test_load_raises_on_feature_names_mismatch(isolated_models_dir):
    save_nn(_Tiny(), "tiny-names-drift")
    sidecar = _sidecar_path(isolated_models_dir / "global" / "tiny-names-drift.pt")
    meta = json.loads(sidecar.read_text())
    meta["feature_names"][0] = "bogus_feature_0"  # tampered
    sidecar.write_text(json.dumps(meta))

    with pytest.raises(StaleCheckpointError, match="feature_names"):
        load_nn("tiny-names-drift", _Tiny())


def test_load_raises_on_schema_version_mismatch(isolated_models_dir):
    save_nn(_Tiny(), "tiny-schema-drift")
    sidecar = _sidecar_path(isolated_models_dir / "global" / "tiny-schema-drift.pt")
    meta = json.loads(sidecar.read_text())
    meta["schema_version"] = "v99"  # tampered
    sidecar.write_text(json.dumps(meta))

    with pytest.raises(StaleCheckpointError, match="schema_version"):
        load_nn("tiny-schema-drift", _Tiny())


def test_load_raises_on_missing_feature_names_in_sidecar(isolated_models_dir):
    save_nn(_Tiny(), "tiny-missing-names")
    sidecar = _sidecar_path(isolated_models_dir / "global" / "tiny-missing-names.pt")
    meta = json.loads(sidecar.read_text())
    del meta["feature_names"]
    sidecar.write_text(json.dumps(meta))

    with pytest.raises(StaleCheckpointError, match="feature_names"):
        load_nn("tiny-missing-names", _Tiny())


def test_load_raises_on_corrupt_sidecar_json(isolated_models_dir):
    save_nn(_Tiny(), "tiny-corrupt-meta")
    sidecar = _sidecar_path(isolated_models_dir / "global" / "tiny-corrupt-meta.pt")
    sidecar.write_text("{not valid json")

    with pytest.raises(StaleCheckpointError, match="cannot parse sidecar"):
        load_nn("tiny-corrupt-meta", _Tiny())


def test_legacy_checkpoint_without_sidecar_warns_and_loads(isolated_models_dir, caplog):
    # Save, then delete sidecar to simulate a pre-GAP-07 checkpoint
    save_nn(_Tiny(), "tiny-legacy")
    sidecar = _sidecar_path(isolated_models_dir / "global" / "tiny-legacy.pt")
    sidecar.unlink()

    # Bridge project logger for caplog (propagate=False otherwise)
    lg = logging.getLogger("cs2analyzer.nn.persistence")
    prior = lg.propagate
    lg.propagate = True
    try:
        caplog.set_level(logging.WARNING, logger="cs2analyzer.nn.persistence")
        load_nn("tiny-legacy", _Tiny())  # must not raise
    finally:
        lg.propagate = prior

    assert any("no metadata sidecar" in rec.message for rec in caplog.records)


def test_extra_meta_round_trips(isolated_models_dir):
    save_nn(_Tiny(), "tiny-extras", extra_meta={"ema_step": 12345, "epoch": 7})

    sidecar = _sidecar_path(isolated_models_dir / "global" / "tiny-extras.pt")
    meta = json.loads(sidecar.read_text())
    assert meta["extra"] == {"ema_step": 12345, "epoch": 7}


def test_save_nn_rolls_back_both_tmp_files_on_failure(isolated_models_dir, monkeypatch):
    """If the sidecar write fails, the checkpoint .pt must also NOT appear in
    its final position — atomicity guarantee across the pair."""
    model = _Tiny()
    # Force json.dumps to raise after torch.save succeeded
    import builtins

    real_dumps = json.dumps

    def _boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr("Programma_CS2_RENAN.backend.nn.persistence.json.dumps", _boom)

    with pytest.raises(OSError):
        save_nn(model, "tiny-rollback")

    pt = isolated_models_dir / "global" / "tiny-rollback.pt"
    sidecar = _sidecar_path(pt)
    assert not pt.exists(), "Checkpoint leaked despite sidecar failure"
    assert not sidecar.exists(), "Sidecar leaked"
    # Temps cleaned up
    assert not pt.with_suffix(".pt.tmp").exists()
