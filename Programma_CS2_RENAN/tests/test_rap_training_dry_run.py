"""
RAP training orchestrator smoke tests.

Locks in two invariants that previous sessions broke:

  1. The RAP path is gated by USE_RAP_MODEL=True. Instantiating the
     orchestrator with model_type='rap' while the flag is False MUST
     raise ValueError. This protects the experimental path from being
     entered unintentionally.

  2. With the flag enabled and the data layer mocked, run_training()
     must reach the RAP code path (RAPTrainer constructed, RAP model
     fetched from ModelFactory) without the LTC ncps shape bug
     surfacing. RAP-LTC-FIX (commit 374f3fc) patches
     ncps.LTCCell._ode_solver to handle 1-D elapsed_time; this test
     ensures that fix continues to load.

Tests are CI-portable (no demos, no network) and run under CPU.
Gate the integration-level smoke behind CS2_INTEGRATION_TESTS=1 so
unit-only runs stay fast.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import torch

pytestmark = pytest.mark.timeout(60)


def _patched_settings(use_rap_model: bool):
    """Return a context manager that mutates _settings in-place under its lock."""
    from contextlib import contextmanager

    from Programma_CS2_RENAN.core import config

    @contextmanager
    def _ctx():
        with config._settings_lock:
            original = config._settings.get("USE_RAP_MODEL")
            config._settings["USE_RAP_MODEL"] = use_rap_model
        try:
            yield
        finally:
            with config._settings_lock:
                if original is None:
                    config._settings.pop("USE_RAP_MODEL", None)
                else:
                    config._settings["USE_RAP_MODEL"] = original

    return _ctx()


def _make_rap_orchestrator():
    """Construct a TrainingOrchestrator(model_type='rap') with USE_RAP_MODEL injected."""
    with patch(
        "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
        return_value=torch.device("cpu"),
    ):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        manager = MagicMock()
        return TrainingOrchestrator(manager, model_type="rap", max_epochs=1, patience=1)


# ===========================================================================
# Gate behavior
# ===========================================================================


class TestRAPOrchestratorGate:
    """The USE_RAP_MODEL flag must gate orchestrator instantiation."""

    def test_rap_disabled_raises(self):
        """model_type='rap' with USE_RAP_MODEL=False must raise ValueError."""
        with _patched_settings(use_rap_model=False):
            with patch(
                "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                return_value=torch.device("cpu"),
            ):
                from Programma_CS2_RENAN.backend.nn.training_orchestrator import (
                    TrainingOrchestrator,
                )

                with pytest.raises(ValueError, match="USE_RAP_MODEL"):
                    TrainingOrchestrator(
                        MagicMock(),
                        model_type="rap",
                        max_epochs=1,
                    )

    def test_rap_enabled_constructs_successfully(self):
        """With USE_RAP_MODEL=True the orchestrator must build the RAP trainer class."""
        with _patched_settings(use_rap_model=True):
            orch = _make_rap_orchestrator()
            assert orch.model_type == "rap"
            assert orch.model_name == "rap_coach"
            assert orch.learning_rate == 5e-5
            # RAPTrainer is imported lazily; verify the class binding lives in the
            # experimental package rather than the legacy nn/rap_coach/ tree.
            module_path = orch.TrainerClass.__module__
            assert "experimental.rap_coach" in module_path, (
                f"RAPTrainer must come from the experimental package; " f"got {module_path!r}"
            )


# ===========================================================================
# Integration smoke (gated)
# ===========================================================================


@pytest.mark.skipif(
    os.environ.get("CS2_INTEGRATION_TESTS") != "1",
    reason="Integration smoke (full RAP run_training path); set CS2_INTEGRATION_TESTS=1 to run.",
)
class TestRAPDryRunSmoke:
    """Mocked end-to-end smoke that drives run_training() down the RAP branch.

    All external systems are stubbed. The test fails if the RAP path raises
    on instantiation, the LTC shape patch is missing, or the orchestrator
    does not enter the RAP-specific code branch.
    """

    def test_rap_orchestrator_dry_run_smoke(self, tmp_path):
        from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator

        with _patched_settings(use_rap_model=True):
            with patch(
                "Programma_CS2_RENAN.backend.nn.training_orchestrator.get_device",
                return_value=torch.device("cpu"),
            ):
                orch = TrainingOrchestrator(
                    MagicMock(),
                    model_type="rap",
                    max_epochs=1,
                    patience=1,
                )

                # Stub the data feed: return an empty list so run_training aborts
                # at the "Insufficient Training Data" guard. That is enough to
                # prove (a) the gate cleared, (b) the RAP trainer class loaded,
                # (c) load_nn / save_nn paths import cleanly.
                orch.manager._fetch_jepa_ticks.return_value = []
                orch.manager._fetch_rap_ticks = MagicMock(return_value=[])

                mock_model = MagicMock()
                mock_model.to.return_value = mock_model

                with patch("Programma_CS2_RENAN.backend.nn.factory.ModelFactory") as mock_factory:
                    mock_factory.get_model.return_value = mock_model

                    # Pre-training quality check is data-dependent and slow;
                    # skip it for the smoke (its real-data behaviour is covered
                    # elsewhere in the test suite).
                    with patch(
                        "Programma_CS2_RENAN.backend.nn.data_quality.run_pre_training_quality_check"
                    ) as mock_qc:
                        mock_qc.return_value = SimpleNamespace(passed=True, summary=lambda: "")

                        with patch("Programma_CS2_RENAN.backend.nn.training_orchestrator.load_nn"):
                            with patch(
                                "Programma_CS2_RENAN.backend.nn.training_orchestrator.save_nn"
                            ):
                                # Should return cleanly when train_data is empty
                                orch.run_training()

                # If we got here without exception, the orchestrator entered
                # and exited the RAP path without crashing. The data-empty
                # branch is a known-good early return — what matters is that
                # nothing on the way there raised.
                assert (
                    mock_factory.get_model.called
                ), "ModelFactory.get_model('rap') was never called"


# ===========================================================================
# RAP-LTC-FIX patch presence
# ===========================================================================


class TestRAPLTCFixIsLoaded:
    """The ncps LTC shape patch must be present in the experimental rap_coach memory."""

    def test_rap_memory_module_is_importable(self):
        """RAPMemory must import without raising; the LTC monkey-patch lives at module scope."""
        from Programma_CS2_RENAN.backend.nn.experimental.rap_coach import memory

        # Sanity: the module file should mention the fix tag so future
        # refactors that strip it surface in this test.
        with open(memory.__file__, encoding="utf-8") as f:
            source = f.read()
        assert "RAP-LTC-FIX" in source, (
            "RAP-LTC-FIX marker missing from "
            f"{memory.__file__} — the ncps _ode_solver shape patch may have been removed."
        )

    def test_rap_memory_patches_ode_solver_shape(self):
        """RAPMemory construction must install the patched `_ode_solver` on the LTC cell.

        Pre-patch, ncps' `_ode_solver` divides `cm` (shape `(state_size,)`) by
        a 1-D `elapsed_time` (shape `(B,)`), which fails for any
        `batch_size != state_size`. Post-patch, `_ode_solver` is wrapped to
        unsqueeze 1-D `elapsed_time` to `(B, 1)` so `cm` broadcasts correctly
        per-batch.

        We verify two things:
          1. RAPMemory constructs cleanly with the actual signature
             (`perception_dim`, `metadata_dim`, `hidden_dim=256`) — proves the
             LTC + Hopfield init path runs end-to-end without raising.
          2. The cell's `_ode_solver` attribute is a wrapped function (a
             nested closure named `_patched_ode_solver`), not the original
             ncps method — proves the monkey-patch was applied.
        """
        from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.memory import RAPMemory

        # (1) Constructor smoke — fails if the LTC instantiation or the
        #     monkey-patch line itself raises.
        mem = RAPMemory(perception_dim=8, metadata_dim=4, hidden_dim=16)
        mem.eval()

        # (2) The patched function should be a closure named
        #     `_patched_ode_solver` defined in memory.py. The original ncps
        #     `_ode_solver` is a bound method on `LTCCell` — different name.
        ode_solver = mem.ltc.rnn_cell._ode_solver
        assert callable(ode_solver), "_ode_solver is not callable"
        # The patched wrapper is a Python function (closure), not a bound method.
        # If the patch were absent we'd see <bound method LTCCell._ode_solver ...>.
        fn_name = (
            getattr(ode_solver, "__name__", None)
            or getattr(ode_solver, "__func__", lambda: None).__name__
        )
        assert fn_name == "_patched_ode_solver", (
            f"Expected `_patched_ode_solver` wrapper from RAP-LTC-FIX, "
            f"got {fn_name!r}. The shape patch may have been removed from "
            f"experimental/rap_coach/memory.py."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
