> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Asset Grafici e Temi UI

Questa directory contiene l'infrastruttura visuale per l'applicazione coach di Counter-Strike. Ospita asset ad alta risoluzione, font personalizzati e panoramiche delle mappe utilizzate per generare sia la GUI interattiva che i report di analisi professionali in formato PDF.

## Panoramica Tecnica

Il sistema utilizza un'architettura basata su temi per mantenere la coerenza visiva tra le diverse iterazioni del gioco (CS 1.6, CS:GO, CS2). Questi asset vengono caricati dinamicamente dal modulo `reporting` per sovrapporre dati tattici (posizioni delle smoke, percorsi dei giocatori) alle panoramiche delle mappe. L'uso di font vettorializzati e sfondi con rapporto d'aspetto coerente garantisce che i report generati siano di alta qualità e leggibili.

## Componenti Chiave

### Temi UI
La directory è organizzata in sottodirectory tematiche che definiscono l'aspetto e l'atmosfera dell'applicazione:
- **`cs16theme/`**: Estetica retrò ispirata a Counter-Strike 1.6.
- **`csgotheme/`**: Visual tattici moderni da Global Offensive.
- **`cs2theme/`**: Asset di nuova generazione progettati per Counter-Strike 2.

### Panoramiche delle Mappe
La sottodirectory **`maps/`** contiene viste radar dall'alto e panoramiche per tutte le mappe del servizio attivo:
- **`de_dust2.png`**, **`de_mirage.png`**, ecc.
- Supporto per variazioni in modalità "Dark" e "Light" per un migliore contrasto nei report.

### Tipografia e Branding
Font essenziali per il rendering della UI e la generazione di PDF:
- **`cs_regular.ttf`**: Font iconico in stile CS per il branding.
- **`JetBrainsMono-Regular.ttf`**: Utilizzato per dati tecnici e log di match in stile codice.
- **`Roboto-Regular.ttf`**: Testo standard per le descrizioni delle analisi.

## Struttura della Directory

```text
Programma_CS2_RENAN/PHOTO_GUI/
├── cs16theme/              # Asset legacy
├── cs2theme/               # Asset moderni CS2
├── csgotheme/              # Asset stile CS:GO
├── maps/                   # Panoramiche mappe per overlay tattici
├── cs_regular.ttf          # Font branding
├── JetBrainsMono-Regular.ttf # Font tecnico
└── ... (altri asset)
```

## Utilizzo

1. **Rendering della GUI**: La dashboard principale utilizza gli sfondi e i temi per fornire un'esperienza utente immersiva.
2. **Overlay Tattici**: Durante l'analisi, il sistema seleziona una mappa da `maps/` e disegna programmaticamente traiettorie delle utility e mappe di calore su di essa.
3. **Generazione PDF**: Il motore di reporting utilizza gli asset qui presenti per compilare i report finali della sessione, garantendo che ogni PDF abbia un layout professionale coerente indipendentemente dalla mappa analizzata.
