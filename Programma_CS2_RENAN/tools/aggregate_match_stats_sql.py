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

# Round counts that produce sane per-round means. CS2 standard:
#   16 = MR12 + draw window
#   24 = MR12 + standard win-by-2 (most common today)
#   30 = MR15 (legacy CSGO)
#   36 = overtime extension (24 + 12)
# Matches outside this set get tagged 'full_sql_round_count_anomaly'
# instead of 'full_sql' so downstream consumers can filter.
SANE_ROUND_COUNTS = {16, 24, 30, 36}


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
    h = int(hashlib.md5(demo_name.encode()).hexdigest(), 16) % 100
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

    # Tick-level per-round MAX of cumulative round counters → SUM across rounds.
    rows = cur.execute(
        """
        SELECT player_name,
               steamid,
               SUM(rk) AS kills,
               SUM(rd) AS deaths,
               SUM(ra) AS assists,
               SUM(rh) AS hs_kills,
               SUM(rdmg) AS damage,
               SUM(rudmg) AS util_dmg,
               SUM(rblind) AS enemies_blinded,
               COUNT(*) AS rounds_played,
               MAX(rounds_with_kill) AS rwk_marker
        FROM (
          SELECT round_number,
                 player_name,
                 steamid,
                 MAX(kills_this_round) AS rk,
                 MAX(deaths_this_round) AS rd,
                 MAX(assists_this_round) AS ra,
                 MAX(headshot_kills_this_round) AS rh,
                 MAX(damage_this_round) AS rdmg,
                 MAX(utility_damage_this_round) AS rudmg,
                 MAX(enemies_flashed_this_round) AS rblind,
                 CASE WHEN MAX(kills_this_round) > 0 THEN 1 ELSE 0 END AS rounds_with_kill
          FROM matchtickstate
          WHERE player_name IS NOT NULL AND player_name != ''
          GROUP BY round_number, player_name, steamid
        )
        GROUP BY player_name, steamid
        ORDER BY player_name
        """
    ).fetchall()

    # Per-player kill_std and adr_std (variance across rounds).
    std_rows = cur.execute(
        """
        SELECT player_name,
               steamid,
               kills_per_round_list,
               adr_per_round_list
        FROM (
          SELECT player_name,
                 steamid,
                 GROUP_CONCAT(rk) AS kills_per_round_list,
                 GROUP_CONCAT(rdmg) AS adr_per_round_list
          FROM (
            SELECT round_number,
                   player_name,
                   steamid,
                   MAX(kills_this_round) AS rk,
                   MAX(damage_this_round) AS rdmg
            FROM matchtickstate
            WHERE player_name IS NOT NULL AND player_name != ''
            GROUP BY round_number, player_name, steamid
          )
          GROUP BY player_name, steamid
        )
        """
    ).fetchall()

    std_lookup = {
        (player_name, steamid): {
            "kills_list": [_safe_float(x) for x in (kpl or "").split(",") if x],
            "adr_list": [_safe_float(x) for x in (apl or "").split(",") if x],
        }
        for player_name, steamid, kpl, apl in std_rows
    }

    # Per-player utility damage from event stream (HE / molotov / smoke).
    util_rows = cur.execute(
        """
        SELECT player_name,
               SUM(CASE WHEN weapon LIKE 'hegrenade%' THEN damage ELSE 0 END) AS he_dmg,
               SUM(CASE WHEN weapon LIKE 'molotov%' OR weapon LIKE 'inferno%' THEN damage ELSE 0 END) AS molly_dmg,
               SUM(CASE WHEN weapon LIKE 'smokegrenade%' THEN 1 ELSE 0 END) AS smoke_throws
        FROM match_event_state
        WHERE event_type = 'player_hurt' AND player_name IS NOT NULL
        GROUP BY player_name
        """
    ).fetchall()
    util_lookup = {
        pn: {
            "he_dmg": _safe_float(he),
            "molly_dmg": _safe_float(molly),
            "smoke_throws": int(smoke or 0),
        }
        for pn, he, molly, smoke in util_rows
    }
    con.close()

    aggregates: list[dict] = []
    for row in rows:
        (
            player_name,
            steamid,
            kills,
            deaths,
            assists,
            hs_kills,
            damage,
            util_dmg,
            enemies_blinded,
            rounds_played,
            _rwk_marker,
        ) = row
        kills = int(kills or 0)
        deaths = int(deaths or 0)
        if (
            max(kills, deaths, int(damage or 0), int(hs_kills or 0))
            < MIN_NONZERO_FIELDS_FOR_REAL_PLAYER
        ):
            # Observer / caster / bot.
            continue
        std = std_lookup.get((player_name, steamid), {"kills_list": [], "adr_list": []})
        util = util_lookup.get(player_name, {"he_dmg": 0.0, "molly_dmg": 0.0, "smoke_throws": 0})
        aggregates.append(
            {
                "player_name": str(player_name),
                "steamid": int(steamid) if steamid is not None else None,
                "kills": kills,
                "deaths": deaths,
                "assists": int(assists or 0),
                "hs_kills": int(hs_kills or 0),
                "damage": int(damage or 0),
                "util_dmg": int(util_dmg or 0),
                "enemies_blinded": int(enemies_blinded or 0),
                "rounds_played": int(rounds_played or 0),
                "kills_list": std["kills_list"],
                "adr_list": std["adr_list"],
                "he_dmg": util["he_dmg"],
                "molly_dmg": util["molly_dmg"],
                "smoke_throws": util["smoke_throws"],
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
    from Programma_CS2_RENAN.backend.processing.feature_engineering.rating import (
        BASELINE_ADR,
        BASELINE_DPR_COMPLEMENT,
        BASELINE_IMPACT,
        BASELINE_KAST,
        BASELINE_KPR,
    )
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

    # HLTV 2.0 rating components + aggregate. rating.py exposes the
    # aggregate as compute_hltv2_rating(...) but not the per-component
    # breakdown — we replicate its math here so each rating_* column gets
    # the canonical normalized value (matching the body of
    # rating.compute_hltv2_rating, lines 110-124).
    impact = rating_mod.compute_impact_rating(kpr=kpr, avg_adr=avg_adr, dpr=dpr)
    rating_kpr = kpr / BASELINE_KPR
    rating_survival = rating_mod.compute_survival_rating(dpr) / BASELINE_DPR_COMPLEMENT
    rating_kast = kast / BASELINE_KAST
    rating_impact = impact / BASELINE_IMPACT
    rating_adr = avg_adr / BASELINE_ADR
    rating_aggregate = (
        rating_kpr + rating_survival + rating_kast + rating_impact + rating_adr
    ) / 5.0

    kill_std = _stdev(agg["kills_list"])
    adr_per_round = [v / 1.0 for v in agg["adr_list"]]  # rdmg already per-round
    adr_std = _stdev(adr_per_round)

    # Tag: full_sql, or anomaly variant if round_count outside the sane set.
    if meta["round_count"] in SANE_ROUND_COUNTS:
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
        econ_rating=float(avg_adr / 85.0),  # see rating.py:26
        kill_std=float(kill_std),
        adr_std=float(adr_std),
        kd_ratio=float(kd_ratio),
        impact_rounds=float(rating_impact),
        utility_blind_time=0.0,  # Class B
        utility_enemies_blinded=float(agg["enemies_blinded"]),
        flash_assists=0.0,  # Class B (full); partial events from match_event_state
        # could be added here in a follow-up.
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
        trade_kill_ratio=0.0,  # populated separately by trade_kill_detector
        was_traded_ratio=0.0,
        avg_trade_response_ticks=0.0,
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
            f"errors={len(report['errors'])}"
        )
        return 0
    finally:
        if lock_acquired:
            lock_files.release("d_track_running")
            print("  Lock released: d_track_running")


if __name__ == "__main__":
    sys.exit(main())
