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


# ── Coach (frames 06/07) — keys mirror CoachViewModel._bg_load ──

COACH_INSIGHTS: list[dict[str, Any]] = [
    {
        "title": "Over-peeking on A-site default",
        "message": "Peeked jungle 4× without flash support · ZywOo waited for "
                   "team util in 87% of comparable rounds.",
        "severity": "High", "focus_area": "positioning",
        "created_at": "2026-04-22 21:14",
        "player_name": "ZywOo", "demo_name": "2026-04-21_vitality_navi_mirage.dem",
        "is_pro": True,
    },
    {
        "title": "Utility burn before engage",
        "message": "HE used avg 4.1s before first contact vs pro baseline 8.3s "
                   "— throw earlier on executes.",
        "severity": "Medium", "focus_area": "utility",
        "created_at": "2026-04-22 19:02",
        "player_name": "macena", "demo_name": "2026-04-22_inferno_comp.dem",
        "is_pro": False,
    },
    {
        "title": "Crosshair placement improving",
        "message": "Head-level crosshair held 78% of ticks, up from 64% last "
                   "10 matches — keep it up.",
        "severity": "Low", "focus_area": "aim",
        "created_at": "2026-04-22 16:47",
        "player_name": "macena", "demo_name": "2026-04-22_mirage_comp.dem",
        "is_pro": False,
    },
    {
        # Frame 06's fourth row carries no category tag / timestamp — the
        # row builder must skip its meta line entirely.
        "title": "Pistol round buy pattern",
        "message": "Armor pickup rate 42% on loss round 2 — consider full-buy "
                   "strategy.",
        "severity": "Low", "focus_area": "", "created_at": "",
        "player_name": "macena", "demo_name": "", "is_pro": False,
    },
]

# Frame-06 belief drivers. Only "samples" has a live source today
# (AppState total_matches); the rest mirror the aggregate a future VM
# WOULD provide (see the FIELD-GAP notes in coach_screen.py).
COACH_DRIVER_STATS: dict[str, Any] = {
    "samples": 47, "complete": 42, "partial": 5, "none": 0,
    "maps_seen": 6, "maps_total": 9,
}

# Frame-07 transcript. Rows mirror CoachingChatViewModel messages
# (role user/assistant/system + content); confidence/references/source on
# the "patterns" reply are a payload superset — the names an annotated
# payload WOULD use — so the mono meta footnote renders under the harness.
COACH_CHAT: list[dict[str, Any]] = [
    {
        "role": "assistant",
        "content": "Hey macena — analyzed your last 10 Mirage matches.\n"
                   "Main pattern: over-peeking A-site jungle without util.",
    },
    {"role": "user", "content": "How can I improve positioning?"},
    {
        "role": "assistant",
        "content": "Three patterns from your data vs ZywOo pro reference:\n"
                   "① Hold jungle angle from stairs, not top · ② Delay peek "
                   "0.4s after flash · ③ Crouch-peek when HP < 60",
        "confidence": 0.82, "references": 4, "source": "RAP-Pedagogy",
    },
    {"role": "user", "content": "Analyze utility usage"},
    {
        "role": "assistant",
        "content": "Your HE avg 4.1s before engage vs pro 8.3s — throw "
                   "earlier on execute plays.",
    },
]

# ── Performance (frame 12) — keys mirror PerformanceViewModel._bg_load ──
#
# data_changed(history, map_stats, sw, utility, is_pro_overview) plus the
# context_changed(dict) percentile strip emitted BEFORE it (R4 MED order).
# History rows carry analytics.get_rating_history keys; map_stats carries
# get_per_map_stats keys; sw carries get_strength_weakness (name, z) tuples
# (curated display names); utility carries get_utility_breakdown user/pro.

# Last 8 ratings per the frame-12 sparkline. 1.04→1.07 and 1.12→1.14 vs the
# frame's dot comment so the last-5 average lands EXACTLY on the frame's
# "Recent trend: 1.17" (the frame's own dots average 1.16 — it rounds).
_PERF_RATING_TAIL = [0.94, 0.74, 0.87, 1.08, 1.07, 1.22, 1.14, 1.34]


def _performance_history() -> list[dict[str, Any]]:
    """47 rows: avg exactly 1.08, range 0.71 — 1.34, last-5 avg exactly 1.17.

    Sum check: 37×1.10 + 0.95 + 0.71 + sum(tail 8.40) = 50.76 = 47 × 1.08.
    """
    ratings = [1.10] * 37 + [0.95, 0.71] + list(_PERF_RATING_TAIL)
    first = _dt(2026, 1, 2, 20, 30)
    return [
        {
            "rating": r,
            "match_date": first + timedelta(days=2 * i, minutes=7 * i),
            "demo_name": f"2026_comp_{i + 1:02d}.dem",
            "kd_ratio": 1.09,
            "avg_adr": 74.6,
            "avg_kast": 0.71,
        }
        for i, r in enumerate(ratings)
    ]


PERFORMANCE_MAP_STATS: dict[str, dict[str, Any]] = {
    "de_mirage": {"rating": 1.22, "adr": 84, "kd": 1.19, "matches": 12},
    "de_inferno": {"rating": 1.12, "adr": 74, "kd": 1.05, "matches": 9},
    "de_nuke": {"rating": 0.94, "adr": 58, "kd": 0.87, "matches": 8},
    "de_ancient": {"rating": 0.78, "adr": 53, "kd": 0.72, "matches": 6},
    "de_overpass": {"rating": 1.08, "adr": 70, "kd": 1.00, "matches": 7},
    "de_anubis": {"rating": 1.18, "adr": 79, "kd": 1.12, "matches": 5},
}

PERFORMANCE_SW: dict[str, list[tuple[str, float]]] = {
    "strengths": [
        ("Clutch Win %", 1.8),
        ("Opening Kill Delta", 1.4),
        ("Flash Assists", 1.1),
        ("Thru-smoke Kills", 0.9),
    ],
    "weaknesses": [
        ("Unused Utility", -2.1),
        ("Trade Response", -1.6),
        ("HS %", -1.3),
        ("Positional Aggression", -0.8),
    ],
}

# Pro values pinned to the frame's chart captions (pro 15.2 / 5.9 / 2.6 /
# 0.91); the metric-row percentages derive from this SAME payload, so two
# rows land 1 point off the frame's rounded copy (frame +22% → real +23%,
# frame -31% → real -32% — the frame is internally inconsistent there).
# Smokes/blind pro baselines are chosen so +12% and +8% land exactly.
PERFORMANCE_UTILITY: dict[str, dict[str, float]] = {
    "user": {
        "he_damage": 12.4,
        "molotov_damage": 5.8,
        "smokes_per_round": 0.80,
        "flash_blind_time": 2.3,
        "flash_assists": 3.2,
        "unused_utility": 1.2,
    },
    "pro": {
        "he_damage": 15.2,
        "molotov_damage": 5.9,
        "smokes_per_round": 0.714,
        "flash_blind_time": 2.13,
        "flash_assists": 2.6,
        "unused_utility": 0.91,
    },
}

# Cluster F percentile strip (context_changed payload keys).
PERFORMANCE_CONTEXT: dict[str, float] = {
    "rating": 0.68,
    "kd": 0.61,
    "adr": 0.64,
    "kast": 0.71,
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


def inject_coach(screen: Any) -> None:
    screen._on_belief(0.73)
    screen._set_driver_stats(dict(COACH_DRIVER_STATS))
    screen._on_insights([dict(i) for i in COACH_INSIGHTS])
    screen._set_llm_model("gemma3:e2b")
    screen._on_chat_availability(True)
    screen._set_chat_open(True)  # pure UI toggle — kicks no VM work
    screen._render_messages([dict(m) for m in COACH_CHAT])


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


# ── Profile (frame 17) — PlayerProfile row shown in the DbRecordCard ──
PROFILE_DB_ROW: dict[str, Any] = {
    "id": 42,
    "player_name": "macena",
    "created_at": "2025-11-12",
    "matches_analyzed": 47,
    "last_match": "2026-04-22",
}


def inject_profile(screen: Any) -> None:
    screen._name_input.setText("macena")
    screen._refresh_record_card(dict(PROFILE_DB_ROW))
    # Frame 17 shows the transient "✓ Saved" chip — pin it visible.
    screen._saved_chip.setVisible(True)


def inject_wizard(screen: Any) -> None:
    """Frame 18: jump to the Brain Path step with a real writable temp
    path so the validation row (writable / free space / existing data)
    shows live computed values instead of neutral dashes."""
    import tempfile

    path = tempfile.mkdtemp(prefix="macena_brain_")
    screen._name_input.setText("macena")
    screen._brain_input.setText(path)  # textChanged → validation refresh
    screen._go_to(2)


def inject_performance(screen: Any) -> None:
    # Context BEFORE data — the VM's R4 MED emission order: the data slot
    # rebuilds the UI synchronously and reads the cached context strip.
    screen._on_context(dict(PERFORMANCE_CONTEXT))
    screen._on_data(
        _performance_history(),
        {name: dict(stats) for name, stats in PERFORMANCE_MAP_STATS.items()},
        {kind: list(rows) for kind, rows in PERFORMANCE_SW.items()},
        {side: dict(vals) for side, vals in PERFORMANCE_UTILITY.items()},
        False,  # is_pro_overview — 47 personal demos analyzed
    )


# ── Pro Comparison (frame 15) — ZywOo vs donk ──────────────────────────────
#
# Stats dict keys mirror ProComparisonViewModel's ``comparison_ready``
# payload EXACTLY where the VM emits them (COMPARISON_METRICS db fields).
# The five extra keys (clutch_win_pct, he_damage_per_round,
# flash_assists_per_match, smoke_kill_pct, trade_kill_ratio) carry the
# names the payload WOULD use — ProPlayerStatCard has no such columns yet
# (# FIELD-GAP, see _H2H_ROWS in pro_comparison_screen.py) — so the frame-15
# table and all 8 radar axes exercise their full-data paths under the
# harness.
#
# Derived rows land on the frame's exact numbers: K/D = kpr/dpr
# (0.7524/0.57 = 1.32 · 0.9306/0.66 = 1.41) and Survival = 1 - dpr
# (43% · 34%).

PRO_COMPARISON_STATS_ZYWOO: dict[str, float] = {
    "rating_2_0": 1.28,
    "kpr": 0.7524,
    "dpr": 0.57,
    "adr": 88.2,
    "kast": 0.78,
    "headshot_pct": 0.52,
    "impact": 1.35,
    "opening_duel_win_pct": 0.56,
    "opening_kill_ratio": 1.12,
    "clutch_win_count": 31,
    "multikill_round_pct": 0.19,
    "maps_played": 20,
    # FIELD-GAP superset keys (names the payload WOULD use):
    "clutch_win_pct": 0.67,
    "he_damage_per_round": 15.8,
    "flash_assists_per_match": 2.8,
    "smoke_kill_pct": 0.12,
    "trade_kill_ratio": 0.36,
}

PRO_COMPARISON_STATS_DONK: dict[str, float] = {
    "rating_2_0": 1.24,
    "kpr": 0.9306,
    "dpr": 0.66,
    "adr": 92.7,
    "kast": 0.72,
    "headshot_pct": 0.58,
    "impact": 1.29,
    "opening_duel_win_pct": 0.61,
    "opening_kill_ratio": 1.38,
    "clutch_win_count": 22,
    "multikill_round_pct": 0.24,
    "maps_played": 20,
    # FIELD-GAP superset keys (names the payload WOULD use):
    "clutch_win_pct": 0.58,
    "he_damage_per_round": 12.4,
    "flash_assists_per_match": 2.9,
    "smoke_kill_pct": 0.08,
    "trade_kill_ratio": 0.42,
}

# Roster mirrors players_loaded payload keys; 312 entries so the selector
# caption reads "312 pros loaded · HLTVDatabase" exactly as in frame 15.
# Sorted like the VM (team_rank, nickname): ZywOo lands in combo A, donk is
# the combo-B default (index 1) — the frame's selected pair.
PRO_COMPARISON_PLAYERS: list[dict[str, Any]] = [
    {"hltv_id": 11893, "nickname": "ZywOo", "team": "Vitality", "team_rank": 1},
    {"hltv_id": 20698, "nickname": "donk", "team": "Spirit", "team_rank": 3},
] + [
    {"hltv_id": 90000 + i, "nickname": f"player{i:03d}", "team": "—", "team_rank": 999}
    for i in range(310)
]


# ── Tactical Viewer (frame 13) — drives the REAL demo-loaded pipeline ──────
#
# Payload shapes mirror what TacticalPlaybackVM.frame_updated actually emits:
# InterpolatedFrame(tick, players: [InterpolatedPlayerState], nades:
# [NadeState]). Frame-13 fields the payload lacks (scoreboard, bomb position,
# per-player death attribution, has_defuser) ride along as attribute
# supersets on the emitted objects — the screen reads them via getattr with
# matching # FIELD-GAP comments.

_MIRAGE_PANE_W, _MIRAGE_PANE_H = 820.0, 688.0  # frame-13 map pane (svg px)
_TACTICAL_TICK = 24_582
_TACTICAL_TOTAL_TICKS = 64_500


def _mirage_world(px: float, py: float) -> tuple[float, float]:
    """Frame-13 pane coords → de_mirage world coords.

    Inverse of MapMetadata.world_to_radar for de_mirage (pos_x=-3230,
    pos_y=1713, scale=5.0, radar 1024px): world_x = nx*5120 - 3230,
    world_y = 1713 - ny*5120.
    """
    nx, ny = px / _MIRAGE_PANE_W, py / _MIRAGE_PANE_H
    return nx * 5120.0 - 3230.0, 1713.0 - ny * 5120.0


# Roster verbatim from frame 13 (CT $21,300 total incl. dead cadiaN_bot;
# T $24,800; CT 4 alive, T 5 alive).
_TACTICAL_ROSTER: list[dict[str, Any]] = [
    dict(pid=1, name="niko_bot", team="ct", pos=(740, 140), yaw=225, hp=100, armor=100,
         money=3500, weapon="M4A1-S", inv=["M4A1-S", "USP", "flash", "flash", "smoke"],
         defuser=True),
    dict(pid=2, name="flames_bot", team="ct", pos=(540, 380), yaw=140, hp=84, armor=64,
         money=1200, weapon="AWP", inv=["AWP", "Deagle", "smoke", "smoke", "HE", "moly"]),
    dict(pid=3, name="hooxi_bot", team="ct", pos=(420, 320), yaw=90, hp=40, armor=21,
         money=4200, weapon="M4A4", inv=["M4A4", "Glock", "flash", "smoke"]),
    dict(pid=4, name="maden_bot", team="ct", pos=(440, 540), yaw=250, hp=100, armor=100,
         money=8100, weapon="M4A1-S", inv=["M4A1-S", "P250", "flash", "flash", "smoke", "HE"]),
    dict(pid=5, name="cadiaN_bot", team="ct", pos=(680, 160), yaw=0, hp=0, armor=0,
         money=4300, weapon="", inv=[], alive=False,
         death=dict(place="palace", by="macena", weapon="awp", tick=24_402)),
    dict(pid=6, name="macena", team="t", pos=(440, 290), yaw=65, hp=89, armor=100,
         money=6400, weapon="AK-47", inv=["AK-47", "Glock", "flash", "flash", "smoke", "HE"]),
    dict(pid=7, name="boombl4_bot", team="t", pos=(310, 560), yaw=180, hp=70, armor=54,
         money=4700, weapon="AK-47", inv=["AK-47", "P250", "flash", "smoke", "smoke"]),
    dict(pid=8, name="s1mple_bot", team="t", pos=(370, 400), yaw=100, hp=100, armor=100,
         money=2100, weapon="AWP", inv=["AWP", "Deagle", "flash", "smoke", "smoke"]),
    dict(pid=9, name="electronic_bot", team="t", pos=(400, 410), yaw=45, hp=60, armor=60,
         money=5200, weapon="AK-47", inv=["AK-47", "USP", "flash", "flash", "moly"]),
    dict(pid=10, name="perfecto_bot", team="t", pos=(200, 500), yaw=330, hp=100, armor=80,
         money=6400, weapon="AK-47", inv=["AK-47", "P250", "flash", "smoke", "HE"]),
]

# Frame-13 movement trails (pane coords) — macena's A push, niko's rotate.
_TRAIL_MACENA = [(650, 580), (600, 480), (500, 400), (460, 320), (440, 290)]
_TRAIL_NIKO = [(150, 100), (240, 180), (400, 210), (540, 170), (640, 160), (740, 140)]

# Star ticks derived from the frame's star x-positions (82/262/418/610/802
# of 1196px over 64,500 ticks).
_TACTICAL_MOMENT_SPECS = [
    (4_102, 4_422, "play", "pistol conversion at A"),
    (13_807, 14_127, "mistake", "over-peek jungle vs mid-hold"),
    (22_216, 22_536, "play", "1v2 clutch win on palace"),
    (32_576, 32_896, "mistake", "post-plant hold failed"),
    (42_931, 43_251, "play", "retake 2v4 win"),
]

_TACTICAL_SCORE: dict[str, Any] = {
    "t_name": "MACENA", "t_score": 9, "ct_score": 4,
    "round_no": 14, "time_remaining": "1:32", "bomb_planted": True,
}


def _tactical_segments() -> dict[str, int]:
    """24 round-start ticks; Round 14 starts at 23,900 so tick 24,582 sits
    inside it AND lands at ~38% of the 64,500-tick timeline (frame 13)."""
    seg: dict[str, int] = {}
    for i in range(1, 25):
        if i <= 14:
            seg[f"Round {i}"] = round(23_900 * (i - 1) / 13)
        else:
            seg[f"Round {i}"] = 23_900 + (i - 14) * 3_690
    return seg


def _tactical_player_states() -> list:
    from Programma_CS2_RENAN.core.demo_frame import PlayerState, Team

    out = []
    for spec in _TACTICAL_ROSTER:
        x, y = _mirage_world(*spec["pos"])
        out.append(
            PlayerState(
                player_id=spec["pid"], name=spec["name"],
                team=Team.CT if spec["team"] == "ct" else Team.T,
                x=x, y=y, z=0.0, yaw=float(spec["yaw"]),
                hp=spec["hp"], armor=spec["armor"],
                is_alive=spec.get("alive", True), is_flashed=False,
                has_defuser=spec.get("defuser", False),
                weapon=spec["weapon"], money=spec["money"],
                inventory=list(spec["inv"]),
            )
        )
    return out


def _tactical_interp_players(overrides: "dict[int, tuple[float, float]] | None" = None) -> list:
    from Programma_CS2_RENAN.core.demo_frame import Team
    from Programma_CS2_RENAN.core.playback_engine import InterpolatedPlayerState

    players = []
    for spec in _TACTICAL_ROSTER:
        pane = (overrides or {}).get(spec["pid"], spec["pos"])
        x, y = _mirage_world(*pane)
        p = InterpolatedPlayerState(
            player_id=spec["pid"], name=spec["name"],
            team=Team.CT if spec["team"] == "ct" else Team.T,
            x=x, y=y, z=0.0, yaw=float(spec["yaw"]),
            hp=spec["hp"], armor=spec["armor"],
            is_alive=spec.get("alive", True), is_flashed=False,
            weapon=spec["weapon"], money=spec["money"],
            kills=0, deaths=0, assists=0, mvps=0,
            inventory=list(spec["inv"]),
        )
        # Superset attrs the design needs but the payload lacks (FIELD-GAP
        # mirrors in player_sidebar.py): defuser flag + death attribution.
        if spec.get("defuser"):
            p.has_defuser = True
        if spec.get("death"):
            p.death_info = dict(spec["death"])
        players.append(p)
    return players


def _tactical_nades(tick: int) -> list:
    from Programma_CS2_RENAN.core.demo_frame import NadeState, NadeType

    sx, sy = _mirage_world(490, 300)  # smoke over jungle (frame 13)
    mx, my = _mirage_world(410, 430)  # molotov mid
    return [
        NadeState(base_id=901, nade_type=NadeType.SMOKE, x=sx, y=sy, z=0.0,
                  starting_tick=tick - 128, ending_tick=tick + 960),
        NadeState(base_id=902, nade_type=NadeType.MOLOTOV, x=mx, y=my, z=0.0,
                  starting_tick=tick - 64, ending_tick=tick + 384),
    ]


def _tactical_demo_frames() -> list:
    from Programma_CS2_RENAN.core.demo_frame import DemoFrame

    players = _tactical_player_states()
    nades = _tactical_nades(_TACTICAL_TICK)
    # A frame at exactly _TACTICAL_TICK matters: the engine snaps
    # get_current_tick() to loaded frame ticks, and the frame-13 header,
    # tick counter, and timeline caption all show 24,582.
    return [
        DemoFrame(tick=t, round_number=14, time_in_round=0.0, map_name="de_mirage",
                  players=players, nades=nades)
        for t in (0, _TACTICAL_TICK, _TACTICAL_TOTAL_TICKS)
    ]


def _interp_polyline(points: list[tuple[float, float]], steps: int) -> list[tuple[float, float]]:
    segs = len(points) - 1
    out = []
    for i in range(steps):
        f = (i / (steps - 1)) * segs
        si = min(int(f), segs - 1)
        u = f - si
        x0, y0 = points[si]
        x1, y1 = points[si + 1]
        out.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u))
    return out


def _tactical_walk_frames() -> list:
    """~30 frames walking macena + niko_bot along their frame-13 trails so
    the map's per-player trail deques fill through the real update path."""
    from Programma_CS2_RENAN.core.playback_engine import InterpolatedFrame

    steps = 30
    macena_path = _interp_polyline(_TRAIL_MACENA, steps)
    niko_path = _interp_polyline(_TRAIL_NIKO, steps)
    nades = _tactical_nades(_TACTICAL_TICK)
    frames = []
    for i in range(steps):
        frames.append(
            InterpolatedFrame(
                tick=_TACTICAL_TICK - (steps - 1 - i),
                players=_tactical_interp_players({6: macena_path[i], 1: niko_path[i]}),
                nades=nades,
            )
        )
    # Superset attrs on the final frame only (# FIELD-GAP mirrors in
    # tactical_viewer_screen.py): scoreboard + planted C4 position.
    bx, by = _mirage_world(340, 560)
    frames[-1].score = dict(_TACTICAL_SCORE)
    frames[-1].bomb = {"x": bx, "y": by, "planted": True}
    return frames


def _tactical_moments() -> list:
    from types import SimpleNamespace

    return [
        SimpleNamespace(start_tick=s, peak_tick=p, end_tick=p + 200, type=t, description=d)
        for s, p, t, d in _TACTICAL_MOMENT_SPECS
    ]


# ── Ghost Mode (frame 14) — payload the screen's set_ghost_payload slot
# renders defensively (Locked Decision 8: TacticalGhostVM has no divergence
# fields today; these carry the names a divergence-capable VM WOULD emit).

_GHOST_PANE_W, _GHOST_PANE_H = 980.0, 688.0  # frame-14 map pane (svg px)


def _ghost_norm(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(x / _GHOST_PANE_W, y / _GHOST_PANE_H) for x, y in points]


TACTICAL_GHOST_PAYLOAD: dict[str, Any] = {
    "pro": "ZywOo", "team": "Vitality", "map": "Mirage", "event": "ESL Paris",
    "player": "macena",
    "you": {"side": "T", "map": "Mirage", "path": "T spawn → jungle → A",
            "decision": "4.2s @ connector", "outcome": "died", "died": True},
    "ghost": {"context": "Same round · ESL Paris", "path": "T spawn → palace → A",
              "decision": "8.7s @ palace", "outcome": "won"},
    "divergence": {
        "entry_timing": {"value": "-4.5s", "verdict": "bad"},
        "peek_angle": {"value": "jungle vs palace", "verdict": "bad"},
        "flash_support": {"value": "0 vs 2", "verdict": "bad"},
        "crouch_ratio": {"value": "22% vs 41%", "verdict": "warn"},
        "crosshair_placement": {"value": "good", "verdict": "good"},
        "outcome": {"value": "died vs won", "verdict": "bad"},
    },
    "causal": {"top_score": 0.87, "top_factor": "positioning",
               "positioning": 0.87, "utility": 0.21, "aim": 0.04,
               "aggression": 0.12, "rotation": 0.08},
    "sync_offset_s": 4.2,
    "you_path": _ghost_norm(
        [(810, 650), (760, 540), (640, 450), (560, 380), (510, 340), (490, 300)]
    ),
    "ghost_path": _ghost_norm(
        [(810, 650), (820, 560), (840, 470), (860, 380), (870, 300),
         (820, 230), (760, 180), (700, 160)]
    ),
    "you_label": "you (died)", "ghost_label": "ghost (won)",
    "divergence_points": [
        {"x": 820 / _GHOST_PANE_W, "y": 560 / _GHOST_PANE_H, "label": "split: +4.5s delay"},
        {"x": 860 / _GHOST_PANE_W, "y": 380 / _GHOST_PANE_H, "label": "palace vs jungle"},
    ],
    "smokes": [
        {"x": 640 / _GHOST_PANE_W, "y": 320 / _GHOST_PANE_H, "label": "smoke (ghost)"}
    ],
}


def inject_tactical_viewer_ghost(screen: Any) -> None:
    """Frame 14: base frame-13 state + ghost overlay + Ghost AI enabled."""
    inject_tactical_viewer(screen)
    # Checking Ghost AI lazy-loads the real torch GhostEngine via the VM —
    # disconnect that path so the harness flip stays checkpoint-free
    # (same pattern as inject_pro_comparison's worker unhook).
    try:
        screen._ghost_check.toggled.disconnect(screen._ghost_vm.set_active)
    except (TypeError, RuntimeError):
        pass
    screen.set_ghost_payload(dict(TACTICAL_GHOST_PAYLOAD))
    screen._ghost_check.setChecked(True)

    # Frame 14 shows the comparison scene, not live dots/nades: emit a bare
    # frame whose score box carries the ghost caption (`T 9 — 4 CT`).
    from Programma_CS2_RENAN.core.playback_engine import InterpolatedFrame

    frame = InterpolatedFrame(tick=_TACTICAL_TICK, players=[], nades=[])
    frame.score = {  # FIELD-GAP superset (see _on_frame_update)
        "t_score": 9, "ct_score": 4, "round_no": 14,
        "ghost_note": "1:32 · Ghost: ESL Paris",
    }
    screen._playback_vm.frame_updated.emit(frame)


def inject_tactical_viewer(screen: Any) -> None:
    # Stem stays unset through _on_demo_loaded so _start_chronovisor_scan
    # skips its DB lookup — a matching row would kick a real scan_match
    # whose error path emits scan_complete([], 0) during the harness settle
    # and wipe the injected stars/footer.
    screen._loaded_demo_stem = None
    screen._on_demo_loaded(
        {"de_mirage": (_tactical_demo_frames(), [], _tactical_segments())}
    )
    screen._loaded_demo_stem = "2026-04-22_mirage_comp"
    screen._round_combo.setCurrentText("Round 14")  # real slot chain → seek
    screen._on_player_select(6)  # macena — selected card + map highlight
    for frame in _tactical_walk_frames():
        screen._playback_vm.frame_updated.emit(frame)
    screen._on_cm_scan_complete(_tactical_moments(), len(_TACTICAL_MOMENT_SPECS))
    screen.set_demo_meta(
        {"source": "demo cache hit", "size_mb": 287, "parser": "demoparser2 v0.4.1"}
    )


def inject_pro_comparison(screen: Any) -> None:
    # on_enter (fired by the harness's switch_screen) kicks a real DB worker;
    # unhook the VM so a late players_loaded/error can't clobber the injected
    # roster mid-render. Injection still goes through the screen's own slots.
    try:
        screen._vm.players_loaded.disconnect(screen._on_players_loaded)
        screen._vm.comparison_ready.disconnect(screen._on_comparison)
        screen._vm.error_changed.disconnect(screen._on_error)
    except (TypeError, RuntimeError):
        pass
    screen._on_players_loaded([dict(p) for p in PRO_COMPARISON_PLAYERS])
    screen._on_comparison(
        dict(PRO_COMPARISON_STATS_ZYWOO),
        dict(PRO_COMPARISON_STATS_DONK),
        "ZywOo",
        "donk",
    )
