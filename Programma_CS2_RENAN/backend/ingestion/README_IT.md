> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Backend Ingestion — Monitoraggio File, Governance Risorse & Migrazione CSV

> **Autorità:** Regola 2 (Sovranità Backend), Regola 4 (Persistenza Dati)

Questo modulo gestisce il livello di ingestion a runtime: monitoraggio di nuovi file demo su disco, governance delle risorse di sistema durante l'elaborazione in background e migrazione di dataset CSV esterni nel database.

Nota: Distinto dalla directory ingestion/ di primo livello che gestisce l'orchestrazione della pipeline multi-stadio. Questo modulo fornisce i componenti di basso livello.

## File

| File | Scopo | Classi Principali |
|------|-------|-------------------|
| `watcher.py` | Monitor del filesystem per file .dem | `DemoFileHandler` |
| `resource_manager.py` | Throttling CPU/RAM per task in background | `ResourceManager` |
| `csv_migrator.py` | Importazione CSV esterna in tabelle SQLModel | `CSVMigrator` |

## watcher.py — Monitor File Demo

Utilizza watchdog per osservare le directory alla ricerca di nuovi file .dem. Il debouncing di stabilità previene la lettura di file scritti parzialmente. Prevenzione duplicati tramite controllo della tabella IngestionTask.

## resource_manager.py — Throttling Carico di Sistema

Throttling CPU basato su isteresi: avvio all'85%, arresto al 70%. Media mobile di 10 secondi. HP_MODE=1 per disabilitare il throttling.

## csv_migrator.py — Importazione Dati Esterni

Migra file CSV esterni nelle tabelle del database SQLModel. Idempotente, gestione UTF-8 con BOM, parsing sicuro.

## Note di Sviluppo

- watcher.py richiede il pacchetto watchdog
- ResourceManager è una classe di utilità statica
- La variabile d'ambiente HP_MODE è solo per lo sviluppo
