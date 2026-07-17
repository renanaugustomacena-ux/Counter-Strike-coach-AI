#!/usr/bin/env python3
"""
Repair zero-rating PlayerMatchStats records.

5 records have rating=0.000 despite having real kill/death/ADR stats.
Root cause: rating components produced NaN which was sanitized to 0.0.
This script recomputes ratings from available stats using the HLTV 2.0 formula.

Rating columns follow the RAW-components contract of
``compute_rating_components()`` (the SSOT): baseline normalization happens
only inside the ``rating`` aggregate, never in the ``rating_*`` columns.

Usage:
    python tools/repair_ratings.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Programma_CS2_RENAN.backend.processing.feature_engineering.rating import (
    compute_rating_components,
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
                print(
                    f"  SKIP {rec.player_name:20s} | {rec.demo_name[:40]} — all stats are zero (ghost player)"
                )
                skipped += 1
                continue

            components = compute_rating_components(kpr=kpr, dpr=dpr, kast=kast, avg_adr=adr)
            new_rating = max(0.0, min(5.0, components["rating"]))

            print(
                f"  FIX  {rec.player_name:20s} | {rec.demo_name[:40]} | "
                f"k={kpr:.2f} d={dpr:.2f} adr={adr:.1f} kast={kast:.2f} → rating={new_rating:.3f}"
            )

            rec.rating = new_rating
            rec.rating_kpr = components["rating_kpr"]
            rec.rating_survival = components["rating_survival"]
            rec.rating_kast = components["rating_kast"]
            rec.rating_impact = components["rating_impact"]
            rec.rating_adr = components["rating_adr"]

            if rec.data_quality == "complete":
                rec.data_quality = "partial"

            session.add(rec)
            repaired += 1

        session.commit()

    print(f"\nDone: {repaired} repaired, {skipped} skipped")

    # DL-1: Record provenance for rating repair
    if repaired > 0:
        db.record_lineage(
            entity_type="batch_rating_repair",
            entity_id=repaired,
            source_demo="zero_rating_records",
            processing_step="rating_repair",
        )


if __name__ == "__main__":
    repair_zero_ratings()
