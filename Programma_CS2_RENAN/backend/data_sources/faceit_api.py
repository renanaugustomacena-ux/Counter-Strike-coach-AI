import requests

from Programma_CS2_RENAN.core.config import get_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.faceit_api")


def fetch_faceit_data(nickname):
    """Fetches FaceIT Elo and Level for a given nickname."""
    api_key = get_setting("FACEIT_API_KEY")
    if not api_key or api_key == "YOUR_FACEIT_KEY":
        return {}

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        # Get Player ID by Nickname
        player_url = f"https://open.faceit.com/data/v4/players?nickname={nickname}&game=cs2"
        player_data = requests.get(player_url, headers=headers, timeout=10).json()

        player_id = player_data.get("player_id")
        if not player_id:
            return {}

        return {
            "faceit_id": player_id,
            "faceit_elo": player_data.get("games", {}).get("cs2", {}).get("faceit_elo", 0),
            "faceit_level": player_data.get("games", {}).get("cs2", {}).get("skill_level", 0),
        }
    except Exception as e:
        logger.error("Error fetching FaceIT data: %s", e)
        return {}
