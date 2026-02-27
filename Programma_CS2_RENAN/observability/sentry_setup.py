"""Sentry SDK integration for remote error reporting (Task 2.21.1).

Double opt-in: requires both ``enabled=True`` AND a valid ``dsn``.
PII is stripped via ``before_send`` — user home paths and server names
are replaced before any event leaves the process.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.sentry")

_initialized: bool = False


# ---------------------------------------------------------------------------
# PII Scrubbing
# ---------------------------------------------------------------------------


def _scrub_string(value: str, home: str) -> str:
    """Replace occurrences of the user home directory in *value*."""
    if home and home in value:
        return value.replace(home, "<user_home>")
    return value


def _before_send(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Strip PII from every outgoing Sentry event."""
    home = str(Path.home())

    # 1. Scrub server_name (machine hostname)
    if "server_name" in event:
        event["server_name"] = "redacted"

    # 2. Scrub exception stacktrace filenames
    for exc in event.get("exception", {}).get("values", []):
        for frame in exc.get("stacktrace", {}).get("frames", []):
            if "filename" in frame:
                frame["filename"] = _scrub_string(frame["filename"], home)
            if "abs_path" in frame:
                frame["abs_path"] = _scrub_string(frame["abs_path"], home)

    # 3. Scrub breadcrumb data
    for crumb in event.get("breadcrumbs", {}).get("values", []):
        if "message" in crumb and isinstance(crumb["message"], str):
            crumb["message"] = _scrub_string(crumb["message"], home)
        for key, val in crumb.get("data", {}).items():
            if isinstance(val, str):
                crumb["data"][key] = _scrub_string(val, home)

    return event


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def init_sentry(
    dsn: Optional[str] = None,
    enabled: bool = False,
) -> bool:
    """Initialise the Sentry SDK.

    Returns ``True`` only when Sentry is successfully initialised.
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _initialized
    if _initialized:
        return True

    # Gate 1: pytest detection
    if "pytest" in sys.modules:
        logger.debug("Sentry skipped: pytest detected")
        return False

    # Gate 2: explicit opt-in
    if not enabled:
        logger.debug("Sentry disabled by user setting")
        return False

    # Gate 3: DSN provided
    if not dsn or not dsn.strip():
        logger.debug("Sentry DSN not configured")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        # Resolve release version
        try:
            from Programma_CS2_RENAN import __version__ as release
        except (ImportError, AttributeError):
            release = "unknown"

        sentry_sdk.init(
            dsn=dsn.strip(),
            traces_sample_rate=0.1,
            send_default_pii=False,
            before_send=_before_send,
            release=release,
            integrations=[
                LoggingIntegration(
                    level=logging.WARNING,
                    event_level=logging.ERROR,
                ),
            ],
        )

        _initialized = True
        logger.info("Sentry error reporting initialised (release=%s)", release)
        return True

    except Exception as exc:
        logger.error("Sentry initialisation failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Breadcrumb helper
# ---------------------------------------------------------------------------


def add_breadcrumb(
    category: str,
    message: str,
    level: str = "info",
    **data: Any,
) -> None:
    """Record a Sentry breadcrumb if the SDK is active, no-op otherwise."""
    if not _initialized:
        return
    try:
        import sentry_sdk

        sentry_sdk.add_breadcrumb(
            category=category,
            message=message,
            level=level,
            data=data if data else None,
        )
    except Exception as e:
        _ = e  # Intentionally suppressed
