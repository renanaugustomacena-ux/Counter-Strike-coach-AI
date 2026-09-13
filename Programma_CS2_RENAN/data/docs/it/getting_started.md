# Primi passi con Macena CS2 Analyzer

## 1. Chi sei nei dati

L'analyzer ti riconosce dal tuo **nome in gioco**, il nickname che CS2 mostra nel tabellone. Impostalo nel wizard iniziale o più tardi nella schermata **Profilo** (Dashboard → Connettività → Profilo). Il confronto è esatto ma non distingue maiuscole e minuscole, e deve essere lo stesso nome che compare dentro le tue demo. Non serve collegare nessun account: la schermata Steam Config è un extra facoltativo per le statistiche del profilo Steam e non ha alcun ruolo nel distinguere i tuoi round da quelli degli altri nove giocatori.

## 2. Due cartelle, due tipi di demo

- **Cartella demo** (wizard, oppure Impostazioni → Analisi e percorsi): le tue partite. Tutto ciò che viene importato da qui è *tuo* e alimenta lo Storico partite, le Analisi avanzate e il coach.
- **Cartella demo pro** (Impostazioni → Analisi e percorsi): partite professionistiche che hai scaricato. Costruiscono la libreria di riferimento con cui l'analyzer ti confronta e non vengono mai mostrate come tua prestazione.

CS2 salva le tue demo nella cartella replay di Steam: `...\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays\` su Windows, `~/.steam/steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/replays/` su Linux. I file sotto i 10 MB vengono ignorati come incompleti.

## 3. Analizza

Nella Dashboard premi **Analizza demo** (la tua cartella) oppure **Analizza demo pro** (la cartella pro). Ogni nuovo `.dem` viene letto tick per tick e le statistiche per partita, i round e le posizioni finiscono nel database locale; una partita completa richiede qualche minuto. La didascalia sotto ogni pulsante riporta quante demo sono state analizzate. Quando il servizio in background è online (chip **Servizio**), sorveglia da solo entrambe le cartelle e mette in coda i file nuovi.

## 4. Cosa si sblocca e quando

- Lo **Storico partite** elenca le tue partite e, separatamente, le partite pro della libreria.
- **Analisi avanzate** e **AI Coach** usano solo le tue demo. Senza demo analizzate mostrano uno stato vuoto onesto; le Analisi avanzate aggiungono un blocco *Riferimento pro* chiaramente etichettato, costruito dalle partite di altri giocatori.
- La **chat del coach** richiede [Ollama](https://ollama.com/download) in esecuzione su questo computer con il modello `gemma4:e2b` scaricato; la schermata Coach indica se è online.
- La **confidenza del modello** cresce con le tue demo analizzate: 50% fino a 49 demo, 80% da 50, 100% da 200.

## 5. Allenare il coach

Il coach neurale impara dalle partite analizzate nel database, le tue e la libreria pro. Nella Dashboard la scheda **Stato addestramento** offre **Addestra il coach**: scegli un preset di passi (200 per un controllo rapido, 2 000 standard, 20 000 per l'esecuzione completa, che su CPU richiede ore) e premi il pulsante. Lo stesso pulsante è nelle Impostazioni accanto ad Avvia ingestione.

L'addestramento non gira mai dentro la finestra: la richiesta va al servizio in background (il chip **Servizio** deve essere *Online*), che assegna la divisione train/validazione, esporta gli shard degli episodi nella tua cartella dati, addestra l'encoder JEPA v2 e registra l'esecuzione. La scheda mostra l'avanzamento dei passi, le loss e una stima del tempo; **Ferma** termina l'esecuzione a un checkpoint ripristinabile. Alla fine la scheda indica il modello attivo con numero di passi, data e numero di demo. Con troppo poche demo analizzate l'esecuzione viene saltata e la scheda spiega perché.

Cosa l'addestramento non fa ancora: il testo dei consigli del coach non usa l'encoder addestrato finché non arrivano i prossimi passi del piano del nucleo neurale, quindi la formulazione degli insight non cambia dopo un'esecuzione.

Da una copia del sorgente la riga di comando funziona ancora:

```bash
python run_full_training_cycle.py --model-type jepa_v2
```
