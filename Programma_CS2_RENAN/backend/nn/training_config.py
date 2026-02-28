"""
Training configuration dataclass.

Centralizes all training hyperparameters in one place for easy tuning.
"""

from dataclasses import dataclass


@dataclass
class TrainingConfig:
    """Configuration for neural network training."""

    # Learning rate
    base_lr: float = 1e-4
    warmup_steps: int = 1000
    lr_schedule: str = "cosine"  # "cosine", "linear", "constant"
    min_lr: float = 1e-6  # Minimum learning rate for scheduler

    # Training
    max_epochs: int = 100
    batch_size: int = 1  # RAP processes 1 match at a time currently
    gradient_clip: float = 1.0

    # Validation
    val_every_n_steps: int = 50  # Validate every N matches processed
    val_batch_size: int = 1

    # Early stopping
    patience: int = 10  # Stop if no improvement for 10 validation checks
    min_delta: float = 1e-4

    # EMA
    ema_decay: float = 0.999
    use_ema: bool = True

    # Checkpointing
    save_every_n_epochs: int = 5
    keep_n_checkpoints: int = 3
    checkpoint_dir: str = "models/checkpoints"

    # Logging
    log_every_n_steps: int = 10
    progress_file: str = "training_progress.json"

    # Device
    device: str = "auto"  # "auto", "cuda", "cpu"


@dataclass
class JEPATrainingConfig(TrainingConfig):
    """Specific config for JEPA Self-Supervised Learning."""

    # JEPA Hyperparameters
    latent_dim: int = 256
    context_window: int = 10
    prediction_window: int = 10

    # Loss
    contrastive_temperature: float = 0.07
    momentum_target: float = 0.996  # EMA decay for target encoder

    # Phases
    pretraining_epochs: int = 50
    finetuning_epochs: int = 50


# Default configuration
DEFAULT_CONFIG = TrainingConfig()
