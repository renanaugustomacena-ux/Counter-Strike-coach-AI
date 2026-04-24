> **[English](OVERVIEW.md)** | **[Italiano](OVERVIEW_IT.md)** | **[Portugues](OVERVIEW_PT.md)**

# .github — Pipeline CI/CD e Configurazione GitHub

> **Autorita:** Rule 7 (CI/CD & Release Engineering), Rule 5 (Security)

Questa directory contiene la pipeline CI/CD di GitHub Actions e la relativa documentazione. La pipeline garantisce qualita del codice, sicurezza e compatibilita multipiattaforma ad ogni push.

## Inventario File

| File | Scopo |
|------|-------|
| `workflows/build.yml` | Definizione pipeline CI/CD principale (383 righe) |
| `ABOUT_CICD.md` | Panoramica pipeline (Inglese) |
| `ABOUT_CICD_IT.md` | Panoramica pipeline (Italiano) |
| `ABOUT_CICD_PT.md` | Panoramica pipeline (Portoghese) |
| `CICD_GUIDE.md` | Guida tecnica dettagliata |
| `PIPELINE.md` | Documentazione architettura pipeline |
| `dependabot.yml` | Configurazione Dependabot per aggiornamento dipendenze |
| `pull_request_template.md` | Template PR |
| `ISSUE_TEMPLATE/bug_report.md` | Template issue segnalazione bug |
| `ISSUE_TEMPLATE/feature_request.md` | Template issue richiesta funzionalita |

## Architettura della Pipeline

Push / PR
    │
    ├── Fase 1: LINT (Ubuntu, ~1 min)
    │       └── pre-commit run --all-files
    │
    ├── Fase 2: TEST (matrice Ubuntu + Windows, ~3 min)
    │       └── pytest --cov-fail-under=33
    │
    ├── Fase 3: INTEGRATION (matrice Ubuntu + Windows, ~5 min)
    │       ├── headless_validator.py (gate a 24 fasi, 313 controlli)
    │       ├── Coerenza cross-modulo (METADATA_DIM == INPUT_DIM)
    │       ├── Test di portabilita
    │       └── Verifica manifesto di integrita
    │
    ├── Fase 4a: SECURITY (Ubuntu, ~2 min)
    │       ├── Bandit (SAST, severita MEDIUM+)
    │       ├── detect-secrets
    │       └── pip-audit (scansione CVE)
    │
    ├── Fase 4b: TYPE-CHECK (Ubuntu, non bloccante)
    │       └── mypy --ignore-missing-imports
    │
    └── Fase 5: BUILD-DISTRIBUTION (Windows, solo branch main, ~15 min)
            ├── Validazione file dati critici
            ├── Build PyInstaller
            ├── Audit post-build (audit_binaries.py)
            └── Upload artefatto (conservazione 30 giorni)

### Dipendenze tra Job

lint ──┬── test ──┬── integration ──┬── build-distribution (solo main)
       │          │                 │
       └── security ────────────────┘
       │
       └── type-check (non bloccante, informativo)

## Trigger

| Trigger | Branch | Percorsi Ignorati |
|---------|--------|-------------------|
| Push | `main`, `develop`, `feature/**`, `fix/**` | `*.md`, `docs/`, `.github/`, `LICENSE`, `.gitignore` |
| Pull Request | `main`, `develop` | Come sopra |

**Concorrenza:** Una pipeline per branch. Nuovi push annullano le esecuzioni in corso.

## Strategia Multipiattaforma

| Piattaforma | Dipendenze | PyTorch |
|-------------|------------|---------|
| Ubuntu | `requirements.txt` + librerie SDL2 | Solo CPU (pip index) |
| Windows | `requirements-ci.txt` (lock file) | Solo CPU (pip index) |

## Misure di Sicurezza

Tutte le GitHub Actions sono **fissate tramite SHA** (non riferite per tag) per prevenire attacchi alla supply-chain.

**Permessi:** Privilegio minimo (`contents: read`), sovrascritto per job se necessario.

## Validazione Locale

Prima di fare push, esegui questi comandi localmente per individuare problemi in anticipo:

```bash
# 1. Hook pre-commit (come Fase 1)
pre-commit run --all-files

# 2. Test (come Fase 2)
pytest Programma_CS2_RENAN/tests/ tests/ --cov=Programma_CS2_RENAN --cov-fail-under=33 -v

# 3. Validatore headless (come Fase 3)
python tools/headless_validator.py

# 4. Test di portabilita
python tools/portability_test.py
```

## Note di Sviluppo

- NON riferire le Actions per tag — usare sempre lo SHA completo per la sicurezza della supply-chain
- Il job `type-check` ha `continue-on-error: true` — informativo, non bloccante
- `build-distribution` viene eseguito solo sui push al branch `main`
- La versione Python e fissata a 3.10 in tutti i job
