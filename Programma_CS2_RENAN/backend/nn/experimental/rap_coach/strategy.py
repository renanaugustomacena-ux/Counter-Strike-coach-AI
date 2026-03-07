import torch
import torch.nn as nn
import torch.nn.functional as F

from Programma_CS2_RENAN.backend.nn.layers.superposition import SuperpositionLayer
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.experimental.rap_coach.strategy")


class ContextualAttention(nn.Module):
    """
    Saliency-Weighted Feature Aggregation (CNN Layer 3 foundation).
    Answers "What matters right now?"
    """

    def __init__(self, feature_dim, context_dim):
        super().__init__()
        self.query_net = nn.Linear(context_dim, feature_dim)
        self.key_net = nn.Linear(feature_dim, feature_dim)
        self.scale = feature_dim**-0.5

    def forward(self, features, context):
        # query from LSTM context (Memory layer)
        query = self.query_net(context).unsqueeze(1)
        # key/value from CNN features (Perception layer)
        keys = self.key_net(features)

        attn_weights = torch.bmm(query, keys.transpose(1, 2)) * self.scale
        attn_probs = F.softmax(attn_weights, dim=-1)

        return attn_probs


class RAPStrategy(nn.Module):
    """
    Decision Optimization Layer.
    Uses Mixture of Experts (MoE) formatted with Superposition Layers.
    """

    def __init__(self, hidden_dim, output_dim, context_dim=METADATA_DIM, num_experts=4):
        super().__init__()
        self.experts = nn.ModuleList(
            [self._create_expert(hidden_dim, output_dim, context_dim) for _ in range(num_experts)]
        )
        self.gate = nn.Sequential(nn.Linear(hidden_dim, num_experts), nn.Softmax(dim=-1))

    def _create_expert(self, hidden_dim, output_dim, context_dim):
        # First layer is Superposition, adaptable to context
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
        """
        gate_weights = self.gate(hidden_state)

        # Execute experts with context
        expert_outputs_list = []
        for expert in self.experts:
            x = expert["super"](hidden_state, context)
            x = expert["activation"](x)
            x = expert["final"](x)
            expert_outputs_list.append(x)

        expert_outputs = torch.stack(expert_outputs_list, dim=1)

        # Weight experts by gate
        final_output = torch.sum(expert_outputs * gate_weights.unsqueeze(-1), dim=1)

        return final_output, gate_weights
