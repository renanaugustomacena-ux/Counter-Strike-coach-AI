> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Log di Sistema Centralizzati

Questa directory funge da hub centralizzato per l'osservabilità dell'intero sistema e i dati diagnostici. Aggrega i log del motore backend, dei servizi di ingestione dei match e dei moduli di inferenza AI per fornire una visione completa della salute operativa del sistema.

## Panoramica Tecnica

L'architettura di logging è progettata per il monitoraggio ad alta granularità del backend del coach di Counter-Strike. I log sono generati utilizzando un formato strutturato per facilitare l'analisi automatizzata e l'alerting. L'obiettivo principale è garantire che i colli di bottiglia delle prestazioni, i fallimenti di ingestione e le deviazioni dei modelli siano identificati e risolti in tempo reale.

## Componenti Chiave

- **`cs2_analyzer.log`**: Il file di log principale per il motore di analisi backend. Tiene traccia di:
    - **Monitoraggio Errori**: Stack trace dettagliati per fallimenti API, problemi di connessione al database ed errori di parsing delle demo.
    - **Throughput di Ingestione**: Metriche su quanti file demo vengono elaborati al minuto, inclusi la dimensione del file e la durata del parsing.
    - **Latenza di Inferenza**: Tempi precisi per le richieste LLM e VLM, consentendo l'ottimizzazione dei tempi di risposta del modello.
    - **Salute del Sistema**: Heartbeat periodici dai processi worker in background e dal servizio di sincronizzazione HLTV.

## Struttura della Directory

```text
logs/
├── cs2_analyzer.log        # Log principale del backend e dell'analisi
├── README.md               # Questa documentazione (EN)
├── README_IT.md            # Versione Italiana
└── README_PT.md            # Versione Portoghese
```

## Utilizzo

### Monitoraggio in Tempo Reale
Per monitorare i log di sistema in tempo reale durante una sessione di ingestione o addestramento su larga scala:
```bash
tail -f logs/cs2_analyzer.log
```

### Rotazione dei Log
Il sistema è configurato per ruotare automaticamente i log quando raggiungono i 100MB, conservando fino a 5 versioni storiche (es. `cs2_analyzer.log.1`) per prevenire l'esaurimento dello spazio su disco.

### Filtrare per Errori
Per identificare rapidamente problemi critici all'interno dei log:
```bash
grep "ERROR" logs/cs2_analyzer.log
```

### Analisi delle Prestazioni
Le voci di log includono campi `latency_ms` per le chiamate di inferenza, che possono essere estratti per generare istogrammi delle prestazioni e identificare risposte lente del modello.
