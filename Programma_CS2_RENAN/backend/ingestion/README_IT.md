> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Backend Ingestion — Monitoraggio File, Governance Risorse & Migrazione CSV

> **Autorità:** Regola 2 (Sovranità Backend), Regola 4 (Persistenza Dati)
> **Skill:** `/resilience-check`, `/data-lifecycle-review`

Questo modulo gestisce il livello di ingestion a runtime: monitoraggio di nuovi file demo su disco, governance delle risorse di sistema durante l'elaborazione in background e migrazione di dataset CSV esterni nel database.

**Nota:** Questo è distinto dalla directory di primo livello `Programma_CS2_RENAN/ingestion/`, che gestisce l'orchestrazione della pipeline multi-stadio. Questo modulo fornisce i componenti di basso livello.

## Inventario File

| File | Linee | Scopo | Classi/Funzioni Principali |
|------|-------|-------|---------------------------|
| `watcher.py` | ~150 | Monitor del filesystem per file `.dem` | `DemoFileHandler(FileSystemEventHandler)` |
| `resource_manager.py` | ~120 | Throttling CPU/RAM per task in background | `ResourceManager` |
| `csv_migrator.py` | ~100 | Importazione CSV esterna in tabelle SQLModel | `CSVMigrator` |

## `watcher.py` — Monitor File Demo

Utilizza [watchdog](https://github.com/gorakhargosh/watchdog) per osservare le directory configurate alla ricerca di nuovi file `.dem`.

### Come Funziona

```
Nuovo file .dem rilevato (on_created / on_moved)
        │
        ├── Pianifica controllo di stabilità (intervallo 1s)
        │       │
        │       ├── Dimensione file invariata per 2 controlli consecutivi? ──> Stabile
        │       │       │
        │       │       └── Accoda come IngestionTask nel database
        │       │
        │       └── Ancora in modifica? ──> Ricontrolla (max 120 tentativi / ~30s)
        │
        └── Valida dimensione minima (MIN_DEMO_SIZE da demo_format_adapter.py)
```

- **Debouncing di stabilità:** Previene la lettura di file scritti parzialmente (Steam scrive le demo in modo progressivo)
- **Prevenzione duplicati:** Controlla se il file esiste già nella tabella `IngestionTask` prima di accodarlo
- **Distinzione Pro/Utente:** Monitora sia le cartelle demo utente (`is_pro_folder=False`) che le cartelle demo professionistiche (`is_pro_folder=True`)

## `resource_manager.py` — Throttling Carico di Sistema

Impedisce al daemon Digester di consumare troppe risorse di sistema durante il parsing in background.

### Soglie di Isteresi

```
Utilizzo CPU (media mobile di 10 secondi su 10 campioni):

  100% ┬───────────────────────────────────
       │        THROTTLE ATTIVO
   85% ├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   ← Avvio throttling
       │
   70% ├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─   ← Arresto throttling
       │        OPERAZIONE NORMALE
    0% ┴───────────────────────────────────
```

- **Isteresi** previene il toggling rapido on/off vicino alla soglia
- **Smoothing:** 10 campioni CPU a intervalli di 1 secondo → media mobile
- **Override:** Impostare la variabile d'ambiente `HP_MODE=1` per disabilitare il throttling (modalità Turbo)
- **Thread-safe:** Lock separati per campioni CPU e stato di throttle

## `csv_migrator.py` — Importazione Dati Esterni

Migra file CSV statistici esterni nelle tabelle del database SQLModel per le analitiche di coaching.

### Sorgenti Dati

| File CSV | Tabella Destinazione | Contenuto |
|----------|---------------------|-----------|
| `data/external/cs2_playstyle_roles_2024.csv` | `Ext_PlayerPlaystyle` | Probabilità di ruolo per giocatore |
| CSV statistiche tornei | `Ext_TeamRoundStats` | Statistiche round a livello di torneo |

- **Idempotente:** Sicuro da rieseguire (controlla i dati esistenti)
- **Encoding:** UTF-8 con gestione BOM
- **Parsing sicuro:** `_safe_float()` e `_safe_int()` prevengono la propagazione di NaN

## Integrazione

```
                    watcher.py
                        │
                        ├── Accoda IngestionTask nel database
                        │
                        └── control/ingest_manager.py preleva i task
                                │
                                ├── resource_manager.should_throttle()?
                                │       SÌ → sleep prima del prossimo batch
                                │       NO  → elabora immediatamente
                                │
                                └── data_sources/demo_parser.py analizza il file .dem
```

## Note di Sviluppo

- `watcher.py` richiede il pacchetto `watchdog` (`pip install watchdog`)
- `ResourceManager` è una classe di utilità statica — non necessita di istanziazione
- `CSVMigrator` estende `DatabaseManager` per l'accesso alle sessioni
- La variabile d'ambiente `HP_MODE` è solo per sviluppo/benchmarking — non per uso in produzione
- Il controllo di stabilità dei file usa il polling di `os.path.getsize()`, non lock del filesystem
