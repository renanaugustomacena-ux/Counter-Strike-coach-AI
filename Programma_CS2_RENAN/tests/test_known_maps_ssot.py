"""Map-SSOT regression (CP0 decision #2): one authority list, and the
seven converted consumers actually import it — no divergent copies."""

import re
from pathlib import Path

from Programma_CS2_RENAN.core import known_maps as km

REPO_ROOT = Path(__file__).resolve().parents[2]

CONSUMERS = [
    "Programma_CS2_RENAN/apps/qt_app/core/match_utils.py",
    "Programma_CS2_RENAN/apps/qt_app/screens/coach_screen.py",
    "tools/rebuild_monolith.py",
    "tools/mine_coaching_experience.py",
    "tools/mine_shard_strategies.py",
    "tools/populate_match_results.py",
    "tools/d3_recover_shard_metadata.py",
]


def test_authority_shape():
    assert "mirage" in km.KNOWN_MAP_NAMES and "train" in km.KNOWN_MAP_NAMES
    assert "de_mirage" in km.KNOWN_MAP_IDS
    assert km.is_known_map("de_cache") and km.is_known_map("office")
    assert not km.is_known_map("de_fantasy_map")
    assert km.sniff_map_from_text("vitality-vs-spirit-m2-train.dem") == "train"


def test_consumers_import_the_authority():
    for rel in CONSUMERS:
        src = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "known_maps import" in src, f"{rel} no longer imports the SSOT"


def test_no_hardcoded_map_set_literals_in_consumers():
    """No consumer may re-declare a 3+-map set literal (drift guard)."""
    trio = re.compile(
        r'"(?:de_)?mirage"[^)}\]]{0,200}"(?:de_)?inferno"[^)}\]]{0,200}"(?:de_)?nuke"'
    )
    offenders = [
        rel for rel in CONSUMERS if trio.search((REPO_ROOT / rel).read_text(encoding="utf-8"))
    ]
    assert offenders == [], f"hardcoded map lists back in: {offenders}"
