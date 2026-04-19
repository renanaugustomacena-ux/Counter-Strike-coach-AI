"""
Training progress monitor.

Logs and persists training metrics (loss, learning rate, etc.) to JSON
for real-time monitoring and post-training analysis.
"""

import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.training_monitor")


def _coerce_json_safe(value: Any) -> Any:
    """Replace NaN/±Inf with None so json.dump emits valid RFC 8259 JSON.

    Fixes #27: training_progress.json has accumulated 543 NaN/Inf literals,
    which RFC 8259 forbids. Python's json module writes them as `NaN`/
    `Infinity` tokens when allow_nan=True (the default), producing output
    that trips strict parsers (browsers, jq, most JSON libraries).
    """
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, dict):
        return {k: _coerce_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_coerce_json_safe(v) for v in value]
    return value


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
        """Persist metrics to JSON file via atomic write (NN-L-12).

        #27: coerce NaN/Inf → null before dumping and set allow_nan=False so
        a future regression (serializing a non-finite without coercion) fails
        loudly instead of emitting invalid JSON.
        """
        dir_path = self.log_file.parent
        fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(
                    _coerce_json_safe(self.metrics),
                    f,
                    indent=2,
                    allow_nan=False,
                )
            os.replace(tmp_path, self.log_file)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

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
