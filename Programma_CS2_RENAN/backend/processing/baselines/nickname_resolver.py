"""
Nickname Resolver Logic

Resolves in-game player names from demos to official HLTV ProPlayer records.
Handles variations like 'Spirit donk', 's1mple-G2-', etc.

Task 2.18.2: Added Levenshtein-style fuzzy matching using SequenceMatcher
for improved nickname resolution when exact matches fail.
"""

import re
from difflib import SequenceMatcher
from typing import List, Optional

from sqlmodel import func, select

from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.nickname_resolver")


class NicknameResolver:
    """
    Utility to bridge the gap between Demo Physics and HLTV Stats.

    Task 2.18.2: Enhanced with Levenshtein-style fuzzy matching.
    Resolution priority:
        1. Exact match (case-insensitive)
        2. Substring match (e.g., 'Spirit donk' -> 'donk')
        3. Fuzzy match (SequenceMatcher with 0.8 threshold)
    """

    # Fuzzy matching threshold (0.0 = no match, 1.0 = identical)
    FUZZY_THRESHOLD = 0.8

    @staticmethod
    def find_pro_player_id(raw_name: str) -> Optional[int]:
        """
        Attempts to find an HLTV ID for a raw demo name.
        Uses exact match first, then substring, then fuzzy matching.

        Args:
            raw_name: Player name from demo (may include team tags, etc.)

        Returns:
            HLTV player ID if found, None otherwise
        """
        db = get_hltv_db_manager()
        clean_name = NicknameResolver._clean(raw_name)

        with db.get_session() as session:
            # 1. Exact Match (case-insensitive — SQLite default is case-sensitive)
            stmt = select(ProPlayer).where(func.lower(ProPlayer.nickname) == clean_name)
            p = session.exec(stmt).first()
            if p:
                return p.hltv_id

            # 2. Substring Match (e.g. "Spirit donk" -> "donk")
            # Fetch all pro players for advanced matching.
            # NOTE (F2-41): Substring + fuzzy lookup is O(n) per query and O(n²) for
            # batch processing N names. Acceptable for <1000 registered pros.
            # If the roster grows to thousands, replace with a trie-based prefix index.
            all_pros = session.exec(select(ProPlayer)).all()

            for pro in all_pros:
                if pro.nickname.lower() in clean_name.lower():
                    logger.debug("Resolved substring: %s -> %s", raw_name, pro.nickname)
                    return pro.hltv_id

            # 3. Fuzzy Match (Task 2.18.2: Levenshtein-style)
            nicknames = [pro.nickname for pro in all_pros]
            fuzzy_match = NicknameResolver._fuzzy_match(
                clean_name, nicknames, threshold=NicknameResolver.FUZZY_THRESHOLD
            )

            if fuzzy_match:
                # Find the ProPlayer with matching nickname
                for pro in all_pros:
                    if pro.nickname.lower() == fuzzy_match.lower():
                        logger.info("Resolved fuzzy: %s -> %s", raw_name, pro.nickname)
                        return pro.hltv_id

        return None

    @staticmethod
    def _fuzzy_match(query: str, candidates: List[str], threshold: float = 0.8) -> Optional[str]:
        """
        Find best match using Levenshtein-like similarity.

        Task 2.18.2: Uses difflib.SequenceMatcher which implements
        a ratio algorithm similar to Levenshtein distance.

        Args:
            query: The name to match
            candidates: List of known player nicknames
            threshold: Minimum similarity ratio (0.0-1.0)

        Returns:
            Best matching nickname if above threshold, None otherwise
        """
        best_match = None
        best_ratio = 0.0

        query_lower = query.lower()

        for candidate in candidates:
            # Calculate similarity ratio
            ratio = SequenceMatcher(None, query_lower, candidate.lower()).ratio()

            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = candidate

        if best_match:
            logger.debug(
                "Fuzzy match: '%s' -> '%s' (%s)", query, best_match, format(best_ratio, ".2f")
            )

        return best_match

    @staticmethod
    def _clean(name: str) -> str:
        """Removes clan tags and special characters."""
        # Remove common separators and non-alphanumeric
        cleaned = re.sub(r"[\[\]\(\)\-\._\s]", "", name)
        return cleaned.lower()
