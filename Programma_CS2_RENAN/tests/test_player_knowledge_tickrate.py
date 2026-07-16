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
        kb = PlayerKnowledgeBuilder(memory_cutoff_ticks=999, memory_decay_tau=5.0, tick_rate=128)
        # Explicit values win over tick-rate derivation; derived windows still scale.
        assert kb.memory_cutoff_ticks == 999
        assert kb.memory_decay_tau == 5.0
        assert kb.smoke_max_ticks == 2304


class TestSoundWindowTickRate:
    """R4 HIGH (2026-07-16): the 1-second audible window must use the
    builder's per-demo tick rate. A ``tick_rate=64`` parameter default used
    to win silently because the call site never forwarded it."""

    @staticmethod
    def _heard_count(kb: PlayerKnowledgeBuilder, delta_ticks: int) -> int:
        from types import SimpleNamespace

        from Programma_CS2_RENAN.backend.processing.player_knowledge import PlayerKnowledge

        knowledge = PlayerKnowledge()
        event = SimpleNamespace(
            event_type="weapon_fire",
            tick=1000 + delta_ticks,
            pos_x=100.0,
            pos_y=0.0,
            pos_z=0.0,
        )
        kb._build_sound_events(knowledge, [event], current_tick=1000)
        return len(knowledge.heard_events)

    def test_128_rate_hears_event_100_ticks_away(self):
        """100 ticks at 128 t/s is 0.78s — inside the 1-second window."""
        assert self._heard_count(PlayerKnowledgeBuilder(tick_rate=128), 100) == 1

    def test_64_rate_rejects_event_100_ticks_away(self):
        """100 ticks at 64 t/s is 1.56s — outside the 1-second window."""
        assert self._heard_count(PlayerKnowledgeBuilder(tick_rate=64), 100) == 0

    def test_64_rate_hears_event_within_window(self):
        assert self._heard_count(PlayerKnowledgeBuilder(tick_rate=64), 50) == 1
