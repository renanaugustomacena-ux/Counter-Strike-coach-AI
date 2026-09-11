"""
Tests for persistence.py — Bug #1: Stale checkpoint handling.

Originally, load_nn() detected architecture mismatches (size mismatch on
load_state_dict) and set model._stale_checkpoint = True, but NO caller in the
entire codebase checked this flag — models silently ran with RANDOM WEIGHTS.

The fix: load_nn() now raises StaleCheckpointError on dimension mismatch,
forcing all callers to handle the error explicitly.

These tests verify:
1. StaleCheckpointError is raised on architecture mismatch
2. Normal loads work correctly (weights match checkpoint)
3. Missing checkpoints return the model unchanged
4. Corrupted checkpoints are handled explicitly
"""

from unittest.mock import patch

import pytest
import torch
import torch.nn as nn


@pytest.fixture
def model_dir(tmp_path):
    """Temporary directory for model checkpoints."""
    d = tmp_path / "models" / "global"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def small_model():
    """A simple model with input_dim=10 for testing dimension mismatches."""
    return nn.Sequential(nn.Linear(10, 5), nn.ReLU(), nn.Linear(5, 2))


@pytest.fixture
def large_model():
    """A simple model with input_dim=25 (production size)."""
    return nn.Sequential(nn.Linear(25, 5), nn.ReLU(), nn.Linear(5, 2))


class TestStaleCheckpointDetection:
    """Verify that load_nn correctly detects architecture mismatches."""

    def test_dimension_mismatch_raises_stale_checkpoint_error(
        self, model_dir, small_model, large_model
    ):
        """When loading a checkpoint saved with different dimensions,
        load_nn must raise StaleCheckpointError."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(StaleCheckpointError, match="is incompatible"):
                load_nn("latest", large_model)

    def test_stale_error_contains_path_info(self, model_dir, small_model, large_model):
        """StaleCheckpointError message must include the checkpoint path for debugging."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(StaleCheckpointError) as exc_info:
                load_nn("latest", large_model)

            assert str(checkpoint_path) in str(
                exc_info.value
            ), "Error message should contain the checkpoint path"

    def test_stale_error_chains_original_runtime_error(self, model_dir, small_model, large_model):
        """StaleCheckpointError must chain the original RuntimeError via __cause__."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(StaleCheckpointError) as exc_info:
                load_nn("latest", large_model)

            assert (
                exc_info.value.__cause__ is not None
            ), "StaleCheckpointError should chain the original RuntimeError"
            assert isinstance(exc_info.value.__cause__, RuntimeError)

    def test_normal_load_succeeds(self, model_dir, small_model):
        """A successful load should return the model with correct weights, no error."""
        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        fresh_model = nn.Sequential(nn.Linear(10, 5), nn.ReLU(), nn.Linear(5, 2))

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            result = load_nn("latest", fresh_model)

        assert not getattr(
            result, "_stale_checkpoint", False
        ), "Successful load should NOT have stale flag"

    def test_model_weights_differ_after_successful_load(self, model_dir, small_model):
        """After a successful load, model weights should match the checkpoint, not be random."""
        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        fresh_model = nn.Sequential(nn.Linear(10, 5), nn.ReLU(), nn.Linear(5, 2))

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            result = load_nn("latest", fresh_model)

        for p_loaded, p_original in zip(result.parameters(), small_model.parameters()):
            assert torch.allclose(
                p_loaded, p_original
            ), "Loaded model weights should match checkpoint"

    def test_no_checkpoint_raises_file_not_found(self, model_dir):
        """When no checkpoint exists, load_nn must raise FileNotFoundError (NN-14)."""
        model = nn.Sequential(nn.Linear(10, 5))

        nonexistent = model_dir / "nonexistent.pt"
        with (
            patch(
                "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
                return_value=nonexistent,
            ),
            patch(
                "Programma_CS2_RENAN.backend.nn.persistence.get_factory_model_path",
                return_value=nonexistent,
            ),
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(FileNotFoundError):
                load_nn("latest", model)


class TestStaleCheckpointPreventsInference:
    """Verify that stale checkpoints cannot be silently used for inference."""

    def test_stale_checkpoint_prevents_silent_usage(self, model_dir, small_model, large_model):
        """load_nn must raise StaleCheckpointError, preventing silent inference
        with random weights. This was Bug #1 — now fixed."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        checkpoint_path = model_dir / "latest.pt"
        torch.save(small_model.state_dict(), checkpoint_path)

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(StaleCheckpointError):
                load_nn("latest", large_model)

    def test_stale_error_is_runtime_error_subclass(self):
        """StaleCheckpointError should be a RuntimeError subclass so existing
        except RuntimeError handlers still catch it when appropriate."""
        from Programma_CS2_RENAN.backend.nn.persistence import StaleCheckpointError

        assert issubclass(StaleCheckpointError, RuntimeError)


class TestCorruptedCheckpoints:
    """Verify handling of corrupted or invalid checkpoint files."""

    def test_corrupted_file_raises(self, model_dir):
        """A corrupted checkpoint file must raise — production re-raises (NN-14)."""
        checkpoint_path = model_dir / "latest.pt"
        checkpoint_path.write_bytes(b"not a valid pytorch checkpoint")

        model = nn.Sequential(nn.Linear(10, 5))

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(Exception):
                load_nn("latest", model)

    def test_empty_file_raises(self, model_dir):
        """An empty checkpoint file must raise — production re-raises (NN-14)."""
        checkpoint_path = model_dir / "latest.pt"
        checkpoint_path.write_bytes(b"")

        model = nn.Sequential(nn.Linear(10, 5))

        with patch(
            "Programma_CS2_RENAN.backend.nn.persistence.get_model_path",
            return_value=checkpoint_path,
        ):
            from Programma_CS2_RENAN.backend.nn.persistence import load_nn

            with pytest.raises(Exception):
                load_nn("latest", model)


class TestV2SidecarValidation:
    """§2.3 / D-09: sidecar v2 fingerprint, numeric_dim, vocab_sizes checks."""

    @pytest.fixture
    def isolated_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("Programma_CS2_RENAN.backend.nn.persistence.BASE_NN_DIR", tmp_path)
        (tmp_path / "global").mkdir()
        return tmp_path

    @pytest.fixture
    def tiny_model(self):
        return nn.Sequential(nn.Linear(4, 2))

    def _running_meta(self):
        return {
            "schema_fingerprint": "abc123",
            "numeric_dim": 21,
            "categorical_vocab_sizes": [10, 8, 3],
        }

    def _v2_sidecar(self, **overrides):
        base = {
            "schema_version": "v2",
            "schema_id": "cs2_v2",
            "schema_fingerprint": "abc123",
            "numeric_dim": 21,
            "categorical_vocab_sizes": [10, 8, 3],
            "extra": {},
        }
        base.update(overrides)
        return base

    def _save_with_v2_sidecar(self, isolated_dir, tiny_model, sidecar_dict):
        import json

        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        path = persistence.get_model_path("v2test")
        torch.save(tiny_model.state_dict(), path)
        sp = persistence._sidecar_path(path)
        sp.write_text(json.dumps(sidecar_dict))
        persistence._register_checkpoint_hash(path)

    def test_v2_fingerprint_mismatch_raises(self, isolated_dir, tiny_model, monkeypatch):
        """§2.3: checkpoint with wrong fingerprint → SchemaMismatchError."""
        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        monkeypatch.setattr(persistence, "_current_schema_meta", lambda: self._running_meta())
        self._save_with_v2_sidecar(
            isolated_dir,
            tiny_model,
            self._v2_sidecar(schema_fingerprint="OLD_FP"),
        )
        fresh = nn.Sequential(nn.Linear(4, 2))
        with pytest.raises(persistence.SchemaMismatchError, match="schema_fingerprint"):
            persistence.load_nn("v2test", fresh)

    def test_v2_numeric_dim_mismatch_raises(self, isolated_dir, tiny_model, monkeypatch):
        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        monkeypatch.setattr(persistence, "_current_schema_meta", lambda: self._running_meta())
        self._save_with_v2_sidecar(isolated_dir, tiny_model, self._v2_sidecar(numeric_dim=25))
        fresh = nn.Sequential(nn.Linear(4, 2))
        with pytest.raises(persistence.SchemaMismatchError, match="numeric_dim"):
            persistence.load_nn("v2test", fresh)

    def test_v2_vocab_mismatch_raises(self, isolated_dir, tiny_model, monkeypatch):
        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        monkeypatch.setattr(persistence, "_current_schema_meta", lambda: self._running_meta())
        self._save_with_v2_sidecar(
            isolated_dir,
            tiny_model,
            self._v2_sidecar(categorical_vocab_sizes=[10, 9, 3]),
        )
        fresh = nn.Sequential(nn.Linear(4, 2))
        with pytest.raises(persistence.SchemaMismatchError, match="categorical_vocab_sizes"):
            persistence.load_nn("v2test", fresh)

    def test_v2_valid_sidecar_loads(self, isolated_dir, tiny_model, monkeypatch):
        """Matching v2 sidecar → load succeeds."""
        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        monkeypatch.setattr(persistence, "_current_schema_meta", lambda: self._running_meta())
        self._save_with_v2_sidecar(isolated_dir, tiny_model, self._v2_sidecar())
        fresh = nn.Sequential(nn.Linear(4, 2))
        result = persistence.load_nn("v2test", fresh)
        for p_loaded, p_orig in zip(result.parameters(), tiny_model.parameters()):
            assert torch.allclose(p_loaded, p_orig)

    def test_v2_vocab_tuple_vs_list(self, isolated_dir, tiny_model, monkeypatch):
        """JSON round-trips lists; running schema may expose tuples."""
        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        running = self._running_meta()
        running["categorical_vocab_sizes"] = (10, 8, 3)
        monkeypatch.setattr(persistence, "_current_schema_meta", lambda: running)
        self._save_with_v2_sidecar(isolated_dir, tiny_model, self._v2_sidecar())
        fresh = nn.Sequential(nn.Linear(4, 2))
        result = persistence.load_nn("v2test", fresh)
        assert result is not None

    def test_schema_mismatch_is_stale_subclass(self):
        from Programma_CS2_RENAN.backend.nn.persistence import (
            SchemaMismatchError,
            StaleCheckpointError,
        )

        assert issubclass(SchemaMismatchError, StaleCheckpointError)

    def test_missing_schema_v2_module_raises(self, isolated_dir, tiny_model, monkeypatch):
        """When schema_v2 is not importable, SchemaMismatchError is raised."""
        import sys

        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        monkeypatch.setitem(
            sys.modules,
            "Programma_CS2_RENAN.backend.processing.feature_engineering.schema_v2",
            None,
        )
        self._save_with_v2_sidecar(isolated_dir, tiny_model, self._v2_sidecar())
        fresh = nn.Sequential(nn.Linear(4, 2))
        with pytest.raises(persistence.SchemaMismatchError, match="not available"):
            persistence.load_nn("v2test", fresh)

    def test_save_nn_with_schema_meta(self, isolated_dir, tiny_model):
        """save_nn(schema_meta=...) writes v2 envelope, skips _build_current_meta."""
        import json

        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        schema_meta = self._v2_sidecar()
        del schema_meta["extra"]
        persistence.save_nn(
            tiny_model,
            "v2save",
            extra_meta={"step": 100},
            schema_meta=schema_meta,
        )
        sp = persistence._sidecar_path(persistence.get_model_path("v2save"))
        data = json.loads(sp.read_text())
        assert data["schema_version"] == "v2"
        assert data["extra"] == {"step": 100}
        assert "metadata_dim" not in data
        assert "feature_names" not in data

    def test_save_nn_without_schema_meta_unchanged(self, isolated_dir, tiny_model):
        """save_nn() without schema_meta still writes v1 sidecar."""
        import json

        import Programma_CS2_RENAN.backend.nn.persistence as persistence

        persistence.save_nn(tiny_model, "v1save")
        sp = persistence._sidecar_path(persistence.get_model_path("v1save"))
        data = json.loads(sp.read_text())
        assert data["schema_version"] == "v1"
        assert "metadata_dim" in data
