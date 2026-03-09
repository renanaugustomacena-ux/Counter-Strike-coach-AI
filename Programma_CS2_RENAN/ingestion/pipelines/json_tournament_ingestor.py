import json
import os
import sys
from pathlib import Path

import pandas as pd

# F6-06: sys.path bootstrap — required only when this utility script is executed directly.
# With proper package installation (pip install -e .) this block is a no-op when imported.
# Technical debt: remove when entrypoints are configured in pyproject.toml/setup.py.
if __name__ == "__main__":
    _project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.json_ingestor")


def process_tournament_jsons(json_dir: str, output_csv: str):
    """Parses tournament JSON files and extracts advanced metrics."""
    json_path = Path(json_dir)
    all_stats = []
    json_files = list(json_path.glob("*.json"))
    logger.info("Found %s JSON files to process.", len(json_files))

    for i, file_path in enumerate(json_files):
        try:
            stats = _process_single_json(file_path)
            all_stats.extend(stats)
            _log_progress(i, len(json_files))
        except Exception as e:
            logger.error("Failed to process %s: %s", file_path.name, e)

    _save_results(all_stats, output_csv)


def _process_single_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    match_id = data.get("id")
    match_slug = data.get("slug")
    return _extract_match_stats(data.get("match_maps", []), match_id, match_slug)


def _extract_match_stats(maps, match_id, match_slug):
    stats = []
    for m_map in maps:
        map_stats = _extract_map_stats(m_map, match_id, match_slug)
        stats.extend(map_stats)
    return stats


def _extract_map_stats(m_map, match_id, match_slug):
    stats = []
    map_name = m_map.get("map_name")
    for game in m_map.get("games", []):
        game_stats = _extract_game_stats(game, match_id, match_slug, map_name)
        stats.extend(game_stats)
    return stats


def _extract_game_stats(game, match_id, match_slug, map_name):
    stats = []
    for rnd in game.get("game_rounds", []):
        round_stats = _extract_round_stats(rnd, match_id, match_slug, map_name)
        stats.extend(round_stats)
    return stats


def _extract_round_stats(rnd, match_id, match_slug, map_name):
    stats = []
    round_num = rnd.get("round_number")
    for t_stats in rnd.get("game_round_team_clans", []):
        stat = _build_flat_stat(t_stats, match_id, match_slug, map_name, round_num)
        stats.append(stat)
    return stats


def _build_flat_stat(t_stats, match_id, match_slug, map_name, round_num):
    s = {
        "match_id": match_id,
        "match_slug": match_slug,
        "map_name": map_name,
        "round_num": round_num,
        "team_name": t_stats.get("clan_name"),
        "kills": t_stats.get("kills", 0),
        "deaths": t_stats.get("death", 0),
        "damage": t_stats.get("damage", 0),
        "hits": t_stats.get("hits", 0),
        "shots": t_stats.get("shots", 0),
        "money_spent": t_stats.get("money_spent", 0),
    }
    s["accuracy"] = s["hits"] / s["shots"] if s["shots"] > 0 else 0
    s["econ_rating"] = s["damage"] / s["money_spent"] if s["money_spent"] > 0 else 0
    return s


def _log_progress(i, total):
    if i > 0 and i % 100 == 0:
        logger.info("Processed %s/%s files...", i, total)


def _save_results(all_stats, output_csv):
    if not all_stats:
        logger.warning("No stats extracted.")
        return
    pd.DataFrame(all_stats).to_csv(output_csv, index=False)
    logger.info("Saved %s records to %s", len(all_stats), output_csv)


if __name__ == "__main__":
    # Use paths relative to project root
    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )

    JSON_DIR = os.path.join(BASE_DIR, "new_datasets", "csgo_tournament_data", "CS_GO_Tournaments")
    OUTPUT_CSV = os.path.join(
        BASE_DIR, "Programma_CS2_RENAN", "data", "external", "tournament_advanced_stats.csv"
    )

    # Ensure directory exists
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    process_tournament_jsons(JSON_DIR, OUTPUT_CSV)
