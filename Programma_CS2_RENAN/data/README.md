# Data — Application Data & Configuration

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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
├── external/                        # External data inputs
│   └── hltv_stats_urls.txt         # HLTV player URLs for scraper
├── knowledge/                       # RAG coaching knowledge base
│   ├── {map}_coaching.txt          # Per-map coaching text (7 maps)
│   ├── {map}_coaching_ocr.txt      # OCR-extracted variants
│   ├── general_coaching.txt        # General CS2 coaching principles (+ OCR variant)
│   ├── coaching_knowledge_base.json # Structured KB (JSON, + OCR variant)
│   └── extraction_summary.json     # Knowledge extraction metadata
├── dataset.csv                      # Training dataset placeholder (currently empty)
├── map_config.json                  # Map spatial configuration (260 lines)
├── map_tensors.json                 # 3D tensor coordinate definitions
└── hltv_sync_state.json            # HLTV scraper sync state
```

## Key Configuration Files

### `map_config.json` (260 lines)

Spatial definitions for all CS2 competitive maps. Map entries live under the
top-level `maps` key (alongside `_description`, `_source`, `_last_updated`,
and `competitive_pool`):

```json
{
  "maps": {
    "de_mirage": {
      "pos_x": -3230,
      "pos_y": 1713,
      "scale": 5.0,
      "display_name": "Mirage",
      "landmarks": {
        "A-Site": [x, y],
        "B-Site": [x, y],
        "Mid": [x, y],
        "T-Spawn": [x, y],
        "CT-Spawn": [x, y]
      }
    }
  }
}
```

- Used by `core/spatial_data.py` for coordinate transformations
- Multi-level maps (Nuke, Vertigo) include `z_cutoff` boundaries and `levels`
- Competitive pool: nuke, inferno, mirage, dust2, ancient, overpass, vertigo, anubis, train

### `map_tensors.json`

3D tensor coordinates for ML training (7 maps: mirage, inferno, dust2, nuke,
overpass, ancient, anubis):
- `image_file` radar reference per map
- Bombsite positions (A/B) with X, Y, Z
- Spawn positions (T/CT)
- Mid-control zones and important zones (connector, jungle, palace, etc.)

## `demos/pro_ingest/`

Staging directory for professional match `.dem` files. The ingestion pipeline picks up files from here for pro baseline training.

- Currently tracked via `.gitkeep` (empty in the repository)
- Production: ~200 pro demo files on the external SSD
- Files are processed by `backend/data_sources/demo_parser.py`

## `external/` — External Data Inputs

Currently contains a single file:

| File | Content | Used By |
|------|---------|---------|
| `hltv_stats_urls.txt` | HLTV player profile URLs | HLTV scraper input |

Third-party CSV datasets (player stats, map statistics, round outcomes) are not
kept in the repository; the tournament JSON ingestor writes its output CSV here
(`tournament_advanced_stats.csv`) when run.

## `knowledge/` — RAG Knowledge Base

Coaching knowledge files for the COPER (Context Optimized with Prompt, Experience, and Replay) framework:

### Per-Map Coaching (7 maps + general, x 2 versions)

Each topic has two versions:
- `{map}_coaching.txt` — Raw coaching text (mostly short stubs)
- `{map}_coaching_ocr.txt` — OCR-extracted variant (carries the bulk of the content)

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
- `hltv_sync_state.json` tracks scraper progress — empty `{}` means no active sync
- Knowledge files are the intellectual foundation of coaching — edit with care
- `dataset.csv` is currently an empty placeholder (bundled by the PyInstaller spec), not hand-edited
