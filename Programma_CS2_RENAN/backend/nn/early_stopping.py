"""
Early Stopping for neural network training.

Monitors validation loss and stops training when performance plateaus,
preventing overfitting and saving computational resources.

Usage:
    early_stopper = EarlyStopping(patience=10, min_delta=1e-4)

    for epoch in range(max_epochs):
        val_loss = validate()
        if early_stopper(val_loss):
            break
"""


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
