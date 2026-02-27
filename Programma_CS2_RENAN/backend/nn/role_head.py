"""
Neural Role Classification Head (Proposal 10)

Lightweight MLP that predicts player role probabilities from playstyle metrics.
Runs as a secondary opinion alongside the heuristic RoleClassifier — consensus
logic in role_classifier.py picks the final result.

Training data: Ext_PlayerPlaystyle table (cs2_playstyle_roles_2024.csv).
Architecture: 5 → 32 → 16 → 5 with softmax output (~750 parameters).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from Programma_CS2_RENAN.backend.analysis.role_classifier import PlayerRole
from Programma_CS2_RENAN.backend.nn.config import get_device
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.role_head")

# Index-to-role mapping for the output vector.
# role_anchor is merged into SUPPORT (anchors hold sites ≈ support playstyle).
ROLE_OUTPUT_ORDER: List[PlayerRole] = [
    PlayerRole.LURKER,  # 0 ← role_lurker
    PlayerRole.ENTRY_FRAGGER,  # 1 ← role_entry
    PlayerRole.SUPPORT,  # 2 ← role_support + role_anchor
    PlayerRole.AWPER,  # 3 ← role_awper
    PlayerRole.IGL,  # 4 ← role_igl
]

# Confidence below this threshold → FLEX
# 0.35 = empirical threshold; below this, player is classified as FLEX (no dominant role)
FLEX_CONFIDENCE_THRESHOLD = 0.35

# Minimum samples required to train
# 20 = minimum samples to avoid overfitting role classification on sparse data
MIN_TRAINING_SAMPLES = 20

# Label smoothing epsilon to avoid log(0) in KL-divergence
LABEL_SMOOTHING_EPS = 0.02


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class NeuralRoleHead(nn.Module):
    """5-dim input → 5-dim role probability distribution."""

    ROLE_INPUT_DIM = 5
    ROLE_OUTPUT_DIM = 5

    def __init__(
        self,
        input_dim: int = 5,
        hidden_dim: int = 32,
        output_dim: int = 5,
    ):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Returns softmax probabilities over roles."""
        return F.softmax(self.net(x), dim=-1)

    def forward_log_softmax(self, x: torch.Tensor) -> torch.Tensor:
        """Returns log-softmax for KL-divergence training loss."""
        return F.log_softmax(self.net(x), dim=-1)


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------


def prepare_role_training_data() -> Optional[Tuple[torch.Tensor, torch.Tensor, Dict]]:
    """Load Ext_PlayerPlaystyle records and produce feature/label tensors.

    Returns:
        (X, y, norm_stats) where X is (N, 5) features, y is (N, 5) soft labels,
        and norm_stats has "mean" and "std" tensors for inference normalization.
        Returns None if insufficient data.
    """
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.database import get_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import Ext_PlayerPlaystyle

    db = get_db_manager()
    with db.get_session() as session:
        records = session.exec(select(Ext_PlayerPlaystyle)).all()

    if len(records) < MIN_TRAINING_SAMPLES:
        logger.info(
            "Insufficient Ext_PlayerPlaystyle data (%d < %d). Skipping role head training.",
            len(records),
            MIN_TRAINING_SAMPLES,
        )
        return None

    features: list = []
    labels: list = []

    for r in records:
        features.append(
            [
                float(r.tapd),
                float(r.oap),
                float(r.podt),
                float(r.rating_impact),
                float(r.aggression_score),
            ]
        )
        # Merge role_anchor into role_support
        support_prob = float(r.role_support) + float(r.role_anchor)
        labels.append(
            [
                float(r.role_lurker),
                float(r.role_entry),
                support_prob,
                float(r.role_awper),
                float(r.role_igl),
            ]
        )

    X = torch.tensor(features, dtype=torch.float32)
    y = torch.tensor(labels, dtype=torch.float32)

    # Label smoothing: replace exact zeros to avoid log(0)
    y = y * (1.0 - LABEL_SMOOTHING_EPS) + LABEL_SMOOTHING_EPS / y.shape[1]

    # Re-normalize rows to sum to 1.0
    row_sums = y.sum(dim=1, keepdim=True).clamp(min=1e-8)
    y = y / row_sums

    # Compute normalization statistics from features
    norm_stats = {
        "mean": X.mean(dim=0).tolist(),
        "std": X.std(dim=0).tolist(),
    }

    logger.info("Prepared %d samples for role head training.", len(X))
    return X, y, norm_stats


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_role_head(
    max_epochs: int = 200,
    patience: int = 15,
    lr: float = 1e-3,
) -> Optional[NeuralRoleHead]:
    """Train the NeuralRoleHead on Ext_PlayerPlaystyle data.

    Returns the trained model, or None if training was skipped.
    """
    from Programma_CS2_RENAN.backend.nn.persistence import save_nn
    from Programma_CS2_RENAN.core.config import MODELS_DIR

    result = prepare_role_training_data()
    if result is None:
        return None

    X, y, norm_stats = result
    device = get_device()

    # Normalize features
    mean_t = torch.tensor(norm_stats["mean"], dtype=torch.float32)
    std_t = torch.tensor(norm_stats["std"], dtype=torch.float32)
    X = (X - mean_t) / (std_t + 1e-8)

    # 80/20 train/val split — cross-sectional data (not sequential), seeded for
    # reproducibility. Generator is local so it doesn't affect global torch state. (F3-32)
    n = len(X)
    perm = torch.randperm(n, generator=torch.Generator().manual_seed(42))
    split_idx = int(n * 0.8)
    train_idx, val_idx = perm[:split_idx], perm[split_idx:]

    X_train, y_train = X[train_idx].to(device), y[train_idx].to(device)
    X_val, y_val = X[val_idx].to(device), y[val_idx].to(device)

    if len(X_train) < 10 or len(X_val) < 2:
        logger.warning("Too few samples after split. Skipping role head training.")
        return None

    model = NeuralRoleHead().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = nn.KLDivLoss(reduction="batchmean")

    best_val_loss = float("inf")
    best_state = None
    patience_counter = 0

    for epoch in range(max_epochs):
        # --- Train ---
        model.train()
        log_probs = model.forward_log_softmax(X_train)
        train_loss = loss_fn(log_probs, y_train)

        optimizer.zero_grad()
        train_loss.backward()
        optimizer.step()

        # --- Validate ---
        model.eval()
        with torch.no_grad():
            val_log_probs = model.forward_log_softmax(X_val)
            val_loss = loss_fn(val_log_probs, y_val).item()

        # --- Early stopping ---
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info("Early stopping at epoch %d (val_loss=%.4f).", epoch, best_val_loss)
                break

    if best_state is None:
        logger.warning("No improvement during training. Skipping save.")
        return None

    # Restore best weights and save
    model.load_state_dict(best_state)
    model.eval()
    save_nn(model, "role_head")

    # Save normalization stats alongside the checkpoint
    norm_path = Path(MODELS_DIR) / "global" / "role_head_norm.json"
    norm_path.parent.mkdir(parents=True, exist_ok=True)
    with open(norm_path, "w") as f:
        json.dump(norm_stats, f)

    logger.info(
        "Role head trained and saved (epochs=%d, val_loss=%.4f, samples=%d).",
        epoch + 1,
        best_val_loss,
        n,
    )
    return model


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_role_head() -> Optional[Tuple[NeuralRoleHead, Dict]]:
    """Load trained NeuralRoleHead and its normalization stats.

    Returns (model, norm_stats) or None if not available.
    """
    from Programma_CS2_RENAN.backend.nn.persistence import get_model_path, load_nn
    from Programma_CS2_RENAN.core.config import MODELS_DIR

    # Check if norm_stats exist first (no point loading model without them)
    norm_path = Path(MODELS_DIR) / "global" / "role_head_norm.json"
    if not norm_path.exists():
        return None

    try:
        with open(norm_path, "r") as f:
            norm_stats = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    # Check if checkpoint exists before attempting load
    checkpoint_path = get_model_path("role_head")
    if not checkpoint_path.exists():
        return None

    model = NeuralRoleHead()
    model = load_nn("role_head", model)
    model.eval()

    return model, norm_stats


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------


def extract_role_features_from_stats(
    player_stats: Dict[str, float],
) -> Optional[torch.Tensor]:
    """Convert a player_stats dict to the 5-dim feature vector for the role head.

    Returns None if critical stats are missing.
    """
    rounds_played = player_stats.get("rounds_played", 0)
    if rounds_played <= 0:
        return None

    tapd = player_stats.get("rounds_survived", 0) / rounds_played
    oap = player_stats.get("entry_frags", 0) / rounds_played
    podt = player_stats.get("was_traded_ratio", 0.0)
    rating_impact = player_stats.get("impact_rating", player_stats.get("rating", 0.0))
    aggression = player_stats.get("positional_aggression_score", 0.0)

    return torch.tensor(
        [tapd, oap, podt, rating_impact, aggression],
        dtype=torch.float32,
    )
