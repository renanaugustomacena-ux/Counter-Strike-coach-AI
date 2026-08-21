"""F-0020 — rebuild the elite-comparison reference CSVs from live data.

The seven ``Programma_CS2_RENAN/data/external/*.csv`` reference files are
gitignored and were lost with the original external datasets. This tool
regenerates every file whose data actually exists in the project databases —
honestly: files whose source data does not exist are SKIPPED with a reason,
never fabricated.

Sources and coverage:

  hltv_metadata.db (ProPlayer + ProPlayerStatCard)
    -> all_Time_best_Players_Stats.csv   (Rating1.0/K-D/ADR/Headshot %/KAST/Impact)
    -> top_100_players.csv               (Name + CS Rating <- rating_2_0)
  database.db (PlayerMatchStats, is_pro=1)
    -> match_players.csv                 (per-match adr/deaths/kills/rating/hs)
    -> tournament_advanced_stats.csv     (accuracy / econ_rating)
  no source exists for:
    -> cs2_playstyle_roles_2024.csv      (no role data anywhere) — SKIPPED
    -> maps_statistics.csv / weapons_statistics.csv — dead loads, removed
       from EliteAnalytics in the same change; not regenerated.

Scale note (F-0019 pairing): ``Headshot %`` and ``KAST`` are written
PERCENT-styled (x100, HLTV convention). The pro-baseline CSV loader
normalizes percent back to ratio on read.

Usage:
    python tools/build_elite_csvs.py            # dry-run: report only
    python tools/build_elite_csvs.py --apply    # write the CSVs

Run on the machine that holds the populated databases (the Linux data box).
Read-only on both DBs (immutable URI); writes only under data/external/.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

_script_dir = Path(__file__).parent.absolute()
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

PACKAGE_ROOT = _project_root / "Programma_CS2_RENAN"
STORAGE_DIR = PACKAGE_ROOT / "backend" / "storage"
EXTERNAL_DIR = PACKAGE_ROOT / "data" / "external"

HLTV_DB = STORAGE_DIR / "hltv_metadata.db"
MONOLITH_DB = STORAGE_DIR / "database.db"

# The pro-baseline CSV loader needs >= 2 numeric rows per column.
MIN_ROWS = 2


def _ro_connect(db_path: Path) -> sqlite3.Connection:
    """Read-only connection that cannot create -wal/-shm side files."""
    return sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)


def _fetch_stat_cards() -> list[dict]:
    if not HLTV_DB.exists():
        print(f"[SKIP] {HLTV_DB} absent — HLTV-derived CSVs unavailable")
        return []
    with _ro_connect(HLTV_DB) as conn:
        try:
            rows = conn.execute(
                "SELECT p.nickname, c.rating_2_0, c.kpr, c.dpr, c.adr, "
                "       c.headshot_pct, c.kast, c.impact "
                "FROM proplayerstatcard c "
                "JOIN proplayer p ON p.hltv_id = c.player_id "
                "WHERE c.time_span = 'all_time'"
            ).fetchall()
        except sqlite3.OperationalError as e:
            print(f"[SKIP] hltv_metadata.db query failed: {e}")
            return []
    return [
        {
            "name": r[0],
            "rating": r[1] or 0.0,
            "kpr": r[2] or 0.0,
            "dpr": r[3] or 0.0,
            "adr": r[4] or 0.0,
            "hs": r[5] or 0.0,
            "kast": r[6] or 0.0,
            "impact": r[7] or 0.0,
        }
        for r in rows
    ]


def _fetch_pro_match_rows() -> list[dict]:
    if not MONOLITH_DB.exists():
        print(f"[SKIP] {MONOLITH_DB} absent — demo-derived CSVs unavailable")
        return []
    with _ro_connect(MONOLITH_DB) as conn:
        try:
            rows = conn.execute(
                "SELECT player_name, demo_name, avg_adr, avg_deaths, avg_kills, "
                "       rating, avg_hs, accuracy, econ_rating "
                "FROM playermatchstats WHERE is_pro = 1"
            ).fetchall()
        except sqlite3.OperationalError as e:
            print(f"[SKIP] database.db query failed: {e}")
            return []
    return [
        {
            "player": r[0],
            "demo": r[1],
            "adr": r[2] or 0.0,
            "deaths": r[3] or 0.0,
            "kills": r[4] or 0.0,
            "rating": r[5] or 0.0,
            "hs": r[6] or 0.0,
            "accuracy": r[7] or 0.0,
            "econ_rating": r[8] or 0.0,
        }
        for r in rows
    ]


def _write_csv(path: Path, header: list[str], rows: list[list], apply: bool) -> None:
    if len(rows) < MIN_ROWS:
        print(f"[SKIP] {path.name}: only {len(rows)} source rows (< {MIN_ROWS})")
        return
    if not apply:
        print(f"[DRY-RUN] would write {path.name}: {len(rows)} rows, columns {header}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"[WRITE] {path.name}: {len(rows)} rows")


def build_hltv_csvs(out_dir: Path, apply: bool) -> None:
    cards = _fetch_stat_cards()
    if not cards:
        print("[SKIP] all_Time_best_Players_Stats.csv + top_100_players.csv (no stat cards)")
        return

    # Percent-styled on disk (HLTV convention); loader divides back to ratio.
    best_rows = [
        [
            c["name"],
            round(c["rating"], 3),
            round(c["kpr"] / c["dpr"], 3) if c["dpr"] >= 0.01 else "",
            round(c["adr"], 1),
            round(c["hs"] * 100.0, 1),
            round(c["kast"] * 100.0, 1),
            round(c["impact"], 3),
        ]
        for c in cards
    ]
    _write_csv(
        out_dir / "all_Time_best_Players_Stats.csv",
        ["Name", "Rating1.0", "K/D", "ADR", "Headshot %", "KAST", "Impact"],
        best_rows,
        apply,
    )

    top = sorted(cards, key=lambda c: c["rating"], reverse=True)[:100]
    _write_csv(
        out_dir / "top_100_players.csv",
        ["Name", "CS Rating"],
        [[c["name"], round(c["rating"], 3)] for c in top],
        apply,
    )


def build_demo_csvs(out_dir: Path, apply: bool) -> None:
    rows = _fetch_pro_match_rows()
    if not rows:
        print("[SKIP] match_players.csv + tournament_advanced_stats.csv (no pro match rows)")
        return

    _write_csv(
        out_dir / "match_players.csv",
        ["player", "demo", "adr", "deaths", "kills", "rating", "hs"],
        [
            [r["player"], r["demo"], r["adr"], r["deaths"], r["kills"], r["rating"], r["hs"]]
            for r in rows
        ],
        apply,
    )
    # utility_value has no honest source anywhere — column omitted; the
    # consumer tolerates its absence (avail-list in _prepare_tournament).
    _write_csv(
        out_dir / "tournament_advanced_stats.csv",
        ["accuracy", "econ_rating"],
        [[r["accuracy"], r["econ_rating"]] for r in rows],
        apply,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Write CSVs (default: dry-run)")
    parser.add_argument(
        "--out-dir", type=Path, default=EXTERNAL_DIR, help="Target directory for CSVs"
    )
    args = parser.parse_args()

    print(f"Elite CSV builder — target: {args.out_dir} ({'APPLY' if args.apply else 'dry-run'})")
    build_hltv_csvs(args.out_dir, args.apply)
    build_demo_csvs(args.out_dir, args.apply)
    print(
        "[NOTE] cs2_playstyle_roles_2024.csv not regenerated — no role data "
        "source exists (get_player_role degrades to 'Unknown')."
    )
    if not args.apply:
        print("Dry-run complete. Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
