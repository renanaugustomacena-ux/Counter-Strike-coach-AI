> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Data — Dati Applicazione & Configurazione

> **Autorità:** Regola 4 (Persistenza Dati)

Questa directory contiene dati runtime, file di configurazione, conoscenza di coaching, dataset statistici esterni e l'area di staging per l'ingestione delle demo. Tutti i file qui presenti sono dati lato utente (non codice).

## Struttura della Directory

```
data/
├── demos/                           # Staging file demo
│   └── pro_ingest/                 # Demo di partite professionistiche per il training
├── docs/                            # Documentazione di aiuto in-app
│   ├── features.md                 # Lista funzionalità di coaching
│   ├── getting_started.md          # Guida alla configurazione utente (regola 10/10)
│   └── troubleshooting.md         # Problemi comuni
├── external/                        # Dataset statistici di terze parti (CSV)
│   ├── all_Time_best_Players_Stats.csv
│   ├── cs2_playstyle_roles_2024.csv
│   ├── csgo_games.csv
│   ├── Maps01_BombPlantOutcomes01.csv
│   ├── Maps01_RoundOutcomes.csv
│   ├── Maps02_BombPlantOutcomes.csv
│   ├── maps_statistics.csv
│   ├── top_100_players.csv
│   ├── weapons_statistics.csv
│   └── hltv_stats_urls.txt         # URL giocatori HLTV per lo scraper
├── knowledge/                       # Base di conoscenza RAG per il coaching
│   ├── {map}_coaching.txt          # Testo di coaching per mappa (8 mappe)
│   ├── {map}_coaching_ocr.txt      # Varianti estratte tramite OCR
│   ├── general_coaching.txt        # Principi generali di coaching CS2
│   ├── coaching_knowledge_base.json # KB strutturata (JSON)
│   └── extraction_summary.json     # Metadati estrazione conoscenza
├── dataset.csv                      # Dataset di training
├── map_config.json                  # Configurazione spaziale mappe (257 linee)
├── map_tensors.json                 # Definizioni coordinate tensore 3D
├── pro_baseline.csv                 # Statistiche baseline professionistiche
└── hltv_sync_state.json            # Stato sincronizzazione scraper HLTV
```

## File di Configurazione Principali

### `map_config.json` (257 linee)

Definizioni spaziali per tutte le mappe competitive di CS2:

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

- Utilizzato da `core/spatial_data.py` per le trasformazioni di coordinate
- Le mappe multi-livello (Nuke, Vertigo) includono confini `z_cutoff`
- Pool competitivo: nuke, inferno, mirage, dust2, ancient, overpass, vertigo, anubis, train

### `map_tensors.json`

Coordinate tensore 3D per il training ML:
- Posizioni bombsite (A/B) con X, Y, Z
- Posizioni spawn (T/CT)
- Zone di controllo mid e zone importanti (connector, jungle, palace, ecc.)

## `demos/pro_ingest/`

Directory di staging per i file `.dem` di partite professionistiche. La pipeline di ingestione preleva i file da qui per il training della baseline professionale.

- Attualmente tracciato tramite `.gitkeep` (vuoto nel repository)
- Produzione: ~200 file demo professionistici sull'SSD esterno
- I file vengono elaborati da `backend/data_sources/demo_parser.py`

## `external/` — Dataset Statistici

Dati CSV di terze parti utilizzati per analisi di riferimento e calibrazione del coaching:

| File | Contenuto | Utilizzato Da |
|------|-----------|---------------|
| `top_100_players.csv` | Statistiche top 100 giocatori HLTV | `processing/external_analytics.py` |
| `all_Time_best_Players_Stats.csv` | Statistiche storiche migliori giocatori | Riferimento baseline professionale |
| `cs2_playstyle_roles_2024.csv` | Dati classificazione ruoli (2024) | `backend/ingestion/csv_migrator.py` |
| `maps_statistics.csv` | Percentuali vittorie e giocabilità mappe | Analisi contesto mappe |
| `weapons_statistics.csv` | Dati danno/precisione armi | Feature classi armi |
| `Maps01_RoundOutcomes.csv` | Distribuzioni esiti round | Training probabilità vittoria |
| `Maps01_BombPlantOutcomes01.csv` | Dati esiti piazzamento bomba | Analisi economia |
| `csgo_games.csv` | Dati storici partite CS:GO | Riferimento legacy |
| `hltv_stats_urls.txt` | URL profili giocatori HLTV | Input scraper HLTV |

## `knowledge/` — Base di Conoscenza RAG

File di conoscenza per il coaching nel framework COPER (Context Optimized with Prompt, Experience, Replay):

### Coaching per Mappa (8 mappe x 2 versioni)

Ogni mappa ha due versioni:
- `{map}_coaching.txt` — Testo di coaching grezzo
- `{map}_coaching_ocr.txt` — Variante estratta tramite OCR

Mappe coperte: Ancient, Anubis, Dust2, Inferno, Mirage, Nuke, Overpass + generale

### Base di Conoscenza Strutturata

- `coaching_knowledge_base.json` — KB strutturata con sezioni per tattiche, posizioni, utility e callout
- `coaching_knowledge_base_ocr.json` — Variante OCR
- `extraction_summary.json` — Metadati sull'estrazione della conoscenza (timestamp, versioni)

### Come Viene Utilizzata la Conoscenza

```
File knowledge/
    │
    └── backend/knowledge/rag_knowledge.py (KnowledgeEmbedder)
            │
            ├── Sentence-BERT genera embedding dei chunk di testo (vettori 384-dim)
            └── Indici FAISS per ricerca rapida per similarità
                    │
                    └── CoachingService recupera conoscenza rilevante per query
```

## `docs/` — Aiuto In-App

File Markdown serviti da `backend/knowledge_base/help_system.py`:

- `getting_started.md` — Guida alla configurazione, regola 10/10, velocità di ingestione, livelli di maturità dati
- `features.md` — Descrizione delle funzionalità
- `troubleshooting.md` — Problemi comuni e soluzioni

## Note di Sviluppo

- **NON committare file demo** (`.dem`) — sono da 50-200MB ciascuno
- Le coordinate di `map_config.json` provengono dai file di gioco CS2 (`resource/overviews/*.txt`)
- I CSV esterni sono dati di riferimento statici — aggiornarli manualmente quando nuovi dati sono disponibili
- `hltv_sync_state.json` traccia il progresso dello scraper — un `{}` vuoto significa nessuna sincronizzazione attiva
- I file di conoscenza sono la base intellettuale del coaching — modificare con cura
- `dataset.csv` e `pro_baseline.csv` sono generati dalla pipeline di training, non modificati manualmente
