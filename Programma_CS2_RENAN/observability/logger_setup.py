"""
Centralized logging infrastructure for the CS2 Analyzer project.

All modules MUST use ``get_logger()`` (or ``get_tool_logger()`` for
standalone CLI tools) instead of configuring their own handlers.

Features:
  - JSON structured output for machine-parseable logs
  - RotatingFileHandler (5 MB × 3 backups) with PermissionError fallback
  - Thread-local correlation IDs for cross-component tracing
  - ``CS2_LOG_LEVEL`` env var override for zero-code debug sessions
  - ``get_tool_logger()`` factory for standalone tool scripts
  - ``configure_retention()`` for log file lifecycle management
"""

import json
import logging
import logging.handlers
import os
import threading
import uuid
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# Log directory, configurable after import via configure_log_dir().
# Defaults to None; get_logger() falls back to "logs" (relative) if unset.
_log_dir: str | None = None

# Thread-local storage for correlation IDs
_correlation_local: threading.local = threading.local()


# ---------------------------------------------------------------------------
# Correlation ID management
# ---------------------------------------------------------------------------


def set_correlation_id(cid: str | None = None) -> str:
    """Set a correlation ID for the current thread.  Returns the ID.

    Call at the start of a request, ingestion job, or training cycle to
    enable cross-component log tracing.
    """
    cid = cid or uuid.uuid4().hex[:12]
    _correlation_local.value = cid
    return cid


def get_correlation_id() -> Optional[str]:
    """Return the correlation ID for the current thread, or None."""
    return getattr(_correlation_local, "value", None)


class _CorrelationFilter(logging.Filter):
    """Inject the thread-local correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = getattr(_correlation_local, "value", None)  # type: ignore[attr-defined]
        return True


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for machine-parseable output.

    Each line emitted is a self-contained JSON object with guaranteed
    fields: ``ts``, ``lvl``, ``mod``, ``thread``, ``msg``.
    Optional fields: ``cid`` (correlation ID), ``code`` (error code),
    ``exc_type``, ``exc_msg``, ``traceback``.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "lvl": record.levelname,
            "mod": record.name,
            "thread": record.threadName,
            "msg": record.getMessage(),
        }

        # Correlation ID (injected by _CorrelationFilter)
        cid = getattr(record, "correlation_id", None)
        if cid:
            log_entry["cid"] = cid

        # Error code (set via extra= kwarg or LoggerAdapter)
        error_code = getattr(record, "error_code", None)
        if error_code:
            log_entry["code"] = error_code

        # Exception info
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exc_type"] = record.exc_info[0].__name__
            log_entry["exc_msg"] = str(record.exc_info[1])
            log_entry["traceback"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Log level resolution
# ---------------------------------------------------------------------------


def _resolve_log_level() -> int:
    """Resolve log level from ``CS2_LOG_LEVEL`` env var, defaulting to INFO."""
    env_level = os.environ.get("CS2_LOG_LEVEL", "").upper()
    return getattr(logging, env_level, logging.INFO)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def configure_log_dir(log_dir: str) -> None:
    """Set the log directory.  Called by config.py after LOG_DIR is resolved.

    This function exists to break the circular dependency between config.py
    and logger_setup.py: config needs get_logger() at import time, but
    get_logger() used to import LOG_DIR from config.  Now config calls
    configure_log_dir(LOG_DIR) after LOG_DIR is computed, and this module
    never imports from config.
    """
    global _log_dir
    _log_dir = log_dir


# ---------------------------------------------------------------------------
# File handler factory
# ---------------------------------------------------------------------------


def _create_file_handler(log_path: str, formatter: logging.Formatter) -> logging.Handler:
    """Create a RotatingFileHandler with fallback to plain FileHandler.

    RotatingFileHandler provides 5 MB rotation with 3 backups, preventing
    unbounded disk growth.  Falls back to plain FileHandler if the OS raises
    PermissionError (Windows daemon subprocesses holding competing handles).
    """
    try:
        handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
    except PermissionError:
        # LS-01: Plain FileHandler has no size rotation — log can grow unbounded.
        # This is acceptable only as a temporary fallback on Windows when another
        # process holds the log file handle. Log a warning so operators are aware.
        handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        logging.getLogger("cs2analyzer.logger_setup").warning(
            "[LS-01] RotatingFileHandler unavailable (PermissionError) — "
            "using plain FileHandler for %s. Log rotation is disabled.", log_path,
        )
    handler.setFormatter(formatter)
    return handler


# ---------------------------------------------------------------------------
# Core logger factory
# ---------------------------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """Return a logger wired to the centralized JSON file + console handlers.

    Safe to call repeatedly — handlers are attached only once.
    All loggers share the ``cs2_analyzer.log`` sink.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(_resolve_log_level())

    formatter = JSONFormatter()

    # Use log directory set by configure_log_dir(), fall back to relative "logs"
    log_dir = _log_dir or "logs"
    os.makedirs(log_dir, exist_ok=True)

    file_handler = _create_file_handler(
        os.path.join(log_dir, "cs2_analyzer.log"), formatter
    )

    # Console handler uses human-readable format, WARNING threshold
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | [%(threadName)s] | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.WARNING)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addFilter(_CorrelationFilter())
    logger.propagate = False

    return logger


# ---------------------------------------------------------------------------
# Tool logger factory (for standalone CLI scripts)
# ---------------------------------------------------------------------------


def get_tool_logger(tool_name: str) -> logging.Logger:
    """Logger factory for standalone tool scripts.

    Produces a logger named ``cs2analyzer.tools.<tool_name>`` with:
    - JSON file handler in ``logs/tools/<tool_name>_<timestamp>.json``
    - Console handler at WARNING (for Rich-based tools that own stdout)
    - Correlation ID filter

    The tool log directory is created automatically.
    """
    canonical_name = f"cs2analyzer.tools.{tool_name}"
    logger = logging.getLogger(canonical_name)

    if logger.handlers:
        return logger

    logger.setLevel(_resolve_log_level())

    tool_log_dir = os.path.join(_log_dir or "logs", "tools")
    os.makedirs(tool_log_dir, exist_ok=True)

    log_file = os.path.join(
        tool_log_dir,
        f"{tool_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(JSONFormatter())
    logger.addHandler(fh)
    logger.addFilter(_CorrelationFilter())
    logger.propagate = False

    return logger


# ---------------------------------------------------------------------------
# Runtime reconfiguration
# ---------------------------------------------------------------------------


def configure_log_level(level: int) -> None:
    """Change the log level of all cs2analyzer loggers at runtime.

    Useful for debug sessions: ``configure_log_level(logging.DEBUG)``.
    """
    manager = logging.Logger.manager
    for name, logger_ref in manager.loggerDict.items():
        if isinstance(logger_ref, logging.Logger) and name.startswith("cs2analyzer"):
            logger_ref.setLevel(level)


def configure_retention(max_days: int = 30) -> None:
    """Purge log files older than *max_days* from the log directory.

    Call at application startup to enforce retention policy.
    Safe to call multiple times.  Best-effort — errors are silently ignored.
    """
    import time as _time

    log_dir = _log_dir or "logs"
    if not os.path.isdir(log_dir):
        return

    cutoff = _time.time() - (max_days * 86400)

    for dirpath, _dirnames, filenames in os.walk(log_dir):
        for fname in filenames:
            if fname.endswith((".log", ".json")):
                fp = os.path.join(dirpath, fname)
                try:
                    if os.path.getmtime(fp) < cutoff:
                        os.remove(fp)
                except OSError:
                    pass  # Best-effort cleanup


# ---------------------------------------------------------------------------
# Singleton logger instance
# ---------------------------------------------------------------------------

app_logger = get_logger("cs2analyzer.app")
