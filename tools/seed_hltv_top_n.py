#!/usr/bin/env python3
"""seed_hltv_top_n.py — Seed/refresh hltv_metadata.db with top-N HLTV teams.

SCOPE: This tool ONLY touches `hltv_metadata.db` (the HLTV-feature database).
It does NOT touch `database.db` (the main monolith / demo-derived DB). The two
are independent — see `~/.claude/projects/.../memory/feedback_hltv_db_is_separate.md`.

What it does:
    1. Fetch HLTV /ranking/teams page → parse top-N currently-ranked teams.
    2. For each team, fetch the team page → roster of active player IDs.
    3. For each player not yet in `proplayer` (or whose `proplayerstatcard.last_updated`
       is older than --refresh-days), fetch their stats card via FlareSolverr.
    4. Write to `proplayer`, `proplayerstatcard`, `proteam` (HLTV DB only).
    5. Players that fail FlareSolverr after --max-retries are written to
       `reports/hltv_seed_<ts>/pending_vision.json` for a later vision-LLM pass
       (handled separately by `tools/seed_hltv_apply_vision.py` or by an
       interactive Claude Code session that can drive puppeteer-mcp natively).

Idempotent + resumable:
    - Re-runs skip players whose stat card is fresh per --refresh-days.
    - Per-player failures don't abort the run; they go to the pending queue.
    - Each invocation writes a fresh report under reports/hltv_seed_<ts>/.

Usage:
    ./.venv/bin/python tools/seed_hltv_top_n.py --top 25 --dry-run
    ./.venv/bin/python tools/seed_hltv_top_n.py --top 25 --apply
    ./.venv/bin/python tools/seed_hltv_top_n.py --top 25 --apply --refresh-days 7
    ./.venv/bin/python tools/seed_hltv_top_n.py --top 25 --apply --max-retries 3

Owner-authorized only: makes ~25 + ~125 live HLTV calls (one per team-page +
~5 players/team × 2-3 stat subpages each). Throttled by the FlareSolverr-side
2-7 sec random delay (stat_fetcher.CRAWL_DELAY_*). Total wall-time: ~1-4 hours.

Doctrine §111/§112/§115/§116/§117/§121 applied:
    - §111 consumer-question: HLTV-feature consumer (analytics screen,
      pro_baseline merger). Required freshness: weekly cadence.
    - §112 simplest design: reuse existing FlareSolverrClient + HLTVStatFetcher.
    - §115 idempotent: last_updated cache + UPSERT semantics.
    - §116 debuggable: per-step report.json + per-player log lines.
    - §117 quality: validates parsed roster (5-7 players per team) +
      validates fetched stat card (rating > 0).
    - §121 backfill-friendly: rerun replays the queue without duplicates.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sqlmodel import select  # noqa: E402

from Programma_CS2_RENAN.backend.data_sources.hltv.flaresolverr_client import (  # noqa: E402
    FlareSolverrClient,
)
from Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher import (  # noqa: E402
    _HLTV_BASE_URL,
    HLTVStatFetcher,
)
from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager  # noqa: E402
from Programma_CS2_RENAN.backend.storage.db_models import (  # noqa: E402
    ProPlayer,
    ProPlayerStatCard,
    ProTeam,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger  # noqa: E402

logger = get_logger("cs2analyzer.seed_hltv_top_n")


# ──────────────────────────────────────────────────────────────────────────────
# Data shapes
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class TeamRecord:
    hltv_id: int
    name: str
    rank: int


@dataclass
class PlayerRecord:
    hltv_id: int
    nickname: str
    team_id: int
    team_name: str


@dataclass
class SeedReport:
    started_at: str
    finished_at: Optional[str] = None
    top_n: int = 0
    refresh_days: int = 7
    apply: bool = False
    teams_discovered: List[dict] = field(default_factory=list)
    players_discovered: List[dict] = field(default_factory=list)
    teams_added_or_updated: List[int] = field(default_factory=list)
    players_added: List[int] = field(default_factory=list)
    players_updated: List[int] = field(default_factory=list)
    players_skipped_fresh: List[int] = field(default_factory=list)
    players_failed: List[dict] = field(default_factory=list)
    pending_vision: List[dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Discovery — top-N teams
# ──────────────────────────────────────────────────────────────────────────────


def _parse_ranking_page(html: str) -> List[TeamRecord]:
    """Parse /ranking/teams HTML, return ranked teams in order."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    teams: List[TeamRecord] = []

    # HLTV ranking page uses .ranked-team divs. Each has .position and
    # .relative-team-name + a link to /team/{id}/{name}.
    blocks = soup.select(".ranked-team") or soup.select("div.ranked-team")
    if not blocks:
        # Fallback selector: any anchor pointing to /team/<id>/
        anchors = soup.select('a[href^="/team/"]')
        for idx, a in enumerate(anchors, 1):
            href = a.get("href", "")
            parts = href.strip("/").split("/")
            if len(parts) >= 3 and parts[0] == "team" and parts[1].isdigit():
                tid = int(parts[1])
                name = parts[2] if len(parts) > 2 else "unknown"
                teams.append(TeamRecord(hltv_id=tid, name=name, rank=idx))
        return teams

    for idx, block in enumerate(blocks, 1):
        # Position
        pos_el = block.select_one(".position")
        rank = idx
        if pos_el:
            try:
                rank = int(pos_el.get_text(strip=True).lstrip("#"))
            except ValueError:
                pass
        # Team link
        link = block.select_one('a[href^="/team/"]')
        if link is None:
            continue
        href = link.get("href", "")
        parts = href.strip("/").split("/")
        if len(parts) < 2 or parts[0] != "team" or not parts[1].isdigit():
            continue
        tid = int(parts[1])
        name = parts[2] if len(parts) > 2 else link.get_text(strip=True)
        teams.append(TeamRecord(hltv_id=tid, name=name, rank=rank))
    return teams


def discover_top_teams(fs: FlareSolverrClient, top_n: int) -> List[TeamRecord]:
    url = f"{_HLTV_BASE_URL}/ranking/teams"
    logger.info("Fetching ranking page: %s", url)
    html = fs.get(url)
    if not html:
        raise RuntimeError("FlareSolverr returned no body for /ranking/teams")
    teams = _parse_ranking_page(html)
    if not teams:
        raise RuntimeError(
            "Parsed 0 teams from /ranking/teams — selector drift; "
            "inspect HTML and update _parse_ranking_page selectors"
        )
    teams = teams[:top_n]
    logger.info("Discovered %d teams (top %d)", len(teams), top_n)
    return teams


# ──────────────────────────────────────────────────────────────────────────────
# Roster fetch per team
# ──────────────────────────────────────────────────────────────────────────────


def _parse_team_roster(html: str, team: TeamRecord) -> List[PlayerRecord]:
    """Parse a /team/{id}/{name} page, return ONLY the 5 active starters.

    HLTV team pages contain many `/player/...` anchors (active roster, bench,
    coach, analyst, historical lineup, opponent links from match boxes). The
    unfiltered scan returned ~36 players/team. Verified 2026-04-29 against
    /team/9565/vitality: `.bodyshot-team` is the active-roster section and
    contains exactly 5 anchors. We narrow to that section. If absent (older
    layouts), fall back to the unfiltered scan capped at 7 (CS2 active-roster
    ceiling — extremely rare 6-7 transitional configs).
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    players: List[PlayerRecord] = []
    seen_ids: set = set()

    roster_section = soup.select_one(".bodyshot-team")
    anchors = roster_section.select('a[href^="/player/"]') if roster_section else []

    if not anchors:
        logger.warning(
            "No .bodyshot-team for team %d (%s) — fallback to capped unfiltered scan",
            team.hltv_id,
            team.name,
        )
        anchors = soup.select('a[href^="/player/"]')[:7]

    for a in anchors:
        href = a.get("href", "")
        parts = href.strip("/").split("/")
        if len(parts) < 3 or parts[0] != "player" or not parts[1].isdigit():
            continue
        pid = int(parts[1])
        if pid in seen_ids:
            continue
        seen_ids.add(pid)
        nick = parts[2]
        players.append(
            PlayerRecord(hltv_id=pid, nickname=nick, team_id=team.hltv_id, team_name=team.name)
        )

    if len(players) < 5:
        logger.warning(
            "Team %d (%s) parsed only %d active players (expected 5-7) — verify layout",
            team.hltv_id,
            team.name,
            len(players),
        )
    elif len(players) > 7:
        logger.warning(
            "Team %d (%s) parsed %d players (>7) — selector leaked beyond active roster",
            team.hltv_id,
            team.name,
            len(players),
        )
    return players


def fetch_team_roster(fs: FlareSolverrClient, team: TeamRecord) -> List[PlayerRecord]:
    url = f"{_HLTV_BASE_URL}/team/{team.hltv_id}/{team.name}"
    logger.info("Fetching team roster: %s", url)
    html = fs.get(url)
    if not html:
        logger.warning("FlareSolverr returned no body for team %d (%s)", team.hltv_id, team.name)
        return []
    roster = _parse_team_roster(html, team)
    if not roster:
        logger.warning(
            "Parsed 0 players for team %d (%s) — selector drift", team.hltv_id, team.name
        )
    return roster


# ──────────────────────────────────────────────────────────────────────────────
# DB upsert helpers (HLTV DB ONLY — never touches main DB)
# ──────────────────────────────────────────────────────────────────────────────


def _upsert_team(team: TeamRecord) -> bool:
    """Insert or update a ProTeam row. Returns True on insert/update."""
    db = get_hltv_db_manager()
    with db.get_session() as s:
        existing = s.exec(select(ProTeam).where(ProTeam.hltv_id == team.hltv_id)).first()
        if existing is None:
            s.add(
                ProTeam(
                    hltv_id=team.hltv_id,
                    name=team.name,
                    last_updated=datetime.now(timezone.utc),
                )
            )
            s.commit()
            logger.info("Inserted team %d (%s)", team.hltv_id, team.name)
            return True
        if existing.name != team.name:
            existing.name = team.name
            existing.last_updated = datetime.now(timezone.utc)
            s.add(existing)
            s.commit()
            logger.info("Updated team %d (%s)", team.hltv_id, team.name)
            return True
        return False


def _is_player_fresh(player_id: int, threshold_seconds: int) -> bool:
    """True if proplayerstatcard for this player_id has last_updated within threshold."""
    db = get_hltv_db_manager()
    with db.get_session() as s:
        card = s.exec(
            select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == player_id)
        ).first()
    if card is None:
        return False
    if card.last_updated is None:
        return False
    age = (datetime.now(timezone.utc) - _aware(card.last_updated)).total_seconds()
    return age < threshold_seconds


def _aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC fallback)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _is_default_stats_card_player_id(player_id: int) -> bool:
    """Re-use the project's canonical default-stats sentinel check."""
    from Programma_CS2_RENAN.backend.knowledge.pro_demo_miner import _is_default_stats_card

    db = get_hltv_db_manager()
    with db.get_session() as s:
        card = s.exec(
            select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == player_id)
        ).first()
    return card is not None and _is_default_stats_card(card)


def _backfill_player_team(player_hltv_id: int, team_id: int) -> None:
    """Set ProPlayer.team_id if currently NULL or different.

    fetch_and_save_player upserts ProPlayer from the HLTV stats page
    which does not expose the team relationship. We know the team from
    the discovery step, so we backfill it here. Idempotent: no-op if
    team_id already matches.
    """
    db = get_hltv_db_manager()
    with db.get_session() as s:
        player = s.exec(select(ProPlayer).where(ProPlayer.hltv_id == player_hltv_id)).first()
        if player is None:
            logger.warning(
                "Cannot backfill team_id for hltv_id=%d — ProPlayer row missing",
                player_hltv_id,
            )
            return
        if player.team_id == team_id:
            return
        player.team_id = team_id
        player.last_updated = datetime.now(timezone.utc)
        s.add(player)
        s.commit()
        logger.info("Backfilled team_id=%d on ProPlayer hltv_id=%d", team_id, player_hltv_id)


# ──────────────────────────────────────────────────────────────────────────────
# Per-player fetch with retry + pending-queue fallback
# ──────────────────────────────────────────────────────────────────────────────


def fetch_player_with_retry(
    fetcher: HLTVStatFetcher,
    player: PlayerRecord,
    max_retries: int,
) -> str:
    """Returns one of: 'added', 'updated', 'failed'.

    'added' / 'updated' when fetch_and_save_player returned True. We don't
    distinguish between insert/update at this layer — fetch_and_save_player
    upserts internally. Caller decides label from pre-existence.
    """
    url = f"{_HLTV_BASE_URL}/stats/players/{player.hltv_id}/{player.nickname.lower()}"
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            ok = fetcher.fetch_and_save_player(url)
        except Exception as exc:  # noqa: BLE001 — outermost retry boundary
            ok = False
            last_err = exc
            logger.warning(
                "fetch %s attempt %d/%d raised: %r",
                player.nickname,
                attempt,
                max_retries,
                exc,
            )
        if ok:
            return "ok"
        # Backoff between retries (in addition to in-fetcher 2-7s throttle)
        if attempt < max_retries:
            time.sleep(min(15, 5 * attempt))
    if last_err is not None:
        logger.error("fetch %s exhausted %d retries: %r", player.nickname, max_retries, last_err)
    else:
        logger.error("fetch %s exhausted %d retries (returned False)", player.nickname, max_retries)
    return "failed"


# ──────────────────────────────────────────────────────────────────────────────
# Main run loop
# ──────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_seed(args: argparse.Namespace) -> int:
    refresh_seconds = args.refresh_days * 86400
    report = SeedReport(
        started_at=datetime.now(timezone.utc).isoformat(),
        top_n=args.top,
        refresh_days=args.refresh_days,
        apply=args.apply,
    )

    out_dir = _REPO_ROOT / "reports" / f"hltv_seed_{_now_iso()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    fs = FlareSolverrClient()
    fetcher = HLTVStatFetcher()

    if args.apply and not args.skip_preflight:
        if not fetcher.preflight_check():
            logger.error("Preflight failed (robots.txt or settings disallow scraping). Abort.")
            report.notes.append("aborted_preflight")
            _write_report(out_dir, report)
            return 2

    # Step 1: discover top-N teams
    try:
        teams = discover_top_teams(fs, args.top)
    except Exception as exc:  # noqa: BLE001 — abort: we have nothing to seed
        logger.error("Top-N discovery failed: %r", exc)
        report.notes.append(f"discovery_failed: {exc!r}")
        _write_report(out_dir, report)
        return 3
    report.teams_discovered = [asdict(t) for t in teams]

    # Step 2: per-team roster fetch
    all_players: List[PlayerRecord] = []
    for team in teams:
        if args.apply:
            _upsert_team(team)
            report.teams_added_or_updated.append(team.hltv_id)
        roster = fetch_team_roster(fs, team)
        report.players_discovered.extend([asdict(p) for p in roster])
        all_players.extend(roster)

    logger.info(
        "Discovery complete: %d teams, %d player slots (may include duplicates across teams)",
        len(teams),
        len(all_players),
    )

    # Deduplicate players by hltv_id (rare cross-team duplicates from transfer windows)
    seen_pids = set()
    unique_players: List[PlayerRecord] = []
    for p in all_players:
        if p.hltv_id in seen_pids:
            continue
        seen_pids.add(p.hltv_id)
        unique_players.append(p)
    logger.info("Unique players to consider: %d", len(unique_players))

    if args.dry_run or not args.apply:
        report.notes.append("dry_run_only_no_db_writes")
        report.finished_at = datetime.now(timezone.utc).isoformat()
        _write_report(out_dir, report)
        logger.info("DRY RUN complete. Report at %s", out_dir / "seed_report.json")
        return 0

    # Step 3: fetch each player's stats with retry, queue failures for vision pass
    for i, player in enumerate(unique_players, 1):
        # Fresh-cache short-circuit
        is_default = _is_default_stats_card_player_id(player.hltv_id)
        if not is_default and _is_player_fresh(player.hltv_id, refresh_seconds):
            logger.info(
                "[%d/%d] SKIP (fresh): %s (hltv_id=%d)",
                i,
                len(unique_players),
                player.nickname,
                player.hltv_id,
            )
            report.players_skipped_fresh.append(player.hltv_id)
            continue

        # Track if it was an insert vs update for the report
        had_card = is_default or _has_card(player.hltv_id)

        logger.info(
            "[%d/%d] FETCH: %s (hltv_id=%d, team=%s)",
            i,
            len(unique_players),
            player.nickname,
            player.hltv_id,
            player.team_name,
        )
        result = fetch_player_with_retry(fetcher, player, max_retries=args.max_retries)
        if result == "ok":
            # Backfill team_id on the ProPlayer row. fetch_and_save_player
            # populates from the stats page, which doesn't expose team_id
            # — but we know it from the discovery step. Without this the
            # player ends up team_id=NULL and is unrouteable from the
            # pro-baseline merger that joins on team. (Surfaced 2026-04-29
            # when jL/19206 landed at mouz with team_id=NULL.)
            _backfill_player_team(player.hltv_id, player.team_id)
            if had_card:
                report.players_updated.append(player.hltv_id)
            else:
                report.players_added.append(player.hltv_id)
        else:
            url = f"{_HLTV_BASE_URL}/stats/players/{player.hltv_id}/{player.nickname.lower()}"
            entry = {
                "hltv_id": player.hltv_id,
                "nickname": player.nickname,
                "team_id": player.team_id,
                "team_name": player.team_name,
                "url": url,
            }
            report.players_failed.append(entry)
            report.pending_vision.append(entry)
            logger.warning(
                "Queued for vision-LLM fallback: %s (hltv_id=%d)",
                player.nickname,
                player.hltv_id,
            )

    report.finished_at = datetime.now(timezone.utc).isoformat()
    _write_report(out_dir, report)

    # Also write the pending_vision queue as a standalone file (consumed by
    # the Phase-2 vision pass — see seed_hltv_apply_vision.py companion or
    # an interactive Claude Code session driving puppeteer-mcp).
    pending_path = out_dir / "pending_vision.json"
    pending_path.write_text(json.dumps(report.pending_vision, indent=2), encoding="utf-8")

    logger.info(
        "Seed run complete. teams=%d added=%d updated=%d skipped_fresh=%d failed=%d pending_vision=%d",
        len(teams),
        len(report.players_added),
        len(report.players_updated),
        len(report.players_skipped_fresh),
        len(report.players_failed),
        len(report.pending_vision),
    )
    logger.info("Report: %s", out_dir / "seed_report.json")
    if report.pending_vision:
        logger.info(
            "Vision-fallback queue (%d players): %s",
            len(report.pending_vision),
            pending_path,
        )
    return 0


def _has_card(player_id: int) -> bool:
    db = get_hltv_db_manager()
    with db.get_session() as s:
        return (
            s.exec(
                select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == player_id)
            ).first()
            is not None
        )


def _write_report(out_dir: Path, report: SeedReport) -> None:
    payload = asdict(report)
    out = out_dir / "seed_report.json"
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, out)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--top",
        type=int,
        default=25,
        help="Number of top teams to seed (default 25).",
    )
    parser.add_argument(
        "--refresh-days",
        type=int,
        default=7,
        help="Skip players whose proplayerstatcard.last_updated is younger than this. "
        "Default-stats sentinel cards are always re-fetched regardless. (default 7)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="FlareSolverr retries per player before queuing for vision fallback (default 3).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover teams + roster, print report, write nothing to DB.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write to DB. Required for actual seeding.",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip robots.txt + scraping-enabled preflight (use only when verified).",
    )
    args = parser.parse_args(argv)

    if not args.dry_run and not args.apply:
        parser.error("Pass either --dry-run or --apply.")
    if args.dry_run and args.apply:
        parser.error("Pass either --dry-run or --apply, not both.")

    return run_seed(args)


if __name__ == "__main__":
    sys.exit(main())
