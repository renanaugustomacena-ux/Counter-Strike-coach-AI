> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Asset Grafici e Temi UI

Questa directory contiene l'infrastruttura visuale per l'applicazione coach di
Counter-Strike. Ospita sfondi ad alta risoluzione, font personalizzati e
panoramiche delle mappe utilizzate dalla GUI interattiva Qt. Contiene
esclusivamente asset -- nessun codice.

## Panoramica Tecnica

Il sistema utilizza un'architettura basata su temi per mantenere la coerenza
visiva tra le diverse iterazioni del gioco (CS 1.6, CS:GO, CS2). Questi asset
vengono caricati a runtime dal frontend Qt: il motore dei temi
(`apps/qt_app/core/theme_engine.py`) registra cinque font all'avvio e risolve
gli sfondi selezionati dall'utente dalla cartella del tema attivo (il default di
design è una superficie piatta senza sfondo), e il widget nativo della mappa
tattica (`apps/qt_app/widgets/tactical/map_widget.py`) renderizza le panoramiche
da `maps/`. L'uso di font vettorializzati e sfondi con rapporto d'aspetto
coerente mantiene la UI nitida a qualsiasi risoluzione.

## Componenti Chiave

### Temi UI
La directory è organizzata in sottodirectory tematiche che definiscono l'aspetto e l'atmosfera dell'applicazione:
- **`cs16theme/`**: Estetica retrò ispirata a Counter-Strike 1.6.
- **`csgotheme/`**: Visual tattici moderni da Global Offensive.
- **`cs2theme/`**: Asset di nuova generazione progettati per Counter-Strike 2.

### Panoramiche delle Mappe
La sottodirectory **`maps/`** contiene 31 PNG panoramiche dall'alto per le mappe competitive:
- **`de_dust2.png`**, **`de_mirage.png`**, **`de_anubis.png`**, ecc. (inclusi i livelli inferiori per Nuke e Vertigo).
- Variazioni "`_dark`" e "`_light`" per la maggior parte delle mappe per un migliore contrasto (Anubis attualmente ha solo la variante base).

### Tipografia e Branding
File font inclusi in questa directory (cinque vengono registrati all'avvio dal motore dei temi; `NewHope-Line.ttf` è incluso ma non è nella mappa font del loader):
- **`cs_regular.ttf`**: Font iconico in stile CS per il branding.
- **`JetBrainsMono-Regular.ttf`**: Utilizzato per dati tecnici e log di match in stile codice.
- **`Roboto-Regular.ttf`**: Testo standard per le descrizioni delle analisi.
- **`NewHope.ttf`**: Font display (**`NewHope-Line.ttf`**: variante companion non registrata).
- **`YUPIX.otf`**: Font display pixel retrò.

Il motore dei temi esegue inoltre una scansione automatica di un secondo stack di font display sotto `assets/fonts/` (Space Grotesk, Inter), quindi questi non sono gli unici font dell'app.

## Struttura della Directory

```text
Programma_CS2_RENAN/PHOTO_GUI/
├── cs16theme/              # Sfondi CS 1.6 (retrò)
├── cs2theme/               # Sfondi CS2
├── csgotheme/              # Sfondi CS:GO
├── maps/                   # PNG panoramiche mappe (base + varianti _dark/_light)
├── cs_regular.ttf          # Font branding
├── JetBrainsMono-Regular.ttf # Font tecnico
├── NewHope.ttf / NewHope-Line.ttf # Font display
├── Roboto-Regular.ttf      # Font testo
└── YUPIX.otf               # Font display pixel
```

## Utilizzo

1. **Rendering della GUI**: Il motore dei temi registra cinque font all'avvio. Gli sfondi sono disattivati per default (superficie piatta); quando l'utente ne seleziona uno nelle Impostazioni (impostazione `BACKGROUND_IMAGE` persistita), viene risolto all'interno della cartella del tema attivo (`cs2theme/`, `csgotheme/`, `cs16theme/`). Una modalità slideshow degli sfondi (`WALLPAPER_SLIDESHOW`) ruota le immagini nella cartella del tema attivo.
2. **Overlay Tattici**: Il widget nativo della mappa tattica (`TacticalMapWidget`) carica le panoramiche `maps/*.png` e disegna posizioni dei giocatori, traiettorie e marcatori sopra di esse durante il replay 2D.
3. **Suoni UI Opzionali**: `apps/qt_app/core/sound.py` scansiona una cartella opzionale `PHOTO_GUI/sounds/` per file WAV forniti dall'utente; l'app degrada silenziosamente se la cartella è assente.
