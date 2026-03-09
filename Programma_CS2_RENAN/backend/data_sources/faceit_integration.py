"""
FACEIT API Integration Module

Downloads match history and demo files from FACEIT platform.
Implements rate limiting and error handling per GEMINI.md backend principles.

API Documentation: https://developers.faceit.com/docs/
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.faceit")


class FACEITAPIError(Exception):
    """Raised when FACEIT API request fails."""

    pass


class FACEITIntegration:
    """
    FACEIT API client with rate limiting.

    Rate Limits:
    - 10 requests per minute (free tier)
    - Exponential backoff on 429 responses
    """

    BASE_URL = "https://open.faceit.com/data/v4"
    RATE_LIMIT_DELAY = 6  # seconds (10 req/min = 1 req per 6s)

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FACEIT client.

        Args:
            api_key: FACEIT API key (defaults to config)
        """
        self.api_key = api_key or get_setting("FACEIT_API_KEY", "")
        if not self.api_key:
            raise FACEITAPIError("FACEIT API key not configured")

        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        )

        self.last_request_time = 0

    def _rate_limited_request(
        self, endpoint: str, params: dict = None, _retry_count: int = 0
    ) -> dict:
        """
        Make rate-limited API request.

        Args:
            endpoint: API endpoint (e.g., "/players/{player_id}")
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            FACEITAPIError: On API error
        """
        # Enforce rate limit
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=10)
            self.last_request_time = time.time()

            if response.status_code == 429:
                MAX_429_RETRIES = 3
                if _retry_count >= MAX_429_RETRIES:
                    raise FACEITAPIError(
                        f"Rate limit exceeded {MAX_429_RETRIES} times for {endpoint}"
                    )
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(
                    "Rate limit exceeded (attempt %d/%d). Waiting %ds",
                    _retry_count + 1,
                    MAX_429_RETRIES,
                    retry_after,
                )
                time.sleep(retry_after)
                return self._rate_limited_request(endpoint, params, _retry_count=_retry_count + 1)

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            raise FACEITAPIError(f"API request failed: {e}")

    def get_player_id(self, nickname: str) -> Optional[str]:
        """
        Get FACEIT player ID from nickname.

        Args:
            nickname: FACEIT username

        Returns:
            Player ID, or None if not found
        """
        try:
            data = self._rate_limited_request("/players", params={"nickname": nickname})
            return data.get("player_id")
        except FACEITAPIError as e:
            logger.error("Failed to get player ID for %s: %s", nickname, e)
            return None

    def fetch_match_history(self, player_id: str, game: str = "cs2", limit: int = 20) -> List[Dict]:
        """
        Fetch player's recent match history.

        Args:
            player_id: FACEIT player ID
            game: Game ID ("cs2" or "csgo")
            limit: Number of matches to fetch (max 100)

        Returns:
            List of match dictionaries
        """
        try:
            data = self._rate_limited_request(
                f"/players/{player_id}/history", params={"game": game, "limit": min(limit, 100)}
            )
            return data.get("items", [])
        except FACEITAPIError as e:
            logger.error("Failed to fetch match history: %s", e)
            return []

    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """
        Get detailed match information.

        Args:
            match_id: FACEIT match ID

        Returns:
            Match details dictionary, or None if not found
        """
        try:
            return self._rate_limited_request(f"/matches/{match_id}")
        except FACEITAPIError as e:
            logger.error("Failed to get match details for %s: %s", match_id, e)
            return None

    def download_demo(self, match_id: str, output_dir: Path) -> Optional[Path]:
        """
        Download demo file for match.

        Note: FACEIT does not always provide demo downloads.
        This method attempts to find demo URL from match details.

        Args:
            match_id: FACEIT match ID
            output_dir: Directory to save demo file

        Returns:
            Path to downloaded demo, or None if unavailable
        """
        match_details = self.get_match_details(match_id)
        if not match_details:
            return None

        # FACEIT demo URLs are in match details under "demo_url"
        demo_url = match_details.get("demo_url")
        if not demo_url:
            logger.info("No demo available for match %s", match_id)
            return None

        # R3-09: Sanitize match_id to prevent directory traversal
        safe_id = str(match_id).replace("/", "").replace("\\", "").replace("..", "")
        if safe_id != str(match_id):
            logger.warning("Rejected suspicious match_id: %s", match_id)
            return None

        # Download demo file
        output_path = output_dir / f"faceit_{safe_id}.dem"

        try:
            response = requests.get(demo_url, stream=True, timeout=30)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info("Downloaded demo: %s", output_path)
            return output_path

        except requests.RequestException as e:
            logger.error("Failed to download demo: %s", e)
            return None


def sync_faceit_matches(nickname: str, output_dir: Path, limit: int = 20) -> List[Dict]:
    """
    Convenience function to sync FACEIT matches.

    Args:
        nickname: FACEIT username
        output_dir: Directory to save demos
        limit: Number of matches to fetch

    Returns:
        List of match metadata with download status
    """
    client = FACEITIntegration()

    # Get player ID
    player_id = client.get_player_id(nickname)
    if not player_id:
        logger.error("Player not found: %s", nickname)
        return []

    # Fetch match history
    matches = client.fetch_match_history(player_id, limit=limit)

    results = []
    for match in matches:
        match_id = match.get("match_id")
        match_info = {
            "match_id": match_id,
            "started_at": match.get("started_at"),
            "finished_at": match.get("finished_at"),
            "demo_downloaded": False,
            "demo_path": None,
        }

        # Attempt demo download
        demo_path = client.download_demo(match_id, output_dir)
        if demo_path:
            match_info["demo_downloaded"] = True
            match_info["demo_path"] = str(demo_path)

        results.append(match_info)

    return results


if __name__ == "__main__":
    # Self-test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python faceit_integration.py <faceit_nickname>")
        sys.exit(1)

    nickname = sys.argv[1]
    output_dir = Path("./faceit_demos")
    output_dir.mkdir(exist_ok=True)

    print(f"=== FACEIT Match Sync: {nickname} ===\n")

    results = sync_faceit_matches(nickname, output_dir, limit=5)

    print(f"Found {len(results)} matches:\n")
    for match in results:
        print(f"  Match ID: {match['match_id']}")
        print(f"  Started: {match['started_at']}")
        print(f"  Demo: {'✓' if match['demo_downloaded'] else '✗'}")
        if match["demo_path"]:
            print(f"  Path: {match['demo_path']}")
        print()
