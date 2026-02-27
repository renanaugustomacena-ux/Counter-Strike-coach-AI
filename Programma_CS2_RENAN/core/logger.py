# DEPRECATED: This module is superseded by observability/logger_setup.py.
# Use `from Programma_CS2_RENAN.observability.logger_setup import get_logger` instead.
# This file is kept only for legacy compatibility; do NOT use it in new code.
# Potential issue: if both modules are imported, handlers accumulate on the root
# logger causing duplicate log entries.
import logging
import os
import sys
from pathlib import Path

from Programma_CS2_RENAN.core.config import LOG_DIR


# --- Configuration (Legacy) ---
def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Creates a configured logger instance.
    """
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Console Handler (Stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (Optional)
    if log_file:
        file_handler = logging.FileHandler(os.path.join(LOG_DIR, log_file))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Default Application Logger
app_logger = setup_logger("MacenaCS2", "app_runtime.log")
