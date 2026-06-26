"""C1.2 (AUDIT 26-TICK-01 / 26-TICK-03): per-demo tick-rate propagation into RAP path.

Locks in the plumbing that activates the tick-rate-aware PlayerKnowledge builder and the
LTC inter-tick ``dt`` for non-64-tick demos (e.g. 128-tick FACEIT), without needing real
demo data — the end-to-end effect is verified on real 128-tick demos at training time.

  1. ``_resolve_tick_rate`` reads ``MatchMetadata.tick_rate`` from the shared metadata
     cache (no extra DB round-trip), falls back to 64 when absent, and rejects
     out-of-range values (valid window [32, 256], per DS-07).
  2. ``_rap_compute_timespans`` uses the per-item ``tick_rates`` to scale the LTC ``dt``:
     a 128-tick demo must produce half the elapsed seconds of a 64-tick demo for the
     same tick delta (otherwise the Liquid Time-Constant integrates on a 2x-wrong scale).
"""

from __future__ import annotations

from types import SimpleNamespace

from Programma_CS2_RENAN.backend.nn.training_orchestrator import TrainingOrchestrator


class TestResolveTickRate:
    """_resolve_tick_rate maps cached MatchMetadata to a safe per-demo tick rate."""

    def test_reads_tick_rate_from_cached_metadata(self):
        cache = {7: SimpleNamespace(tick_rate=128.0)}
        assert TrainingOrchestrator._resolve_tick_rate(7, None, cache) == 128

    def test_defaults_to_64_when_metadata_missing(self):
        assert TrainingOrchestrator._resolve_tick_rate(None, None, {}) == 64

    def test_defaults_to_64_when_meta_is_none(self):
        cache = {3: None}
        assert TrainingOrchestrator._resolve_tick_rate(3, None, cache) == 64

    def test_rejects_out_of_range_tick_rate(self):
        # Absurd values (0, 9999) fall back to the safe default rather than poisoning
        # the memory/flash windows and the LTC dt downstream.
        cache = {1: SimpleNamespace(tick_rate=9999), 2: SimpleNamespace(tick_rate=0)}
        assert TrainingOrchestrator._resolve_tick_rate(1, None, cache) == 64
        assert TrainingOrchestrator._resolve_tick_rate(2, None, cache) == 64


class TestRapComputeTimespans:
    """_rap_compute_timespans scales the LTC dt by the per-item tick rate."""

    @staticmethod
    def _items(ticks):
        return [SimpleNamespace(tick=t) for t in ticks]

    def test_dt_scales_with_default_tick_rate(self):
        # 64 ticks apart at 64 t/s = 1.0s.
        dt = TrainingOrchestrator._rap_compute_timespans(self._items([0, 64, 128]))
        assert abs(dt[0] - 1.0) < 1e-6

    def test_128_tick_halves_dt_vs_64(self):
        items = self._items([0, 64, 128])
        dt64 = TrainingOrchestrator._rap_compute_timespans(items, tick_rates=[64, 64, 64])
        dt128 = TrainingOrchestrator._rap_compute_timespans(items, tick_rates=[128, 128, 128])
        # Same tick delta (64), double the rate → half the elapsed seconds.
        assert abs(dt64[0] - 1.0) < 1e-6
        assert abs(dt128[0] - 0.5) < 1e-6

    def test_per_item_tick_rates_override_default(self):
        dt = TrainingOrchestrator._rap_compute_timespans(
            self._items([0, 64]), tick_rates=[128, 128]
        )
        assert abs(dt[0] - 0.5) < 1e-6

    def test_falls_back_to_default_when_tick_rates_absent(self):
        # 32 ticks apart at the default 64 t/s = 0.5s.
        dt = TrainingOrchestrator._rap_compute_timespans(
            self._items([0, 32]), default_tick_rate=64.0
        )
        assert abs(dt[0] - 0.5) < 1e-6
