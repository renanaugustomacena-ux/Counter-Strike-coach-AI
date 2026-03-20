from datetime import datetime, timedelta, timezone

from sqlmodel import delete, select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats, PlayerTickState
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.maintenance")


def prune_old_metadata(days_threshold: int = 30):
    """
    Implementation of Pillar 2 - Phase 2 (70%): Metadata Pruning.
    Removes high-fidelity tick data for old matches while preserving aggregate stats.
    """
    db = get_db_manager()
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

    logger.info("Starting metadata pruning (Threshold: %s days)...", days_threshold)

    try:
        with db.get_session() as session:
            # 1. Identify demo names of matches older than the threshold
            stmt = select(PlayerMatchStats.demo_name).where(
                PlayerMatchStats.processed_at < cutoff_date
            )
            old_demo_names = session.exec(stmt).all()

            if not old_demo_names:
                logger.info("No old metadata found to prune.")
                return

            # 2. Delete PlayerTickState records linked to these demos (by demo_name, not PK).
            # Batched in chunks of 500 to stay under SQLite's SQLITE_MAX_VARIABLE_NUMBER (999).
            _CHUNK_SIZE = 500
            ticks_removed = 0
            demo_list = list(old_demo_names)
            for i in range(0, len(demo_list), _CHUNK_SIZE):
                chunk = demo_list[i : i + _CHUNK_SIZE]
                delete_stmt = delete(PlayerTickState).where(PlayerTickState.demo_name.in_(chunk))
                result = session.execute(delete_stmt)
                ticks_removed += result.rowcount

            logger.info("Pruning complete. Removed %s non-essential tick records.", ticks_removed)
            session.commit()

    except Exception as e:
        logger.error("Metadata pruning failed: %s", e)
