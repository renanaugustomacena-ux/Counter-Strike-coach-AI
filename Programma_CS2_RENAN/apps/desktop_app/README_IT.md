# Applicazione Desktop (Legacy Kivy/KivyMD)

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Dominio:** Desktop UI / Frontend Kivy
> **Livello:** Intermedio -- richiede familiarita con il ciclo di vita dei widget Kivy, i componenti Material di KivyMD e il pattern MVVM.

> **Nota:** Questo e il frontend **legacy** Kivy/KivyMD. E ancora funzionante e mantenuto come fallback. Il frontend primario e PySide6/Qt -- vedi [`qt_app/`](../qt_app/).

---

## Panoramica

Applicazione desktop Kivy/KivyMD che implementa l'architettura **Model-View-ViewModel (MVVM)** per l'analisi tattica CS2 e il coaching AI. Il modulo fornisce 6 schermate dedicate (definite in questa directory) oltre a 7 schermate aggiuntive definite nel punto di ingresso dell'applicazione principale. Tutto il layout visivo e dichiarato in un singolo file `layout.kv` (~60 KB, 1621 righe) che utilizza la libreria di componenti Material Design di KivyMD.

L'applicazione renderizza replay di partite su una mappa tattica 2D pixel-accurate, visualizza lo stato dei giocatori in tempo reale nelle sidebar, crea grafici di economia e momentum tramite grafici Matplotlib integrati, e fornisce un'interfaccia di chat per il coaching AI supportata dal motore coaching COPER.

---

## Inventario dei File

| File | Righe | Scopo |
|------|-------|-------|
| `__init__.py` | 1 | Marcatore di pacchetto (vuoto). |
| `wizard_screen.py` | 418 | Procedura guidata di configurazione iniziale -- percorso Steam, brain data root, cartella demo. |
| `tactical_viewer_screen.py` | 295 | Replay mappa 2D con controlli di riproduzione, ghost AI, navigazione chronovisor. |
| `match_history_screen.py` | 162 | Lista partite scorrevole con rating HLTV 2.0 codificato per colore. |
| `match_detail_screen.py` | 454 | Analisi dettagliata di una singola partita: panoramica, round, grafico economia, highlight. |
| `performance_screen.py` | 331 | Dashboard aggregata: trend rating, statistiche per mappa, forze/debolezze, utility. |
| `help_screen.py` | 80 | Centro assistenza con ricerca, supportato dal modulo opzionale `help_system`. |
| `widgets.py` | 275 | 7 widget grafici basati su Matplotlib (trend, radar, economia, momentum, sparkline, utility, base). |
| `tactical_map.py` | 607 | Il widget "Living Map" -- rendering ottimizzato GPU con InstructionGroup per giocatori, granate, heatmap. |
| `player_sidebar.py` | 362 | LivePlayerCard + PlayerSidebar con pooling dei widget per lo stato giocatore in tempo reale. |
| `timeline.py` | 129 | TimelineScrubber interattivo con marcatori eventi (kill, plant, defuse). |
| `ghost_pixel.py` | 140 | Overlay di debug GhostPixelValidator per la calibrazione delle coordinate. |
| `tactical_viewmodels.py` | 345 | 3 ViewModel: TacticalPlaybackViewModel, TacticalGhostViewModel, TacticalChronovisorViewModel. |
| `coaching_chat_vm.py` | 140 | CoachingChatViewModel -- gestione sessione dialogo AI con thread safety. |
| `data_viewmodels.py` | 316 | 3 ViewModel: MatchHistoryViewModel, MatchDetailViewModel, PerformanceViewModel. |
| `theme.py` | 74 | Costanti di colore condivise, registro palette (CS2/CSGO/CS1.6), helper per rating. |
| `layout.kv` | 1621 | Definizioni layout KivyMD per tutte le schermate (~60 KB). Componenti Material Design. |

**Totale: 16 file Python + 1 file layout KV.**

---

## Schermate (6 in questa directory)

### 1. WizardScreen (`wizard_screen.py`)
Procedura guidata di configurazione iniziale con flusso in 4 fasi: `intro` -> `brain_path` -> `demo_path` -> `finish`. Utilizza `MDFileManager` per la selezione delle cartelle con supporto multi-disco su Windows. Valida i percorsi, crea la struttura di sottodirectory `knowledge/`, `models/`, `datasets/` sotto `BRAIN_DATA_ROOT`, e salva le impostazioni tramite `save_user_setting()`. Include normalizzazione del percorso contro il traversal (WZ-01) e logica di fallback per permessi negati.

### 2. TacticalViewerScreen (`tactical_viewer_screen.py`)
Schermata centrale di replay che coordina tre ViewModel. Carica i dati demo analizzati nel `PlaybackEngine`, renderizza i frame su `TacticalMap`, e aggiorna i widget `PlayerSidebar` per squadra. Supporta play/pause, velocita variabile, seek per tick, salto tra segmenti di round, overlay ghost AI, e navigazione dei momenti critici del chronovisor. Il timer UI dei tick funziona solo mentre la schermata e attiva (avviato su `on_enter`, cancellato su `on_leave`).

### 3. MatchHistoryScreen (`match_history_screen.py`)
Visualizza la lista delle partite dell'utente ordinata per data. Ogni scheda mostra il rating HLTV 2.0 con codifica colore e etichette di testo per accessibilita (P4-07), nome mappa estratto via regex, rapporto K/D, ADR, kill e morti. Toccando una scheda si naviga a `MatchDetailScreen`. Il caricamento dati e delegato a `MatchHistoryViewModel`.

### 4. MatchDetailScreen (`match_detail_screen.py`)
Analisi dettagliata in 4 sezioni per una singola partita:
- **Panoramica:** Rating HLTV 2.0 con barre di scomposizione dei componenti (KPR, DPR, impatto, ecc.)
- **Timeline Round:** Statistiche per round con colore per lato (CT blu / T oro), vittoria/sconfitta, K/D, danno, economia, opening kill
- **Economia:** Grafico a barre `EconomyGraphWidget` del valore equipaggiamento per round
- **Highlight e Momentum:** Insight del coaching con icone di severita + grafico `MomentumGraphWidget` del delta K-D cumulativo

### 5. PerformanceScreen (`performance_screen.py`)
Dashboard aggregata in 4 pannelli:
- **Trend Rating:** `RatingSparklineWidget` con linee di riferimento a 1.0, 1.1, 0.9
- **Statistiche per Mappa:** Scroll orizzontale di schede mappa con rating, ADR, K/D, numero partite
- **Forze/Debolezze:** Confronto Z-score rispetto al baseline professionale (colonne verde/rosso)
- **Efficacia Utility:** `UtilityBarWidget` barre orizzontali raggruppate (utente vs media pro)

### 6. HelpScreen (`help_screen.py`)
Lista argomenti nella sidebar con pannello contenuto. Utilizza il modulo opzionale `help_system` (degradazione aggraziata tramite try/except). Supporta il filtraggio per ricerca degli argomenti. Carica il primo argomento di default all'ingresso.

### Schermate Aggiuntive (definite in `main.py`)
HomeScreen, CoachScreen, UserProfileScreen, SettingsScreen, ProfileScreen, SteamConfigScreen, FaceitConfigScreen.

---

## Widget Personalizzati

### Widget Grafici (`widgets.py`)

Tutti i widget grafici estendono `MatplotlibWidget`, che renderizza figure Matplotlib in texture Kivy tramite un buffer PNG in memoria. Le figure vengono chiuse immediatamente dopo il rendering (WG-01) per prevenire memory leak.

| Widget | Tipo | Descrizione |
|--------|------|-------------|
| `MatplotlibWidget` | Base | Conversione buffer-to-texture con context manager `BytesIO` (WG-02). |
| `TrendGraphWidget` | Linea | Grafico a doppio asse: Rating (sinistro, ciano) e ADR (destro, ambra). Ultime 20 partite. |
| `RadarChartWidget` | Polare | Grafico radar/spider per attributi di abilita. Richiede minimo 3 punti dati (F7-36). |
| `EconomyGraphWidget` | Barre | Valore equipaggiamento per round. Barre CT in blu (#5C9EE8), barre T in oro (#E8C95C). |
| `MomentumGraphWidget` | Linea+Riempimento | Delta kill-death cumulativo. Riempimento verde sopra lo zero, rosso sotto. |
| `RatingSparklineWidget` | Linea+Riempimento | Progressione rating con linee di riferimento a 1.0 (neutro), 1.1 (buono), 0.9 (scarso). |
| `UtilityBarWidget` | Barre Orizzontali | Barre orizzontali raggruppate che confrontano le statistiche utility dell'utente vs media professionale. |

### Widget Tattici

| Widget | File | Descrizione |
|--------|------|-------------|
| `TacticalMap` | `tactical_map.py` | Mappa 2D ottimizzata GPU con 3 layer InstructionGroup (mappa statica, heatmap, giocatori/granate dinamici). Supporta caricamento asincrono della mappa, cache LRU per texture dei nomi (64 voci), rendering traiettorie granate con visualizzazione altezza 3D, overlay raggio detonazione (HE/Molotov/Smoke/Flash), coni FoV dei giocatori, highlight selezione, e click-to-select con hitbox ingrandite. |
| `LivePlayerCard` | `player_sidebar.py` | Scheda statistiche in tempo reale: barre progresso HP/armatura, economia, KDA, arma. Lo stato di morte diminuisce l'opacita. |
| `PlayerSidebar` | `player_sidebar.py` | Lista giocatori scorrevole con pooling dei widget (riuso oggetti invece di creare/distruggere ogni frame). Include `LivePlayerCard` per il dettaglio del giocatore selezionato. |
| `TimelineScrubber` | `timeline.py` | Barra di progresso interattiva con marcatori eventi codificati per colore. Marcatori kill a meta altezza (rosso), plant (giallo) e defuse (blu) a altezza piena. Supporta seek tramite click e trascinamento. |
| `GhostPixelValidator` | `ghost_pixel.py` | Overlay di debug che mostra coordinate normalizzate e mondiali al punto di tocco. Renderizza punti di riferimento landmark e un mirino magenta. Attivo solo quando `debug_mode=True`. |

---

## Architettura MVVM

### ViewModel

L'applicazione segue il pattern **Model-View-ViewModel**. Le View (classi Screen + `layout.kv`) gestiscono il rendering e l'interazione utente. I ViewModel possiedono la logica business e il caricamento dati. Tutti i ViewModel estendono l'`EventDispatcher` di Kivy con proprieta osservabili, usano daemon thread per l'I/O, e restituiscono i risultati al thread UI tramite `Clock.schedule_once`.

| ViewModel | File | Responsabilita |
|-----------|------|----------------|
| `TacticalPlaybackViewModel` | `tactical_viewmodels.py` | Play/pause, velocita, seeking, tracciamento tick tramite `PlaybackEngine`. |
| `TacticalGhostViewModel` | `tactical_viewmodels.py` | `GhostEngine` caricato lazy per predizioni posizioni AI. |
| `TacticalChronovisorViewModel` | `tactical_viewmodels.py` | Scansione in background per momenti critici, navigazione avanti/indietro con buffer tick. |
| `CoachingChatViewModel` | `coaching_chat_vm.py` | Sessione dialogo AI: verifica disponibilita, avvio sessione, invio/ricezione messaggi. Lista messaggi thread-safe (F7-24). |
| `MatchHistoryViewModel` | `data_viewmodels.py` | Caricamento in background della lista partite dalla tabella `PlayerMatchStats`. Supporto cancellazione (DV-01). |
| `MatchDetailViewModel` | `data_viewmodels.py` | Caricamento in background di statistiche partita, round, insight coaching, scomposizione HLTV 2.0. |
| `PerformanceViewModel` | `data_viewmodels.py` | Caricamento in background di storico rating, statistiche per mappa, forze/debolezze, dati utility. |

---

## Punto di Ingresso

Questo modulo **non** e autonomo. Il punto di ingresso dell'applicazione e `main.py` nella root del progetto, che:
1. Crea la sottoclasse `MDApp`
2. Carica `layout.kv` tramite `Builder.load_file()`
3. Registra tutte le schermate con lo `ScreenManager`
4. Avvia il loop eventi di Kivy

Le schermate in questa directory sono importate da `main.py` e registrate tramite il decoratore `@registry.register()`.

---

## File di Layout (`layout.kv`)

Il file `layout.kv` (1621 righe, ~60 KB) definisce l'interfaccia dichiarativa per tutte le schermate usando i componenti Material Design di KivyMD. Include:

- Layout delle schermate con `MDNavigationLayout`, `MDTopAppBar`, `MDNavigationDrawer`
- Alberi di widget per ogni schermata con riferimenti `id` usati dal codice Python
- Regole di stile per schede, etichette, pulsanti e widget personalizzati
- Dimensionamento responsive con unita `dp()` e `sp()`
- Binding dei temi per il registro palette in `theme.py`

Tutti i riferimenti `self.ids.<widget_id>` nel codice Python corrispondono alle dichiarazioni `id: <widget_id>` in questo file.

---

## Sistema dei Temi (`theme.py`)

Fornisce una palette di colori condivisa con tre temi selezionabili:

| Tema | Colore Superficie | Accento | Sfondo Grafici |
|------|-------------------|---------|----------------|
| **CS2** (default) | Nero-viola scuro | Arancione | `#1a1a1a` |
| **CSGO** | Grigio scuro | Blu-grigio | `#1c1e20` |
| **CS1.6** | Verde scuro | Verde | `#181e18` |

La codifica colore del rating segue le soglie standard HLTV: verde (>1.10), giallo (0.90-1.10), rosso (<0.90). Le etichette di testo ("Excellent", "Good", "Average", "Below Avg") garantiscono l'accessibilita WCAG 1.4.1 per daltonismo (P4-07).

---

## Note di Sviluppo

### Stato Legacy
Questo frontend e l'interfaccia **originale** costruita durante lo sviluppo iniziale. Rimane funzionante ed e mantenuta come fallback, ma **tutto lo sviluppo di nuove funzionalita e diretto al frontend PySide6/Qt** in `qt_app/`. Correzioni di bug e patch critiche vengono ancora applicate qui.

### Decisioni di Design Chiave
- **Layer InstructionGroup** in `TacticalMap` evitano di ricaricare la texture della mappa sulla GPU ad ogni frame. I layer statici vengono ridisegnati solo al ridimensionamento o al cambio mappa.
- **Pooling dei widget** in `PlayerSidebar` riutilizza i widget `MDListItem` invece di crearli/distruggerli ogni frame, riducendo la pressione sul GC.
- **Import lazy** per dipendenze pesanti (`torch`, `GhostEngine`, `ChronovisorScanner`) prevengono blocchi all'avvio.
- **Thread safety** garantita tramite `threading.Lock` sulle liste di messaggi condivise e `threading.Event` per la cancellazione.

### Limitazioni Note
- `HelpScreen` dipende da un modulo opzionale `help_system` che potrebbe non essere ancora implementato (F7-09)
- `GhostEngine` richiede un checkpoint di modello addestrato per funzionare
- I grafici Matplotlib sono renderizzati come texture PNG statiche (nessuna interattivita)
- Il file `layout.kv` e grande e monolitico; la sua suddivisione e un obiettivo di refactoring futuro
