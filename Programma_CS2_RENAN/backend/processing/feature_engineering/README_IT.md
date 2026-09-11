# Feature Engineering -- Estrazione Features Unificata

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autorevolezza:** `Programma_CS2_RENAN/backend/processing/feature_engineering/`

## Introduzione

Questo pacchetto e la **singola fonte di verita** per il vettore di features
a 25 dimensioni (`METADATA_DIM = 25`) consumato da ogni rete neurale del
progetto (RAP Coach, JEPA, AdvancedCoachNN). Tutta la logica di estrazione,
normalizzazione e codifica delle features risiede qui -- nessun altro modulo
e autorizzato a costruire vettori di features indipendentemente.

Il contratto fondamentale: training e inferenza DEVONO produrre vettori di
features identici per dati di input identici. Qualsiasi divergenza causa
corruzione silenziosa del modello nota come *Inference-Training Skew*.

## Inventario File

| File | Scopo | Export Principali |
|------|-------|-------------------|
| `vectorizer.py` | Estrazione e validazione vettore features 25-dim | `FeatureExtractor`, `FEATURE_NAMES`, `METADATA_DIM`, `DataQualityError`, `WEAPON_CLASS_MAP` |
| `base_features.py` | Soglie euristiche configurabili + aggregazione a livello match | `HeuristicConfig`, `extract_match_stats()`, `load_learned_heuristics()`, `save_heuristic_config()` |
| `rating.py` | Formula unificata HLTV 2.0 rating e componenti RAW `rating_*` | `compute_hltv2_rating()`, `compute_rating_components()`, `compute_impact_rating()`, `compute_survival_rating()` |
| `kast.py` | Calcolo KAST (Kill/Assist/Survive/Trade) | `calculate_kast_for_round()`, `calculate_kast_percentage()`, `estimate_kast_from_stats()` |
| `role_features.py` | Features specifiche per ruolo e classificazione | `classify_role()`, `extract_role_features()`, `get_role_coaching_focus()`, `get_adaptive_signatures()`, `ROLE_SIGNATURES`, `PlayerRole` |
| `__init__.py` | Dispatcher lazy-import (previene deadlock import-lock) | Riesporta lazily i nomi pubblici di `vectorizer`, `kast` e `role_features`; `base_features` e `rating` sono importati direttamente dai loro consumatori |

## Il Vettore di Features a 25 Dimensioni

Ogni tick di ogni giocatore e codificato in esattamente 25 valori float32.
L'ordine e fisso e imposto dall'asserzione compile-time
`len(FEATURE_NAMES) == METADATA_DIM` (invariante `P-X-01`).

| Idx | Nome | Normalizzazione | Intervallo | Categoria |
|-----|------|-----------------|------------|-----------|
| 0 | `health` | /100 | [0, 1] | Vitali |
| 1 | `armor` | /100 | [0, 1] | Vitali |
| 2 | `has_helmet` | binario | {0, 1} | Vitali |
| 3 | `has_defuser` | binario | {0, 1} | Vitali |
| 4 | `equipment_value` | /10000 | [0, 1] | Economia |
| 5 | `is_crouching` | binario | {0, 1} | Postura |
| 6 | `is_scoped` | binario | {0, 1} | Postura |
| 7 | `is_blinded` | binario | {0, 1} | Postura |
| 8 | `enemies_visible` | /5, clamped | [0, 1] | Consapevolezza |
| 9 | `pos_x` | /4096, clipped | [-1, 1] | Posizione |
| 10 | `pos_y` | /4096, clipped | [-1, 1] | Posizione |
| 11 | `pos_z` | /1024, clipped | [-1, 1] | Posizione |
| 12 | `view_yaw_sin` | sin(yaw_rad) | [-1, 1] | Angolo Visuale |
| 13 | `view_yaw_cos` | cos(yaw_rad) | [-1, 1] | Angolo Visuale |
| 14 | `view_pitch` | /90 | [-1, 1] | Angolo Visuale |
| 15 | `z_penalty` | `compute_z_penalty()` | [0, 1] | Spaziale |
| 16 | `kast_estimate` | rapporto KAST | [0, 1] | Prestazione |
| 17 | `map_id` | hash md5 -> [0, 1] | [0, 1] | Contesto |
| 18 | `round_phase` | 0/0.33/0.66/1.0 | [0, 1] | Economia |
| 19 | `weapon_class` | categorico 0-1 | [0, 1] | Equipaggiamento |
| 20 | `time_in_round` | /115, clamped | [0, 1] | Contesto |
| 21 | `bomb_planted` | binario | {0, 1} | Contesto |
| 22 | `teammates_alive` | /4 | [0, 1] | Contesto |
| 23 | `enemies_alive` | /5 | [0, 1] | Contesto |
| 24 | `team_economy` | /16000 | [0, 1] | Economia |

### Decisioni di Design

- **L'angolo yaw usa codifica sin/cos** (indici 12-13) per evitare la
  discontinuita +/-180 gradi che confonderebbe i modelli gradient-based.
- **L'identita mappa usa `hashlib.md5`** (indice 17), non `hash()` di
  Python, per riproducibilita deterministica tra sessioni.
- **Le features di contesto 20-24** vengono lette prima da `tick_data`
  (arricchiti durante l'ingestione), con fallback a un dict `context`
  (DemoFrame in inferenza), eliminando lo skew training/inferenza.
- **Weapon class** (indice 19) mappa circa 90 nomi di armi CS2 (nomi interni
  + nomi display demoparser2) in 8 valori di categoria via `WEAPON_CLASS_MAP`
  (knife 0.0, special 0.05, grenade 0.1, livelli 0.2-1.0; unknown 0.5).

## Architettura & Concetti

### FeatureExtractor (`vectorizer.py`)

L'interfaccia principale. Configurazione a livello classe tramite
`HeuristicConfig` abilita hot-swap runtime dei limiti di normalizzazione
(Task 6.3).

Metodi chiave:
- `extract(tick_data, map_name, context, _config_override)` -- singolo tick.
- `extract_batch(tick_data_list, map_name, contexts)` -- batch con snapshot
  config (`R4-14-03`) per consistenza thread-safe.
- `validate_feature_parity(vec, label)` -- asserisce che l'ultima dimensione
  sia uguale a `METADATA_DIM` ai confini training e inferenza (`P-SR-01`).
- `get_feature_names()` -- delega alla tupla `FEATURE_NAMES`.

Meccanismi di sicurezza:
- `P-VEC-01`: Warning se `map_name` mancante (z_penalty default 0.0).
- `P-VEC-02`: Rilevamento NaN/Inf con logging ERROR e clamp ai default.
- `P-VEC-03`: Parametro `_config_override` per consistenza batch.
- `P3-A`: Quality gate batch -- `DataQualityError` sollevato quando >5% dei
  vettori nel batch contenevano NaN/Inf prima del clamping.
- `H-12`: Armi sconosciute loggate a WARNING alla prima occorrenza, poi
  DEBUG.

### HeuristicConfig (`base_features.py`)

Un `@dataclass` che incapsula tutti i limiti di normalizzazione e le costanti
di soglia. Serializzabile in/da JSON tramite `to_dict()` / `from_dict()`.
Chiavi sconosciute vengono ignorate silenziosamente per compatibilita futura.

`extract_match_stats()` aggrega DataFrame per-round in statistiche a livello
match, calcolando il rating HLTV 2.0 unificato attraverso le funzioni di
`rating.py` per prevenire Inference-Training Skew.

### HLTV 2.0 Rating (`rating.py`)

Una formula di produzione piu un contratto di componenti:

1. **`compute_hltv2_rating()`** -- media per componente, ogni termine
   normalizzato contro una baseline formula e indipendentemente
   interpretabile. Usato per analisi deviazioni coaching. L'argomento
   `kast` e un RAPPORTO (0.0-1.0), mai una percentuale.
2. **`compute_rating_components()`** -- singola fonte di verita per le
   colonne `rating_*` di `PlayerMatchStats`. Contratto: le colonne
   memorizzano componenti RAW (`rating_kpr = kpr`, `rating_survival =
   1 - dpr`, `rating_kast` = rapporto KAST [0, 1], `rating_adr` = ADR
   grezzo) -- la normalizzazione baseline avviene SOLO all'interno
   dell'aggregato `rating`.

La precedente `compute_hltv2_rating_regression()` e stata ELIMINATA
(F2-39/R4 LOW, 2026-07-17): aveva zero call site in produzione e
portava semantiche kast in percentuale che invitavano rating x100
silenziosamente errati. I coefficienti di regressione (R^2=0.995)
rimangono nel modulo come costanti di documentazione. La media per
componente diverge deliberatamente dalla formula di regressione
pubblicata da HLTV (`F2-40`) -- NON riconciliarle.

### Calcolo KAST (`kast.py`)

Tre granularita:
- `calculate_kast_for_round()` -- per-round a livello eventi (verifica
  K/A/S/T con finestra trade e tick rate configurabili).
- `calculate_kast_percentage()` -- aggregato multi-round.
- `estimate_kast_from_stats()` -- approssimazione statistica quando gli
  eventi per-round non sono disponibili (usa euristica overlap assist 0.8
  e stima probabilita trade 30%).

### Role Features (`role_features.py`)

- `ROLE_SIGNATURES` -- profili centroide statici per Entry, AWPer, Support,
  Lurker e IGL basati su analisi top-20 giocatori HLTV.
- `classify_role()` -- delega a `RoleClassifier` (soglie apprese + consenso
  neurale), fallback a euristica distanza euclidea in cold start.
- `get_adaptive_signatures()` -- allarga le bande di tolleranza tramite
  `MetaDriftEngine.get_meta_confidence_adjustment()` quando meta drift > 0.3.
- `get_role_coaching_focus()` -- restituisce chiavi statistiche prioritarie
  per ruolo.

### Lazy Imports (`__init__.py`)

Usa `__getattr__` per differire gli import dei sottomoduli fino al primo
accesso attributo. Questo previene deadlock `_ModuleLock` quando thread
daemon (worker di ingestione) importano sottomoduli mentre il thread UI
detiene il lock di import.

## Punti di Integrazione

| Consumatore | Utilizzo |
|-------------|----------|
| `backend/nn/training_orchestrator.py` | `FeatureExtractor.extract_batch()` per dati di training |
| `backend/nn/jepa_train.py` | `FeatureExtractor.extract_batch()` per training JEPA |
| `backend/processing/state_reconstructor.py` | `extract_batch()` + `validate_feature_parity()` per tensori RAP-Coach |
| `backend/nn/inference/ghost_engine.py` | `validate_feature_parity()` al confine di inferenza |
| `backend/services/coaching_service.py` | `FeatureExtractor` estrazione per inferenza live |
| `backend/coaching/pro_bridge.py`, `ingestion/pipelines/user_ingest.py` | `extract_match_stats()` per statistiche a livello match |

## Note di Sviluppo

- **Non aggiungere mai una feature** senza aggiornare `FEATURE_NAMES`,
  `METADATA_DIM`, la docstring di `extract()` e tutte le asserzioni
  `input_dim` dei modelli.
- **Non includere mai `round_won`** come feature di training -- e un label
  di outcome (invariante `P-RSB-03`).
- **Chiamare sempre `extract()` con `map_name`** durante il training --
  z_penalty si rompe senza (`P-VEC-01`).
- Usare `_config_override` in `extract()` per elaborazione batch (`P-VEC-03`).
- Il logging strutturato usa `get_logger("cs2analyzer.vectorizer")`.
- Dipendenze: NumPy, Pandas, hashlib (stdlib), math (stdlib).
