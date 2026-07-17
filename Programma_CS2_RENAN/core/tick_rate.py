"""26-NORM-01 SSOT — per-demo tick rate.

The ONLY module in the codebase allowed to spell the CS2 default tick
rate. A 64.0 assumed for a 128-tick demo silently halves every derived
time window (trade windows, flash windows, LTC dt, miner windows), which
is why the supreme invariant reads "tick rate SEMPRE per-demo
dall'header/metadata, mai 64 hardcodato".

Resolution contract (owner decision 2026-07-17, C11):
    shard/match metadata rate  →  .dem header rate (GAP-01)  →  None.
``None`` is the honest sentinel: callers that MUST render something
(e.g. UI playback with no demo loaded) may fall back to
``DEFAULT_TICK_RATE`` explicitly — and that import is the audit trail.
``Programma_CS2_RENAN/tests/test_tick_rate_ssot.py`` forbids new bare
literals anywhere else.
"""

from __future__ import annotations

import logging

_logger = logging.getLogger("cs2analyzer.tick_rate")

# The ONLY sanctioned tick-rate literal in the codebase (26-NORM-01).
DEFAULT_TICK_RATE: int = 64

# GAP-01 / DS-07 validity window for header- or metadata-derived rates.
TICK_RATE_MIN: float = 32.0
TICK_RATE_MAX: float = 256.0


def is_valid_tick_rate(rate: object) -> bool:
    """True when ``rate`` parses to a float inside the GAP-01 window."""
    try:
        value = float(rate)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    return TICK_RATE_MIN <= value <= TICK_RATE_MAX


def resolve_tick_rate(
    metadata_rate: object = None,
    header_rate: object = None,
    *,
    context: str = "",
) -> float | None:
    """Resolve a per-demo tick rate: metadata first, then header, else None.

    Never fabricates a default — returning ``None`` forces the caller to
    decide (and log) what a missing rate means for its own semantics.
    Out-of-range candidates are rejected loudly, not clamped.
    """
    for source, rate in (("metadata", metadata_rate), ("header", header_rate)):
        if rate is None:
            continue
        if is_valid_tick_rate(rate):
            return float(rate)  # type: ignore[arg-type]
        _logger.warning(
            "26-NORM-01: rejected out-of-range %s tick rate %r%s",
            source,
            rate,
            f" ({context})" if context else "",
        )
    return None
