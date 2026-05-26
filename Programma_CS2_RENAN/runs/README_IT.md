> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Sessioni di Esecuzione e Dati di Processo

Questa directory funge da storage volatile e spazio di lavoro per tutti i dati di esecuzione specifici della sessione generati dal coach IA di Counter-Strike. Agisce come un buffer temporaneo per le attività di elaborazione attive e come record storico per i cicli di analisi completati.

## Panoramica Tecnica

La directory `runs/` è progettata per gestire un elevato throughput di dati durante l'ingestione dei match e l'addestramento del modello. Ogni ciclo di esecuzione (una "run") crea una sottodirectory con timestamp o basata su ID per isolare i suoi dati dalle altre sessioni. Questo isolamento garantisce che i risultati dell'analisi intermedia e i checkpoint di addestramento non si sovrascrivano a vicenda, consentendo l'elaborazione simultanea di più demo o sessioni di addestramento.

## Componenti Chiave

- **Checkpoint di Addestramento**: Durante i cicli di fine-tuning del modello o di apprendimento per rinforzo, vengono salvati periodicamente gli stati del modello (pesi, stati dell'ottimizzatore).
- **Risultati di Analisi Intermedia**: File JSON e binari temporanei generati durante il parsing dei file demo prima di essere aggregati nel database finale o nel report.
- **Log di Sessione Raw**: Log di esecuzione dettagliati e di basso livello specifici per una singola run, utili per il debug di ingestioni fallite o drift del modello.
- **Cache di Inferenza**: Dati transitori utilizzati durante l'inferenza VLM/LLM per velocizzare le query ripetitive all'interno della stessa sessione.

## Struttura della Directory

```text
Programma_CS2_RENAN/runs/
├── [run_id_o_timestamp]/   # Spazio di lavoro isolato per una sessione specifica
│   ├── checkpoints/         # Pesi del modello e stato dell'addestramento
│   ├── intermediate/        # Dati demo parzialmente elaborati
│   └── session.log          # Log dettagliato per questa specifica run
├── README.md                # Documentazione in inglese
├── README_IT.md             # Questa documentazione
└── README_PT.md             # Versione portoghese
```

## Utilizzo

1. **Elaborazione Attiva**: Quando inizia una nuova ingestione di demo, il sistema crea automaticamente una nuova cartella in `runs/` per archiviare lo stato temporaneo.
2. **Addestramento del Modello**: Lo script di addestramento scrive i suoi progressi e i file periodici `.pth` o `.ckpt` in questa directory.
3. **Pulizia**: Poiché questo storage è considerato volatile, si raccomanda di archiviare i checkpoint importanti e cancellare periodicamente le vecchie cartelle di run per risparmiare spazio su disco. Il sistema include policy di pulizia automatica per le run più vecchie di una determinata soglia.
4. **Debugging**: In caso di crash del motore, i file all'interno della cartella della run specifica sono la fonte primaria per l'analisi post-mortem.
