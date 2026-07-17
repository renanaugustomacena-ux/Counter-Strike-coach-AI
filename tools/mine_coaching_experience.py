#!/usr/bin/env python3
"""
Mine CoachingExperience records from the RoundStats table.

Identifies high-impact tactical moments (entry frags, multi-kills, eco upsets,
trades, utility damage) from pro demo round stats and populates the
CoachingExperience table via ExperienceBank.add_experience().

Idempotent: skips insertion if context_hash already exists in the DB.

Usage:
    python tools/mine_coaching_experience.py
    python tools/mine_coaching_experience.py --dry-run
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = str(PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db")

KNOWN_MAPS = {"mirage", "dust2", "inferno", "nuke", "overpass", "ancient", "anubis", "vertigo"}


def _extract_map_name(demo_name: str) -> str:
    """Extract map name from demo_name like 'furia-vs-vitality-m1-mirage'."""
    for part in reversed(demo_name.split("-")):
        if part in KNOWN_MAPS:
            return part
    return "unknown"


def _classify_round_phase(round_number: int, equipment_value: int) -> str:
    """Classify round into pistol/eco/force/full_buy."""
    if round_number in (1, 13):
        return "pistol"
    if equipment_value < 2000:
        return "eco"
    if equipment_value < 4000:
        return "force"
    return "full_buy"


def _classify_equipment_tier(equipment_value: int) -> str:
    """Map equipment value to tier label."""
    if equipment_value < 2000:
        return "eco"
    if equipment_value < 4000:
        return "force"
    return "full"


def _mine_scenarios(rows) -> list:
    """Scan roundstats rows and emit scenario dicts for entry frags, multi-kills,
    trades, eco upsets, and utility-impact wins. Pure transform: no DB writes."""
    scenarios: list = []
    for row in rows:
        demo_name = row["demo_name"]
        map_name = _extract_map_name(demo_name)
        rnum = row["round_number"]
        player = row["player_name"]
        side = row["side"]
        ev = row["equipment_value"]
        round_phase = _classify_round_phase(rnum, ev)

        base_ctx = {
            "map_name": map_name,
            "round_phase": round_phase,
            "side": side,
            "equipment_tier": _classify_equipment_tier(ev),
        }
        game_state = {
            "demo_name": demo_name,
            "round_number": rnum,
            "player_name": player,
            "side": side,
            "kills": row["kills"],
            "deaths": row["deaths"],
            "assists": row["assists"],
            "damage_dealt": row["damage_dealt"],
            "equipment_value": ev,
            "round_won": bool(row["round_won"]),
            "round_rating": row["round_rating"],
        }

        def _add(action, outcome, delta):
            scenarios.append(
                {
                    "context": {**base_ctx},
                    "action": action,
                    "outcome": outcome,
                    "delta": delta,
                    "game_state": game_state,
                    "player": player,
                    "demo": demo_name,
                }
            )

        if row["opening_kill"]:
            _add("entry_frag", "kill", 0.15)
        if row["opening_death"]:
            _add("entry_frag", "death", -0.15)
        if row["kills"] >= 2 and row["round_won"]:
            _add("multi_kill", "round_win", 0.25)
        if row["was_traded"] and row["deaths"] == 1:
            _add("aggressive_push", "traded", -0.05)
        if 0 < ev < 2000 and row["round_won"] and rnum not in (1, 13):
            _add("eco_force", "upset_win", 0.30)
        nade_dmg = (row["he_damage"] or 0) + (row["molotov_damage"] or 0)
        if nade_dmg >= 50 and row["round_won"]:
            _add("utility_damage", "round_win", 0.10)
    return scenarios


def main() -> None:
    import sqlite3

    from Programma_CS2_RENAN.backend.knowledge.experience_bank import (
        PRO_EXPERIENCE_CONFIDENCE,
        ExperienceBank,
        ExperienceContext,
    )
    from Programma_CS2_RENAN.backend.storage.database import init_database

    dry_run = "--dry-run" in sys.argv

    print("=== Coaching Experience Mining ===")
    print(f"    MODE: {'Dry run' if dry_run else 'Live'}\n")

    init_database()

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row

    # Check current state
    existing = conn.execute("SELECT COUNT(*) FROM coachingexperience").fetchone()[0]
    print(f"Existing CoachingExperience records: {existing}")

    # Load all round stats
    rows = conn.execute(
        """
        SELECT demo_name, round_number, player_name, side,
               kills, deaths, assists, damage_dealt,
               headshot_kills, trade_kills, was_traded,
               opening_kill, opening_death,
               he_damage, molotov_damage, flashes_thrown, smokes_thrown,
               equipment_value, round_won, kast, round_rating
        FROM roundstats
        ORDER BY demo_name, round_number, player_name
    """
    ).fetchall()

    print(f"RoundStats rows to scan: {len(rows)}")
    scenarios = _mine_scenarios(rows)
    conn.close()

    # Scenario summary
    from collections import Counter

    action_counts = Counter(s["action"] for s in scenarios)
    print(f"\nMined {len(scenarios)} scenarios:")
    for action, count in sorted(action_counts.items()):
        print(f"  {action}: {count}")

    if dry_run:
        print("\nDry run — no records created.")
        return

    # Insert via ExperienceBank
    print(f"\nInserting {len(scenarios)} CoachingExperience records...")
    bank = ExperienceBank()
    inserted = 0
    skipped = 0

    for i, s in enumerate(scenarios, 1):
        ctx = ExperienceContext(
            map_name=s["context"]["map_name"],
            round_phase=s["context"]["round_phase"],
            side=s["context"]["side"],
            equipment_tier=s["context"]["equipment_tier"],
        )

        try:
            bank.add_experience(
                context=ctx,
                action_taken=s["action"],
                outcome=s["outcome"],
                delta_win_prob=s["delta"],
                game_state=s["game_state"],
                pro_player_name=s["player"],
                source_demo=s["demo"],
                confidence=PRO_EXPERIENCE_CONFIDENCE,
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1
        except Exception as e:
            if "UNIQUE" in str(e).upper() or "duplicate" in str(e).lower():
                skipped += 1
            else:
                print(f"  ERROR at #{i}: {e}")

        if i % 100 == 0:
            print(f"  Progress: {i}/{len(scenarios)} ({inserted} inserted, {skipped} skipped)")

    # Final report
    conn2 = sqlite3.connect(DB_PATH, timeout=10)
    conn2.execute("PRAGMA journal_mode=WAL")
    conn2.execute("PRAGMA busy_timeout=30000")
    final = conn2.execute("SELECT COUNT(*) FROM coachingexperience").fetchone()[0]
    conn2.close()

    print(f"\n=== Done ===")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (duplicate): {skipped}")
    print(f"  Total CoachingExperience records: {final}")

    # DL-1: Record provenance for experience mining
    if inserted > 0:
        from Programma_CS2_RENAN.backend.storage.database import get_db_manager

        get_db_manager().record_lineage(
            entity_type="batch_experience_mining",
            entity_id=inserted,
            source_demo="roundstats_aggregate",
            processing_step="experience_mining",
        )


if __name__ == "__main__":
    main()
