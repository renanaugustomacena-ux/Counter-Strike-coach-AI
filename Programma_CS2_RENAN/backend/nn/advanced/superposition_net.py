import torch
import torch.nn as nn
import torch.nn.functional as F


class SuperpositionLayer(nn.Module):
    def __init__(self, in_features, out_features):
        super(SuperpositionLayer, self).__init__()
        self.weight = nn.Parameter(torch.randn(out_features, in_features))
        self.bias = nn.Parameter(torch.zeros(out_features))
        # WARNING (F3-20): context_dim=5 is hardcoded. The canonical layers/superposition.py
        # uses METADATA_DIM=25. If this module is ever activated in production, passing a
        # 25-dim context vector here will crash at runtime with a shape mismatch.
        # FIX before activating: replace 5 with METADATA_DIM from feature_engineering.
        self.context_gate = nn.Linear(5, out_features)

    def forward(self, x, context):
        gate = torch.sigmoid(self.context_gate(context))
        out = F.linear(x, self.weight, self.bias)
        return out * gate


class AdaptiveSuperpositionMLP(nn.Module):
    def __init__(self, input_dim):
        super(AdaptiveSuperpositionMLP, self).__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.super_layer = SuperpositionLayer(128, 128)
        self.fc2 = nn.Linear(128, 64)
        self.impact_head = nn.Linear(64, 1)
        self.feedback_head = nn.Linear(64, 4)

    def forward(self, x, context):
        # Handle case where context might be missing
        if context is None:
            context = torch.zeros(x.shape[0], 5).to(x.device)

        x = F.relu(self.fc1(x))
        x = self.super_layer(x, context)
        x = F.relu(self.fc2(x))

        return {"impact": self.impact_head(x), "feedback": torch.tanh(self.feedback_head(x))}
