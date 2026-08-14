"""F-0039 regression: the 'safe' runner must never schedule a tool whose
BARE invocation mutates live data.

The audit census (docs/audit/FINDINGS.md F-0039) confirmed 13 such
tools slipping through the six original prefixes; rebuild_monolith's
delete-first phase + the runner's 120s timeout-kill = pro stats left
empty. This suite pins the gate against every census member and keeps
the genuinely-safe tools scheduled."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "verify_all_safe_under_test", REPO_ROOT / "tools" / "verify_all_safe.py"
)


def _is_safe(name: str) -> bool:
    import os
    from unittest.mock import patch

    mod = importlib.util.module_from_spec(_spec)
    with patch.dict(os.environ, {"CI": "1"}):  # bypass the venv guard on import
        _spec.loader.exec_module(mod)
    return mod.is_safe_to_run(Path(name))


# The 13 confirmed bare-invocation mutating tools (F-0039 census).
CENSUS_MEMBERS = [
    "repair_ratings.py",
    "repair_kast.py",
    "repair_equipment_value.py",
    "repair_tick_features.py",
    "flag_ghost_players.py",
    "purge_default_stats_rag.py",
    "mine_shard_strategies.py",
    "mine_coaching_experience.py",
    "populate_round_stats.py",
    "populate_match_results.py",
    "rebuild_monolith.py",
    "observe_training_cycle.py",
    "ingest_pro_demos.py",
]


def test_every_census_member_is_gated():
    leaked = [n for n in CENSUS_MEMBERS if _is_safe(n)]
    assert leaked == [], f"mutating tools still scheduled by the safe runner: {leaked}"


def test_interactive_and_longrunning_are_gated():
    assert not _is_safe("Sanitize_Project.py")
    assert not _is_safe("fuzz_demo_parser.py")
    assert not _is_safe("run_console_boot.py")


def test_genuinely_safe_tools_stay_scheduled():
    for name in [
        "d4_disk_hygiene_audit.py",
        "tick_census.py",
        "verify_lock_hashes.py",
        "dev_health.py",
        "policy_runner.py",
        "drift_detector.py",
        "merge_demo_pool.py",  # dry-run default
        "rescrape_placeholder_pros.py",  # dry-run default
        "sync_pro_players.py",  # dry-run default
    ]:
        assert _is_safe(name), f"{name} should remain scheduled"
