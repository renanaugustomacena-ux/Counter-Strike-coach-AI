import math
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.nn.superposition")


class SuperpositionLayer(nn.Module):
    """
    FiLM-conditioned Superposition Layer.

    Applies Feature-wise Linear Modulation (Perez et al., AAAI 2018):
        y = gamma(context) * (W·x + b) + beta(context)

    RAP-AUDIT-06: Previous multiplicative-only gating (y = gate * out) could only
    suppress features, never inject new ones. When (W·x+b)_j = 0, the output was
    forced to 0 regardless of context. The additive beta term allows context-driven
    feature injection (e.g., AWP-specific positioning, post-plant behavior).
    Beta weights initialized to zero so the layer starts with its previous behavior
    (pure multiplicative gating) and gradually learns the additive shift.
    """

    def __init__(self, in_features, out_features, context_dim=METADATA_DIM):
        super(SuperpositionLayer, self).__init__()
        # P1-09: Kaiming initialization for proper variance scaling
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
        self.bias = nn.Parameter(torch.zeros(out_features))

        # Context-dependent gating — gamma (multiplicative modulation)
        self.context_gate = nn.Linear(context_dim, out_features)

        # RAP-AUDIT-06: Context-dependent shift — beta (additive modulation)
        # Initialized to zero so the layer starts with pure multiplicative behavior
        # and gradually learns context-driven feature injection via backprop.
        self.context_beta = nn.Linear(context_dim, out_features)
        nn.init.zeros_(self.context_beta.weight)
        nn.init.zeros_(self.context_beta.bias)

        # Observable state
        self._last_gate_activations: Optional[torch.Tensor] = None
        self._last_gate_live: Optional[torch.Tensor] = None
        self._gate_stats_log_interval = 100
        self._forward_count = 0

    def forward(self, x, context):
        """
        Args:
            x: Input tensor [batch, in_features]
            context: Context tensor [batch, context_dim]
        """
        # Generate gamma (multiplicative) and beta (additive) from context
        gamma = torch.sigmoid(self.context_gate(context))
        beta = self.context_beta(context)

        # Store live tensor for sparsity loss (NN-24 fix: must retain grad)
        self._last_gate_live = gamma
        # Detached copy for observability (no grad needed)
        self._last_gate_activations = gamma.detach()
        self._forward_count += 1

        # Periodic gate statistics logging during training
        if self.training and self._forward_count % self._gate_stats_log_interval == 0:
            with torch.no_grad():
                gate_mean = gamma.mean(dim=0)
                active_dims = (gate_mean > 0.5).sum().item()
                sparse_dims = (gate_mean < 0.1).sum().item()

                _logger.debug(
                    "SuperpositionGate [step %d]: active=%d/%d, sparse=%d, mean=%.3f",
                    self._forward_count,
                    active_dims,
                    gamma.shape[-1],
                    sparse_dims,
                    gate_mean.mean().item(),
                )

        # Apply FiLM: y = gamma * (W·x + b) + beta
        out = F.linear(x, self.weight, self.bias)
        return gamma * out + beta

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
        if self._last_gate_live is None:
            return torch.tensor(0.0, device=self.weight.device)
        return self._last_gate_live.abs().mean()

    def enable_tracing(self, interval: int = 1):
        """Enable verbose gate logging for debugging."""
        self._gate_stats_log_interval = interval

    def disable_tracing(self):
        """Disable verbose gate logging."""
        self._gate_stats_log_interval = 100
