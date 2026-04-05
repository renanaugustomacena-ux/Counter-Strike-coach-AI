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

import sqlite3
import sys
from pathlib import Path
from typing import List

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from Programma_CS2_RENAN.backend.nn.jepa_model import JEPACoachingModel, jepa_contrastive_loss
from Programma_CS2_RENAN.backend.processing.feature_engineering import (
    METADATA_DIM,
    FeatureExtractor,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DB_PATH = str(_PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db")

logger = get_logger("cs2analyzer.jepa_train")


def _open_db(row_factory: bool = False) -> sqlite3.Connection:
    """Open monolith DB with WAL mode and busy timeout enforced."""
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn

# J-1 FIX: Tick-level sequence constants.
# context_len + target_len = 20 minimum ticks for one training sample.
_MIN_TICKS_FOR_SEQUENCE = 20

# Memory bound: cap per player-demo to avoid OOM on large demos (~1.5M ticks each).
# 500 ticks ≈ 25 potential context+target pairs per sequence.
_MAX_TICKS_PER_SEQUENCE = 500


class JEPAPretrainDataset(Dataset):
    """
    Dataset for JEPA pre-training on pro demos.

    Returns context and target windows from match sequences.
    """

    def __init__(
        self, match_sequences: List[np.ndarray], context_len: int = 10, target_len: int = 10
    ):
        # M2 FIX: Enforce that min ticks constant covers context + target windows.
        # Without this, changes to context/target lengths could silently produce
        # under-sized tensors that crash DataLoader collation.
        required = context_len + target_len
        assert _MIN_TICKS_FOR_SEQUENCE >= required, (
            f"_MIN_TICKS_FOR_SEQUENCE ({_MIN_TICKS_FOR_SEQUENCE}) must be >= "
            f"context_len + target_len ({required})"
        )
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


def _load_tick_sequence(
    demo_name: str,
    player_name: str,
    max_ticks: int = _MAX_TICKS_PER_SEQUENCE,
) -> np.ndarray:
    """Load tick-level features for one player in one demo via FeatureExtractor.

    Uses raw sqlite3 (no ORM overhead) with the composite index
    idx_pts_demo_player_tick for O(max_ticks) query cost instead of a full
    demo scan.

    J-1 FIX: Uses the same FeatureExtractor as the orchestrator (Path A),
    producing the canonical 25-dim tick-level vector (health/100, armor/100,
    pos_x/4096, ...). This eliminates the semantic collision where round-
    aggregate features (kills, deaths, ...) occupied the same indices.

    Academic justification: I-JEPA (Assran et al., CVPR 2023) operates on
    observation-level data, not aggregated summaries.

    Returns:
        np.ndarray of shape (num_ticks, METADATA_DIM), or empty array if
        insufficient ticks.
    """
    conn = _open_db(row_factory=True)
    try:
        rows = conn.execute(
            "SELECT * FROM playertickstate "
            "WHERE demo_name = ? AND player_name = ? "
            "ORDER BY tick LIMIT ?",
            (demo_name, player_name, max_ticks),
        ).fetchall()

        # KAST FIX: Inject avg_kast from playermatchstats so feature #16 is non-zero.
        # Without this, kast_estimate is always 0.0 because playertickstate has no
        # kast fields and the vectorizer's estimate_kast_from_stats() fallback also
        # gets all zeros (no kills/deaths columns in tick data).
        row_kast = conn.execute(
            "SELECT avg_kast FROM playermatchstats "
            "WHERE demo_name = ? AND LOWER(player_name) = LOWER(?)",
            (demo_name, player_name),
        ).fetchone()
    finally:
        conn.close()

    if len(rows) < _MIN_TICKS_FOR_SEQUENCE:
        return np.array([], dtype=np.float32)

    # Convert sqlite3.Row → dict so FeatureExtractor.extract() uses .get() path
    tick_dicts = [dict(row) for row in rows]
    map_name = tick_dicts[0].get("map_name")

    # Inject KAST if available (even 0.0 is valid — it means the player had no
    # positive-impact rounds, distinct from "no data available")
    if row_kast is not None and row_kast[0] is not None:
        avg_kast = float(row_kast[0])
        for td in tick_dicts:
            td["kast"] = avg_kast

    # V-4 FIX: extract_batch() can raise DataQualityError (>5% NaN/Inf).
    # Without try/except, one corrupt demo crashes the entire data loading run.
    try:
        features = FeatureExtractor.extract_batch(tick_dicts, map_name=map_name)
    except Exception as e:
        logger.warning("Skipping %s/%s — extract_batch failed: %s", demo_name, player_name, e)
        return np.array([], dtype=np.float32)
    return features


def load_pro_demo_sequences(limit: int = 100) -> List[np.ndarray]:
    """
    Load pro demo sequences as tick-level features via FeatureExtractor.

    Uses raw sqlite3 for match listing and tick extraction — avoids ORM
    instantiation overhead for potentially 100 × 500 = 50K row objects.
    Ghost players (sample_weight=0.0) are excluded from training data.

    J-1 FIX: Queries PlayerTickState (tick-level) instead of RoundStats
    (round-aggregate), producing the canonical 25-dim vector that matches
    the orchestrator's Path A. Eliminates feature-index semantic collision.

    Args:
        limit: Maximum number of matches to load

    Returns:
        List of match sequences [num_ticks, METADATA_DIM]
    """
    conn = _open_db()
    try:
        rows = conn.execute(
            "SELECT demo_name, player_name FROM playermatchstats "
            "WHERE is_pro = 1 AND sample_weight > 0 "
            "LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    sequences = []
    skipped = 0

    for demo_name, player_name in rows:
        features = _load_tick_sequence(demo_name, player_name)
        if features.size == 0:
            skipped += 1
            continue
        sequences.append(features)

    logger.info(
        "Loaded %d pro demo tick sequences via FeatureExtractor (%d skipped — insufficient ticks)",
        len(sequences),
        skipped,
    )
    return sequences


def load_user_match_sequences(limit: int = 200) -> tuple:
    """
    Load real user match tick sequences for JEPA fine-tuning.

    J-1 FIX: Uses tick-level features via FeatureExtractor (same pipeline
    as orchestrator Path A) instead of round-aggregate RoundStats features.

    Returns:
        (X_train, y_train) where X_train is [N, seq_len, METADATA_DIM]
        and y_train is [N, METADATA_DIM] (last-tick features as target).
    """
    conn = _open_db()
    try:
        rows = conn.execute(
            "SELECT demo_name, player_name FROM playermatchstats "
            "WHERE is_pro = 0 AND sample_weight > 0 "
            "ORDER BY match_date "
            "LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    X_sequences = []
    y_targets = []

    for demo_name, player_name in rows:
        features = _load_tick_sequence(demo_name, player_name)
        if features.size == 0:
            continue

        X_sequences.append(features)
        y_targets.append(features[-1])

    if not X_sequences:
        return None, None

    # Pad/truncate to uniform sequence length
    # WR-53: Repeat last valid tick instead of zero-padding.
    # Zero vectors encode physically impossible game states (health=0,
    # position at origin) that corrupt the LSTM hidden state.
    max_len = max(s.shape[0] for s in X_sequences)
    X_padded = []
    for s in X_sequences:
        if s.shape[0] < max_len:
            pad_len = max_len - s.shape[0]
            last_tick = s[-1:]  # [1, METADATA_DIM]
            pad = np.repeat(last_tick, pad_len, axis=0)
            s = np.concatenate([s, pad], axis=0)
        X_padded.append(s[:max_len])

    return np.array(X_padded), np.array(y_targets)


def train_jepa_pretrain(
    model: JEPACoachingModel,
    num_epochs: int = 50,
    batch_size: int = 16,
    learning_rate: float = 1e-4,
    num_negatives: int = 8,
    log_dir: str = "runs/jepa_pretrain",
):
    """
    JEPA pre-training on pro demos (self-supervised).

    Args:
        model: JEPACoachingModel instance
        num_epochs: Number of pre-training epochs
        batch_size: Batch size
        learning_rate: Learning rate
        num_negatives: Number of negative samples for contrastive loss
        log_dir: TensorBoard log directory
    """
    from Programma_CS2_RENAN.backend.nn.config import set_global_seed
    from Programma_CS2_RENAN.backend.nn.early_stopping import EarlyStopping
    from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback
    from Programma_CS2_RENAN.backend.nn.training_callbacks import CallbackRegistry

    set_global_seed()  # P1-02: Reproducible training
    logger.info("Starting JEPA pre-training...")

    # ── Callback Registry (TensorBoard + any future callbacks) ──
    tb_callback = TensorBoardCallback(log_dir=log_dir, model_type="jepa_pretrain")
    callbacks = CallbackRegistry([tb_callback])

    def _worker_init(worker_id: int) -> None:
        set_global_seed(42 + worker_id)

    # Load pro demo data
    sequences = load_pro_demo_sequences(limit=100)

    # NN-33: Guard against empty dataset
    if not sequences:
        logger.warning("No valid pro demo sequences found — skipping JEPA pre-training")
        callbacks.close_all()
        return

    dataset = JEPAPretrainDataset(sequences, context_len=10, target_len=10)

    if len(dataset) == 0:
        logger.warning("JEPAPretrainDataset is empty — skipping JEPA pre-training")
        callbacks.close_all()
        return

    dataloader = DataLoader(
        dataset, batch_size=batch_size, shuffle=True, worker_init_fn=_worker_init
    )

    # NN-JM-04: Target encoder is updated ONLY via EMA, never by gradient.
    # Freeze it before training so update_target_encoder() safety check passes.
    for param in model.target_encoder.parameters():
        param.requires_grad = False

    optimizer = torch.optim.AdamW(
        [{"params": model.context_encoder.parameters()}, {"params": model.predictor.parameters()}],
        lr=learning_rate,
        weight_decay=1e-2,  # J-7: Loshchilov & Hutter (ICLR 2019) AdamW default
    )

    from Programma_CS2_RENAN.backend.nn.config import get_device

    device = get_device()
    model.to(device)

    early_stopper = EarlyStopping(patience=10, min_delta=1e-5)  # P1-01

    # NN-L-15: Cosine LR schedule (matches JEPATrainer in jepa_trainer.py)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs)

    # J-6: EMA cosine momentum schedule (Assran et al., CVPR 2023, Section 3.2)
    import math as _math

    _ema_base = 0.996
    _ema_total = num_epochs * len(dataloader)  # total training steps
    _ema_step = 0

    # Training metadata for checkpoint
    loss_history = []
    best_loss = float("inf")
    final_epoch = 0

    # ── Fire on_train_start ──
    train_config = {
        "model_type": "jepa_pretrain",
        "num_epochs": num_epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "num_negatives": num_negatives,
        "num_sequences": len(sequences),
        "num_batches": len(dataloader),
        "device": str(device),
    }
    callbacks.fire("on_train_start", model=model, config=train_config)

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0
        final_epoch = epoch

        callbacks.fire("on_epoch_start", epoch=epoch)

        for batch_idx, batch in enumerate(dataloader):
            x_context = batch["context"].to(device)
            x_target = batch["target"].to(device)

            # Forward pass
            pred, target = model.forward_jepa_pretrain(x_context, x_target)

            # M1 FIX: Skip degenerate single-sample batches where positive==negative
            # produces zero contrastive loss (no learning signal).
            batch_size_actual = pred.size(0)
            if batch_size_actual < 2:
                continue

            # P1-05 + NN-35: Sample negatives via randperm (O(B) instead of O(B²))
            effective_negatives = min(num_negatives, batch_size_actual - 1)
            if effective_negatives > 0:
                # For each sample i, shift a random permutation to exclude i
                perm = torch.randperm(batch_size_actual - 1, device=device)
                perm = perm.unsqueeze(0).expand(batch_size_actual, -1)
                arange = torch.arange(batch_size_actual, device=device).unsqueeze(1)
                # Shift indices >= i by +1 so index i is never selected
                neg_indices = perm + (perm >= arange).long()
                neg_indices = neg_indices[:, :effective_negatives]
            else:
                neg_indices = torch.zeros(
                    batch_size_actual, max(1, effective_negatives), dtype=torch.long, device=device
                )
            negatives = target[neg_indices]

            # Contrastive loss
            loss = jepa_contrastive_loss(pred, target, negatives)

            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)  # P1-06
            optimizer.step()

            # J-6: EMA update with cosine momentum schedule
            _progress = min(_ema_step / max(1, _ema_total), 1.0)
            _momentum = 1.0 - (1.0 - _ema_base) * (_math.cos(_math.pi * _progress) + 1) / 2
            model.update_target_encoder(momentum=_momentum)
            _ema_step += 1

            total_loss += loss.item()

            callbacks.fire(
                "on_batch_end",
                batch_idx=batch_idx,
                loss=loss.item(),
                outputs={"infonce_loss": loss.item(), "ema_momentum": _momentum},
            )

        avg_loss = total_loss / len(dataloader)
        loss_history.append(avg_loss)
        if avg_loss < best_loss:
            best_loss = avg_loss

        if (epoch + 1) % 10 == 0:
            logger.info("Epoch %s/%s - Loss: %s", epoch + 1, num_epochs, format(avg_loss, ".4f"))

        scheduler.step()

        # Fire on_epoch_end (self-supervised: val_loss = train_loss)
        callbacks.fire(
            "on_epoch_end",
            epoch=epoch,
            train_loss=avg_loss,
            val_loss=avg_loss,
            model=model,
            optimizer=optimizer,
        )

        # P1-01: Early stopping based on training loss (self-supervised, no val set)
        if early_stopper(avg_loss):
            logger.info("JEPA early stopping triggered at epoch %d", epoch + 1)
            break

    logger.info("JEPA pre-training complete")

    # Fire on_train_end with final metrics
    callbacks.fire(
        "on_train_end",
        model=model,
        final_metrics={
            "final_loss": loss_history[-1] if loss_history else 0.0,
            "best_loss": best_loss,
            "total_epochs": final_epoch + 1,
            "num_sequences": len(sequences),
        },
    )
    callbacks.close_all()

    # Freeze encoders for fine-tuning
    model.freeze_encoders()

    # Attach training metadata for save_jepa_model
    model._training_metadata = {
        "loss_history": loss_history,
        "best_loss": best_loss,
        "final_epoch": final_epoch + 1,
        "num_sequences": len(sequences),
        "training_config": train_config,
    }

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
    dataloader = DataLoader(
        dataset, batch_size=batch_size, shuffle=True, worker_init_fn=_worker_init
    )

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
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)  # NN-H-01
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / len(dataloader)

        if (epoch + 1) % 5 == 0:
            logger.info("Epoch %s/%s - Loss: %s", epoch + 1, num_epochs, format(avg_loss, ".4f"))

    logger.info("JEPA fine-tuning complete")

    return model


def save_jepa_model(model: JEPACoachingModel, path: str, optimizer=None):
    """Save JEPA model checkpoint with full training metadata.

    Checkpoint contents:
        - model_state_dict: Model weights
        - is_pretrained: Pre-training flag
        - optimizer_state_dict: Optimizer state (if provided)
        - training_metadata: Loss history, epoch count, config (if available)
        - input_dim / output_dim: Model architecture dimensions
        - param_count: Total parameter count
        - save_timestamp: ISO 8601 save time
    """
    import datetime

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "is_pretrained": model.is_pretrained,
        "input_dim": model.input_dim,
        "output_dim": model.output_dim,
        "param_count": sum(p.numel() for p in model.parameters()),
        "save_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    if optimizer is not None:
        checkpoint["optimizer_state_dict"] = optimizer.state_dict()

    metadata = getattr(model, "_training_metadata", None)
    if metadata:
        checkpoint["training_metadata"] = metadata

    # M3 FIX: Atomic write — save to temp file then os.replace() so a crash
    # mid-save doesn't leave a corrupt checkpoint that breaks the next load.
    import os
    import tempfile

    save_dir = os.path.dirname(os.path.abspath(path))
    os.makedirs(save_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=save_dir, delete=False, suffix=".tmp") as tmp:
        torch.save(checkpoint, tmp.name)
        tmp_path = tmp.name
    os.replace(tmp_path, path)

    logger.info(
        "Saved JEPA model to %s (%d params, pretrained=%s)",
        path,
        checkpoint["param_count"],
        model.is_pretrained,
    )


def load_jepa_model(path: str, input_dim: int, output_dim: int) -> JEPACoachingModel:
    """Load JEPA model checkpoint.

    Returns the model with training metadata attached (if present in checkpoint)
    as model._training_metadata.
    """
    model = JEPACoachingModel(input_dim, output_dim)
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.is_pretrained = checkpoint.get("is_pretrained", False)

    metadata = checkpoint.get("training_metadata")
    if metadata:
        model._training_metadata = metadata

    param_count = checkpoint.get("param_count", "?")
    timestamp = checkpoint.get("save_timestamp", "unknown")
    logger.info("Loaded JEPA model from %s (%s params, saved %s)", path, param_count, timestamp)
    return model


if __name__ == "__main__":
    import argparse

    from Programma_CS2_RENAN.backend.nn.config import OUTPUT_DIM
    from Programma_CS2_RENAN.backend.processing.feature_engineering import METADATA_DIM

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["pretrain", "finetune"], required=True)
    # L3 FIX: Resolve relative to project root so the path is stable regardless
    # of the working directory when invoked via `python -m`.
    parser.add_argument(
        "--model-path", default=str(_PROJECT_ROOT / "models" / "jepa_model.pt")
    )
    args = parser.parse_args()

    if args.mode == "pretrain":
        # WR-63: Use OUTPUT_DIM (10) so checkpoints are compatible with inference
        model = JEPACoachingModel(input_dim=METADATA_DIM, output_dim=OUTPUT_DIM)
        model = train_jepa_pretrain(model, num_epochs=50)
        save_jepa_model(model, args.model_path)

    elif args.mode == "finetune":
        # Load pre-trained model
        model = load_jepa_model(args.model_path, input_dim=METADATA_DIM, output_dim=OUTPUT_DIM)

        X_train, y_train = load_user_match_sequences(limit=200)
        if X_train is None:
            logger.error(
                "No user match data with sufficient tick data found. "
                "Ingest demos with at least %d ticks before fine-tuning.",
                _MIN_TICKS_FOR_SEQUENCE,
            )
            sys.exit(1)

        logger.info("Fine-tuning on %d user matches", len(X_train))
        model = train_jepa_finetune(model, X_train, y_train, num_epochs=30)
        save_jepa_model(model, args.model_path.replace(".pt", "_finetuned.pt"))
