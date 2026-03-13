# GitHub Actions - Configurazione CI/CD

> **[English](ABOUT_CICD.md)** | **[Italiano](ABOUT_CICD_IT.md)** | **[Português](ABOUT_CICD_PT.md)**

Questa directory contiene la pipeline CI/CD di GitHub Actions per il progetto Macena CS2 Analyzer.

## Panoramica della Pipeline

La pipeline viene eseguita ad **ogni push e pull request**, validando la qualita del codice su entrambe le piattaforme Linux e Windows. La build di distribuzione finale e destinata a Windows (dove si trovano i giocatori di CS2).

**File del workflow:** [`.github/workflows/build.yml`](workflows/build.yml)

## Stadi della Pipeline

```
lint ──┬── test (Ubuntu + Windows) ── integration (Ubuntu + Windows) ──┐
       │                                                                ├── build-distribution (Windows, solo main)
       ├── security ───────────────────────────────────────────────────┘
       └── type-check (informativo, non bloccante)
```

### Stadio 1: Lint & Controllo Formato
- **Runner:** Ubuntu
- Hook pre-commit, formattazione Black, ordinamento import isort

### Stadio 2: Test Unitari + Copertura
- **Runner:** Ubuntu + Windows (matrice)
- pytest con tracciamento della copertura (soglia 30%)
- Report di copertura caricati come artifact

### Stadio 3: Integrazione
- **Runner:** Ubuntu + Windows (matrice)
- Validatore headless (gate a 23 fasi)
- Controlli di coerenza cross-modulo (METADATA_DIM, PlayerRole)
- Test di portabilita
- Verifica del manifesto di integrita

### Stadio 4: Scansione Sicurezza
- **Runner:** Ubuntu (parallelo ai test)
- Bandit security linter (severita MEDIUM+)
- detect-secrets per credenziali hardcoded

### Stadio 4b: Controllo Tipi
- **Runner:** Ubuntu (informativo, non bloccante)
- Analisi statica dei tipi con mypy

### Stadio 5: Build di Distribuzione
- **Runner:** Windows (solo branch main, dopo il superamento di tutti i gate)
- Build eseguibile PyInstaller
- Audit di integrita post-build
- Upload artifact (ritenzione 30 giorni)

## Sicurezza della Supply Chain

Tutte le GitHub Actions sono **pinned tramite SHA** (non riferimento a tag) per prevenire attacchi alla supply chain:
- `actions/checkout` — pinnato a SHA v4
- `actions/setup-python` — pinnato a SHA v5
- `actions/upload-artifact` — pinnato a SHA v4

## Strategia Cross-Platform

| Piattaforma | Dipendenze | Scopo |
|-------------|-----------|-------|
| Linux | `requirements.txt` + indice CPU PyTorch | Sviluppo + validazione CI |
| Windows | `requirements-ci.txt` (file di lock) | Build riproducibili + distribuzione |

## Documentazione

- **[CICD_GUIDE.md](CICD_GUIDE.md)** — Guida dettagliata della pipeline con test locali, risoluzione problemi e trigger dei workflow
