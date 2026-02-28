"""
Exponential Moving Average (EMA) for model weights.

EMA maintains a shadow copy of model parameters that is updated more slowly
than the actual training weights. This provides:
- More stable model behavior
- Better generalization
- Reduced sensitivity to local minima

Usage:
    model = RAPCoachModel()
    ema = EMA(model, decay=0.999)

    for batch in train_loader:
        loss = train_step(batch)
        ema.update()  # Update shadow weights

    # For inference, use EMA weights
    ema.apply_shadow()
    predictions = model(test_data)
    ema.restore()
"""

from copy import deepcopy

import torch

from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.nn.ema")


class EMA:
    """Maintains exponential moving average of model parameters."""

    def __init__(self, model, decay=0.999):
        """
        Args:
            model: PyTorch model to track
            decay: EMA decay rate (higher = slower updates, more stable)
                   Typical values: 0.999, 0.9999
        """
        self.model = model
        self.decay = decay
        self.shadow = {}
        self.backup = {}
        self._register()

    def _register(self):
        """Store initial shadow copies of model parameters."""
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.shadow[name] = param.data.clone()

    def update(self):
        """
        Update shadow parameters using exponential moving average.

        Formula: shadow = decay * shadow + (1 - decay) * param

        Call this after each training step (optimizer.step()).
        """
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                if name not in self.shadow:
                    self.shadow[name] = param.data.clone()
                self.shadow[name] = self.decay * self.shadow[name] + (1 - self.decay) * param.data

    def apply_shadow(self):
        """
        Temporarily replace model weights with EMA shadow weights.

        Use this before inference/validation to get smoother predictions.
        Always call restore() afterward to return to training weights.
        """
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                self.backup[name] = param.data.clone()
                param.data = self.shadow[name]

    def restore(self):
        """Restore original training weights after using shadow weights."""
        for name, param in self.model.named_parameters():
            if param.requires_grad:
                param.data = self.backup[name]
        self.backup = {}

    def state_dict(self):
        """Return shadow weights for saving to checkpoint.

        Returns cloned tensors so callers cannot corrupt the internal shadow
        weights through in-place modifications. (F3-30)
        """
        return {k: v.clone() for k, v in self.shadow.items()}

    def load_state_dict(self, state_dict):
        """Load shadow weights from checkpoint."""
        self.shadow = {
            k: v.clone() if hasattr(v, "clone") else deepcopy(v) for k, v in state_dict.items()
        }


# Example usage
if __name__ == "__main__":
    # Mock model
    model = torch.nn.Linear(10, 5)
    ema = EMA(model, decay=0.999)

    _logger.info("Testing EMA...")

    # Simulate training
    for _ in range(100):
        # Mock training step
        model.weight.data += torch.randn_like(model.weight) * 0.1
        ema.update()

    _logger.info("Original weight norm: %s", torch.norm(model.weight).item())

    # Use EMA weights
    ema.apply_shadow()
    _logger.info("EMA weight norm: %s", torch.norm(model.weight).item())

    # Restore
    ema.restore()
    _logger.info("Restored weight norm: %s", torch.norm(model.weight).item())

    _logger.info("EMA test passed.")
