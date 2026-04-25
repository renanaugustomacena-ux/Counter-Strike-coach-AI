"""LabelSourceMonitor — telemetry for the G-01 concept-labelling path choice.

Per CS2_Coach_Modernization_Report.pdf §9 and the N=260 supplement §5.1
item 3: every concept-alignment batch must report whether its labels came
from the canonical RoundStats outcome path or fell through to a skip
(no RoundStats available, concept alignment skipped, InfoNCE-only loss).

This module owns:
  - the per-batch ``label_source`` enum (``LABEL_SOURCE_ROUND_STATS`` /
    ``LABEL_SOURCE_SKIPPED_NO_ROUND_STATS``),
  - a sliding-window counter that alarms when the SKIPPED rate exceeds
    a threshold (default 1% over a 5-minute window).

Why a 5-minute window: the report specifies "alert if heuristic exceeds
1% of batches over any 5-minute window". A sliding window is preferable
to all-time totals because a regression in mid-training (e.g. a data
pipeline change that drops RoundStats coverage) would otherwise be
diluted by hours of healthy prior batches.

The monitor is a passive recorder — it does not block training. The
alarm is a loud ``logger.error`` plus a one-shot ``alarm_active`` flag
that the caller can poll to surface in dashboards / CI.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Tuple

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.label_source")

# Canonical enum values — anything else is a contract bug.
LABEL_SOURCE_ROUND_STATS = "round_stats"
LABEL_SOURCE_SKIPPED_NO_ROUND_STATS = "skipped_no_round_stats"

VALID_LABEL_SOURCES = frozenset({LABEL_SOURCE_ROUND_STATS, LABEL_SOURCE_SKIPPED_NO_ROUND_STATS})


class LabelSourceMonitor:
    """Sliding-window monitor for concept-label routing decisions.

    Thread-safe: ``record()`` and ``check_alarm()`` may be called from
    DataLoader workers, the main training loop, or evaluation hooks
    concurrently.

    Args:
        window_seconds: Width of the sliding window in seconds. Default
            300 (= 5 minutes per the report spec).
        skipped_rate_threshold: Maximum tolerated SKIPPED rate inside the
            window before the alarm fires. Default 0.01 (= 1%).
        min_samples: Minimum sample count inside the window before the
            alarm can fire. Prevents single-batch false positives during
            warm-up. Default 50.
    """

    def __init__(
        self,
        window_seconds: float = 300.0,
        skipped_rate_threshold: float = 0.01,
        min_samples: int = 50,
    ):
        self.window_seconds = float(window_seconds)
        self.skipped_rate_threshold = float(skipped_rate_threshold)
        self.min_samples = int(min_samples)

        self._events: Deque[Tuple[float, str]] = deque()
        self._lock = threading.Lock()

        # Persistent counters across the whole run (independent of window).
        self.total_round_stats: int = 0
        self.total_skipped: int = 0

        # One-shot alarm latch — flips True once threshold is crossed,
        # stays True until reset() is called. Prevents log spam.
        self.alarm_active: bool = False

    def record(self, label_source: str, *, ts: float | None = None) -> None:
        """Record one batch's label_source decision.

        Raises ValueError if `label_source` is not one of VALID_LABEL_SOURCES
        — a contract violation we want loud, not silent.
        """
        if label_source not in VALID_LABEL_SOURCES:
            raise ValueError(
                f"Unknown label_source {label_source!r}; expected one of "
                f"{sorted(VALID_LABEL_SOURCES)}"
            )
        ts = time.monotonic() if ts is None else float(ts)
        with self._lock:
            self._events.append((ts, label_source))
            if label_source == LABEL_SOURCE_ROUND_STATS:
                self.total_round_stats += 1
            else:
                self.total_skipped += 1
            self._evict_locked(ts)
            self._check_alarm_locked()

    def _evict_locked(self, now: float) -> None:
        cutoff = now - self.window_seconds
        events = self._events
        while events and events[0][0] < cutoff:
            events.popleft()

    def _check_alarm_locked(self) -> None:
        n = len(self._events)
        if n < self.min_samples:
            return
        n_skipped = sum(1 for _, src in self._events if src == LABEL_SOURCE_SKIPPED_NO_ROUND_STATS)
        rate = n_skipped / n if n else 0.0
        if rate > self.skipped_rate_threshold and not self.alarm_active:
            self.alarm_active = True
            logger.error(
                "G-01 ALARM: label_source SKIPPED rate %.2f%% (%d/%d) over the "
                "last %.0fs exceeds the %.2f%% threshold. The concept-alignment "
                "path is degrading toward InfoNCE-only — investigate RoundStats "
                "coverage upstream.",
                100.0 * rate,
                n_skipped,
                n,
                self.window_seconds,
                100.0 * self.skipped_rate_threshold,
            )

    def check_alarm(self) -> bool:
        """Return whether the alarm latch is currently active."""
        with self._lock:
            return self.alarm_active

    def reset(self) -> None:
        """Clear the alarm latch and the sliding-window history.

        Persistent counters (``total_*``) are NOT reset — they remain a
        run-long aggregate. Use this after acting on an alarm to avoid
        log spam without losing audit trail.
        """
        with self._lock:
            self.alarm_active = False
            self._events.clear()

    def stats(self) -> dict:
        """Return a snapshot of monitor state. Safe under contention."""
        with self._lock:
            n = len(self._events)
            n_skipped = sum(
                1 for _, src in self._events if src == LABEL_SOURCE_SKIPPED_NO_ROUND_STATS
            )
            return {
                "window_seconds": self.window_seconds,
                "skipped_rate_threshold": self.skipped_rate_threshold,
                "min_samples": self.min_samples,
                "window_samples": n,
                "window_skipped": n_skipped,
                "window_skipped_rate": (n_skipped / n) if n else 0.0,
                "alarm_active": self.alarm_active,
                "total_round_stats": self.total_round_stats,
                "total_skipped": self.total_skipped,
            }
