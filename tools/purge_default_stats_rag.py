"""One-shot cleanup — remove pro_baseline / opening_duels RAG entries that
were generated from DEFAULT_STATS placeholder stat cards.

Why: `tools/seed_hltv_top20.py:1266 DEFAULT_STATS` is a placeholder row the
seed script writes when HLTV scrape returned no per-player data. Running
`pro_demo_miner.mine_all_pro_stats()` before the fix in `pro_demo_miner.py`
embedded these fallback numbers into `knowledgeentry` rows — RAG retrieval
then returned 24 different pros with byte-identical stats.

This script is idempotent. Run once after pulling the CHAT-06 fix:
    python tools/purge_default_stats_rag.py [--dry-run]

Tracked: TASKS#34, AUDIT §8.6.
"""

from __future__ import annotations

import argparse
import sys

from sqlmodel import select

from Programma_CS2_RENAN.backend.knowledge.pro_demo_miner import _is_default_stats_card
from Programma_CS2_RENAN.backend.storage.database import get_db_manager, get_hltv_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import (
    ProPlayer,
    ProPlayerStatCard,
    TacticalKnowledge,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.purge_default_stats")


def _collect_default_stats_nicknames() -> list[str]:
    """Return the list of nicknames whose stat card matches DEFAULT_STATS."""
    hltv_db = get_hltv_db_manager()
    nicknames: list[str] = []
    with hltv_db.get_session() as session:
        cards = session.exec(select(ProPlayerStatCard)).all()
        for card in cards:
            if not _is_default_stats_card(card):
                continue
            player = session.exec(
                select(ProPlayer).where(ProPlayer.hltv_id == card.player_id)
            ).first()
            if player and player.nickname:
                nicknames.append(player.nickname)
    return nicknames


def _find_polluted_knowledge(nicknames: list[str]) -> list[tuple[int, str, str]]:
    """Return (id, title, category) of knowledgeentry rows that mention one
    of the default-stats nicknames via the title-prefix conventions used by
    pro_demo_miner (`Pro baseline: {nick}`, `Opening duels: {nick}`).
    """
    db = get_db_manager()
    hits: list[tuple[int, str, str]] = []
    prefixes: list[str] = []
    for nick in nicknames:
        prefixes.append(f"Pro baseline: {nick} ")
        prefixes.append(f"Pro baseline: {nick}(")  # edge case w/o space
        prefixes.append(f"Opening duels: {nick}")
    with db.get_session() as session:
        entries = session.exec(select(TacticalKnowledge)).all()
        for entry in entries:
            title = entry.title or ""
            for prefix in prefixes:
                if title.startswith(prefix):
                    hits.append((entry.id, title, entry.category))
                    break
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be purged without deleting.",
    )
    args = parser.parse_args()

    nicknames = _collect_default_stats_nicknames()
    print(f"Found {len(nicknames)} players with DEFAULT_STATS placeholder cards:")
    for nick in sorted(nicknames):
        print(f"  - {nick}")

    if not nicknames:
        print("Nothing to purge.")
        return 0

    hits = _find_polluted_knowledge(nicknames)
    print(f"\nPolluted knowledgeentry rows: {len(hits)}")
    for entry_id, title, category in hits[:20]:
        print(f"  - id={entry_id} category={category} title={title!r}")
    if len(hits) > 20:
        print(f"  ... and {len(hits) - 20} more")

    if args.dry_run:
        print("\n--dry-run — no changes written.")
        return 0

    if not hits:
        print("No knowledge rows matched — DB already clean.")
        return 0

    db = get_db_manager()
    with db.get_session() as session:
        for entry_id, _title, _cat in hits:
            entry = session.get(TacticalKnowledge, entry_id)
            if entry is not None:
                session.delete(entry)
        session.commit()

    print(f"\nDeleted {len(hits)} polluted knowledgeentry rows.")
    logger.info("DEFAULT_STATS RAG purge complete: %s rows removed", len(hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
