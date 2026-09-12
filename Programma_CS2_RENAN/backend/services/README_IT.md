# Services -- Livello di Orchestrazione dei Servizi Applicativi

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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

La maggior parte dei servizi usa dependency injection per l'accesso a `DatabaseManager`
(tramite il singleton `get_db_manager()`). I servizi che non hanno dipendenza dal
database (`LLMService`, `OllamaCoachWriter`, `VisualizationService`,
`telemetry_client`) operano in modo autonomo. Tutti i servizi usano logging
strutturato (tramite `get_logger("cs2analyzer.<modulo>")`).

## Inventario File

| File | Righe | Scopo | Export Principali |
|------|-------|-------|-------------------|
| `__init__.py` | 0 | Marcatore di pacchetto | -- |
| `coaching_service.py` | ~1068 | Orchestratore principale di coaching (4 modalita) | `CoachingService` |
| `analysis_orchestrator.py` | ~1149 | Coordinamento analisi Phase 6 (11 motori) | `AnalysisOrchestrator`, `MatchAnalysis`, `RoundAnalysis` |
| `analysis_service.py` | 91 | Analisi prestazioni e rilevamento drift | `AnalysisService`, `get_analysis_service()` |
| `coaching_dialogue.py` | ~2014 | Chat di coaching interattiva multi-turno con tool-calling su DB | `CoachingDialogueEngine`, `get_dialogue_engine()` |
| `lesson_generator.py` | 383 | Generazione strutturata di lezioni da demo | `LessonGenerator`, `check_lesson_system_status()` |
| `llm_service.py` | ~484 | Wrapper provider Ollama LLM (incl. tool calling) | `LLMService`, `get_llm_service()`, `check_ollama_status()` |
| `ollama_writer.py` | 108 | Rifinitura in linguaggio naturale per insight | `OllamaCoachWriter`, `get_ollama_writer()` |
| `player_lookup.py` | ~557 | Rilevamento nomi giocatori e recupero dati HLTV per chat | `PlayerLookupService` |
| `profile_service.py` | 165 | Integrazione profili Steam/FaceIT | `ProfileService` |
| `telemetry_client.py` | 64 | Invio telemetria partita al server ML | `send_match_telemetry()` |
| `visualization_service.py` | 136 | Grafici radar e grafici comparativi | `VisualizationService`, `get_visualization_service()` |

## Architettura e Concetti

### `CoachingService` -- Orchestratore Principale di Coaching

Il motore di coaching centrale con una catena di fallback a 4 modalita prioritizzate
(P9-03):

1. **COPER** (default, `USE_COPER_COACHING=True`): Coaching context-aware usando
   Experience Bank + RAG + Riferimenti Pro. Richiede `map_name` e `tick_data`.
2. **Hybrid** (`USE_HYBRID_COACHING=True`): Deviazioni Z-score dalla baseline pro
   sintetizzate con recupero conoscenza RAG. Richiede `player_stats`. I contributi
   della rete neurale raggiungono la catena degli insight tramite il modulo
   `jepa_insight_adapter`, non tramite questo motore (F-0028, chiuso 2026-08-21).
3. **Traditional + RAG** (`USE_RAG_COACHING=True`): Motore di correzione potenziato
   con recupero conoscenza tattica.
4. **Traditional** (sempre disponibile): Motore di correzione puro basato su
   deviazioni. Fedelta minima, zero dipendenze esterne. Fallback terminale.

Transizioni di fallback: Fallimento COPER -> Hybrid (se abilitato) -> Traditional.

Pipeline post-coaching (non bloccanti):
- Analisi Avanzata Phase 6 (momentum, inganno, entropia, teoria dei giochi)
- Generazione insight JEPA (F1.2, controllata da `USE_JEPA_MODEL`, default off;
  l'adapter ora rifiuta checkpoint solo pretrain tramite una guardia sidecar
  `head_trained`, F-0029 chiuso 2026-08-21)
- Coaching Longitudinale dei Trend (rilevamento regressione/miglioramento tramite
  `compute_trend()`)
- Rifinitura in linguaggio naturale Ollama (tramite `OllamaCoachWriter`)
- Narrative di spiegabilita (tramite `ExplanationGenerator`)

Metodo chiave: `generate_new_insights(player_name, demo_name, deviations,
rounds_played, map_name, player_stats, tick_data)`.

Protezione timeout: Tutta la generazione di coaching passa attraverso
`_run_with_timeout()` con un default di 30 secondi (`_COACHING_TIMEOUT`) per
prevenire blocchi dell'UI quando il download SBERT, la ricerca FAISS o la
rifinitura Ollama si bloccano.

### `AnalysisOrchestrator` -- Coordinamento Analisi Phase 6

Istanzia 10 motori di analisi eagerly (l'analizzatore di qualita del movimento e
importato lazy al momento dell'analisi) e esegue una suite di 11 passi (Game Tree
e Blind Spots condividono un passo) producendo oggetti `CoachingInsight` per il
salvataggio nel database:

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
| 10 | Death Probability Estimator | `tick_data` | Stima bayesiana del rischio di morte |
| 11 | Movement Quality Analyzer | `tick_data` | Rilevamento errori di posizionamento |

Il passo utility ora deriva i conteggi di lancio da `RoundStats` (F-0031, chiuso
2026-08-21). I passi strategy, win-probability ed economy restano inattivi perche
nessun produttore upstream popola `game_states` (vedi `docs/OPEN_ISSUES.md` R9).

Strutture dati: `RoundAnalysis` (insight per round) e `MatchAnalysis` (insight
aggregati per partita con proprieta `all_insights`).

Tracciamento fallimenti moduli: Usa `_module_failure_counts` con soppressione log
(primi 3, poi ogni 10) per prevenire flooding dei log da fallimenti persistenti.

### `AnalysisService` -- Analisi Prestazioni

Servizio leggero per recupero prestazioni e rilevamento drift:

- `analyze_latest_performance(player_name)`: Recupera ultimo `PlayerMatchStats`
- `get_pro_comparison(player_name, pro_name)`: Statistiche fianco a fianco
  utente vs pro
- `check_for_drift(player_name)`: Rileva drift feature usando le ultime 100 partite
  tramite `detect_feature_drift()` dal modulo di validazione

### `CoachingDialogueEngine` -- Chat di Coaching Interattiva

Dialogo di coaching multi-turno con augmentation RAG e Experience Bank:

- **Ciclo di vita sessione**: `start_session()` -> `respond()` / `respond_stream()`
  (ripetuto) -> `clear_session()`
- **Classificazione intent**: Routing basato su keyword in 7 categorie (positioning,
  utility, economy, aim, player_query, round_query, match_query) piu fallback
  "general"
- **Tool-calling su database (DP-03)**: Quando il modello Ollama attivo supporta
  il function calling, le risposte passano attraverso una fase tool (massimo 4
  round di tool) con quattro tool DB -- `list_matches`, `get_match_overview`,
  `get_round_details`, `lookup_player` -- ancorando le risposte ai dati reali
  delle demo analizzate; i modelli senza supporto tool ricadono sul percorso
  chat semplice
- **Augmentation RAG**: Ogni messaggio utente attiva il recupero da
  `KnowledgeRetriever` e `ExperienceBank`, iniettato come contesto nel prompt LLM
- **Finestra di contesto scorrevole**: Ultimi `MAX_CONTEXT_TURNS * 2` messaggi
  (default 12)
- **Top-k RAG**: `RETRIEVAL_TOP_K = 3` risultati dal recupero knowledge/experience
- **Timeout** (sovrascrivibili via env): `_DIALOGUE_TIMEOUT` 180 s,
  `_OPENING_TIMEOUT` 90 s, `_FALLBACK_RETRY_TIMEOUT` 90 s,
  `_STREAM_STALL_TIMEOUT` 30 s
- **Thread safety**: Tutto lo stato mutabile protetto da `_state_lock`
  (threading.Lock)
- **Fallback offline**: Risposte basate su template con conoscenza RAG quando
  Ollama non e disponibile

Singleton: `get_dialogue_engine()` con double-checked locking.

### `LessonGenerator` -- Lezioni Strutturate da Demo

Genera lezioni di coaching educative dall'analisi demo:

- `generate_lesson(demo_name, focus_area)`: Produce una lezione multi-sezione con
  panoramica, punti di forza, miglioramenti, suggerimenti pro e narrativa LLM
  opzionale
- Soglie nominate: `_ADR_STRONG_THRESHOLD`, `_HS_WEAK_THRESHOLD`,
  `_DEATH_RATIO_WARNING`, ecc. -- nessun numero magico
- Suggerimenti pro specifici per mappa: mirage, inferno, dust2, ancient, nuke
- `check_lesson_system_status()`: Funzione diagnostica per salute LLM e DB

### `LLMService` -- Integrazione Ollama

Wrapper per l'API REST di Ollama per inferenza LLM locale:

- **Scala di risoluzione modello** (valutata alla costruzione e su `refresh_model()`):
  env `OLLAMA_MODEL` -> impostazione utente `LLM_COACH_MODEL` -> hard default
  `"gemma4:e2b"`
- **Endpoint**: `/api/generate` (singola richiesta), `/api/chat` (multi-turno),
  streaming tramite `chat_stream()`, lista modelli tramite `list_models()`
  (`/api/tags`)
- **Tool calling (DP-03)**: `chat_tools()` invia richieste di function-calling
  Ollama; un HTTP 400 mette in cache `tools_supported=False` (esposto tramite la
  proprieta `tools_supported`) per il modello corrente cosi che i turni successivi
  saltino la fase tool
- **`refresh_model()`** (D-03): Risolve nuovamente il modello dalla scala delle
  impostazioni cosi che la scelta del modello nella CoachScreen abbia effetto
  senza riavviare il servizio
- **Caching disponibilita**: TTL di 60 secondi su controlli `is_available()`
- **Selezione automatica modello**: Se il modello configurato non si trova, usa
  il primo modello disponibile (preferendo la stessa famiglia)
- **Marcatori errore**: Tutte le risposte errore iniziano con prefisso `[LLM`
  per facile rilevamento a valle
- Metodi specializzati: `generate_lesson()`, `explain_round_decision()`,
  `generate_pro_tip()`

### `OllamaCoachWriter` -- Rifinitura in Linguaggio Naturale

Trasforma dati di coaching strutturati in consigli conversazionali tramite Ollama:

- `polish(title, message, focus_area, severity, map_name)`: Migliora un messaggio
  di coaching; restituisce testo originale immutato se Ollama e disabilitato o
  non disponibile
- Feature flag: `USE_OLLAMA_COACHING` controlla l'abilitazione
- Inizializzazione lazy del servizio LLM per evitare chiamate HTTP al momento
  dell'import

### `PlayerLookupService` -- Rilevamento Giocatori nella Chat

Rileva menzioni di nomi giocatore nei messaggi di coaching chat e recupera
dati fattuali strutturati dai database HLTV e monolith:

- `detect_player_mentions(message)`: Tokenizza il messaggio utente, filtra le
  stop word e fa exact-match dei token contro un set di nickname in cache
  (TTL 60 s, da `ProPlayer` in `hltv_metadata.db` con fallback su
  `PlayerMatchStats`); ricade su fuzzy matching (`SequenceMatcher`, soglia
  `_CHAT_FUZZY_THRESHOLD=0.75`) solo quando non si trova un match esatto
- `lookup_player(name)`: Assembla una dataclass `ProPlayerProfile` da
  `ProPlayer`, `ProPlayerStatCard`, `ProTeam` e righe `PlayerMatchStats`
  derivate da demo. Contrassegna i profili costruiti dalla sentinella
  DEFAULT_STATS (CHAT-06) con `is_default_stats=True` cosi che il renderer
  possa mostrare "stats non ancora scaricate" invece di numeri fabbricati
- `format_player_context(profile)`: Renderizza il profilo in un blocco testuale
  `VERIFIED PLAYER DATA` iniettato nel prompt LLM da `CoachingDialogueEngine`
- Cross-database: legge `hltv_metadata.db` tramite `get_hltv_db_manager()` e
  `database.db` tramite `get_db_manager()`

### `ProfileService` -- Integrazione Profili Esterni

Gestisce la sincronizzazione profili Steam e FaceIT:

- `fetch_steam_stats(steam_id)`: Recupera info giocatore e ore CS2 con retry
  limitato (3 tentativi, backoff esponenziale)
- `fetch_faceit_stats(nickname)`: Recupera Elo FaceIT e livello di abilita
- `sync_all_external_data()`: Orchestra entrambi i fetch e persiste in
  `PlayerProfile` nel database
- Sicurezza: Chiavi API caricate da keyring/env tramite `get_credential()`, mai
  hard-coded (F5-22)
- Guardia (AC-28-01): Salta il salvataggio del profilo quando entrambi i fetch
  falliscono

### `VisualizationService` -- Rendering Grafici

Genera visualizzazioni basate su matplotlib:

- `generate_performance_radar(user_stats, pro_stats, output_path)`: Grafico radar
  polare che compara utente vs pro, salvato su file
- `plot_comparison_v2(p1_name, p2_name, p1_stats, p2_stats)`: Grafico radar
  comparativo restituito come buffer `io.BytesIO` per embedding Qt

### `telemetry_client` -- Invio Telemetria Partita

Invia statistiche partita a un server ML Coach centrale tramite httpx:

- Dipendenza opzionale: `httpx` importato con try/except; degrada in modo
  trasparente
- Endpoint: `POST /api/ingest/telemetry` su `CS2_TELEMETRY_URL`
- Nessun dato di test fabbricato (Regola Anti-Fabbricazione)

## Integrazione

```
App Desktop (Qt)
    |
    +-- Schermate / ViewModel
            |
            +-- CoachingService.generate_new_insights()
            |       +-- correction_engine (tradizionale)
            |       +-- experience_bank (sintesi COPER: Experience Bank + RAG)
            |       +-- hybrid_engine (baseline Z + RAG)
            |       +-- OllamaCoachWriter.polish()
            |       +-- AnalysisOrchestrator.analyze_match()
            |
            +-- CoachingDialogueEngine.respond()
            |       +-- LLMService.chat() / chat_tools()
            |       +-- KnowledgeRetriever.retrieve()
            |       +-- ExperienceBank.retrieve_similar()
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
  dipendenze esterne (Ollama, Steam API, FaceIT API) sono non disponibili.
- **Nessun segreto hard-coded**: Tutte le chiavi API usano `get_credential()` da
  `core/config.py`, caricate dal keyring del sistema operativo o da variabili
  d'ambiente.
- **Logging strutturato**: Tutti i servizi usano
  `get_logger("cs2analyzer.<modulo>")` con output JSON strutturato e ID di
  correlazione.
- **Thread safety**: `CoachingDialogueEngine` e `CoachingService` proteggono lo
  stato mutabile con lock espliciti. I singleton usano pattern double-checked locking.
