"""
Pro Player Knowledge Mining Pipeline

Extracts tactical knowledge from professional player statistics (ProPlayerStatCard).
Generates knowledge entries for the RAG coaching knowledge base based on real
HLTV-sourced player data.

Pipeline:
    1. Read pro player stat cards from hltv_metadata.db
    2. Identify standout performance patterns
    3. Generate knowledge entries (archetypes, baselines, traits)
    4. Add to RAG knowledge base
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import select

from Programma_CS2_RENAN.backend.knowledge.rag_knowledge import KnowledgePopulator
from Programma_CS2_RENAN.backend.storage.database import get_hltv_db_manager
from Programma_CS2_RENAN.backend.storage.db_models import ProPlayer, ProPlayerStatCard, ProTeam
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.pro_demo_miner")

# Archetype classification thresholds
_STAR_FRAGGER_IMPACT = 1.15
_SNIPER_HS_THRESHOLD = 0.35
_SUPPORT_KAST_THRESHOLD = 0.72
_ENTRY_OPENING_THRESHOLD = 0.52

_KNOWN_MAPS = {"mirage", "dust2", "inferno", "nuke", "overpass", "ancient", "anubis", "vertigo"}

# Minimum rounds on a (map, side) combination for map-specific knowledge
_MIN_MAP_ROUNDS = 10


class ProStatsMiner:
    """
    Extract tactical knowledge from professional player statistics.

    Uses real HLTV-sourced data in ProPlayerStatCard to generate
    coaching knowledge about pro playstyles, baselines, and archetypes.
    """

    def __init__(self):
        self.db = get_hltv_db_manager()
        self.populator = KnowledgePopulator()

    def mine_all_pro_stats(self, limit: int = 50) -> int:
        """
        Mine knowledge from all pro player stat cards.

        Args:
            limit: Maximum number of players to process

        Returns:
            Number of knowledge entries created
        """
        logger.info("Starting pro stats mining (limit=%s)", limit)

        with self.db.get_session() as session:
            stat_cards = session.exec(
                select(ProPlayerStatCard)
                .order_by(ProPlayerStatCard.last_updated.desc())
                .limit(limit)
            ).all()

            if not stat_cards:
                logger.warning("No pro stat cards found to mine")
                return 0

            total_knowledge = 0

            for card in stat_cards:
                player = session.exec(
                    select(ProPlayer).where(ProPlayer.hltv_id == card.player_id)
                ).first()
                nickname = player.nickname if player else f"Player_{card.player_id}"

                # Fetch team + identity metadata for richer knowledge entries
                team_name = None
                country = player.country if player else None
                real_name = player.real_name if player else None
                if player and player.team_id:
                    team = session.exec(
                        select(ProTeam).where(ProTeam.hltv_id == player.team_id)
                    ).first()
                    if team:
                        team_name = team.name

                try:
                    entries = self._generate_player_knowledge(
                        card, nickname, team_name, country, real_name
                    )
                    for entry in entries:
                        try:
                            self.populator.add_knowledge(**entry)
                        except Exception as e:
                            logger.error("Failed to add knowledge for %s: %s", nickname, e)
                    total_knowledge += len(entries)
                    logger.info("Mined %s entries for %s", len(entries), nickname)
                except Exception as e:
                    logger.error("Failed to mine stats for %s: %s", nickname, e)

        logger.info("Total knowledge mined: %s entries", total_knowledge)
        return total_knowledge

    def _generate_player_knowledge(
        self,
        card: ProPlayerStatCard,
        nickname: str,
        team_name: Optional[str] = None,
        country: Optional[str] = None,
        real_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate knowledge entries from a player's stat card."""
        knowledge = []

        archetype = self._classify_archetype(card)

        # Build identity prefix with available metadata
        identity_parts = [nickname]
        if real_name:
            identity_parts.append(f"({real_name})")
        if country:
            identity_parts.append(f"— {country}")
        if team_name:
            identity_parts.append(f"— Team: {team_name}")
        identity = " ".join(identity_parts)

        # Baseline knowledge entry
        knowledge.append(
            {
                "title": f"Pro baseline: {nickname} ({archetype})",
                "description": (
                    f"{identity} — Rating 2.0: {card.rating_2_0:.2f}, "
                    f"KPR: {card.kpr:.2f}, DPR: {card.dpr:.2f}, "
                    f"ADR: {card.adr:.1f}, "
                    # C-3 FIX: Use 1.0 as discriminator (unambiguous boundary).
                    # Ratio values are in [0,1]; percentage values are in [0,100].
                    # The old boundary of 1.5 was in a dead zone — no real KAST falls
                    # between 1.0 (max ratio) and ~30 (min plausible percentage).
                    f"KAST: {(card.kast * 100 if card.kast <= 1.0 else card.kast):.1f}%, "
                    f"HS: {(card.headshot_pct * 100 if card.headshot_pct <= 1.0 else card.headshot_pct):.1f}%, "
                    f"Impact: {card.impact:.2f}. "
                    f"Maps played: {card.maps_played}. "
                    f"Time span: {card.time_span}."
                ),
                "category": "pro_baseline",
                "situation": f"Pro player reference — {archetype}",
                "map_name": None,
                "pro_example": f"{nickname} (HLTV stats)",
            }
        )

        # Opening duels entry (if data available)
        if card.opening_kill_ratio > 0 or card.opening_duel_win_pct > 0:
            knowledge.append(
                {
                    "title": f"Opening duels: {nickname}",
                    "description": (
                        f"{nickname} opening kill ratio: {card.opening_kill_ratio:.2f}, "
                        f"opening duel win rate: {card.opening_duel_win_pct:.1f}%. "
                        f"{'Aggressive entry fragger.' if card.opening_duel_win_pct > 52 else 'Disciplined opener.'}"
                    ),
                    "category": "opening_duels",
                    "situation": "Entry fragging reference",
                    "map_name": None,
                    "pro_example": f"{nickname} (HLTV stats)",
                }
            )

        # Clutch/multikill entry (if data available)
        if card.clutch_win_count > 0 or card.multikill_round_pct > 0:
            knowledge.append(
                {
                    "title": f"Clutch & multikills: {nickname}",
                    "description": (
                        f"{nickname} clutch wins: {card.clutch_win_count}, "
                        f"multikill round %: {card.multikill_round_pct:.1f}%. "
                        f"{'High clutch performer.' if card.clutch_win_count > 50 else 'Standard clutch rate.'}"
                    ),
                    "category": "clutch_performance",
                    "situation": "Clutch situation reference",
                    "map_name": None,
                    "pro_example": f"{nickname} (HLTV stats)",
                }
            )

        return knowledge

    def mine_map_specific_knowledge(self) -> int:
        """
        Generate map-specific tactical knowledge from RoundStats demo data.

        Aggregates per-(player, map, side) performance from the monolith DB's
        roundstats table and creates TacticalKnowledge entries for standout
        performances (avg_rating >= 1.0, minimum rounds threshold).

        Returns:
            Number of knowledge entries created.
        """
        import sqlite3
        from pathlib import Path

        db_path: str = str(Path(__file__).resolve().parent.parent / "storage" / "database.db")
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")

        # Load all roundstats grouped by (demo_name, player, side)
        rows = conn.execute(
            """
            SELECT demo_name, player_name, side,
                   SUM(kills) as total_kills,
                   SUM(damage_dealt) as total_dmg,
                   CAST(SUM(kast) AS REAL) / COUNT(*) as kast_rate,
                   CAST(SUM(opening_kill) AS REAL) / COUNT(*) as ok_rate,
                   AVG(round_rating) as avg_rating,
                   COUNT(*) as rounds_played
            FROM roundstats
            GROUP BY demo_name, player_name, side
        """
        ).fetchall()
        conn.close()

        # Re-group by (map, player, side) across demos
        aggregates: Dict[Tuple[str, str, str], Dict[str, Any]] = defaultdict(
            lambda: {
                "total_kills": 0,
                "total_dmg": 0,
                "kast_sum": 0.0,
                "ok_sum": 0.0,
                "rating_sum": 0.0,
                "rounds": 0,
                "demos": 0,
            }
        )

        for demo_name, player, side, t_kills, t_dmg, kast, ok, rating, rnds in rows:
            map_name = None
            for part in reversed(demo_name.split("-")):
                if part in _KNOWN_MAPS:
                    map_name = part
                    break
            if not map_name:
                continue

            key = (map_name, player, side)
            a = aggregates[key]
            a["total_kills"] += int(t_kills or 0)
            a["total_dmg"] += int(t_dmg or 0)
            a["kast_sum"] += float(kast or 0) * int(rnds or 0)
            a["ok_sum"] += float(ok or 0) * int(rnds or 0)
            a["rating_sum"] += float(rating or 0) * int(rnds or 0)
            a["rounds"] += int(rnds or 0)
            a["demos"] += 1

        # Generate knowledge for standout performances
        entries_created = 0
        for (map_name, player, side), a in aggregates.items():
            rounds_played: int = int(a["rounds"])
            if rounds_played < _MIN_MAP_ROUNDS:
                continue

            avg_rating = float(a["rating_sum"]) / rounds_played
            kast_rate = float(a["kast_sum"]) / rounds_played
            ok_rate = float(a["ok_sum"]) / rounds_played
            kpr = int(a["total_kills"]) / rounds_played
            adr = int(a["total_dmg"]) / rounds_played

            # Only notable performances
            if avg_rating < 1.0:
                continue

            display_name = player.title()
            title = f"{display_name}: {map_name.title()} {side}-side reference"
            description = (
                f"{display_name} on {map_name.title()} ({side}-side): "
                f"Rating {avg_rating:.2f}, KPR {kpr:.2f}, ADR {adr:.0f}, "
                f"KAST {kast_rate * 100:.0f}%, "
                f"Opening duel rate {ok_rate * 100:.0f}%. "
                f"Based on {rounds_played} rounds across {int(a['demos'])} demos."
            )
            situation = f"{side}-side play on {map_name.title()}"

            try:
                self.populator.add_knowledge(
                    title=title,
                    description=description,
                    category="pro_map_reference",
                    situation=situation,
                    map_name=map_name,
                    pro_example=f"{display_name} ({map_name} stats)",
                )
                entries_created += 1
            except Exception as e:
                logger.warning("Failed to add map knowledge for %s: %s", title, e)

        logger.info(
            "Map-specific knowledge: %d entries from %d aggregates",
            entries_created,
            len(aggregates),
        )
        return entries_created

    def _classify_archetype(self, card: ProPlayerStatCard) -> str:
        """Classify player archetype based on stat profile."""
        if card.impact >= _STAR_FRAGGER_IMPACT and card.rating_2_0 >= 1.10:
            return "Star Fragger"
        if card.headshot_pct < _SNIPER_HS_THRESHOLD and card.impact >= 1.05:
            return "AWP Specialist"
        if card.kast >= _SUPPORT_KAST_THRESHOLD and card.impact < 1.05:
            return "Support Anchor"
        if card.opening_duel_win_pct >= _ENTRY_OPENING_THRESHOLD:
            return "Entry Fragger"
        return "Versatile"


# Keep backward-compatible alias for init_knowledge_base.py
ProDemoMiner = ProStatsMiner


def auto_populate_from_pro_demos(limit: int = 50) -> int:
    """
    Convenience function for automated knowledge population.

    Args:
        limit: Maximum number of players to process

    Returns:
        Number of knowledge entries created
    """
    miner = ProStatsMiner()
    return miner.mine_all_pro_stats(limit=limit)


if __name__ == "__main__":
    from Programma_CS2_RENAN.backend.storage.database import init_database

    init_database()
    logger.info("=== Pro Stats Mining ===\n")
    miner = ProStatsMiner()
    count = miner.mine_all_pro_stats(limit=50)
    logger.info("Mined %s knowledge entries from pro stats", count)
    map_count = miner.mine_map_specific_knowledge()
    logger.info("Mined %s map-specific knowledge entries", map_count)
