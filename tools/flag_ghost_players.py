#!/usr/bin/env python3
"""
Flag ghost players (coaches/standins) with sample_weight=0.0.

Ghost players are detected by: avg_kills=0 AND avg_deaths=0 AND avg_adr=0
on a pro demo. These are players who joined the server but didn't engage
in gameplay (coaches, spectators, standins who barely played).

Setting sample_weight=0.0 excludes them from:
- Pro baseline computation
- Training data selection
- Z-score deviation calculations

Records are NOT deleted — they retain valid tick data for lineage.

Usage:
    python tools/flag_ghost_players.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import select, update

from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats


def flag_ghosts():
    """Flag ghost players with sample_weight=0.0."""
    init_database()
    db = get_db_manager()

    with db.get_session() as session:
        # Find ghost players: zero engagement on pro demos
        stmt = select(PlayerMatchStats).where(
            PlayerMatchStats.is_pro == True,  # noqa: E712
            PlayerMatchStats.avg_kills == 0.0,
            PlayerMatchStats.avg_deaths == 0.0,
            PlayerMatchStats.avg_adr == 0.0,
            PlayerMatchStats.sample_weight > 0.0,  # Not already flagged
        )
        ghosts = session.exec(stmt).all()

        if not ghosts:
            print("No ghost players found (or all already flagged).")
            return

        print(f"Found {len(ghosts)} ghost player records:\n")
        for g in ghosts:
            print(
                f"  {g.player_name:20s} | {g.demo_name[:40]} | "
                f"k={g.avg_kills:.1f} d={g.avg_deaths:.1f} adr={g.avg_adr:.1f} "
                f"kast={g.avg_kast:.2f} rating={g.rating:.3f}"
            )
            g.sample_weight = 0.0
            session.add(g)

        session.commit()
        print(f"\nFlagged {len(ghosts)} ghost players with sample_weight=0.0")


if __name__ == "__main__":
    flag_ghosts()
