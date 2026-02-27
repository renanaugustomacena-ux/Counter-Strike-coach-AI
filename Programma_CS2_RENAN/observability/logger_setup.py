import logging
import os


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )

    # Resolve log directory from centralized config (falls back to relative)
    try:
        from Programma_CS2_RENAN.core.config import LOG_DIR

        log_dir = LOG_DIR
    except ImportError:
        log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Plain FileHandler avoids the Windows PermissionError that
    # TimedRotatingFileHandler causes when the daemon subprocess
    # holds a competing file handle during log rotation.
    file_handler = logging.FileHandler(
        os.path.join(log_dir, "cs2_analyzer.log"),
        mode="a",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger


# Singleton logger instance
app_logger = get_logger("CS2_Coach_App")
