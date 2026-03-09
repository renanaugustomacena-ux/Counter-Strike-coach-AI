# Applicazione Desktop

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

Applicazione desktop Kivy/KivyMD che implementa l'architettura MVVM per l'analisi tattica CS2 e il coaching AI.

## Architettura

**Pattern:** Model-View-ViewModel (MVVM)
- **Views:** Classi Screen e widget (definizioni layout.kv)
- **ViewModels:** Orchestratori di logica business (tactical_viewmodels.py, coaching_chat_vm.py)
- **Models:** Livello dati backend (database.py, db_models.py)

## Schermate (6)

1. **WizardScreen** (`wizard_screen.py`) — Procedura guidata di configurazione iniziale per integrazione Steam e configurazione cartelle
2. **TacticalViewerScreen** (`tactical_viewer_screen.py`) — Replay mappa 2D con rendering pixel-accurate e timeline scrubbing
3. **MatchHistoryScreen** (`match_history_screen.py`) — Elenco partite con rating HLTV 2.0 codificato per colore
4. **MatchDetailScreen** (`match_detail_screen.py`) — Analisi in 4 sezioni:
   - Panoramica + statistiche HLTV 2.0
   - Dettaglio per round
   - Timeline economia
   - Highlights + grafico Momentum
5. **PerformanceScreen** (`performance_screen.py`) — Analisi prestazioni in 4 pannelli:
   - Sparkline trend rating
   - Card statistiche per mappa
   - Punti di forza/debolezza vs baseline professionisti (Z-score)
   - Pannello utilizzo utility (6 metriche)
6. **HelpScreen** (`help_screen.py`) — Documentazione e guide utente

**Schermate Aggiuntive (in main.py):**
- HomeScreen, CoachScreen, UserProfileScreen, SettingsScreen, ProfileScreen, SteamConfigScreen, FaceitConfigScreen

## Widget Personalizzati

**`widgets.py`** — 7 widget personalizzati:
- `MatplotlibWidget` — Canvas matplotlib integrato per grafici generali
- `TrendGraphWidget` — Visualizzazione trend serie temporali
- `RadarChartWidget` — Radar prestazioni multidimensionale
- `EconomyGraphWidget` — Timeline economia round-by-round
- `MomentumGraphWidget` — Evoluzione momentum squadra
- `RatingSparklineWidget` — Sparkline compatto storico rating
- `UtilityBarWidget` — Barre confronto utilizzo utility (utente vs baseline pro)

**`tactical_map.py`** — Widget `TacticalMap` con rendering 2D pixel-accurate da coordinate spatial_data.py

**`player_sidebar.py`** — `LivePlayerCard`, `PlayerSidebar` per visualizzazione stato giocatore in tempo reale

**`timeline.py`** — `TimelineScrubber` per navigazione playback demo

**`ghost_pixel.py`** — `GhostPixelValidator` per debug tactical viewer e verifica coordinate

## ViewModels (MVVM)

**`tactical_viewmodels.py`** — 3 ViewModels per Tactical Viewer:
- `TacticalPlaybackViewModel` — Controllo playback e gestione timeline
- `TacticalGhostViewModel` — Rendering ghost player per modalità confronto
- `TacticalChronovisorViewModel` — Rilevamento e visualizzazione momenti critici (integrazione chronovisor)

**`coaching_chat_vm.py`** — `CoachingChatViewModel` per gestione dialogo coaching AI

## Definizioni Layout

**`layout.kv`** (56 KB) — Definizioni layout KivyMD per tutte le schermate con componenti Material Design
