> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Configurazioni Tattiche

Questa directory funge da repository centralizzato per i metadati tattici
specifici delle mappe utilizzati dal coach IA di Counter-Strike. Archivia le
conoscenze strategiche fondamentali in formato JSON strutturato, consentendo
all'IA di fornire un coaching consapevole del contesto basato su standard
professionali stabiliti.

## Panoramica Tecnica

Disaccoppiando i dati tattici dalla logica principale, questa directory consente
aggiornamenti al "meta" senza richiedere modifiche al codice. Ogni file JSON
contiene un identificatore di mappa, una stringa di versione e una lista di
regole di coaching basate sui ruoli, indicizzate da un trigger in-round.

## Componenti Chiave

- **`mirage_defaults.json`**: Un file di riferimento seed per la mappa de_mirage (versione 1.0). Attualmente contiene due regole di consiglio basate sui ruoli:
    - **AWPer / `round_start`**: Controllare il timing di Mid Nest -- lo standard professionistico prevede di raggiungere la finestra entro 1:48.
    - **Entry Fragger / `t_side_exec`**: Dare priorità al clearing di Sandwich e Firebox durante l'esecuzione del sito A.

Ogni regola è un oggetto `{role, trigger, advice}`; nel file attuale non sono presenti coordinate per lineup o tempistiche delle utility.

## Struttura della Directory

```text
Programma_CS2_RENAN/tactics/
├── mirage_defaults.json  # Riferimento strategico per de_mirage
├── README.md             # Documentazione in inglese
├── README_IT.md          # Questa documentazione
└── README_PT.md          # Versione portoghese
```

## Utilizzo

**Stato: non ancora collegato al runtime.** Attualmente nessun codice carica file
da `tactics/`; la pipeline di coaching ottiene i propri contenuti tattici da
`backend/knowledge/` (base di conoscenza RAG e Coach Book). Questa directory è
la sede designata per i file di regole specifiche per mappa, nel caso in cui il
coaching tattico basato su trigger venga integrato:
1. **Caricamento dei Riferimenti**: Scansionare la directory `tactics/` e memorizzare le configurazioni JSON in cache.
2. **Matching delle Regole**: Incrociare il `trigger` di una regola (es. `round_start`, `t_side_exec`) e il `role` con il contesto in-round del giocatore.
3. **Generazione di Feedback**: Mostrare il testo `advice` della regola come coaching correttivo.
