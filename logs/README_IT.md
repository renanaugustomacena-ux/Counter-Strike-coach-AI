> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Log di Sistema Centralizzati

Questa directory raccoglie i log di runtime dal tooling operatore alla root del repo (l'operatore Goliath, la console sviluppatore, gli strumenti di manutenzione) e funge da sink di fallback per lo stack di logging del backend. L'applicazione stessa risolve la propria directory di log dalla configurazione (`LOG_DIR = <USER_DATA_ROOT>/logs`, default `Programma_CS2_RENAN/logs`, sovrascrivibile tramite `BRAIN_DATA_ROOT` / `CUSTOM_STORAGE_PATH`), quindi il `cs2_analyzer.log` primario normalmente finisce la, non qui.

## Panoramica Tecnica

L'architettura di logging e progettata per il monitoraggio ad alta granularita del backend del coach di Counter-Strike. Il logging e configurato da `Programma_CS2_RENAN/observability/logger_setup.py`: tutti i logger condividono un singolo sink `cs2_analyzer.log` (output JSON strutturato, analizzabile da macchina), e le esecuzioni di tool standalone scrivono inoltre log JSON con timestamp sotto `tools/`. `core/config.py` collega il `LOG_DIR` risolto in `logger_setup` tramite `configure_log_dir()`; gli script che usano `logger_setup` senza quel collegamento ricadono sul percorso relativo `logs/` — questa directory, quando eseguiti dalla root del repo. L'obiettivo principale e garantire che i colli di bottiglia delle prestazioni, i fallimenti di ingestione e le deviazioni dei modelli siano identificati e risolti rapidamente.

## Componenti Chiave

Tutti i file sottostanti sono generati a runtime e gitignored (solo i README sono tracciati):

- **`cs2_analyzer.log`**: Copia di fallback del log principale backend/analisi (righe JSON: errori con stack trace, eventi di parsing e ingestione per demo). La copia primaria risiede in `<USER_DATA_ROOT>/logs/`.
- **`tools/`**: Log JSON per-tool delle esecuzioni (`<nome_tool>_<YYYYMMDD_HHMMSS>.json`) da `get_tool_logger()`, creati quando i tool CLI (es. `tools/build_pipeline.py`) vengono eseguiti dalla root del repo.
- **`goliath_master_<YYYYMMDD>.json`**: Log master giornaliero dell'operatore Goliath (`goliath.py`), appeso tra le esecuzioni.
- **`spawn_<tool>_<HHMMSS>.log`**: stderr dei tool in background lanciati tramite il comando `svc spawn` della console (`console.py`).
- **`wipe_audit_<YYYYMMDD>.jsonl`**: Trail di audit append-only scritto da `tools/wipe_for_reingest_safe.py` per ogni operazione di wipe/restore.

## Struttura della Directory

```text
logs/
├── cs2_analyzer.log              # Log fallback backend/analisi (generato a runtime)
├── tools/                        # Log JSON con timestamp delle esecuzioni tool (generati)
├── goliath_master_<date>.json    # Log master giornaliero operatore Goliath (generato)
├── spawn_<tool>_<time>.log       # stderr dei tool in background lanciati dalla console (generati)
├── wipe_audit_<date>.jsonl       # Trail di audit wipe/restore (generato)
├── README.md                     # Questa documentazione
├── README_IT.md                  # Versione Italiana
└── README_PT.md                  # Versione Portoghese
```

## Utilizzo

### Monitoraggio in Tempo Reale
Per monitorare i log di sistema in tempo reale durante una sessione di ingestione o addestramento su larga scala:
```bash
tail -f logs/cs2_analyzer.log
```

### Rotazione dei Log
Un `RotatingFileHandler` ruota `cs2_analyzer.log` a 5 MB, mantenendo 3 versioni storiche (es. `cs2_analyzer.log.1`) per prevenire l'esaurimento dello spazio su disco. Se l'handler non puo essere creato (PermissionError), il setup ricade su un `FileHandler` semplice (nessuna rotazione). Ogni processo scrive il proprio file di log (indicizzato sulla variabile d'ambiente `CS2_LOG_ROLE`), quindi ogni rotating handler ha un singolo writer. Gli altri file qui (`goliath_master_*`, `spawn_*`, `wipe_audit_*`) non sono ruotati; `configure_retention()` in `logger_setup.py` puo eliminare file `.log`/`.json` piu vecchi di 30 giorni.

### Filtrare per Errori
Per identificare rapidamente problemi critici all'interno dei log:
```bash
grep "ERROR" logs/cs2_analyzer.log
```
