import json
import time

import httpx

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.telemetry")

# This would be configured to the Developer's IP address
# e.g., "http://203.0.113.45:8000" if port forwarded, or an ngrok URL
DEV_SERVER_URL = "http://127.0.0.1:8000"


def send_match_telemetry(player_id: str, match_id: str, stats: dict):
    """
    Sends match statistics to the central ML Coach server.
    """
    payload = {
        "player_id": player_id,
        "match_id": match_id,
        "stats": stats,
        "timestamp": time.time(),
    }

    try:
        logger.info("[*] Sending telemetry to %s...", DEV_SERVER_URL)
        with httpx.Client() as client:
            response = client.post(
                f"{DEV_SERVER_URL}/api/ingest/telemetry", json=payload, timeout=10.0
            )

        if response.status_code == 200:
            logger.info("[+] Data successfully sent to the Coach.")
            return True
        else:
            logger.error("[-] Failed to send data: %s - %s", response.status_code, response.text)
            return False

    except Exception as e:
        logger.error("[!] Connection error: %s", e)
        logger.error("    (Ensure the Developer's Server is running and accessible)")
        return False


if __name__ == "__main__":
    # Test sending dummy data
    dummy_stats = {"kills": 24, "deaths": 12, "headshot_pct": 45.5, "map": "de_mirage"}
    send_match_telemetry("User_Test_001", "match_display_123", dummy_stats)
