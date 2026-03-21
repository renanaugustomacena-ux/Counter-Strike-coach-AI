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
| `rating.py` | Formula unificata HLTV 2.0 rating (componenti + regressione) | `compute_hltv2_rating()`, `compute_impact_rating()`, `compute_survival_rating()`, `compute_hltv2_rating_regression()` |
| `kast.py` | Calcolo KAST (Kill/Assist/Survive/Trade) | `calculate_kast_for_round()`, `calculate_kast_percentage()`, `estimate_kast_from_stats()` |
| `role_features.py` | Features specifiche per ruolo e classificazione | `classify_role()`, `extract_role_features()`, `get_role_coaching_focus()`, `get_adaptive_signatures()`, `ROLE_SIGNATURES`, `PlayerRole` |
| `__init__.py` | Dispatcher lazy-import (previene deadlock import-lock) | Riesporta tutti i nomi pubblici dai sottomoduli |

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
- **Weapon class** (indice 19) mappa circa 70 nomi di armi CS2 (nomi interni
  + nomi display demoparser2) in 6 categorie via `WEAPON_CLASS_MAP`.

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

Due implementazioni coesistono per design (`F2-40`):

1. **`compute_hltv2_rating()`** -- media per componente, ogni termine
   indipendentemente interpretabile. Usato per analisi deviazioni coaching.
2. **`compute_hltv2_rating_regression()`** -- coefficienti di regressione
   che corrispondono ai valori pubblicati HLTV (R^2=0.995). Usato per
   validazione display UI. Include una guardia runtime contro la confusione
   rapporto/percentuale kast.

Le due funzioni divergono deliberatamente -- NON riconciliarle.

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
Kivy detiene il lock di import.

## Punti di Integrazione

| Consumatore | Utilizzo |
|-------------|----------|
| `backend/nn/rap_coach/trainer.py` | `FeatureExtractor.extract_batch()` per dati di training |
| `backend/nn/jepa_trainer.py` | `FeatureExtractor.extract_batch()` con `validate_feature_parity()` |
| `backend/services/coaching_service.py` | `FeatureExtractor.extract()` per inferenza live |
| `backend/services/analysis_orchestrator.py` | `extract_match_stats()` per analisi a livello match |
| `backend/processing/baselines/role_thresholds.py` | `classify_role()` per validazione soglie |
| `core/session_engine.py` | `FeatureExtractor.configure()` all'avvio |

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
