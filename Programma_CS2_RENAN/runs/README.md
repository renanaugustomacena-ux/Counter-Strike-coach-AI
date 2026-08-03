> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Session Runs & Execution Data

This directory is the default output location for TensorBoard event logs generated during model training by the Counter-Strike coach AI. It contains no code; only regeneratable training telemetry is written here at runtime.

## Technical Overview

The path is resolved as `RUNS_DIR = USER_DATA_ROOT/runs` in `core/config.py` (created automatically at import). When `BRAIN_DATA_ROOT` is configured, runs are written under that root instead of the in-repo directory. The `TensorBoardCallback` (`backend/nn/tensorboard_callback.py`) — Layer 2 of the Coach Introspection Observatory — defaults its log directory to `RUNS_DIR/coach_training`, so TensorBoard events co-locate with the package instead of spawning a repo-root `runs/` orphan on every training run.

## Key Components

- **TensorBoard Event Files**: Scalars (loss, learning rate, sparsity), histograms, and custom scalar layouts logged per epoch during training.
- **MaturityObservatory Scalars**: The observatory shares the same `SummaryWriter`, so its conviction/maturity signals land in the same logdir.
- **Per-Run Subdirectories**: Each training invocation writes its own event files under the logdir, keeping runs separable in the TensorBoard UI.

## Usage

1. **Training**: `python run_full_training_cycle.py` registers the TensorBoard callback by default; `--tb-logdir` overrides the destination (default: `RUNS_DIR`) and `--no-tensorboard` disables logging.
2. **Viewing**: Launch `tensorboard --logdir Programma_CS2_RENAN/runs` and open the printed URL to inspect training curves.
3. **Cleanup**: Event files are volatile, regeneratable artifacts — old run directories can be deleted freely to save disk space.
