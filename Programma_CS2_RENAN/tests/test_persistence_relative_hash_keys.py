"""D-43 — the checkpoint hash registry is keyed by the path relative to the
models root, so a models folder that moves (installer, brain-root change)
keeps verifying.  Absolute keys written by older builds still verify.
"""

from __future__ import annotations

import json
import shutil

import torch.nn as nn


def _tiny():
    return nn.Sequential(nn.Linear(4, 2))


def test_save_registers_a_relative_key(tmp_path, monkeypatch):
    from Programma_CS2_RENAN.backend.nn import persistence

    monkeypatch.setattr(persistence, "BASE_NN_DIR", tmp_path / "models")
    persistence.save_nn(_tiny(), "tiny-rel")

    registry = json.loads((tmp_path / "models" / "checkpoint_hashes.json").read_text())
    assert list(registry) == ["global/tiny-rel.pt"]


def test_a_moved_models_folder_still_verifies(tmp_path, monkeypatch):
    from Programma_CS2_RENAN.backend.nn import persistence

    monkeypatch.setattr(persistence, "BASE_NN_DIR", tmp_path / "a")
    persistence.save_nn(_tiny(), "tiny-move")
    shutil.copytree(tmp_path / "a", tmp_path / "b")

    monkeypatch.setattr(persistence, "BASE_NN_DIR", tmp_path / "b")
    moved = tmp_path / "b" / "global" / "tiny-move.pt"
    assert persistence._verify_checkpoint_hash(moved) is True
    moved.write_bytes(moved.read_bytes() + b"x")
    assert persistence._verify_checkpoint_hash(moved) is False


def test_legacy_absolute_keys_still_verify(tmp_path, monkeypatch):
    from Programma_CS2_RENAN.backend.nn import persistence

    root = tmp_path / "models"
    (root / "global").mkdir(parents=True)
    monkeypatch.setattr(persistence, "BASE_NN_DIR", root)
    ckpt = root / "global" / "old.pt"
    ckpt.write_bytes(b"weights")
    (root / "checkpoint_hashes.json").write_text(
        json.dumps({str(ckpt): persistence._compute_file_hash(ckpt)})
    )

    assert persistence._verify_checkpoint_hash(ckpt) is True
    ckpt.write_bytes(b"tampered")
    assert persistence._verify_checkpoint_hash(ckpt) is False
