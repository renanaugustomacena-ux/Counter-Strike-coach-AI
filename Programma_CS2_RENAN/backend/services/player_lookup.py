"""
Player Lookup Service

Detects player name mentions in chat messages and retrieves structured
factual data from the HLTV and monolith databases. Returns verified
player profiles that the LLM can reference without hallucinating.

Integration Points:
    - nickname_resolver.py: Fuzzy name matching against HLTV ProPlayer table
    - coaching_dialogue.py: Injects VERIFIED PLAYER DATA blocks into chat context
    - database.py: Cross-database lookups (hltv_metadata.db + database.db)
"""

import re
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sqlmodel import func, select

from Programma_CS2_RENAN.backend.storage.database import get_db_manager, get_hltv_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import (
    PlayerMatchStats,
    ProPlayer,
    ProPlayerStatCard,
    ProTeam,
)
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.player_lookup")

# Words that should never be treated as player name candidates
_STOP_WORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "shall",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "about",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "some",
        "no",
        "how",
        "what",
        "who",
        "which",
        "when",
        "where",
        "why",
        "that",
        "this",
        "these",
        "those",
        "i",
        "me",
        "my",
        "we",
        "you",
        "your",
        "he",
        "she",
        "it",
        "they",
        "them",
        "his",
        "her",
        "its",
        "our",
        "their",
        # CS2 domain words that aren't player names
        "player",
        "pro",
        "team",
        "coach",
        "stats",
        "stat",
        "rating",
        "compare",
        "tell",
        "show",
        "give",
        "like",
        "play",
        "game",
        "match",
        "round",
        "kill",
        "death",
        "map",
        "side",
        "ct",
        "terrorist",
        "smoke",
        "flash",
        "molotov",
        "grenade",
        "weapon",
        "rifle",
        "awp",
        "ak",
        "m4",
        "pistol",
        "knife",
        "bomb",
        "site",
        "push",
        "hold",
        "peek",
        "aim",
        "spray",
        "headshot",
        "clutch",
        "ace",
        "entry",
        "support",
        "lurk",
        "info",
        "improve",
        "better",
        "best",
        "worst",
        "good",
        "bad",
        "high",
        "low",
    }
)

# Fuzzy matching threshold for chat queries (slightly lower than NicknameResolver's 0.8)
_CHAT_FUZZY_THRESHOLD = 0.75


@dataclass
class ProPlayerProfile:
    """Structured factual profile assembled from HLTV + demo databases."""

    nickname: str
    hltv_id: int
    real_name: Optional[str] = None
    country: Optional[str] = None
    team_name: Optional[str] = None
    team_world_rank: Optional[int] = None
    # HLTV stats
    rating_2_0: float = 0.0
    kpr: float = 0.0
    dpr: float = 0.0
    adr: float = 0.0
    kast: float = 0.0
    headshot_pct: float = 0.0
    impact: float = 0.0
    opening_duel_win_pct: float = 0.0
    maps_played: int = 0
    # Demo performance (from monolith DB)
    demo_matches: int = 0
    demo_avg_rating: Optional[float] = None
    demo_avg_adr: Optional[float] = None


class PlayerLookupService:
    """Detects player mentions in chat and retrieves verified profiles."""

    _CACHE_TTL = 60.0  # seconds

    def __init__(self):
        self._nickname_cache: List[str] = []
        self._nickname_set_lower: set = set()
        self._cache_loaded_at: float = 0.0

    def _ensure_cache(self):
        """Load/refresh the nickname cache from HLTV DB."""
        if (
            self._nickname_cache
            and (time.monotonic() - self._cache_loaded_at) < self._CACHE_TTL
        ):
            return

        try:
            hltv_db = get_hltv_db_manager()
            with hltv_db.get_session() as session:
                players = session.exec(select(ProPlayer.nickname)).all()
                self._nickname_cache = [n for n in players if n]
                self._nickname_set_lower = {n.lower() for n in self._nickname_cache}
                self._cache_loaded_at = time.monotonic()
                logger.debug("Refreshed nickname cache: %d players", len(self._nickname_cache))
        except Exception as exc:
            logger.warning("Failed to refresh nickname cache: %s", exc)

    def detect_player_mentions(self, message: str) -> List[str]:
        """Extract player names mentioned in a chat message.

        Uses exact match against cached HLTV nicknames, then falls back
        to fuzzy matching for close variants.

        Args:
            message: User chat message (e.g., "tell me about molodoy").

        Returns:
            List of matched player nicknames (empty if none found).
        """
        self._ensure_cache()
        if not self._nickname_cache:
            return []

        # Tokenize: extract word-like tokens from the message
        tokens = re.findall(r"[a-zA-Z0-9_]+", message)
        if not tokens:
            return []

        found: List[str] = []
        found_lower: set = set()

        # Pass 1: Exact match (case-insensitive) against nickname cache
        for token in tokens:
            token_lower = token.lower()
            if token_lower in _STOP_WORDS:
                continue
            if len(token_lower) < 2:
                continue
            if token_lower in self._nickname_set_lower and token_lower not in found_lower:
                # Find the canonical-case nickname
                for nick in self._nickname_cache:
                    if nick.lower() == token_lower:
                        found.append(nick)
                        found_lower.add(token_lower)
                        break

        # Pass 2: 2-word ngrams (for names like "FALLEN" appearing as "FalleN")
        # Already covered by pass 1 since we match individual tokens.

        # Pass 3: Fuzzy match for remaining tokens (only if no exact matches found)
        if not found:
            from difflib import SequenceMatcher

            for token in tokens:
                token_lower = token.lower()
                if token_lower in _STOP_WORDS or len(token_lower) < 3:
                    continue

                best_match = None
                best_ratio = 0.0
                for nick in self._nickname_cache:
                    ratio = SequenceMatcher(None, token_lower, nick.lower()).ratio()
                    if ratio > best_ratio and ratio >= _CHAT_FUZZY_THRESHOLD:
                        best_ratio = ratio
                        best_match = nick

                if best_match and best_match.lower() not in found_lower:
                    found.append(best_match)
                    found_lower.add(best_match.lower())
                    logger.debug(
                        "Fuzzy-matched '%s' -> '%s' (%.2f)", token, best_match, best_ratio
                    )

        return found

    def lookup_player(self, name: str) -> Optional[ProPlayerProfile]:
        """Full DB lookup for a player: HLTV identity + stats + demo performance.

        Queries hltv_metadata.db for ProPlayer/ProTeam/ProPlayerStatCard,
        then database.db for PlayerMatchStats.

        Args:
            name: Player nickname (as matched by detect_player_mentions).

        Returns:
            ProPlayerProfile if found, None otherwise.
        """
        # Step 1: Find ProPlayer in HLTV DB
        try:
            from Programma_CS2_RENAN.backend.processing.baselines.nickname_resolver import (
                NicknameResolver,
            )

            hltv_id = NicknameResolver.find_pro_player_id(name)
            if hltv_id is None:
                logger.debug("No HLTV match for '%s'", name)
                return None
        except Exception as exc:
            logger.warning("NicknameResolver failed for '%s': %s", name, exc)
            return None

        # Step 2: Fetch identity + team from HLTV DB
        profile = ProPlayerProfile(nickname=name, hltv_id=hltv_id)

        try:
            hltv_db = get_hltv_db_manager()
            with hltv_db.get_session() as session:
                player = session.exec(
                    select(ProPlayer).where(ProPlayer.hltv_id == hltv_id)
                ).first()

                if player:
                    profile.nickname = player.nickname
                    profile.real_name = player.real_name
                    profile.country = player.country

                    if player.team_id:
                        team = session.exec(
                            select(ProTeam).where(ProTeam.hltv_id == player.team_id)
                        ).first()
                        if team:
                            profile.team_name = team.name
                            profile.team_world_rank = team.world_rank

                # Fetch stat card
                stat_card = session.exec(
                    select(ProPlayerStatCard)
                    .where(ProPlayerStatCard.player_id == hltv_id)
                    .order_by(ProPlayerStatCard.last_updated.desc())
                    .limit(1)
                ).first()

                if stat_card:
                    profile.rating_2_0 = stat_card.rating_2_0
                    profile.kpr = stat_card.kpr
                    profile.dpr = stat_card.dpr
                    profile.adr = stat_card.adr
                    profile.kast = stat_card.kast
                    profile.headshot_pct = stat_card.headshot_pct
                    profile.impact = stat_card.impact
                    profile.opening_duel_win_pct = stat_card.opening_duel_win_pct
                    profile.maps_played = stat_card.maps_played
        except Exception as exc:
            logger.warning("HLTV lookup failed for hltv_id=%d: %s", hltv_id, exc)

        # Step 3: Fetch demo performance from monolith DB
        try:
            db = get_db_manager()
            with db.get_session() as session:
                demo_stats = session.exec(
                    select(PlayerMatchStats).where(
                        PlayerMatchStats.pro_player_id == hltv_id
                    )
                ).all()

                if demo_stats:
                    profile.demo_matches = len(demo_stats)
                    ratings = [s.rating for s in demo_stats if s.rating > 0]
                    adrs = [s.avg_adr for s in demo_stats if s.avg_adr > 0]
                    if ratings:
                        profile.demo_avg_rating = sum(ratings) / len(ratings)
                    if adrs:
                        profile.demo_avg_adr = sum(adrs) / len(adrs)
        except Exception as exc:
            logger.warning("Demo stats lookup failed for hltv_id=%d: %s", hltv_id, exc)

        return profile

    def format_player_context(self, profile: ProPlayerProfile) -> str:
        """Format a ProPlayerProfile as a structured text block for LLM injection.

        The block is clearly delimited so the system prompt's anti-hallucination
        rules can reference it by name ("VERIFIED PLAYER DATA").

        Args:
            profile: Assembled player profile from lookup_player().

        Returns:
            Formatted text block with all available facts.
        """
        lines = ["=== VERIFIED PLAYER DATA (use ONLY this data, do not guess) ==="]
        lines.append(f"Player: {profile.nickname}")

        if profile.real_name:
            lines.append(f"Real Name: {profile.real_name}")
        if profile.country:
            lines.append(f"Country: {profile.country}")

        team_str = profile.team_name or "Unknown"
        if profile.team_world_rank:
            team_str += f" (World Rank #{profile.team_world_rank})"
        lines.append(f"Team: {team_str}")

        # Format KAST/HS% consistently (ratio vs percentage)
        kast_pct = profile.kast * 100 if profile.kast <= 1.0 else profile.kast
        hs_pct = (
            profile.headshot_pct * 100 if profile.headshot_pct <= 1.0 else profile.headshot_pct
        )

        lines.append(
            f"HLTV Stats: Rating 2.0: {profile.rating_2_0:.2f} | "
            f"KPR: {profile.kpr:.2f} | DPR: {profile.dpr:.2f} | "
            f"ADR: {profile.adr:.1f}"
        )
        lines.append(
            f"KAST: {kast_pct:.1f}% | HS%: {hs_pct:.1f}% | "
            f"Impact: {profile.impact:.2f} | "
            f"Opening Duel Win: {profile.opening_duel_win_pct:.1f}%"
        )
        lines.append(f"Maps Played: {profile.maps_played}")

        if profile.demo_matches > 0:
            demo_parts = [f"Demo Performance: {profile.demo_matches} matches analyzed"]
            if profile.demo_avg_rating is not None:
                demo_parts.append(f"avg rating {profile.demo_avg_rating:.2f}")
            if profile.demo_avg_adr is not None:
                demo_parts.append(f"avg ADR {profile.demo_avg_adr:.1f}")
            lines.append(", ".join(demo_parts))

        lines.append("=== END VERIFIED DATA ===")
        return "\n".join(lines)
