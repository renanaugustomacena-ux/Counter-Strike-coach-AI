# Dataset di riferimento esterni (confronto elite)

I file `*.csv` in questa directory sono dataset di riferimento **gitignored**
consumati da `backend/processing/external_analytics.py` (`EliteAnalytics`) e
dal layer CSV di `backend/processing/baselines/pro_baseline.py`. Un checkout
nuovo non ne contiene nessuno — la funzionalità di confronto elite degrada
gracefully fino a quando non vengono (ri)generati.

## Rigenerazione (F-0020)

Sulla macchina che contiene i database popolati:

```bash
python tools/build_elite_csvs.py            # report dry-run
python tools/build_elite_csvs.py --apply    # scrive i CSV qui
```

| File | Sorgente | Colonne consumate |
|---|---|---|
| `all_Time_best_Players_Stats.csv` | stat card di hltv_metadata.db | `Rating1.0`, `K/D`, `ADR`, `Headshot %`, `KAST`, `Impact` (layer CSV pro-baseline) |
| `top_100_players.csv` | stat card di hltv_metadata.db (top 100 ordinati per rating) | `Name`, `CS Rating` |
| `match_players.csv` | `PlayerMatchStats` pro di database.db | `adr`, `deaths`, `kills`, `rating`, `hs` |
| `tournament_advanced_stats.csv` | `PlayerMatchStats` pro di database.db | `accuracy`, `econ_rating` (`utility_value` non ha sorgente onesta — omesso, il consumer lo tollera) |
| `cs2_playstyle_roles_2024.csv` | **nessuna sorgente esistente** — non rigenerato; `get_player_role` restituisce "Unknown" | `player_name`, `role_overall` |

Convenzione di scala: `Headshot %` e `KAST` sono scritti **in stile percentuale**
(convenzione HLTV, ×100); il loader pro-baseline normalizza di nuovo a rapporto
in lettura (F-0019).

`hltv_stats_urls.txt` alimenta lo scraper HLTV con URL di statistiche giocatori.
