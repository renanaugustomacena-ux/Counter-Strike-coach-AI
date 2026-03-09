import csv
import sys
from pathlib import Path

# F6-06: sys.path bootstrap — required only when this utility script is executed directly.
# With proper package installation (pip install -e .) this block is a no-op when imported.
# Technical debt: remove when entrypoints are configured in pyproject.toml/setup.py.
if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[3]  # .../Macena_cs2_analyzer
    sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from Programma_CS2_RENAN.backend.storage.database import DatabaseManager
from Programma_CS2_RENAN.backend.storage.db_models import Ext_PlayerPlaystyle, Ext_TeamRoundStats
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.csv_migrator")


# F6-17: Extracted safe_float to module level — was redefined inside every loop iteration.
def _safe_float(value, default: float = 0.0) -> float:
    """Parse float safely; return default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default: int = 0) -> int:
    """Parse int safely; return default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class CSVMigrator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        # Use absolute paths derived from project_root
        # All CSVs are now in Programma_CS2_RENAN/data/external
        self.data_dir = Path(__file__).resolve().parents[3] / "Programma_CS2_RENAN/data/external"

        # Translation/Alignment Logic:
        # - We map "lurker", "entry" etc. to normalized role probabilities.
        # - We ensure match_id is handled (though external IDs may conflict, we store them as external_match_id).

    def run_migration(self):
        """Orchestrates the migration of all CSVs."""
        logger.info("Starting CSV Migration...")

        # 1. Matches (Metadata) - Note: schema mapping for this might need adjustment if we want to store it in Ext tables or MatchMetadata
        # For now, we focus on the requested Ext tables.

        # 2. Player Playstyles
        self.migrate_playstyles()

        # 3. Tournament Advanced Stats (Team/Round)
        self.migrate_tournament_stats()

        logger.info("CSV Migration Completed.")

    def migrate_playstyles(self):
        file_path = self.data_dir / "cs2_playstyle_roles_2024.csv"
        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return

        logger.info("Migrating Playstyles from %s...", file_path)
        count = 0
        with self.db.get_session() as session:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Idempotency check (simple)
                    existing = session.exec(
                        select(Ext_PlayerPlaystyle).where(
                            Ext_PlayerPlaystyle.player_name == row["player_name"],
                            Ext_PlayerPlaystyle.team_name == row["team_clan_name"],
                        )
                    ).first()

                    if existing:
                        continue

                    # Parse role
                    role_overall = row.get("role_overall", "Flex")

                    # Initialize role probabilities (default 0.0)
                    roles = {
                        "lurker": 0.0,
                        "entry": 0.0,
                        "support": 0.0,
                        "awper": 0.0,
                        "anchor": 0.0,
                        "igl": 0.0,
                    }

                    # Set the primary role to 1.0 (binary encoding for now, unless mixed data exists)
                    # Mapping generic role names to our fields
                    if "Lurker" in role_overall:
                        roles["lurker"] = 1.0
                    elif "Spacetaker" in role_overall:
                        roles["entry"] = 1.0  # Assuming Spacetaker ~ Entry
                    elif "Support" in role_overall:
                        roles["support"] = 1.0
                    elif "AWPer" in role_overall:
                        roles["awper"] = 1.0  # Or Sniper
                    elif "Anchor" in role_overall:
                        roles["anchor"] = 1.0
                    elif "IGL" in role_overall:
                        roles["igl"] = 1.0

                    player_stats = Ext_PlayerPlaystyle(
                        player_name=row["player_name"],
                        steamid=row.get("steamid"),
                        team_name=row["team_clan_name"],
                        role_lurker=roles["lurker"],
                        role_entry=roles["entry"],
                        role_support=roles["support"],
                        role_awper=roles["awper"],
                        role_anchor=roles["anchor"],
                        role_igl=roles["igl"],
                        assigned_role=role_overall,
                        # Raw Metrics mapping — F6-17: use module-level _safe_float
                        tapd=_safe_float(row.get("tapd_overall")),
                        oap=_safe_float(row.get("oap_overall")),
                        podt=_safe_float(row.get("podt_overall")),
                        # No direct 'impact_rating' or 'aggression' column found in inspection,
                        # so likely oap serves as aggression proxy. Leaving 0.0 for now if not present.
                        rating_impact=0.0,
                        aggression_score=0.0,
                    )
                    session.add(player_stats)
                    count += 1

            session.commit()
            logger.info("Imported %s playstyle records.", count)

    def migrate_tournament_stats(self):
        file_path = self.data_dir / "tournament_advanced_stats.csv"
        if not file_path.exists():
            logger.warning("File not found: %s", file_path)
            return

        logger.info("Migrating Tournament Stats from %s...", file_path)
        count = 0
        with self.db.get_session() as session:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    # Batch commit every 1000 rows
                    if i > 0 and i % 1000 == 0:
                        session.commit()
                        logger.info("Processed %s rows...", i)  # F6-05

                    try:
                        match_id = int(row["match_id"])
                        round_num = int(row["round_num"])
                        team_name = row["team_name"]

                        # R3-H05: Idempotency check — skip if record already exists
                        existing = session.exec(
                            select(Ext_TeamRoundStats).where(
                                Ext_TeamRoundStats.external_match_id == match_id,
                                Ext_TeamRoundStats.round_num == round_num,
                                Ext_TeamRoundStats.team_name == team_name,
                            )
                        ).first()
                        if existing:
                            continue

                        record = Ext_TeamRoundStats(
                            match_id=0,  # No internal match link yet
                            external_match_id=match_id,
                            map_name=row["map_name"],
                            round_num=round_num,
                            team_name=team_name,
                            # F6-17: use module-level _safe_float / _safe_int
                            kills=_safe_int(row["kills"]),
                            deaths=_safe_int(row["deaths"]),
                            damage=_safe_float(row["damage"]),
                            hits=_safe_int(row["hits"]),
                            shots=_safe_int(row["shots"]),
                            utility_value=_safe_float(row["utility_value"]),
                            money_spent=_safe_float(row["money_spent"]),
                            headshots=_safe_int(row["headshots"]),
                            first_kills=_safe_int(row["first_kills"]),
                            first_deaths=_safe_int(row["first_deaths"]),
                            accuracy=_safe_float(row["accuracy"]),
                            econ_rating=_safe_float(row["econ_rating"]),
                        )
                        session.add(record)
                        count += 1
                    except Exception as e:
                        logger.error("Error row %s: %s", i, e)

            session.commit()
            logger.info("Imported %s tournament round records.", count)


if __name__ == "__main__":
    db = DatabaseManager()
    db.create_db_and_tables()  # Ensure schema exists
    migrator = CSVMigrator(db)
    migrator.run_migration()
