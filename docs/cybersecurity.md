# Manuale Completo di Cybersecurity e Integrità del Sistema - Macena CS2 Analyzer

**Versione Documento:** 1.0.0
**Data di Pubblicazione:** 27 Febbraio 2026
**Classificazione:** Internal / Confidential
**Progetto:** Macena CS2 Analyzer (Programma_CS2_RENAN)

---

## Indice

1.  **Introduzione e Visione Strategica**
    *   1.1 Filosofia di Sicurezza: "Anti-Placebo" e Sovranità dei Dati
    *   1.2 Scopo del Documento
    *   1.3 Destinatari e Responsabilità
2.  **Architettura di Sicurezza del Sistema**
    *   2.1 Isolamento dei Componenti (Core, Backend, Ingestion)
    *   2.2 Gestione dell'Ambiente di Esecuzione (Virtual Environment & Frozen State)
    *   2.3 Sicurezza del Database (SQLite & SQLAlchemy)
    *   2.4 Interfaccia Console e Controllo degli Accessi
3.  **Gestione delle Identità e delle Credenziali (IAM)**
    *   3.1 Integrazione con Windows Credential Locker (Keyring)
    *   3.2 Protezione delle API Key (Steam, Faceit)
    *   3.3 Gestione dei File di Configurazione (`user_settings.json`)
    *   3.4 Politiche di Masking nei Log
4.  **Sicurezza dei Dati e Privacy (Data Protection)**
    *   4.1 Sovranità dei Dati: Architettura Local-First
    *   4.2 Sanitizzazione Industriale (`Sanitize_Project.py`)
    *   4.3 Gestione dei Dati Personali (PII) e Conformità GDPR
    *   4.4 Crittografia a Riposo e in Transito
5.  **Integrità del Codice e della Build (Supply Chain Security)**
    *   5.1 Protocollo di Audit "Anti-Placebo"
    *   5.2 Verifica dell'Integrità dei Binari (`audit_binaries.py`)
    *   5.3 Sicurezza della Pipeline di Build (PyInstaller & GitHub Actions)
    *   5.4 Rilevamento del Codice Morto e Vulnerabilità Statiche
6.  **Sicurezza Operativa (OpSec) e Monitoraggio**
    *   6.1 Logging Strutturato e Auditing
    *   6.2 Safe Mode e Validazione Dinamica (`verify_all_safe.py`)
    *   6.3 Gestione delle Risorse e Prevenzione DoS
7.  **Analisi delle Minacce e Vettori di Attacco**
    *   7.1 Parsing di File Demo Malformati
    *   7.2 Injection Attacks (SQL & Command Injection)
    *   7.3 Manipolazione della Memoria Runtime
8.  **Procedure Operative Standard (SOP) per la Sicurezza**
    *   8.1 SOP-SEC-01: Inizializzazione Sicura del Sistema
    *   8.2 SOP-SEC-02: Gestione di un Incidente di Sicurezza
    *   8.3 SOP-SEC-03: Audit Periodico e Manutenzione
9.  **Piano di Risposta agli Incidenti (Incident Response)**
    *   9.1 Identificazione e Classificazione
    *   9.2 Contenimento ed Eradicazione
    *   9.3 Recupero e Post-Incident Analysis
10. **Roadmap e Sviluppi Futuri della Sicurezza**

---

## 1. Introduzione e Visione Strategica

### 1.1 Filosofia di Sicurezza: "Anti-Placebo" e Sovranità dei Dati

La sicurezza nel progetto **Macena CS2 Analyzer** non è un semplice livello aggiuntivo, ma un pilastro fondante dell'architettura. In un ecosistema che analizza dati comportamentali complessi derivati da replay di gioco (demo CS2), la fiducia nell'integrità del dato è fondamentale.

La nostra filosofia si basa su due concetti chiave:

1.  **Standard Anti-Placebo**: Codificato nel `AUDIT_PROTOCOL.md`, questo principio impone che ogni test, ogni validazione e ogni misura di sicurezza debba basarsi su dati empirici reali e non su simulazioni (mock) o assunzioni felici. Un sistema sicuro è un sistema che non mente al suo operatore. Se un componente fallisce, deve fallire in modo rumoroso e visibile, non degradare silenziosamente.
2.  **Sovranità dei Dati (Local-First)**: A differenza di molte piattaforme di analisi moderne che richiedono l'upload dei dati in cloud, Macena CS2 Analyzer è progettato per operare interamente in locale. Il database, i modelli di Machine Learning e i log risiedono sulla macchina dell'utente. Questo riduce drasticamente la superficie di attacco esposta verso l'esterno e garantisce all'utente il controllo totale sui propri dati.

### 1.2 Scopo del Documento

Questo documento serve come riferimento autoritativo per tutte le questioni relative alla cybersecurity del progetto. Esso definisce:
*   Le misure tecniche implementate per proteggere il codice, i dati e l'infrastruttura.
*   Le procedure operative per mantenere lo stato di sicurezza.
*   I protocolli di risposta in caso di anomalie o compromissioni.

È destinato agli sviluppatori, agli ingegneri della sicurezza, agli auditor e agli utenti avanzati che necessitano di comprendere il modello di minaccia del software.

### 1.3 Destinatari e Responsabilità

*   **Sviluppatori Core**: Responsabili dell'implementazione delle pratiche di "Secure Coding" descritte nella sezione 5 e del mantenimento dei test di integrità.
*   **DevSecOps**: Responsabili della manutenzione della pipeline CI/CD e degli strumenti di audit automatico (`audit_binaries.py`, `Sanitize_Project.py`).
*   **Utenti Finali**: Responsabili della custodia fisica della macchina su cui gira il software e della gestione sicura delle proprie API Key (Steam, Faceit).

---

## 2. Architettura di Sicurezza del Sistema

Il sistema Macena CS2 Analyzer è costruito su un'architettura modulare che favorisce la "Defense in Depth" (Difesa in Profondità).

### 2.1 Isolamento dei Componenti

Il codice è suddiviso in domini funzionali con confini chiari, riducendo il rischio di movimenti laterali in caso di vulnerabilità in un modulo specifico.

*   **Core (`Programma_CS2_RENAN/core`)**: Contiene la logica di business immutabile, le configurazioni e i gestori di asset. Questo modulo ha dipendenze minime e funge da "Trust Anchor" per il resto dell'applicazione.
*   **Backend (`Programma_CS2_RENAN/backend`)**: Gestisce l'orchestrazione, l'accesso al database e il controllo dei processi. L'accesso al database è mediato rigorosamente attraverso ORM (SQLAlchemy/Alembic) per prevenire SQL Injection.
*   **Ingestion (`Programma_CS2_RENAN/ingestion`)**: Il componente più esposto, responsabile del parsing dei file `.dem` e del download da fonti esterne. È progettato per essere resiliente a dati malformati (vedi Sezione 7.1).
*   **Tools (`tools/`)**: Una suite di script amministrativi separati dal runtime principale. Strumenti critici come `Sanitize_Project.py` risiedono qui per evitare che possano essere invocati accidentalmente durante il normale funzionamento dell'app.

### 2.2 Gestione dell'Ambiente di Esecuzione

Il software supporta due modalità di esecuzione, ciascuna con le proprie implicazioni di sicurezza:

1.  **Sorgente (Python Venv)**: Utilizza un ambiente virtuale (`venv_win`) per isolare le dipendenze Python dal sistema operativo host. Questo previene conflitti di librerie ("Dependency Hell") e assicura che vengano caricate solo versioni verificate dei pacchetti (tramite `requirements-lock.txt`).
2.  **Frozen State (PyInstaller)**: Nella distribuzione finale, il codice viene "congelato" in un eseguibile standalone. Il sistema rileva questa modalità tramite `sys.frozen` (vedi `core/config.py`) e adatta i percorsi delle risorse. I file temporanei vengono estratti in una directory protetta (`_MEIPASS`), riducendo la possibilità di manipolazione del codice sorgente da parte di malware residenti.

### 2.3 Sicurezza del Database

Il cuore della persistenza è un database SQLite locale (`database.db`).

*   **Integrità Referenziale**: L'uso di `Alembic` per le migrazioni garantisce che lo schema del database sia sempre consistente e versionato. Script come `tools/db_health_diagnostic.py` e `tools/migrate_db.py` permettono di verificare l'integrità strutturale del DB.
*   **Prevenzione SQL Injection**: Tutte le query sono costruite utilizzando l'ORM o query parametrizzate. L'input utente non viene mai concatenato direttamente nelle stringhe SQL.
*   **File Locking**: SQLite gestisce il locking dei file per prevenire corruzione dovuta a accessi concorrenti non gestiti, critico in un ambiente multithreaded (ingestion + UI).

### 2.4 Interfaccia Console e Controllo degli Accessi

Il sistema è controllato principalmente tramite `console.py`.

*   **Validazione dei Comandi**: Ogni comando inserito viene validato contro una whitelist di comandi registrati.
*   **Gestione degli Errori Sicura**: Le eccezioni durante l'esecuzione dei comandi vengono catturate e loggate in modo strutturato, evitando di mostrare stack trace completi all'utente finale che potrebbero rivelare dettagli interni dell'infrastruttura, pur fornendo informazioni sufficienti per il debug nei log.

---

## 3. Gestione delle Identità e delle Credenziali (IAM)

Sebbene sia un'applicazione desktop monoutente, la gestione delle credenziali per servizi terzi (Steam, Faceit) è trattata con standard enterprise.

### 3.1 Integrazione con Windows Credential Locker (Keyring)

Come evidenziato dall'analisi di `core/config.py`, il sistema utilizza la libreria `keyring` per interfacciarsi con il sottosistema di gestione credenziali nativo del sistema operativo (Windows Credential Locker su Windows).

*   **Meccanismo**: Le API Key non vengono salvate in chiaro nei file di testo se possibile. Vengono delegate al sistema operativo, che le cifra utilizzando le credenziali di login dell'utente Windows.
*   **Vantaggio**: Anche se un attaccante ottenesse accesso ai file di progetto (es. rubando la cartella), non potrebbe recuperare le chiavi API senza conoscere anche la password dell'account Windows dell'utente.

### 3.2 Protezione delle API Key

Il sistema gestisce due chiavi critiche:
*   **STEAM_API_KEY**: Permette l'accesso ai dati pubblici dei giocatori su Steam.
*   **FACEIT_API_KEY**: Permette il download di demo e statistiche dalla piattaforma Faceit.

Se il `keyring` non è disponibile (fallback), le chiavi vengono salvate in `user_settings.json`. Il sistema emette warning nei log in questo scenario, invitando l'utente a mettere in sicurezza il proprio ambiente.

### 3.3 Gestione dei File di Configurazione (`user_settings.json`)

Il file `user_settings.json` contiene le preferenze utente e, in caso di fallback, le chiavi API.
*   **Posizione**: Risiede nella root del progetto o in `%LOCALAPPDATA%` in modalità frozen.
*   **Accesso**: I permessi di lettura/scrittura dovrebbero essere limitati all'utente corrente (standard Windows DACL).
*   **Sanitizzazione**: Lo strumento `Sanitize_Project.py` prevede la rimozione sicura di questo file per riportare il sistema a uno stato "vergine" e privo di dati sensibili.

### 3.4 Politiche di Masking nei Log

Per prevenire il "Logging of Sensitive Information" (CWE-532), il modulo `core/config.py` implementa la funzione `mask_secret`.
*   **Funzionamento**: Qualsiasi segreto letto o scritto viene mascherato (es. `ABCD...1234`) prima di essere passato al logger.
*   **Audit**: I log possono essere condivisi per il debug senza timore di esporre le chiavi API complete.

---

## 4. Sicurezza dei Dati e Privacy (Data Protection)

### 4.1 Sovranità dei Dati: Architettura Local-First

La privacy è garantita dall'architettura. I dati sensibili (statistiche di gioco, pattern comportamentali, cronologia match) non lasciano mai la macchina dell'utente.
*   **Nessuna Telemetria Nascosta**: Non ci sono "phone home" non documentati. Le uniche connessioni esterne sono esplicite verso Steam, Faceit o servizi HLTV, e sono attivate solo su richiesta dell'utente (comandi `ingest` o `sync`).
*   **Database Portabile**: Il database SQLite può essere facilmente backuppato o distrutto dall'utente.

### 4.2 Sanitizzazione Industriale (`Sanitize_Project.py`)

Uno degli strumenti più potenti nell'arsenale di sicurezza del progetto è `tools/Sanitize_Project.py`. Questo script implementa una "pulizia di grado industriale".

*   **Target di Cancellazione**:
    1.  `user_settings.json`: Rimuove tutte le credenziali e preferenze.
    2.  `database.db`: Distrugge l'intero storico delle partite e delle analisi.
    3.  `logs/`: Elimina le tracce di esecuzione che potrebbero contenere metadati sensibili (IP, percorsi file).
    4.  `*.pid`: Rimuove file di lock stantii.
*   **Modalità d'Uso**: Deve essere eseguito con conferma esplicita (o flag `--yes` in automazione). È essenziale prima di dismettere un PC, condividere la cartella del progetto o effettuare un "hard reset" dell'installazione.

### 4.3 Gestione dei Dati Personali (PII) e Conformità GDPR

Sebbene il software non sia un servizio SaaS, tratta dati che possono essere considerati PII (Personal Identifiable Information), come Steam ID e nickname.
*   **Minimizzazione**: Vengono scaricati solo i dati necessari per l'analisi del gioco.
*   **Diritto all'Oblio**: L'utente può utilizzare `Sanitize_Project.py` o i comandi `maint prune` per eliminare specifici dati o l'intero dataset, esercitando effettivamente il proprio diritto alla cancellazione in locale.

### 4.4 Crittografia a Riposo e in Transito

*   **In Transito (Data in Transit)**: Tutte le comunicazioni verso API esterne (Steam, Faceit, HLTV) avvengono rigorosamente su HTTPS (TLS 1.2/1.3), proteggendo i dati da intercettazione (Man-in-the-Middle).
*   **A Riposo (Data at Rest)**: I dati su disco non sono cifrati nativamente dal database SQLite (per performance), ma le credenziali sensibili sono cifrate dal sistema operativo via `keyring`. Si raccomanda agli utenti di utilizzare BitLocker o sistemi di cifratura del disco intero per proteggere la cartella del progetto.

---

## 5. Integrità del Codice e della Build (Supply Chain Security)

La sicurezza della supply chain è vitale per prevenire l'introduzione di codice malevolo o vulnerabilità durante il ciclo di sviluppo.

### 5.1 Protocollo di Audit "Anti-Placebo"

Il documento `AUDIT_PROTOCOL.md` stabilisce regole ferree per i test.
*   **Divieto di Mocking Eccessivo**: È vietato l'uso di mock per componenti critici come il database. I test devono verificare il comportamento reale. Questo previene la "sicurezza illusoria" dove tutti i test passano ma il sistema reale è vulnerabile o rotto.
*   **Verifica dei Falsi Positivi/Negativi**: Gli auditor devono cercare test che passano sempre (assert True) o che skippano silenziosamente gli errori.

### 5.2 Verifica dell'Integrità dei Binari (`audit_binaries.py`)

Per garantire che i binari distribuiti non siano stati alterati:
*   **Hashing SHA-256**: Lo strumento scansiona la cartella `dist/`, calcola l'hash SHA-256 di ogni `.exe`, `.dll` e `.pyd`.
*   **Manifesto di Integrità**: Genera un file `binary_integrity.json` che funge da "snapshot" dello stato sicuro. Questo file può essere usato per verificare che l'installazione dell'utente corrisponda esattamente alla build certificata.

### 5.3 Sicurezza della Pipeline di Build (PyInstaller & GitHub Actions)

*   **Ambiente Pulito**: Le build vengono eseguite in ambienti effimeri (GitHub Actions) o ambienti di build dedicati, riducendo il rischio di contaminazione da malware persistenti sulla macchina dello sviluppatore.
*   **Dependency Locking**: L'uso di `requirements-lock.txt` assicura che vengano installate le esatte versioni delle librerie testate, prevenendo attacchi di "Dependency Confusion" o l'introduzione di versioni vulnerabili di pacchetti terzi.

### 5.4 Rilevamento del Codice Morto e Vulnerabilità Statiche

Lo strumento `tools/dead_code_detector.py` e l'uso di linter statici aiutano a mantenere la codebase pulita.
*   **Riduzione Superficie d'Attacco**: Il codice morto (non utilizzato) è un rischio perché potrebbe contenere vulnerabilità non mantenute che un attaccante potrebbe trovare il modo di attivare. Rimuoverlo riduce la superficie d'attacco.

---

## 6. Sicurezza Operativa (OpSec) e Monitoraggio

### 6.1 Logging Strutturato e Auditing

Il sistema utilizza un framework di logging avanzato (`Programma_CS2_RENAN/observability/logger_setup`).
*   **Formato JSON**: I log critici possono essere strutturati in JSON per facilitare l'ingestione in strumenti di analisi (SIEM) se necessario.
*   **Livelli di Log**: Separazione netta tra DEBUG, INFO, WARNING, ERROR, CRITICAL. Gli eventi di sicurezza (fallimento auth, errori keyring) sono loggati a livello ERROR o CRITICAL.
*   **Rotazione**: I log vengono ruotati per evitare il riempimento del disco (DoS locale).

### 6.2 Safe Mode e Validazione Dinamica (`verify_all_safe.py`)

Prima di operazioni critiche o rilasci, lo script `tools/verify_all_safe.py` esegue una batteria di test su tutti gli script ausiliari.
*   **Esecuzione Sandbox**: Ogni tool viene lanciato in un sottoprocesso isolato.
*   **Verifica Exit Code**: Si assicura che ogni tool termini correttamente (Exit Code 0) e non crashi. Questo garantisce che gli strumenti di sicurezza stessi siano operativi e affidabili.

### 6.3 Gestione delle Risorse e Prevenzione DoS

*   **Throttling**: I comandi di ML e Ingestion supportano flag o configurazioni per limitare l'uso di CPU/RAM.
*   **Rate Limiting API**: Per evitare di essere bannati da Steam/Faceit, il sistema implementa delay e backoff nelle chiamate API (gestito nei moduli di ingestion).

---

## 7. Analisi delle Minacce e Vettori di Attacco

### 7.1 Parsing di File Demo Malformati

Il parsing dei file `.dem` (replay di CS2) è il vettore di attacco più probabile per codice esterno.
*   **Rischio**: Un file demo creato ad arte potrebbe sfruttare vulnerabilità nel parser per eseguire codice arbitrario (RCE) o causare crash (DoS).
*   **Mitigazione**:
    *   Il parser è scritto in Python (memory safe), riducendo drasticamente il rischio di Buffer Overflow tipici di C/C++.
    *   Validazione rigorosa degli header e della struttura del file prima del processamento completo.
    *   Gestione delle eccezioni granulare per isolare il fallimento di un singolo demo senza crashare l'intera pipeline di ingestion.

### 7.2 Injection Attacks (SQL & Command Injection)

*   **SQL Injection**: Mitigato dall'uso pervasivo di SQLAlchemy ORM.
*   **Command Injection**: L'uso di `subprocess.run` con liste di argomenti (invece di `shell=True`) previene l'iniezione di comandi shell malevoli quando il sistema invoca tool esterni.

### 7.3 Manipolazione della Memoria Runtime

Essendo un'applicazione locale, un utente con privilegi amministrativi può manipolare la memoria del processo.
*   **Rischio**: Cheating, modifica delle statistiche locali.
*   **Accettazione del Rischio**: Dato che l'app è per analisi personale e non un sistema anti-cheat competitivo, questo rischio è accettato. La priorità è proteggere l'utente da minacce esterne, non da se stesso. Tuttavia, il `integrity_manifest.json` aiuta a rilevare modifiche ai file su disco.

---

## 8. Procedure Operative Standard (SOP) per la Sicurezza

### 8.1 SOP-SEC-01: Inizializzazione Sicura del Sistema

**Obiettivo**: Configurare un nuovo ambiente Macena CS2 Analyzer in modo sicuro.

1.  **Installazione**: Clonare il repository o estrarre l'archivio in una directory protetta (es. non sul Desktop se condiviso).
2.  **Configurazione API Key**:
    *   Avviare la console.
    *   Usare il comando `set steam <KEY>` e `set faceit <KEY>`.
    *   Verificare nei log che appaia "Secret stored in keyring".
    *   **NON** modificare manualmente `user_settings.json` per inserire le chiavi se possibile.
3.  **Verifica Integrità**:
    *   Eseguire `tools/audit_binaries.py` (se da distribuzione buildata) per verificare che l'installazione sia conforme.
    *   Eseguire `sys audit` dalla console per verificare la salute del database.

### 8.2 SOP-SEC-02: Gestione di un Incidente di Sicurezza

**Scenario**: Sospetto di corruzione dati, malware o comportamento anomalo.

1.  **Stop Immediato**: Terminare tutti i processi Python/exe relativi a Macena (comando `svc kill-all` o Task Manager).
2.  **Isolamento**: Disconnettere la rete se si sospetta esfiltrazione (basso rischio data l'architettura, ma buona prassi).
3.  **Sanitizzazione**:
    *   Eseguire `python tools/Sanitize_Project.py`.
    *   Confermare la cancellazione di database e credenziali.
4.  **Reinstallazione**: Scaricare una nuova copia verificata del software.
5.  **Rotazione Chiavi**: Rigenerare le API Key di Steam e Faceit dai rispettivi portali web.

### 8.3 SOP-SEC-03: Audit Periodico e Manutenzione

**Frequenza**: Mensile o dopo ogni aggiornamento maggiore.

1.  **Aggiornamento Dipendenze**:
    *   `pip install --upgrade -r requirements.txt`
    *   Verificare eventuali avvisi di sicurezza sui pacchetti installati.
2.  **Database Health**:
    *   Eseguire `tools/db_health_diagnostic.py`.
    *   Risolvere eventuali inconsistenze segnalate.
3.  **Log Review**: Controllare la cartella `logs/` per errori ricorrenti o accessi anomali.

---

## 9. Piano di Risposta agli Incidenti (Incident Response)

In caso di vulnerabilità critica scoperta nel codice distribuito:

### 9.1 Identificazione e Classificazione
*   Il team di sviluppo classifica la vulnerabilità (es. CVSS score).
*   Se critica (es. RCE via demo file), viene emesso un avviso di sicurezza immediato.

### 9.2 Contenimento ed Eradicazione
*   Sviluppo di una patch di emergenza.
*   Rilascio di una nuova build con numero di versione incrementato.
*   Lo script `Sanitize_Project.py` può essere aggiornato per rimuovere artefatti specifici dell'attacco.

### 9.3 Recupero e Post-Incident Analysis
*   Gli utenti sono invitati ad aggiornare.
*   Viene pubblicato un report post-mortem (senza rivelare dettagli sfruttabili se non patchati ovunque) per trasparenza.

---

## 10. Roadmap e Sviluppi Futuri della Sicurezza

Per mantenere il livello di sicurezza adeguato alle minacce future, sono previste le seguenti implementazioni:

1.  **Firma del Codice (Code Signing)**: Firmare digitalmente l'eseguibile Windows (.exe) per garantire l'autenticità e prevenire avvisi SmartScreen.
2.  **Sandboxing del Parser**: Spostare il processo di parsing dei demo in una sandbox ancora più ristretta (es. container Docker opzionale o restrizioni OS-level più severe).
3.  **Cifratura del Database**: Implementare il supporto opzionale per SQLCipher, permettendo la cifratura trasparente del file `database.db` a riposo.
4.  **Audit Automatico delle Dipendenze**: Integrare strumenti come `pip-audit` o `safety` direttamente nella pipeline CI/CD per bloccare build con dipendenze vulnerabili note.

---

*Fine del Documento. Questo manuale è parte integrante della documentazione tecnica del progetto Macena CS2 Analyzer.*

---

## Appendice A: Approfondimenti Teorici e Framework di Riferimento

Questa sezione esplora i concetti teorici fondamentali che hanno guidato le decisioni architetturali di sicurezza in Macena CS2 Analyzer.

### A.1 La Triade CIA (Confidenzialità, Integrità, Disponibilità)

La sicurezza delle informazioni è tradizionalmente modellata sulla triade CIA. Ecco come viene applicata nel nostro contesto:

1.  **Confidenzialità (Confidentiality)**:
    *   *Definizione*: Garantire che le informazioni siano accessibili solo a chi è autorizzato.
    *   *Applicazione*: Le API Key sono protette dal `keyring` di sistema. I dati delle partite, che potrebbero rivelare strategie sensibili di un team competitivo, risiedono esclusivamente sul disco locale dell'analista e non vengono caricati su server centralizzati. L'uso di `mask_secret` nei log previene la divulgazione accidentale.

2.  **Integrità (Integrity)**:
    *   *Definizione*: Garantire che le informazioni e i sistemi siano accurati e completi, e non siano stati alterati in modo non autorizzato.
    *   *Applicazione*: Questo è il pilastro più critico per un software di analisi.
        *   Il protocollo **Anti-Placebo** assicura l'integrità logica dei risultati (l'analisi è vera?).
        *   L'hashing SHA-256 dei binari (`audit_binaries.py`) assicura l'integrità fisica dell'eseguibile (il software è quello originale?).
        *   Le transazioni atomiche del database SQLite assicurano l'integrità dei dati a riposo.

3.  **Disponibilità (Availability)**:
    *   *Definizione*: Garantire che gli utenti autorizzati abbiano accesso alle informazioni e alle risorse associate quando necessario.
    *   *Applicazione*: Essendo un software locale, la disponibilità dipende principalmente dalla stabilità del software stesso. Le misure contro il Denial of Service (DoS) locale, come la gestione delle eccezioni nel parsing dei demo e il throttling delle risorse CPU durante il training ML, servono a mantenere l'interfaccia utente responsiva e il sistema utilizzabile anche sotto carico pesante.

### A.2 Defense in Depth (Difesa in Profondità)

Il principio della "Defense in Depth" prevede l'uso di più livelli di sicurezza per proteggere gli asset. Se un livello fallisce, gli altri forniscono protezione.

*   **Livello 1: Perimetro Fisico/OS**: L'utente protegge l'accesso al proprio PC (password Windows, BitLocker).
*   **Livello 2: Sicurezza Applicativa**: Il software valida rigorosamente gli input (demo file) e gestisce le eccezioni.
*   **Livello 3: Sicurezza dei Dati**: Le credenziali sono cifrate, i dati sensibili possono essere sanitizzati.
*   **Livello 4: Audit e Monitoraggio**: I log registrano anomalie, permettendo la rilevazione post-fatto.

### A.3 Principle of Least Privilege (PoLP)

Anche in un'applicazione monoutente, il principio del privilegio minimo viene applicato:
*   Il processo di build e test (`verify_all_safe.py`) non richiede privilegi di amministratore.
*   L'accesso alle API esterne richiede solo permessi di lettura (non scrittura/modifica) sui profili utente Steam/Faceit, minimizzando il danno se le chiavi venissero compromesse.

---

## Appendice B: Manuale Tecnico degli Strumenti di Sicurezza

Questa sezione fornisce una guida operativa dettagliata per gli strumenti di sicurezza presenti nella cartella `tools/`.

### B.1 `tools/Sanitize_Project.py` - Industrial Grade Cleaner

**Scopo**: Riportare il progetto a uno stato "Tabula Rasa", eliminando dati utente, log e database.

**Codice Sorgente Rilevante**:
La classe `IndustrialSanitizer` definisce i target:
```python
self.targets = [
    {"path": ... / "user_settings.json", "action": "DELETE", ...},
    {"path": ... / "backend/storage/database.db", "action": "DELETE", ...},
    # ...
]
```

**Workflow Operativo**:
1.  L'operatore lancia `python tools/Sanitize_Project.py`.
2.  Il sistema mostra una tabella riassuntiva degli oggetti che verranno distrutti ("Action Plan").
3.  Viene richiesta una conferma esplicita (Y/N).
4.  Il sistema procede alla cancellazione fisica (unlink) dei file e allo svuotamento ricorsivo delle cartelle log.
5.  Un report finale conferma il successo.

**Troubleshooting**:
*   *Errore "Permission Denied"*: Verificare che non ci siano processi `python.exe` o `MacenaCS2Analyzer.exe` attivi che tengono in lock il database o i log. Usare `svc kill-all` prima di sanificare.

### B.2 `tools/audit_binaries.py` - Binary Integrity Verifier

**Scopo**: Generare e verificare l'impronta digitale crittografica della distribuzione compilata.

**Algoritmo**:
Utilizza SHA-256, che offre una resistenza alle collisioni adeguata per il prossimo decennio.
```python
def calculate_sha256(self, file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(8192), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
```

**Utilizzo**:
*   *Post-Build*: Dopo aver compilato con PyInstaller, lanciare lo script per generare `binary_integrity.json`. Questo file deve essere incluso nel pacchetto di distribuzione.
*   *Verifica Utente*: L'utente può ricalcolare gli hash e confrontarli con quelli nel JSON fornito per assicurarsi che il download non sia corrotto o manomesso (Man-in-the-Middle).

### B.3 `tools/verify_all_safe.py` - Dynamic Safety Harness

**Scopo**: Eseguire in sicurezza tutti gli script di manutenzione e test per validare lo stato del sistema senza causare danni.

**Logica di Sicurezza**:
*   **Filtering**: La funzione `is_safe_to_run()` esclude esplicitamente script con prefissi pericolosi come `fix_`, `reset_`, `migrate_`.
*   **Isolation**: Ogni script è lanciato come sottoprocesso indipendente (`subprocess.run`). Un crash in uno script non ferma il verificatore.
*   **Timeout**: (Implicitamente gestito dal sistema operativo, ma il design prevede esecuzioni rapide).

**Output**:
Genera un report "PASS/FAIL" per ogni componente. Un "FAIL" in questo tool indica che l'ambiente di sviluppo o di produzione è instabile e non dovrebbe essere utilizzato per analisi critiche.

---

## Appendice C: Analisi di Conformità Normativa (Compliance)

### C.1 GDPR (General Data Protection Regulation - UE 2016/679)

Sebbene Macena CS2 Analyzer sia un software eseguito localmente (on-premise/desktop) e non un servizio cloud, i principi del GDPR sono rilevanti per gli utenti europei che processano dati di terzi (es. allenatori che analizzano demo dei propri giocatori).

*   **Art. 5 (Principi applicabili al trattamento)**:
    *   *Minimizzazione*: Il software estrae dai demo solo i dati di telemetria necessari (posizioni, kill, danni), ignorando chat vocale o testuale se non strettamente funzionale (e attualmente non supportata).
    *   *Limitazione della conservazione*: Gli strumenti di `prune` permettono di cancellare dati vecchi.

*   **Art. 32 (Sicurezza del trattamento)**:
    *   Il software implementa misure tecniche adeguate (keyring, sanitizzazione) per proteggere i dati locali.

*   **Responsabilità dell'Utente (Data Controller)**:
    *   L'utente che installa il software agisce come "Titolare del Trattamento" per i dati salvati sul proprio PC. È responsabilità dell'utente assicurarsi che il PC sia protetto (password, antivirus) e che i dati non vengano diffusi illecitamente.

### C.2 CCPA (California Consumer Privacy Act)

Per gli utenti in California, il diritto alla cancellazione ("Right to Delete") è pienamente supportato tramite le funzioni di sanitizzazione e gestione del database locale. Non essendoci vendita di dati a terzi (il software non comunica con ad-tech server), molti obblighi complessi del CCPA non si applicano, semplificando la compliance.

---

## Appendice D: Glossario dei Termini di Sicurezza

*   **API Key**: Una stringa univoca utilizzata per autenticare una richiesta API. In questo progetto, equivale a una password per i servizi Steam/Faceit.
*   **Hash (SHA-256)**: Una funzione matematica che trasforma dati di lunghezza arbitraria in una stringa di lunghezza fissa (impronta digitale). Modificando anche un solo bit del file originale, l'hash cambia completamente.
*   **Keyring**: Un'interfaccia software che permette alle applicazioni di memorizzare password e chiavi in modo sicuro utilizzando i servizi di crittografia del sistema operativo ospite.
*   **Placebo (in testing)**: Un test che passa sempre, indipendentemente dalla correttezza del codice, dando una falsa sensazione di sicurezza. Il nemico numero uno del nostro Audit Protocol.
*   **Sanitizzazione**: Il processo di rimozione irreversibile di dati sensibili da un supporto di memorizzazione.
*   **SQL Injection**: Una tecnica di attacco che sfrutta la mancata validazione degli input per eseguire comandi SQL non autorizzati. Prevenuta qui tramite l'uso di ORM.
*   **Supply Chain Attack**: Un attacco che mira a compromettere il software inserendo codice malevolo durante la fase di sviluppo o distribuzione, prima che arrivi all'utente finale.

---

*Fine delle Appendici.*
