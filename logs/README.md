> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Centralized System Logs

This directory collects runtime logs from the repo-root operator tooling (the Goliath operator, the developer console, maintenance tools) and serves as the fallback sink for the backend logging stack. The application itself resolves its log directory from configuration (`LOG_DIR = <USER_DATA_ROOT>/logs`, default `Programma_CS2_RENAN/logs`, overridable via `BRAIN_DATA_ROOT` / `CUSTOM_STORAGE_PATH`), so the primary `cs2_analyzer.log` normally lands there, not here.

## Technical Overview

The logging architecture is designed for high-granularity monitoring of the Counter-Strike coach backend. Logging is configured by `Programma_CS2_RENAN/observability/logger_setup.py`: all loggers share a single `cs2_analyzer.log` sink (structured, machine-parseable JSON output), and standalone tool runs additionally write timestamped JSON logs under `tools/`. `core/config.py` wires the resolved `LOG_DIR` into `logger_setup` via `configure_log_dir()`; scripts that use `logger_setup` without that wiring fall back to the relative path `logs/` — this directory, when run from the repo root. The primary goal is to ensure that performance bottlenecks, ingestion failures, and model drift are identified and resolved quickly.

## Key Components

All files below are generated at runtime and gitignored (only the READMEs are tracked):

- **`cs2_analyzer.log`**: Fallback copy of the main backend/analysis log (JSON lines: errors with stack traces, per-demo parsing and ingestion task events). The primary copy lives in `<USER_DATA_ROOT>/logs/`.
- **`tools/`**: Per-tool JSON run logs (`<tool_name>_<YYYYMMDD_HHMMSS>.json`) from `get_tool_logger()`, created when CLI tools (e.g. `tools/build_pipeline.py`) run from the repo root.
- **`goliath_master_<YYYYMMDD>.json`**: Daily master log of the Goliath operator (`goliath.py`), appended across runs.
- **`spawn_<tool>_<HHMMSS>.log`**: stderr of background tools launched via the console's `svc spawn` command (`console.py`).
- **`wipe_audit_<YYYYMMDD>.jsonl`**: Append-only audit trail written by `tools/wipe_for_reingest_safe.py` for every wipe/restore operation.

## Directory Structure

```text
logs/
├── cs2_analyzer.log              # Fallback backend/analysis log (generated at runtime)
├── tools/                        # Timestamped JSON logs from tool runs (generated)
├── goliath_master_<date>.json    # Goliath operator daily master log (generated)
├── spawn_<tool>_<time>.log       # stderr of console-spawned background tools (generated)
├── wipe_audit_<date>.jsonl       # Wipe/restore audit trail (generated)
├── README.md                     # This documentation
├── README_IT.md                  # Italian version
└── README_PT.md                  # Portuguese version
```

## Usage

### Real-time Monitoring
To monitor the system logs in real-time during a large-scale ingestion or training session:
```bash
tail -f logs/cs2_analyzer.log
```

### Log Rotation
A `RotatingFileHandler` rotates `cs2_analyzer.log` at 5 MB, keeping 3 historical versions (e.g., `cs2_analyzer.log.1`) to prevent disk space exhaustion. If the handler cannot be created (PermissionError), the setup falls back to a plain `FileHandler` (no rotation). Rotation is only safe for today's single-writer usage — when two processes share the same rotating log file, rotation can race (open issue F-0011 in `docs/OPEN_ISSUES.md`). The other files here (`goliath_master_*`, `spawn_*`, `wipe_audit_*`) are not rotated; `configure_retention()` in `logger_setup.py` can purge `.log`/`.json` files older than 30 days.

### Filtering for Errors
To quickly identify critical issues within the logs:
```bash
grep "ERROR" logs/cs2_analyzer.log
```
