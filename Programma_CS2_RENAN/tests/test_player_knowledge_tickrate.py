"""C1 (AUDIT 26-TICK-01): PlayerKnowledgeBuilder memory/flash/utility windows must be
derived from the per-demo tick rate, not the 64-hardcoded constants.

At tick_rate=64 every window must equal the legacy value (backward compatible); at 128
each window must scale to the same real-time duration (twice the ticks). This covers the
memory decay/cutoff (C1.1), the flash recency window (C1.1), and the smoke/molotov expiry
windows (the C1.1 follow-up that previously stayed hardcoded at 64).
"""

from __future__ import annotations

from Programma_CS2_RENAN.backend.processing.player_knowledge import PlayerKnowledgeBuilder


class TestTickRateAwareWindows:
    def test_windows_at_64_match_legacy_values(self):
        kb = PlayerKnowledgeBuilder(tick_rate=64)
        assert kb.tick_rate == 64
        assert kb.flash_window_ticks == 128  # 2.0s
        assert kb.smoke_max_ticks == 1152  # 18.0s
        assert kb.molotov_max_ticks == 448  # 7.0s
        assert kb.memory_cutoff_ticks == 480  # 7.5s
        assert abs(kb.memory_decay_tau - 160.0) < 1e-6  # 2.5s

    def test_windows_scale_to_same_duration_at_128(self):
        kb = PlayerKnowledgeBuilder(tick_rate=128)
        assert kb.tick_rate == 128
        # Same real-time durations → exactly twice the ticks of the 64-tick case.
        assert kb.flash_window_ticks == 256  # 2.0s @128
        assert kb.smoke_max_ticks == 2304  # 18.0s @128
        assert kb.molotov_max_ticks == 896  # 7.0s @128
        assert kb.memory_cutoff_ticks == 960  # 7.5s @128
        assert abs(kb.memory_decay_tau - 320.0) < 1e-6  # 2.5s @128

    def test_default_tick_rate_is_64(self):
        kb = PlayerKnowledgeBuilder()
        assert kb.tick_rate == 64
        assert kb.flash_window_ticks == 128

    def test_explicit_overrides_take_precedence(self):
        kb = PlayerKnowledgeBuilder(
            memory_cutoff_ticks=999, memory_decay_tau=5.0, tick_rate=128
        )
        # Explicit values win over tick-rate derivation; derived windows still scale.
        assert kb.memory_cutoff_ticks == 999
        assert kb.memory_decay_tau == 5.0
        assert kb.smoke_max_ticks == 2304
