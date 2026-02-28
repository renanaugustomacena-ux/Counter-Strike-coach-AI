# GitHub Actions - Configurazione CI/CD

> **[English](ABOUT_CICD.md)** | **[Italiano](ABOUT_CICD_IT.md)** | **[Português](ABOUT_CICD_PT.md)**

Questa directory contiene i workflow di GitHub Actions e le configurazioni di automazione per il progetto Macena CS2 Analyzer.

## Workflow

La directory `.github/workflows/` contiene le pipeline CI/CD automatizzate:

### CI/CD Principale
- **[build.yml](workflows/build.yml)** — Pipeline di verifica build
  Eseguita ad ogni push e pull request per validare la qualità del codice:
  - Controlli di linting e stile del codice (flake8, black)
  - Esecuzione di test unitari e di integrazione (pytest)
  - Scansione vulnerabilità di sicurezza (bandit, safety)
  - Verifica delle dipendenze
  - Generazione degli artifact di build

### Automazione Gemini AI
- **[gemini-dispatch.yml](workflows/gemini-dispatch.yml)** — Workflow di dispatch Gemini AI
  Dispatcher centralizzato per instradare i task Gemini AI ai gestori appropriati

- **[gemini-invoke.yml](workflows/gemini-invoke.yml)** — Invocazione comandi Gemini
  Esegue comandi Gemini AI per generazione automatica del codice e refactoring

- **[gemini-review.yml](workflows/gemini-review.yml)** — Revisione del codice basata su AI
  Revisione automatica del codice usando Gemini per le pull request, verifica:
  - Qualità del codice e aderenza ai principi ingegneristici
  - Vulnerabilità di sicurezza e anti-pattern
  - Completezza della documentazione
  - Requisiti di copertura dei test

- **[gemini-triage.yml](workflows/gemini-triage.yml)** — Automazione triage issue
  Categorizza, etichetta e prioritizza automaticamente le issue di GitHub usando Gemini AI

- **[gemini-scheduled-triage.yml](workflows/gemini-scheduled-triage.yml)** — Triage issue pianificato
  Esegue triage periodico sulle issue aperte per mantenere l'igiene del progetto

## Configurazione Comandi

La directory `.github/commands/` contiene file di configurazione TOML per i workflow Gemini AI:

- **[gemini-invoke.toml](commands/gemini-invoke.toml)** — Configurazione comando invoke
- **[gemini-review.toml](commands/gemini-review.toml)** — Configurazione comando review
- **[gemini-triage.toml](commands/gemini-triage.toml)** — Configurazione comando triage
- **[gemini-scheduled-triage.toml](commands/gemini-scheduled-triage.toml)** — Configurazione triage pianificato

## Documentazione

- **[CICD_GUIDE.md](CICD_GUIDE.md)** — Documentazione completa della pipeline CI/CD
  Guida dettagliata che copre trigger dei workflow, configurazione dell'ambiente, gestione dei segreti e risoluzione dei problemi

## Utilizzo

I workflow vengono attivati automaticamente dagli eventi del repository (push, pull request, creazione issue). Il dispatch manuale dei workflow è disponibile tramite l'interfaccia GitHub Actions per test e debug.

Per informazioni dettagliate su ciascun workflow e opzioni di configurazione, consulta **[CICD_GUIDE.md](CICD_GUIDE.md)**.
