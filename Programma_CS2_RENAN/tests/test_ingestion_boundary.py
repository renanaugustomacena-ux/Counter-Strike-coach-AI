"""Boundary tests: demo ingestion must never reach into hltv_metadata.db.

These guardrails exist because previous refactors bolted HLTV reads
(ProPlayerLinker, NicknameResolver, get_pro_baseline) onto the ingestion
hot path, which created cross-DB FK violations and coupled demo ingestion
to HLTV availability. Ingestion writes raw demo-derived stats and returns;
HLTV lookups happen later in a separate coaching-inference stage.

If these tests fail, ingestion has regressed to reading hltv_metadata.db.
Do not weaken the assertions; trace the leak back to the new import or
call and re-isolate it.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Module suffixes that must not appear in run_ingestion's transitive import
# graph. Each entry is checked with substring match against every key in
# sys.modules after `import Programma_CS2_RENAN.run_ingestion`.
FORBIDDEN_MODULE_MARKERS = (
    "baselines.pro_baseline",
    "baselines.pro_player_linker",
    "baselines.nickname_resolver",
    "baselines.meta_drift",
    "data_sources.hltv",
    "hltv_scraper",
    "hltv_sync_service",
)


def test_run_ingestion_has_no_hltv_modules_in_import_graph() -> None:
    """`import Programma_CS2_RENAN.run_ingestion` must not pull any HLTV module.

    Runs in a fresh subprocess so it is unaffected by test-order pollution
    (other tests may legitimately import HLTV code and leave it resident in
    sys.modules of the main interpreter).
    """
    probe = textwrap.dedent(
        f"""
        import sys
        import Programma_CS2_RENAN.run_ingestion  # noqa: F401

        forbidden = {FORBIDDEN_MODULE_MARKERS!r}
        leaks = sorted(
            name
            for name in sys.modules
            if any(marker in name for marker in forbidden)
        )
        if leaks:
            for name in leaks:
                print(name)
            sys.exit(1)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        "run_ingestion pulled HLTV modules into its import graph:\n"
        f"{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_save_player_stats_does_not_touch_hltv_db_manager(monkeypatch) -> None:
    """Calling the stats-save path must not invoke get_hltv_db_manager().

    We replace get_hltv_db_manager with a tripwire that records any call.
    Then we call _save_player_stats with a minimal row and a stub db_manager
    whose upsert is a no-op. If the function attempts to resolve an HLTV id
    or read a pro baseline, the tripwire records the access and the test
    fails.
    """
    import pandas as pd

    from Programma_CS2_RENAN import run_ingestion
    from Programma_CS2_RENAN.backend.storage import database as database_module

    tripwire: list[str] = []

    def _forbidden(*_args, **_kwargs):
        tripwire.append("get_hltv_db_manager called during ingestion")
        raise RuntimeError("ingestion must not read hltv_metadata.db")

    monkeypatch.setattr(database_module, "get_hltv_db_manager", _forbidden)

    class _StubDB:
        def upsert(self, _obj):
            return None

        def get_session(self):
            raise AssertionError(
                "_save_player_stats should not open a main-DB session in this "
                "boundary test; upsert is stubbed out."
            )

    # Minimal stats row — only fields _save_player_stats actually reads
    # before building PlayerMatchStats. Missing/zero values are sanitised.
    row = pd.Series(
        {
            "player_name": "test_player",
            "avg_kills": 15.0,
            "avg_deaths": 15.0,
            "avg_adr": 70.0,
            "avg_hs": 0.4,
            "avg_kast": 0.7,
            "accuracy": 0.2,
            "econ_rating": 0.0,
            "kill_std": 0.0,
            "adr_std": 0.0,
            "kd_ratio": 1.0,
            "impact_rounds": 0.0,
            "utility_blind_time": 0.0,
            "utility_enemies_blinded": 0.0,
            "opening_duel_win_pct": 0.5,
            "clutch_win_pct": 0.0,
            "positional_aggression_score": 0.0,
            "rating": 1.0,
        }
    )

    # is_pro=True exercises the exact path that previously called
    # ProPlayerLinker().link_player(p_name). is_pro=False exercises the
    # personal-demo path that previously called run_ml_pipeline → get_pro_baseline.
    for is_pro in (True, False):
        run_ingestion._save_player_stats(_StubDB(), row, "test_demo.dem", is_pro=is_pro)

    assert not tripwire, "\n".join(tripwire)
