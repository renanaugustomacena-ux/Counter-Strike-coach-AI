# Registro File Demo & Gestione Lifecycle

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Panoramica

Tracking registro file demo e gestione stati lifecycle. Previene ingestion duplicata, traccia stato elaborazione e fornisce audit trail per tutte le operazioni file demo.

## Componenti Chiave

### `registry.py`
- **Registrazione file demo** — Registra tutti i file demo scoperti nella tabella `DemoFileRecord`
- **Rilevamento duplicati** — Verifica hash file previene elaborazione ridondante
- **Tracking metadati** — Dimensione file, timestamp discovery, tipo sorgente (user/pro/tournament)
- **Interfaccia query** — Recupera file per stato, sorgente, intervallo date

### `lifecycle.py`
- **Implementazione macchina stati** — Gestisce lifecycle elaborazione demo
- **Stati**: `discovered` → `queued` → `processing` → `completed` | `failed`
- **Transizioni stato atomiche** — Transazioni database garantiscono consistenza
- **Gestione stato errore** — File falliti marcati con codice errore e contatore retry

## Stati Lifecycle

1. **Discovered** — File trovato durante scansione directory, non ancora validato
2. **Queued** — Validato e pronto per ingestion, in attesa slot elaborazione
3. **Processing** — Attualmente in parsing e ingestion
4. **Completed** — Ingestion riuscita, tutti i dati derivati persistiti
5. **Failed** — Ingestion fallita, errore loggato, marcato per revisione manuale

## Integrazione

Usato da tutte le pipeline ingestion (`user_ingest.py`, `pro_ingest.py`, `json_tournament_ingestor.py`) per:
- Verificare se file già elaborato prima di iniziare ingestion
- Aggiornare stato elaborazione in tempo reale
- Marcare completamento o fallimento con contesto errore dettagliato

## Query Registro

- `get_pending_files()` — Restituisce tutti i file in stato `discovered` o `queued`
- `get_failed_files()` — Restituisce file con ingestion fallita con dettagli errore
- `get_completed_files(source_type, date_range)` — Recupera file elaborati con successo per criteri filtro

## Gestione Errori

Ingestion fallite incrementano contatore retry. Dopo 3 fallimenti, file è marcato come permanentemente fallito e richiede intervento manuale. Tutti gli errori loggati con ID correlazione per tracciabilità.

## Schema Database

Tabella `DemoFileRecord` include:
- `file_path`, `file_hash`, `file_size`, `source_type`
- `lifecycle_state`, `error_code`, `retry_count`
- `discovered_at`, `queued_at`, `processing_started_at`, `completed_at`
