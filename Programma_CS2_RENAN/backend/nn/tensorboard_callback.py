"""
TensorBoard Callback — Layer 2 of the Coach Introspection Observatory.

Logs all training signals to TensorBoard: scalars (loss, LR, sparsity),
histograms (weights, gradients, gate activations, belief vectors),
and custom scalar layouts for organized dashboards.

Usage:
    from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback

    cb = TensorBoardCallback(log_dir="runs/coach_training")
    # ... pass to CallbackRegistry ...
    # Launch: tensorboard --logdir runs/
"""

import os
from typing import Any, Dict, Optional

import torch

from Programma_CS2_RENAN.backend.nn.training_callbacks import TrainingCallback
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.tensorboard")


def resolve_device_tag() -> str:
    """Name the accelerator training actually ran on, not the one requested."""
    if not torch.cuda.is_available():
        return "cpu"
    if getattr(torch.version, "hip", None):
        return "rocm"
    if getattr(torch.version, "cuda", None):
        return "cuda"
    return "cpu"


def _extract_probe_context(batch: Any) -> Optional["torch.Tensor"]:
    """Best-effort context tensor from a heterogeneous probe batch.

    The two training paths hand over different shapes: jepa_train's dataloader
    yields dicts with a "context" key, and TrainingOrchestrator yields a
    PREPARED tensor-batch dict (D-16 — it used to hand over raw ORM rows,
    which this function could not consume, silently killing the embed/*
    telemetry). Returns None when nothing tensor-shaped is found.
    """
    if isinstance(batch, torch.Tensor):
        return batch
    if isinstance(batch, dict):
        for key in ("context", "x", "input"):
            value = batch.get(key)
            if isinstance(value, torch.Tensor):
                return value
        for value in batch.values():
            if isinstance(value, torch.Tensor):
                return value
        return None
    if isinstance(batch, (list, tuple)):
        for value in batch:
            if isinstance(value, torch.Tensor):
                return value
    return None


def build_run_dir(model_type: str) -> str:
    """Return RUNS_DIR/<model_type>/<UTC timestamp>-<device tag>.

    Scoping per run keeps experiments from piling into one directory, and the
    device tag stops a Windows CPU smoke run from being mistaken for a real
    Linux/ROCm run in the dashboard.
    """
    from datetime import datetime, timezone

    from Programma_CS2_RENAN.core.config import RUNS_DIR

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return os.path.join(RUNS_DIR, model_type, f"{stamp}-{resolve_device_tag()}")


try:
    from torch.utils.tensorboard import SummaryWriter

    _TB_AVAILABLE = True
except ImportError:
    SummaryWriter = None  # type: ignore[assignment,misc]
    _TB_AVAILABLE = False
    logger.warning("tensorboard not installed — TensorBoardCallback will be a no-op")


class TensorBoardCallback(TrainingCallback):
    """
    Logs training signals to TensorBoard.

    Scalars logged per epoch:
        loss/train, loss/val, loss/gap (overfitting detector)
        lr/current

    Scalars logged per batch (from trainer outputs):
        RAP: rap/sparsity_ratio, rap/z_axis_error, rap/loss_position
        JEPA: jepa/infonce_loss, jepa/concept_loss, jepa/diversity_loss
        Gate: gates/mean_activation, gates/sparsity, gates/active_ratio

    Histograms logged per epoch:
        params/* — parameter distributions
        grads/* — gradient distributions
        belief/vector — RAP belief state distribution
        concepts/embedding_norms — VL-JEPA concept embedding norms
        gates/activations — SuperpositionLayer gate values
    """

    def __init__(self, log_dir: Optional[str] = None, model_type: str = ""):
        self._active = _TB_AVAILABLE
        self._model_type = model_type
        self._epoch = 0
        self._global_step = 0
        self._warned_unavailable = False
        self._probe_batch: Optional[Any] = None
        self.writer: Optional[Any] = None

        # Stage-4 relocation: default log_dir under the package's RUNS_DIR so
        # TensorBoard events co-locate with models/ instead of spawning a
        # repo-root `runs/` orphan on every train.
        if log_dir is None:
            from Programma_CS2_RENAN.core.config import RUNS_DIR

            log_dir = os.path.join(RUNS_DIR, "coach_training")

        if not self._active and os.environ.get("CS2_TB_STRICT") == "1":
            raise RuntimeError(
                "CS2_TB_STRICT=1 and tensorboard is not installed. "
                "Install it with: pip install tensorboard==2.21.0"
            )

        if self._active:
            self.writer = SummaryWriter(log_dir)
            logger.info("TensorBoard writer initialized: %s", log_dir)

    # ── Lifecycle Hooks ──────────────────────────────────────────────

    def on_train_start(self, model, config: Dict[str, Any]) -> None:
        if not self._active or self.writer is None:
            if not self._warned_unavailable:
                self._warned_unavailable = True
                logger.warning(
                    "TensorBoard unavailable — no metrics will be recorded for "
                    "this run. Install tensorboard==2.21.0, or set "
                    "CS2_TB_STRICT=1 to fail instead of degrading."
                )
            return
        self._model_type = config.get("model_type", self._model_type)
        self._probe_batch = config.get("probe_batch")
        if self._probe_batch is None:
            logger.warning(
                "No probe_batch supplied — collapse metrics (embed/*) will not "
                "be logged for this run."
            )
        elif _extract_probe_context(self._probe_batch) is None:
            # D-16 (26-ORCH-01 spirit — failure telemetry must fail loudly):
            # an unconsumable probe used to disable embed/* SILENTLY; the
            # production orchestrator passed raw ORM rows for months and no
            # run ever logged a collapse metric.
            logger.warning(
                "probe_batch of type %s is unconsumable — collapse metrics "
                "(embed/*) will not be logged for this run.",
                type(self._probe_batch).__name__,
            )
        self._create_custom_layout()

    def on_epoch_start(self, epoch: int) -> None:
        self._epoch = epoch

    def on_batch_end(self, batch_idx: int, loss: float, outputs: Dict[str, Any]) -> None:
        if not self._active or self.writer is None:
            return
        self._global_step += 1
        step = self._global_step

        # Core loss
        self.writer.add_scalar("loss/batch", loss, step)

        # RAP-specific signals
        if "sparsity_ratio" in outputs:
            self.writer.add_scalar("rap/sparsity_ratio", outputs["sparsity_ratio"], step)
        if "z_error" in outputs:
            self.writer.add_scalar("rap/z_axis_error", outputs["z_error"], step)
        if "loss_pos" in outputs:
            self.writer.add_scalar("rap/loss_position", outputs["loss_pos"], step)

        # Gate statistics (from RAP SuperpositionLayer)
        gate_stats = outputs.get("gate_stats", {})
        if gate_stats and "error" not in gate_stats:
            self.writer.add_scalar(
                "gates/mean_activation", gate_stats.get("mean_activation", 0), step
            )
            self.writer.add_scalar("gates/sparsity", gate_stats.get("sparsity", 0), step)
            self.writer.add_scalar("gates/active_ratio", gate_stats.get("active_ratio", 0), step)

        # VL-JEPA signals
        if "infonce_loss" in outputs:
            self.writer.add_scalar("jepa/infonce_loss", outputs["infonce_loss"], step)
        if "concept_loss" in outputs:
            self.writer.add_scalar("jepa/concept_loss", outputs["concept_loss"], step)
        if "diversity_loss" in outputs:
            self.writer.add_scalar("jepa/diversity_loss", outputs["diversity_loss"], step)

    def on_epoch_end(
        self,
        epoch: int,
        train_loss: float,
        val_loss: float,
        model,
        **kwargs,
    ) -> None:
        if not self._active or self.writer is None:
            return

        # ── Epoch Scalars ──
        self.writer.add_scalar("loss/train", train_loss, epoch)
        self.writer.add_scalar("loss/val", val_loss, epoch)
        self.writer.add_scalar("loss/gap", val_loss - train_loss, epoch)

        # Learning rate
        optimizer = kwargs.get("optimizer")
        if optimizer is not None:
            param_groups = getattr(optimizer, "param_groups", None)
            if param_groups is not None:
                for i, pg in enumerate(param_groups):
                    self.writer.add_scalar(f"lr/group_{i}", pg["lr"], epoch)

        # ── Representation health ──
        self._log_collapse_metrics(model, epoch)

        # ── Histograms ──
        self._log_parameter_histograms(model, epoch)
        self._log_belief_histogram(model, epoch)
        self._log_gate_histograms(model, epoch)
        self._log_concept_histograms(model, epoch)

        self.writer.flush()

    def on_train_end(self, model, final_metrics: Dict[str, Any]) -> None:
        if not self._active or self.writer is None:
            return
        for key, val in final_metrics.items():
            if isinstance(val, (int, float)):
                self.writer.add_scalar(f"final/{key}", val, self._epoch)
        self.writer.flush()

    def close(self) -> None:
        if self._active and self.writer is not None:
            self.writer.close()
            logger.info("TensorBoard writer closed")

    # ── Histogram Helpers ────────────────────────────────────────────

    def _log_collapse_metrics(self, model, epoch: int) -> None:
        """Log representation-collapse indicators from the fixed probe batch.

        Silent no-ops here are deliberate and narrow: a model without a
        context_encoder (e.g. RAP) simply has nothing to measure.
        """
        if self.writer is None or self._probe_batch is None:
            return

        encoder = getattr(model, "context_encoder", None)
        if encoder is None:
            return

        context = _extract_probe_context(self._probe_batch)
        if context is None:
            return

        from Programma_CS2_RENAN.backend.nn.collapse_metrics import (
            compute_collapse_metrics,
            compute_ema_drift,
        )

        try:
            with torch.no_grad():
                try:
                    device = next(model.parameters()).device
                except StopIteration:
                    device = torch.device("cpu")
                embeddings = encoder(context.to(device))
        except Exception as exc:
            # A probe the encoder cannot consume is a wiring problem, not a
            # training problem. Say so once, then stop retrying every epoch.
            self._probe_batch = None
            logger.warning(
                "Probe batch is not consumable by context_encoder (%s) — "
                "collapse metrics disabled for this run.",
                exc,
            )
            return

        for name, value in compute_collapse_metrics(embeddings).items():
            self.writer.add_scalar(f"embed/{name}", value, epoch)

        target = getattr(model, "target_encoder", None)
        if target is not None:
            self.writer.add_scalar(
                "embed/ema_drift",
                compute_ema_drift(encoder.parameters(), target.parameters()),
                epoch,
            )

    def _log_parameter_histograms(self, model, epoch: int) -> None:
        """Log parameter and gradient distributions."""
        if self.writer is None:
            return
        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            self.writer.add_histogram(f"params/{name}", param.data, epoch)
            if param.grad is not None:
                self.writer.add_histogram(f"grads/{name}", param.grad, epoch)

    def _log_belief_histogram(self, model, epoch: int) -> None:
        """Log RAP belief vector distribution (64-dim)."""
        if self.writer is None:
            return
        belief = getattr(model, "_last_belief_batch", None)
        if belief is not None and isinstance(belief, torch.Tensor):
            self.writer.add_histogram("belief/vector", belief, epoch)

    def _log_gate_histograms(self, model, epoch: int) -> None:
        """Log SuperpositionLayer gate activation distributions."""
        if self.writer is None:
            return
        strategy = getattr(model, "strategy", None)
        if strategy is None:
            return
        superposition = getattr(strategy, "superposition", None)
        if superposition is None:
            return
        gate_act = getattr(superposition, "get_gate_activations", lambda: None)()
        if gate_act is not None:
            self.writer.add_histogram("gates/activations", gate_act, epoch)

    def _log_concept_histograms(self, model, epoch: int) -> None:
        """Log VL-JEPA concept embedding norms."""
        if self.writer is None:
            return
        concept_embs = getattr(model, "concept_embeddings", None)
        if concept_embs is not None:
            norms = concept_embs.weight.data.norm(dim=1)
            self.writer.add_histogram("concepts/embedding_norms", norms, epoch)

    # ── Custom Layout ────────────────────────────────────────────────

    def _create_custom_layout(self) -> None:
        """Define TensorBoard custom scalar layout for organized dashboards."""
        if self.writer is None:
            return
        layout = {
            "Coach Vital Signs": {
                "Loss": ["Multiline", ["loss/train", "loss/val", "loss/gap"]],
                # NOTE (F3-35): lr/group_0 hardcoded — models with multiple param groups
                # would also have lr/group_1, lr/group_2, etc. that won't appear here.
                "Learning Rate": ["Multiline", ["lr/group_0"]],
            },
            "RAP Coach Internals": {
                "Sparsity": ["Multiline", ["rap/sparsity_ratio"]],
                "Positioning": ["Multiline", ["rap/z_axis_error", "rap/loss_position"]],
            },
            "JEPA Self-Supervised": {
                "Losses": [
                    "Multiline",
                    [
                        "jepa/infonce_loss",
                        "jepa/concept_loss",
                        "jepa/diversity_loss",
                    ],
                ],
            },
            "Superposition Gates": {
                "Gate Dynamics": [
                    "Multiline",
                    [
                        "gates/mean_activation",
                        "gates/sparsity",
                        "gates/active_ratio",
                    ],
                ],
            },
        }
        self.writer.add_custom_scalars(layout)
