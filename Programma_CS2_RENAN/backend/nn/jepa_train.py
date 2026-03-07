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

from typing import List

import numpy as np
import torch
import torch.nn as nn
from sqlmodel import select
from torch.utils.data import DataLoader, Dataset

from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel, jepa_contrastive_loss
from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.jepa_train")


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
            # NOTE (F3-25): Uses unseeded global random state — window selection is
            # non-reproducible across runs. For deterministic training, seed the DataLoader
            # worker via worker_init_fn or use a Generator passed to DataLoader.
            start = np.random.randint(0, max_start)
            context = sequence[start : start + self.context_len]
            target = sequence[start + self.context_len : start + self.context_len + self.target_len]

        return {"context": torch.FloatTensor(context), "target": torch.FloatTensor(target)}


def load_pro_demo_sequences(limit: int = 100) -> List[np.ndarray]:
    """
    Load pro demo sequences from database.

    Args:
        limit: Maximum number of matches to load

    Returns:
        List of match sequences [num_rounds, num_features]
    """
    db = get_db_manager()
    sequences = []

    with db.get_session() as session:
        # Fetch pro matches
        stmt = select(PlayerMatchStats).where(PlayerMatchStats.is_pro == True).limit(limit)

        matches = session.exec(stmt).all()

        for match in matches:
            # Match-aggregate features (12 values) padded to METADATA_DIM.
            # Canonical tick-level pipeline uses full 19-dim via FeatureExtractor.
            base = [
                match.avg_kills,
                match.avg_deaths,
                match.avg_adr,
                match.avg_hs,
                match.avg_kast,
                match.kill_std,
                match.adr_std,
                match.kd_ratio,
                match.impact_rounds,
                match.accuracy,
                match.econ_rating,
                match.rating,
            ]
            features = np.array(base + [0.0] * (METADATA_DIM - len(base)))

            # WARNING (F3-08): np.tile creates 20 IDENTICAL frames from a single match-aggregate
            # vector. JEPA context-target prediction is trivially solved (copy input) and the
            # model learns an identity mapping — NOT temporal dynamics. This standalone script
            # is functionally a no-op for representation learning.
            # FIX: Replace with actual per-round RoundStats sequences for real temporal contrast.
            # NOTE: TrainingOrchestrator uses real per-tick data and is NOT affected by this.
            sequence = np.tile(features, (20, 1))  # 20 pseudo-rounds (no temporal contrast)
            sequences.append(sequence)

    logger.info("Loaded %s pro demo sequences", len(sequences))
    if sequences:
        logger.warning(
            "load_pro_demo_sequences: sequences are built with np.tile (F3-08) — "
            "JEPA will learn an identity mapping, NOT temporal dynamics. "
            "Replace with per-round RoundStats for meaningful pre-training."
        )
    return sequences


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

    # Load pro demo data
    sequences = load_pro_demo_sequences(limit=100)
    dataset = JEPAPretrainDataset(sequences, context_len=10, target_len=10)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

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

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0

        for batch in dataloader:
            x_context = batch["context"].to(device)
            x_target = batch["target"].to(device)

            # Forward pass
            pred, target = model.forward_jepa_pretrain(x_context, x_target)

            # P1-05: Sample negatives from batch, excluding positive index for each sample
            batch_size_actual = pred.size(0)
            effective_negatives = min(num_negatives, batch_size_actual - 1)
            if effective_negatives > 0 and batch_size_actual > 1:
                neg_indices = []
                for i in range(batch_size_actual):
                    candidates = [j for j in range(batch_size_actual) if j != i]
                    neg_indices.append(candidates[:effective_negatives])
                neg_indices = torch.tensor(neg_indices, device=device)
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

    dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

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

        # WARNING (F3-26): Placeholder uses synthetic random data — violates the
        # project's no-fabricated-data rule. Replace with real user match data before
        # any production fine-tuning run.
        X_train = np.random.randn(100, 15, METADATA_DIM)
        y_train = np.random.randn(100, METADATA_DIM)

        model = train_jepa_finetune(model, X_train, y_train, num_epochs=30)
        save_jepa_model(model, args.model_path.replace(".pt", "_finetuned.pt"))
