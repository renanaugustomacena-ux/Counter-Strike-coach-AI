> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Analysis — Motori di Teoria dei Giochi e Statistica

**Autorevolezza:** Implementazione Phase 6 Game Theory + moduli fondamentali Phase 1B.
**Livello di competenza:** Avanzato — Inferenza bayesiana, teoria dell'informazione, ricerca avversariale, classificazione neurale.

---

## Panoramica

Questa directory contiene 11 motori analitici che costituiscono il livello di intelligenza tattica del sistema di coaching CS2. Trasformano i dati grezzi delle demo (posizioni tick, eventi kill, snapshot economici, lanci utility) in consigli di coaching utilizzabili tramite teoria dei giochi, modellazione probabilistica e analisi statistica.

Ogni modulo segue il pattern factory function per accesso singleton thread-safe. Tutti i motori sono orchestrati da `backend/services/coaching_service.py` ed esposti alla UI attraverso l'analysis orchestrator.

---

## Inventario dei File

| File | Classi Principali | Factory Function | Scopo |
|------|-------------------|------------------|-------|
| `belief_model.py` | `DeathProbabilityEstimator`, `BeliefState`, `AdaptiveBeliefCalibrator` | `get_death_estimator()` | Probabilita di morte bayesiana con calibrazione online |
| `win_probability.py` | `WinProbabilityPredictor`, `WinProbabilityNN`, `GameState` | `get_win_predictor()` | Predizione neurale di vittoria round da stato di gioco |
| `blind_spots.py` | `BlindSpotDetector`, `BlindSpot` | `get_blind_spot_detector()` | Decisioni subottimali ricorrenti vs. game tree |
| `engagement_range.py` | `EngagementRangeAnalyzer`, `NamedPositionRegistry`, `EngagementProfile` | `get_engagement_range_analyzer()` | Profilo distanze kill e annotazione callout |
| `entropy_analysis.py` | `EntropyAnalyzer`, `UtilityImpact` | `get_entropy_analyzer()` | Entropia di Shannon per efficacia utility |
| `deception_index.py` | `DeceptionAnalyzer`, `DeceptionMetrics` | `get_deception_analyzer()` | Quantificazione dell'inganno tattico |
| `game_tree.py` | `ExpectiminimaxSearch`, `OpponentModel`, `GameNode` | `get_game_tree_search()` | Albero decisionale avversariale con nodi chance |
| `role_classifier.py` | `RoleClassifier`, `RoleProfile` | `get_role_classifier()` | Classificazione neurale + euristica a 5 ruoli |
| `utility_economy.py` | `UtilityAnalyzer`, `EconomyOptimizer`, `EconomyDecision` | `get_utility_analyzer()`, `get_economy_optimizer()` | Efficienza granate e ottimizzazione buy round |
| `momentum.py` | `MomentumTracker`, `MomentumState` | `get_momentum_tracker()` | Momentum round con rilevamento tilt |
| `movement_quality.py` | `MovementQualityAnalyzer` | `get_movement_quality_analyzer()` | Rilevatore di errori di posizionamento (paper MLMove, 4 pattern) |
| `__init__.py` | _(ri-esporta tutti i simboli pubblici)_ | _(tutte le factory function)_ | Superficie API del package |

---

## Descrizioni dei Moduli

### 1. Modelli Probabilistici

#### belief_model.py — Valutazione Bayesiana della Morte

Stima `P(death | belief, HP, armor, weapon_class)` usando un aggiornamento bayesiano logistico. Il dataclass `BeliefState` cattura l'asimmetria informativa: nemici visibili, conteggio nemici inferiti, eta dell'informazione ed esposizione posizionale. La minaccia decade esponenzialmente tramite `THREAT_DECAY_LAMBDA` (default 0.1, calibrabile).

L'`AdaptiveBeliefCalibrator` estende la calibrazione con tre pipeline:
- **Prior per fascia HP** dai tassi storici di morte round (raggruppati in full/damaged/critical).
- **Moltiplicatori letalita armi** dai rapporti kill per classe d'arma, normalizzati a rifle = 1.0.
- **Lambda decay della minaccia** adattato tramite minimi quadrati log-linearizzati su bin di information-age.

Tutti i valori calibrati sono limitati da safety bounds e persistiti come righe `CalibrationSnapshot` per osservabilita. La funzione helper `extract_death_events_from_db()` estrae i dati di calibrazione da `RoundStats` con un limite di `MAX_CALIBRATION_SAMPLES = 5000`.

#### win_probability.py — Predizione Neurale della Vittoria

Una rete neurale feedforward a 12 feature (64 -> 32 -> 1 con sigmoid) predice la probabilita di vittoria del round in tempo reale. Il dataclass `GameState` cattura economia, conteggio giocatori, utility, controllo mappa, tempo, stato bomba e lato. Normalizzazione feature: economia / 16000, giocatori / 5, tempo / 115, utility / 5.

Il post-processing euristico sovrascrive l'output neurale per casi deterministici (0 vivi = 0%, 0 nemici = 100%) e applica clamp di vantaggio giocatori e aggiustamenti per bomba piazzata. La validazione checkpoint (regola A-12) impedisce il caricamento incrociato del modello trainer a 9 dimensioni nel predictor a 12 dimensioni.

---

### 2. Analisi Tattica

#### blind_spots.py — Rilevamento Debolezze Strategiche

Confronta le azioni del giocatore con le raccomandazioni ottimali di `ExpectiminimaxSearch` attraverso i round storici. Classifica gli stati di gioco in situazioni leggibili (es. "1v3 clutch", "post-plant advantage", "eco round") e aggrega le discrepanze per frequenza e impatto sulla probabilita di vittoria.

Il metodo `generate_training_plan()` produce un piano di coaching in linguaggio naturale mirato ai top-N blind spot piu impattanti, con raccomandazioni specifiche per tipo di azione (push, hold, rotate, use_utility).

#### engagement_range.py — Profilazione Distanze Kill

Calcola le distanze euclidee dei kill da posizioni 3D e le classifica in quattro fasce: close (<500u), medium (500-1500u), long (1500-3000u), extreme (>3000u). L'`EngagementProfile` viene confrontato con le baseline pro specifiche per ruolo (AWPer, Entry, Support, Lurker, IGL, Flex) con una soglia di deviazione del 15%.

Include `NamedPositionRegistry` con 60+ posizioni callout hardcoded su 9 mappe competitive (Mirage, Inferno, Dust2, Anubis, Nuke, Ancient, Overpass, Vertigo, Train). Supporta estensione JSON per callout della community. Gli eventi kill sono annotati con la posizione nominata piu vicina per output leggibile.

#### entropy_analysis.py — Valutazione Utility basata sulla Teoria dell'Informazione

Misura l'entropia di Shannon `H = -sum(p * log2(p))` delle distribuzioni posizionali nemiche prima e dopo i lanci utility. Le posizioni sono discretizzate su una griglia 32x32 (configurabile). Il delta di entropia quantifica il guadagno informativo di ogni lancio, normalizzato rispetto ai massimi teorici per tipo di utility (smoke: 2.5 bit, molotov: 2.0, flash: 1.8, HE: 1.5).

La thread safety e mantenuta tramite `_buffer_lock` che protegge il buffer griglia pre-allocato. Il metodo `rank_utility_usage()` ordina i lanci per efficacia per l'output di coaching.

#### deception_index.py — Quantificazione dell'Inganno Tattico

Calcola un indice di inganno composito da tre sotto-metriche:
- **Tasso fake flash** (peso 0.25): frazione di flashbang che non accecano nemici entro 128 tick (~2s). Rilevato tramite `searchsorted` vettorizzato sui tick degli eventi blind.
- **Tasso rotation feint** (peso 0.40): inversioni di direzione significative (>108 gradi) nei percorsi di movimento campionati, normalizzate per estensione mappa.
- **Punteggio sound deception** (peso 0.35): rapporto crouch inverso come proxy per generazione deliberata di rumore vs. movimento silenzioso.

Il metodo `compare_to_baseline()` produce output di coaching in linguaggio naturale confrontando le metriche del giocatore con le baseline pro.

---

### 3. Ottimizzazione Decisionale

#### game_tree.py — Ricerca Expectiminimax

Modella la strategia round CS2 come un albero alternato max/min/chance con quattro azioni tattiche: push, hold, rotate, use_utility. I nodi foglia sono valutati da `WinProbabilityPredictor` (caricato in modo lazy per evitare import circolari).

L'`OpponentModel` adatta le distribuzioni delle azioni usando:
- Prior per fascia economica (eco/force/full_buy).
- Aggiustamenti per lato (T push di piu, CT hold di piu).
- Modificatori per vantaggio giocatori e pressione temporale.
- Blending EMA con profili appresi una volta disponibili 10+ round di dati.

Funzionalita prestazionali: transposition table (`_TT_MAX_SIZE = 10000`), hashing deterministico dello stato, budget nodi configurabile (`DEFAULT_NODE_BUDGET = 1000`). Il metodo `suggest_strategy()` restituisce raccomandazioni in linguaggio naturale con probabilita di vittoria e livello di confidenza.

#### role_classifier.py — Classificazione Neurale a 5 Ruoli

Architettura a doppio classificatore che combina scoring euristico ponderato con un'opinione secondaria neurale:
- **Euristico**: calcola punteggi di affinita per ruolo dalle statistiche (AWP kill ratio, entry rate, assist rate, survival rate, solo kills) rispetto a soglie apprese da `RoleThresholdStore`.
- **Neurale**: head softmax a 5 classi caricata da checkpoint (`load_role_head()`), con normalizzazione feature usando statistiche di training.
- **Consensus**: l'accordo aumenta la confidenza (+0.1), il neurale sovrascrive l'euristico solo con margine sufficiente (+0.1).

Il guard cold-start restituisce FLEX con 0% confidenza quando `RoleThresholdStore` non ha dati appresi. La classificazione a livello di team (`classify_team()`) impone vincoli di composizione (massimo 1 AWPer). Il metodo `audit_team_balance()` rileva debolezze strutturali (Entry mancante, Lurker duplicati, ecc.).

I consigli di coaching specifici per ruolo vengono recuperati tramite RAG (`KnowledgeRetriever`) con fallback a `_FALLBACK_TIPS` statici.

---

### 4. Economia e Risorse

#### utility_economy.py — Efficienza Granate e Decisioni Buy

`UtilityAnalyzer` valuta ogni tipo di utility rispetto alle baseline pro: molotov (35 dmg/lancio), HE (25 dmg/lancio), flash (1.2 nemici/flash), smoke (0.9 tasso utilizzo). Genera raccomandazioni per tipo quando l'efficacia < 50% e calcola l'impatto economico in dollari.

`EconomyOptimizer` raccomanda decisioni d'acquisto (full-buy, force-buy, half-buy, eco, pistol) basandosi su denaro corrente, numero round, lato, differenziale punteggio e loss bonus. Supporta formati MR12 (default CS2) e MR13 (legacy) tramite mapping `HALF_ROUND` configurabile. Gestisce casi speciali per pistol round e round critici al cambio meta.

#### momentum.py — Tracciamento del Momentum Psicologico

Modella il momentum come un moltiplicatore a decadimento temporale (limitato [0.7, 1.4]) guidato da serie di vittorie/sconfitte. Le serie vittoriose aggiungono +0.05 per round; le serie di sconfitte sottraggono -0.04 (asimmetrico per riflettere il vantaggio economico CS2). Il momentum decade esponenzialmente tra round saltati (`decay_rate = 0.15`) e si resetta al cambio meta (round 13 MR12, round 16 MR13).

Il rilevamento tilt si attiva quando il moltiplicatore < 0.85 (~3 sconfitte consecutive). La funzione helper `predict_performance_adjustment()` scala i rating base del giocatore tramite il moltiplicatore momentum. La funzione `from_round_stats()` costruisce una timeline completa di momentum da record `RoundStats`.

---

## Flusso di Integrazione

```
Demo Parser (demoparser2)
    |
    v
Feature Engineering (vectorizer.py, 25-dim)
    |
    +--> WinProbabilityPredictor ----+
    |                                |
    +--> DeathProbabilityEstimator --+--> BlindSpotDetector
    |                                |        |
    +--> EntropyAnalyzer ------------+        v
    |                                |   Piano di Allenamento
    +--> DeceptionAnalyzer ----------+
    |                                |
    +--> EngagementRangeAnalyzer ----+--> Coaching Service
    |                                |    (coaching_service.py)
    +--> RoleClassifier -------------+        |
    |                                |        v
    +--> MomentumTracker -----------+    Analysis Orchestrator
    |                                |    (analysis_orchestrator.py)
    +--> UtilityAnalyzer -----------+        |
    |                                |        v
    +--> EconomyOptimizer ----------+    UI / Report
    |                                |
    +--> ExpectiminimaxSearch ------+
              |
              v
         OpponentModel
```

---

## Export delle Factory Function

Tutte le factory function sono ri-esportate da `__init__.py`:

```python
from Programma_CS2_RENAN.backend.analysis import (
    get_death_estimator,        # -> DeathProbabilityEstimator
    get_win_predictor,          # -> WinProbabilityPredictor
    get_blind_spot_detector,    # -> BlindSpotDetector
    get_engagement_range_analyzer,  # -> EngagementRangeAnalyzer
    get_entropy_analyzer,       # -> EntropyAnalyzer
    get_deception_analyzer,     # -> DeceptionAnalyzer
    get_game_tree_search,       # -> ExpectiminimaxSearch
    get_role_classifier,        # -> RoleClassifier
    get_utility_analyzer,       # -> UtilityAnalyzer
    get_economy_optimizer,      # -> EconomyOptimizer
    get_momentum_tracker,       # -> MomentumTracker
)
```

---

## Algoritmi Chiave

| Algoritmo | Modulo | Descrizione |
|-----------|--------|-------------|
| Aggiornamento logistico bayesiano | `belief_model.py` | Prior log-odds + termini likelihood ponderati -> posterior sigmoid |
| Decadimento esponenziale della minaccia | `belief_model.py` | `P(threat) = visible + inferred * exp(-lambda * age) * 0.5` |
| Fit lambda minimi quadrati | `belief_model.py` | Log-linearizzazione death rate vs. info age, `polyfit` grado 1 |
| MLP con inizializzazione Xavier | `win_probability.py` | 12 -> 64 -> 32 -> 1 sigmoid, ReLU + Dropout |
| Entropia di Shannon su griglia | `entropy_analysis.py` | `H = -sum(p * log2(p))` su discretizzazione spaziale 32x32 |
| Rilevamento flash vettorizzato | `deception_index.py` | `searchsorted` su tick blind ordinati per matching O(F log B) |
| Expectiminimax + TT | `game_tree.py` | Albero max/min/chance con memoizzazione transposition table |
| Blending EMA avversario | `game_tree.py` | `(1 - alpha) * base + alpha * learned`, alpha limitato a 0.7 |
| Consensus doppio classificatore | `role_classifier.py` | Euristico + neurale con regole fusione boost/margine |
| Decadimento esponenziale momentum | `momentum.py` | `multiplier = 1.0 +/- streak_delta * exp(-decay * gap)` |

---

## Note di Sviluppo

1. **Thread safety.** `DeathProbabilityEstimator` usa double-checked locking per il suo singleton. `EntropyAnalyzer` protegge il suo buffer griglia condiviso con `_buffer_lock`. Gli altri moduli sono istanziati per-request tramite factory function.

2. **Import lazy.** `ExpectiminimaxSearch` carica `WinProbabilityPredictor` in modo lazy per interrompere catene di import circolari. `BlindSpotDetector` importa `ExpectiminimaxSearch` al momento dell'`__init__` (a livello di funzione).

3. **Pipeline di calibrazione.** `AdaptiveBeliefCalibrator.auto_calibrate()` e chiamato dal daemon Teacher periodicamente. Gli snapshot di calibrazione sono persistiti come righe DB `CalibrationSnapshot` per rollback e osservabilita.

4. **Comportamento cold-start.** `RoleClassifier` restituisce FLEX/0% confidenza quando `RoleThresholdStore` non ha dati appresi. `OpponentModel` ricade su `_DEFAULT_OPPONENT_PROBS` finche non vengono osservati 10+ round.

5. **Isolamento checkpoint.** `WinProbabilityNN` (predictor 12-dim) e `WinProbabilityTrainerNN` (trainer 9-dim) sono architetture separate. La regola A-12 valida la dimensione input prima di `load_state_dict` per prevenire corruzione silenziosa.

6. **Posizioni nominate.** Il `NamedPositionRegistry` include 60+ callout su 9 mappe. Posizioni aggiuntive possono essere caricate da JSON senza modifiche al codice tramite `load_from_json()`.

7. **Safety bounds.** Tutti i parametri calibrati sono limitati: prior [0.05, 0.95], letalita armi [0.1, 3.0], lambda decay [0.01, 1.0], momentum [0.7, 1.4]. Questo previene valori patologici dal corrompere le analisi a valle.

8. **Logging strutturato.** Ogni modulo usa `get_logger("cs2analyzer.analysis.<modulo>")` con supporto correlation ID per tracciare le chiamate di analisi attraverso la pipeline di coaching.

---

## Dipendenze

- **PyTorch** — `WinProbabilityNN`, head neurale per ruoli, operazioni tensor.
- **NumPy** — Calcolo entropia su griglia, rilevamento flash vettorizzato, analisi statistica.
- **pandas** — DataFrame di calibrazione, dati round per analisi dell'inganno.
- **SQLModel** — Persistenza `CalibrationSnapshot`, query `RoundStats`.
- **Libreria standard** — `math`, `threading`, `dataclasses`, `json`, `pathlib`, `enum`, `collections`.
