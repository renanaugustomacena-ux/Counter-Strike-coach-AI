"""Frame-realistic fixture payloads for the UI screenshot harness.

Numbers mirror the design atlas (design/frames/) so harness renders are
directly comparable with the frames: 47 personal demos, 2,148 pro demos
indexed, belief 73%, last match de_mirage 2026-04-22 rating 1.34, etc.

Injection calls the screens' OWN signal-handler slots (the same ones their
ViewModels emit into) — no DB, no backend, no monkeypatching.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _dt(y: int, mo: int, d: int, h: int, mi: int) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


# ── Match list (frame 08) — keys mirror MatchHistoryViewModel._bg_load ──

SAMPLE_MATCHES: list[dict[str, Any]] = [
    {
        "demo_name": "2026-04-22_mirage_comp.dem",
        "match_date": _dt(2026, 4, 22, 21, 14),
        "rating": 1.34, "kd_ratio": 1.26, "avg_adr": 82.3,
        "avg_kills": 24.0, "avg_deaths": 19.0, "avg_kast": 0.78,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-22_inferno_comp.dem",
        "match_date": _dt(2026, 4, 22, 19, 2),
        "rating": 1.12, "kd_ratio": 1.05, "avg_adr": 74.1,
        "avg_kills": 22.0, "avg_deaths": 21.0, "avg_kast": 0.71,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-21_vitality_navi_mirage.dem",
        "match_date": _dt(2026, 4, 21, 18, 30),
        "rating": 1.47, "kd_ratio": 1.68, "avg_adr": 96.8,
        "avg_kills": 27.0, "avg_deaths": 16.0, "avg_kast": 0.83,
        "is_pro": True, "player_name": "ZywOo",
    },
    {
        "demo_name": "2026-04-21_nuke_comp.dem",
        "match_date": _dt(2026, 4, 21, 15, 47),
        "rating": 0.94, "kd_ratio": 0.87, "avg_adr": 58.4,
        "avg_kills": 18.0, "avg_deaths": 20.0, "avg_kast": 0.62,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-20_ancient_comp.dem",
        "match_date": _dt(2026, 4, 20, 22, 18),
        "rating": 0.74, "kd_ratio": 0.71, "avg_adr": 51.2,
        "avg_kills": 15.0, "avg_deaths": 21.0, "avg_kast": 0.54,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-19_g2_faze_inferno.dem",
        "match_date": _dt(2026, 4, 19, 20, 0),
        "rating": 1.21, "kd_ratio": 1.29, "avg_adr": 87.3,
        "avg_kills": 23.0, "avg_deaths": 18.0, "avg_kast": 0.76,
        "is_pro": True, "player_name": "NiKo",
    },
    {
        "demo_name": "2026-04-19_overpass_comp.dem",
        "match_date": _dt(2026, 4, 19, 14, 22),
        "rating": 1.08, "kd_ratio": 1.00, "avg_adr": 70.5,
        "avg_kills": 20.0, "avg_deaths": 20.0, "avg_kast": 0.68,
        "is_pro": False, "player_name": "macena",
    },
    {
        "demo_name": "2026-04-18_mirage_comp.dem",
        "match_date": _dt(2026, 4, 18, 21, 50),
        "rating": 1.22, "kd_ratio": 1.18, "avg_adr": 88.1,
        "avg_kills": 26.0, "avg_deaths": 22.0, "avg_kast": 0.74,
        "is_pro": False, "player_name": "macena",
    },
]

# ── Training status (frame 05) — keys mirror AppState.training_changed ──

TRAINING_STATUS: dict[str, Any] = {
    "current_epoch": 12,
    "total_epochs": 40,
    "train_loss": 0.0841,
    "val_loss": 0.0923,
    "eta_seconds": 23 * 60 + 14,
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
    screen._on_matches_changed(list(SAMPLE_MATCHES))
    screen._on_insight_changed(dict(FOCUS_INSIGHT))
    screen._on_training(dict(TRAINING_STATUS))


def inject_match_history(screen: Any) -> None:
    screen._on_matches_loaded(list(SAMPLE_MATCHES))
