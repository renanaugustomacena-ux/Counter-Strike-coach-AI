"""GAP-06 · Re-scrape HLTV placeholder pro stat cards.

Background
----------
24 ProPlayerStatCard rows in `hltv_metadata.db` carry the DEFAULT_STATS
sentinel (`pro_demo_miner._DEFAULT_STATS_SENTINEL`). They were written by
`tools/seed_hltv_top20.py` as fallback rows when HLTV scraping failed for
some GamerLegion / Tier-2 players. RAG mining now skips these (CHAT-06 fix
2026-04-19), but coaching coverage suffers as long as they remain in the
default state.

This tool reuses `HLTVStatFetcher.fetch_and_save_player(url)` to refresh
each placeholder card from the live HLTV stats page. The fetcher already
applies the 2–7 s `CRAWL_DELAY_*` jitter inside `_fetch_player_stats`, so
this script does not add its own throttle on top.

Usage
-----
    ./.venv/bin/python tools/rescrape_placeholder_pros.py              # dry-run
    ./.venv/bin/python tools/rescrape_placeholder_pros.py --apply      # live HLTV calls
    ./.venv/bin/python tools/rescrape_placeholder_pros.py --apply --limit 5

Safe-by-default
---------------
- `--dry-run` (default): list placeholders + the URLs that would be hit.
- `--apply`: live HLTV calls via FlareSolverr. Owner-authorized only —
  network egress + browser automation. Robots.txt preflight runs first.
- `--limit N`: cap the number of players hit in a single run (resume-friendly).
- Idempotent: re-scraping a player that's no longer default is a no-op
  beyond bandwidth (the upsert path overwrites in place).

Acceptance gate (per TASKS#38)
------------------------------
After a successful `--apply` run:
    ./.venv/bin/python tools/purge_default_stats_rag.py --dry-run
should report 0 default cards.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from Programma_CS2_RENAN.observability.logger_setup import get_logger  # noqa: E402

logger = get_logger("cs2analyzer.rescrape_placeholder_pros")

_HLTV_BASE = "https://www.hltv.org"


def _list_placeholders() -> List[Tuple[int, str]]:
    """Return [(hltv_id, nickname), ...] for every default-stats card.

    Reads from hltv_metadata.db via the canonical manager so we never touch
    the main DB. Reuses `_is_default_stats_card` so the predicate stays in
    one place (avoids drift if the sentinel ever changes).
    """
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.knowledge.pro_demo_miner import _is_default_stats_card
    from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard

    out: List[Tuple[int, str]] = []
    hltv = get_hltv_db_manager()
    with hltv.get_session() as session:
        cards = session.exec(select(ProPlayerStatCard)).all()
        for card in cards:
            if not _is_default_stats_card(card):
                continue
            player = session.exec(
                select(ProPlayer).where(ProPlayer.hltv_id == card.player_id)
            ).first()
            if player and player.nickname:
                out.append((int(card.player_id), player.nickname))
    out.sort(key=lambda x: x[1].lower())
    return out


def _build_url(hltv_id: int, nickname: str) -> str:
    """HLTV canonical stats URL: /stats/players/{id}/{nickname-lowercase}."""
    safe_nick = nickname.lower().strip()
    return f"{_HLTV_BASE}/stats/players/{hltv_id}/{safe_nick}"


def _refresh_one(fetcher, hltv_id: int, nickname: str) -> bool:
    """Wrap fetch_and_save_player with structured logging. Returns success."""
    url = _build_url(hltv_id, nickname)
    print(f"[rescrape] {nickname} (hltv_id={hltv_id}) -> {url}")
    try:
        ok = fetcher.fetch_and_save_player(url)
    except Exception as exc:
        logger.exception("rescrape failed for %s (%d)", nickname, hltv_id)
        print(f"[rescrape] FAIL {nickname}: {exc}")
        return False
    print(f"[rescrape] {'OK ' if ok else 'NO-DATA '} {nickname}")
    return bool(ok)


def _still_default(hltv_id: int) -> bool:
    """Re-read the card after rescrape to confirm sentinel cleared."""
    from sqlmodel import select

    from Programma_CS2_RENAN.backend.knowledge.pro_demo_miner import _is_default_stats_card
    from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
    from Programma_CS2_RENAN.backend.storage.db_models import ProPlayerStatCard

    hltv = get_hltv_db_manager()
    with hltv.get_session() as session:
        card = session.exec(
            select(ProPlayerStatCard).where(ProPlayerStatCard.player_id == hltv_id)
        ).first()
    if card is None:
        return False
    return _is_default_stats_card(card)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="GAP-06 HLTV placeholder rescrape")
    p.add_argument("--apply", action="store_true", help="live HLTV calls (default is dry-run)")
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="max players to hit this run (0 = no cap, resume-friendly)",
    )
    p.add_argument(
        "--skip-preflight",
        action="store_true",
        help="bypass robots.txt + scraping-enabled check (use only when verified)",
    )
    args = p.parse_args(argv)

    placeholders = _list_placeholders()
    print(f"[rescrape] Placeholder cards in HLTV DB: {len(placeholders)}")
    for hid, nick in placeholders:
        print(f"  - {nick} (hltv_id={hid}) -> {_build_url(hid, nick)}")

    if not placeholders:
        print("[rescrape] No placeholder cards — nothing to do (idempotent).")
        return 0

    if args.limit and args.limit > 0:
        placeholders = placeholders[: args.limit]
        print(f"[rescrape] --limit {args.limit} → will hit {len(placeholders)} this run")

    if not args.apply:
        print("\n[DRY-RUN] No HLTV calls made. Re-run with --apply to execute.")
        return 0

    # Live path — instantiate fetcher, run preflight, iterate.
    from Programma_CS2_RENAN.backend.data_sources.hltv.stat_fetcher import HLTVStatFetcher

    fetcher = HLTVStatFetcher()
    if not args.skip_preflight:
        if not fetcher.preflight_check():
            print("[rescrape] Preflight failed — robots.txt or settings disallow scraping.")
            return 2

    succ: List[str] = []
    fail: List[str] = []
    still_default: List[str] = []
    for hid, nick in placeholders:
        ok = _refresh_one(fetcher, hid, nick)
        if not ok:
            fail.append(nick)
            continue
        if _still_default(hid):
            print(f"[rescrape] WARN {nick} card still matches DEFAULT_STATS — investigate")
            still_default.append(nick)
        succ.append(nick)

    print(
        f"\n[rescrape] DONE — ok={len(succ)} fail={len(fail)} "
        f"still_default={len(still_default)} of {len(placeholders)}"
    )
    if fail:
        print(f"[rescrape] Failed: {fail}")
    if still_default:
        print(f"[rescrape] Still default after rescrape: {still_default}")

    return 0 if not fail and not still_default else 1


if __name__ == "__main__":
    sys.exit(main())
