"""
HLTV Match Orchestrator

Automatically discovers and downloads recent pro CS2 matches from HLTV.org.
Implements incremental sync to avoid duplicate downloads.

Adheres to GEMINI.md principles:
- Explicit state management (HLTVDownload tracking)
- Fail-fast validation
- Rate limiting and politeness
"""

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from playwright.sync_api import sync_playwright
from sqlmodel import select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
from Programma_CS2_RENAN.backend.storage.db_models import HLTVDownload, IngestionTask
from Programma_CS2_RENAN.ingestion.downloader import download_single_match
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.hltv_orchestrator")


class HLTVOrchestrator:
    """
    Orchestrates HLTV match discovery and download.

    Features:
    - Scrapes HLTV results page
    - Filters CS2 matches
    - Tracks downloaded matches
    - Rate limits requests
    """

    HLTV_RESULTS_URL = "https://www.hltv.org/results"
    REQUEST_DELAY = 3  # seconds between requests

    def __init__(self):
        init_database()
        self.db = get_db_manager()

    def run_sync_cycle(self, limit: int = 20):
        """
        Main orchestration function.

        Args:
            limit: Number of recent matches to check
        """
        logger.info("Starting HLTV sync cycle (limit=%s)", limit)

        try:
            # Discover recent matches
            matches = self.fetch_recent_matches(limit=limit)
            logger.info("Found %s recent matches", len(matches))

            # Filter CS2 only
            cs2_matches = self.filter_cs2_matches(matches)
            logger.info("Filtered to %s CS2 matches", len(cs2_matches))

            # Download new matches
            downloaded_count = 0
            for match in cs2_matches:
                if self.download_match_if_new(match):
                    downloaded_count += 1
                time.sleep(self.REQUEST_DELAY)  # Rate limiting

            logger.info("HLTV sync complete: %s new matches downloaded", downloaded_count)

        except Exception as e:
            logger.error("HLTV sync failed: %s", e)

    def fetch_recent_matches(self, limit: int = 20) -> List[Dict]:
        """
        Scrape HLTV results page for recent matches.

        Returns:
            List of match dictionaries with keys:
            - match_id: Unique identifier
            - match_url: Full HLTV URL
            - teams: "Team1 vs Team2"
            - event: Tournament name
            - date: Match date
        """
        matches = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36"
                )
                page = context.new_page()

                logger.info("Fetching %s", self.HLTV_RESULTS_URL)
                page.goto(self.HLTV_RESULTS_URL, wait_until="domcontentloaded")
                page.wait_for_selector(".result-con", timeout=30000)

                # Extract match data
                result_elements = page.locator(".result-con").all()[:limit]

                for elem in result_elements:
                    try:
                        # Extract match URL
                        link = elem.locator("a.a-reset").first
                        match_url = "https://www.hltv.org" + link.get_attribute("href")

                        # Extract teams
                        team1 = elem.locator(".team1").inner_text().strip()
                        team2 = elem.locator(".team2").inner_text().strip()
                        teams = f"{team1} vs {team2}"

                        # Extract event
                        event_elem = elem.locator(".event-name")
                        event = (
                            event_elem.inner_text().strip() if event_elem.count() > 0 else "Unknown"
                        )

                        # Generate match ID from URL
                        match_id = match_url.split("/")[-2] if "/" in match_url else match_url

                        matches.append(
                            {
                                "match_id": match_id,
                                "match_url": match_url,
                                "teams": teams,
                                "event": event,
                                "date": datetime.utcnow().isoformat(),
                            }
                        )

                    except Exception as e:
                        logger.warning("Failed to parse match element: %s", e)
                        continue

                browser.close()

        except Exception as e:
            logger.error("Failed to fetch HLTV matches: %s", e)

        return matches

    def filter_cs2_matches(self, matches: List[Dict]) -> List[Dict]:
        """
        Filter matches to CS2 only.

        Note: HLTV doesn't provide explicit CS2/CSGO tags on results page.
        This filter relies on the fact that HLTV results page only shows
        recent matches, and CS2 released Sept 27, 2023. Any match from
        the results page scraped after CS2 release is assumed to be CS2.

        LIMITATION: If this code runs before Sept 2023, it will fail.
        If run after, assumes all recent matches are CS2 (CSGO no longer competitive).
        """
        cs2_release_date = datetime(2023, 9, 27)
        current_date = datetime.utcnow()

        # Safety check: if running before CS2 release, cannot reliably filter
        if current_date < cs2_release_date:
            logger.error(
                "Cannot filter CS2 matches - current date %s is before CS2 release %s",
                current_date,
                cs2_release_date,
            )
            raise ValueError("HLTV orchestrator cannot distinguish CS2/CSGO before Sept 2023")

        # Since we're past CS2 release and HLTV results page only shows recent matches,
        # all matches on the results page are CS2 (CSGO competitive scene ended)
        logger.info(
            "CS2 filter: Assuming all %s recent matches are CS2 (post-release scraping)",
            len(matches),
        )

        # Future enhancement: parse individual match pages to check game version explicitly
        return matches

    def download_match_if_new(self, match: Dict) -> bool:
        """
        Download match if not already in database.

        Args:
            match: Match dictionary from fetch_recent_matches()

        Returns:
            True if downloaded, False if skipped
        """
        match_id = match["match_id"]

        # Check if already downloaded
        with self.db.get_session() as session:
            existing = session.exec(
                select(HLTVDownload).where(HLTVDownload.match_id == match_id)
            ).first()

            if existing:
                logger.info("Skipping %s: already downloaded", match_id)
                return False

        # Download match
        try:
            logger.info("Downloading %s: %s", match_id, match["teams"])
            result = download_single_match(match["match_url"], match_id)

            # Track download
            with self.db.get_session() as session:
                download_record = HLTVDownload(
                    match_id=match_id,
                    match_url=match["match_url"],
                    teams=match["teams"],
                    event=match["event"],
                    demo_count=len(result.get("maps", [])),
                )
                session.add(download_record)
                session.commit()

            logger.info("Downloaded %s: %s demos", match_id, len(result.get("maps", [])))
            return True

        except Exception as e:
            logger.error("Failed to download %s: %s", match_id, e)
            return False


def run_hltv_sync_cycle(limit: int = 20):
    """
    Convenience function for HLTV sync.

    Args:
        limit: Number of recent matches to check
    """
    orchestrator = HLTVOrchestrator()
    orchestrator.run_sync_cycle(limit=limit)


if __name__ == "__main__":
    # Self-test
    logger.info("=== HLTV Orchestrator Test ===")
    run_hltv_sync_cycle(limit=5)
