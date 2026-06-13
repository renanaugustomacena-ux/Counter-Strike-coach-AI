"""Registration-only pass for orphan match_*.db files.

Background
----------
The demo ingestion pipeline writes per-match SQLite databases at
``DEMO_PRO_PLAYERS/match_data/match_{id}.db`` containing the parsed tick
stream and event log. The aggregate per-player numbers that feed the
dashboard live in ``database.db`` table ``playermatchstats``. When the
ingestion pipeline is interrupted between those two writes — or when only
the per-match files are restored from a backup — the dashboard sees no
matches even though hundreds of fully-parsed match files sit on disk.

This tool walks every ``match_*.db`` under the configured pro-demo path
and emits a ``PlayerMatchStats`` row per (demo, player) without
re-parsing the .dem source. Aggregations are computed directly from the
tick stream's per-round cumulative counters. Numeric fields that need
the full ML pipeline (rating, opening duels, clutches, trade-kill
timing) stay zero; rows are tagged ``data_quality='registered_only'`` so
a follow-up backfill job can find and complete them.

Safety
------
- Default mode is dry-run; ``--commit`` is required to write.
- Refuses to overwrite rows whose existing ``data_quality='complete'``
  unless ``--force`` is given.
- Uses ``UPSERT ON CONFLICT (demo_name, player_name)`` so re-runs are
  idempotent.
- Source ``match_*.db`` files are opened read-only; this tool never
  mutates the per-match data.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# Threshold below which a "player" row is treated as observer / caster / bot
# noise: the matchtickstate table includes spectators with no kills, deaths,
# or damage across the full match.
MIN_NONZERO_FIELDS = 1

# data_quality marker for registration-only rows. A follow-up backfill job
# can target rows with this label without touching ``complete`` rows.
DATA_QUALITY_REGISTERED = "registered_only"

REQUIRED_TABLES = {"match_metadata", "matchtickstate"}


@dataclass(frozen=True)
class MatchSummary:
    """Per-match metadata extracted from a single match_*.db file."""

    demo_name: str
    map_name: str
    round_count: int
    match_date: datetime
    is_pro_match: bool


@dataclass(frozen=True)
class PlayerAggregate:
    """Per-player aggregate computed from per-round cumulative counters."""

    player_name: str
    total_kills: int
    total_deaths: int
    total_damage: int
    total_headshots: int
    rounds_played: int

    @property
    def is_noise(self) -> bool:
        nonzero = sum(
            1
            for v in (
                self.total_kills,
                self.total_deaths,
                self.total_damage,
                self.total_headshots,
            )
            if v
        )
        return nonzero < MIN_NONZERO_FIELDS


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="register_orphan_matches",
        description="Register parsed match_*.db files into PlayerMatchStats without re-parsing.",
    )
    parser.add_argument(
        "--match-data-dir",
        type=Path,
        default=None,
        help="Directory holding match_*.db files. Defaults to PRO_DEMO_PATH/match_data.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually write rows. Without this flag the tool runs read-only.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing rows even if their data_quality is 'complete'.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N match files (0 = all). Useful for spot-checks.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log per-file detail (otherwise only summary + warnings).",
    )
    return parser


def _resolve_match_data_dir(cli_dir: Optional[Path]) -> Path:
    if cli_dir is not None:
        return cli_dir
    # Default: PRO_DEMO_PATH/match_data — falls through cleanly when env empty.
    from Programma_CS2_RENAN.core.config import get_setting

    pro_demo_path = get_setting("PRO_DEMO_PATH", "")
    if not pro_demo_path:
        raise SystemExit(
            "PRO_DEMO_PATH not set and --match-data-dir not provided. "
            "Set the env or pass --match-data-dir <path>."
        )
    return Path(pro_demo_path) / "match_data"


def _iter_match_files(root: Path, limit: int) -> Iterable[Path]:
    if not root.is_dir():
        raise SystemExit(f"match_data directory does not exist: {root}")
    files = sorted(root.glob("match_*.db"))
    if limit > 0:
        files = files[:limit]
    return files


def _load_match_summary(con: sqlite3.Connection, src: Path) -> Optional[MatchSummary]:
    cur = con.cursor()
    row = cur.execute(
        "SELECT demo_name, map_name, round_count, match_date, is_pro_match "
        "FROM match_metadata LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    demo_name, map_name, round_count, match_date_raw, is_pro_match = row

    # round_count is unreliable on some recorded matches; derive from the tick
    # stream when the metadata writer left it at 0.
    if not round_count:
        derived = cur.execute("SELECT MAX(round_number) FROM matchtickstate").fetchone()[0]
        round_count = int(derived or 0)

    # match_date can be NULL on older parser versions; fall back to file mtime
    # so the dashboard still has a sortable timestamp.
    if match_date_raw:
        try:
            match_date = datetime.fromisoformat(match_date_raw)
        except ValueError:
            match_date = datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc)
    else:
        match_date = datetime.fromtimestamp(src.stat().st_mtime, tz=timezone.utc)

    # Files at this path were ingested via the pro-demo flow, so even when the
    # metadata writer flagged is_pro_match=0 we treat them as pro for the
    # registration row. The ML pipeline can re-classify on full ingestion.
    return MatchSummary(
        demo_name=str(demo_name or src.stem.replace("match_", "")),
        map_name=str(map_name or "de_unknown"),
        round_count=int(round_count or 0),
        match_date=match_date,
        is_pro_match=True,
    )


def _player_aggregates(con: sqlite3.Connection) -> list[PlayerAggregate]:
    """Compute per-player aggregates from cumulative per-round counters.

    matchtickstate.kills_this_round (etc.) reset to 0 at the start of each
    round, so the per-round MAX is the round total. Summing across rounds
    yields the match total without re-parsing the .dem.
    """
    cur = con.cursor()
    rows = cur.execute(
        """
        SELECT player_name,
               SUM(round_kills)     AS total_kills,
               SUM(round_deaths)    AS total_deaths,
               SUM(round_damage)    AS total_damage,
               SUM(round_headshots) AS total_headshots,
               COUNT(*)             AS rounds_played
        FROM (
          SELECT round_number, player_name,
                 MAX(kills_this_round)          AS round_kills,
                 MAX(deaths_this_round)         AS round_deaths,
                 MAX(damage_this_round)         AS round_damage,
                 MAX(headshot_kills_this_round) AS round_headshots
          FROM matchtickstate
          WHERE player_name IS NOT NULL AND player_name != ''
          GROUP BY round_number, player_name
        )
        GROUP BY player_name
        ORDER BY player_name
        """
    ).fetchall()
    aggregates = []
    for player_name, k, d, dmg, hs, rounds in rows:
        aggregates.append(
            PlayerAggregate(
                player_name=str(player_name),
                total_kills=int(k or 0),
                total_deaths=int(d or 0),
                total_damage=int(dmg or 0),
                total_headshots=int(hs or 0),
                rounds_played=int(rounds or 0),
            )
        )
    return aggregates


def _build_player_match_stats(
    summary: MatchSummary,
    agg: PlayerAggregate,
):
    """Construct an unsaved PlayerMatchStats instance for one (match, player)."""
    from Programma_CS2_RENAN.backend.storage.db_models import DatasetSplit, PlayerMatchStats

    # Use round_count from metadata if available, else fall back to the player's
    # rounds_played. This handles cases where the metadata round_count is 0 but
    # the player participated in N rounds (player joined late, etc.).
    rounds = summary.round_count or agg.rounds_played or 1

    avg_kills = agg.total_kills / rounds
    avg_deaths = agg.total_deaths / rounds
    avg_adr = agg.total_damage / rounds
    avg_hs = agg.total_headshots / agg.total_kills if agg.total_kills > 0 else 0.0
    kd_ratio = (
        agg.total_kills / agg.total_deaths if agg.total_deaths > 0 else float(agg.total_kills)
    )

    # Demo name is the canonical key; strip any trailing extension to match
    # the convention used by run_ingestion._save_player_stats (Path(name).stem).
    demo_stem = summary.demo_name
    if demo_stem.endswith(".dem"):
        demo_stem = demo_stem[: -len(".dem")]

    return PlayerMatchStats(
        player_name=agg.player_name,
        demo_name=demo_stem,
        match_date=summary.match_date,
        processed_at=datetime.now(timezone.utc),
        dataset_split=DatasetSplit.UNASSIGNED,
        data_quality=DATA_QUALITY_REGISTERED,
        avg_kills=float(avg_kills),
        avg_deaths=float(avg_deaths),
        avg_adr=float(avg_adr),
        avg_hs=float(avg_hs),
        kpr=float(avg_kills),
        dpr=float(avg_deaths),
        kd_ratio=float(kd_ratio),
        is_pro=summary.is_pro_match,
    )


def _existing_data_quality(session, demo_name: str, player_name: str) -> Optional[str]:
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats

    row = session.exec(
        select(PlayerMatchStats.data_quality).where(
            PlayerMatchStats.demo_name == demo_name,
            PlayerMatchStats.player_name == player_name,
        )
    ).first()
    return row


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    log_level = logging.DEBUG if args.verbose else logging.INFO
    # force=True overrides any logging config the project's transitive imports
    # may have set; without it the root logger keeps a parent handler that
    # silently drops WARNING/ERROR records we emit here.
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )
    log = logging.getLogger("register_orphan_matches")
    log.setLevel(log_level)

    match_dir = _resolve_match_data_dir(args.match_data_dir)
    files = list(_iter_match_files(match_dir, args.limit))
    log.info("Scanning %s — found %d match_*.db files", match_dir, len(files))
    if not files:
        log.info("Nothing to do.")
        return 0

    if args.commit:
        from Programma_CS2_RENAN.backend.storage.database import get_db_manager

        db_manager = get_db_manager()
    else:
        db_manager = None
        log.info("DRY RUN — no rows will be written. Re-run with --commit to persist.")

    stats_seen = 0
    stats_inserted = 0
    stats_skipped_complete = 0
    stats_skipped_noise = 0
    stats_failed = 0
    started = time.monotonic()

    for idx, src in enumerate(files, 1):
        try:
            uri = f"file:{src}?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as con:
                con.row_factory = sqlite3.Row
                tables = {
                    r[0]
                    for r in con.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                if not REQUIRED_TABLES.issubset(tables):
                    log.warning("%s missing required tables; skipping", src.name)
                    stats_failed += 1
                    continue
                summary = _load_match_summary(con, src)
                if summary is None:
                    log.warning("%s has no match_metadata row; skipping", src.name)
                    stats_failed += 1
                    continue
                aggregates = _player_aggregates(con)

            if not aggregates:
                log.warning("%s has no per-player tick data; skipping", src.name)
                stats_failed += 1
                continue

            log.debug(
                "[%d/%d] %s — %s, %d rounds, %d players",
                idx,
                len(files),
                src.name,
                summary.demo_name,
                summary.round_count,
                len(aggregates),
            )

            for agg in aggregates:
                stats_seen += 1
                if agg.is_noise:
                    stats_skipped_noise += 1
                    continue

                pms = _build_player_match_stats(summary, agg)

                if args.commit and db_manager is not None:
                    if not args.force:
                        with db_manager.get_session() as session:
                            existing_quality = _existing_data_quality(
                                session, pms.demo_name, pms.player_name
                            )
                        if existing_quality == "complete":
                            stats_skipped_complete += 1
                            continue
                    db_manager.upsert(pms)

                stats_inserted += 1

        except Exception as exc:  # pragma: no cover — operational guardrail
            log.exception("Failed to process %s: %s", src.name, exc)
            stats_failed += 1

    elapsed = time.monotonic() - started
    log.info(
        "Done in %.1fs — files=%d, player-rows seen=%d, inserted=%d, "
        "skipped_complete=%d, skipped_noise=%d, failed=%d",
        elapsed,
        len(files),
        stats_seen,
        stats_inserted,
        stats_skipped_complete,
        stats_skipped_noise,
        stats_failed,
    )
    if not args.commit:
        log.info("Re-run with --commit to write these rows.")
    return 0 if stats_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
