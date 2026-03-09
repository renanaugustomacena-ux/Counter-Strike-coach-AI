# Livello Servizi Applicazione

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Panoramica

Livello di orchestrazione dei servizi ad alto livello che fornisce coaching, analisi, visualizzazione e integrazione LLM. I servizi coordinano molteplici moduli backend e forniscono logica di business per l'applicazione desktop.

## Servizi Chiave

### `coaching_service.py`
- **`CoachingService`** — Motore di coaching principale con 4 modalità: COPER (default), Hybrid, RAG, Neural Network
- Arricchimento baseline temporale tramite `_get_temporal_baseline()` e `_baseline_context_note()`
- Integrazione Experience Bank per recupero insight storici
- Confronto riferimenti pro e RAG di conoscenza tattica

### `analysis_orchestrator.py`
- **`AnalysisOrchestrator`** — Coordina tutti i motori di analisi (teoria del gioco, modelli di belief, momentum, spaziale, classificazione ruoli)
- Pattern factory per istanziazione motori

### `analysis_service.py`
- **`AnalysisService`** — Analisi prestazioni, rilevamento drift feature, confronto pro
- `check_for_drift()` ora collegato a reale `detect_feature_drift()` usando ultimi 50 match dal DB

### `coaching_dialogue.py`
- **`CoachingDialogueEngine`** — Conversazioni di coaching interattive multi-turno con tracking contesto

### `lesson_generator.py`
- **`LessonGenerator`** — Generazione lezioni strutturate con drill e raccomandazioni pratica

### `ollama_writer.py`
- **`OllamaCoachWriter`** — Integrazione LLM Ollama per raffinamento linguaggio naturale degli insight di coaching
- Trasforma insight strutturati in testo di coaching conversazionale

### `llm_service.py`
- **`LLMService`** — Wrapper astratto provider LLM con logica retry e gestione timeout

### `visualization_service.py`
- **`VisualizationService`** — Orchestra generazione heatmap, mappe engagement e grafici momentum

## Pattern di Integrazione

I servizi sono istanziati in `main.py` e usati dalle schermate UI. Tutti i servizi usano dependency injection per database manager e config.
