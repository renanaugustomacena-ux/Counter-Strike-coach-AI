"""DOCTRINE D-02 regression — the per-player analysis block must render.

The old chain called the deleted ``HybridCoachingEngine._get_ml_predictions``
and the pre-F-0028 5-arg ``_synthesize_insights`` — it raised AttributeError
on EVERY call, swallowed by a broad except, so the block silently returned
"" forever ("LIVE NEURAL NETWORK ANALYSIS" never rendered). These tests
exercise the REAL seam: real HybridCoachingEngine methods, the real C-41
baseline fallback ladder, and an in-memory SQLite (the sanctioned GAP-05
idiom — real logic, no production DB). Before the repair, the first test
fails (empty string); after it, the block renders with honest labeling.
"""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from sqlmodel import Session, SQLModel, create_engine

from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats


@pytest.fixture
def seeded_env(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        # A player whose deviations are large enough to clear the |z| >= 0.5
        # synthesis threshold against HARD_DEFAULT_BASELINE.
        s.add(
            PlayerMatchStats(
                player_name="s1mple",
                demo_name="test-demo-mirage",
                avg_kills=0.2,
                avg_deaths=1.4,
                avg_adr=40.0,
                avg_hs=0.10,
                avg_kast=0.40,
                kd_ratio=0.3,
                rating=0.55,
            )
        )
        s.commit()

    class _FakeMgr:
        @contextmanager
        def get_session(self):
            with Session(engine) as s:
                yield s

    mgr = _FakeMgr()
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.services.coaching_dialogue.get_db_manager",
        lambda: mgr,
    )
    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.coaching.hybrid_engine.get_db_manager",
        lambda: mgr,
    )

    # Force the REAL C-41 ladder onto its deterministic HARD_DEFAULT_BASELINE
    # rung (get_pro_baseline raising is a genuine production failure mode).
    def _raise(*_a, **_k):
        raise RuntimeError("test: dynamic baseline unavailable")

    monkeypatch.setattr(
        "Programma_CS2_RENAN.backend.processing.baselines.pro_baseline.get_pro_baseline",
        _raise,
    )
    return engine


class TestBaselineDeviationBlock:
    def test_block_renders_for_player_with_stats(self, seeded_env, caplog):
        from Programma_CS2_RENAN.backend.services.coaching_dialogue import CoachingDialogueEngine

        with caplog.at_level("WARNING"):
            block = CoachingDialogueEngine._get_ml_analysis_for_players(["s1mple"])

        # Before the D-02 repair this was "" on every call (AttributeError
        # swallowed by the broad except).
        assert block, "the analysis block must render for a player with stats"
        assert "BASELINE DEVIATION ANALYSIS for s1mple" in block
        # Law I: no fabricated neural provenance on a path where no model ran.
        assert "NEURAL NETWORK ANALYSIS" not in block.upper()
        assert "no neural model ran" in block
        # The block must have succeeded, not died into the swallow branch.
        assert "analysis block failed" not in caplog.text

    def test_unknown_player_yields_empty(self, seeded_env):
        from Programma_CS2_RENAN.backend.services.coaching_dialogue import CoachingDialogueEngine

        assert CoachingDialogueEngine._get_ml_analysis_for_players(["nobody"]) == ""
