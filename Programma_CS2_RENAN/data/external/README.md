# External reference datasets (elite comparison)

The `*.csv` files in this directory are **gitignored** reference datasets
consumed by `backend/processing/external_analytics.py` (`EliteAnalytics`) and
the CSV layer of `backend/processing/baselines/pro_baseline.py`. A fresh
checkout has none of them — the elite-comparison feature degrades gracefully
until they are (re)generated.

## Regeneration (F-0020)

On the machine that holds the populated databases (the Linux data box):

```bash
python tools/build_elite_csvs.py            # dry-run report
python tools/build_elite_csvs.py --apply    # write the CSVs here
```

| File | Source | Consumed columns |
|---|---|---|
| `all_Time_best_Players_Stats.csv` | hltv_metadata.db stat cards | `Rating1.0`, `K/D`, `ADR`, `Headshot %`, `KAST`, `Impact` (pro-baseline CSV layer) |
| `top_100_players.csv` | hltv_metadata.db stat cards (rating-sorted top 100) | `Name`, `CS Rating` |
| `match_players.csv` | database.db pro `PlayerMatchStats` | `adr`, `deaths`, `kills`, `rating`, `hs` |
| `tournament_advanced_stats.csv` | database.db pro `PlayerMatchStats` | `accuracy`, `econ_rating` (`utility_value` has no honest source — omitted, consumer tolerates) |
| `cs2_playstyle_roles_2024.csv` | **no source exists** — not regenerated; `get_player_role` returns "Unknown" | `player_name`, `role_overall` |

Scale convention: `Headshot %` and `KAST` are written **percent-styled**
(HLTV convention, ×100); the pro-baseline loader normalizes back to ratio on
read (F-0019).

`hltv_stats_urls.txt` seeds the HLTV scraper with player stat URLs.
