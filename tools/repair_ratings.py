#!/usr/bin/env python3
"""
Repair zero-rating PlayerMatchStats records.

5 records have rating=0.000 despite having real kill/death/ADR stats.
Root cause: rating components produced NaN which was sanitized to 0.0.
This script recomputes ratings from available stats using the HLTV 2.0 formula.

Usage:
    python tools/repair_ratings.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Programma_CS2_RENAN.backend.processing.feature_engineering.rating import (
    compute_hltv2_rating,
)
from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database
from Programma_CS2_RENAN.backend.storage.db_models import PlayerMatchStats


def repair_zero_ratings():
    """Find and repair PlayerMatchStats records with rating=0 but valid stats."""
    init_database()
    db = get_db_manager()

    repaired = 0
    skipped = 0

    with db.get_session() as session:
        from sqlmodel import select

        stmt = select(PlayerMatchStats).where(PlayerMatchStats.rating == 0.0)
        zero_ratings = session.exec(stmt).all()

        if not zero_ratings:
            print("No zero-rating records found. Nothing to repair.")
            return

        print(f"Found {len(zero_ratings)} records with rating=0.000\n")

        for rec in zero_ratings:
            # Try to recompute from per-round stats
            kpr = rec.avg_kills or 0.0
            dpr = rec.avg_deaths or 0.0
            kast = rec.avg_kast or 0.0
            adr = rec.avg_adr or 0.0

            if kpr == 0.0 and dpr == 0.0 and adr == 0.0:
                print(f"  SKIP {rec.player_name:20s} | {rec.demo_name[:40]} — all stats are zero (ghost player)")
                skipped += 1
                continue

            new_rating = compute_hltv2_rating(kpr=kpr, dpr=dpr, kast=kast, avg_adr=adr)
            new_rating = max(0.0, min(5.0, new_rating))

            print(
                f"  FIX  {rec.player_name:20s} | {rec.demo_name[:40]} | "
                f"k={kpr:.2f} d={dpr:.2f} adr={adr:.1f} kast={kast:.2f} → rating={new_rating:.3f}"
            )

            rec.rating = new_rating
            # Also recompute and store rating components
            from Programma_CS2_RENAN.backend.processing.feature_engineering.rating import (
                BASELINE_ADR,
                BASELINE_DPR_COMPLEMENT,
                BASELINE_IMPACT,
                BASELINE_KAST,
                BASELINE_KPR,
                compute_impact_rating,
                compute_survival_rating,
            )

            impact = compute_impact_rating(kpr, adr, dpr=dpr)
            rec.rating_kpr = kpr / BASELINE_KPR if BASELINE_KPR else 0.0
            rec.rating_survival = compute_survival_rating(dpr) / BASELINE_DPR_COMPLEMENT if BASELINE_DPR_COMPLEMENT else 0.0
            rec.rating_kast = kast / BASELINE_KAST if BASELINE_KAST else 0.0
            rec.rating_impact = impact / BASELINE_IMPACT if BASELINE_IMPACT else 0.0
            rec.rating_adr = adr / BASELINE_ADR if BASELINE_ADR else 0.0

            if rec.data_quality == "complete":
                rec.data_quality = "partial"

            session.add(rec)
            repaired += 1

        session.commit()

    print(f"\nDone: {repaired} repaired, {skipped} skipped")


if __name__ == "__main__":
    repair_zero_ratings()
