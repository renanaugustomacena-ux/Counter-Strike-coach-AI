> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Test di Verifica e Forensi a Livello Root

Test di verifica e forensi a livello root per componenti critici del sistema.

## Scopo

Questi test verificano funzionalità end-to-end, integrità dei dati e comportamento dei sottosistemi critici utilizzando dati reali simili a quelli di produzione.

## File di Test Principali

- `conftest.py` — Fixture a livello root per test di verifica
- `verify_chronovisor_logic.py` — Verifica logica Chronovisor (rilevamento scala, deduplicazione)
- `verify_chronovisor_real.py` — Verifica Chronovisor con dati demo reali
- `verify_csv_ingestion.py` — Verifica pipeline ingestion CSV
- `verify_map_integration.py` — Verifica integrazione mappe e dati spaziali
- `verify_reporting.py` — Verifica pipeline reporting (generazione PDF, visualizzazioni)
- `verify_superposition.py` — Verifica rete superposition
- `setup_golden_data.py` — Configurazione dati golden per test di regressione

## Filosofia di Test

- **Approccio forense** — I test investigano percorsi dati reali e comportamento effettivo del sistema
- **Nessun dato sintetico** — Tutti i test usano file demo reali o dati equivalenti a produzione
- **Skip se non disponibile** — I test saltano correttamente se i dati richiesti mancano
- **Copertura end-to-end** — Focus su punti di integrazione e workflow cross-modulo

## Esecuzione Test di Verifica

```bash
# Esegui tutti i test di verifica
python -m pytest tests/ -v

# Esegui verifica specifica
python tests/verify_chronovisor_real.py

# Configura dati golden per test di regressione
python tests/setup_golden_data.py
```

## Note

Questi test complementano la suite di test principale in `Programma_CS2_RENAN/tests/` con verifica di livello superiore orientata all'integrazione.
