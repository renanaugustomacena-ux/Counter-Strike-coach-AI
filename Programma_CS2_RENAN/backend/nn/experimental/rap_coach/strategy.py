from typing import cast

import torch
import torch.nn as nn
import torch.nn.functional as F

from Programma_CS2_RENAN.backend.nn.layers.superposition import SuperpositionLayer
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.experimental.rap_coach.strategy")


class RAPStrategy(nn.Module):
    """
    Decision Optimization Layer with Top-2 Sparse MoE Routing.

    RAP-AUDIT-08: Upgraded from dense softmax routing (all experts always active)
    to Top-2 sparse routing per Shazeer et al. (ICLR 2017) / Fedus et al. (JMLR 2021).
    Only the 2 highest-scoring experts execute for each input, promoting specialization:
    - Experts only receive gradients from inputs they're selected for
    - Prevents convergence to identical functions (averaging behavior)
    - Reduces forward-pass compute by 50% (2/4 experts instead of 4/4)

    Gate outputs raw logits (no softmax); Top-2 indices select which experts to run;
    selected logits are softmax-normalized for weighted combination.
    """

    # Top-K routing parameter
    TOP_K = 2

    def __init__(self, hidden_dim, output_dim, context_dim=METADATA_DIM, num_experts=4):
        super().__init__()
        self.num_experts = num_experts
        self.experts = nn.ModuleList(
            [self._create_expert(hidden_dim, output_dim, context_dim) for _ in range(num_experts)]
        )
        # RAP-AUDIT-08: Raw logits (NO softmax) — top-k selects, then local softmax
        self.gate = nn.Linear(hidden_dim, num_experts)

    def _create_expert(self, hidden_dim, output_dim, context_dim):
        # First layer is Superposition (FiLM-conditioned), adaptable to context
        return nn.ModuleDict(
            {
                "super": SuperpositionLayer(hidden_dim, hidden_dim // 2, context_dim),
                "activation": nn.ReLU(),
                "final": nn.Linear(hidden_dim // 2, output_dim),
            }
        )

    def forward(self, hidden_state, context):
        """
        Args:
            hidden_state: [batch, hidden_dim]
            context: [batch, context_dim] for Superposition

        Returns:
            final_output: [batch, output_dim] — weighted combination of top-2 experts
            gate_probs: [batch, num_experts] — full softmax probabilities (for sparsity loss)
        """
        # Raw gate logits → full softmax for loss computation (entropy regularization)
        gate_logits = self.gate(hidden_state)  # [B, num_experts]
        gate_probs = F.softmax(gate_logits, dim=-1)  # [B, num_experts]

        # Top-K selection: pick the 2 highest-probability experts per sample
        top_k_probs, top_k_indices = torch.topk(gate_probs, self.TOP_K, dim=-1)  # [B, 2]

        # Renormalize selected expert weights to sum to 1
        top_k_weights = top_k_probs / (top_k_probs.sum(dim=-1, keepdim=True) + 1e-8)  # [B, 2]

        # Execute ONLY selected experts (not all 4)
        batch_size = hidden_state.shape[0]
        first_expert = cast(nn.ModuleDict, self.experts[0])
        output_dim = cast(nn.Linear, first_expert["final"]).out_features
        final_output = torch.zeros(batch_size, output_dim, device=hidden_state.device)

        # Determine which experts are needed across the batch
        unique_experts = top_k_indices.unique()
        expert_outputs_cache = {}

        for expert_idx in unique_experts:
            expert_idx_val = int(expert_idx.item())
            expert = cast(nn.ModuleDict, self.experts[expert_idx_val])
            # Find which batch samples need this expert
            mask = (top_k_indices == expert_idx_val).any(dim=-1)  # [B] bool
            if not mask.any():
                continue

            # Run expert only on relevant samples
            h_subset = hidden_state[mask]
            c_subset = context[mask]
            x = expert["super"](h_subset, c_subset)
            x = expert["activation"](x)
            x = expert["final"](x)
            expert_outputs_cache[expert_idx_val] = (mask, x)

        # Combine top-K expert outputs with normalized weights
        for k in range(self.TOP_K):
            expert_indices = top_k_indices[:, k]  # [B]
            weights = top_k_weights[:, k].unsqueeze(-1)  # [B, 1]

            for expert_idx_val, (mask, expert_out) in expert_outputs_cache.items():
                # Which samples selected this expert at position k?
                selected = (expert_indices == expert_idx_val) & mask
                if not selected.any():
                    continue
                # Map back: expert_out has shape [num_mask_true, output_dim]
                # We need to index into it for the selected samples
                mask_indices = torch.where(mask)[0]
                selected_in_mask = torch.isin(mask_indices, torch.where(selected)[0])
                if selected_in_mask.any():
                    final_output[selected] += weights[selected] * expert_out[selected_in_mask]

        # Return full gate_probs for entropy-based sparsity loss (RAP-AUDIT-04)
        return final_output, gate_probs
