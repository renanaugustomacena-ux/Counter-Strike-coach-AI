# Observability & Protezione Runtime

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Panoramica

Auto-protezione runtime applicazione (RASP), logging strutturato con ID correlazione e tracking errori Sentry con scrubbing PII. Fornisce observability completa per debugging, audit sicurezza e monitoraggio produzione.

## Componenti Chiave

### `rasp.py`
- **`RASPGuard`** — Verifica integrità runtime tramite controllo hash file
- **`run_rasp_audit()`** — Scansiona file sorgente Python e confronta con manifest integrità
- **`IntegrityError`** — Eccezione custom sollevata quando rilevato mismatch hash
- Rileva modifiche codice non autorizzate, attacchi supply chain e corruzione file
- Risultati audit loggati con livelli severità (CRITICAL, ERROR, WARNING)

### `logger_setup.py`
- **`get_logger(name)`** — Factory function per logger strutturati
- Iniezione ID correlazione per tracing richieste tra moduli
- Output log formattato JSON per parsing macchina
- Filtraggio livello log per namespace modulo
- Redazione automatica campi sensibili (PII, secrets, token)
- Rotazione file con compressione e policy retention

### `sentry_setup.py`
- **`init_sentry()`** — Inizializza SDK Sentry con DSN specifico ambiente
- **`add_breadcrumb()`** — Logging breadcrumb contestuale per report errori
- **Scrubbing PII** — Rimozione automatica dati sensibili da stack trace
- Monitoraggio performance con campionamento transazioni
- Tagging release per tracking versioni
- Separazione ambienti (development/staging/production)

## Pattern Logging Strutturato

```python
from observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.mymodule")
logger.info("Processing match", extra={"match_id": 12345, "map": "de_dust2"})
logger.error("Ingestion failed", extra={"file": "demo.dem", "error_code": "PARSE_ERROR"})
```

## Integrazione Audit RASP

Audit RASP eseguito:
- All'avvio applicazione (se `config.ENABLE_RASP=True`)
- Via CLI: `python macena.py sys rasp-audit`
- In pipeline CI/CD tramite controlli sicurezza `Goliath_Hospital.py`

## Integrazione Sentry

Configurazione tracking errori:
- `SENTRY_DSN` caricato da variabile ambiente
- Sample rate: 100% in development, 10% in production
- Traces sample rate: 10% per monitoraggio performance
- Scrubbing PII tramite hook `before_send`

## ID Correlazione

Tutte le voci log includono `correlation_id` per tracing richieste. Generato ai punti ingresso ingestion/analisi/coaching e propagato attraverso catena chiamate.

## Retention Log

- Development: 7 giorni
- Production: 90 giorni
- Errori critici: retention permanente in Sentry
