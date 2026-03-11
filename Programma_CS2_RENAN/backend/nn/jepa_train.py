"""
JEPA Training Pipeline

Separate training functions for JEPA model.
Does NOT modify existing train.py or coach_manager.py.

Usage:
    # Pre-training
    python -m Programma_CS2_RENAN.backend.nn.jepa_train --mode pretrain

    # Fine-tuning
    python -m Programma_CS2_RENAN.backend.nn.jepa_train --mode finetune
"""

import sys
from typing import List

import numpy as np
import torch
import torch.nn as nn
from sqlmodel import select
from torch.utils.data import DataLoader, Dataset

from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel, jepa_contrastive_loss
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats, RoundStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.jepa_train")

# Minimum rounds needed for a meaningful JEPA sequence
_MIN_ROUNDS_FOR_SEQUENCE = 6


class JEPAPretrainDataset(Dataset):
    """
    Dataset for JEPA pre-training on pro demos.

    Returns context and target windows from match sequences.
    """

    def __init__(
        self, match_sequences: List[np.ndarray], context_len: int = 10, target_len: int = 10
    ):
        self.sequences = match_sequences
        self.context_len = context_len
        self.target_len = target_len

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        sequence = self.sequences[idx]

        # Sample random starting point
        max_start = len(sequence) - (self.context_len + self.target_len)
        if max_start <= 0:
            # Sequence too short, pad
            context = sequence[: self.context_len]
            target = sequence[self.context_len : self.context_len + self.target_len]
        else:
            start = np.random.randint(0, max_start)
            context = sequence[start : start + self.context_len]
            target = sequence[start + self.context_len : start + self.context_len + self.target_len]

        return {"context": torch.FloatTensor(context), "target": torch.FloatTensor(target)}


def _roundstats_to_features(rs: RoundStats) -> List[float]:
    """Extract a feature vector from a single RoundStats row.

    P-RSB-03: ``round_won`` is deliberately EXCLUDED — it is a future-looking
    outcome label, not an observable feature.  Including it would leak the
    round result into the training input, allowing the model to trivially
    predict outcomes from the outcome itself.  ``round_won`` is correctly
    used as a LABEL in ``label_from_round_stats()`` (jepa_model.py).
    """
    return [
        float(rs.kills),
        float(rs.deaths),
        float(rs.damage_dealt) / 100.0,  # normalise ADR-scale
        float(rs.headshot_kills),
        float(rs.assists),
        float(rs.trade_kills),
        float(1 if rs.was_traded else 0),
        float(1 if rs.opening_kill else 0),
        float(1 if rs.opening_death else 0),
        float(rs.he_damage) / 100.0,
        float(rs.molotov_damage) / 100.0,
        float(rs.flashes_thrown),
        float(rs.smokes_thrown),
        float(rs.equipment_value) / 5000.0,  # normalise to typical buy range
        # P-RSB-03: round_won removed — outcome label, not a feature
        float(rs.round_rating or 0.0),
        float(1 if rs.side == "CT" else 0),
    ]


def _build_sequence_from_rounds(
    round_rows: List[RoundStats],
) -> np.ndarray:
    """Build a [num_rounds, METADATA_DIM] array from RoundStats rows."""
    n_features = len(_roundstats_to_features(round_rows[0]))
    pad_len = max(0, METADATA_DIM - n_features)
    rows = []
    for rs in round_rows:
        feats = _roundstats_to_features(rs)
        rows.append(feats + [0.0] * pad_len)
    return np.array(rows, dtype=np.float32)


def load_pro_demo_sequences(limit: int = 100) -> List[np.ndarray]:
    """
    Load pro demo sequences from database using real per-round RoundStats.

    Falls back to match-aggregate padding only when no RoundStats exist.

    Args:
        limit: Maximum number of matches to load

    Returns:
        List of match sequences [num_rounds, num_features]
    """
    db = get_db_manager()
    sequences = []
    fallback_count = 0

    with db.get_session() as session:
        stmt = select(PlayerMatchStats).where(PlayerMatchStats.is_pro == True).limit(limit)
        matches = session.exec(stmt).all()

        for match in matches:
            # Try real per-round data first (F3-08 fix)
            round_rows = session.exec(
                select(RoundStats)
                .where(RoundStats.demo_name == match.demo_name)
                .where(RoundStats.player_name == match.player_name)
                .order_by(RoundStats.round_number)
            ).all()

            if len(round_rows) >= _MIN_ROUNDS_FOR_SEQUENCE:
                sequence = _build_sequence_from_rounds(round_rows)
                sequences.append(sequence)
            else:
                # NN-32: Skip matches without enough RoundStats — insufficient
                # rounds cannot form meaningful temporal sequences.
                fallback_count += 1
                continue

    logger.info("Loaded %d pro demo sequences from RoundStats (%d matches skipped — no RoundStats)",
                len(sequences), fallback_count)
    if fallback_count > 0:
        logger.warning(
            "%d matches skipped (no RoundStats). "
            "Ingest demos with RoundStats for meaningful temporal pre-training.",
            fallback_count,
        )
    return sequences


def load_user_match_sequences(limit: int = 200) -> tuple:
    """
    Load real user match sequences for JEPA fine-tuning.

    Returns:
        (X_train, y_train) where X_train is [N, seq_len, METADATA_DIM]
        and y_train is [N, METADATA_DIM] (last-round features as target).
    """
    db = get_db_manager()
    X_sequences = []
    y_targets = []

    with db.get_session() as session:
        stmt = (
            select(PlayerMatchStats)
            .where(PlayerMatchStats.is_pro == False)
            .order_by(PlayerMatchStats.match_date)
            .limit(limit)
        )
        matches = session.exec(stmt).all()

        for match in matches:
            round_rows = session.exec(
                select(RoundStats)
                .where(RoundStats.demo_name == match.demo_name)
                .where(RoundStats.player_name == match.player_name)
                .order_by(RoundStats.round_number)
            ).all()

            if len(round_rows) < _MIN_ROUNDS_FOR_SEQUENCE:
                continue

            seq = _build_sequence_from_rounds(round_rows)
            # Use all rounds as input, last round features as target
            X_sequences.append(seq)
            y_targets.append(seq[-1])

    if not X_sequences:
        return None, None

    # Pad/truncate to uniform sequence length
    max_len = max(s.shape[0] for s in X_sequences)
    X_padded = []
    for s in X_sequences:
        if s.shape[0] < max_len:
            pad = np.zeros((max_len - s.shape[0], METADATA_DIM), dtype=np.float32)
            s = np.concatenate([s, pad], axis=0)
        X_padded.append(s[:max_len])

    return np.array(X_padded), np.array(y_targets)


def train_jepa_pretrain(
    model: JEPACoachingModel,
    num_epochs: int = 50,
    batch_size: int = 16,
    learning_rate: float = 1e-4,
    num_negatives: int = 8,
):
    """
    JEPA pre-training on pro demos (self-supervised).

    Args:
        model: JEPACoachingModel instance
        num_epochs: Number of pre-training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        num_negatives: Number of negative samples for contrastive loss
    """
    from Programma_CS2_RENAN.backend.nn.config import set_global_seed
    from Programma_CS2_RENAN.backend.nn.early_stopping import EarlyStopping

    set_global_seed()  # P1-02: Reproducible training
    logger.info("Starting JEPA pre-training...")

    def _worker_init(worker_id: int) -> None:
        set_global_seed(42 + worker_id)

    # Load pro demo data
    sequences = load_pro_demo_sequences(limit=100)

    # NN-33: Guard against empty dataset
    if not sequences:
        logger.warning("No valid pro demo sequences found — skipping JEPA pre-training")
        return

    dataset = JEPAPretrainDataset(sequences, context_len=10, target_len=10)

    if len(dataset) == 0:
        logger.warning("JEPAPretrainDataset is empty — skipping JEPA pre-training")
        return

    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                            worker_init_fn=_worker_init)

    # Optimizer — target encoder is updated ONLY via EMA, never by gradient
    optimizer = torch.optim.AdamW(
        [{"params": model.context_encoder.parameters()}, {"params": model.predictor.parameters()}],
        lr=learning_rate,
        weight_decay=1e-4,
    )

    from Programma_CS2_RENAN.backend.nn.config import get_device

    device = get_device()
    model.to(device)

    early_stopper = EarlyStopping(patience=10, min_delta=1e-5)  # P1-01

    # NN-L-15: Cosine LR schedule (matches JEPATrainer in jepa_trainer.py)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0

        for batch in dataloader:
            x_context = batch["context"].to(device)
            x_target = batch["target"].to(device)

            # Forward pass
            pred, target = model.forward_jepa_pretrain(x_context, x_target)

            # P1-05 + NN-35: Sample negatives via randperm (O(B) instead of O(B²))
            batch_size_actual = pred.size(0)
            effective_negatives = min(num_negatives, batch_size_actual - 1)
            if effective_negatives > 0 and batch_size_actual > 1:
                # For each sample i, shift a random permutation to exclude i
                perm = torch.randperm(batch_size_actual - 1, device=device)
                perm = perm.unsqueeze(0).expand(batch_size_actual, -1)
                arange = torch.arange(batch_size_actual, device=device).unsqueeze(1)
                # Shift indices >= i by +1 so index i is never selected
                neg_indices = perm + (perm >= arange).long()
                neg_indices = neg_indices[:, :effective_negatives]
            else:
                neg_indices = torch.zeros(batch_size_actual, max(1, effective_negatives), dtype=torch.long, device=device)
            negatives = target[neg_indices]

            # Contrastive loss
            loss = jepa_contrastive_loss(pred, target, negatives)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)  # P1-06
            optimizer.step()

            # EMA update for target encoder (must happen after optimizer.step)
            model.update_target_encoder()

            total_loss += loss.item()

        avg_loss = total_loss / len(dataloader)

        if (epoch + 1) % 10 == 0:
            logger.info("Epoch %s/%s - Loss: %s", epoch + 1, num_epochs, format(avg_loss, ".4f"))

        scheduler.step()

        # P1-01: Early stopping based on training loss (self-supervised, no val set)
        if early_stopper(avg_loss):
            logger.info("JEPA early stopping triggered at epoch %d", epoch + 1)
            break

    logger.info("JEPA pre-training complete")

    # Freeze encoders for fine-tuning
    model.freeze_encoders()

    return model


def train_jepa_finetune(
    model: JEPACoachingModel,
    X_train: np.ndarray,
    y_train: np.ndarray,
    num_epochs: int = 30,
    batch_size: int = 16,
    learning_rate: float = 1e-3,
):
    """
    Fine-tune LSTM coaching head on user data (supervised).

    Args:
        model: Pre-trained JEPACoachingModel
        X_train: Training features [num_samples, seq_len, input_dim]
        y_train: Training labels [num_samples, output_dim]
        num_epochs: Number of fine-tuning epochs
        batch_size: Batch size
        learning_rate: Learning rate
    """
    logger.info("Starting JEPA fine-tuning...")

    # Ensure encoders are frozen
    model.freeze_encoders()

    # Optimizer (only for LSTM + MoE)
    optimizer = torch.optim.AdamW(
        [
            {"params": model.lstm.parameters()},
            {"params": model.experts.parameters()},
            {"params": model.gate.parameters()},
        ],
        lr=learning_rate,
        weight_decay=1e-3,
    )

    loss_fn = nn.MSELoss()
    from Programma_CS2_RENAN.backend.nn.config import get_device

    device = get_device()
    model.to(device)

    # Convert to tensors
    X_tensor = torch.FloatTensor(X_train)
    y_tensor = torch.FloatTensor(y_train)

    def _worker_init(worker_id: int) -> None:
        from Programma_CS2_RENAN.backend.nn.config import set_global_seed as _seed
        _seed(42 + worker_id)

    dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                            worker_init_fn=_worker_init)

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0

        for X_batch, y_batch in dataloader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            # Forward pass
            predictions = model.forward_coaching(X_batch)

            # Loss
            loss = loss_fn(predictions, y_batch)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(dataloader)

        if (epoch + 1) % 5 == 0:
            logger.info("Epoch %s/%s - Loss: %s", epoch + 1, num_epochs, format(avg_loss, ".4f"))

    logger.info("JEPA fine-tuning complete")

    return model


def save_jepa_model(model: JEPACoachingModel, path: str):
    """Save JEPA model checkpoint."""
    torch.save({"model_state_dict": model.state_dict(), "is_pretrained": model.is_pretrained}, path)
    logger.info("Saved JEPA model to %s", path)


def load_jepa_model(path: str, input_dim: int, output_dim: int) -> JEPACoachingModel:
    """Load JEPA model checkpoint."""
    model = JEPACoachingModel(input_dim, output_dim)
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.is_pretrained = checkpoint["is_pretrained"]
    logger.info("Loaded JEPA model from %s", path)
    return model


if __name__ == "__main__":
    import argparse

    from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["pretrain", "finetune"], required=True)
    parser.add_argument("--model-path", default="models/jepa_model.pt")
    args = parser.parse_args()

    if args.mode == "pretrain":
        model = JEPACoachingModel(input_dim=METADATA_DIM, output_dim=METADATA_DIM)
        model = train_jepa_pretrain(model, num_epochs=50)
        save_jepa_model(model, args.model_path)

    elif args.mode == "finetune":
        # Load pre-trained model
        model = load_jepa_model(args.model_path, input_dim=METADATA_DIM, output_dim=METADATA_DIM)

        X_train, y_train = load_user_match_sequences(limit=200)
        if X_train is None:
            logger.error(
                "No user match data with RoundStats found. "
                "Ingest at least %d demos before fine-tuning.", _MIN_ROUNDS_FOR_SEQUENCE
            )
            sys.exit(1)

        logger.info("Fine-tuning on %d user matches", len(X_train))
        model = train_jepa_finetune(model, X_train, y_train, num_epochs=30)
        save_jepa_model(model, args.model_path.replace(".pt", "_finetuned.pt"))
