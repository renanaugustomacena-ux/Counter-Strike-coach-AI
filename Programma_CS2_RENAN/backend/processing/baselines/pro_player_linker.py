"""
Pro Player Linker

Links PlayerMatchStats.pro_player_id to ProPlayer.hltv_id via NicknameResolver.
Supports both retroactive backfill (one-time) and per-ingestion linking.

The NicknameResolver handles exact, substring, and fuzzy matching against the
HLTV ProPlayer table. This module wraps it for batch operations and provides
the ingestion hook.
"""

from typing import Dict, List, Optional

from sqlmodel import select, update

from Programma_CS2_RENAN.backend.processing.baselines.nickname_resolver import (
    NicknameResolver,
)
from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.pro_player_linker")


class ProPlayerLinker:
    """Links PlayerMatchStats records to ProPlayer.hltv_id via NicknameResolver."""

    def link_player(self, player_name: str) -> Optional[int]:
        """Resolve a single player name to hltv_id.

        Args:
            player_name: In-game name from demo (e.g., "molodoy", "FalleN").

        Returns:
            HLTV player ID if resolved, None otherwise.
        """
        try:
            return NicknameResolver.find_pro_player_id(player_name)
        except Exception as exc:
            logger.warning("Failed to resolve '%s': %s", player_name, exc)
            return None

    def backfill_all(self) -> Dict:
        """Retroactive linkage of all is_pro=True records with pro_player_id=NULL.

        Idempotent: skips rows that already have a pro_player_id set.

        Returns:
            dict with keys: linked (int), unresolved (int), unresolved_names (list).
        """
        db = get_db_manager()
        linked = 0
        unresolved_names: List[str] = []

        # Step 1: Get distinct unlinked pro player names
        with db.get_session() as session:
            stmt = (
                select(PlayerMatchStats.player_name)
                .where(
                    PlayerMatchStats.is_pro == True,  # noqa: E712
                    PlayerMatchStats.pro_player_id.is_(None),
                )
                .distinct()
            )
            names = [row for row in session.exec(stmt).all()]

        if not names:
            logger.info("No unlinked pro players found — nothing to backfill")
            return {"linked": 0, "unresolved": 0, "unresolved_names": []}

        logger.info("Backfilling pro_player_id for %d unique names", len(names))

        # Step 2: Resolve each name via NicknameResolver
        name_to_id: Dict[str, int] = {}
        for name in names:
            hltv_id = self.link_player(name)
            if hltv_id is not None:
                name_to_id[name] = hltv_id
            else:
                unresolved_names.append(name)

        # Step 3: Batch update matched rows
        with db.get_session() as session:
            for name, hltv_id in name_to_id.items():
                result = session.exec(
                    update(PlayerMatchStats)
                    .where(
                        PlayerMatchStats.player_name == name,
                        PlayerMatchStats.is_pro == True,  # noqa: E712
                        PlayerMatchStats.pro_player_id.is_(None),
                    )
                    .values(pro_player_id=hltv_id)
                )
                count = result.rowcount  # type: ignore[union-attr]
                linked += count
                logger.info("Linked '%s' -> hltv_id=%d (%d rows)", name, hltv_id, count)

            session.commit()

        if unresolved_names:
            logger.warning(
                "Unresolved pro names (%d): %s", len(unresolved_names), unresolved_names
            )

        logger.info(
            "Backfill complete: linked=%d, unresolved=%d", linked, len(unresolved_names)
        )
        return {
            "linked": linked,
            "unresolved": len(unresolved_names),
            "unresolved_names": unresolved_names,
        }
