# Implementazioni Pipeline Ingestion

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Panoramica

Pipeline ingestion file demo per diverse fonti dati: demo utente, demo professionali e file JSON tornei. Tutte le pipeline ora includono arricchimento statistico a livello round tramite `round_stats_builder.py`.

## Pipeline Chiave

### `user_ingest.py`
- **`ingest_user_demos()`** — Pipeline elaborazione file demo utente
- Analizza file `.dem` dalla directory Steam CS2 dell'utente
- Estrae eventi tick-level, stati giocatori, risultati round
- **Arricchimento statistiche round**: Chiama `aggregate_round_stats_to_match()` + `enrich_from_demo()`
- Persiste su tabelle `PlayerMatchStats` (aggregato) e `RoundStats` (per-round)
- Crea database SQLite per-match tramite `MatchDataManager`

### `pro_ingest.py`
- **`ingest_pro_demos()`** — Pipeline elaborazione demo professionali
- Sorgenti demo da directory `PRO_DEMO_PATH`
- Arricchimento metadati HLTV tramite `HLTVApiService` (nomi giocatori, composizioni team, contesto torneo)
- **Arricchimento statistiche round**: Come pipeline utente — `enrich_from_demo()` popola `RoundStats`
- Popola tabelle `ProPlayer`, `MatchResult`, `TeamComposition`
- Genera record conoscenza tattica per retrieval RAG

### `json_tournament_ingestor.py`
- **`process_tournament_jsons()`** — Ingestion file JSON tornei
- Elabora export JSON strutturati da database tornei
- Valida schema, estrae metadati match, statistiche giocatori, timeline round
- Insert batch con confini transazionali
- Usato per import dati storici e analisi tornei offline

## Pattern Comuni

Tutte le pipeline seguono questo flusso:
1. **Discovery**: Scansione directory sorgente per file non elaborati
2. **Validation**: Verifica integrità file, formato, schema
3. **Parsing**: Estrazione dati strutturati tramite parser demo
4. **Enrichment**: Statistiche round, metadati HLTV, dati spaziali
5. **Persistence**: Scritture DB atomiche con rollback su errore
6. **Registration**: Marcatura file come elaborato nel registro `DemoFileRecord`

## Integrazione Round Stats (2026-02-16)

Fase 1 del Fusion Plan ha connesso la pipeline aggregazione:
- `round_stats_builder.py` ora chiamato da ingestion utente e pro
- Rating HLTV 2.0 per-round, kill noscope, kill blind, assist flash tutti persistiti
- Tabella `RoundStats` estesa con nuovi campi
- Costruzione timeline momentum ora usa `RoundStats.compute_round_rating()`

## Gestione Errori

Fallimenti ingestion sono loggati con ID correlazione. Ingestion parziale viene rollbackata. File falliti sono marcati con stato errore nel registro per revisione manuale.
