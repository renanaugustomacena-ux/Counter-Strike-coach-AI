> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Data — Dati Applicazione & Configurazione

> **Autorità:** Regola 4 (Persistenza Dati)

Questa directory contiene dati runtime, file di configurazione, conoscenza di coaching, input di dati statistici esterni e l'area di staging per l'ingestione delle demo. Tutti i file qui presenti sono dati lato utente (non codice).

## Struttura della Directory

```
data/
├── demos/                           # Staging file demo
│   └── pro_ingest/                 # Demo di partite professionistiche per il training
├── docs/                            # Documentazione di aiuto in-app
│   ├── features.md                 # Lista funzionalità di coaching
│   ├── getting_started.md          # Guida alla configurazione utente (regola 10/10)
│   └── troubleshooting.md         # Problemi comuni
├── external/                        # Input di dati esterni
│   └── hltv_stats_urls.txt         # URL giocatori HLTV (lista input storica)
├── knowledge/                       # Base di conoscenza RAG per il coaching
│   ├── {map}_coaching.txt          # Testo di coaching per mappa (7 mappe)
│   ├── {map}_coaching_ocr.txt      # Varianti estratte tramite OCR
│   ├── general_coaching.txt        # Principi generali di coaching CS2 (+ variante OCR)
│   ├── coaching_knowledge_base.json # KB strutturata (JSON, + variante OCR)
│   └── extraction_summary.json     # Metadati estrazione conoscenza
├── dataset.csv                      # Placeholder dataset di training (attualmente vuoto)
├── map_config.json                  # Configurazione spaziale mappe (260 linee)
├── map_tensors.json                 # Definizioni coordinate tensore 3D
└── hltv_sync_state.json            # Stato sincronizzazione scraper HLTV
```

## File di Configurazione Principali

### `map_config.json` (260 linee)

Definizioni spaziali per tutte le mappe competitive di CS2. Le voci delle mappe
risiedono sotto la chiave top-level `maps` (accanto a `_description`, `_source`,
`_last_updated` e `competitive_pool`):

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

- Utilizzato da `core/spatial_data.py` per le trasformazioni di coordinate
- Le mappe multi-livello (Nuke, Vertigo) includono confini `z_cutoff` e `levels`
- Pool competitivo: nuke, inferno, mirage, dust2, ancient, overpass, vertigo, anubis, train

### `map_tensors.json`

Coordinate tensore 3D per il training ML (7 mappe: mirage, inferno, dust2, nuke,
overpass, ancient, anubis):
- `image_file` riferimento radar per mappa
- Posizioni bombsite (A/B) con X, Y, Z
- Posizioni spawn (T/CT)
- Zone di controllo mid e zone importanti (connector, jungle, palace, ecc.)

## `demos/pro_ingest/`

Placeholder lato repository per file `.dem` di partite professionistiche, mantenuto
per test dev-scale locali (`tests/test_demo_parser.py` salta quando è vuoto).

- Attualmente tracciato tramite `.gitkeep` (vuoto nel repository)
- La directory di ingestione pro a runtime è configurata dall'utente: l'impostazione
  `PRO_DEMO_PATH` quando impostata, altrimenti `pro_ingest/` sotto la root di storage
  (`backend/storage/storage_manager.py`)
- Il corpus completo di demo pro e il database di training monolite risiedono su un
  volume esterno, non in questo repository (vedi `docs/OPEN_ISSUES.md` §2)
- I file vengono elaborati da `backend/data_sources/demo_parser.py`

## `external/` — Input di Dati Esterni

Attualmente contiene un singolo file:

| File | Contenuto | Utilizzato Da |
|------|-----------|---------------|
| `hltv_stats_urls.txt` | URL profili giocatori HLTV | Nessun consumatore di codice attivo (lista input di un helper di fetch rimosso; mantenuto come dato) |

I dataset CSV di terze parti (statistiche giocatori, statistiche mappe, esiti round)
non sono mantenuti nel repository; `backend/processing/external_analytics.py` li legge
da qui quando presenti, e l'ingestor di tornei JSON
(`ingestion/pipelines/json_tournament_ingestor.py`) scrive il suo CSV di output qui
(`tournament_advanced_stats.csv`) quando eseguito.

## `knowledge/` — Base di Conoscenza RAG

File di conoscenza per il coaching nel framework COPER (Context Optimized with Prompt, Experience, and Replay):

### Coaching per Mappa (7 mappe + generale, x 2 versioni)

Ogni argomento ha due versioni:
- `{map}_coaching.txt` — Testo di coaching grezzo (per lo più brevi bozze)
- `{map}_coaching_ocr.txt` — Variante estratta tramite OCR (contiene il grosso del contenuto)

Mappe coperte: Ancient, Anubis, Dust2, Inferno, Mirage, Nuke, Overpass + generale

### Base di Conoscenza Strutturata

- `coaching_knowledge_base.json` — KB strutturata con sezioni per tattiche, posizioni, utility e callout
- `coaching_knowledge_base_ocr.json` — Variante OCR
- `extraction_summary.json` — Metadati sull'estrazione della conoscenza (timestamp, versioni)

### Come Viene Utilizzata la Conoscenza

Questi file sono il materiale sorgente grezzo della conoscenza di coaching. La base
di conoscenza RAG a runtime viene popolata da `backend/knowledge/book/index.json`
(Coach Book, con `backend/knowledge/tactical_knowledge.json` come fallback legacy)
nella tabella database `tacticalknowledge` da `backend/knowledge/init_knowledge_base.py`;
l'unico consumatore automatizzato di `data/knowledge/` stesso è un controllo strutturale
in `tools/headless_validator.py`.

```
Tabella DB tacticalknowledge (popolata da init_knowledge_base.py)
    │
    └── backend/knowledge/rag_knowledge.py (KnowledgeEmbedder)
            │
            ├── Sentence-BERT genera embedding dei chunk di testo (vettori 384-dim)
            └── Indice FAISS quando disponibile (fallback coseno brute-force)
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
- `hltv_sync_state.json` traccia lo stato di sincronizzazione HLTV — un `{}` vuoto significa
  nessuna sincronizzazione attiva (attualmente azzerato solo da `tools/reset_pro_data.py`)
- I file di conoscenza sono la base intellettuale del coaching — modificare con cura
- `dataset.csv` è attualmente un placeholder vuoto (incluso dallo spec PyInstaller), non modificato manualmente
- Lo spec PyInstaller include anche `map_config.json`, `external/` e `docs/` da qui
