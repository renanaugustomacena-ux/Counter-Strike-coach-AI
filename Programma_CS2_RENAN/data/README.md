# Data — Application Data & Configuration

> **Authority:** Rule 4 (Data Persistence)

This directory contains runtime data, configuration files, coaching knowledge, external statistical datasets, and the demo ingestion staging area. All files here are user-side data (not code).

## Directory Structure

```
data/
├── demos/                           # Demo file staging
│   └── pro_ingest/                 # Professional match demos for training
├── docs/                            # In-app help documentation
│   ├── features.md                 # Coaching features list
│   ├── getting_started.md          # User setup guide (10/10 rule)
│   └── troubleshooting.md         # Common issues
├── external/                        # Third-party statistical datasets (CSV)
│   ├── all_Time_best_Players_Stats.csv
│   ├── cs2_playstyle_roles_2024.csv
│   ├── csgo_games.csv
│   ├── Maps01_BombPlantOutcomes01.csv
│   ├── Maps01_RoundOutcomes.csv
│   ├── Maps02_BombPlantOutcomes.csv
│   ├── maps_statistics.csv
│   ├── top_100_players.csv
│   ├── weapons_statistics.csv
│   └── hltv_stats_urls.txt         # HLTV player URLs for scraper
├── knowledge/                       # RAG coaching knowledge base
│   ├── {map}_coaching.txt          # Per-map coaching text (8 maps)
│   ├── {map}_coaching_ocr.txt      # OCR-extracted variants
│   ├── general_coaching.txt        # General CS2 coaching principles
│   ├── coaching_knowledge_base.json # Structured KB (JSON)
│   └── extraction_summary.json     # Knowledge extraction metadata
├── dataset.csv                      # Training dataset
├── map_config.json                  # Map spatial configuration (257 lines)
├── map_tensors.json                 # 3D tensor coordinate definitions
└── hltv_sync_state.json            # HLTV scraper sync state
```

## Key Configuration Files

### `map_config.json` (257 lines)

Spatial definitions for all CS2 competitive maps:

```json
{
  "de_mirage": {
    "display_name": "Mirage",
    "pos_x": -3230,
    "pos_y": 1713,
    "scale": 5.0,
    "landmarks": {
      "a_site": [x, y],
      "b_site": [x, y],
      "mid_control": [x, y],
      "t_spawn": [x, y],
      "ct_spawn": [x, y]
    }
  }
}
```

- Used by `core/spatial_data.py` for coordinate transformations
- Multi-level maps (Nuke, Vertigo) include `z_cutoff` boundaries
- Competitive pool: nuke, inferno, mirage, dust2, ancient, overpass, vertigo, anubis, train

### `map_tensors.json`

3D tensor coordinates for ML training:
- Bombsite positions (A/B) with X, Y, Z
- Spawn positions (T/CT)
- Mid-control zones and important zones (connector, jungle, palace, etc.)

## `demos/pro_ingest/`

Staging directory for professional match `.dem` files. The ingestion pipeline picks up files from here for pro baseline training.

- Currently tracked via `.gitkeep` (empty in the repository)
- Production: ~200 pro demo files on the external SSD
- Files are processed by `backend/data_sources/demo_parser.py`

## `external/` — Statistical Datasets

Third-party CSV data used for reference analytics and coaching calibration:

| File | Content | Used By |
|------|---------|---------|
| `top_100_players.csv` | Top 100 HLTV player statistics | `processing/external_analytics.py` |
| `all_Time_best_Players_Stats.csv` | Historical best player stats | Pro baseline reference |
| `cs2_playstyle_roles_2024.csv` | Role classification data (2024) | `backend/ingestion/csv_migrator.py` |
| `maps_statistics.csv` | Map win rates and play rates | Map context analysis |
| `weapons_statistics.csv` | Weapon damage/accuracy data | Weapon class features |
| `Maps01_RoundOutcomes.csv` | Round outcome distributions | Win probability training |
| `Maps01_BombPlantOutcomes01.csv` | Bomb plant outcome data (dataset 1) | Economy analysis |
| `Maps02_BombPlantOutcomes.csv` | Bomb plant outcome data (dataset 2) | Economy analysis |
| `csgo_games.csv` | Historical CS:GO match data | Legacy reference |
| `hltv_stats_urls.txt` | HLTV player profile URLs | HLTV scraper input |

## `knowledge/` — RAG Knowledge Base

Coaching knowledge files for the COPER (Context Optimized with Prompt, Experience, Replay) framework:

### Per-Map Coaching (8 maps x 2 versions)

Each map has two versions:
- `{map}_coaching.txt` — Raw coaching text
- `{map}_coaching_ocr.txt` — OCR-extracted variant

Maps covered: Ancient, Anubis, Dust2, Inferno, Mirage, Nuke, Overpass + general

### Structured Knowledge Base

- `coaching_knowledge_base.json` — Structured KB with sections for tactics, positions, utility, and callouts
- `coaching_knowledge_base_ocr.json` — OCR variant
- `extraction_summary.json` — Metadata about knowledge extraction (timestamps, versions)

### How Knowledge Is Used

```
knowledge/ files
    │
    └── backend/knowledge/rag_knowledge.py (KnowledgeEmbedder)
            │
            ├── Sentence-BERT embeds text chunks (384-dim vectors)
            └── FAISS indexes for fast similarity search
                    │
                    └── CoachingService retrieves relevant knowledge per query
```

## `docs/` — In-App Help

Markdown files served by `backend/knowledge_base/help_system.py`:

- `getting_started.md` — Setup guide, 10/10 rule, ingestion speeds, data maturity levels
- `features.md` — Feature descriptions
- `troubleshooting.md` — Common issues and solutions

## Development Notes

- **Do NOT commit demo files** (`.dem`) — they are 50-200MB each
- `map_config.json` coordinates come from CS2 game files (`resource/overviews/*.txt`)
- External CSVs are static reference data — update them manually when new data is available
- `hltv_sync_state.json` tracks scraper progress — empty `{}` means no active sync
- Knowledge files are the intellectual foundation of coaching — edit with care
- `dataset.csv` is generated by the training pipeline, not hand-edited
