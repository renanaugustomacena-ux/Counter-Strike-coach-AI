> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Centralized System Logs

This directory serves as the centralized hub for system-wide observability and diagnostic data. It aggregates logs from the backend engine, match ingestion services, and AI inference modules to provide a comprehensive view of the system's operational health.

## Technical Overview

The logging architecture is designed for high-granularity monitoring of the Counter-Strike coach backend. Logging is configured by `Programma_CS2_RENAN/observability/logger_setup.py`: all loggers share a single `cs2_analyzer.log` sink (structured, machine-parseable JSON output), and standalone tool runs additionally write timestamped JSON reports under `tools/`. The primary goal is to ensure that performance bottlenecks, ingestion failures, and model drift are identified and resolved quickly.

## Key Components

- **`cs2_analyzer.log`**: The primary log file for the backend analysis engine (generated at runtime). It tracks:
    - **Error Monitoring**: Detailed stack traces for API failures, database connection issues, and demo parsing errors.
    - **Ingestion Progress**: Per-demo parsing and ingestion task events.
    - **System Health**: Periodic heartbeats from background daemons and the HLTV sync service.
- **`tools/`**: Per-tool JSON run reports (`<tool_name>_<timestamp>.json`), created when CLI tools run with logging enabled.

## Directory Structure

```text
logs/
├── cs2_analyzer.log        # Main backend and analysis log (generated at runtime)
├── tools/                  # Timestamped JSON reports from tool runs (generated)
├── README.md               # This documentation
├── README_IT.md            # Italian version
└── README_PT.md            # Portuguese version
```

## Usage

### Real-time Monitoring
To monitor the system logs in real-time during a large-scale ingestion or training session:
```bash
tail -f logs/cs2_analyzer.log
```

### Log Rotation
A `RotatingFileHandler` rotates the log at 5 MB, keeping 3 historical versions (e.g., `cs2_analyzer.log.1`) to prevent disk space exhaustion. If the handler cannot be created (PermissionError), the setup falls back to a plain `FileHandler`.

### Filtering for Errors
To quickly identify critical issues within the logs:
```bash
grep "ERROR" logs/cs2_analyzer.log
```
