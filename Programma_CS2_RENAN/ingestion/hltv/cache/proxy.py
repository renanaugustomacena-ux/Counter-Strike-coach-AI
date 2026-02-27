"""
HLTV Caching Proxy

Intercepts HLTV requests to serve cached HTML content, reducing external load
and preventing IP bans. Uses SQLite for persistent storage with TTL.
"""

import datetime
import os
import sqlite3
from typing import Optional, Tuple

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.hltv_cache")


class HLTVCachingProxy:
    """
    Manages caching of HLTV player profiles.

    Database: data/hltv_cache.db
    Table: hltv_player_cache
    TTL: 7 days (default)
    """

    DB_PATH = os.path.join(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        ),
        "data",
        "hltv_cache.db",
    )

    def __init__(self, ttl_days: int = 7):
        self.ttl = datetime.timedelta(days=ttl_days)
        self._init_db()

    def _init_db(self):
        """Initialize the cache database schema."""
        os.makedirs(os.path.dirname(self.DB_PATH), exist_ok=True)
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hltv_player_cache (
                        player_id INTEGER PRIMARY KEY,
                        html_content TEXT,
                        last_updated TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                """
                )
                conn.commit()
        except Exception as e:
            logger.error("Failed to initialize HLTV cache DB: %s", e)

    def get_player_html(self, player_id: int) -> Optional[str]:
        """
        Retrieve cached HTML for a player ID if valid.

        Returns:
            HTML string if found and not expired, else None.
        """
        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                cursor = conn.execute(
                    "SELECT html_content, expires_at FROM hltv_player_cache WHERE player_id = ?",
                    (player_id,),
                )
                row = cursor.fetchone()

                if not row:
                    return None

                html, expires_at_str = row

                # Check expiration
                expires_at = datetime.datetime.fromisoformat(expires_at_str)
                if datetime.datetime.now() > expires_at:
                    logger.info("Cache expired for Player %s", player_id)
                    return None

                logger.debug("Cache HIT for Player %s", player_id)
                return html

        except Exception as e:
            logger.error("Cache lookup failed for %s: %s", player_id, e)
            return None

    def save_player_html(self, player_id: int, html: str):
        """Save HTML content to cache with new TTL."""
        now = datetime.datetime.now()
        expires_at = now + self.ttl

        try:
            with sqlite3.connect(self.DB_PATH) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO hltv_player_cache
                    (player_id, html_content, last_updated, expires_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (player_id, html, now.isoformat(), expires_at.isoformat()),
                )
                conn.commit()
            logger.debug("Cached Player %s (expires %s)", player_id, expires_at)

        except Exception as e:
            logger.error("Failed to cache Player %s: %s", player_id, e)


# Singleton instance
_proxy_instance = None


def get_proxy() -> HLTVCachingProxy:
    global _proxy_instance
    if not _proxy_instance:
        _proxy_instance = HLTVCachingProxy()
    return _proxy_instance
