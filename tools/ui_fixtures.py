"""Frame-realistic fixture payloads for the UI screenshot harness.

Numbers mirror the design atlas (design/frames/) so harness renders are
directly comparable with the frames: 47 personal demos, 2,148 pro demos
indexed, belief 73%, last match de_mirage 2026-04-22 rating 1.34, etc.

Injection calls the screens' OWN signal-handler slots (the same ones their
ViewModels emit into) — no DB, no backend, no monkeypatching.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _dt(y: int, mo: int, d: int, h: int, mi: int) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


# ── Match list (frame 08) — keys mirror MatchHistoryViewModel._bg_load ──
#
# The 8 curated rows below are the frame-08 rows verbatim. They are topped
# up by _older_personal_rows() so the corpus totals 47 personal matches —
# the number frame 05's "Matches: 47" chip and "47 analyzed" caption and
# frame 08's "47 personal" header caption all derive by counting rows.
#
# clutches_won / clutches_total / demo_size_mb / pro_teams / pro_event /
# pro_score are a superset of today's VM payload: PlayerMatchStats has no
# such columns yet (see the FIELD-GAP comments in match_history_vm.py).
# They carry the names the payload WOULD use, so MatchRowCard's defensive
# rendering exercises its full-data path under the harness.

_CURATED_MATCHES: list[dict[str, Any]] = [
    {
        "demo_name": "2026-04-22_mirage_comp.dem",
        "match_date": _dt(2026, 4, 22, 21, 14),
        "rating": 1.34, "kd_ratio": 1.26, "avg_adr": 82.3,
        "avg_kills": 24.0, "avg_deaths": 19.0, "avg_kast": 0.78,
        "avg_hs": 0.52, "clutch_win_pct": 0.67,
        "clutches_won": 2, "clutches_total": 3, "demo_size_mb": 312,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-22_inferno_comp.dem",
        "match_date": _dt(2026, 4, 22, 19, 2),
        "rating": 1.12, "kd_ratio": 1.05, "avg_adr": 74.1,
        "avg_kills": 22.0, "avg_deaths": 21.0, "avg_kast": 0.71,
        "avg_hs": 0.47, "clutch_win_pct": 0.0,
        "clutches_won": 0, "clutches_total": 2, "demo_size_mb": 287,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-21_vitality_navi_mirage.dem",
        "match_date": _dt(2026, 4, 21, 18, 30),
        "rating": 1.47, "kd_ratio": 1.68, "avg_adr": 96.8,
        "avg_kills": 27.0, "avg_deaths": 16.0, "avg_kast": 0.83,
        "avg_hs": 0.58, "clutch_win_pct": 0.75,
        "is_pro": True, "player_name": "ZywOo",
        "pro_teams": "Vitality vs NAVI", "pro_event": "ESL Pro League",
        "pro_score": "16-11 CT",
    },
    {
        "demo_name": "2026-04-21_nuke_comp.dem",
        "match_date": _dt(2026, 4, 21, 15, 47),
        "rating": 0.94, "kd_ratio": 0.87, "avg_adr": 58.4,
        "avg_kills": 18.0, "avg_deaths": 20.0, "avg_kast": 0.62,
        "avg_hs": 0.44, "clutch_win_pct": 0.0,
        "clutches_won": 0, "clutches_total": 1, "demo_size_mb": 198,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-20_ancient_comp.dem",
        "match_date": _dt(2026, 4, 20, 22, 18),
        "rating": 0.74, "kd_ratio": 0.71, "avg_adr": 51.2,
        "avg_kills": 15.0, "avg_deaths": 21.0, "avg_kast": 0.54,
        "avg_hs": 0.38, "clutch_win_pct": 0.0,
        "clutches_won": 0, "clutches_total": 2, "demo_size_mb": 164,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-19_g2_faze_inferno.dem",
        "match_date": _dt(2026, 4, 19, 20, 0),
        "rating": 1.21, "kd_ratio": 1.29, "avg_adr": 87.3,
        "avg_kills": 23.0, "avg_deaths": 18.0, "avg_kast": 0.76,
        "avg_hs": 0.51, "clutch_win_pct": 0.5,
        "is_pro": True, "player_name": "NiKo",
        "pro_teams": "G2 vs FaZe", "pro_event": "BLAST Paris Major",
        "pro_score": "16-13 T",
    },
    {
        "demo_name": "2026-04-19_overpass_comp.dem",
        "match_date": _dt(2026, 4, 19, 14, 22),
        "rating": 1.08, "kd_ratio": 1.00, "avg_adr": 70.5,
        "avg_kills": 20.0, "avg_deaths": 20.0, "avg_kast": 0.68,
        "avg_hs": 0.41, "clutch_win_pct": 0.5,
        "clutches_won": 1, "clutches_total": 2, "demo_size_mb": 241,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-18_mirage_comp.dem",
        "match_date": _dt(2026, 4, 18, 21, 50),
        "rating": 1.22, "kd_ratio": 1.18, "avg_adr": 88.1,
        "avg_kills": 26.0, "avg_deaths": 22.0, "avg_kast": 0.74,
        "avg_hs": 0.49, "clutch_win_pct": 1.0,
        "clutches_won": 1, "clutches_total": 1, "demo_size_mb": 302,
        "is_pro": False, "player_name": "macena",
    },
]


def _older_personal_rows(count: int = 41) -> list[dict[str, Any]]:
    """Deterministic filler rows older than the curated ones (below the fold).

    They exist so row-derived counters reach the frame numbers (47 personal)
    without hand-writing 41 dicts. Values cycle through plausible ranges;
    dates walk backward one day per row from 2026-04-17.
    """
    maps = ("mirage", "inferno", "nuke", "overpass", "ancient", "anubis", "dust2")
    ratings = (1.08, 0.97, 1.21, 0.88, 1.14, 1.02, 0.79, 1.31, 0.93, 1.06)
    rows: list[dict[str, Any]] = []
    for i in range(count):
        rating = ratings[i % len(ratings)]
        kills = 14 + (i * 3) % 13
        deaths = 15 + (i * 5) % 9
        clutches_total = i % 3
        base = _dt(2026, 4, 17, 20 - (i % 6), (i * 7) % 60)
        match_date = base - timedelta(days=i)  # walks back into March
        rows.append(
            {
                "demo_name": f"2026-{match_date.month:02d}-{match_date.day:02d}_"
                             f"{maps[i % len(maps)]}_comp.dem",
                "match_date": match_date,
                "rating": rating,
                "kd_ratio": round(kills / max(deaths, 1), 2),
                "avg_adr": round(52.0 + rating * 28.0, 1),
                "avg_kills": float(kills),
                "avg_deaths": float(deaths),
                "avg_kast": round(0.52 + (rating - 0.74) * 0.4, 2),
                "avg_hs": round(0.34 + (rating - 0.74) * 0.3, 2),
                "clutch_win_pct": 0.0 if clutches_total == 0 else round(
                    min(i % 2, clutches_total) / clutches_total, 2
                ),
                "clutches_won": min(i % 2, clutches_total),
                "clutches_total": clutches_total,
                "demo_size_mb": 150 + (i * 13) % 200,
                "is_pro": False,
                "player_name": "macena",
            }
        )
    return rows


SAMPLE_MATCHES: list[dict[str, Any]] = _CURATED_MATCHES + _older_personal_rows()

# ── Training status (frame 05) — keys mirror AppState.training_changed ──

TRAINING_STATUS: dict[str, Any] = {
    "current_epoch": 12,
    "total_epochs": 40,
    "train_loss": 0.0841,
    "val_loss": 0.0923,
    "eta_seconds": 23 * 60 + 14,
    # FIELD-GAP: AppState._apply filters training_changed to the five keys
    # above, so batch progress never reaches the screen today. These mirror
    # the keys the payload WOULD carry (frame 05 footer: "batch 184/512");
    # the home screen composes them defensively when present.
    "batch": 184,
    "total_batches": 512,
}

# ── Focus insight (home hero pair) ──

FOCUS_INSIGHT: dict[str, Any] = {
    "area": "Utility burn before engage",
    "body": "HE used avg 4.1s before first contact vs pro baseline 8.3s "
            "— throw earlier on executes.",
    "navigate_to": "performance",
}


def inject(name: str, screen: Any) -> bool:
    """Inject the fixture for ``name`` into ``screen``.

    Returns False when no fixture exists — the harness then renders the
    screen's natural (cold-start / DB) state, which is itself meaningful
    for empty-state frames.
    """
    fn = globals().get(f"inject_{name}")
    if fn is None:
        return False
    fn(screen)
    return True


def inject_home(screen: Any) -> None:
    screen._on_service_active(True)
    screen._on_coach_status("Idle")
    screen._on_matches_changed(list(SAMPLE_MATCHES))
    screen._on_insight_changed(dict(FOCUS_INSIGHT))
    screen._on_training(dict(TRAINING_STATUS))


def inject_match_history(screen: Any) -> None:
    screen._on_matches_loaded(list(SAMPLE_MATCHES))
