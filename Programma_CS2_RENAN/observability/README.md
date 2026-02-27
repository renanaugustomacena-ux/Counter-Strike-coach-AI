# Observability & Runtime Protection

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Overview

Runtime application self-protection (RASP), structured logging with correlation IDs, and Sentry error tracking with PII scrubbing. Provides comprehensive observability for debugging, security auditing, and production monitoring.

## Key Components

### `rasp.py`
- **`RASPGuard`** — Runtime integrity verification via file hash checking
- **`run_rasp_audit()`** — Scans Python source files and compares against integrity manifest
- **`IntegrityError`** — Custom exception raised when hash mismatch detected
- Detects unauthorized code modifications, supply chain attacks, and file corruption
- Audit results logged with severity levels (CRITICAL, ERROR, WARNING)

### `logger_setup.py`
- **`get_logger(name)`** — Factory function for structured loggers
- Correlation ID injection for request tracing across modules
- JSON-formatted log output for machine parsing
- Log level filtering by module namespace
- Automatic redaction of sensitive fields (PII, secrets, tokens)
- File rotation with compression and retention policy

### `sentry_setup.py`
- **`init_sentry()`** — Initializes Sentry SDK with environment-specific DSN
- **`add_breadcrumb()`** — Contextual breadcrumb logging for error reports
- **PII scrubbing** — Automatic removal of sensitive data from stack traces
- Performance monitoring with transaction sampling
- Release tagging for version tracking
- Environment separation (development/staging/production)

## Structured Logging Pattern

```python
from observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.mymodule")
logger.info("Processing match", extra={"match_id": 12345, "map": "de_dust2"})
logger.error("Ingestion failed", extra={"file": "demo.dem", "error_code": "PARSE_ERROR"})
```

## RASP Audit Integration

RASP audit runs:
- On application startup (if `config.ENABLE_RASP=True`)
- Via CLI: `python macena.py sys rasp-audit`
- In CI/CD pipeline via `Goliath_Hospital.py` security checks

## Sentry Integration

Error tracking configuration:
- `SENTRY_DSN` loaded from environment variable
- Sample rate: 100% in development, 10% in production
- Traces sample rate: 10% for performance monitoring
- PII scrubbing via `before_send` hook

## Correlation IDs

All log entries include `correlation_id` for request tracing. Generated at ingestion/analysis/coaching entry points and propagated through call chain.

## Log Retention

- Development: 7 days
- Production: 90 days
- Critical errors: permanent retention in Sentry
