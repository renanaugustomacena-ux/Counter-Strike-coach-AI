# Datasets de referência externos (comparação elite)

Os arquivos `*.csv` neste diretório são datasets de referência **gitignored**
consumidos por `backend/processing/external_analytics.py` (`EliteAnalytics`) e
pela camada CSV de `backend/processing/baselines/pro_baseline.py`. Um checkout
novo não contém nenhum deles — a funcionalidade de comparação elite degrada
gracefully até que sejam (re)gerados.

## Regeneração (F-0020)

Na máquina que contém os bancos de dados populados:

```bash
python tools/build_elite_csvs.py            # relatório dry-run
python tools/build_elite_csvs.py --apply    # escreve os CSVs aqui
```

| Arquivo | Fonte | Colunas consumidas |
|---|---|---|
| `all_Time_best_Players_Stats.csv` | stat cards de hltv_metadata.db | `Rating1.0`, `K/D`, `ADR`, `Headshot %`, `KAST`, `Impact` (camada CSV pro-baseline) |
| `top_100_players.csv` | stat cards de hltv_metadata.db (top 100 ordenados por rating) | `Name`, `CS Rating` |
| `match_players.csv` | `PlayerMatchStats` pro de database.db | `adr`, `deaths`, `kills`, `rating`, `hs` |
| `tournament_advanced_stats.csv` | `PlayerMatchStats` pro de database.db | `accuracy`, `econ_rating` (`utility_value` não tem fonte honesta — omitido, o consumer tolera) |
| `cs2_playstyle_roles_2024.csv` | **nenhuma fonte existente** — não regenerado; `get_player_role` retorna "Unknown" | `player_name`, `role_overall` |

Convenção de escala: `Headshot %` e `KAST` são escritos **em estilo percentual**
(convenção HLTV, ×100); o loader pro-baseline normaliza de volta para razão
na leitura (F-0019).

`hltv_stats_urls.txt` alimenta o scraper HLTV com URLs de estatísticas de jogadores.
