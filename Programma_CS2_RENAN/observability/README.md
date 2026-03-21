# Observability & Runtime Protection

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Authority:** `Programma_CS2_RENAN/observability/`
**Owner:** Macena CS2 Analyzer core infrastructure

## Introduction

This package provides the three pillars of runtime observability for the CS2 Analyzer:
structured logging, integrity protection, and remote error tracking. Every module in the
project routes its diagnostics through this package, ensuring a single, consistent
observability surface. The design prioritises deterministic behaviour, zero silent
failures, and strict PII isolation before any data leaves the process boundary.

## File Inventory

| File | Purpose | Key Exports |
|------|---------|-------------|
| `logger_setup.py` | Centralised structured JSON logging with correlation IDs | `get_logger()`, `get_tool_logger()`, `set_correlation_id()`, `configure_log_dir()`, `configure_retention()` |
| `rasp.py` | Runtime Application Self-Protection integrity guard | `RASPGuard`, `run_rasp_audit()`, `IntegrityError` |
| `sentry_setup.py` | Sentry SDK integration with double opt-in and PII scrubbing | `init_sentry()`, `add_breadcrumb()` |
| `error_codes.py` | Centralised error code registry with severity and remediation | `ErrorCode`, `log_with_code()`, `get_all_codes()` |
| `exceptions.py` | Domain exception hierarchy rooted at `CS2AnalyzerError` | `CS2AnalyzerError`, `ConfigurationError`, `DatabaseError`, `IngestionError`, `TrainingError`, `IntegrationError`, `UIError` |
| `__init__.py` | Package marker | -- |

## Architecture & Concepts

### Structured Logging (`logger_setup.py`)

All loggers are created via `get_logger("cs2analyzer.<module>")`. The factory wires
each logger to two handlers:

1. **File handler** -- `RotatingFileHandler` writing JSON lines to `cs2_analyzer.log`
   (5 MB rotation, 3 backups). Falls back to plain `FileHandler` when a
   `PermissionError` occurs (Windows lock contention, annotated as `LS-01`).
2. **Console handler** -- human-readable format at `WARNING` threshold, keeping
   stdout clean during normal operation.

Every log record is enriched by `_CorrelationFilter`, which injects the thread-local
`correlation_id` set via `set_correlation_id()`. This enables end-to-end tracing of a
single ingestion job, training cycle, or coaching session across all modules.

The log level is resolved at logger creation time from the `CS2_LOG_LEVEL` environment
variable (e.g. `CS2_LOG_LEVEL=DEBUG`), allowing zero-code debug sessions without
modifying source files. Runtime reconfiguration is also possible via
`configure_log_level(logging.DEBUG)`.

Standalone CLI tools (validators, diagnostics) use `get_tool_logger(tool_name)`, which
writes to a dedicated `logs/tools/<tool_name>_<timestamp>.json` file to avoid
polluting the main application log.

`configure_retention(max_days=30)` enforces a log lifecycle policy by purging `.log`
and `.json` files older than the retention window. Best-effort -- OS errors are silently
ignored to avoid crashing the application over housekeeping.

### RASP Integrity Guard (`rasp.py`)

`RASPGuard` verifies that no Python source file has been tampered with since the last
build or manifest generation. It reads `core/integrity_manifest.json`, which maps
relative file paths to their SHA-256 hashes, and compares each entry against the live
filesystem.

Key behaviours:

- **HMAC signing** (`R1-12`): the manifest itself is signed with an HMAC-SHA256 key.
  Production builds inject the key via `CS2_MANIFEST_KEY`; development falls back to
  a static key with a logged warning (`RP-01`).
- **Frozen binary support**: when running inside a PyInstaller bundle, the manifest
  is resolved from `sys._MEIPASS` with multiple candidate paths.
- **Convenience entry point**: `run_rasp_audit(project_root)` instantiates the guard,
  runs the check, and logs all violations at `CRITICAL` level.

### Sentry Error Tracking (`sentry_setup.py`)

Remote error reporting follows a **double opt-in** model: both `enabled=True` and a
valid `dsn` string must be provided. This prevents accidental telemetry leaks.

PII is stripped in the `_before_send` hook before any event leaves the process:

- `server_name` is replaced with `"redacted"`.
- Stack-trace filenames containing the user home directory are scrubbed.
- Breadcrumb messages and data fields are sanitised identically.

The SDK is initialised with `send_default_pii=False` and a 10% `traces_sample_rate`
for lightweight performance monitoring. The `LoggingIntegration` captures WARNING-level
breadcrumbs and escalates ERROR-level records to full Sentry events.

`add_breadcrumb()` is a no-op when Sentry is not initialised, making it safe to call
unconditionally throughout the codebase.

### Error Code Registry (`error_codes.py`)

Every annotated error code in the project (e.g. `LS-01`, `RP-01`, `SE-04`) is
registered as an `ErrorCode` enum member carrying severity, owning module, description,
and remediation guidance. `log_with_code(ErrorCode.LS_01, "message")` prefixes the
message with the formal code for machine-parseable log grepping.

### Exception Hierarchy (`exceptions.py`)

All domain exceptions inherit from `CS2AnalyzerError`, which accepts an optional
`error_code` parameter for structured logging. Subtypes include
`ConfigurationError`, `DatabaseError`, `IngestionError`, `TrainingError`,
`IntegrationError`, and `UIError`.

## Integration

| Consumer | Usage |
|----------|-------|
| `core/session_engine.py` | `set_correlation_id()` at daemon cycle start; `run_rasp_audit()` at boot |
| `core/config.py` | `configure_log_dir(LOG_DIR)` after path resolution to break circular import |
| `ingestion/` pipeline | `get_logger()` + correlation IDs for per-demo tracing |
| `backend/nn/` training | `get_logger()` for epoch/loss logging; `add_breadcrumb()` at checkpoints |
| `apps/qt_app/` | `init_sentry()` at application startup with user-consented DSN |
| `tools/` scripts | `get_tool_logger()` for isolated tool diagnostics |
| Pre-commit hooks | `run_rasp_audit()` via `tools/headless_validator.py` |

## Development Notes

- **Circular import guard**: `config.py` needs `get_logger()` at import time, but
  `get_logger()` must not import from `config`. The solution is `configure_log_dir()`,
  called by `config.py` after `LOG_DIR` is computed.
- **Thread safety**: `_correlation_local` uses `threading.local()`, so correlation IDs
  are isolated per thread. Daemon threads in the Quad-Daemon engine each set their
  own ID at cycle start.
- **Testing**: in test suites, `CS2_LOG_LEVEL=DEBUG` and `configure_log_dir(tmp_path)`
  redirect all output to a temporary directory. Sentry is automatically skipped when
  `pytest` is detected in `sys.modules`.
- **Pre-commit**: the `integrity-manifest` hook regenerates and signs the manifest;
  `headless_validator.py` runs `run_rasp_audit()` to verify it.
