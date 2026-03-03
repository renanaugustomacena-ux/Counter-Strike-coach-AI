import logging
import logging.handlers
import os

# Module-level log directory, configurable after import via configure_log_dir().
# Defaults to None; get_logger() falls back to "logs" (relative) if unset.
_log_dir: str | None = None


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
        handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    handler.setFormatter(formatter)
    return handler


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | [%(threadName)s] | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    # Use log directory set by configure_log_dir(), fall back to relative "logs"
    log_dir = _log_dir or "logs"
    os.makedirs(log_dir, exist_ok=True)

    file_handler = _create_file_handler(
        os.path.join(log_dir, "cs2_analyzer.log"), formatter
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger


def configure_log_level(level: int) -> None:
    """Change the log level of all cs2analyzer loggers at runtime.

    Useful for debug sessions: ``configure_log_level(logging.DEBUG)``.
    """
    manager = logging.Logger.manager
    for name, logger_ref in manager.loggerDict.items():
        if isinstance(logger_ref, logging.Logger) and name.startswith("cs2analyzer"):
            logger_ref.setLevel(level)


# Singleton logger instance
app_logger = get_logger("CS2_Coach_App")
