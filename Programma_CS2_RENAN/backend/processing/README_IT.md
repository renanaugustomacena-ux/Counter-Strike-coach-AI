> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Processing -- Pipeline Dati, Feature Engineering e Generazione Tensori

> **Autorità:** Regola 1 (Correttezza), Regola 5 (I Dati Sopravvivono al Codice),
> Contratto Dimensionale (`METADATA_DIM = 25`)

Il package `processing` è il livello centrale di trasformazione dati del
CS2 Coach AI. Si posiziona tra i dati grezzi delle demo (prodotti da
`backend/data_sources/`) e i modelli di rete neurale (consumati da
`backend/nn/`). Ogni modulo in questo package converte, arricchisce o
valida dati -- nessuno di essi memorizza o addestra nulla.

## Inventario File

| File | Righe | Scopo | Export Principali |
|------|-------|-------|-------------------|
| `__init__.py` | 1 | Marcatore di package | -- |
| `connect_map_context.py` | ~113 | Feature spaziali Z-aware relative agli obiettivi della mappa | `distance_with_z_penalty()`, `calculate_map_context_features()` |
| `cv_framebuffer.py` | ~193 | Ring buffer thread-safe per cattura frame CV ed estrazione HUD | `FrameBuffer`, `HeatmapData` |
| `data_pipeline.py` | ~330 | Pulizia dati, scaling, split temporale, decontaminazione giocatori | `ProDataPipeline` |
| `external_analytics.py` | ~202 | Confronto z-score con dataset CSV di riferimento elite | `EliteAnalytics` |
| `heatmap_engine.py` | ~301 | Mappe di occupazione Gaussiana e heatmap differenziali utente-vs-pro | `HeatmapEngine`, `HeatmapData`, `DifferentialHeatmapData` |
| `player_knowledge.py` | ~617 | Sistema di percezione Player-POV (modello sensoriale NO-WALLHACK) | `PlayerKnowledge`, `PlayerKnowledgeBuilder` |
| `round_stats_builder.py` | ~573 | Statistiche per-round, per-giocatore dagli eventi demo | `build_round_stats()`, `aggregate_round_stats_to_match()`, `enrich_from_demo()` |
| `skill_assessment.py` | ~155 | Decomposizione skill a 5 assi e proiezione livello curriculum | `SkillLatentModel`, `SkillAxes` |
| `state_reconstructor.py` | ~131 | Conversione tick-a-tensori per addestramento e inferenza RAP-Coach | `RAPStateReconstructor` |
| `tensor_factory.py` | ~748 | Tensori di percezione Player-POV (map, view, motion) | `TensorFactory`, `TensorConfig`, `TrainingTensorConfig`, `get_tensor_factory()` |
| `tick_enrichment.py` | ~352 | Feature contestuali cross-giocatore per indici METADATA_DIM 20-24 | `enrich_tick_data()` |

## Sub-Package

| Sub-Package | File | Scopo |
|-------------|------|-------|
| `feature_engineering/` | `vectorizer.py`, `base_features.py`, `role_features.py`, `rating.py`, `kast.py` | Estrazione feature unificata a 25-dim (`FeatureExtractor`), rating HLTV 2.0, calcolo KAST, feature specifiche per ruolo |
| `baselines/` | `pro_baseline.py`, `role_thresholds.py`, `meta_drift.py`, `nickname_resolver.py` | Baseline professionisti, soglie ruoli, decay temporale, rilevamento meta-drift, risoluzione nickname |
| `validation/` | `dem_validator.py`, `schema.py`, `sanity.py`, `drift.py` | Validazione file demo, conformità schema, controlli di sanità, rilevamento drift delle feature |

## Architettura e Concetti

### Flusso Dati

```
file .dem
  --> data_sources/ (demoparser2)
    --> tick_enrichment.py (feature cross-giocatore)
      --> round_stats_builder.py (aggregazione per-round)
        --> data_pipeline.py (pulizia, scaling, split)
          --> feature_engineering/vectorizer.py (vettore 25-dim)
            --> tensor_factory.py (tensori di percezione a 3 canali)
              --> nn/ (RAP Coach, JEPA)
```

### Percezione Player-POV (NO-WALLHACK)

Un principio di design fondamentale è che il coach AI vede solo ciò che
il giocatore conosce legittimamente ad ogni tick. Questo è applicato da
`player_knowledge.py` e consumato da `tensor_factory.py`:

- **Stato proprio:** Accesso completo (posizione, yaw, salute, armatura, arma).
- **Compagni:** Sempre noti (radar/comunicazioni).
- **Nemici visibili:** Solo quando `enemies_visible > 0` E all'interno del
  cono FOV. Le mappe multi-livello (Nuke, Vertigo) usano una soglia Z-floor.
- **Ultimi nemici conosciuti:** Memoria con decadimento esponenziale
  (`half-life = MEMORY_DECAY_TAU_TICKS`).
- **Inferenza sonora:** Eventi `weapon_fire` entro `HEARING_RANGE_GUNFIRE`.
- **Zone utility:** Smoke, molotov attivi e flash recenti.
- **Stato bomba:** Noto a tutti i giocatori.

### Canali Tensori

`TensorFactory` produce tre tensori a 3 canali per sequenza di tick:

| Tensore | Canale 0 | Canale 1 | Canale 2 |
|---------|----------|----------|----------|
| **map** | Posizioni compagni | Posizioni nemici (visibili + ultimi noti con decay) | Zone utility + bomba |
| **view** | Maschera FOV (cono geometrico) | Entità visibili (pesate per distanza) | Zone utility attive |
| **motion** | Traccia traiettoria (ultimi 32 tick) | Gradiente radiale velocità | Codifica yaw-delta del mirino |

### Salvaguardie della Pipeline Dati

`ProDataPipeline` applica diverse regole di integrità dei dati:

- **P-DP-01:** Soglie outlier derivate solo dal set di addestramento
  (previene il data leakage).
- **P-DP-02:** La decontaminazione giocatori assegna ogni giocatore al
  suo split temporale **più antico**, eliminando le righe degli split
  successivi.
- **P-DP-03:** Il moltiplicatore IQR per outlier è una costante nominata (3.0x).
- **P-DP-04:** Guardia di idempotenza previene il doppio scaling.
- **P-DP-05:** Controllo versione sklearn dello scaler (confronto major.minor).

### Valutazione delle Skill

`SkillLatentModel` decompone le statistiche del giocatore in cinque assi:

| Asse | Metriche |
|------|----------|
| Mechanics | `accuracy`, `avg_hs` |
| Positioning | `rating_survival`, `rating_kast` |
| Utility | `utility_blind_time`, `utility_enemies_blinded` |
| Timing | `opening_duel_win_pct`, `positional_aggression_score` |
| Decision | `clutch_win_pct`, `rating_impact` |

Il punteggio skill medio è proiettato su un livello curriculum 1-10 tramite
approssimazione CDF Gaussiana (`sigmoid(1.702 * z)`).

## Integrazione

- **Pipeline di Ingestione:** `tick_enrichment.enrich_tick_data()` viene
  chiamato durante l'ingestione demo per calcolare le feature 20-24 del
  vettore 25-dim. `round_stats_builder.enrich_from_demo()` produce
  arricchimento a livello di partita.
- **Reti Neurali:** `state_reconstructor.RAPStateReconstructor` e
  `tensor_factory.TensorFactory` producono i tensori consumati dai
  modelli RAP-Coach e JEPA.
- **Motore di Coaching:** `skill_assessment.SkillLatentModel` alimenta
  il livello curriculum. `external_analytics.EliteAnalytics` fornisce
  confronti z-score per il motore di correzione.
- **UI / Visualizzazione:** `heatmap_engine.HeatmapEngine` genera dati
  RGBA per heatmap di posizione e overlay differenziali.
  `cv_framebuffer.FrameBuffer` cattura frame per OCR delle regioni HUD.

## Note di Sviluppo

- Tutti i calcoli di distanza spaziale su mappe multi-livello devono
  usare `distance_with_z_penalty()` da `connect_map_context.py`, non
  la distanza Euclidea grezza.
- `FrameBuffer` è thread-safe per `capture_frame()` e `get_latest()`,
  ma `create_texture_from_data()` (Kivy) deve essere chiamato dal
  thread principale OpenGL.
- `HeatmapEngine.generate_heatmap_data()` e
  `generate_differential_heatmap_data()` sono thread-safe.
- `ProDataPipeline` limita le righe in memoria a `_MAX_PIPELINE_ROWS`
  (50.000) per prevenire OOM su deployment di grandi dimensioni.
- `player_knowledge.py` limita i nemici tracciati a `MAX_TRACKED_ENEMIES`
  (10) e l'attraversamento della cronologia a `MAX_HISTORY_TICKS` (512).
- Il modulo usa logging strutturato tramite
  `get_logger("cs2analyzer.<module>")` con ID di correlazione.
- Tutte le modifiche alle feature devono aggiornare `FEATURE_NAMES`,
  `METADATA_DIM`, docstring di `extract()` e asserzioni `input_dim`
  dei modelli.
