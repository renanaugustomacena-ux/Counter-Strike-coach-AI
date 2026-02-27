"""
Training progress monitor.

Logs and persists training metrics (loss, learning rate, etc.) to JSON
for real-time monitoring and post-training analysis.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.training_monitor")


class TrainingMonitor:
    """Monitors and logs training progress."""

    def __init__(self, log_file="training_progress.json"):
        """
        Args:
            log_file: Path to JSON file for metrics storage
        """
        self.log_file = Path(log_file)
        self.metrics = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "epochs": [],
            "train_loss": [],
            "val_loss": [],
            "learning_rate": [],
            "best_val_loss": None,
            "early_stopped": False,
        }

        # Load existing progress if resuming
        if self.log_file.exists():
            with open(self.log_file, "r") as f:
                self.metrics = json.load(f)

    def log_epoch(self, epoch, train_loss, val_loss=None, lr=None):
        """
        Record metrics for an epoch.

        Args:
            epoch: Current epoch number
            train_loss: Average training loss for this epoch
            val_loss: Validation loss (if available)
            lr: Current learning rate
        """
        self.metrics["epochs"].append(epoch)
        self.metrics["train_loss"].append(train_loss)

        if val_loss is not None:
            self.metrics["val_loss"].append(val_loss)

            # Update best validation loss
            if self.metrics["best_val_loss"] is None or val_loss < self.metrics["best_val_loss"]:
                self.metrics["best_val_loss"] = val_loss

        if lr is not None:
            self.metrics["learning_rate"].append(lr)

        self._save()

    def mark_early_stop(self):
        """Mark that training was stopped early."""
        self.metrics["early_stopped"] = True
        self.metrics["stopped_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def mark_complete(self):
        """Mark that training completed normally."""
        self.metrics["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def _save(self):
        """Persist metrics to JSON file."""
        with open(self.log_file, "w") as f:
            json.dump(self.metrics, f, indent=2)

    def get_summary(self):
        """Return a summary of training progress."""
        if not self.metrics["epochs"]:
            return "No training data yet."

        summary = [
            f"Epochs: {len(self.metrics['epochs'])}",
            (
                f"Best Val Loss: {self.metrics['best_val_loss']:.4f}"
                if self.metrics["best_val_loss"]
                else "No validation"
            ),
            f"Latest Train Loss: {self.metrics['train_loss'][-1]:.4f}",
        ]

        if self.metrics.get("early_stopped"):
            summary.append("Status: Early Stopped")
        elif self.metrics.get("completed_at"):
            summary.append("Status: Completed")
        else:
            summary.append("Status: In Progress")

        return "\n".join(summary)


# Example usage
if __name__ == "__main__":
    monitor = TrainingMonitor("test_progress.json")

    logger.info("Testing Training Monitor...")

    # Simulate training
    for epoch in range(5):
        train_loss = 1.0 / (epoch + 1)
        val_loss = 1.1 / (epoch + 1)
        lr = 0.001 * (0.9**epoch)

        monitor.log_epoch(epoch, train_loss, val_loss, lr)

    logger.info(monitor.get_summary())
    logger.info("Training monitor test passed.")
