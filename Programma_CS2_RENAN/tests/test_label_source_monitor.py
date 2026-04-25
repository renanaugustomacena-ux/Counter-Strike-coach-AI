"""Unit tests for LabelSourceMonitor — the G-01 concept-routing telemetry.

The trainer marks every concept-alignment batch with
``label_source ∈ {round_stats, skipped_no_round_stats}``. The monitor
sliding-windows those decisions and alarms when SKIPPED batches dominate
— i.e. the canonical RoundStats outcome path is silently degrading.

These tests inject synthetic events with controlled timestamps so the
sliding window can be exercised deterministically without sleep().
"""

import pytest

from Programma_CS2_RENAN.observability.label_source_monitor import (
    LABEL_SOURCE_ROUND_STATS,
    LABEL_SOURCE_SKIPPED_NO_ROUND_STATS,
    LabelSourceMonitor,
)


def test_initial_state():
    m = LabelSourceMonitor()
    s = m.stats()
    assert s["window_samples"] == 0
    assert s["window_skipped"] == 0
    assert s["window_skipped_rate"] == 0.0
    assert s["alarm_active"] is False
    assert s["total_round_stats"] == 0
    assert s["total_skipped"] == 0


def test_record_unknown_source_raises():
    m = LabelSourceMonitor()
    with pytest.raises(ValueError):
        m.record("heuristic")  # legacy name no longer valid


def test_healthy_run_no_alarm():
    """A run where every batch hits round_stats must never alarm."""
    m = LabelSourceMonitor(min_samples=10)
    for i in range(200):
        m.record(LABEL_SOURCE_ROUND_STATS, ts=float(i))
    assert m.check_alarm() is False
    s = m.stats()
    assert s["total_round_stats"] == 200
    assert s["total_skipped"] == 0
    assert s["window_skipped_rate"] == 0.0


def test_skip_rate_above_1pct_alarms():
    """5 SKIPPED out of 200 (2.5%) must trip the 1% alarm."""
    m = LabelSourceMonitor(skipped_rate_threshold=0.01, min_samples=50)
    # Spread 5 SKIPPED throughout 200 events, all inside the window.
    for i in range(200):
        src = LABEL_SOURCE_SKIPPED_NO_ROUND_STATS if i % 40 == 0 else LABEL_SOURCE_ROUND_STATS
        m.record(src, ts=float(i))
    assert m.check_alarm() is True
    s = m.stats()
    assert s["window_skipped"] == 5
    assert s["window_samples"] == 200
    assert s["window_skipped_rate"] == pytest.approx(0.025)


def test_skip_rate_at_threshold_does_not_alarm():
    """Rate at exactly the threshold (not above) must NOT alarm.

    The check is strict-greater-than (rate > threshold). Use
    min_samples=100 to suppress the per-record alarm check until the
    full batch is recorded — otherwise the running rate can briefly
    exceed the threshold before settling at it.
    """
    m = LabelSourceMonitor(skipped_rate_threshold=0.05, min_samples=100)
    # 5 / 100 = 0.05 == threshold. Record 95 healthy first, then 5 SKIPPED.
    for i in range(95):
        m.record(LABEL_SOURCE_ROUND_STATS, ts=float(i))
    for i in range(95, 100):
        m.record(LABEL_SOURCE_SKIPPED_NO_ROUND_STATS, ts=float(i))
    assert m.check_alarm() is False
    s = m.stats()
    assert s["window_skipped_rate"] == pytest.approx(0.05)


def test_min_samples_gate_suppresses_early_alarm():
    """A 100% skip rate from 3 batches must not alarm until min_samples reached."""
    m = LabelSourceMonitor(skipped_rate_threshold=0.01, min_samples=50)
    for i in range(3):
        m.record(LABEL_SOURCE_SKIPPED_NO_ROUND_STATS, ts=float(i))
    assert m.check_alarm() is False  # below min_samples
    # Now push past min_samples — alarm should fire.
    for i in range(3, 60):
        m.record(LABEL_SOURCE_SKIPPED_NO_ROUND_STATS, ts=float(i))
    assert m.check_alarm() is True


def test_sliding_window_evicts_old_events():
    """Events older than window_seconds drop off.

    A burst of SKIPPED outside the window should not influence the
    in-window rate.
    """
    m = LabelSourceMonitor(window_seconds=300.0, skipped_rate_threshold=0.01, min_samples=50)
    # First inject 100 SKIPPED events at t=0..99 (would alarm if in-window).
    for i in range(100):
        m.record(LABEL_SOURCE_SKIPPED_NO_ROUND_STATS, ts=float(i))
    # Now inject 200 ROUND_STATS at t=10000..10199 — well past 5-min cutoff.
    # Each record() triggers eviction, so the old events get cleared.
    for i in range(200):
        m.record(LABEL_SOURCE_ROUND_STATS, ts=10000.0 + i)

    s = m.stats()
    assert s["window_samples"] == 200
    assert s["window_skipped"] == 0
    # The alarm latched True earlier from the SKIPPED burst — that latch
    # is intentional; reset() clears it.
    assert s["total_skipped"] == 100
    assert s["total_round_stats"] == 200


def test_reset_clears_alarm_and_window():
    m = LabelSourceMonitor(skipped_rate_threshold=0.01, min_samples=50)
    for i in range(60):
        m.record(LABEL_SOURCE_SKIPPED_NO_ROUND_STATS, ts=float(i))
    assert m.check_alarm() is True
    m.reset()
    s = m.stats()
    assert s["window_samples"] == 0
    assert s["alarm_active"] is False
    # Persistent counters survive reset.
    assert s["total_skipped"] == 60


def test_alarm_latched_no_log_spam():
    """Once alarm fires, repeat-recording does not retrigger the error log.

    The latch behaviour is what prevents spamming logger.error per batch.
    """
    m = LabelSourceMonitor(skipped_rate_threshold=0.01, min_samples=10)
    for i in range(20):
        m.record(LABEL_SOURCE_SKIPPED_NO_ROUND_STATS, ts=float(i))
    assert m.check_alarm() is True
    # Continue recording — alarm stays True without reset, no second error.
    for i in range(20, 40):
        m.record(LABEL_SOURCE_SKIPPED_NO_ROUND_STATS, ts=float(i))
    assert m.check_alarm() is True
