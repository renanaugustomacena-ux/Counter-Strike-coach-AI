# Services -- Livello di Orchestrazione dei Servizi Applicativi

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Autorita:** Regola 1 (Correttezza), Regola 2 (Sovranita Backend)
> **Skills:** `/api-contract-review`, `/state-audit`, `/correctness-check`

## Introduzione

Questo e il livello di servizi di primo livello che coordina tra i moduli di analisi
backend e l'interfaccia utente. I servizi in questa directory sono i punti di ingresso
principali per l'applicazione desktop -- orchestrano la generazione del coaching, le
pipeline di analisi, l'integrazione LLM, la gestione dei profili giocatore, il
rendering delle visualizzazioni e l'invio della telemetria. Ogni servizio incapsula
una capacita di business distinta dipendendo da moduli di livello inferiore (storage,
processing, analysis, knowledge) per dati e calcolo.

Tutti i servizi usano dependency injection per l'accesso a `DatabaseManager` (tramite
il singleton `get_db_manager()`) e logging strutturato (tramite
`get_logger("cs2analyzer.<modulo>")`).

## Inventario File

| File | Righe | Scopo | Export Principali |
|------|-------|-------|-------------------|
| `__init__.py` | 0 | Marcatore di pacchetto | -- |
| `coaching_service.py` | ~950 | Orchestratore principale di coaching (4 modalita) | `CoachingService` |
| `analysis_orchestrator.py` | ~830 | Coordinamento analisi Phase 6 (9 motori) | `AnalysisOrchestrator`, `MatchAnalysis`, `RoundAnalysis` |
| `analysis_service.py` | 92 | Analisi prestazioni e rilevamento drift | `AnalysisService`, `get_analysis_service()` |
| `coaching_dialogue.py` | 391 | Chat di coaching interattiva multi-turno | `CoachingDialogueEngine`, `get_dialogue_engine()` |
| `lesson_generator.py` | 382 | Generazione strutturata di lezioni da demo | `LessonGenerator`, `check_lesson_system_status()` |
| `llm_service.py` | 253 | Wrapper provider Ollama LLM | `LLMService`, `get_llm_service()`, `check_ollama_status()` |
| `ollama_writer.py` | 110 | Rifinitura in linguaggio naturale per insight | `OllamaCoachWriter`, `get_ollama_writer()` |
| `profile_service.py` | 167 | Integrazione profili Steam/FaceIT | `ProfileService` |
| `telemetry_client.py` | 60 | Invio telemetria partita al server ML | `send_match_telemetry()` |
| `visualization_service.py` | 131 | Grafici radar e grafici comparativi | `VisualizationService`, `get_visualization_service()` |

## Architettura e Concetti

### `CoachingService` -- Orchestratore Principale di Coaching

Il motore di coaching centrale con una catena di fallback a 4 modalita prioritizzate
(P9-03):

1. **COPER** (default, `USE_COPER_COACHING=True`): Coaching context-aware usando
   Experience Bank + RAG + Riferimenti Pro. Richiede `map_name` e `tick_data`.
2. **Hybrid** (`USE_HYBRID_COACHING=True`): Predizioni ML sintetizzate con recupero
   conoscenza RAG. Richiede `player_stats`.
3. **Traditional + RAG** (`USE_RAG_COACHING=True`): Motore di correzione potenziato
   con recupero conoscenza tattica.
4. **Traditional** (sempre disponibile): Motore di correzione puro basato su
   deviazioni. Fedelta minima, zero dipendenze esterne. Fallback terminale.

Transizioni di fallback: Fallimento COPER -> Hybrid (se abilitato) -> Traditional.

Pipeline post-coaching (non bloccanti):
- Analisi Avanzata Phase 6 (momentum, inganno, entropia, teoria dei giochi)
- Coaching Longitudinale dei Trend (rilevamento regressione/miglioramento)
- Rifinitura in linguaggio naturale Ollama (tramite `OllamaCoachWriter`)
- Narrative di spiegabilita (tramite `ExplanationGenerator`)

Protezione timeout: Tutta la generazione di coaching passa attraverso
`_run_with_timeout()` con un default di 30 secondi per prevenire blocchi dell'UI.

### `AnalysisOrchestrator` -- Coordinamento Analisi Phase 6

Coordina 9 motori di analisi e produce oggetti `CoachingInsight` per il salvataggio
nel database:

| Passo | Motore | Input Richiesto | Area di Focus |
|-------|--------|-----------------|---------------|
| 1 | Momentum Tracker | `round_outcomes` | Rilevamento tilt/hot-streak |
| 2 | Deception Analyzer | `tick_data` | Identificazione fake play |
| 3 | Entropy Analyzer | `tick_data` | Prevedibilita uso utilita |
| 4 | Game Tree + Blind Spots | `game_states` | Alternative decisionali strategiche |
| 5 | Engagement Range | `tick_data` | Distanze ottimali di combattimento |
| 6 | Win Probability | `game_states` | Accuratezza predizione vittoria round |
| 7 | Role Classifier | `player_stats` | Identificazione ruolo giocatore |
| 8 | Utility Analyzer | `player_stats` | Efficienza uso utilita |
| 9 | Economy Optimizer | `game_states` | Analisi decisioni buy/save |

Strutture dati: `RoundAnalysis` (insight per round) e `MatchAnalysis` (insight
aggregati per partita con proprieta `all_insights`).

Tracciamento fallimenti moduli: Usa `_module_failure_counts` con soppressione log
(primi 3, poi ogni 10) per prevenire flooding dei log da fallimenti persistenti.

### `AnalysisService` -- Analisi Prestazioni

Servizio leggero per recupero prestazioni e rilevamento drift:

- `analyze_latest_performance(player_name)`: Recupera ultimo `PlayerMatchStats`
- `get_pro_comparison(player_name, pro_name)`: Statistiche fianco a fianco
- `check_for_drift(player_name)`: Rileva drift feature usando ultime 100 partite

### `CoachingDialogueEngine` -- Chat di Coaching Interattiva

Dialogo di coaching multi-turno con augmentation RAG e Experience Bank:

- **Ciclo di vita sessione**: `start_session()` -> `respond()` (ripetuto) ->
  `clear_session()`
- **Classificazione intent**: Routing basato su keyword in 4 categorie (positioning,
  utility, economy, aim) piu fallback "general"
- **Augmentation RAG**: Ogni messaggio utente attiva il recupero da
  `KnowledgeRetriever` e `ExperienceBank`
- **Finestra di contesto scorrevole**: Ultimi `MAX_CONTEXT_TURNS * 2` messaggi
- **Thread safety**: Stato mutabile protetto da `_state_lock` (threading.Lock)
- **Fallback offline**: Risposte basate su template con conoscenza RAG quando
  Ollama non e disponibile

### `LessonGenerator` -- Lezioni Strutturate da Demo

Genera lezioni di coaching educative dall'analisi demo:

- `generate_lesson(demo_name, focus_area)`: Produce una lezione multi-sezione
- Soglie nominate: `_ADR_STRONG_THRESHOLD`, `_HS_WEAK_THRESHOLD`, ecc.
- Suggerimenti pro specifici per mappa: mirage, inferno, dust2, ancient, nuke
- `check_lesson_system_status()`: Funzione diagnostica per salute LLM e DB

### `LLMService` -- Integrazione Ollama

Wrapper per l'API REST di Ollama per inferenza LLM locale:

- **Endpoint**: `/api/generate` (singola richiesta) e `/api/chat` (multi-turno)
- **Caching disponibilita**: TTL di 60 secondi su controlli `is_available()`
- **Selezione automatica modello**: Se il modello configurato non si trova, usa
  il primo modello disponibile
- **Marcatori errore**: Tutte le risposte errore iniziano con prefisso `[LLM`

### `OllamaCoachWriter` -- Rifinitura in Linguaggio Naturale

Trasforma dati di coaching strutturati in consigli conversazionali tramite Ollama:

- `polish(title, message, focus_area, severity, map_name)`: Migliora un messaggio;
  restituisce testo originale se Ollama e disabilitato o non disponibile
- Feature flag: `USE_OLLAMA_COACHING` controlla l'abilitazione

### `ProfileService` -- Integrazione Profili Esterni

Gestisce la sincronizzazione profili Steam e FaceIT:

- `fetch_steam_stats(steam_id)`: Recupera info giocatore e ore CS2 con retry
  limitato (3 tentativi, backoff esponenziale)
- `fetch_faceit_stats(nickname)`: Recupera Elo FaceIT e livello di abilita
- `sync_all_external_data()`: Orchestra entrambi i fetch e persiste in
  `PlayerProfile`
- Sicurezza: Chiavi API caricate da keyring/env tramite `get_credential()`

### `VisualizationService` -- Rendering Grafici

Genera visualizzazioni basate su matplotlib:

- `generate_performance_radar()`: Grafico radar polare utente vs pro
- `plot_comparison_v2()`: Grafico radar comparativo restituito come buffer
  `io.BytesIO`

### `telemetry_client` -- Invio Telemetria Partita

Invia statistiche partita a un server ML Coach centrale tramite httpx:

- Dipendenza opzionale: `httpx` importato con try/except
- Endpoint: `POST /api/ingest/telemetry` su `CS2_TELEMETRY_URL`

## Integrazione

```
App Desktop (Qt)
    |
    +-- Schermate / ViewModel
            |
            +-- CoachingService.generate_new_insights()
            |       +-- correction_engine (tradizionale)
            |       +-- coper_engine (Experience Bank + RAG)
            |       +-- OllamaCoachWriter.polish()
            |       +-- AnalysisOrchestrator.analyze_match()
            |
            +-- CoachingDialogueEngine.respond()
            |       +-- LLMService.chat()
            |       +-- KnowledgeRetriever.retrieve()
            |
            +-- LessonGenerator.generate_lesson()
            |       +-- LLMService.generate_lesson()
            |
            +-- ProfileService.sync_all_external_data()
            |       +-- Steam API / FaceIT API
            |
            +-- VisualizationService.generate_performance_radar()
```

## Note di Sviluppo

- **Pattern singleton**: La maggior parte dei servizi espone una funzione factory
  `get_*()` per accesso singleton thread-safe. Usare queste invece della costruzione
  diretta.
- **Protezione timeout**: `CoachingService` avvolge le chiamate costose in
  `_run_with_timeout()` per prevenire blocchi del thread UI.
- **Degradazione graziosa**: Ogni servizio degrada in modo pulito quando le
  dipendenze esterne sono non disponibili.
- **Nessun segreto hard-coded**: Tutte le chiavi API usano `get_credential()`.
- **Logging strutturato**: Tutti i servizi usano
  `get_logger("cs2analyzer.<modulo>")`.
- **Thread safety**: `CoachingDialogueEngine` e `CoachingService` proteggono lo
  stato mutabile con lock espliciti.
