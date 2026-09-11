> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching -- Pipeline di Coaching Multi-Modalita

> **Autorita:** `backend/coaching/`
> **Skill:** `/ml-check`, `/api-contract-review`
> **Modulo proprietario:** `backend/services/coaching_service.py`

## Panoramica

Il pacchetto coaching e il livello di intelligenza che trasforma i dati di analisi grezzi
in feedback azionabile per il giocatore. Implementa una **pipeline di coaching a quattro
modalita** dove ciascuna modalita offre un compromesso diverso tra consigli basati sulla
conoscenza e previsioni di rete neurale. La modalita predefinita e **COPER** ("Context Optimized with Prompt, Experience,
and Replay"), che combina un Experience Bank, recupero conoscenza RAG e dati di
riferimento di giocatori professionisti per produrre output di coaching fondato su prove
reali di partita.

Tutte le modalita di coaching sono consumate da un singolo punto di ingresso --
`backend/services/coaching_service.py` -- che seleziona la modalita attiva in base ai
flag di funzionalita `USE_COPER_COACHING`, `USE_HYBRID_COACHING` e `USE_RAG_COACHING`
(il flag separato `USE_JEPA_MODEL` controlla l'adattatore di insight JEPA, non la
selezione della modalita).

## Le Quattro Modalita di Coaching

| # | Modalita | Flag | Descrizione |
|---|----------|------|-------------|
| 1 | **COPER** | `USE_COPER_COACHING=True` (predefinito) | Recupero semantico Experience Bank + conoscenza RAG + Riferimenti Pro. Richiede nome mappa + dati tick. |
| 2 | **Hybrid** | `USE_HYBRID_COACHING=True` (predefinito False) | Z-score di deviazione dal baseline sintetizzati con contesto RAG. Richiede statistiche giocatore. |
| 3 | **Traditional + RAG** | `USE_RAG_COACHING=True` (predefinito False) | Motore di correzione potenziato con recupero conoscenza tattica. Nessuna inferenza ML. |
| 4 | **Traditional** | _(nessuno — sempre disponibile)_ | Motore di correzione puro basato su deviazione. Zero dipendenze esterne; fallback definitivo. |

### Flusso di Fallback del Coaching

Quando una modalita a maggiore fedelta non e disponibile (modello mancante,
knowledge base vuota, ecc.), la pipeline degrada in modo controllato attraverso la
seguente catena:

```
COPER (Experience Bank + RAG + Pro)
   |  [errore/timeout, o dati mappa/tick mancanti]
   v
Hybrid (baseline Z + RAG)
   |  [disabilitato, statistiche giocatore mancanti, o errore]
   v
Traditional + RAG (motore di correzione + recupero conoscenza)
   |  [USE_RAG_COACHING disabilitato]
   v
Correzioni euristiche Traditional (correction_engine.py — terminale)
```

Ogni transizione viene registrata a livello WARNING con un messaggio contenente
la ragione della degradazione, cosi l'operatore sa sempre quale modalita e attiva.

Nota: la catena sopra e una *scala di priorita*. Al momento dell'errore, un
fallimento/timeout di COPER passa a Hybrid solo quando `USE_HYBRID_COACHING` e abilitato
e le statistiche giocatore sono disponibili — altrimenti arriva direttamente a Traditional;
un fallimento di Hybrid arriva sempre a Traditional. Il livello Traditional + RAG viene
scelto solo al momento del dispatch quando ne COPER ne Hybrid sono selezionati e
`USE_RAG_COACHING` e abilitato.

## Inventario File

| File | Esportazione Primaria | Scopo |
|------|----------------------|-------|
| `__init__.py` | API Pacchetto | Ri-esporta `HybridCoachingEngine`, `generate_corrections`, `ExplanationGenerator`, `PlayerCardAssimilator`, `get_pro_baseline_for_coach` |
| `hybrid_engine.py` | `HybridCoachingEngine` | Orchestratore modalita Hybrid: deviazioni Z-score dal baseline + recupero conoscenza RAG + punteggio di confidenza |
| `correction_engine.py` | `generate_corrections()` | Classifica deviazioni Z-score precalcolate nelle top-3 correzioni ponderate (scalatura confidenza e importanza) |
| `nn_refinement.py` | `apply_nn_refinement()` | Scalatura pesi correzioni — moltiplica le deviazioni Z-score per pesi per-feature. NON esegue inferenza NN (nome storico) |
| `longitudinal_engine.py` | `generate_longitudinal_coaching()` | Traccia trend di performance nel tempo usando integrazione di decay baseline temporale per consigli di miglioramento a lungo termine |
| `explainability.py` | `ExplanationGenerator` | Generazione narrativa basata su template per asse di abilita, piu classificazione severita insight |
| `pro_bridge.py` | `PlayerCardAssimilator` | Assimila stat card di giocatori professionisti in baseline formato coach e archetipi |
| `token_resolver.py` | `PlayerTokenResolver` | Recupera "Player Token" statici dei pro (stat card) da `hltv_metadata.db` e confronta statistiche partita con essi |
| `jepa_insight_adapter.py` | `JEPAInsightAdapter` | Converte le uscite sigmoid del coaching-head JEPA in oggetti `InsightCandidate`. Mappa i primi 10 delle 25 dimensioni a 5 assi tattici. Gating per maturità; attivato dal flag `USE_JEPA_MODEL` (default `False`). Conforme NO-WALLHACK — consuma solo dati POV del giocatore. |

## Descrizioni Moduli

### hybrid_engine.py -- HybridCoachingEngine

`HybridCoachingEngine` e l'orchestratore primario per la modalita Hybrid di coaching.
La sua pipeline: calcola le deviazioni Z-score delle `player_stats` rispetto al baseline
pro (opzionalmente un baseline contestuale dalla stat card di un pro specifico), recupera
conoscenza pertinente dall'indice RAG e sintetizza insight unificati dalle deviazioni e
dal contesto della conoscenza. Contributi neurali entrano nella catena di insight tramite
`JEPAInsightAdapter` quando il flag `USE_JEPA_MODEL` e abilitato (26-HYB-01). La
confidenza dell'insight combina |Z| con conteggi di utilizzo della conoscenza; baseline
di fallback obsoleti marcano ogni insight con un avviso di baseline degradato (F4-02).

### correction_engine.py -- generate_corrections()

Funzione stateless che prende deviazioni Z-score *precalcolate* (il confronto con il
baseline avviene a monte) piu `rounds_played`. Ogni deviazione viene scalata da un fattore
di confidenza (`rounds_played / 300`, limitato a 1.0) e un peso di importanza per-feature
(sovrascrivibile tramite l'impostazione `COACH_WEIGHT_OVERRIDES`); le top-3 correzioni
ordinate per `|weighted_z| * importance` vengono restituite come dizionari (`feature`,
`weighted_z`, `importance`). Severita e narrative leggibili vengono aggiunte a valle da
`coaching_service.py` usando `ExplanationGenerator`. Questo modulo e il fallback finale
quando tutte le modalita di coaching a maggiore fedelta non sono disponibili.

### nn_refinement.py -- apply_nn_refinement()

Passo di scalatura pesi correzioni (DA-03: il nome storico e fuorviante). Prende
correzioni euristiche da `correction_engine.py` e moltiplica ogni `weighted_z` per
`(1 + feature_weight)` da un dizionario di aggiustamenti fornito. Questa e pura aritmetica
— nessuna rete neurale viene caricata, nessuna inferenza modello avviene, nessun punteggio
di confidenza viene calcolato. Il dizionario di aggiustamenti *puo* originare dall'output
di un modello NN a monte, ma questo modulo e una moltiplicazione scalare. Chiamato
condizionalmente da `correction_engine.py` solo quando `nn_adjustments` non e vuoto — il
percorso di servizio corrente non passa mai aggiustamenti, quindi questo passo e dormiente
in produzione.

### longitudinal_engine.py -- generate_longitudinal_coaching()

Genera consigli di coaching basati su trend di performance attraverso piu partite o
sessioni. Usa il decay baseline temporale da
`backend/processing/baselines/pro_baseline.py` (`TemporalBaselineDecay`) per pesare le performance recenti piu
delle precedenti. Produce indicatori di direzione del trend
(miglioramento/peggioramento/stabile) per ogni metrica tracciata e adatta i consigli
di conseguenza.

### explainability.py -- ExplanationGenerator

Generazione narrativa basata su template: `generate_narrative()` renderizza template
per-asse (`SkillAxes` MECHANICS / POSITIONING / UTILITY / TIMING / DECISION) con
contesto dinamico (posizione, arma, magnitudine delta). Delta sotto la soglia di silenzio
(|delta| < 0.2) non producono feedback — "il silenzio e un'azione valida" — e un filtro
per livello di abilita semplifica l'output per principianti. `classify_insight_severity()`
mappa |delta| a High / Medium / Low. Usato da `coaching_service.py` per trasformare
Z-score di correzione in messaggi di coaching leggibili.

### pro_bridge.py -- PlayerCardAssimilator

Colma il divario tra le statistiche dei giocatori professionisti (da `hltv_metadata.db`)
e la pipeline di coaching. Il `PlayerCardAssimilator` traduce una `ProPlayerStatCard`
nel formato baseline del coach su scale per-round (KPR/DPR — P3-02), con normalizzazione
difensiva di valori in forma percentuale legacy (V-2), e classifica l'archetipo del pro
tramite `get_player_archetype()` (Star Fragger / Support Anchor / Sniper Specialist /
All-Rounder). L'helper `get_pro_baseline_for_coach()` fornisce un dizionario baseline
contestuale pronto all'uso, utilizzato da `hybrid_engine.py` quando un riferimento pro
e selezionato.

### token_resolver.py -- PlayerTokenResolver

Recupera "Player Token" statici dei pro per l'AI Coach: `get_player_token()` cerca un
professionista per nickname esatto in `hltv_metadata.db` (`ProPlayer` + ultimo
`ProPlayerStatCard`) e assembla un dizionario token strutturato (identita, metriche core,
baseline tattici, statistiche dettagliate granulari, metadati).
`compare_performance_to_token()` restituisce un "Correction Delta" (delta rating / ADR /
KAST / HS piu un flag di underperformance) per valutazione esperta contro il token.
Il fuzzy name matching risiede altrove (`nickname_resolver.py`, usato da
`backend/services/player_lookup.py`), non in questo modulo.

## Integrazione con il Livello Servizi

```
coaching_service.py
    |
    +-- seleziona modalita coaching (COPER / Hybrid / Traditional+RAG / Traditional)
    |
    +-- chiama hybrid_engine.py (modalita Hybrid)
    |       |-- deviazioni Z-score dal baseline (baseline contestuali pro_bridge.py)
    |       +-- recupero RAG (knowledge/)
    |
    +-- chiama correction_engine.py (modalita Traditional e fallback per errori)
    |       +-- nn_refinement.py (solo se nn_adjustments passati -- dormiente oggi)
    |
    +-- chiama longitudinal_engine.py (trend da compute_trend())
    |
    +-- chiama explainability.py (narrative + severita per correzioni)
    |
    +-- salva righe CoachingInsight nel database (consumate dalla UI)
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

- **PyTorch** -- Inferenza modello adattatore insight JEPA in `jepa_insight_adapter.py`
- **sentence-transformers** -- Generazione embedding per recupero RAG ed Experience Bank
- **SQLModel** -- Accesso database (conoscenza tattica, insight di coaching, stat card pro)
