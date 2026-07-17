#!/usr/bin/env python3
"""
Populate the MatchResult table from demo metadata + RoundStats outcomes.

For each unique demo_name in playertickstate:
  1. Parses team names and map from the demo_name convention
  2. Derives the outcome per STARTING SIDE from RoundStats round_won counts
  3. Gets map_name from playertickstate
  4. Creates a MatchResult row

Outcome derivation: group players by starting side, score = max rounds_won
within each group, winner reported as "CT_start"/"T_start"/"draw". Team
NAMES from the filename are stored as metadata only — the DB carries no
side↔name mapping, so pairing them would fabricate data (see
derive_winner_from_roundstats docstring).

Idempotent: skips demos that already have a MatchResult row.
Use --full to rebuild all rows.

Usage:
    python tools/populate_match_results.py            # incremental
    python tools/populate_match_results.py --full     # rebuild
"""

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = str(PROJECT_ROOT / "Programma_CS2_RENAN" / "backend" / "storage" / "database.db")

KNOWN_MAPS = {
    "mirage",
    "overpass",
    "inferno",
    "dust2",
    "ancient",
    "nuke",
    "anubis",
    "vertigo",
    "train",
}


def parse_demo_name(name: str) -> dict:
    result = {"team_a": None, "team_b": None, "map_name": None, "year": None}

    year_match = re.match(r"^(\d{4})-(.+)$", name)
    if year_match:
        result["year"] = int(year_match.group(1))
        name = year_match.group(2)

    parts = name.split("-vs-", 1)
    if len(parts) != 2:
        return result

    result["team_a"] = parts[0]
    remainder = parts[1]

    remainder = re.sub(r"\(.*?\)$", "", remainder)
    remainder = re.sub(r"-p\d+$", "", remainder)

    for map_name in KNOWN_MAPS:
        if remainder.endswith("-" + map_name) or remainder.endswith("_" + map_name):
            result["map_name"] = map_name
            remainder = remainder[: -(len(map_name) + 1)]
            break

    remainder = re.sub(r"-m\d+$", "", remainder)
    result["team_b"] = remainder

    return result


def derive_winner_from_roundstats(conn: sqlite3.Connection, demo_name: str) -> tuple:
    """
    Derive the match outcome from roundstats round_won data.

    Groups players by starting side (the side they played most rounds on is
    their first-half side in MR12). Returns
    (ct_start_score, t_start_score, winner_start_side) where
    winner_start_side is "CT_start", "T_start" or "draw" — or (None, None,
    None) when no roundstats exist.

    ANTI-FABRICATION: nothing in the DB links a starting side to the team
    NAMES parsed from the filename (that mapping lives only in the .dem
    scoreboard, which this tool does not open). An earlier revision guessed
    winner = team_a whenever the CT-start group won — a coin flip recorded
    as fact. The outcome is therefore reported per starting side only; team
    names stay in the JSON strictly as filename metadata.
    """
    rows = conn.execute(
        """
        SELECT player_name, side,
               SUM(CASE WHEN round_won = 1 THEN 1 ELSE 0 END) as rounds_won,
               COUNT(*) as total_rounds
        FROM roundstats
        WHERE demo_name = ?
        GROUP BY player_name, side
        """,
        (demo_name,),
    ).fetchall()

    if not rows:
        return None, None, None

    player_sides = {}
    for player_name, side, rounds_won, total_rounds in rows:
        if player_name not in player_sides:
            player_sides[player_name] = {"CT": 0, "T": 0, "CT_won": 0, "T_won": 0}
        player_sides[player_name][side] = total_rounds
        player_sides[player_name][f"{side}_won"] = rounds_won

    ct_start_scores = []
    t_start_scores = []
    for player, sides in player_sides.items():
        total_won = sides["CT_won"] + sides["T_won"]
        if sides["CT"] >= sides["T"]:
            ct_start_scores.append(total_won)
        else:
            t_start_scores.append(total_won)

    if not ct_start_scores or not t_start_scores:
        return None, None, None

    # A full-match player's round_won count IS the team score; substitutes
    # or disconnects undercount, so take the max across the group instead
    # of whichever player happened to come first.
    ct_team_won = max(ct_start_scores)
    t_team_won = max(t_start_scores)

    if ct_team_won > t_team_won:
        return ct_team_won, t_team_won, "CT_start"
    elif t_team_won > ct_team_won:
        return ct_team_won, t_team_won, "T_start"
    else:
        return ct_team_won, t_team_won, "draw"


def main() -> None:
    from Programma_CS2_RENAN.backend.storage.database import init_database

    full_rebuild = "--full" in sys.argv

    print("=== MatchResult Population ===")
    print(f"    MODE: {'Full rebuild' if full_rebuild else 'Incremental'}\n")

    init_database()

    conn = sqlite3.connect(DB_PATH, timeout=60)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")

    demo_names = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT demo_name FROM playertickstate ORDER BY demo_name"
        ).fetchall()
    ]
    print(f"Found {len(demo_names)} demos in playertickstate.\n")

    existing_demos = set()
    if not full_rebuild:
        existing_demos = {
            r[0]
            for r in conn.execute(
                "SELECT event_name FROM matchresult WHERE event_name LIKE 'demo:%'"
            ).fetchall()
        }

    if full_rebuild:
        conn.execute("DELETE FROM matchresult WHERE event_name LIKE 'demo:%'")
        conn.commit()

    total_inserted = 0
    total_skipped = 0
    total_with_winner = 0

    for i, demo_name in enumerate(demo_names, 1):
        event_key = f"demo:{demo_name}"

        if event_key in existing_demos:
            total_skipped += 1
            continue

        parsed = parse_demo_name(demo_name)
        team_a = parsed["team_a"] or "unknown"
        team_b = parsed["team_b"] or "unknown"
        map_name = parsed["map_name"]

        if not map_name:
            row = conn.execute(
                "SELECT DISTINCT map_name FROM playertickstate WHERE demo_name = ? LIMIT 1",
                (demo_name,),
            ).fetchone()
            if row:
                map_name = row[0].replace("de_", "")

        ct_score, t_score, winner_side = derive_winner_from_roundstats(conn, demo_name)

        date_row = conn.execute(
            "SELECT MIN(created_at) FROM roundstats WHERE demo_name = ?",
            (demo_name,),
        ).fetchone()
        match_date = (
            date_row[0] if date_row and date_row[0] else datetime.now(timezone.utc).isoformat()
        )

        # team_a/team_b are FILENAME metadata; scores/winner are per starting
        # side — the DB cannot link the two (see derive_winner docstring).
        map_picks: dict = {"map": map_name, "team_a": team_a, "team_b": team_b}
        if ct_score is not None:
            map_picks.update(
                {
                    "score_ct_start": ct_score,
                    "score_t_start": t_score,
                    "winner_start_side": winner_side,
                }
            )
        map_picks_json = json.dumps(map_picks)

        conn.execute(
            """
            INSERT INTO matchresult (created_at, date, event_name, map_picks)
            VALUES (?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                match_date,
                event_key,
                map_picks_json,
            ),
        )
        total_inserted += 1
        if winner_side:
            total_with_winner += 1

        status = (
            f"ct_start={ct_score} t_start={t_score} winner={winner_side}"
            if ct_score is not None
            else "no roundstats"
        )
        if (i % 25 == 0) or (i == len(demo_names)):
            print(f"[{i:03d}/{len(demo_names)}] Last: {demo_name} ({status})")

    conn.commit()
    conn.close()

    print(f"\n=== Done ===")
    print(f"  Inserted: {total_inserted}")
    print(f"  Skipped (existing): {total_skipped}")
    print(f"  With winner derived: {total_with_winner}")
    print(f"  Without roundstats: {total_inserted - total_with_winner}")

    conn2 = sqlite3.connect(DB_PATH, timeout=10)
    total = conn2.execute("SELECT COUNT(*) FROM matchresult").fetchone()[0]
    conn2.close()
    print(f"\n  Total matchresult rows: {total}")


if __name__ == "__main__":
    main()
