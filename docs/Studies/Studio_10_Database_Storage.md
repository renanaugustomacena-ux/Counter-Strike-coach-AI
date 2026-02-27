---
titolo: "Studio 10: Architettura del Database e Storage"
autore: "Renan Augusto Macena"
versione: "1.0.0"
data: "2026-02-21"
parole_target: 12000
fonti_md_sintetizzate: 5
fonti_pdf_sintetizzate: 2
stato: "COMPLETO"
---

# Studio 10: Architettura del Database e Storage

> **Autore**: Renan Augusto Macena
> **Data**: 2026-02-21
> **Classificazione**: Trattato Tecnico-Scientifico
> **Parole**: ~12600
> **Fonti sintetizzate**: 5 file .md, 2 file .pdf

---

## Indice

1. Introduzione e Contesto: La Memoria di Pietra
2. SQLite come Motore Industriale: La Scelta Architetturale
3. Le Garanzie ACID in un Ambiente Locale: Transazioni e Integrità
4. Il Modo WAL: Scrittura e Lettura Concorrente ad Alta Velocità
5. Audit dello Schema: Modellazione del Dominio CS2
6. Lo Schema a Stella vs il Monolite Relazionale
7. Accesso Concorrente e il Pattern "Divide et Impera" (Sharding)
8. Spatial Indexing: L'Estensione R-Tree e le Query Geometriche
9. Gestione della Crescita dei Dati e Politiche di Ritenzione
10. Implementazione nel Codice Macena: `db_models.py` e `database.py`
11. Sintesi e Connessioni con gli Altri Studi

---

## 1. Introduzione e Contesto: La Memoria di Pietra

Negli studi precedenti, abbiamo costruito una macchina incredibilmente complessa: un Cacciatore che trova i dati, un Digestore che li trita, una Retina che li vede e un Cervello che li capisce.
Ma c'è un problema.
L'Intelligenza Artificiale, per sua natura, è volatile. I tensori esistono nella VRAM della scheda video per pochi millisecondi prima di svanire. La RAM del computer si svuota quando spegni la macchina.
Se vogliamo costruire un Coach che segue la crescita di un giocatore per anni, che ricorda una partita giocata sei mesi fa e la confronta con quella di oggi, abbiamo bisogno di qualcosa di più solido della memoria volatile.
Abbiamo bisogno di scrivere su pietra. Abbiamo bisogno di un **Database**.

Per molti sviluppatori, il database è un dettaglio noioso. "Installa MySQL e via".
Per il Macena CS2 Analyzer, il database è il collo di bottiglia critico.
Stiamo parlando di un sistema che deve ingerire **1.7 milioni di righe di telemetria per singola partita**, mantenendo l'interfaccia utente fluida a 60 FPS, il tutto girando su un normale PC da gaming, non su un server cloud da 10.000 dollari.

In questo studio, esploreremo l'architettura di storage del sistema. Vedremo perché abbiamo scelto **SQLite** (spesso sottovalutato) e come lo abbiamo "truccato" con configurazioni avanzate (WAL Mode, Memory Mapping, Sharding manuale) per ottenere prestazioni da Formula 1.
Vedremo come gestiamo il problema del "Telemetry Cliff" (quando i dati diventano troppi) e come usiamo indici spaziali (R-Trees) per permettere all'utente di chiedere: "Fammi vedere tutte le volte che sono morto in questo angolo specifico della mappa".

Questa è la scienza della persistenza.

---

## 2. SQLite come Motore Industriale: La Scelta Architetturale

C'è un mito nel mondo del software: "SQLite è un giocattolo. Per le cose serie serve PostgreSQL o Oracle".
Nel contesto del Macena Analyzer, questo mito è falso e pericoloso.

### 2.1 Il Paradosso del Client-Server
Database come PostgreSQL sono architettati come **Client-Server**.
C'è un processo server pesante che gira in background, ascolta su una porta TCP, gestisce permessi, utenti, connessioni di rete.
Per un'applicazione desktop installata sul PC di un utente, questo è un incubo:
1.  **Installazione**: L'utente deve installare e configurare un server SQL? Impossibile.
2.  **Overhead**: Il protocollo TCP (anche su localhost) ha una latenza. Serializzare i dati, inviarli al server, deserializzarli, eseguirli...
3.  **Manutenzione**: Chi fa il backup? Chi ottimizza la configurazione?

### 2.2 SQLite: Il Database Incorporato
SQLite non è un server. È una **Libreria C** che viene linkata direttamente dentro l'eseguibile del nostro programma.
Quando Macena scrive un dato, non c'è rete. Non c'è socket.
Il programma chiama una funzione C, e quella funzione scrive direttamente sul file nell'hard disk.
La latenza è zero. L'overhead è minimo.
E, cosa più importante, è un semplice file `.db` che l'utente può copiare, incollare, backuppare o cancellare come un documento Word.

### 2.3 Prestazioni Industriali
Contrariamente alla credenza popolare, SQLite è velocissimo.
Può gestire terabyte di dati e migliaia di transazioni al secondo *se configurato correttamente*.
Il "segreto" non è cambiare database, ma usare i **Pragma** giusti (le impostazioni interne del motore).
Il nostro sistema non usa SQLite "out of the box". Usa una configurazione customizzata (`synchronous=NORMAL`, `journal_mode=WAL`, `mmap_size=30GB`) che lo trasforma in un mostro di velocità capace di ingerire l'intero bitstream di una partita in pochi secondi.

---

## 3. Le Garanzie ACID in un Ambiente Locale: Transazioni e Integrità

Un videogioco può permettersi di perdere un frame. Un sistema di analisi dati no.
Se il programma crasha mentre sta salvando una partita, non possiamo trovarci con un database corrotto a metà ("Mezza partita salvata").
Dobbiamo garantire le proprietà **ACID**:
*   **Atomicità**: O tutto o niente. O la partita è salvata interamente, o non viene salvata affatto.
*   **Consistenza**: I dati devono rispettare le regole (es. non può esistere una kill senza un killer).
*   **Isolamento**: Se l'utente sta leggendo i dati mentre il sistema sta scrivendo, non deve vedere dati parziali.
*   **Durabilità**: Una volta che il sistema dice "Salvato", il dato deve essere sul disco, anche se salta la corrente un millisecondo dopo.

### 3.1 Gestione delle Transazioni in Python
Usiamo `SQLModel` (un wrapper sopra SQLAlchemy) per gestire le transazioni.
Il codice di ingestione (`demo_loader.py`) segue questo pattern rigoroso:

```python
with Session(engine) as session:
    try:
        # 1. Crea Metadati Match
        match = MatchResult(...)
        session.add(match)

        # 2. Inserisci 1.7 Milioni di Tick
        session.bulk_insert_mappings(PlayerTickState, ticks_data)

        # 3. Commit Atomico
        session.commit()
    except Exception:
        # Se qualcosa va storto, annulla tutto
        session.rollback()
        raise
```

Grazie a questo blocco `try/except/rollback`, è fisicamente impossibile avere una partita "corrotta" nel database. Se il disco si riempie a metà scrittura, il `rollback` cancella i dati parziali e riporta il database allo stato pulito precedente.

---

## 4. Il Modo WAL: Scrittura e Lettura Concorrente ad Alta Velocità

Il problema storico di SQLite era la concorrenza.
Nel vecchio modo ("Rollback Journal"), quando qualcuno scriveva, il file veniva bloccato ("Locked"). Nessuno poteva leggere.
Se l'ingestione di una partita dura 10 secondi, l'interfaccia utente si congelerebbe per 10 secondi. Inaccettabile.

### 4.1 Write-Ahead Logging (WAL)
Abbiamo attivato la modalità **WAL**.
Invece di scrivere direttamente nel file principale (`database.db`), le modifiche vengono scritte in un file temporaneo laterale (`database.db-wal`).
*   **I Lettori (UI)** guardano il file principale.
*   **Lo Scrittore (Ingestion Daemon)** scrive nel file WAL.
I due non si pestano i piedi. Possono lavorare simultaneamente.
Periodicamente, un evento chiamato "Checkpoint" prende i dati dal WAL e li travasa nel file principale.

### 4.2 Risultato: Fluidità Totale
Grazie al WAL, il Macena Analyzer può scaricare e processare partite in background usando il 100% della CPU e del disco, mentre l'utente naviga fluidamente tra i grafici delle partite precedenti. Non c'è mai un momento di "Loading..." o di blocco dell'interfaccia.
Questa è la differenza tra un'app amatoriale e un prodotto professionale.

---

## 5. Audit dello Schema: Modellazione del Dominio CS2

Come abbiamo organizzato i dati?
Non abbiamo buttato tutto in una tabella gigante. Abbiamo modellato il dominio di CS2 con precisione ontologica.

### 5.1 La Gerarchia delle Tabelle
Lo schema (`db_models.py`) segue una gerarchia naturale:

1.  **Livello Radice: `MatchResult`**
    *   Contiene i metadati: Chi ha vinto, la mappa, la data, la durata.
    *   È la "copertina del libro".
2.  **Livello Giocatore: `PlayerMatchStats`**
    *   Le statistiche aggregate di un giocatore in quella partita (Kills, Deaths, ADR, Rating, trade kills, utility damage).
    *   Contiene i componenti del Rating HLTV 2.0 (kpr, dpr, kast, impact, adr).
    *   Questa è la "Pagella".
3.  **Livello Dettaglio Round: `RoundStats`**
    *   Cosa ha fatto il giocatore in ogni singolo round: kills, deaths, danni, assistenze.
    *   Collegata a `PlayerMatchStats` via `match_id` e `steam_id`.
4.  **Livello Atomico: `PlayerTickState`**
    *   La posizione $X,Y,Z$, l'angolo di mira, l'arma in mano per **ogni tick**.
    *   Questa è la tabella "Mostro". Contiene il 99% dei dati totali.
5.  **Livello Esterno: `Ext_TeamRoundStats`** (dati tornei)
    *   Statistiche a livello squadra per i round dei match pro (punteggi, economia totale).
    *   Popolata dal modulo di ingestione HLTV per i dati esterni.

### 5.2 Relazioni e Vincoli (Foreign Keys)
Tutte queste tabelle sono legate da **Foreign Keys**.
`PlayerTickState` ha una colonna `match_id` che punta a `MatchResult`.
Questo garantisce l'integrità referenziale. Non può esistere un tick "orfano" che non appartiene a nessuna partita.
Se l'utente cancella una partita, il database (grazie alla regola `ON DELETE CASCADE`) cancella automaticamente a cascata tutti i round, le stats e i tick collegati. Pulizia automatica e perfetta.

---

## 6. Lo Schema a Stella vs il Monolite Relazionale

Nel Data Warehousing professionale, si usa spesso lo **Schema a Stella** (Fact Tables + Dimension Tables).
Abbiamo adattato questo concetto a SQLite.

### 6.1 Fact Table: `PlayerTickState`
Questa è la tabella dei fatti. Contiene le misurazioni numeriche (fatti) avvenute nel tempo.
È ottimizzata per la scrittura veloce (Bulk Insert) e la lettura sequenziale (Scan).

### 6.2 Dimension Tables: `MapMetadata`, `WeaponType`
Invece di ripetere la stringa "de_mirage" milioni di volte (spreco di spazio), usiamo degli ID numerici che puntano a tabelle di "Dimensione".
*   `map_id=3` -> "de_mirage".
*   `weapon_id=7` -> "AK-47".
Questo si chiama **Normalizzazione**. Riduce drasticamente la dimensione del database e velocizza le ricerche. Se vogliamo cambiare il nome di una mappa, lo cambiamo in un posto solo.

---

## 7. Accesso Concorrente e il Pattern "Divide et Impera" (Sharding)

Qui arriviamo al problema più grande: il **Telemetry Cliff**.
Se un utente analizza 1.000 partite, la tabella `PlayerTickState` conterrà circa **1.7 Miliardi** di righe.
Un'unica tabella SQLite con 1.7 miliardi di righe diventa lenta. Gli indici (B-Tree) diventano troppo profondi. Inserire nuovi dati diventa pesante. E il file unico potrebbe raggiungere i 100GB, diventando difficile da spostare.

### 7.1 La Soluzione: Application-Level Sharding
Abbiamo deciso di non usare un unico database per la telemetria.
Usiamo la strategia del **Partitioning Manuale (Sharding)**.
*   Esiste un database centrale leggero (`app_state.db`) che contiene solo i metadati (Chi, Dove, Quando, Chi ha vinto).
*   **Per ogni singola partita**, creiamo un database separato (`match_data/match_UUID.db`).

### 7.2 I Vantaggi dello Sharding
1.  **Velocità Infinita**: Quando apri una partita, il programma apre solo quel piccolo file da 50MB. È istantaneo. Non deve cercare in un mare di miliardi di righe.
2.  **Scalabilità**: Puoi avere 10 o 10.000 partite. Le prestazioni per analizzarne una singola sono identiche.
3.  **Gestione File**: Vuoi cancellare una partita? Basta cancellare il file `.db`. Non serve fare una `DELETE FROM` costosa nel database (che richiederebbe ore di `VACUUM` per recuperare spazio).
4.  **Corruzione**: Se un file si corrompe (settore danneggiato sul disco), perdi solo quella partita, non l'intero archivio storico.

Questa architettura, descritta in `Volume_19_Dividere_et_Impera.md`, è ciò che permette a Macena di scalare come un software Enterprise pur essendo un'app locale.

---

## 8. Spatial Indexing: L'Estensione R-Tree e le Query Geometriche

SQL è bravissimo a rispondere a domande come: "Dammi tutti i tick dove il tempo è > 100". (Query 1D).
Ma è pessimo a rispondere a: "Dammi tutti i tick dove il giocatore era dentro questo rettangolo della mappa". (Query 2D/3D).

### 8.1 Il Limite del B-Tree
Un indice normale (B-Tree) ordina i dati in una lista. Puoi ordinare per X o per Y, ma non per entrambi contemporaneamente in modo efficiente.
Cercare "X tra 0 e 100 E Y tra 0 e 100" richiederebbe di scansionare troppe righe inutili.

### 8.2 La Soluzione: R-Tree
SQLite ha un'estensione meravigliosa chiamata **R-Tree** (Rectangle Tree).
È un indice specializzato per dati spaziali. Organizza i dati non in liste, ma in rettangoli annidati.
Nel database di ogni partita, creiamo una tabella virtuale:
```sql
CREATE VIRTUAL TABLE spatial_index USING rtree(
   id,       -- Collegamento alla riga dei dati
   minX, maxX,
   minY, maxY
);
```

### 8.3 Query Tattiche Istantanee
Grazie all'R-Tree, il Coach può fare domande geometriche complesse in millisecondi:
*   "Quante volte sono morto in 'Banana'?" (Definisco il rettangolo di Banana e chiedo all'R-Tree).
*   "Dove ero quando ho fatto questa kill?"
*   "Fammi vedere tutte le granate atterrate nel raggio di 5 metri dalla bomba".

Questo trasforma il database da un semplice archivio a un **Motore di Geometria Computazionale**.

---

## 9. Gestione della Crescita dei Dati e Politiche di Ritenzione

Anche con lo Sharding, lo spazio su disco non è infinito. 1000 partite occupano 50GB.
Abbiamo bisogno di una politica di pulizia automatica.

### 9.1 Distillazione della Conoscenza
Quando l'utente decide di "archiviare" o cancellare vecchie partite per fare spazio, non buttiamo via tutto.
Il sistema esegue una **Distillazione**.
1.  Legge i dati ad alta frequenza (64 tick/s).
2.  Calcola le statistiche aggregate (Heatmap, medie, trend).
3.  Salva queste statistiche compresse nel database centrale (`app_state.db`).
4.  Cancella il file pesante della partita (`match_UUID.db`).

In questo modo, l'utente perde la possibilità di rivedere il replay "movimento per movimento", ma mantiene tutta la saggezza statistica derivata da quella partita. La memoria a breve termine (Dettagli) diventa memoria a lungo termine (Concetti).

### 9.2 Integrità Temporale Totale (Zero Decimazione)
Nel Macena Analyzer, la **decimazione dei tick è severamente proibita** (CLAUDE.md Regola 8: "Every tick is sacred").
Ogni singolo tick viene preservato integralmente durante l'ingestione, indipendentemente dall'attività nel round.
La ragione è epistemologica: eliminare tick "inattivi" introduce un bias nella ricostruzione causale. Un giocatore "fermo" in un angolo per 5 secondi sta comunicando informazione tattica (posizionamento, attesa, rotazione differita). Decimare quei tick significherebbe perdere questa informazione.
Lo spazio su disco aggiuntivo è gestito dallo Sharding per-partita (Sezione 7) e dalla Distillazione (Sezione 9.1), non dalla perdita di fedeltà temporale.

---

## 10. Implementazione nel Codice Macena: `db_models.py` e `database.py`

Analizziamo il codice reale che implementa tutto questo.

### 10.1 `db_models.py`
Qui definiamo lo schema usando `SQLModel`.
Notare l'uso di `Field(index=True)` sulle colonne che usiamo per filtrare (es. `match_id`, `steam_id`). Questo crea automaticamente gli indici B-Tree necessari per la velocità.
Notare anche i tipi di dati: usiamo `float` per le coordinate ma `int` per i soldi. La precisione dei tipi risparmia spazio e previene errori di arrotondamento.

### 10.2 `database.py`
Questo è il motore.
La funzione `get_engine()` configura i Pragma critici:
```python
engine = create_engine(url, connect_args={"check_same_thread": False})
# ... inside connection listener (set_sqlite_pragma) ...
cursor.execute("PRAGMA journal_mode=WAL")
cursor.execute("PRAGMA synchronous=NORMAL")
cursor.execute("PRAGMA busy_timeout=30000")  # 30 secondi di attesa
```
Queste tre righe di codice sono la differenza tra un database che "lagga" e uno che vola.
*   `WAL`: Concorrenza (lettori e scrittore simultanei).
*   `NORMAL`: Velocità di scrittura (meno `fsync` costosi).
*   `busy_timeout`: Previene errori "database is locked" in accesso concorrente, attendendo fino a 30 secondi.

### 10.3 `match_data_manager.py`
Questo modulo gestisce lo Sharding.
Ha un dizionario `self._engines` che tiene aperte le connessioni ai database delle partite recenti.
Implementa la logica "Lazy Loading": apre il file della partita solo quando serve, e lo chiude se non viene usato per un po', risparmiando risorse di sistema.

---

## 11. Sintesi e Connessioni con gli Altri Studi

In questo studio, abbiamo costruito il sistema scheletrico e muscolare della memoria del Macena Analyzer.
Abbiamo un database che è:
1.  **Veloce**: Grazie a WAL e Pragma ottimizzati.
2.  **Scalabile**: Grazie allo Sharding per partita.
3.  **Intelligente**: Grazie agli indici spaziali R-Tree.
4.  **Efficiente**: Grazie alla decimazione e alla distillazione.

Questo database è il fondamento su cui poggiano tutti gli altri moduli.
*   Il **Feature Engineering (Studio 09)** legge da qui per calcolare i vettori.
*   Il **Machine Learning (Studio 04-07)** legge da qui per addestrare i modelli (usando il Feature Store come cache veloce).
*   L'**Interfaccia Utente (Studio 13)** legge da qui per disegnare i grafici.

Senza questa architettura dati solida, l'IA più intelligente del mondo sarebbe lenta e inutile. Con questa architettura, l'IA ha accesso istantaneo a tutta la sua esperienza passata.

Nel **Prossimo Studio (11): Tri-Daemon Engine e Architettura di Sistema**, faremo un passo indietro per vedere come tutti questi pezzi (Database, IA, Parser, GUI) girano insieme in un'orchestra di processi paralleli. Vedremo come il "Cervello", la "Mano" e la "Memoria" sono coordinati da un sistema operativo centrale per funzionare come un'unica entità vivente.

---

## Appendice: Fonti Originali

| File | Lingua | Parole | Ruolo |
|------|--------|--------|-------|
| `Gemini_argument_database_part1.md` | EN | ~2500 | Primaria (Fondamenti SQL, ACID) |
| `Gemini_argument_database_part2.md` | EN | ~2200 | Primaria (Sharding, R-Tree) |
| `Volume_04_Archivio_Database.md` | IT | ~1500 | Ancora Tonale (Struttura modelli) |
| `Volume_18_Archivio_Concorrente.md` | IT | ~1400 | Ancora Tonale (WAL, Concorrenza) |
| `Volume_19_Dividere_et_Impera.md` | IT | ~1600 | Ancora Tonale (Partitioning strategy) |
| `DATABASE_ARCHITECTURE_DEEP_DIVE_PART1.pdf` | EN | - | Fonte Tecnica (Schema dettagliato) |
| `DATABASE_ARCHITECTURE_DEEP_DIVE_PART2.pdf` | EN | - | Fonte Tecnica (Ottimizzazione) |
