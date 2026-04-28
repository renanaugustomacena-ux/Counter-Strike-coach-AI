#!/usr/bin/env python3
"""seed_hltv_apply_vision.py — Phase 2 vision-fallback writer for HLTV seeding.

SCOPE: Touches `hltv_metadata.db` only. Never writes to `database.db`.

Phase-2 companion to `seed_hltv_top_n.py`. The Phase-1 tool emits a
`reports/hltv_seed_<ts>/pending_vision.json` file with players that
FlareSolverr could not scrape after `--max-retries` attempts. This script
takes a single player's structured stats (extracted out-of-band via a
vision-capable LLM driving puppeteer-mcp screenshots) and writes the
ProPlayer + ProPlayerStatCard rows.

Two execution modes:

1. Single-player CLI (one-shot apply):
       ./.venv/bin/python tools/seed_hltv_apply_vision.py \\
           --player-id 12345 --nickname alex --team-id 9999 --team-name "team_x" \\
           --stats-json '{"rating_2_0": 1.07, "dpr": 0.65, ...}'

2. Batch mode from a JSON file produced by an external process:
       ./.venv/bin/python tools/seed_hltv_apply_vision.py \\
           --batch reports/hltv_seed_<ts>/vision_extracted.json

   Where vision_extracted.json is a list of:
       [{"player_id": ..., "nickname": ..., "team_id": ..., "team_name": ...,
         "stats": {"rating_2_0": ..., ...}}, ...]

The driver responsible for screenshotting + vision extraction is NOT this
script. The intended flow:

    1. seed_hltv_top_n.py (FlareSolverr) writes pending_vision.json
    2. An interactive Claude Code session drives puppeteer-mcp:
         - puppeteer_navigate(url)
         - puppeteer_screenshot()
         - reads the screenshot natively via multimodal vision
         - extracts stats into structured dict
         - invokes this script with --player-id + --stats-json
    3. This script validates + writes to hltv_metadata.db

Schema validated in --stats-json:
    Required (all 8 default-sentinel fields):
        rating_2_0, dpr, kast, impact, adr, kpr, headshot_pct, maps_played
    Optional:
        opening_kill_ratio, opening_duel_win_pct, clutch_win_count,
        multikill_round_pct, time_span, detailed_stats_json

§115 idempotent: re-running with the same player overwrites in place.
§117 quality-gated: rejects rating_2_0 == 0 OR all-zero defaults
    (would re-create a placeholder card).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sqlmodel import select  # noqa: E402

from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager  # noqa: E402
from Programma_CS2_RENAN.backend.storage.db_models import (  # noqa: E402
    ProPlayer,
    ProPlayerStatCard,
    ProTeam,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger  # noqa: E402

logger = get_logger("cs2analyzer.seed_hltv_apply_vision")


# Required fields in the stats dict.
REQUIRED_FIELDS = (
    "rating_2_0",
    "dpr",
    "kast",
    "impact",
    "adr",
    "kpr",
    "headshot_pct",
    "maps_played",
)

# Optional fields with their defaults (matching ProPlayerStatCard NOT NULL columns).
OPTIONAL_FIELDS_WITH_DEFAULTS: Dict[str, Any] = {
    "opening_kill_ratio": 0.0,
    "opening_duel_win_pct": 0.0,
    "clutch_win_count": 0,
    "multikill_round_pct": 0.0,
    "detailed_stats_json": "{}",
    "time_span": "all-time",
}


def _validate_stats(stats: Dict[str, Any]) -> None:
    """Raise ValueError if stats dict is missing required fields or all-zero."""
    missing = [f for f in REQUIRED_FIELDS if f not in stats]
    if missing:
        raise ValueError(f"stats missing required fields: {missing}")

    # Reject all-zero (would just re-write the default sentinel)
    numeric_required = ("rating_2_0", "dpr", "kast", "impact", "adr", "kpr", "headshot_pct")
    if (
        all(float(stats.get(k, 0)) == 0.0 for k in numeric_required)
        and int(stats.get("maps_played", 0)) == 0
    ):
        raise ValueError("all-zero stats — would recreate the default sentinel; rejecting")

    # Sanity ranges (warn, don't raise — pro stats are highly variable)
    rating = float(stats["rating_2_0"])
    if rating < 0.3 or rating > 2.0:
        logger.warning("rating_2_0 outside plausible pro range [0.3, 2.0]: %.3f", rating)
    kast = float(stats["kast"])
    if kast > 1.0 and kast <= 100.0:
        # KAST sometimes scraped as percent, normalize to ratio
        stats["kast"] = kast / 100.0
        logger.info("normalized KAST from percent (%.1f) to ratio (%.3f)", kast, kast / 100.0)
    elif kast < 0 or kast > 1.0:
        logger.warning("kast outside plausible [0, 1] range: %.3f", kast)


def _ensure_team(team_id: int, team_name: str) -> None:
    """Idempotent ProTeam upsert."""
    db = get_hltv_db_manager()
    with db.get_session() as s:
        existing = s.exec(select(ProTeam).where(ProTeam.hltv_id == team_id)).first()
        if existing is None:
            s.add(ProTeam(hltv_id=team_id, name=team_name, last_updated=datetime.now(timezone.utc)))
            s.commit()
            logger.info("Inserted ProTeam hltv_id=%d (%s)", team_id, team_name)
        elif existing.name != team_name:
            existing.name = team_name
            existing.last_updated = datetime.now(timezone.utc)
            s.add(existing)
            s.commit()
            logger.info("Updated ProTeam hltv_id=%d name → %s", team_id, team_name)


def _upsert_player_and_card(
    player_id: int, nickname: str, team_id: int, stats: Dict[str, Any]
) -> str:
    """Returns one of: 'inserted', 'updated', 'no-op'."""
    db = get_hltv_db_manager()
    now = datetime.now(timezone.utc)

    with db.get_session() as s:
        # Player row
        player = s.exec(select(ProPlayer).where(ProPlayer.hltv_id == player_id)).first()
        if player is None:
            player = ProPlayer(
                hltv_id=player_id,
                nickname=nickname,
                team_id=team_id,
                last_updated=now,
            )
            s.add(player)
            s.commit()
            s.refresh(player)
            player_action = "inserted"
        else:
            changed = False
            if player.nickname != nickname:
                player.nickname = nickname
                changed = True
            if player.team_id != team_id:
                player.team_id = team_id
                changed = True
            if changed:
                player.last_updated = now
                s.add(player)
                s.commit()
                s.refresh(player)
                player_action = "updated"
            else:
                player_action = "no-op"

        # Stat card
        card = s.exec(
            select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == player_id)
        ).first()
        kwargs = {
            "player_id": player_id,
            "rating_2_0": float(stats["rating_2_0"]),
            "dpr": float(stats["dpr"]),
            "kast": float(stats["kast"]),
            "impact": float(stats["impact"]),
            "adr": float(stats["adr"]),
            "kpr": float(stats["kpr"]),
            "headshot_pct": float(stats["headshot_pct"]),
            "maps_played": int(stats["maps_played"]),
            "last_updated": now,
        }
        for key, default in OPTIONAL_FIELDS_WITH_DEFAULTS.items():
            kwargs[key] = stats.get(key, default)
        if isinstance(kwargs["detailed_stats_json"], dict):
            kwargs["detailed_stats_json"] = json.dumps(kwargs["detailed_stats_json"])

        if card is None:
            s.add(ProPlayerStatCard(**kwargs))
            s.commit()
            return "inserted" if player_action != "no-op" else "card_inserted"

        for k, v in kwargs.items():
            setattr(card, k, v)
        s.add(card)
        s.commit()
        return "updated"


def apply_one(
    player_id: int,
    nickname: str,
    team_id: int,
    team_name: str,
    stats: Dict[str, Any],
) -> str:
    _validate_stats(stats)
    _ensure_team(team_id, team_name)
    result = _upsert_player_and_card(player_id, nickname, team_id, stats)
    logger.info(
        "Applied vision-extracted stats for %s (hltv_id=%d): %s",
        nickname,
        player_id,
        result,
    )
    return result


def apply_batch(batch_path: Path) -> int:
    """Read a JSON list of {player_id, nickname, team_id, team_name, stats} entries
    and apply each. Returns 0 on full success, 1 if any entry failed."""
    if not batch_path.is_file():
        logger.error("Batch file not found: %s", batch_path)
        return 2
    payload = json.loads(batch_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        logger.error("Batch file must contain a JSON array")
        return 2
    failures = 0
    for idx, entry in enumerate(payload, 1):
        try:
            apply_one(
                player_id=int(entry["player_id"]),
                nickname=str(entry["nickname"]),
                team_id=int(entry["team_id"]),
                team_name=str(entry["team_name"]),
                stats=entry["stats"],
            )
        except Exception as exc:  # noqa: BLE001 — boundary: log + continue with next
            failures += 1
            logger.error(
                "[%d/%d] Failed for player_id=%s: %r",
                idx,
                len(payload),
                entry.get("player_id"),
                exc,
            )
    return 0 if failures == 0 else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="mode", required=False)

    # Allow flat arguments (no subcommand) for convenience
    parser.add_argument("--player-id", type=int)
    parser.add_argument("--nickname", type=str)
    parser.add_argument("--team-id", type=int)
    parser.add_argument("--team-name", type=str)
    parser.add_argument("--stats-json", type=str, help="JSON dict of stats (use single quotes)")
    parser.add_argument("--stats-file", type=Path, help="Path to a JSON file with stats dict")
    parser.add_argument(
        "--batch",
        type=Path,
        help="Path to a JSON list of {player_id, nickname, team_id, team_name, stats}",
    )

    args = parser.parse_args(argv)

    if args.batch:
        return apply_batch(args.batch)

    # Single-player path
    required = ("player_id", "nickname", "team_id", "team_name")
    missing = [r for r in required if getattr(args, r) is None]
    if missing:
        parser.error(
            f"Single-player mode requires: {', '.join('--' + m.replace('_', '-') for m in missing)}"
        )

    if args.stats_json and args.stats_file:
        parser.error("Pass exactly one of --stats-json or --stats-file")
    if not args.stats_json and not args.stats_file:
        parser.error("Pass either --stats-json or --stats-file")

    if args.stats_json:
        stats = json.loads(args.stats_json)
    else:
        stats = json.loads(args.stats_file.read_text(encoding="utf-8"))

    try:
        apply_one(
            player_id=args.player_id,
            nickname=args.nickname,
            team_id=args.team_id,
            team_name=args.team_name,
            stats=stats,
        )
    except Exception as exc:  # noqa: BLE001 — top-level CLI boundary
        logger.error("apply_one failed: %r", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
