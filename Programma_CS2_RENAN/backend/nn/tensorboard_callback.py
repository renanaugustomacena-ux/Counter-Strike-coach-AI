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

from typing import Any, Dict, Optional

import torch

from Programma_CS2_RENAN.backend.nn.training_callbacks import TrainingCallback
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.tensorboard")

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

    def __init__(self, log_dir: str = "runs/coach_training", model_type: str = ""):
        self._active = _TB_AVAILABLE
        self._model_type = model_type
        self._epoch = 0
        self._global_step = 0
        self.writer: Optional[Any] = None

        if self._active:
            self.writer = SummaryWriter(log_dir)
            logger.info("TensorBoard writer initialized: %s", log_dir)

    # ── Lifecycle Hooks ──────────────────────────────────────────────

    def on_train_start(self, model, config: Dict[str, Any]) -> None:
        if not self._active or self.writer is None:
            return
        self._model_type = config.get("model_type", self._model_type)
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
