> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Session Runs & Execution Data

This directory is the default output location for TensorBoard event logs generated during model training by the Counter-Strike coach AI. It contains no code; only regeneratable training telemetry is written here at runtime.

## Technical Overview

The path is resolved as `RUNS_DIR = USER_DATA_ROOT/runs` in `core/config.py` (created automatically at import). When `BRAIN_DATA_ROOT` is configured, runs are written under that root instead of the in-repo directory. The `TensorBoardCallback` (`backend/nn/tensorboard_callback.py`) — Layer 2 of the Coach Introspection Observatory — keeps `RUNS_DIR/coach_training` as its constructor default, but the training entry point (`run_full_training_cycle.py`) scopes each run via `build_run_dir(model_type)`, which returns `RUNS_DIR/<model_type>/<UTC timestamp>-<device tag>` (e.g. `runs/jepa/20260817T142530Z-cpu`). The device tag comes from `resolve_device_tag()` (`cpu` / `cuda` / `rocm`), so a Windows CPU smoke run is never mistaken for a real Linux ROCm run in the dashboard.

## Key Components

- **TensorBoard Event Files**: Scalars (loss, learning rate, sparsity), histograms, and custom scalar layouts logged per epoch during training.
- **MaturityObservatory Scalars**: The observatory shares the same `SummaryWriter`, so its conviction/maturity signals land in the same logdir.
- **Per-Run Subdirectories**: Each training invocation gets its own `<model_type>/<UTC timestamp>-<device tag>` directory, keeping experiments separable in the TensorBoard UI instead of piling into one folder.

## Usage

1. **Training**: `python run_full_training_cycle.py` registers the TensorBoard callback by default; `--tb-logdir` overrides the destination (default `None` means a run-scoped directory from `build_run_dir()`; an explicit path disables run scoping and writes there directly) and `--no-tensorboard` disables logging. Full-scale training over the demo corpus runs on the Linux data box (see `docs/OPEN_ISSUES.md` §3); runs produced locally on Windows are dev-scale smoke runs, typically tagged `-cpu`.
2. **Viewing**: Launch `tensorboard --logdir Programma_CS2_RENAN/runs` and open the printed URL to inspect training curves.
3. **Cleanup**: Event files are volatile, regeneratable artifacts — old run directories can be deleted freely to save disk space.
