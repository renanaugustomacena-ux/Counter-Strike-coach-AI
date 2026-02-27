# Baseline Professionali & Rilevamento Meta Drift

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Panoramica

Questo modulo fornisce baseline di giocatori professionisti, soglie di classificazione ruoli, rilevamento di drift del meta-gioco e risoluzione fuzzy dei nickname. Abilita il decadimento temporale delle statistiche professionali e le soglie di ruolo apprese e persistite nel database.

## Componenti Chiave

### `pro_baseline.py`
- **`get_pro_baseline()`** — Recupera statistiche di giocatori professionisti con ponderazione di decadimento temporale
- **`calculate_deviations()`** — Calcola le deviazioni delle prestazioni utente dalla baseline pro
- **`TemporalBaselineDecay`** — Modello di decadimento esponenziale per statistiche professionali invecchiate (default λ=0.0001/giorno)

### `role_thresholds.py`
- **`RoleThresholdStore`** — Archiviazione in memoria per soglie di classificazione ruoli apprese
- **`LearnedThreshold`** — Dataclass per soglie statistiche per ruolo (entry, support, lurk, AWP, IGL)
- **`persist_to_db()` / `load_from_db()`** — Persistenza su database per soglie apprese

### `meta_drift.py`
- **`MetaDriftEngine`** — Rileva cambiamenti nei pattern del meta-gioco professionale (uso armi, meta utility, tendenze controllo mappa)

### `nickname_resolver.py`
- **`NicknameResolver`** — Matching fuzzy per nickname di giocatori professionisti (gestisce leet-speak, abbreviazioni, alias)

## Integrazione

Utilizzato da `CoachingService` per arricchimento baseline temporale, daemon `Teacher` per rilevamento meta-shift dopo riaddestramento e `NeuralRoleHead` per apprendimento soglie classificazione ruoli.

## Fonti Dati

Baseline professionali provenienti da tabelle `ProPlayer` e `MatchResult` tramite pipeline scraping HLTV.
