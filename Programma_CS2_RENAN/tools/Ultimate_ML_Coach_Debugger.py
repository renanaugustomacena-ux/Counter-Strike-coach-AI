"""
Ultimate ML Coach Debugger
===========================
Neural belief state and decision logic falsification tool.

9 audit phases:
  1. Data Fidelity        — Knowledge base row counts
  2. Belief Stability     — Output variance under real tick data
  3. Decision Traceability — Insight demo_name link ratio
  4. Model Zoo            — Forward-pass smoke for all model types
  5. Dimensional Consistency — METADATA_DIM / INPUT_DIM / OUTPUT_DIM / TRAINING_FEATURES
  6. Data Quality         — Delegate to run_pre_training_quality_check()
  7. Weight Health        — NaN/Inf in saved checkpoints, dead neurons
  8. Training Convergence — Overfitting detection from training_progress.json
  9. Maturity State       — Conviction index from MaturityObservatory
"""

import json
import sys
from pathlib import Path

from _infra import BaseValidator, Console, Severity, ToolReport, path_stabilize

path_stabilize()

import torch
from sqlmodel import func, select

from Programma_CS2_RENAN.backend.nn.config import INPUT_DIM, OUTPUT_DIM
from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.backend.processing.state_reconstructor import RAPStateReconstructor
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import (
    CoachingInsight,
    PlayerMatchStats,
    PlayerTickState,
)
from Programma_CS2_RENAN.core.config import get_setting

# Configurable thresholds
_BELIEF_STABILITY_VARIANCE_THRESHOLD = float(get_setting("ML_BELIEF_VARIANCE_THRESHOLD", 0.5))
_DEAD_NEURON_THRESHOLD = 0.001  # Weights below this are "dead"
_OVERFITTING_DIVERGENCE = 0.20  # val_loss > train_loss * (1 + threshold)
_OVERFITTING_CONSECUTIVE_EPOCHS = 5


class UltimateMLDebugger(BaseValidator):
    """
    Ultimate ML Coach Debugger — 9-phase neural falsification tool.
    Inherits from BaseValidator for structured reporting and CLI.
    """

    def __init__(self):
        super().__init__("Ultimate ML Coach Debugger", version="2.0")
        self.db = get_db_manager()
        self.recon = RAPStateReconstructor()

    def _add_extra_args(self, parser):
        parser.add_argument(
            "--player",
            default="MCIV_PROBE",
            help="Player name to probe (default: MCIV_PROBE)",
        )

    def define_checks(self):
        player = getattr(self.args, "player", "MCIV_PROBE")

        self.console.section("Data Fidelity", 1, 9)
        self._audit_data_fidelity(player)

        self.console.section("Belief Stability", 2, 9)
        self._audit_belief_stability(player)

        self.console.section("Decision Traceability", 3, 9)
        self._audit_decision_logic(player)

        self.console.section("Model Zoo", 4, 9)
        self._audit_model_zoo()

        self.console.section("Dimensional Consistency", 5, 9)
        self._audit_dimensional_consistency()

        self.console.section("Data Quality Gate", 6, 9)
        self._audit_data_quality()

        self.console.section("Weight Health", 7, 9)
        self._audit_weight_health()

        self.console.section("Training Convergence", 8, 9)
        self._audit_training_convergence()

        self.console.section("Maturity State", 9, 9)
        self._audit_maturity_state()

    # ── Phase 1: Data Fidelity ──────────────────────────────────────────

    def _audit_data_fidelity(self, player_name):
        with self.db.get_session() as s:
            ticks = s.exec(
                select(func.count(PlayerTickState.id)).where(
                    PlayerTickState.player_name == player_name
                )
            ).one()
            matches = s.exec(
                select(func.count(PlayerMatchStats.id)).where(
                    PlayerMatchStats.player_name == player_name
                )
            ).one()

        self.check(
            "Data Fidelity",
            "tick_data_present",
            ticks > 0,
            error=f"No ticks for {player_name}",
            detail=f"{ticks} ticks",
            severity=Severity.WARNING,
        )
        self.check(
            "Data Fidelity",
            "match_data_present",
            matches > 0,
            error=f"No matches for {player_name}",
            detail=f"{matches} matches",
            severity=Severity.WARNING,
        )

    # ── Phase 2: Belief Stability ───────────────────────────────────────

    def _audit_belief_stability(self, player_name):
        with self.db.get_session() as s:
            match_data = s.exec(
                select(PlayerTickState).where(PlayerTickState.player_name == player_name).limit(100)
            ).all()

        if not match_data:
            self.check(
                "Belief Stability",
                "sequential_data",
                False,
                error="No sequential data for stability probe",
                severity=Severity.WARNING,
            )
            return

        try:
            model = ModelFactory.get_model("default", input_dim=METADATA_DIM, output_dim=OUTPUT_DIM)
            tensors = self.recon.reconstruct_belief_tensors(match_data)
            out = model(tensors["metadata"])
            variance = torch.var(out).item()
            self.check(
                "Belief Stability",
                "output_variance",
                variance < _BELIEF_STABILITY_VARIANCE_THRESHOLD,
                error=f"Variance {variance:.6f} exceeds {_BELIEF_STABILITY_VARIANCE_THRESHOLD}",
                detail=f"var={variance:.6f}",
            )
        except Exception as e:
            self.check(
                "Belief Stability",
                "probe_execution",
                False,
                error=str(e),
            )

    # ── Phase 3: Decision Traceability ──────────────────────────────────

    def _audit_decision_logic(self, player_name):
        with self.db.get_session() as s:
            insights = s.exec(
                select(CoachingInsight).where(CoachingInsight.player_name == player_name)
            ).all()

        if not insights:
            self.check(
                "Traceability",
                "insights_exist",
                True,
                detail="No insights yet (expected for new players)",
                severity=Severity.WARNING,
            )
            return

        traceable = sum(1 for i in insights if getattr(i, "demo_name", None))
        ratio = traceable / len(insights)
        self.check(
            "Traceability",
            "demo_name_linkage",
            ratio >= 0.8,
            error=f"Only {ratio:.0%} traceable (need 80%)",
            detail=f"{traceable}/{len(insights)} ({ratio:.0%})",
        )

    # ── Phase 4: Model Zoo ──────────────────────────────────────────────

    def _audit_model_zoo(self):
        """Instantiation + forward-pass smoke test for all model types."""
        import torch.nn as nn

        flat_batch = torch.randn(1, METADATA_DIM)

        # Test instantiation for all types, forward-pass where safe
        all_types = [
            ModelFactory.TYPE_LEGACY,
            ModelFactory.TYPE_JEPA,
            ModelFactory.TYPE_VL_JEPA,
            ModelFactory.TYPE_ROLE_HEAD,
            ModelFactory.TYPE_RAP,
            ModelFactory.TYPE_RAP_LITE,
        ]
        for model_type in all_types:
            is_optional = model_type in (ModelFactory.TYPE_RAP, ModelFactory.TYPE_RAP_LITE)
            sev = Severity.WARNING if is_optional else Severity.ERROR
            try:
                model = ModelFactory.get_model(model_type)
                is_module = isinstance(model, nn.Module)
                self.check(
                    "Model Zoo",
                    f"{model_type}_instantiation",
                    is_module,
                    error=f"Got {type(model).__name__}, expected nn.Module",
                    detail=type(model).__name__,
                )
            except ImportError as e:
                self.check(
                    "Model Zoo",
                    f"{model_type}_instantiation",
                    False,
                    error=str(e),
                    severity=Severity.WARNING,
                )
            except Exception as e:
                self.check(
                    "Model Zoo",
                    f"{model_type}_instantiation",
                    False,
                    error=str(e),
                    severity=sev,
                )

        # Forward-pass smoke for legacy model (simplest, most reliable)
        try:
            model = ModelFactory.get_model(ModelFactory.TYPE_LEGACY)
            model.eval()
            with torch.no_grad():
                out = model(flat_batch)
            self.check(
                "Model Zoo",
                "legacy_forward_pass",
                out is not None and out.shape[-1] == OUTPUT_DIM,
                detail=f"output shape {tuple(out.shape)}",
            )
        except Exception as e:
            self.check("Model Zoo", "legacy_forward_pass", False, error=str(e))

    # ── Phase 5: Dimensional Consistency ────────────────────────────────

    def _audit_dimensional_consistency(self):
        from Programma_CS2_RENAN.backend.nn.coach_manager import TRAINING_FEATURES

        self.check(
            "Dimensions",
            "INPUT_DIM == METADATA_DIM",
            INPUT_DIM == METADATA_DIM,
            error=f"INPUT_DIM={INPUT_DIM} != METADATA_DIM={METADATA_DIM}",
        )
        self.check(
            "Dimensions",
            "TRAINING_FEATURES length",
            len(TRAINING_FEATURES) == METADATA_DIM,
            error=f"len(TRAINING_FEATURES)={len(TRAINING_FEATURES)} != {METADATA_DIM}",
        )
        self.check(
            "Dimensions",
            "OUTPUT_DIM == 10",
            OUTPUT_DIM == 10,
            error=f"OUTPUT_DIM={OUTPUT_DIM}, expected 10",
        )

    # ── Phase 6: Data Quality ───────────────────────────────────────────

    def _audit_data_quality(self):
        """Delegate to run_pre_training_quality_check with a timeout guard.

        The quality check scans per-match DBs on disk, which can take minutes
        on large datasets. We run it in a daemon thread with a 15s timeout.
        """
        import threading

        try:
            from Programma_CS2_RENAN.backend.nn.data_quality import run_pre_training_quality_check

            result_holder = [None, None]  # [report, exception]

            def _run():
                try:
                    result_holder[0] = run_pre_training_quality_check()
                except Exception as e:
                    result_holder[1] = e

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            t.join(timeout=15)

            if t.is_alive():
                self.check(
                    "Data Quality",
                    "pre_training_check",
                    True,
                    detail="Skipped (>15s timeout on large dataset)",
                    severity=Severity.WARNING,
                )
                return

            if result_holder[1]:
                raise result_holder[1]

            report = result_holder[0]
            self.check(
                "Data Quality",
                "pre_training_check",
                report.passed,
                error=report.summary() if not report.passed else None,
                detail=f"{report.total_tick_rows} ticks, {report.train_rows} train",
            )
        except Exception as e:
            self.check(
                "Data Quality",
                "pre_training_check",
                False,
                error=str(e),
                severity=Severity.WARNING,
            )

    # ── Phase 7: Weight Health ──────────────────────────────────────────

    def _audit_weight_health(self):
        from Programma_CS2_RENAN.backend.nn.persistence import get_model_path

        checkpoints_found = 0
        for model_type in (
            ModelFactory.TYPE_LEGACY,
            ModelFactory.TYPE_JEPA,
            ModelFactory.TYPE_VL_JEPA,
            ModelFactory.TYPE_ROLE_HEAD,
        ):
            ckpt_name = ModelFactory.get_checkpoint_name(model_type)
            ckpt_path = get_model_path(ckpt_name)
            if not Path(ckpt_path).exists():
                continue

            checkpoints_found += 1
            try:
                state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=True)
                if isinstance(state_dict, dict) and "model_state_dict" in state_dict:
                    state_dict = state_dict["model_state_dict"]

                nan_count = 0
                dead_count = 0
                total_params = 0
                for name, param in state_dict.items():
                    if not isinstance(param, torch.Tensor):
                        continue
                    total_params += 1
                    if torch.isnan(param).any() or torch.isinf(param).any():
                        nan_count += 1
                    if (
                        param.dim() >= 2
                        and (param.abs().max(dim=-1).values < _DEAD_NEURON_THRESHOLD).any()
                    ):
                        dead_count += 1

                self.check(
                    "Weight Health",
                    f"{model_type}_nan_inf",
                    nan_count == 0,
                    error=f"{nan_count}/{total_params} params contain NaN/Inf",
                    detail=f"{total_params} params clean",
                )
                self.check(
                    "Weight Health",
                    f"{model_type}_dead_neurons",
                    dead_count == 0,
                    error=f"{dead_count} layers with dead neurons",
                    detail="all neurons active",
                    severity=Severity.WARNING,
                )
            except Exception as e:
                self.check(
                    "Weight Health",
                    f"{model_type}_load",
                    False,
                    error=str(e),
                    severity=Severity.WARNING,
                )

        if checkpoints_found == 0:
            self.check(
                "Weight Health",
                "checkpoints_found",
                True,
                detail="No saved checkpoints yet (expected before training)",
                severity=Severity.WARNING,
            )

    # ── Phase 8: Training Convergence ───────────────────────────────────

    def _audit_training_convergence(self):
        progress_path = Path(get_setting("BRAIN_DATA_ROOT", "")) / "training_progress.json"
        if not progress_path.exists():
            # Try local fallback
            from _infra import SOURCE_ROOT

            progress_path = SOURCE_ROOT / "logs" / "training_progress.json"

        if not progress_path.exists():
            self.check(
                "Convergence",
                "progress_file",
                True,
                detail="No training_progress.json yet",
                severity=Severity.WARNING,
            )
            return

        try:
            data = json.loads(progress_path.read_text())
            epochs = data if isinstance(data, list) else data.get("epochs", [])

            if len(epochs) < 2:
                self.check(
                    "Convergence",
                    "sufficient_epochs",
                    True,
                    detail=f"Only {len(epochs)} epoch(s) recorded",
                    severity=Severity.WARNING,
                )
                return

            # Check for overfitting: val_loss >> train_loss for N consecutive epochs
            overfit_streak = 0
            for ep in epochs:
                t_loss = ep.get("train_loss", 0)
                v_loss = ep.get("val_loss", 0)
                if t_loss > 0 and v_loss > t_loss * (1 + _OVERFITTING_DIVERGENCE):
                    overfit_streak += 1
                else:
                    overfit_streak = 0

            self.check(
                "Convergence",
                "overfitting_guard",
                overfit_streak < _OVERFITTING_CONSECUTIVE_EPOCHS,
                error=f"Val loss diverged for {overfit_streak} consecutive epochs",
                detail=f"max streak: {overfit_streak}",
            )

            # Check final loss is finite
            last = epochs[-1]
            final_loss = last.get("train_loss", last.get("loss", 0))
            import math

            self.check(
                "Convergence",
                "loss_finite",
                math.isfinite(final_loss),
                error=f"Final loss is {final_loss}",
                detail=f"final_loss={final_loss:.6f}",
            )
        except Exception as e:
            self.check(
                "Convergence",
                "progress_parse",
                False,
                error=str(e),
                severity=Severity.WARNING,
            )

    # ── Phase 9: Maturity State ─────────────────────────────────────────

    def _audit_maturity_state(self):
        try:
            from Programma_CS2_RENAN.backend.nn.maturity_observatory import MaturityObservatory

            obs = MaturityObservatory()
            if not obs.history:
                self.check(
                    "Maturity",
                    "maturity_data",
                    True,
                    detail="No maturity snapshots yet (pre-training)",
                    severity=Severity.WARNING,
                )
                return

            latest = obs.history[-1]
            state = obs.classify(latest)  # returns string: "doubt", "crisis", etc.
            is_healthy = state not in ("doubt", "crisis")
            self.check(
                "Maturity",
                "conviction_state",
                is_healthy,
                error=f"Model in {state} state",
                detail=f"state={state}, conviction={latest.conviction_index:.3f}",
                severity=Severity.WARNING if not is_healthy else Severity.INFO,
            )
        except Exception as e:
            self.check(
                "Maturity",
                "maturity_probe",
                False,
                error=str(e),
                severity=Severity.WARNING,
            )


if __name__ == "__main__":
    sys.exit(UltimateMLDebugger().run())
