#!/usr/bin/env python3
"""D2A — SQL-only PlayerMatchStats aggregator (no .dem required).

Reads each match_*.db, runs SQL aggregations against matchtickstate +
match_event_state, computes the 25 Class-A PlayerMatchStats fields
(per-round counters, KAST, HLTV 2.0 rating, trade kills, utility per
round) and UPSERTs rows tagged ``data_quality='full_sql'``.

The 11 Class-B fields (accuracy, opening_duel_win_pct, clutch_win_pct,
flash_assists full, utility_blind_time, positional_aggression_score,
thrusmoke/wallbang/noscope/blind_kill_pct, unused_utility_per_round)
require demoparser2 re-parse and stay at default 0.0 here. Phase D2B
upgrades those rows to ``data_quality='complete'`` when the source
.dem is on disk.

Class-C fields (anomaly_score, sample_weight, pro_player_id) are
populated separately: D2C runs ProPlayerLinker.backfill_all() for the
foreign key, and ML scoring is out of scope per v3 plan §22.4.

CLI (all flags optional; sensible defaults match v3 plan §5):
  --match-id N            Process only the demo whose stem hashes to N.
  --limit N               Process at most N matches this run.
  --dry-run               Read-only; no DB writes (default).
  --commit                Write rows; requires d_track_running lock.
  --reconcile             Diff new aggregates vs the 30 existing 'complete'
                          rows and exit with a written report (no writes).
  --force                 Overwrite existing 'registered_only'/'partial'
                          rows; still skip 'complete'.
  --really-force          Overwrite 'complete' rows too. 5-second
                          countdown banner before proceeding.
  --no-lock               Skip d_track_running lock check.
  --checkpoint-file PATH  Resume across kills (default under backups/).
  --report-out PATH       JSON report destination (default under docs/).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from Programma_CS2_RENAN.core import lock_files  # noqa: E402

# pandas is only imported when detect_trade_kills runs (per-match).
# Keeping the import inside the function avoids paying the cost when the
# tool is invoked in --reconcile or --dry-run modes that skip writes.

# CS2 MR12 valid round-count band:
#   13       — minimum (13-0 sweep)
#   13-25    — typical no-OT range (winner reaches 13)
#   26-36    — with overtime (each OT adds up to 6 rounds; max 2 OTs in
#              practice, plus the regulation 24)
# Outside [13, 36] → tag full_sql_round_count_anomaly (forfeits, partial
# parses, multi-match accumulator bugs in source files).
#
# The previous {16, 24, 30, 36} set was inherited from CSGO MR15 thinking
# and mis-flagged 81% of CS2 demos as anomalous. (See 2026-05-05 audit.)
MIN_VALID_ROUND_COUNT = 13
MAX_VALID_ROUND_COUNT = 36


# Tracks every distinct ``data_quality`` value this tool can write.
DATA_QUALITY_FULL_SQL = "full_sql"
DATA_QUALITY_FULL_SQL_ROUND_ANOMALY = "full_sql_round_count_anomaly"
DATA_QUALITY_COMPLETE = "complete"
DATA_QUALITY_REGISTERED_ONLY = "registered_only"
DATA_QUALITY_PARTIAL = "partial"

# Threshold below which a "player" row in matchtickstate is treated as
# observer / caster / bot noise. Mirrors register_orphan_matches.py.
MIN_NONZERO_FIELDS_FOR_REAL_PLAYER = 1


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aggregate_match_stats_sql",
        description="D2A — SQL-only PlayerMatchStats aggregator.",
    )
    parser.add_argument("--match-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--reconcile", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--really-force", action="store_true")
    parser.add_argument("--no-lock", action="store_true")
    parser.add_argument(
        "--checkpoint-file",
        type=Path,
        default=Path("Programma_CS2_RENAN/backups/d2a_checkpoint.json"),
    )
    parser.add_argument(
        "--report-out",
        type=Path,
        default=Path("docs/d2a_run_report.json"),
    )
    return parser


def _ds_split_for_demo(demo_name: str) -> str:
    """Deterministic 70/15/15 train/val/test split keyed on demo_name.

    Hashing on the demo identity keeps every player-row from the same
    match in the same split (no leakage). MD5 is non-cryptographic but
    fine for split assignment.
    """
    h = int(hashlib.md5(demo_name.encode(), usedforsecurity=False).hexdigest(), 16) % 100
    if h < 70:
        return "train"
    if h < 85:
        return "val"
    return "test"


def _safe_float(v) -> float:
    """Coerce DB values to a finite float; NaN/Inf/None map to 0.0."""
    if v is None:
        return 0.0
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(f) or math.isinf(f):
        return 0.0
    return f


def _read_match_metadata(match_db_path: Path) -> Optional[dict]:
    """Read match_metadata + minimal tick stats from a match_*.db. None if corrupted."""
    try:
        con = sqlite3.connect(f"file:{match_db_path}?mode=ro&immutable=1", uri=True)
    except sqlite3.OperationalError:
        return None
    cur = con.cursor()
    try:
        meta_row = cur.execute(
            """
            SELECT demo_name, map_name, round_count, match_date, is_pro_match,
                   team1_name, team2_name, team1_score, team2_score
            FROM match_metadata LIMIT 1
            """
        ).fetchone()
    except sqlite3.OperationalError:
        con.close()
        return None
    if not meta_row:
        con.close()
        return None
    demo_name, map_name, round_count, match_date_raw, is_pro_match, t1n, t2n, t1s, t2s = meta_row

    # Derive round_count if metadata had 0 (some bugged matches).
    if not round_count:
        try:
            derived = cur.execute("SELECT MAX(round_number) FROM matchtickstate").fetchone()[0]
            round_count = int(derived or 0)
        except sqlite3.OperationalError:
            round_count = 0

    if match_date_raw:
        try:
            match_date = datetime.fromisoformat(str(match_date_raw))
        except ValueError:
            match_date = datetime.fromtimestamp(match_db_path.stat().st_mtime, tz=timezone.utc)
    else:
        match_date = datetime.fromtimestamp(match_db_path.stat().st_mtime, tz=timezone.utc)

    con.close()
    return {
        "demo_name": str(demo_name or ""),
        "map_name": str(map_name or "de_unknown"),
        "round_count": int(round_count or 0),
        "match_date": match_date,
        "is_pro_match": bool(is_pro_match),
        "team1_name": str(t1n or ""),
        "team2_name": str(t2n or ""),
        "team1_score": int(t1s or 0),
        "team2_score": int(t2s or 0),
    }


def _aggregate_per_player(match_db_path: Path) -> list[dict]:
    """Per-player aggregation from matchtickstate + match_event_state.

    Returns a list of dicts; one entry per real player (observers and
    bots filtered via MIN_NONZERO_FIELDS_FOR_REAL_PLAYER).
    """
    con = sqlite3.connect(f"file:{match_db_path}?mode=ro&immutable=1", uri=True)
    cur = con.cursor()

    # Per-player TOTALS use cumulative MAX(_total) columns — these are the
    # source of truth in matchtickstate. The per-round counters
    # (kills_this_round etc.) are NOT a faithful decomposition of the totals:
    # they undercount on every match we cross-checked (e.g. 910 on m1-mirage:
    # MAX(kills_total)=35, SUM(MAX(kills_this_round))=17). The cumulative
    # column rolls forward across the whole match including any post-tick
    # adjustments the per-round snapshot misses.
    #
    # Per-round damage MUST come from damage_this_round (no damage_total
    # column exists in the source schema).
    rows = cur.execute(
        """
        SELECT player_name,
               steamid,
               MAX(kills_total)               AS kills,
               MAX(deaths_total)              AS deaths,
               MAX(assists_total)             AS assists,
               MAX(headshot_kills_total)      AS hs_kills,
               MAX(score)                     AS score,
               MAX(cash_spent_total)          AS cash_spent
        FROM matchtickstate
        WHERE player_name IS NOT NULL AND player_name != ''
        GROUP BY player_name, steamid
        ORDER BY player_name
        """
    ).fetchall()

    # Per-round arrays: per-round damage SUM (for total damage + adr_std),
    # per-round kills for kill_std + impact_rounds (rounds with ≥1 kill share),
    # per-round util damage / enemies flashed (for class A util fields).
    perround_rows = cur.execute(
        """
        SELECT player_name, steamid, round_number,
               MAX(kills_this_round)                AS rk,
               MAX(damage_this_round)               AS rdmg,
               MAX(utility_damage_this_round)       AS rudmg,
               MAX(enemies_flashed_this_round)      AS rblind
        FROM matchtickstate
        WHERE player_name IS NOT NULL AND player_name != ''
        GROUP BY player_name, steamid, round_number
        """
    ).fetchall()

    perround: dict[tuple, dict] = {}
    for pn, sid, rn, rk, rdmg, rudmg, rblind in perround_rows:
        d = perround.setdefault(
            (pn, sid),
            {
                "kills_per_round": [],
                "damage_per_round": [],
                "util_dmg_per_round": [],
                "blinded_per_round": [],
                "rounds_played": 0,
            },
        )
        d["kills_per_round"].append(int(rk or 0))
        d["damage_per_round"].append(int(rdmg or 0))
        d["util_dmg_per_round"].append(int(rudmg or 0))
        d["blinded_per_round"].append(int(rblind or 0))
        d["rounds_played"] += 1

    # Per-player utility damage from event stream (HE + molotov damage).
    # Smokes don't damage players, so smoke counts come from a separate
    # query against event_type='smoke_start'.
    util_rows = cur.execute(
        """
        SELECT player_name,
               SUM(CASE WHEN weapon LIKE 'hegrenade%' THEN damage ELSE 0 END) AS he_dmg,
               SUM(CASE WHEN weapon LIKE 'molotov%'
                          OR weapon LIKE 'inferno%'
                          OR weapon LIKE 'incgrenade%' THEN damage ELSE 0 END) AS molly_dmg
        FROM match_event_state
        WHERE event_type = 'player_hurt' AND player_name IS NOT NULL
        GROUP BY player_name
        """
    ).fetchall()
    smoke_rows = cur.execute(
        """
        SELECT player_name, COUNT(*) AS n
        FROM match_event_state
        WHERE event_type = 'smoke_start'
              AND player_name IS NOT NULL AND player_name != ''
        GROUP BY player_name
        """
    ).fetchall()
    smoke_lookup = {pn: int(n or 0) for pn, n in smoke_rows}
    util_lookup = {
        pn: {
            "he_dmg": _safe_float(he),
            "molly_dmg": _safe_float(molly),
            "smoke_throws": smoke_lookup.get(pn, 0),
        }
        for pn, he, molly in util_rows
    }
    # Players who threw smokes but inflicted no util damage need an entry too.
    for pn, n in smoke_lookup.items():
        if pn not in util_lookup:
            util_lookup[pn] = {"he_dmg": 0.0, "molly_dmg": 0.0, "smoke_throws": n}

    # Trade-kill detection via match_event_state.player_death.
    death_rows = cur.execute(
        """
        SELECT tick, player_name AS attacker_name, victim_name AS user_name,
               round_number AS round_num
        FROM match_event_state
        WHERE event_type = 'player_death'
              AND player_name IS NOT NULL AND player_name != ''
              AND victim_name IS NOT NULL AND victim_name != ''
        ORDER BY tick
        """
    ).fetchall()

    # Team roster from early ticks (pre-half-side-flip), via SQL.
    tick_bounds = cur.execute("SELECT MIN(tick), MAX(tick) FROM matchtickstate").fetchone()
    tmin, tmax = tick_bounds or (0, 1)
    cutoff = (tmin or 0) + int(((tmax or 1) - (tmin or 0)) * 0.1)
    roster_rows = cur.execute(
        """
        SELECT player_name, team, COUNT(*) AS n
        FROM matchtickstate
        WHERE tick <= ?
              AND player_name IS NOT NULL AND player_name != ''
              AND team IS NOT NULL AND team != ''
        GROUP BY player_name, team
        """,
        (cutoff,),
    ).fetchall()
    # Source uses full team names: 'TERRORIST' for T-side, 'CT' for CT-side.
    # Map to the team_num convention detect_trade_kills expects (2=T, 3=CT).
    # Earlier draft compared `winner.upper() == "T"` — only matched two-letter
    # codes that don't appear in this schema. Fix: handle full names too.
    _votes: dict[str, dict] = {}
    for pn, tm, n in roster_rows:
        _votes.setdefault(pn, {})[tm] = int(n or 0)
    team_roster: dict[str, int] = {}
    for pn, votes in _votes.items():
        winner = max(votes.items(), key=lambda kv: kv[1])[0]
        if isinstance(winner, str):
            w = winner.upper().strip()
            if w in ("T", "TERRORIST", "TERRORISTS"):
                tn = 2
            elif w in ("CT", "COUNTER-TERRORIST", "COUNTER_TERRORIST", "COUNTERTERRORIST"):
                tn = 3
            else:
                tn = 0
        else:
            tn = int(winner) if winner in (2, 3) else 0
        if tn:
            team_roster[pn.strip().lower()] = tn

    # R4 HIGH (2026-07-16, 26-TICK invariant): the trade window is defined in
    # ticks from the tick rate — read the per-demo rate persisted by GAP-01
    # instead of hardcoding the 64 default (which halved the real-time trade
    # window on 128-tick demos). Pre-GAP-01 match DBs lack the column.
    match_tick_rate = 0
    try:
        _tr_row = cur.execute("SELECT tick_rate FROM match_metadata LIMIT 1").fetchone()
        if _tr_row and _tr_row[0]:
            match_tick_rate = int(_tr_row[0])
    except sqlite3.OperationalError:
        match_tick_rate = 0

    con.close()

    # Run trade-kill detection on the gathered death + roster data.
    trade_per_attacker: dict[str, int] = {}
    trade_total_kills_seen: dict[str, int] = {}
    was_traded_per_victim: dict[str, int] = {}
    trade_response_ticks: dict[str, list[int]] = {}
    if death_rows and team_roster:
        import pandas as _pd  # local import — keeps cold-start light

        from Programma_CS2_RENAN.backend.data_sources.trade_kill_detector import (
            DEFAULT_TICK_RATE,
            detect_trade_kills,
        )

        if not match_tick_rate:
            print(
                f"  WARN: {match_db_path.name}: no tick_rate in match_metadata — "
                f"trade windows use default {DEFAULT_TICK_RATE} t/s"
            )
            match_tick_rate = DEFAULT_TICK_RATE

        deaths_df = _pd.DataFrame(
            death_rows, columns=["tick", "attacker_name", "user_name", "round_num"]
        )
        try:
            trade_result = detect_trade_kills(
                deaths_df=deaths_df,
                team_roster=team_roster,
                tick_rate=match_tick_rate,
            )
            # Canonical trade_details dict keys per
            # Programma_CS2_RENAN/backend/data_sources/trade_kill_detector.py:238-248:
            #   trade_killer    — player who got the revenge kill (the "trader")
            #   original_killer — enemy player who killed our teammate
            #   original_victim — the teammate whose death was avenged ("was traded")
            #   response_ticks  — gap between the two kills
            for det in trade_result.trade_details:
                attacker = det.get("trade_killer")
                if attacker:
                    a = str(attacker).strip().lower()
                    trade_per_attacker[a] = trade_per_attacker.get(a, 0) + 1
                    if "response_ticks" in det:
                        trade_response_ticks.setdefault(a, []).append(int(det["response_ticks"]))

                victim = det.get("original_victim")
                if victim:
                    v = str(victim).strip().lower()
                    was_traded_per_victim[v] = was_traded_per_victim.get(v, 0) + 1
        except Exception as e:  # noqa: BLE001 — graceful on parser quirks
            print(f"  WARN: trade-kill detection failed for {match_db_path.name}: {e}")

    aggregates: list[dict] = []
    for row in rows:
        (
            player_name,
            steamid,
            kills,
            deaths,
            assists,
            hs_kills,
            score,
            cash_spent,
        ) = row
        kills = int(kills or 0)
        deaths = int(deaths or 0)
        hs_kills = int(hs_kills or 0)
        if max(kills, deaths, hs_kills) < MIN_NONZERO_FIELDS_FOR_REAL_PLAYER:
            # Observer / caster / bot row — every total counter at zero.
            continue

        pr = perround.get(
            (player_name, steamid),
            {
                "kills_per_round": [],
                "damage_per_round": [],
                "util_dmg_per_round": [],
                "blinded_per_round": [],
                "rounds_played": 0,
            },
        )
        damage = sum(pr["damage_per_round"])
        util_dmg = sum(pr["util_dmg_per_round"])
        enemies_blinded = sum(pr["blinded_per_round"])
        rounds_played = pr["rounds_played"]

        util = util_lookup.get(player_name, {"he_dmg": 0.0, "molly_dmg": 0.0, "smoke_throws": 0})
        nlow = str(player_name).strip().lower()
        my_trade_kills = trade_per_attacker.get(nlow, 0)
        my_was_traded = was_traded_per_victim.get(nlow, 0)
        my_response_ticks = trade_response_ticks.get(nlow, [])
        aggregates.append(
            {
                "player_name": str(player_name),
                "steamid": int(steamid) if steamid is not None else None,
                "kills": kills,
                "deaths": deaths,
                "assists": int(assists or 0),
                "hs_kills": hs_kills,
                "damage": damage,
                "util_dmg": util_dmg,
                "enemies_blinded": enemies_blinded,
                "rounds_played": rounds_played,
                "score": int(score or 0),
                "cash_spent": int(cash_spent or 0),
                "kills_list": [float(k) for k in pr["kills_per_round"]],
                "adr_list": [float(d) for d in pr["damage_per_round"]],
                "he_dmg": util["he_dmg"],
                "molly_dmg": util["molly_dmg"],
                "smoke_throws": util["smoke_throws"],
                "trade_kills": my_trade_kills,
                "was_traded": my_was_traded,
                "avg_trade_response_ticks": (
                    sum(my_response_ticks) / len(my_response_ticks) if my_response_ticks else 0.0
                ),
            }
        )
    return aggregates


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)


def _build_player_match_stats(meta: dict, agg: dict, source_path: Path):
    """Compose a PlayerMatchStats SQLModel instance for one (match, player)."""
    from Programma_CS2_RENAN.backend.processing.feature_engineering import kast as kast_mod
    from Programma_CS2_RENAN.backend.processing.feature_engineering import rating as rating_mod
    from Programma_CS2_RENAN.backend.storage.db_models import DatasetSplit, PlayerMatchStats

    rounds = meta["round_count"] or agg["rounds_played"] or 1
    kills = agg["kills"]
    deaths = agg["deaths"]
    assists = agg["assists"]
    damage = agg["damage"]
    hs_kills = agg["hs_kills"]

    avg_kills = kills / rounds
    avg_deaths = deaths / rounds
    avg_adr = damage / rounds
    avg_hs = hs_kills / kills if kills > 0 else 0.0
    kpr = avg_kills
    dpr = avg_deaths
    kd_ratio = kills / deaths if deaths > 0 else float(kills)

    # KAST estimate from kills/assists/deaths/rounds (closed-form).
    kast = kast_mod.estimate_kast_from_stats(kills, assists, deaths, rounds)

    # HLTV 2.0 rating components + aggregate via the canonical SSOT
    # (rating.compute_rating_components). The rating_* columns carry RAW
    # components — a prior draft wrote baseline-normalized ratios here,
    # which silently disagreed with demo_parser/base_features and corrupted
    # every downstream Z-score against pro_baseline.
    components = rating_mod.compute_rating_components(kpr=kpr, dpr=dpr, kast=kast, avg_adr=avg_adr)
    rating_kpr = components["rating_kpr"]
    rating_survival = components["rating_survival"]
    rating_kast = components["rating_kast"]
    rating_impact = components["rating_impact"]
    rating_adr = components["rating_adr"]
    rating_aggregate = components["rating"]

    kill_std = _stdev(agg["kills_list"])
    adr_per_round = [v / 1.0 for v in agg["adr_list"]]  # rdmg already per-round
    adr_std = _stdev(adr_per_round)

    # impact_rounds: share of rounds where the player got at least 1 kill.
    # This is the canonical "impact" count metric (different from the HLTV
    # 2.0 rating_impact COMPONENT, which is a normalized score). Conflating
    # them was a bug in the prior draft.
    if rounds > 0 and agg["kills_list"]:
        rounds_with_kill_share = sum(1 for k in agg["kills_list"] if k > 0) / rounds
    else:
        rounds_with_kill_share = 0.0

    # Trade-kill ratios. The detector populated raw counts in agg; convert
    # to ratios per the existing PlayerMatchStats semantics.
    trade_kill_ratio = agg["trade_kills"] / max(1, kills)
    was_traded_ratio = agg["was_traded"] / max(1, deaths)
    avg_trade_response_ticks = float(agg["avg_trade_response_ticks"])

    # Tag: full_sql, or anomaly variant if round_count is outside the sane
    # CS2 MR12 band [MIN_VALID_ROUND_COUNT, MAX_VALID_ROUND_COUNT].
    if MIN_VALID_ROUND_COUNT <= meta["round_count"] <= MAX_VALID_ROUND_COUNT:
        data_quality = DATA_QUALITY_FULL_SQL
    else:
        data_quality = DATA_QUALITY_FULL_SQL_ROUND_ANOMALY

    # is_pro override: source path under PRO_DEMO_PATH/match_data/ → pro.
    # The metadata.is_pro_match flag is unreliable (sample showed 0 for
    # known-pro Vitality match). Path-based override is canonical truth.
    is_pro = bool(meta["is_pro_match"]) or "DEMO_PRO_PLAYERS" in str(source_path)

    demo_stem = meta["demo_name"]
    if demo_stem.endswith(".dem"):
        demo_stem = demo_stem[: -len(".dem")]

    return PlayerMatchStats(
        player_name=agg["player_name"],
        steamid=agg["steamid"],
        demo_name=demo_stem,
        match_date=meta["match_date"],
        processed_at=datetime.now(timezone.utc),
        dataset_split=DatasetSplit(_ds_split_for_demo(demo_stem)),
        data_quality=data_quality,
        avg_kills=float(avg_kills),
        avg_deaths=float(avg_deaths),
        avg_adr=float(avg_adr),
        avg_hs=float(avg_hs),
        avg_kast=float(kast),
        accuracy=0.0,  # Class B — needs .dem
        econ_rating=0.0,  # No canonical SQL-only formula in codebase. D2B may
        # populate from .dem round-economy events.
        kill_std=float(kill_std),
        adr_std=float(adr_std),
        kd_ratio=float(kd_ratio),
        impact_rounds=float(rounds_with_kill_share),
        utility_blind_time=0.0,  # Class B
        utility_enemies_blinded=float(agg["enemies_blinded"]),
        flash_assists=0.0,  # Class B (full). The match_event_state.flash_detonate
        # events carry empty victim_name in current sources, so per-victim
        # blind tracking requires .dem re-parse (D2B).
        opening_duel_win_pct=0.0,  # Class B
        clutch_win_pct=0.0,  # Class B
        positional_aggression_score=0.0,  # Class B
        kpr=float(kpr),
        dpr=float(dpr),
        rating_impact=float(rating_impact),
        rating_survival=float(rating_survival),
        rating_kast=float(rating_kast),
        rating_kpr=float(rating_kpr),
        rating_adr=float(rating_adr),
        trade_kill_ratio=float(trade_kill_ratio),
        was_traded_ratio=float(was_traded_ratio),
        avg_trade_response_ticks=float(avg_trade_response_ticks),
        thrusmoke_kill_pct=0.0,  # Class B
        wallbang_kill_pct=0.0,
        noscope_kill_pct=0.0,
        blind_kill_pct=0.0,
        he_damage_per_round=float(agg["he_dmg"] / rounds),
        molotov_damage_per_round=float(agg["molly_dmg"] / rounds),
        smokes_per_round=float(agg["smoke_throws"] / rounds),
        unused_utility_per_round=0.0,  # Class B
        anomaly_score=0.0,
        sample_weight=1.0,
        is_pro=is_pro,
        rating=max(0.0, min(5.0, float(rating_aggregate))),
    )


def _existing_quality(session, demo_name: str, player_name: str) -> Optional[str]:
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    return session.exec(
        select(PlayerMatchStats.data_quality).where(
            PlayerMatchStats.demo_name == demo_name,
            PlayerMatchStats.player_name == player_name,
        )
    ).first()


# ---------------------------------------------------------------------------
# Reconciliation against existing 'complete' rows
# ---------------------------------------------------------------------------

# Per master plan §5 D2A.4. Halt if more than ROW_HALT_PCT of the reconciled
# rows show > FIELD_TOLERANCE_PCT drift on any single Class-A field.
RECONCILE_FIELD_TOLERANCE_PCT = 5.0
RECONCILE_ROW_HALT_PCT = 10.0

# Class-A fields whose drift between the existing 'complete' row and a fresh
# SQL re-derivation matters. Class B fields stay at 0 in full_sql, so diffing
# them against a (potentially populated) complete row would always show drift
# for the wrong reason.
RECONCILE_FIELDS = (
    "avg_kills",
    "avg_deaths",
    "avg_adr",
    "avg_hs",
    "avg_kast",
    "kpr",
    "dpr",
    "kd_ratio",
    "kill_std",
    "adr_std",
    "impact_rounds",
    "rating",
    "rating_impact",
    "rating_survival",
    "rating_kast",
    "rating_kpr",
    "rating_adr",
    "trade_kill_ratio",
    "was_traded_ratio",
    "he_damage_per_round",
    "molotov_damage_per_round",
    "smokes_per_round",
    "utility_enemies_blinded",
)


def _reconcile_against_complete(report_path: Path) -> dict:
    """Diff fresh aggregates against existing data_quality='complete' rows.

    Returns the report dict; also writes JSON to report_path. Does not write
    anything to playermatchstats.
    """
    from Programma_CS2_RENAN.backend.storage.match_data_manager import get_match_data_manager
    from Programma_CS2_RENAN.core.config import CORE_DB_DIR

    monolith_path = Path(CORE_DB_DIR) / "database.db"
    mdm = get_match_data_manager()
    match_data_dir = Path(mdm.match_data_path)

    # Pull existing complete rows via raw sqlite3 (read-only; no lock contention).
    _conn = sqlite3.connect(f"file:{monolith_path}?mode=ro", uri=True)
    try:
        cur = _conn.cursor()
        # B608 false positive: RECONCILE_FIELDS and DATA_QUALITY_COMPLETE are
        # hardcoded module constants (not user input) — no SQL-injection vector.
        _cols = ", ".join(RECONCILE_FIELDS)
        _sql = f"SELECT demo_name, player_name, {_cols} FROM playermatchstats WHERE data_quality = '{DATA_QUALITY_COMPLETE}'"  # nosec B608
        cur.execute(_sql)
        existing = {(r[0], r[1]): r[2:] for r in cur.fetchall()}
    finally:
        _conn.close()
    if not existing:
        report = {
            "verdict": "no_complete_rows",
            "rows_compared": 0,
            "drifts": [],
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2))
        return report

    # Map demo_name → match_*.db source path.
    demos_needed = {d for (d, _) in existing}
    src_for_demo: dict[str, Path] = {}
    for sp in match_data_dir.glob("match_*.db"):
        meta = _read_match_metadata(sp)
        if meta and meta["demo_name"] in demos_needed:
            src_for_demo[meta["demo_name"]] = sp
        if len(src_for_demo) == len(demos_needed):
            break

    drifts: list[dict] = []
    rows_compared = 0
    rows_with_drift = 0

    for demo in sorted(demos_needed):
        sp = src_for_demo.get(demo)
        if sp is None:
            drifts.append({"demo_name": demo, "issue": "source_match_db_missing"})
            continue
        meta = _read_match_metadata(sp)
        if meta is None:
            drifts.append({"demo_name": demo, "issue": "metadata_unreadable"})
            continue
        try:
            aggs = _aggregate_per_player(sp)
        except sqlite3.OperationalError as e:
            drifts.append({"demo_name": demo, "issue": f"aggregator_error: {e}"})
            continue

        new_by_player = {a["player_name"]: a for a in aggs}

        for (d, pname), old_vals in existing.items():
            if d != demo:
                continue
            new_agg = new_by_player.get(pname)
            if new_agg is None:
                drifts.append(
                    {
                        "demo_name": demo,
                        "player_name": pname,
                        "issue": "player_missing_in_new_aggregate",
                    }
                )
                continue
            new_pms = _build_player_match_stats(meta, new_agg, sp)
            row_drifts: dict[str, dict] = {}
            for i, fld in enumerate(RECONCILE_FIELDS):
                old_v = _safe_float(old_vals[i])
                new_v = _safe_float(getattr(new_pms, fld, 0.0))
                if abs(old_v) < 1e-6 and abs(new_v) < 1e-6:
                    continue
                denom = max(abs(old_v), 1e-6)
                pct = abs(old_v - new_v) / denom * 100.0
                if pct > RECONCILE_FIELD_TOLERANCE_PCT:
                    row_drifts[fld] = {
                        "old": round(old_v, 4),
                        "new": round(new_v, 4),
                        "pct": round(pct, 2),
                    }
            rows_compared += 1
            if row_drifts:
                rows_with_drift += 1
                drifts.append(
                    {
                        "demo_name": demo,
                        "player_name": pname,
                        "drifts": row_drifts,
                    }
                )

    drift_row_pct = rows_with_drift / rows_compared * 100.0 if rows_compared else 0.0
    halt = drift_row_pct > RECONCILE_ROW_HALT_PCT
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows_compared": rows_compared,
        "rows_with_drift": rows_with_drift,
        "drift_row_pct": round(drift_row_pct, 2),
        "field_tolerance_pct": RECONCILE_FIELD_TOLERANCE_PCT,
        "halt_threshold_row_pct": RECONCILE_ROW_HALT_PCT,
        "verdict": "drift_detected" if halt else "within_tolerance",
        "drifts": drifts,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, default=str))
    return report


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    write_mode = args.commit
    if write_mode:
        args.dry_run = False

    if args.really_force and not args.commit:
        print("ERROR: --really-force without --commit makes no sense; aborting.")
        return 2

    print(f"=== D2A — SQL-only PlayerMatchStats aggregator ===")
    print(f"  Mode:               {'COMMIT' if write_mode else 'DRY-RUN'}")
    print(f"  Force flags:        force={args.force} really_force={args.really_force}")
    print(f"  Reconcile-only:     {args.reconcile}")
    print(f"  Limit:              {args.limit or '<all>'}")
    print(f"  Match-id:           {args.match_id or '<all>'}")
    print(f"  Checkpoint:         {args.checkpoint_file}")
    print(f"  Report:             {args.report_out}")
    print()

    # Reconcile-only mode: diff against existing 'complete' rows; do not write.
    if args.reconcile:
        report = _reconcile_against_complete(args.report_out)
        print(
            f"  reconcile: rows_compared={report.get('rows_compared', 0)}, "
            f"rows_with_drift={report.get('rows_with_drift', 0)} "
            f"({report.get('drift_row_pct', 0)}% > {report.get('halt_threshold_row_pct', 0)}% halt) "
            f"→ verdict={report.get('verdict', '?')}"
        )
        print(f"  Report written: {args.report_out}")
        return 2 if report.get("verdict") == "drift_detected" else 0

    # Lock acquisition only when writing.
    lock_acquired = False
    if write_mode and not args.no_lock:
        lock_files.install_signal_handlers()
        try:
            lock_files.acquire("d_track_running")
            lock_acquired = True
            print("  Lock acquired: d_track_running\n")
        except lock_files.LockConflict as conflict:
            print(f"  Lock acquisition FAILED: {conflict}")
            return 2

    if args.really_force:
        print("  WARNING: --really-force will overwrite existing 'complete' rows.")
        for s in (5, 4, 3, 2, 1):
            print(f"    Continuing in {s}s...", end="\r", flush=True)
            time.sleep(1)
        print()

    try:
        from Programma_CS2_RENAN.backend.storage.database import get_db_manager
        from Programma_CS2_RENAN.backend.storage.match_data_manager import (
            MatchDataManager,
            get_match_data_manager,
        )

        mdm: MatchDataManager = get_match_data_manager()
        match_data_dir = Path(mdm.match_data_path)
        match_files = sorted(match_data_dir.glob("match_*.db"))
        if args.match_id is not None:
            match_files = [f for f in match_files if f.stem == f"match_{args.match_id}"]
        if args.limit:
            match_files = match_files[: args.limit]
        print(f"  match_*.db files to consider: {len(match_files)}")

        db = get_db_manager()
        report = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "mode": "commit" if write_mode else "dry-run",
            "matches_seen": 0,
            "matches_skipped_missing_metadata": 0,
            "matches_processed": 0,
            "rows_written": 0,
            "rows_skipped_complete": 0,
            "rows_skipped_needs_force": 0,
            "rows_skipped_noise": 0,
            "rows_overwritten": 0,
            "errors": [],
        }

        for src in match_files:
            report["matches_seen"] += 1
            meta = _read_match_metadata(src)
            if meta is None or not meta["demo_name"]:
                report["matches_skipped_missing_metadata"] += 1
                continue
            try:
                aggs = _aggregate_per_player(src)
            except sqlite3.OperationalError as agg_err:
                report["errors"].append({"file": src.name, "error": str(agg_err)})
                continue

            for agg in aggs:
                pms = _build_player_match_stats(meta, agg, src)
                if write_mode:
                    with db.get_session() as session:
                        existing = _existing_quality(session, pms.demo_name, pms.player_name)
                    skip = False
                    if existing == DATA_QUALITY_COMPLETE and not args.really_force:
                        skip = True
                        report["rows_skipped_complete"] += 1
                    # R4 MED: --force was a no-op — the CLI contract says
                    # registered_only/partial rows are overwritten only WITH
                    # --force, but the write path never consulted the flag.
                    elif (
                        existing in (DATA_QUALITY_REGISTERED_ONLY, DATA_QUALITY_PARTIAL)
                        and not args.force
                        and not args.really_force
                    ):
                        skip = True
                        report["rows_skipped_needs_force"] += 1
                    if not skip:
                        if existing == DATA_QUALITY_COMPLETE:
                            report["rows_overwritten"] += 1
                        db.upsert(pms)
                        report["rows_written"] += 1
                else:
                    # Dry-run only counts what WOULD be written.
                    report["rows_written"] += 1

            report["matches_processed"] += 1

        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(json.dumps(report, indent=2, default=str))
        print(f"\n  Report written: {args.report_out}")
        print(
            f"  Summary: matches={report['matches_processed']}/{report['matches_seen']}, "
            f"rows={report['rows_written']}, "
            f"skipped(complete)={report['rows_skipped_complete']}, "
            f"skipped(needs --force)={report['rows_skipped_needs_force']}, "
            f"errors={len(report['errors'])}"
        )
        return 0
    finally:
        if lock_acquired:
            lock_files.release("d_track_running")
            print("  Lock released: d_track_running")


if __name__ == "__main__":
    sys.exit(main())
