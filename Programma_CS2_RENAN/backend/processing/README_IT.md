> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Processing — Pipeline Dati e Feature Engineering

Pipeline elaborazione dati orchestrando estrazione features, gestione baseline, validazione e generazione tensori per modelli ML.

## Moduli Top-Level

### Statistiche Round
- **round_stats_builder.py** — `build_round_stats()`, `compute_round_rating()`, `aggregate_round_stats_to_match()`, `enrich_from_demo()` — Calcolo rating HLTV 2.0 per-round, aggregazione a statistiche livello partita, arricchimento demo con noscope/blind kills, flash assists, uso utility.

### Tensori Visivi
- **tensor_factory.py** — `TensorFactory` — Genera tensori visivi 5 canali per livello percezione RAP Coach: Ch0 (cono vista), Ch1 (zone pericolo - placeholder), Ch2 (contesto mappa), Ch3 (vettori movimento), Ch4 (posizioni compagni).

### Heatmaps e Visualizzazione
- **heatmap_engine.py** — `HeatmapEngine` — Generazione heatmap posizioni 2D con smoothing kernel Gaussiano per posizioni morte, zone ingaggio e uso utility.

### Ricostruzione Stato
- **state_reconstructor.py** — `RAPStateReconstructor` — Ricostruzione completa stato gioco da dati tick per training RAP Coach. Integra awareness spaziale, tracciamento economia e stato momentum.

### Contesto Mappa
- **connect_map_context.py** — Estrazione features spaziali map-aware con penalità asse Z per mappe multi-livello (Nuke, Vertigo). Integrato con `core/spatial_data.py` per logica Z-cutoff.

## Sub-Packages

### feature_engineering/
Estrazione features unificata: `FeatureExtractor` (vettore 25-dim), componenti rating HLTV 2.0, calcolo KAST, features role-specific.

### baselines/
Baseline professionisti, soglie ruoli, decay temporale, rilevamento drift features.

### validation/
Validazione file demo, conformità schema, rilevamento drift.

## Dipendenze
NumPy, Pandas, PyTorch, OpenCV (heatmaps), SQLModel.
