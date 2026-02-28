from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.nn.superposition")


class SuperpositionLayer(nn.Module):
    """
    Introduces Superposition into the MLP.
    Allows the model to learn multiple 'modes' (e.g., Standard Coach vs Advanced Brain)
    and dynamically blend them based on a context vector.
    """

    def __init__(self, in_features, out_features, context_dim=METADATA_DIM):
        super(SuperpositionLayer, self).__init__()
        self.weight = nn.Parameter(torch.randn(out_features, in_features))
        self.bias = nn.Parameter(torch.zeros(out_features))

        # Context-dependent gating (Superposition Controller)
        self.context_gate = nn.Linear(context_dim, out_features)

        # Observable state
        self._last_gate_activations: Optional[torch.Tensor] = None
        self._gate_stats_log_interval = 100
        self._forward_count = 0

    def forward(self, x, context):
        """
        Args:
            x: Input tensor [batch, in_features]
            context: Context tensor [batch, context_dim]
        """
        # Generate a gating mask based on match context
        gate = torch.sigmoid(self.context_gate(context))

        # Store for observability
        self._last_gate_activations = gate.detach()
        self._forward_count += 1

        # Periodic gate statistics logging during training
        if self.training and self._forward_count % self._gate_stats_log_interval == 0:
            with torch.no_grad():
                gate_mean = gate.mean(dim=0)
                active_dims = (gate_mean > 0.5).sum().item()
                sparse_dims = (gate_mean < 0.1).sum().item()

                _logger.debug(
                    "SuperpositionGate [step %d]: active=%d/%d, sparse=%d, mean=%.3f",
                    self._forward_count,
                    active_dims,
                    gate.shape[-1],
                    sparse_dims,
                    gate_mean.mean().item(),
                )

        # Apply weights with superposition bias
        out = F.linear(x, self.weight, self.bias)

        # Modulate output by the context gate
        return out * gate

    def get_gate_activations(self) -> Optional[torch.Tensor]:
        """Get the most recent gate activations for analysis."""
        return self._last_gate_activations

    def get_gate_statistics(self) -> Dict[str, float]:
        """Compute summary statistics of gate activations."""
        if self._last_gate_activations is None:
            return {"error": "no_activations_recorded"}

        gate = self._last_gate_activations
        mean = gate.mean(dim=0)

        return {
            "mean_activation": float(mean.mean()),
            "std_activation": float(gate.std()),
            "sparsity": float((mean < 0.1).sum() / mean.shape[0]),
            "active_ratio": float((mean > 0.5).sum() / mean.shape[0]),
            "top_3_dims": mean.topk(min(3, mean.shape[0])).indices.tolist(),
            "bottom_3_dims": mean.topk(min(3, mean.shape[0]), largest=False).indices.tolist(),
        }

    def gate_sparsity_loss(self) -> torch.Tensor:
        """L1 regularization loss on gate activations for expert specialization."""
        if self._last_gate_activations is None:
            return torch.tensor(0.0)
        return self._last_gate_activations.abs().mean()

    def enable_tracing(self, interval: int = 1):
        """Enable verbose gate logging for debugging."""
        self._gate_stats_log_interval = interval

    def disable_tracing(self):
        """Disable verbose gate logging."""
        self._gate_stats_log_interval = 100
