# Guida alle funzioni

## Dashboard

La barra di stato mostra **Coach** (inattivo o in analisi), **Servizio** (il Session Engine in background: *Online* finché il suo heartbeat è recente, *Offline* altrimenti) e **Partite** (le tue demo analizzate). Sotto: la tua ultima partita con la sparkline del rating, la scheda focus, la striscia delle partite recenti, le schede **Analisi demo** e **Ingestione demo pro** con i selettori di cartella e i pulsanti Analizza, le scorciatoie Connettività (Profilo, Steam Config, FaceIt Config), le scorciatoie di Analisi tattica e la scheda **Stato addestramento**: l'azione **Addestra il coach** con i preset di passi, un pulsante **Ferma** mentre un'esecuzione è in corso, il modello attivo addestrato su questa macchina (oppure "Nessun modello addestrato su questa macchina finora") e l'avanzamento in tempo reale dei passi, le loss e la stima del tempo dell'esecuzione corrente.

## AI Coach

**Confidenza del modello** con i suoi driver (il conteggio campioni è dato dalle tue demo analizzate), **Consigli recenti** (i tuoi consigli, ordinati per gravità, i primi tre in evidenza) e la chat. Le risposte arrivano da un modello Ollama locale (predefinito `gemma4:e2b`) che riceve le tue analisi e la libreria pro come contesto ed è istruito a non descrivere mai i numeri di altri giocatori come tuoi.

## Storico partite

Ogni partita analizzata. La didascalia in alto separa *N personali · M riferimento pro*; ogni riga riporta rating, K/D, ADR, KAST e percentuale di colpi alla testa. Aprendo una riga si va al Dettaglio partita.

## Dettaglio partita

Quattro schede: **Panoramica** (riquadri principali, striscia dei round, componenti HLTV 2.0, arricchimento uccisioni, utility per round), **Round**, **Economia** e **Momenti salienti**. Una partita pro in cui non hai giocato ha il titolo *Demo pro · giocatore — non sei tu* e mostra le righe di quel giocatore.

## Analisi avanzate

Le tue medie (rating, partite, K/D, ADR, KAST), il tuo percentile rispetto alla coorte pro, l'andamento del rating, punti di forza e debolezza rispetto alla media pro, i riquadri per mappa e l'efficacia delle utility. Senza demo personali mostra uno stato vuoto più un blocco *Riferimento pro* che media le partite di altri giocatori: materiale di riferimento, non la tua prestazione.

## Analizzatore tattico

Un replay 2D di una demo: giocatori, utility, bomba, scorrimento dei round e momenti critici. Le sovrapposizioni "ghost" di un modello addestrato compaiono solo quando quel modello è abilitato nelle impostazioni.

## Confronto pro

Confronta le schede statistiche di due giocatori pro dai metadati HLTV; il pulsante Dettagli apre la pagina del giocatore.

## Impostazioni

**Aspetto** (tema, carattere, sfondo), **Analisi e percorsi** (cartella demo, cartella demo pro, modalità di ingestione, Avvia ingestione) e **Lingua** (English, Italiano, Português).
