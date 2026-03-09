> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Feature Engineering — Estrazione Features Unificata

Pipeline estrazione features unificata per training e inferenza con calcolo rating HLTV 2.0 e features role-specific.

## Moduli Principali

### Vettore Features Unificato
- **vectorizer.py** — `FeatureExtractor` — Vettore features unificato 25 dimensioni (METADATA_DIM=25) per tutti i modelli ML. Assicura rappresentazione features consistente tra training e inferenza. Estrae features per-tick: posizione (x, y, z), velocità, salute, armatura, statistiche arma, conteggi utility, stato economia, contesto round.

### Rating HLTV 2.0
- **rating.py** — `compute_hltv2_rating()`, `compute_impact_rating()`, `compute_survival_rating()` — Implementazione completa rating HLTV 2.0 con tre componenti:
  - Impact Rating: Kills/morti/assists pesati da moltiplicatori multi-kill
  - Survival Rating: Inverso morti per round con penalità
  - Integrazione KAST: Contributo percentuale Kill/Assist/Survive/Trade

### Calcolo KAST
- **kast.py** — `estimate_kast_from_stats()` — Calcolo percentuale KAST da statistiche round. KAST = percentuale round con Kill O Assist O Sopravvissuto O Scambiato.

### Features Base
- **base_features.py** — `HeuristicConfig`, `extract_match_stats()`, `load_learned_heuristics()` — Estrazione features euristiche con caricamento parametri appresi da training. Pesi features e soglie configurabili.

### Features Role-Specific
- **role_features.py** — Estrazione features role-specific per ruoli Entry Fragger, Lurker, Support, AWPer e IGL. Estrae metriche rilevanti ruolo (first kills, backstabs, utility assists, AWP kills, decision outcomes).

## Integrazione

FeatureExtractor usato da:
- Training RAP Coach (`backend/nn/rap_coach/trainer.py`)
- Training JEPA (`backend/nn/jepa_trainer.py`)
- Servizio coaching (`backend/services/coaching_service.py`)
- Orchestratore analisi (`backend/services/analysis_service.py`)

## Componenti Vettore Features (25-dim)
Posizione (3), velocità (3), salute/armatura (2), arma (5), utility (4), economia (3), contesto round (5).

## Dipendenze
NumPy, Pandas, SQLModel.
