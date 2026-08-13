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

# ── Match detail (frames 09/10/11) — keys mirror MatchDetailViewModel._bg_load ──

MATCH_DETAIL_STATS: dict[str, Any] = {
    "demo_name": "2026-04-22_mirage_comp.dem",
    "match_date": _dt(2026, 4, 22, 21, 14),
    "rating": 1.34, "kd_ratio": 1.26, "avg_adr": 82.3, "avg_kast": 0.78,
    "avg_hs": 0.52, "avg_kills": 24.0, "avg_deaths": 19.0,
    "kpr": 1.0, "dpr": 0.79,
    # HLTV 2.0 per-match components (frame 09 left column)
    "rating_impact": 1.28, "rating_survival": 1.12, "rating_kast": 1.08,
    "rating_kpr": 1.32, "rating_adr": 1.41,
    # Trade / duel metrics (frame 09 right column; ratios 0-1)
    "trade_kill_ratio": 0.34, "was_traded_ratio": 0.62,
    "opening_duel_win_pct": 0.55, "clutch_win_pct": 0.67,
    "positional_aggression_score": 0.72,
    # Kill enrichment (ratios 0-1)
    "thrusmoke_kill_pct": 0.08, "wallbang_kill_pct": 0.04,
    "noscope_kill_pct": 0.0, "blind_kill_pct": 0.0,
    # Utility breakdown
    "he_damage_per_round": 12.4, "molotov_damage_per_round": 5.8,
    "smokes_per_round": 0.8, "flash_assists": 3.0,
    "unused_utility_per_round": 1.2,
    # Display-only extras — no DB source yet (see screen FIELD-GAP notes).
    "demo_size_mb": 312, "duration_min": 45,
}


def _md_round(  # noqa: PLR0913 — table row, one arg per frame-10 column
    n: int, side: str, won: bool, k: int, d: int, dmg: int, equip: int,
    fk: bool, bomb: str | None, left: int, note: str,
    sev: str | None = None, od: bool = False,
) -> dict[str, Any]:
    return {
        "round_number": n, "side": side, "round_won": won,
        "kills": k, "deaths": d, "damage_dealt": dmg,
        "opening_kill": fk, "opening_death": od, "equipment_value": equip,
        # Fixture-only display fields (not in the RoundStats payload —
        # the screen renders them defensively; see its FIELD-GAP notes).
        "bomb": bomb, "enemies_left": left,
        "note": note, "note_severity": sev,
    }


# 24 rounds exactly as frame 10 draws them (T half 7W-5L, CT half 9W-3L).
MATCH_DETAIL_ROUNDS: list[dict[str, Any]] = [
    _md_round(1, "T", True, 2, 0, 152, 4600, True, "planted", 3, "pistol · eco save CT"),
    _md_round(2, "T", True, 1, 0, 98, 3800, False, "planted", 2, "force · trade kill at palace"),
    _md_round(3, "T", False, 0, 1, 18, 5200, False, None, 5,
              "over-peek jungle vs mid-hold", sev="warning", od=True),
    _md_round(4, "T", True, 1, 1, 84, 5000, False, "defused", 0, "1v2 clutch win on palace"),
    _md_round(5, "T", False, 1, 1, 42, 4800, True, None, 4, "got traded fast"),
    _md_round(6, "T", True, 2, 1, 128, 5200, False, "planted", 2, "A default · flash assist x2"),
    _md_round(7, "T", True, 2, 1, 144, 5400, True, "planted", 1, "full save by CT"),
    _md_round(8, "T", True, 1, 0, 76, 5000, False, "planted", 3, "B split execute"),
    _md_round(9, "T", False, 2, 1, 168, 5200, False, None, 2,
              "post-plant hold failed", sev="warning"),
    _md_round(10, "T", False, 0, 1, 32, 5200, False, None, 4,
              "crossfire death top-mid", od=True),
    _md_round(11, "T", True, 2, 1, 156, 5400, True, "planted", 1, "opening pick at palace"),
    _md_round(12, "T", False, 1, 1, 68, 5200, False, None, 3, "last round of half"),
    _md_round(13, "CT", True, 2, 0, 126, 3800, True, None, 2, "CT pistol · hold A"),
    _md_round(14, "CT", False, 1, 1, 58, 4200, False, "lost", 3,
              "B rush · late rotate", od=True),
    _md_round(15, "CT", True, 1, 0, 72, 4800, False, "defused", 1, "hold connector"),
    _md_round(16, "CT", True, 2, 0, 148, 5200, True, "defused", 2,
              "retake 2v4 win", sev="success"),
    _md_round(17, "CT", True, 1, 1, 88, 5200, False, "lost", 0, "time ran out"),
    _md_round(18, "CT", True, 2, 0, 134, 5200, True, None, 1, "mid-jungle aim duel"),
    _md_round(19, "CT", False, 1, 1, 54, 5200, False, "lost", 2,
              "over-peeked vs flash", sev="warning", od=True),
    _md_round(20, "CT", True, 2, 1, 112, 5200, False, "defused", 1, "solid hold B"),
    _md_round(21, "CT", False, 0, 1, 28, 5200, False, "lost", 4,
              "caught repositioning", od=True),
    _md_round(22, "CT", True, 2, 0, 142, 5200, True, "defused", 1, "double on A ramp"),
    _md_round(23, "CT", True, 1, 1, 76, 5200, False, "defused", 3, "mid rotate to B save"),
    _md_round(24, "CT", True, 2, 1, 98, 5200, False, "defused", 0,
              "match point · win 16-8", sev="success"),
]

MATCH_DETAIL_INSIGHTS: list[dict[str, Any]] = [
    {
        "title": "Over-peeking on A-site default",
        "message": "Died first in 3 of 12 T rounds holding the same jungle angle "
                   "— vary the peek timing or play the off-angle.",
        "severity": "critical", "focus_area": "Positioning",
    },
    {
        "title": "Utility burn before engage",
        "message": "HE used avg 4.1s before first contact vs pro baseline 8.3s "
                   "— throw earlier on executes.",
        "severity": "warning", "focus_area": "Utility",
    },
    {
        "title": "Crosshair placement improving",
        "message": "Head-level tracking up 9% over the last five matches — keep "
                   "the current warmup routine.",
        "severity": "info", "focus_area": "Aim",
    },
    {
        "title": "Pistol round buy pattern",
        "message": "Kevlar-only on both pistols; consider a P250 upgrade when "
                   "playing entry on T side.",
        "severity": "info", "focus_area": "Economy",
    },
]

# Cross-match aggregate — mirrors analytics.get_hltv2_breakdown() keys.
MATCH_DETAIL_HLTV: dict[str, float] = {
    "Kill": 1.32, "Survival": 1.12, "KAST": 1.08, "Impact": 1.28, "Damage": 1.41,
}

# Critical moments — keys mirror chronovisor_scanner.CriticalMoment.to_dict()
# plus a display-only "round" (the scanner result carries no round number).
MATCH_DETAIL_MOMENTS: list[dict[str, Any]] = [
    {
        "description": "1v2 clutch win on palace", "type": "play", "round": 4,
        "start_tick": 61440, "peak_tick": 61888, "end_tick": 62220,
        "severity": 0.42, "scale": "standard",
    },
    {
        "description": "Over-peek jungle vs mid-hold", "type": "mistake", "round": 3,
        "start_tick": 48120, "peak_tick": 48310, "end_tick": 48540,
        "severity": 0.38, "scale": "micro",
    },
    {
        "description": "Post-plant hold failed", "type": "mistake", "round": 9,
        "start_tick": 118400, "peak_tick": 118750, "end_tick": 119100,
        "severity": 0.35, "scale": "standard",
    },
    {
        "description": "Retake 2v4 win", "type": "play", "round": 16,
        "start_tick": 201300, "peak_tick": 201740, "end_tick": 202150,
        "severity": 0.51, "scale": "macro",
    },
    {
        "description": "Opening pick at palace", "type": "play", "round": 11,
        "start_tick": 142080, "peak_tick": 142200, "end_tick": 142380,
        "severity": 0.22, "scale": "micro",
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


def inject_match_detail(screen: Any) -> None:
    # Moments first (no rebuild yet — the payload lands right after and
    # builds every tab exactly once).
    screen.set_critical_moments([dict(m) for m in MATCH_DETAIL_MOMENTS])
    screen._on_data(
        dict(MATCH_DETAIL_STATS),
        [dict(r) for r in MATCH_DETAIL_ROUNDS],
        [dict(i) for i in MATCH_DETAIL_INSIGHTS],
        dict(MATCH_DETAIL_HLTV),
    )
