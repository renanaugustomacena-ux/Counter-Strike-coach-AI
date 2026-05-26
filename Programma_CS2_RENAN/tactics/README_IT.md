> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Configurazioni Tattiche

Questa directory funge da repository centralizzato per i metadati tattici specifici delle mappe utilizzati dal coach IA di Counter-Strike. Archivia le conoscenze strategiche fondamentali in formato JSON strutturato, consentendo all'IA di fornire un coaching consapevole del contesto basato su standard professionali stabiliti.

## Panoramica Tecnica

Il motore tattico si affida a questi file di configurazione per convalidare le azioni dei giocatori, suggerire miglioramenti e comprendere lo stato di un round. Decoppiando i dati tattici dalla logica principale, il sistema consente facili aggiornamenti al "meta" senza richiedere modifiche al codice. Il coach IA analizza questi file per confrontare i dati di gioco in tempo reale con parametri di esecuzione "perfetti" predefiniti.

## Componenti Chiave

- **`mirage_defaults.json`**: Questo è il file di riferimento principale per la mappa de_mirage. Contiene punti dati completi tra cui:
    - **Smoke Lineups**: Coordinate precise e angoli di visuale per le granate fumogene essenziali (es. Jungle, Stairs, Nest).
    - **Flash Timings**: Ritardi ottimali e durate delle pop-flash per massimizzare la cecità dei nemici.
    - **Default Setups**: Distribuzioni standard lato CT (es. 2-1-2) ed esecuzioni predefinite lato T.
    - **Metadati Strategici**: Soglie per l'efficienza delle utility e mappe di calore del posizionamento.

## Struttura della Directory

```text
Programma_CS2_RENAN/tactics/
├── mirage_defaults.json  # Riferimento strategico per de_mirage
├── README.md             # Documentazione in inglese
├── README_IT.md          # Questa documentazione
└── README_PT.md          # Versione portoghese
```

## Utilizzo

Il coach IA utilizza questi file sia durante la fase di ingestione che in quella di analisi:
1. **Caricamento dei Riferimenti**: All'avvio, la directory `tactics/` viene scansionata e tutte le configurazioni JSON vengono caricate in memoria.
2. **Motore di Confronto**: Durante l'analisi del match, il motore incrocia l'uso delle utility del giocatore con le coordinate definite in `mirage_defaults.json`.
3. **Generazione di Feedback**: Se il tempismo o il posizionamento di un giocatore deviano significativamente dal "default", il coach genera consigli correttivi specifici.
