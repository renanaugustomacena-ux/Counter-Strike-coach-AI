> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching -- Pipeline di Coaching Multi-Modalita

> **Autorita:** `backend/coaching/`
> **Skill:** `/ml-check`, `/api-contract-review`
> **Modulo proprietario:** `backend/services/coaching_service.py`

## Panoramica

Il pacchetto coaching e il livello di intelligenza che trasforma i dati di analisi grezzi
in feedback azionabile per il giocatore. Implementa una **pipeline di coaching a quattro
modalita** dove ciascuna modalita offre un compromesso diverso tra consigli basati sulla
conoscenza e previsioni di rete neurale. La modalita predefinita e **COPER** (Contextual
Observation Pattern Experience Retrieval), che combina un Experience Bank, recupero
conoscenza RAG e dati di riferimento di giocatori professionisti per produrre output di
coaching fondato su prove reali di partita.

Tutte le modalita di coaching sono consumate da un singolo punto di ingresso --
`backend/services/coaching_service.py` -- che seleziona la modalita attiva in base ai
flag di funzionalita `USE_COPER_COACHING`, `USE_HYBRID_COACHING`, `USE_RAG_COACHING` e
`USE_JEPA_MODEL` / `USE_RAP_MODEL` in `core/config.py`.

## Le Quattro Modalita di Coaching

| # | Modalita | Flag | Descrizione |
|---|----------|------|-------------|
| 1 | **COPER** | `USE_COPER_COACHING=True` (predefinito) | Recupero semantico Experience Bank + conoscenza RAG + Riferimenti Pro. Nessun modello ML richiesto. |
| 2 | **Hybrid** | `USE_HYBRID_COACHING=True` | Previsioni rete neurale sintetizzate con contesto RAG per output misto. |
| 3 | **RAG** | `USE_RAG_COACHING=True` | Recupero puro di conoscenza da pattern demo pro indicizzati. Nessuna inferenza ML. |
| 4 | **Neural** | `USE_JEPA_MODEL=True` o `USE_RAP_MODEL=True` | Previsioni ML pure senza augmentazione conoscenza. Richiede un checkpoint modello addestrato. |

### Flusso di Fallback del Coaching

Quando una modalita a maggiore fedelta non e disponibile (checkpoint modello mancante,
knowledge base vuota, ecc.), la pipeline degrada in modo controllato attraverso la
seguente catena:

```
Neural (ML puro)
   |  [checkpoint modello mancante o errore di inferenza]
   v
Hybrid (ML + RAG)
   |  [indice RAG vuoto o ML non disponibile]
   v
COPER (Experience Bank + RAG + Pro)
   |  [experience bank vuoto]
   v
RAG (solo recupero conoscenza)
   |  [indice conoscenza vuoto]
   v
Correzioni euristiche (fallback correction_engine.py)
```

Ogni transizione viene registrata a livello WARNING con un messaggio JSON strutturato
contenente la ragione della degradazione, cosi l'operatore sa sempre quale modalita
e attiva.

## Inventario File

| File | Esportazione Primaria | Scopo |
|------|----------------------|-------|
| `__init__.py` | API Pacchetto | Ri-esporta `HybridCoachingEngine`, `generate_corrections`, `ExplanationGenerator`, `PlayerCardAssimilator`, `get_pro_baseline_for_coach` |
| `hybrid_engine.py` | `HybridCoachingEngine` | Orchestratore centrale che sintetizza previsioni ML con recupero conoscenza RAG per insights di coaching bilanciati |
| `correction_engine.py` | `generate_corrections()` | Genera correzioni tattiche confrontando le deviazioni di performance del giocatore rispetto ai baseline professionisti |
| `nn_refinement.py` | `apply_nn_refinement()` | Scalatura pesi correzioni — moltiplica le deviazioni Z-score per pesi per-feature. NON esegue inferenza NN (nome storico) |
| `longitudinal_engine.py` | `generate_longitudinal_coaching()` | Traccia trend di performance nel tempo usando integrazione di decay baseline temporale per consigli di miglioramento a lungo termine |
| `explainability.py` | `ExplanationGenerator` | Converte tensori di previsione ML opachi in spiegazioni leggibili dall'uomo con catene di attribuzione causale |
| `pro_bridge.py` | `PlayerCardAssimilator` | Collega le stat card di giocatori professionisti a insights di coaching via comparazione basata su ruolo (entry fragger, AWPer, ecc.) |
| `token_resolver.py` | `PlayerTokenResolver` | Canonicalizza nomi giocatori usando fuzzy matching, normalizzazione leet-speak e risoluzione alias |

## Descrizioni Moduli

### hybrid_engine.py -- HybridCoachingEngine

`HybridCoachingEngine` e l'orchestratore primario per la modalita Hybrid di coaching.
Accetta un vettore di caratteristiche a 25 dimensioni (vedi `METADATA_DIM` in
`nn/config.py`), esegue inferenza ML attraverso il modello attivo (JEPA o RAP), recupera
conoscenza pertinente dall'indice RAG e fonde entrambi i segnali in una risposta di
coaching unificata. Il motore applica una strategia di fusione pesata per confidenza:
previsioni ML ad alta confidenza dominano, mentre quelle a bassa confidenza cedono
alla conoscenza RAG.

### correction_engine.py -- generate_corrections()

Funzione stateless che prende uno snapshot di performance del round del giocatore e lo
confronta con il baseline professionale (fornito da `pro_bridge.py`). Deviazioni che
superano soglie configurabili producono voci di correzione con severita
(info/warning/critical), una descrizione leggibile e la metrica specifica che ha attivato
la correzione. Questo modulo e il fallback finale quando tutte le modalita di coaching
a maggiore fedelta non sono disponibili.

### nn_refinement.py -- apply_nn_refinement()

Livello di post-elaborazione che prende correzioni euristiche da `correction_engine.py`
e le raffina usando una rete neurale addestrata. Ogni correzione riceve un punteggio di
confidenza (0.0--1.0). Le correzioni sotto la soglia di confidenza vengono soppresse per
ridurre il rumore. Il passo di raffinamento e opzionale e si attiva solo quando un
checkpoint di modello addestrato e disponibile.

### longitudinal_engine.py -- generate_longitudinal_coaching()

Genera consigli di coaching basati su trend di performance attraverso piu partite o
sessioni. Usa il decay baseline temporale da
`backend/processing/baselines/pro_baseline.py` (`TemporalBaselineDecay`) per pesare le performance recenti piu
delle precedenti. Produce indicatori di direzione del trend
(miglioramento/peggioramento/stabile) per ogni metrica tracciata e adatta i consigli
di conseguenza.

### explainability.py -- ExplanationGenerator

Implementa la spiegabilita del modello decomponendo le previsioni della rete neurale in
spiegazioni leggibili. Usa attribuzione delle caratteristiche (quale delle 25 dimensioni
di input ha contribuito maggiormente alla previsione) e catene di ragionamento causale
per spiegare *perche* il modello raccomanda una particolare azione. Fondamentale per
costruire la fiducia del giocatore nei consigli di coaching guidati da ML.

### pro_bridge.py -- PlayerCardAssimilator

Colma il divario tra le statistiche dei giocatori professionisti (da `hltv_metadata.db`)
e la pipeline di coaching. Il `PlayerCardAssimilator` carica le stat card dei pro e
esegue comparazioni basate su ruolo: se l'utente gioca come entry fragger, le sue
statistiche vengono confrontate con quelle degli entry fragger professionisti.
L'helper `get_pro_baseline_for_coach()` fornisce un dizionario baseline pronto all'uso
per il motore di correzione.

### token_resolver.py -- PlayerTokenResolver

Risolve riferimenti ambigui di nomi giocatore a identita canoniche. Gestisce sfide comuni
nella nomenclatura CS2: sostituzioni leet-speak (es. "s1mple" vs "simple"), prefissi
clan tag, omoglifi Unicode e corrispondenze parziali di nomi. Usa fuzzy string matching
con soglie di similarita configurabili. Essenziale per abbinare nomi forniti dall'utente
a voci nel database di giocatori professionisti.

## Integrazione con il Livello Servizi

```
coaching_service.py
    |
    +-- seleziona modalita coaching (COPER / Hybrid / RAG / Neural)
    |
    +-- chiama hybrid_engine.py (modalita Hybrid)
    |       |-- inferenza ML (modello JEPA o RAP)
    |       +-- recupero RAG (knowledge/)
    |
    +-- chiama correction_engine.py (tutte le modalita)
    |       +-- pro_bridge.py (baseline professionale)
    |
    +-- chiama nn_refinement.py (se modello disponibile)
    |
    +-- chiama longitudinal_engine.py (se dati storici presenti)
    |
    +-- chiama explainability.py (se previsioni ML usate)
    |
    +-- restituisce CoachingResponse al livello UI
```

L'orchestratore `coaching_service.py` inietta anche contesto di baseline temporale da
`backend/processing/baselines/pro_baseline.py` (`TemporalBaselineDecay`), assicurando che i consigli di coaching
tengano conto di come il livello di abilita del giocatore si e evoluto nelle sessioni
recenti.

## Note di Sviluppo

- **Disciplina flag funzionalita:** Non bypassare mai i flag. La modalita di coaching viene
  selezionata esclusivamente attraverso i flag di `core/config.py`. Hard-codare una modalita
  causa fallimenti nei test.
- **Contratto 25-dim:** Ogni modulo che tocca il vettore di caratteristiche deve rispettare
  `METADATA_DIM=25`. Vedi la tabella Contratto Dimensionale nel `CLAUDE.md` del progetto root.
- **Logging strutturato:** Tutti i moduli usano `get_logger("cs2analyzer.coaching.<modulo>")`.
  Le transizioni di fallback loggano a livello WARNING con correlation ID.
- **Thread safety:** La pipeline di coaching puo essere invocata dal thread Teacher del
  Quad-Daemon. Tutto lo stato condiviso deve essere acceduto tramite accessor thread-safe,
  mai globali a livello di modulo.
- **Testing:** I test risiedono in `Programma_CS2_RENAN/tests/`. Usa le fixture
  `mock_db_manager` e `torch_no_grad` per i test di coaching.

## Dipendenze

- **PyTorch** -- Inferenza rete neurale per modalita Hybrid e Neural
- **sentence-transformers** -- Generazione embedding per recupero RAG ed Experience Bank
- **SQLModel** -- Persistenza Experience Bank
- **scikit-learn** -- Metriche di similarita per risoluzione token (opzionale)
