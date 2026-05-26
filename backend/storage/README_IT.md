> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Database Storage e Migrazioni

Questa directory gestisce il layer di persistenza dei dati dell'applicazione coach di Counter-Strike. Utilizza SQLAlchemy come Object-Relational Mapper (ORM) e Alembic per una gestione robusta dell'evoluzione dello schema del database e delle migrazioni.

## Panoramica Tecnica

Il motore di storage è progettato per garantire l'integrità dei dati e la coerenza dello schema in diversi ambienti di distribuzione. Utilizzando Alembic, il sistema mantiene una cronologia lineare delle modifiche al database, consentendo aggiornamenti e rollback fluidi. Lo schema è ottimizzato per query ad alte prestazioni su statistiche di match, metriche di performance dei giocatori e metadati tattici.

## Componenti Chiave

### Migrazioni Alembic
La sottodirectory **`migrations/`** contiene la logica per l'evoluzione del database:
- **`env.py`**: Il punto di ingresso per l'ambiente Alembic, che configura la connessione al database e il contesto della migrazione.
- **`script.py.mako`**: Un file template utilizzato da Alembic per generare nuovi script di migrazione.
- **`versions/`**: Una raccolta di script di migrazione incrementali.
    - **`b609a11e13cc_baseline_schema.py`**: Stabilisce le tabelle iniziali (Giocatori, Match, Round, ecc.).
    - **`5d5764ef9f26_add_rating_components.py`**: Un esempio di aggiornamento incrementale che aggiunge campi complessi per il calcolo del rating nel database.

## Struttura della Directory

```text
backend/storage/
├── migrations/             # Motore di migrazione Alembic
│   ├── env.py              # Configurazione dell'ambiente
│   ├── script.py.mako      # Template script di migrazione
│   └── versions/           # Versioni incrementali dello schema
├── README.md               # Documentazione in inglese
├── README_IT.md            # Questa documentazione
└── README_PT.md            # Versione portoghese
```

## Utilizzo

### Applicazione delle Migrazioni
Per portare il database all'ultima versione, esegui il seguente comando dalla root del progetto:
```bash
alembic upgrade head
```

### Creazione di una Nuova Migrazione
Quando i modelli SQLAlchemy nel backend vengono aggiornati, genera un nuovo script di migrazione utilizzando:
```bash
alembic revision --autogenerate -m "descrizione delle modifiche"
```

### Rollback
Per tornare a una versione precedente:
```bash
alembic downgrade -1
```

I parametri di connessione al database vengono solitamente caricati dalle variabili d'ambiente o dal file centrale `settings.json`.
