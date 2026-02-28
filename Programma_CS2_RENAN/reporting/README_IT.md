# Visualizzazione & Generazione Report

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Panoramica

Motore visualizzazione basato su Matplotlib e generazione report PDF. Produce heatmap, mappe engagement, grafici momentum, breakdown utility e report performance multi-sezione.

## Componenti Chiave

### `visualizer.py`
- **`MatchVisualizer`** — Classe visualizzazione principale per analisi match
- **Generazione heatmap** — Posizioni morte, zone engagement, uso utility sovrapposto a layout mappe
- **Mappe engagement** — Posizionamento giocatori durante momenti critici con marker scale-aware (micro/standard/macro)
- **Grafici momentum** — Timeline momentum round-per-round con annotazioni vittoria/sconfitta
- **Legenda scala** — Indicatore visivo per scala momento critico (micro=100px, standard=200px, macro=350px)
- Gestione figure Matplotlib con controllo DPI per output alta qualità

### `report_generator.py`
- **Generazione report PDF** — Report multi-pagina con sezioni: Overview, Round Breakdown, Economy Timeline, Highlights
- **Visualizzazione rating HLTV 2.0** — Grafici a barre che confrontano utente vs baseline pro
- **Breakdown utility** — Grafici a barre per HE, molotov, smokes, flash, utility non usata
- **Card performance per-mappa** — Rating, K/D, ADR, KAST% per mappa
- **Punti forza/debolezza** — Confronto Z-score contro baseline professionale

### `backend/reporting/analytics.py`
- **`get_rating_history()`** — Trend rating nel tempo per rendering sparkline
- **`get_per_map_stats()`** — Statistiche performance aggregate raggruppate per mappa
- **`get_strength_weakness()`** — Identifica top 3 punti forza e debolezza tramite Z-score
- **`get_utility_breakdown()`** — Confronto uso utility utente vs pro con metriche efficacia
- **`get_hltv2_breakdown()`** — Breakdown componenti rating HLTV 2.0 (K, S, KAST)

## Pattern Visualizzazione

Tutte le visualizzazioni usano:
- **Proiezione coordinate map-aware** — Coordinate tick → coordinate pixel tramite `SpatialData`
- **Gestione Z-cutoff** — Mappe multi-livello (Nuke, Vertigo) con separazione piani verticali
- **Coerenza colori** — Colori team (CT=blu, T=arancione), colori severità (critico=rosso, warning=giallo)
- **Output alta DPI** — 300 DPI per embedding PDF, 150 DPI per preview UI

## Rendering Momenti Critici

- **Scala micro** (1-3 tick): marker 100px, contorno arancione
- **Scala standard** (4-10 tick): marker 200px, contorno rosso
- **Scala macro** (>10 tick): marker 350px, riempimento rosso scuro

## Integrazione

Usato da `VisualizationService` per orchestrazione e schermate UI (`PerformanceScreen`, `MatchDetailScreen`) per rendering grafici inline.

## Formati Output

- PNG per display UI
- PDF per export report
- SVG per embedding web (futuro)
