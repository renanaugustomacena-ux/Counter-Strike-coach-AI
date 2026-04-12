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

    # Mine scenarios
    scenarios = []

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

        # Scenario 1: Entry Frag (opening kill)
        if row["opening_kill"]:
            scenarios.append(
                {
                    "context": {**base_ctx},
                    "action": "entry_frag",
                    "outcome": "kill",
                    "delta": 0.15,
                    "game_state": game_state,
                    "player": player,
                    "demo": demo_name,
                }
            )

        # Scenario 2: Entry Death (opening death)
        if row["opening_death"]:
            scenarios.append(
                {
                    "context": {**base_ctx},
                    "action": "entry_frag",
                    "outcome": "death",
                    "delta": -0.15,
                    "game_state": game_state,
                    "player": player,
                    "demo": demo_name,
                }
            )

        # Scenario 3: Multi-kill round win
        if row["kills"] >= 2 and row["round_won"]:
            scenarios.append(
                {
                    "context": {**base_ctx},
                    "action": "multi_kill",
                    "outcome": "round_win",
                    "delta": 0.25,
                    "game_state": game_state,
                    "player": player,
                    "demo": demo_name,
                }
            )

        # Scenario 4: Trade death (died but was traded)
        if row["was_traded"] and row["deaths"] == 1:
            scenarios.append(
                {
                    "context": {**base_ctx},
                    "action": "aggressive_push",
                    "outcome": "traded",
                    "delta": -0.05,
                    "game_state": game_state,
                    "player": player,
                    "demo": demo_name,
                }
            )

        # Scenario 5: Eco upset (low equipment, still won)
        if 0 < ev < 2000 and row["round_won"] and rnum not in (1, 13):
            scenarios.append(
                {
                    "context": {**base_ctx},
                    "action": "eco_force",
                    "outcome": "upset_win",
                    "delta": 0.30,
                    "game_state": game_state,
                    "player": player,
                    "demo": demo_name,
                }
            )

        # Scenario 6: Utility impact (significant grenade damage in a win)
        nade_dmg = (row["he_damage"] or 0) + (row["molotov_damage"] or 0)
        if nade_dmg >= 50 and row["round_won"]:
            scenarios.append(
                {
                    "context": {**base_ctx},
                    "action": "utility_damage",
                    "outcome": "round_win",
                    "delta": 0.10,
                    "game_state": game_state,
                    "player": player,
                    "demo": demo_name,
                }
            )

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
