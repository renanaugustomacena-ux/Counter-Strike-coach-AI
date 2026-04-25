"""
Early Stopping for neural network training.

Monitors validation loss and stops training when performance plateaus,
preventing overfitting and saving computational resources.

Also includes EmbeddingCollapseDetector: a hard-stop guard against the
P9-02 representation-collapse failure mode. The current jepa_trainer
emits a per-batch warning when embedding variance drops below 0.01
(advisory only). The modernization report (§9, Phase 0) and its N=260
supplement (§5.1 item 4) require this to abort training after two
consecutive validation epochs of collapse — silent collapse renders all
subsequent metrics meaningless and the larger corpus only buys more
opportunities for it. EmbeddingCollapseDetector implements that gate.

Usage:
    early_stopper = EarlyStopping(patience=10, min_delta=1e-4)

    for epoch in range(max_epochs):
        val_loss = validate()
        if early_stopper(val_loss):
            break

    collapse_detector = EmbeddingCollapseDetector(threshold=0.01, patience=2)
    for epoch in range(max_epochs):
        epoch_variance = train_one_epoch(...)
        collapse_detector.update(epoch_variance)  # raises if collapsed
"""


class EmbeddingCollapseError(RuntimeError):
    """Raised when the JEPA encoder collapses to a degenerate representation.

    Triggered by EmbeddingCollapseDetector after `patience` consecutive
    validation epochs with mean per-dim embedding variance below `threshold`.
    """


class EmbeddingCollapseDetector:
    """Hard-stop guard for the P9-02 embedding collapse failure mode.

    Modernization report §9 (Logical Coherence Audit):
        P9-02: embedding-collapse warning at variance < 0.01 is advisory only
        Resolution: promote to early-stop signal — abort training after two
        consecutive collapsed val epochs.

    The detector maintains a single counter of consecutive epochs where the
    epoch-mean embedding variance falls below `threshold`. A healthy epoch
    resets the counter. When the counter reaches `patience`, `update()`
    raises EmbeddingCollapseError.

    Variance source: typically the mean across latent dimensions of the
    per-dim variance computed across a batch's pooled embeddings. The same
    quantity already returned by JEPATrainer._log_embedding_diversity().
    """

    def __init__(self, threshold: float = 0.01, patience: int = 2):
        self.threshold = float(threshold)
        self.patience = int(patience)
        self.consecutive_collapsed = 0
        self.last_variance: float = float("nan")

    def update(self, epoch_mean_variance: float) -> None:
        """Feed an epoch's mean embedding variance.

        Resets the counter if the variance is healthy (>= threshold).
        Increments on collapse and raises EmbeddingCollapseError once the
        consecutive-collapsed counter reaches `patience`.

        Args:
            epoch_mean_variance: Mean variance across latent dimensions for
                the just-completed epoch. Negative or NaN values are treated
                as collapse (defensive against numerical surprise).

        Raises:
            EmbeddingCollapseError: when collapse persists `patience` epochs.
        """
        v = float(epoch_mean_variance)
        self.last_variance = v
        # NaN, negative, or below-threshold all count as collapse. NaN
        # comparison: "v < threshold" is False for NaN, so test explicitly.
        is_collapsed = (v != v) or (v < self.threshold)
        if is_collapsed:
            self.consecutive_collapsed += 1
        else:
            self.consecutive_collapsed = 0

        if self.consecutive_collapsed >= self.patience:
            raise EmbeddingCollapseError(
                f"P9-02: JEPA embedding variance below {self.threshold} for "
                f"{self.consecutive_collapsed} consecutive epochs (last="
                f"{v:.6f}). Encoder has collapsed; training aborted to "
                "prevent meaningless downstream metrics. Investigate: "
                "(a) InfoNCE temperature τ too low, (b) EMA momentum too "
                "fast, (c) data pipeline returning non-diverse contexts, "
                "(d) VICReg variance term not yet added (Pillar I)."
            )

    def reset(self) -> None:
        """Reset the consecutive-collapse counter (e.g. after retraining)."""
        self.consecutive_collapsed = 0
        self.last_variance = float("nan")


class EarlyStopping:
    """Early stopping to prevent overfitting."""

    def __init__(self, patience=10, min_delta=1e-4):
        """
        Args:
            patience: Number of epochs with no improvement before stopping
            min_delta: Minimum change to qualify as an improvement
        """
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.should_stop = False

    def __call__(self, val_loss):
        """
        Check if training should stop based on validation loss.

        Args:
            val_loss: Current validation loss

        Returns:
            True if training should stop, False otherwise
        """
        if self.best_loss is None:
            self.best_loss = val_loss
            return False

        # Check if validation loss improved
        if val_loss < self.best_loss - self.min_delta:
            # Improvement detected
            self.best_loss = val_loss
            self.counter = 0
            return False
        else:
            # No improvement
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True
                return True
            return False

    def reset(self):
        """Reset early stopping state."""
        self.counter = 0
        self.best_loss = None
        self.should_stop = False


# Example usage
if __name__ == "__main__":
    from Programma_CS2_RENAN.observability.logger_setup import get_logger as _get_logger

    _logger_es = _get_logger("cs2analyzer.nn.early_stopping")

    early_stopper = EarlyStopping(patience=3, min_delta=0.01)

    _logger_es.info("Testing Early Stopping...")

    # Simulate validation losses
    val_losses = [1.0, 0.9, 0.85, 0.84, 0.8399, 0.8398, 0.8397]

    for epoch, loss in enumerate(val_losses):
        _logger_es.info("Epoch %s: val_loss=%.4f", epoch, loss)
        if early_stopper(loss):
            _logger_es.info("Early stopping at epoch %s.", epoch)
            break

    _logger_es.info("Early stopping test passed.")
