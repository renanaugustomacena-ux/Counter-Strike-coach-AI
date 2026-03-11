"""
Training Callbacks Framework — Layer 1 of the Coach Introspection Observatory.

Provides a plugin architecture for training instrumentation without modifying
the core training loop. Callbacks receive lifecycle events and can log metrics,
compute derived signals, or trigger external tools (TensorBoard, UMAP, etc.).

Usage:
    from Programma_CS2_RENAN.backend.nn.training_callbacks import (
        TrainingCallback, CallbackRegistry,
    )

    class MyCallback(TrainingCallback):
        def on_epoch_end(self, epoch, train_loss, val_loss, model, **kw):
            print(f"Epoch {epoch}: {train_loss:.4f}")

    registry = CallbackRegistry([MyCallback()])
    registry.fire("on_epoch_end", epoch=1, train_loss=0.1, val_loss=0.2, model=model)
"""

from abc import ABC
from typing import Any, Dict, List, Optional

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nn.callbacks")


class TrainingCallback(ABC):
    """Abstract base class for training instrumentation callbacks.

    NOTE (F3-31): No methods use @abstractmethod by design — this is an opt-in
    pattern where subclasses override only the hooks they need. All hooks default
    to no-ops. This differs from strict ABC usage; do not add @abstractmethod
    without updating all existing subclasses.
    """

    def on_train_start(self, model, config: Dict[str, Any]) -> None:
        """Called once before the first epoch."""

    def on_epoch_start(self, epoch: int) -> None:
        """Called at the beginning of each epoch."""

    def on_batch_end(self, batch_idx: int, loss: float, outputs: Dict[str, Any]) -> None:
        """Called after each training batch with trainer outputs."""

    def on_epoch_end(
        self,
        epoch: int,
        train_loss: float,
        val_loss: float,
        model,
        **kwargs,
    ) -> None:
        """Called at the end of each epoch with aggregate metrics."""

    def on_validation_end(self, epoch: int, val_loss: float, model) -> None:
        """Called after the validation pass completes."""

    def on_train_end(self, model, final_metrics: Dict[str, Any]) -> None:
        """Called once after training completes (normal or early stop)."""

    def close(self) -> None:
        """Release resources (file handles, writers, etc.)."""


class CallbackRegistry:
    """
    Manages a collection of TrainingCallbacks and dispatches lifecycle events.

    Zero-impact when no callbacks are registered: all fire() calls become no-ops.
    Errors in individual callbacks are caught and logged — they never crash training.
    """

    def __init__(self, callbacks: Optional[List[TrainingCallback]] = None):
        self.callbacks: List[TrainingCallback] = callbacks or []

    def add(self, callback: TrainingCallback) -> None:
        # NN-L-13: Prevent duplicate callback registration
        if callback in self.callbacks:
            logger.debug("Callback %s already registered — skipping", callback.__class__.__name__)
            return
        self.callbacks.append(callback)

    def fire(self, event: str, **kwargs) -> None:
        """
        Dispatch a lifecycle event to all registered callbacks.

        Args:
            event: Name of the callback method (e.g., "on_epoch_end").
            **kwargs: Arguments forwarded to the callback method.
        """
        for cb in self.callbacks:
            method = getattr(cb, event, None)
            if method is None:
                continue
            try:
                method(**kwargs)
            except Exception as e:
                logger.warning(
                    "Callback %s.%s failed: %s",
                    cb.__class__.__name__,
                    event,
                    e,
                )

    def close_all(self) -> None:
        """Close all registered callbacks."""
        for cb in self.callbacks:
            try:
                cb.close()
            except Exception as e:
                logger.warning("Callback %s.close() failed: %s", cb.__class__.__name__, e)
