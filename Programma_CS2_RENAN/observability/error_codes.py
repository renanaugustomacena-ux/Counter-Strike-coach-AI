"""
Centralized Error Code Registry for the CS2 Analyzer project.

Every inline error code annotation (LS-01, RP-01, SE-04, etc.) is registered
here as a formal enum member with severity, module, description, and
remediation.

Usage::

    from Programma_CS2_RENAN.observability.error_codes import ErrorCode, log_with_code

    logger.warning(
        log_with_code(ErrorCode.LS_01, "RotatingFileHandler unavailable for %s"),
        log_path,
    )
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class Severity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ErrorCodeDef(NamedTuple):
    code: str
    severity: Severity
    module: str
    description: str
    remediation: str


class ErrorCode(Enum):
    """Every error code used across the project.

    Naming convention: <MODULE_PREFIX>_<NUMBER>

    Prefixes:
      LS  — Logger Setup
      RP  — RASP (Runtime Protection)
      DA  — Data Access
      P*  — Pipeline / Processing
      F*  — Feature / Fix
      SE  — Session Engine
      IM  — Ingestion Manager
      NN  — Neural Network
      G   — Game Analysis
      H   — Knowledge / HLTV
      CO  — Console Control
      R1  — Release / Manifest
    """

    # --- Logger Setup ---
    LS_01 = ErrorCodeDef(
        "LS-01", Severity.MEDIUM, "observability.logger_setup",
        "RotatingFileHandler unavailable — using plain FileHandler",
        "Check file permissions. On Windows, close other processes holding the log file.",
    )

    # --- RASP ---
    RP_01 = ErrorCodeDef(
        "RP-01", Severity.HIGH, "observability.rasp",
        "CS2_MANIFEST_KEY not set — using static fallback HMAC key",
        "Set CS2_MANIFEST_KEY environment variable for production builds.",
    )

    # --- Data Access ---
    DA_01_03 = ErrorCodeDef(
        "DA-01-03", Severity.LOW, "main",
        "Malformed JSON from database (pc_specs_json)",
        "Re-run hardware detection or manually edit player profile.",
    )

    # --- Pipeline ---
    P0_07 = ErrorCodeDef(
        "P0-07", Severity.LOW, "main",
        "Attribute initialized to prevent AttributeError",
        "No user action needed. Internal guard.",
    )
    P3_01 = ErrorCodeDef(
        "P3-01", Severity.LOW, "main",
        "Role enum canonical mapping",
        "No user action needed. Role key normalization.",
    )
    P4_B = ErrorCodeDef(
        "P4-B", Severity.MEDIUM, "core.session_engine",
        "Configurable zombie task threshold",
        "Adjust ZOMBIE_TASK_THRESHOLD_SECONDS setting if large demos are being reset.",
    )
    P7_01 = ErrorCodeDef(
        "P7-01", Severity.HIGH, "console",
        "API keys stored in plaintext settings.json",
        "Migrate to OS credential store via the keyring library.",
    )
    P7_02 = ErrorCodeDef(
        "P7-02", Severity.HIGH, "console",
        "Secret sanitization in error messages",
        "Ensure all secret keys are listed in the sanitization loop.",
    )

    # --- Feature / Fix ---
    F6_03 = ErrorCodeDef(
        "F6-03", Severity.LOW, "core.session_engine",
        "Explicit commit for trained sample count",
        "No user action needed.",
    )
    F6_06 = ErrorCodeDef(
        "F6-06", Severity.LOW, "core.session_engine",
        "sys.path bootstrap for direct script execution",
        "Remove when entrypoints are configured in pyproject.toml.",
    )
    F6_SE = ErrorCodeDef(
        "F6-SE", Severity.HIGH, "core.session_engine",
        "Backup failure — training gate engaged",
        "Resolve backup issue and restart session engine.",
    )
    F7_12 = ErrorCodeDef(
        "F7-12", Severity.LOW, "console",
        "sys.path bootstrap for root-level CLI entry points",
        "Remove when pip install -e . and python -m invocation are standard.",
    )
    F7_19 = ErrorCodeDef(
        "F7-19", Severity.LOW, "main",
        "Training status card KivyMD properties",
        "No user action needed.",
    )
    F7_30 = ErrorCodeDef(
        "F7-30", Severity.MEDIUM, "console",
        "API key masking shows last 4 characters",
        "Acceptable until keyring is integrated.",
    )

    # --- Session Engine ---
    SE_02 = ErrorCodeDef(
        "SE-02", Severity.MEDIUM, "core.session_engine",
        "Daemon thread join for graceful shutdown",
        "No user action needed.",
    )
    SE_04 = ErrorCodeDef(
        "SE-04", Severity.MEDIUM, "core.session_engine",
        "Config validation for zombie threshold",
        "Ensure ZOMBIE_TASK_THRESHOLD_SECONDS is a positive integer.",
    )
    SE_05 = ErrorCodeDef(
        "SE-05", Severity.HIGH, "core.session_engine",
        "Backup failure surfaced to UI",
        "Check backup manager configuration and disk space.",
    )
    SE_06 = ErrorCodeDef(
        "SE-06", Severity.LOW, "core.session_engine",
        "Short wait for faster shutdown response",
        "No user action needed.",
    )
    SE_07 = ErrorCodeDef(
        "SE-07", Severity.MEDIUM, "core.session_engine",
        "Settings reload once per scan cycle (TOCTOU window)",
        "Acceptable for MEDIUM severity. Next cycle picks up new values.",
    )

    # --- Ingestion Manager ---
    IM_03 = ErrorCodeDef(
        "IM-03", Severity.MEDIUM, "core.session_engine",
        "Event wait/clear ordering to prevent lost wakeup signals",
        "No user action needed.",
    )

    # --- Neural Network ---
    NN_02 = ErrorCodeDef(
        "NN-02", Severity.MEDIUM, "core.session_engine",
        "Module-level training lock prevents concurrent training",
        "No user action needed.",
    )

    # --- Game Analysis ---
    G_07 = ErrorCodeDef(
        "G-07", Severity.LOW, "core.session_engine",
        "Belief calibration wired to Teacher daemon",
        "No user action needed.",
    )

    # --- Knowledge / HLTV ---
    H_02 = ErrorCodeDef(
        "H-02", Severity.LOW, "core.session_engine",
        "One-time knowledge base population from pro demos",
        "No user action needed.",
    )

    # --- Console Control ---
    CO_01 = ErrorCodeDef(
        "CO-01", Severity.HIGH, "backend.control.console",
        "Console boot sequence failed",
        "Check database connectivity and disk space. Review console logs.",
    )
    CO_02 = ErrorCodeDef(
        "CO-02", Severity.MEDIUM, "backend.control.console",
        "Shutdown timeout — subsystems still running after grace period",
        "Check for stuck training or ingestion tasks. Process exit will force termination.",
    )
    CO_03 = ErrorCodeDef(
        "CO-03", Severity.HIGH, "backend.control.console",
        "Service monitor timeout — subprocess killed after 1h unresponsive",
        "Check service script for infinite loops or hung network calls.",
    )
    CO_04 = ErrorCodeDef(
        "CO-04", Severity.MEDIUM, "backend.control.console",
        "Service auto-restart exhausted — manual intervention required",
        "Investigate root cause of repeated crashes. Restart service manually.",
    )

    # --- Release / Manifest ---
    R1_12 = ErrorCodeDef(
        "R1-12", Severity.HIGH, "observability.rasp",
        "HMAC manifest signing for integrity verification",
        "Ensure CS2_MANIFEST_KEY is set at build time.",
    )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def log_with_code(error_code: ErrorCode, message: str) -> str:
    """Prefix a log message with its formal error code.

    Usage::

        logger.warning(log_with_code(ErrorCode.LS_01, "Handler unavailable for %s"), path)
    """
    defn = error_code.value
    return f"[{defn.code}] {message}"


def get_all_codes() -> list[dict]:
    """Return all error codes as a list of dicts for programmatic access."""
    return [
        {
            "code": e.value.code,
            "severity": e.value.severity.value,
            "module": e.value.module,
            "description": e.value.description,
            "remediation": e.value.remediation,
        }
        for e in ErrorCode
    ]
