"""
HLTV Statistics Sync Cycle

Fetches PRO PLAYER STATISTICS from HLTV.org (Rating, K/D, ADR, etc.).
This is NOT related to demo downloads - only statistics sync for the pro baseline.
"""

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.hltv")


def run_hltv_sync_cycle(limit=20):
    """
    Run HLTV statistics sync cycle using HLTVApiService.

    Fetches pro player statistics (Rating 2.0, K/D, ADR, KAST, etc.) from HLTV.org
    to populate the pro baseline for coach comparisons.

    Args:
        limit: Number of player IDs to sync (default: 20)
    """
    try:
        from Programma_CS2_RENAN.ingestion.hltv.hltv_api_service import HLTVApiService

        logger.info("Starting HLTV Statistics Sync (limit=%s)", limit)
        service = HLTVApiService(headless=True)

        # Sync a range of top player IDs for pro baseline
        # IDs correspond to HLTV player profiles
        start_id = 1
        end_id = start_id + limit
        synced = service.sync_range(start_id, end_id)

        logger.info("HLTV Statistics Sync completed: %s players synced", synced)
        return synced

    except ImportError as e:
        logger.error("Failed to import HLTVApiService: %s", e)
        logger.error(
            "Ensure Playwright is installed: pip install playwright && playwright install chromium"
        )
        return 0
    except Exception as e:
        logger.error("HLTV Statistics Sync failed: %s", e)
        return 0
