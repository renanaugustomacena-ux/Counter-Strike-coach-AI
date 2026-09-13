# Guida alla risoluzione dei problemi

## "Nessuna demo personale analizzata"

- Il tuo nome in gioco deve corrispondere al nome dentro la demo (maiuscole e minuscole non contano). Controllalo nella schermata Profilo.
- La cartella demo deve essere impostata e contenere file `.dem` completi (10 MB o più).
- Premi **Analizza demo** nella Dashboard e osserva la didascalia sotto il pulsante.
- Le partite pro non contano mai come personali, anche se un pro usa il tuo nickname.

## Servizio: Offline

Il Session Engine in background non è in esecuzione o non ha inviato un heartbeat negli ultimi cinque minuti. Riavvia l'applicazione; se resta offline, leggi `cs2_analyzer_daemon.log` nella cartella dei log. La sorveglianza automatica delle cartelle richiede il servizio; i pulsanti Analizza funzionano anche senza.

## "Backend Startup Error"

La console non è riuscita a inizializzarsi (database o percorsi). La finestra resta utilizzabile; cerca la causa in `cs2_analyzer.log` nella cartella dei log: di solito è una cartella demo che non esiste più.

## Chat del coach offline

La chat richiede Ollama in esecuzione su questo computer con il modello selezionato scaricato: `ollama pull gemma4:e2b`, poi `ollama serve`. Il menu dei modelli nella schermata Coach elenca ciò che Ollama ha a disposizione.

## Download del "modello linguistico AI"

La ricerca nella conoscenza del coach usa un piccolo modello linguistico (circa 90 MB) scaricato una sola volta, in background, dopo l'apertura della finestra. Senza di esso il coach ripiega su una ricerca per similarità più semplice; nient'altro viene bloccato.

## Database bloccato

Non aprire `database.db` con uno strumento SQLite esterno mentre l'app è in esecuzione. Un'ingestione pesante può causare brevi ritentativi, che si risolvono da soli.

## Sincronizzazione HLTV / Docker

Lo scraping HLTV in tempo reale è facoltativo e richiede Docker. Quando Docker non è disponibile l'app usa le baseline pro in cache e prosegue; l'impostazione `ENABLE_HLTV_SYNC` disattiva del tutto la sincronizzazione.

## Dove sono i log

`cs2_analyzer.log` (applicazione) e `cs2_analyzer_daemon.log` (servizio in background) si trovano nella cartella `logs` della tua posizione dati: la cartella del progetto in un'installazione da sorgente, oppure la cartella "brain" scelta nel wizard.
