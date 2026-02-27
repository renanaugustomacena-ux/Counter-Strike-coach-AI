import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.nn.rap_coach.memory import RAPMemory
from Programma_CS2_RENAN.backend.nn.rap_coach.pedagogy import CausalAttributor, RAPPedagogy
from Programma_CS2_RENAN.backend.nn.rap_coach.perception import RAPPerception
from Programma_CS2_RENAN.backend.nn.rap_coach.strategy import RAPStrategy
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

# Canonical scale factor for converting normalised position-delta outputs
# (model range ≈ [-1, 1]) to CS2 world-unit displacements.
# MUST be used consistently in both GhostEngine and overlay code. (F3-05)
RAP_POSITION_SCALE = 500.0


class RAPCoachModel(nn.Module):
    """
    Near-Perfect CS2 Machine Learning Coach (Full Integration).
    Layers: Perception, Prediction, Evaluation, Strategy, Memory, Pedagogy.
    """

    def __init__(self, metadata_dim=METADATA_DIM, output_dim=10, heuristic_config=None):
        super().__init__()

        # Resolve L1 sparsity weight from HeuristicConfig or default
        if heuristic_config is not None:
            self.context_gate_l1_weight = heuristic_config.context_gate_l1_weight
        else:
            self.context_gate_l1_weight = 1e-4

        # 1. Perception Layer (70 Conv Layer Budget)
        self.perception = RAPPerception()
        # Perception output dim = 64 (view) + 32 (map) + 32 (motion) = 128
        perception_dim = 128

        # 2. Memory Layer (Recurrent Belief State)
        hidden_dim = 256
        self.memory = RAPMemory(perception_dim, metadata_dim, hidden_dim)

        # 3. Strategy Layer (Decision Optimization)
        self.strategy = RAPStrategy(hidden_dim, output_dim, context_dim=metadata_dim)

        # 4. Pedagogy Layer (Causal Attribution)
        self.pedagogy = RAPPedagogy(hidden_dim)
        self.attributor = CausalAttributor(hidden_dim)

        # 5. Position Head (Optimal Shadow)
        # Predicts delta (dx, dy, dz) from current pos to optimal pos
        self.position_head = nn.Linear(hidden_dim, 3)

    def forward(self, view_frame, map_frame, motion_diff, metadata, skill_vec=None):
        # x metadata shape: (batch, seq_len, metadata_dim)
        batch_size, seq_len, _ = metadata.shape

        # Process Perception per timestep (or sampled)
        # Note: In production, we extract CNN features once per frame
        z_spatial = self.perception(view_frame, map_frame, motion_diff)  # (batch, 128)

        # Expand z_spatial to match seq_len if metadata is a sequence
        z_spatial_seq = z_spatial.unsqueeze(1).repeat(1, seq_len, 1)

        lstm_in = torch.cat([z_spatial_seq, metadata], dim=2)

        # Forward through Recurrent Belief State
        hidden_seq, belief, _ = self.memory(lstm_in)

        # Last hidden state for decision
        last_hidden = hidden_seq[:, -1, :]

        # Strategy Execution
        # We pass the last metadata frame as context for Superposition
        context = metadata[:, -1, :]
        prediction, gate_weights = self.strategy(last_hidden, context)

        # Evaluation (Value function)
        value_v = self.pedagogy(last_hidden, skill_vec)

        # Positioning (Optimal Shadow)
        optimal_pos = self.position_head(last_hidden)  # [Batch, 3]

        # Causal Attribution (Why?)
        attribution = self.attributor.diagnose(last_hidden, optimal_pos)  # [Batch, 5]

        return {
            "advice_probs": prediction,
            "belief_state": belief,
            "value_estimate": value_v,
            "gate_weights": gate_weights,
            "optimal_pos": optimal_pos,
            "attribution": attribution,
        }

    def compute_sparsity_loss(self, gate_weights: torch.Tensor = None) -> torch.Tensor:
        """
        Computes L1 Regularization loss on the Context Gate activations.
        Enforces sparsity (interpretability) in decision making.

        Args:
            gate_weights: Gate weight tensor from the last forward() call.
                Callers should pass out["gate_weights"] explicitly to avoid
                thread-safety issues that arise from caching on self. (F3-07)
        """
        if gate_weights is None:
            return torch.tensor(0.0)

        # L1 Norm: Mean of absolute values
        # We want gate values to be mostly near 0, with few strong activations
        l1_loss = torch.mean(torch.abs(gate_weights))
        return self.context_gate_l1_weight * l1_loss
