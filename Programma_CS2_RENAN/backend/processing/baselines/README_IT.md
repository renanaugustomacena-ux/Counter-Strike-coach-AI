# Baseline Professionali & Rilevamento Meta-Drift

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autorevolezza:** `Programma_CS2_RENAN/backend/processing/baselines/`

## Introduzione

Questo pacchetto stabilisce il quadro di riferimento professionale rispetto al
quale ogni metrica di performance dell'utente viene valutata. Risponde alla
domanda *"come si confronta questo giocatore con i pro?"* mantenendo baseline
gaussiane (media + deviazione standard) derivate da statistiche HLTV reali,
rilevando quando il meta competitivo cambia abbastanza da invalidare tali
baseline, risolvendo i nickname delle demo in-game verso identita HLTV
canoniche e apprendendo soglie di classificazione ruoli da dati empirici
invece che da costanti hardcoded.

Il pacchetto e deliberatamente **read-heavy / write-rare**: le baseline e le
soglie vengono calcolate una volta (durante la sincronizzazione HLTV o dopo
l'ingestione delle demo) e poi consumate migliaia di volte dalla pipeline di
coaching.

## Inventario File

| File | Scopo | Export Principali |
|------|-------|-------------------|
| `pro_baseline.py` | Baseline gaussiane da record `ProPlayerStatCard` HLTV | `get_pro_baseline()`, `calculate_deviations()`, `get_pro_positions()`, `TemporalBaselineDecay` |
| `role_thresholds.py` | Soglie di classificazione ruoli apprese (con gestione cold-start) | `RoleThresholdStore`, `LearnedThreshold`, `get_role_threshold_store()` |
| `meta_drift.py` | Rileva drift statistico e spaziale nei pattern di gioco pro | `MetaDriftEngine` |
| `nickname_resolver.py` | Risoluzione fuzzy dei nomi giocatore delle demo verso ID HLTV | `NicknameResolver` |
| `__init__.py` | Marcatore pacchetto vuoto | -- |

## Architettura & Concetti

### Fallback Baseline a Tre Livelli (`pro_baseline.py`)

`get_pro_baseline()` risolve le baseline attraverso una catena di priorita rigorosa:

1. **Database** -- Aggrega righe `ProPlayerStatCard` da `hltv_metadata.db`
   in medie per giocatore, poi calcola media/deviazione standard globali.
   Supporta il filtraggio opzionale per `map_name` (Task 2.18.1) per
   coaching specifico per mappa.
2. **CSV** -- Ripiego su `data/external/all_Time_best_Players_Stats.csv`
   quando il database e vuoto. Mappa dinamicamente le colonne CSV tramite
   `_CSV_COLUMN_MAP`.
3. **Default hardcoded** -- `HARD_DEFAULT_BASELINE` fornisce 16 distribuzioni
   di metriche calibrate manualmente cosi che il coach possa comunque
   funzionare su un'installazione nuova. Una chiave `_provenance` marca la
   baseline come degradata.

Protezioni:
- `P-PB-01`: Rapporto K/D saltato quando DPR < 0.01 (evita rapporti gonfiati).
- `P-PB-02`: Sopravvivenza approssimata come `max(0, min(1, 1 - dpr))` poiche
  HLTV non espone una metrica di sopravvivenza dedicata.
- `P-PB-03`: La mappatura colonne CSV e dinamica, non hardcoded a tre colonne.
- `std = 0.0` e ammesso; a valle `calculate_deviations()` salta lo Z-score
  per quella metrica invece di dividere per zero.

### Decadimento Temporale Baseline (`TemporalBaselineDecay`)

Il CS2 professionale evolve: le statistiche recenti devono avere piu peso
rispetto ai dati di sei mesi fa. `TemporalBaselineDecay` avvolge il legacy
`get_pro_baseline()` con ponderazione temporale esponenziale:

- **Emivita:** 90 giorni (configurabile tramite `HALF_LIFE_DAYS`).
- **Peso minimo:** 0.1 (`MIN_WEIGHT`) -- i dati vecchi sono sotto-ponderati,
  mai scartati completamente.
- **Rilevamento meta-shift:** `detect_meta_shift()` confronta due epoche di
  baseline e segnala metriche che si sono spostate piu del 5%
  (`META_SHIFT_THRESHOLD`).

La baseline temporale viene fusa con la baseline legacy per garantire che
nessuna metrica sia mai mancante.

### Sorveglianza Meta-Drift (`meta_drift.py`)

`MetaDriftEngine` combina due segnali di drift:

| Segnale | Peso | Fonte |
|---------|------|-------|
| Drift statistico (variazione media Rating 2.0) | 0.4 | `hltv_metadata.db` via `ProPlayerStatCard` |
| Drift spaziale (variazione centroide posizioni) | 0.6 | `database.db` via `PlayerTickState` |

- Il drift spaziale usa `P-MD-01`: dimensioni mappa reali da `spatial_data`
  quando disponibili, con ripiego sulla dispersione dati osservata.
- Soglia drift: 10% dell'estensione mappa o 500 unita mondo, il maggiore.
- Coefficiente finale in `[0.0, 1.0]` alimenta
  `get_meta_confidence_adjustment()` che restituisce un moltiplicatore di
  confidenza coaching in `[0.5, 1.0]`.

### Apprendimento Soglie Ruolo (`role_thresholds.py`)

`RoleThresholdStore` segue il **Principio Anti-Mock**: ogni soglia inizia
come `None` e viene popolata esclusivamente da dati reali.

- **Rilevamento cold-start:** `is_cold_start()` ritorna `True` finche almeno
  3 soglie hanno `>= MIN_SAMPLES_FOR_VALIDITY` (30) giocatori unici.
- **Validazione consistenza:** `validate_consistency()` verifica intervallo
  `[0, 1]` prima di ogni persistenza (`P-RT-03`).
- **Apprendimento percentile:** `learn_from_pro_data()` calcola il 75esimo
  percentile per ogni statistica di ruolo (`P-RT-01`), contando giocatori
  unici non punti dati totali (`P-RT-02`).
- **Singleton thread-safe:** `get_role_threshold_store()` usa double-checked
  locking (`P3-06`).
- **Persistenza database:** `persist_to_db()` / `load_from_db()` usano il
  modello `RoleThresholdRecord` per il recupero tra riavvii.

### Risoluzione Nickname (`nickname_resolver.py`)

Collega i nomi giocatore delle demo (es. `"Spirit donk"`, `"s1mple-G2-"`)
a `ProPlayer.hltv_id` attraverso una pipeline a tre fasi:

1. **Match esatto** -- query SQL case-insensitive.
2. **Match sottostringa** -- verifica se un nickname noto e contenuto nel
   nome demo ripulito.
3. **Match fuzzy** -- `SequenceMatcher` con `FUZZY_THRESHOLD = 0.8`.

Nota complessita (`F2-41`): lookup sottostringa + fuzzy e `O(n)` per query,
accettabile per < 1000 pro registrati.

## Punti di Integrazione

| Consumatore | Utilizzo |
|-------------|----------|
| `CoachingService` | Chiama `get_pro_baseline()` e `calculate_deviations()` per generare report Z-score |
| Daemon `Teacher` | Chiama `MetaDriftEngine.calculate_drift_coefficient()` dopo il riaddestramento |
| `AnalysisOrchestrator` | Usa `TemporalBaselineDecay.get_temporal_baseline()` per confronti pesati per recenza |
| `RoleClassifier` | Legge `get_role_threshold_store()` per le soglie apprese |
| `NicknameResolver` | Chiamato durante l'ingestione demo per taggare giocatori pro |
| `role_features.py` | Chiama `MetaDriftEngine.get_meta_confidence_adjustment()` per firme adattive |

## Fonti Dati

- **`hltv_metadata.db`** -- Tabelle `ProPlayer`, `ProPlayerStatCard`,
  `ProTeam` popolate dalla pipeline di scraping HLTV.
- **`database.db`** -- `PlayerMatchStats`, `PlayerTickState` per analisi
  drift spaziale e recupero posizioni pro.
- **Database per-match** -- `match_data/<id>.db` per `get_pro_positions()`.
- **Ripiego CSV** -- `data/external/all_Time_best_Players_Stats.csv`.

## Note di Sviluppo

- Tutte le funzioni baseline sono **lettori puri** -- non mutano mai il
  database. Solo `RoleThresholdStore.persist_to_db()` scrive.
- Il logging strutturato usa `get_logger("cs2analyzer.<module>")`.
- Il dizionario `HARD_DEFAULT_BASELINE` e l'ultima risorsa e dovrebbe
  essere aggiornato periodicamente per riflettere le medie pro attuali.
- `get_pro_positions()` limita l'output tramite campionamento uniforme per
  contenere la memoria.
- `R4-20-01`: Le query al database usano `.limit()` e `.yield_per(500)` per
  prevenire consumo di memoria illimitato.
