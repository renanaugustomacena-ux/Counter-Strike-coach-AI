import argparse
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Programma_CS2_RENAN.backend.nn.coach_manager import CoachTrainingManager
from Programma_CS2_RENAN.backend.nn.training_callbacks import CallbackRegistry
from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator
from Programma_CS2_RENAN.core.logger import app_logger


def _build_callbacks(args) -> CallbackRegistry:
    """Build callback registry based on CLI flags."""
    registry = CallbackRegistry()

    if not args.no_tensorboard:
        from Programma_CS2_RENAN.backend.nn.tensorboard_callback import TensorBoardCallback

        tb = TensorBoardCallback(log_dir=args.tb_logdir)
        registry.add(tb)
        app_logger.info("TensorBoard callback registered (logdir: %s)", args.tb_logdir)

    return registry


def main():
    parser = argparse.ArgumentParser(
        description="Macena CS2 Analyzer - Training Pipeline Entry Point"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run a single epoch dry run to verify pipeline integrity",
    )
    parser.add_argument(
        "--resume", action="store_true", help="Resume from latest checkpoint if available"
    )
    parser.add_argument("--epochs", type=int, default=100, help="Override default max epochs")
    parser.add_argument(
        "--model-type",
        choices=["all", "jepa", "rap"],
        default="all",
        help="Specific model to train",
    )
    parser.add_argument(
        "--tb-logdir",
        type=str,
        default="runs/",
        help="TensorBoard log directory (default: runs/)",
    )
    parser.add_argument(
        "--no-tensorboard",
        action="store_true",
        help="Disable TensorBoard logging",
    )

    args = parser.parse_args()

    app_logger.info(
        "Training Cycle Initiated. Mode: %s | Dry Run: %s", args.model_type.upper(), args.dry_run
    )

    if args.dry_run:
        app_logger.warning(
            "DRY RUN ENABLED: Training will run for only 1 epoch and will NOT save production weights."
        )

    # Initialize Manager (State Controller)
    manager = CoachTrainingManager()

    # Build callback registry (TensorBoard etc.)
    callbacks = _build_callbacks(args)

    # Override epochs for dry run
    epochs = 1 if args.dry_run else args.epochs

    # Assign dataset splits before training (chronological 70/15/15)
    manager.assign_dataset_splits()

    try:
        if args.model_type in ["all", "jepa"]:
            app_logger.info(">>> Starting Phase 1: JEPA Pre-Training (World Model) <<<")
            orchestrator_jepa = TrainingOrchestrator(
                manager,
                model_type="jepa",
                max_epochs=epochs,
                patience=5 if args.dry_run else 10,
                callbacks=callbacks,
            )
            orchestrator_jepa.run_training()

        if args.model_type in ["all", "rap"]:
            app_logger.info(">>> Starting Phase 2: RAP Coach Training (Policy) <<<")
            orchestrator_rap = TrainingOrchestrator(
                manager,
                model_type="rap",
                max_epochs=epochs,
                patience=5 if args.dry_run else 10,
                callbacks=callbacks,
            )
            orchestrator_rap.run_training()

        app_logger.info("Full Training Cycle Completed Successfully.")

    except Exception as e:
        app_logger.critical("Training Cycle Failed: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        callbacks.close_all()


if __name__ == "__main__":
    main()
