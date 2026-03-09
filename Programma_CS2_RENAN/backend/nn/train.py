import random

import torch
import torch.nn as nn
from sqlmodel import select
from torch.utils.data import DataLoader

from Programma_CS2_RENAN.backend.nn.config import EPOCHS, LEARNING_RATE
from Programma_CS2_RENAN.backend.nn.dataset import ProPerformanceDataset
from Programma_CS2_RENAN.backend.nn.model import TeacherRefinementNN
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn_train")


def train_nn(X, y, X_val=None, y_val=None, model=None, config_name="default", context=None):
    """
    ML-Audited Training Entry Point with GPU support.
    Supports Model Factory selection (Legacy vs JEPA).
    """
    from Programma_CS2_RENAN.backend.nn.config import get_device, get_intensity_batch_size, set_global_seed
    from Programma_CS2_RENAN.backend.nn.factory import ModelFactory

    set_global_seed()  # P1-02: Reproducible training
    device = get_device()

    # Check if we are in JEPA mode (Self-Supervised)
    if config_name == ModelFactory.TYPE_JEPA:
        return _train_jepa_self_supervised(X, device, context=context)

    # Validated Supervised Loop (Legacy/RAP)
    X_train, X_val, y_train, y_val = _prepare_splits(X, y, X_val, y_val)
    if X_train is None:
        # P1-04: Insufficient data — refuse to train
        logger.error("Training aborted: insufficient data for train/val split.")
        return None
    train_ds = ProPerformanceDataset(X_train, y_train)
    val_ds = ProPerformanceDataset(X_val, y_val)

    effective_batch = get_intensity_batch_size()
    train_loader = DataLoader(
        train_ds, batch_size=min(effective_batch, len(train_ds)), shuffle=True
    )
    val_loader = DataLoader(val_ds, batch_size=min(len(val_ds), 256), shuffle=False)  # P1-11: Cap val batch size

    # Use Factory to get model instance (if not provided)
    if model is None:
        model = ModelFactory.get_model(config_name)

    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-2)
    loss_fn = nn.MSELoss()

    logger.info("Training [%s] on %s | Intensity batch: %s.", config_name, device, effective_batch)
    _execute_validated_loop(
        model, train_loader, val_loader, optimizer, loss_fn, device, context=context
    )

    return model.cpu()  # Return to CPU for persistence/saving


def _train_jepa_self_supervised(X, device, context=None):
    """
    Stage 1: Self-Supervised Pre-training for JEPA.
    Uses Contrastive Loss, not MSE. User labels (y) are ignored.
    """
    from Programma_CS2_RENAN.backend.nn.config import get_intensity_batch_size, set_global_seed
    from Programma_CS2_RENAN.backend.nn.dataset import SelfSupervisedDataset
    from Programma_CS2_RENAN.backend.nn.early_stopping import EarlyStopping
    from Programma_CS2_RENAN.backend.nn.factory import ModelFactory
    from Programma_CS2_RENAN.backend.nn.jepa_model import jepa_contrastive_loss

    set_global_seed()  # P1-02: Reproducible training
    logger.info("Starting JEPA Self-Supervised Pre-training (Prototype)...")

    # 1. Prepare Data (Unlabeled Sequences)
    # Using small windows for prototype: Context=10, Predator=5
    ds = SelfSupervisedDataset(X, context_len=10, prediction_len=5)
    batch_size = get_intensity_batch_size()
    loader = DataLoader(ds, batch_size=min(batch_size, len(ds)), shuffle=True)

    logger.info("JEPA Dataset: %s samples. Batch Size: %s", len(ds), batch_size)

    # 2. Init Model via Factory
    model = ModelFactory.get_model(ModelFactory.TYPE_JEPA)
    model.to(device)
    model.train()

    # Optimizer (AdamW standard for Transformers/JEPAs)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-2)

    # 3. Pre-training Loop
    # In production, this would be 100+ epochs.
    # For "Activation" prototype, we do enough to verify gradients and loss decrease.
    JEPA_EPOCHS = 5
    early_stopper = EarlyStopping(patience=10, min_delta=1e-5)  # P1-01

    for epoch in range(JEPA_EPOCHS):
        if context:
            context.check_state()
        total_loss = 0.0
        batch_count = 0

        for context_tensor, target in loader:
            if context:
                context.check_state()
            context_tensor, target = context_tensor.to(device), target.to(device)

            optimizer.zero_grad()

            # Forward Pass: Context -> Predicted Target Embedding
            # Target Encoder: Target -> Target Embedding (No Grad)
            pred_emb, target_emb = model.forward_jepa_pretrain(context_tensor, target)

            # P1-03: Use contrastive loss to prevent embedding collapse.
            # Sample negatives from current batch (excluding positive for each sample).
            batch_size_actual = pred_emb.size(0)
            num_negatives = min(8, batch_size_actual - 1)
            if num_negatives > 0 and batch_size_actual > 1:
                # P1-05 pattern: exclude positive index from negatives
                neg_indices = []
                for i in range(batch_size_actual):
                    candidates = [j for j in range(batch_size_actual) if j != i]
                    selected = random.sample(candidates, k=num_negatives)
                    neg_indices.append(selected)
                neg_indices = torch.tensor(neg_indices, device=device)
                negatives = target_emb[neg_indices]
                loss = jepa_contrastive_loss(pred_emb, target_emb, negatives)
            else:
                # Fallback for batch_size=1: use MSE (cannot do contrastive with 1 sample)
                loss = nn.MSELoss()(pred_emb, target_emb)

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)  # P1-06
            optimizer.step()

            # EMA Update for Target Encoder (Critical for preventing collapse)
            model.update_target_encoder()

            total_loss += loss.item()
            batch_count += 1

        avg_loss = total_loss / max(1, batch_count)
        logger.info("JEPA Epoch %s/%s | Loss: %s", epoch + 1, JEPA_EPOCHS, format(avg_loss, ".6f"))

        # P1-01: Early stopping on training loss (no separate val set for self-supervised)
        if early_stopper(avg_loss):
            logger.info("JEPA early stopping triggered at epoch %d", epoch + 1)
            break

    logger.info("JEPA Pre-training Complete.")
    return model.cpu()


MIN_TRAINING_SAMPLES = 20  # P1-04 / AR-6: Minimum samples for meaningful train/val split


def _prepare_splits(X, y, X_val, y_val):
    from sklearn.model_selection import train_test_split

    if X_val is not None:
        return X, X_val, y, y_val
    if len(X) < MIN_TRAINING_SAMPLES:
        # P1-04: Refuse to train with insufficient data instead of using train=val
        logger.warning(
            "Insufficient training data (%d < %d). Cannot create meaningful train/val split.",
            len(X), MIN_TRAINING_SAMPLES,
        )
        return None, None, None, None
    return train_test_split(X, y, test_size=0.2, random_state=42)


def _execute_validated_loop(
    model, train_loader, val_loader, optimizer, loss_fn, device, context=None
):
    import time

    from Programma_CS2_RENAN.backend.nn.config import get_throttling_delay
    from Programma_CS2_RENAN.backend.nn.early_stopping import EarlyStopping

    delay = get_throttling_delay()
    early_stopper = EarlyStopping(patience=10, min_delta=1e-4)  # P1-01

    for epoch in range(EPOCHS):
        if context:
            context.check_state()
        model.train()
        t_loss = _run_training_epoch(
            model, train_loader, optimizer, loss_fn, delay, device, context=context
        )

        model.eval()
        v_loss = _run_validation_pass(model, val_loader, loss_fn, device)

        avg_v_loss = v_loss / max(len(val_loader), 1)

        if (epoch + 1) % 10 == 0:
            logger.info(
                "Epoch %s: T-Loss=%s, V-Loss=%s",
                epoch + 1,
                format(t_loss / len(train_loader), ".4f"),
                format(avg_v_loss, ".4f"),
            )

        # P1-01: Early stopping based on validation loss
        if early_stopper(avg_v_loss):
            logger.info("Early stopping triggered at epoch %d (patience=%d)", epoch + 1, early_stopper.patience)
            break


def _run_training_epoch(model, loader, optimizer, loss_fn, delay, device, context=None):
    import time

    total_loss = 0.0
    for xb, yb in loader:
        if context:
            context.check_state()
        xb, yb = xb.to(device), yb.to(device)
        optimizer.zero_grad()
        pred = model(xb)
        loss = loss_fn(pred, yb)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)  # P1-06: Prevent exploding gradients in LSTM
        optimizer.step()
        total_loss += loss.item()
        if delay > 0:
            time.sleep(delay)
    return total_loss


def _run_validation_pass(model, loader, loss_fn, device):
    v_loss = 0.0
    with torch.no_grad():
        for xv, yv in loader:
            xv, yv = xv.to(device), yv.to(device)
            v_pred = model(xv)
            v_loss += loss_fn(v_pred, yv).item()
    return v_loss


def run_training():
    """
    Corrected Standalone Training.
    Uses real deltas from pro baseline instead of rating proxies.
    """
    from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager

    manager = CoachTrainingManager()

    # We leverage the manager's preparation logic to ensure feature consistency
    raw_pro = manager._fetch_training_data(is_pro=True, split="train")
    if not raw_pro:
        return logger.error("No Pro data found.")

    X, y = manager._prepare_tensors(raw_pro)
    model = train_nn(X, y)
    _finalize_training(model)


def _log_epoch(epoch, total_loss):
    if (epoch + 1) % 10 == 0:
        logger.info("Epoch %s: loss=%s", epoch + 1, format(total_loss, ".4f"))


def _finalize_training(model):
    from Programma_CS2_RENAN.backend.nn.persistence import save_nn

    save_nn(model, "latest")
    logger.info("Training complete. Model saved as 'latest'.")


if __name__ == "__main__":
    run_training()
