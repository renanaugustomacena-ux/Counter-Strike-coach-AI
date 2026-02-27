# Camada de Serviços da Aplicação

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Visão Geral

Camada de orquestração de serviços de alto nível fornecendo coaching, análise, visualização e integração LLM. Os serviços coordenam múltiplos módulos backend e fornecem lógica de negócio para a aplicação desktop.

## Serviços Principais

### `coaching_service.py`
- **`CoachingService`** — Motor de coaching principal com 4 modos: COPER (padrão), Hybrid, RAG, Neural Network
- Enriquecimento de baseline temporal via `_get_temporal_baseline()` e `_baseline_context_note()`
- Integração Experience Bank para recuperação de insights históricos
- Comparação de referências pro e RAG de conhecimento tático

### `analysis_orchestrator.py`
- **`AnalysisOrchestrator`** — Coordena todos os motores de análise (teoria dos jogos, modelos de crença, momentum, espacial, classificação de papéis)
- Padrão factory para instanciação de motores

### `analysis_service.py`
- **`AnalysisService`** — Análise de desempenho, detecção de drift de features, comparação pro
- `check_for_drift()` agora conectado ao real `detect_feature_drift()` usando últimos 50 matches do DB

### `coaching_dialogue.py`
- **`CoachingDialogueEngine`** — Conversas de coaching interativas multi-turno com rastreamento de contexto

### `lesson_generator.py`
- **`LessonGenerator`** — Geração de lições estruturadas com exercícios e recomendações de prática

### `ollama_writer.py`
- **`OllamaCoachWriter`** — Integração LLM Ollama para polimento em linguagem natural de insights de coaching
- Transforma insights estruturados em texto de coaching conversacional

### `llm_service.py`
- **`LLMService`** — Wrapper abstrato de provedor LLM com lógica de retry e tratamento de timeout

### `visualization_service.py`
- **`VisualizationService`** — Orquestra geração de heatmap, mapas de engajamento e gráficos de momentum

## Padrão de Integração

Serviços são instanciados em `main.py` e usados pelas telas da UI. Todos os serviços usam injeção de dependência para database manager e config.
