import torch
import torch.nn as nn
import torch.optim as optim
from torch.amp import GradScaler, autocast
from torch.optim.lr_scheduler import CosineAnnealingLR

from Programma_CS2_RENAN.backend.nn.experimental.rap_coach.model import RAPCoachModel
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.experimental.rap_coach.trainer")


class RAPTrainer:
    """
    Orchestrates training for the multi-layered RAP-Coach.
    Handles temporal gradients across Perception and Memory layers.
    """

    # NN-58: Loss weights extracted to class-level constants for tuning
    LOSS_WEIGHT_STRATEGY = 1.0
    LOSS_WEIGHT_VALUE = 0.5
    LOSS_WEIGHT_SPARSITY = 1.0
    LOSS_WEIGHT_POSITION = 1.0

    # NN-TR-02b: Z-axis penalty weight for position loss. Verticality errors in CS2
    # are disproportionately impactful (wrong floor = instant death), so Z-axis MSE
    # is penalised 2× relative to X/Y. (Task 2.17.1: Strict verticality enforcement)
    Z_AXIS_PENALTY_WEIGHT = 2.0

    def __init__(self, model: RAPCoachModel, lr=1e-4, t_max=100, accumulation_steps: int = 4):
        self.model = model
        self.optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
        self.criterion_strat = nn.MSELoss()
        self.criterion_val = nn.MSELoss()
        self.criterion_pos = nn.MSELoss()
        self.z_axis_penalty_weight = self.Z_AXIS_PENALTY_WEIGHT
        self._accumulation_steps = accumulation_steps
        self.scheduler = CosineAnnealingLR(self.optimizer, T_max=t_max, eta_min=1e-6)

        dev = next(model.parameters()).device
        self._use_amp = dev.type == "cuda"
        self._scaler = GradScaler("cuda", enabled=self._use_amp)

    def train_step(self, batch, *, step_optimizer: bool = True):
        """Single optimisation step over a temporal window.

        Args:
            batch: tensor dict produced by the orchestrator.
            step_optimizer: when False, accumulate gradients without stepping.
                The orchestrator sets this to implement gradient accumulation.
        """
        dev_type = next(self.model.parameters()).device.type

        with autocast(dev_type, enabled=self._use_amp):
            try:
                outputs = self.model(
                    batch["view"],
                    batch["map"],
                    batch["motion"],
                    batch["metadata"],
                    timespans=batch.get("timespans"),
                )
            except Exception:
                logger.exception("Forward pass failed during train_step")
                raise

            loss_strat = self.criterion_strat(outputs["advice_probs"], batch["target_strat"])

            val_mask = batch.get("val_mask")
            if val_mask is not None and val_mask.any() and not val_mask.all():
                loss_val = self.criterion_val(
                    outputs["value_estimate"][val_mask], batch["target_val"][val_mask]
                )
            elif val_mask is not None and not val_mask.any():
                loss_val = torch.tensor(0.0, device=loss_strat.device)
            else:
                loss_val = self.criterion_val(outputs["value_estimate"], batch["target_val"])

            gate_weights = outputs.get("gate_weights")
            loss_sparsity = self.model.compute_sparsity_loss(gate_weights)

            loss_pos = torch.tensor(0.0, device=loss_strat.device)
            z_error = 0.0
            if "target_pos" in batch:
                loss_pos, z_error = self.compute_position_loss(
                    outputs["optimal_pos"], batch["target_pos"]
                )

            total_loss = (
                self.LOSS_WEIGHT_STRATEGY * loss_strat
                + self.LOSS_WEIGHT_VALUE * loss_val
                + self.LOSS_WEIGHT_SPARSITY * loss_sparsity
                + self.LOSS_WEIGHT_POSITION * loss_pos
            )

        sparsity_ratio = 0.0
        if gate_weights is not None:
            with torch.no_grad():
                sparsity_ratio = (gate_weights.abs() < 0.01).float().mean().item()

        self._scaler.scale(total_loss / self._accumulation_steps).backward()

        if step_optimizer:
            self._scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self._scaler.step(self.optimizer)
            self._scaler.update()
            self.optimizer.zero_grad()
            self._notify_memory_step()

        logger.debug(
            "train_step: loss=%.4f sparsity=%.3f pos_loss=%.4f z_err=%.4f amp=%s",
            total_loss.item(),
            sparsity_ratio,
            loss_pos.item(),
            z_error,
            self._use_amp,
        )

        return {
            "loss": total_loss.item(),
            "sparsity_ratio": sparsity_ratio,
            "loss_pos": loss_pos.item(),
            "z_error": z_error,
        }

    def _optimizer_step(self):
        """Flush accumulated gradients — called by orchestrator at epoch end."""
        self._scaler.unscale_(self.optimizer)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self._scaler.step(self.optimizer)
        self._scaler.update()
        self.optimizer.zero_grad()
        self._notify_memory_step()

    def _notify_memory_step(self):
        """NN-MEM-01 (R4 MED): tell the Hopfield memory a REAL optimizer step
        happened — its activation gate is step-driven, not forward-driven."""
        memory = getattr(self.model, "memory", None)
        if memory is not None and hasattr(memory, "notify_optimizer_step"):
            memory.notify_optimizer_step()

    def compute_position_loss(self, pred_delta, target_delta):
        """
        Computes weighted MSE for position, penalizing Z-axis errors.
        Args:
            pred_delta: (Batch, 3) [dx, dy, dz]
            target_delta: (Batch, 3) [dx, dy, dz]
        Returns:
            weighted_loss, z_error (for logging)
        """
        # Separate components
        diff = pred_delta - target_delta
        squared_diff = diff**2  # (Batch, 3)

        mse_x = squared_diff[:, 0].mean()
        mse_y = squared_diff[:, 1].mean()
        mse_z = squared_diff[:, 2].mean()

        # Apply strict Z-penalty
        weighted_loss = mse_x + mse_y + (self.z_axis_penalty_weight * mse_z)

        return weighted_loss, mse_z.item()
