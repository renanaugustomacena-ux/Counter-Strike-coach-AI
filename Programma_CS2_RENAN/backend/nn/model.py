import json
import os
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import torch
import torch.nn as nn

from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM


@dataclass
class CoachNNConfig:
    """Configuration for AdvancedCoachNN. Centralizes hyperparameters."""

    input_dim: int = METADATA_DIM  # Canonical 25-dim feature vector (METADATA_DIM=25)
    output_dim: int = METADATA_DIM
    hidden_dim: int = 128
    num_experts: int = 3
    num_lstm_layers: int = 2
    dropout: float = 0.2
    use_layer_norm: bool = True


class AdvancedCoachNN(nn.Module):
    """
    Advanced Neural Architecture:
    1. LSTM Sequence Learning with LayerNorm
    2. Mixture of Experts (MoE) specialized heads
    3. SHAP-compatible forward pass
    """

    def __init__(
        self,
        input_dim: int = None,
        output_dim: int = None,
        hidden_dim: int = 128,
        num_experts: int = 3,
        config: Optional[CoachNNConfig] = None,
    ):
        super().__init__()

        # Support both legacy (positional args) and new (config) initialization
        if config is not None:
            input_dim = config.input_dim
            output_dim = config.output_dim
            hidden_dim = config.hidden_dim
            num_experts = config.num_experts
            num_layers = config.num_lstm_layers
            dropout = config.dropout
            use_layer_norm = config.use_layer_norm
        else:
            num_layers = 2
            dropout = 0.2
            use_layer_norm = True

        # P1-12: Store architecture config for checkpoint serialization
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_dim = hidden_dim
        self.num_experts = num_experts
        self.num_lstm_layers = num_layers

        self.lstm = nn.LSTM(
            input_dim, hidden_dim, batch_first=True, num_layers=num_layers, dropout=dropout
        )

        # Add LayerNorm after LSTM for training stability
        self.layer_norm = nn.LayerNorm(hidden_dim) if use_layer_norm else nn.Identity()

        self.experts = nn.ModuleList(
            [self._create_expert(hidden_dim, output_dim) for _ in range(num_experts)]
        )
        self.gate = nn.Sequential(nn.Linear(hidden_dim, num_experts), nn.Softmax(dim=-1))

    def _create_expert(self, h_dim, o_dim):
        return nn.Sequential(
            nn.Linear(h_dim, h_dim),
            nn.LayerNorm(h_dim),  # Add normalization within experts
            nn.ReLU(),
            nn.Linear(h_dim, o_dim),
        )

    def forward(self, x, role_id=None):
        x = self._validate_input_dim(x)
        lstm_out, _ = self.lstm(x)
        last_hidden = self.layer_norm(lstm_out[:, -1, :])  # Apply normalization
        gate_weights = self.gate(last_hidden)

        if role_id is not None:
            gate_weights = self._apply_role_bias(gate_weights, role_id)

        return _compute_nn_output(self.experts, last_hidden, gate_weights)

    def _validate_input_dim(self, x):
        if x.dim() < 2:
            raise ValueError(
                f"Input tensor must have at least 2 dims [batch, features], got {x.dim()}D. "
                "Unsqueeze explicitly before calling forward()."
            )
        if x.dim() == 2:
            return x.unsqueeze(1)
        return x

    def _apply_role_bias(self, gate_weights, role_id):
        role_id_int = int(role_id)
        max_role = self.num_experts - 1

        if role_id_int < 0 or role_id_int > max_role:
            warnings.warn(
                f"role_id {role_id_int} out of bounds [0, {max_role}], clamping.", UserWarning
            )
            role_id_int = max(0, min(role_id_int, max_role))

        role_bias = torch.zeros_like(gate_weights)
        role_bias[:, role_id_int] = 1.0
        return (gate_weights + role_bias) / 2.0


def _compute_nn_output(experts, last_hidden, gate_weights):
    expert_outputs = torch.stack([expert(last_hidden) for expert in experts], dim=1)
    return torch.tanh(torch.sum(expert_outputs * gate_weights.unsqueeze(-1), dim=1))


# NN-L-01: Deprecated alias — use AdvancedCoachNN directly.
# Retained for backward compatibility with train_pipeline.py (also deprecated).
TeacherRefinementNN = AdvancedCoachNN


class ModelManager:
    """
    MLOps Versioning & Deployment
    """

    def __init__(self, model_dir=None):
        if model_dir is None:
            from Programma_CS2_RENAN.core.config import MODELS_DIR

            model_dir = os.path.join(MODELS_DIR, "nn", "versions")
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    def save_version(self, model, metrics: dict):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        v_name = f"brain_{timestamp}"
        path = os.path.join(self.model_dir, f"{v_name}.pt")
        torch.save(model.state_dict(), path)
        # P1-12: Include architecture config so checkpoints are self-describing
        architecture = {}
        for attr in ("input_dim", "output_dim", "hidden_dim", "num_experts", "num_lstm_layers"):
            if hasattr(model, attr):
                architecture[attr] = getattr(model, attr)
        _save_model_metadata(path, v_name, timestamp, metrics, architecture)
        return path


def _save_model_metadata(path, v_name, timestamp, metrics, architecture=None):
    meta_path = path.replace(".pt", ".json")
    meta = {"version": v_name, "timestamp": timestamp, "metrics": metrics}
    if architecture:
        meta["architecture"] = architecture
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=4)


# Integrated RAP-Coach Architecture (optional - requires ncps and hflayers)
try:
    from .experimental.rap_coach.communication import RAPCommunication
    from .experimental.rap_coach.model import RAPCoachModel

    RAP_COACH_AVAILABLE = True
except ImportError:
    RAPCoachModel = None
    RAPCommunication = None
    RAP_COACH_AVAILABLE = False

# JEPA-Enhanced Model (NEW - coexists with AdvancedCoachNN)
# To use JEPA: from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel
# Existing models remain unchanged and fully functional
