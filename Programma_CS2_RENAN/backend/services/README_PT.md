# Services -- Camada de Orquestracao de Servicos da Aplicacao

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Autoridade:** Regra 1 (Corretude), Regra 2 (Soberania do Backend)
> **Skills:** `/api-contract-review`, `/state-audit`, `/correctness-check`

## Introducao

Esta e a camada de servicos de nivel superior que coordena entre os modulos de analise
do backend e a interface do usuario. Os servicos neste diretorio sao os pontos de
entrada principais para a aplicacao desktop -- eles orquestram a geracao de coaching,
pipelines de analise, integracao com LLM, gerenciamento de perfis de jogadores,
renderizacao de visualizacoes e despacho de telemetria. Cada servico encapsula uma
capacidade de negocio distinta enquanto depende de modulos de nivel inferior (storage,
processing, analysis, knowledge) para dados e computacao.

Todos os servicos usam injecao de dependencia para acesso ao `DatabaseManager` (via
singleton `get_db_manager()`) e logging estruturado (via
`get_logger("cs2analyzer.<modulo>")`).

## Inventario de Arquivos

| Arquivo | Linhas | Finalidade | Exports Principais |
|---------|--------|------------|--------------------|
| `__init__.py` | 0 | Marcador de pacote | -- |
| `coaching_service.py` | ~950 | Orquestrador principal de coaching (4 modos) | `CoachingService` |
| `analysis_orchestrator.py` | ~830 | Coordenacao de analise Phase 6 (9 motores) | `AnalysisOrchestrator`, `MatchAnalysis`, `RoundAnalysis` |
| `analysis_service.py` | 92 | Analise de desempenho e deteccao de drift | `AnalysisService`, `get_analysis_service()` |
| `coaching_dialogue.py` | 391 | Chat de coaching interativo multi-turno | `CoachingDialogueEngine`, `get_dialogue_engine()` |
| `lesson_generator.py` | 382 | Geracao estruturada de licoes a partir de demos | `LessonGenerator`, `check_lesson_system_status()` |
| `llm_service.py` | 253 | Wrapper do provedor Ollama LLM | `LLMService`, `get_llm_service()`, `check_ollama_status()` |
| `ollama_writer.py` | 110 | Polimento em linguagem natural para insights | `OllamaCoachWriter`, `get_ollama_writer()` |
| `profile_service.py` | 167 | Integracao de perfis Steam/FaceIT | `ProfileService` |
| `telemetry_client.py` | 60 | Despacho de telemetria de partida para servidor ML | `send_match_telemetry()` |
| `visualization_service.py` | 131 | Graficos radar e graficos comparativos | `VisualizationService`, `get_visualization_service()` |

## Arquitetura e Conceitos

### `CoachingService` -- Orquestrador Principal de Coaching

O motor de coaching central com uma cadeia de fallback de 4 modos priorizada (P9-03):

1. **COPER** (padrao, `USE_COPER_COACHING=True`): Coaching context-aware usando
   Experience Bank + RAG + Referencias Pro. Requer `map_name` e `tick_data`.
2. **Hybrid** (`USE_HYBRID_COACHING=True`): Predicoes ML sintetizadas com recuperacao
   de conhecimento RAG. Requer `player_stats`.
3. **Traditional + RAG** (`USE_RAG_COACHING=True`): Motor de correcao aprimorado com
   recuperacao de conhecimento tatico.
4. **Traditional** (sempre disponivel): Motor de correcao puro baseado em desvios.
   Fidelidade minima, zero dependencias externas. Fallback terminal.

Transicoes de fallback: Falha COPER -> Hybrid (se habilitado) -> Traditional.

Pipelines pos-coaching (nao bloqueantes):
- Analise Avancada Phase 6 (momentum, decepcao, entropia, teoria dos jogos)
- Coaching Longitudinal de Tendencias (deteccao de regressao/melhoria)
- Polimento em linguagem natural via Ollama (via `OllamaCoachWriter`)
- Narrativas de explicabilidade (via `ExplanationGenerator`)

Protecao de timeout: Toda geracao de coaching passa por `_run_with_timeout()` com
padrao de 30 segundos para prevenir travamentos da UI.

### `AnalysisOrchestrator` -- Coordenacao de Analise Phase 6

Coordena 9 motores de analise e produz objetos `CoachingInsight` para armazenamento
no banco de dados:

| Passo | Motor | Input Necessario | Area de Foco |
|-------|-------|------------------|--------------|
| 1 | Momentum Tracker | `round_outcomes` | Deteccao de tilt/hot-streak |
| 2 | Deception Analyzer | `tick_data` | Identificacao de fake play |
| 3 | Entropy Analyzer | `tick_data` | Previsibilidade de uso de utilidades |
| 4 | Game Tree + Blind Spots | `game_states` | Alternativas de decisao estrategica |
| 5 | Engagement Range | `tick_data` | Distancias otimas de combate |
| 6 | Win Probability | `game_states` | Precisao de predicao de vitoria |
| 7 | Role Classifier | `player_stats` | Identificacao de papel do jogador |
| 8 | Utility Analyzer | `player_stats` | Eficiencia de uso de utilidades |
| 9 | Economy Optimizer | `game_states` | Analise de decisoes buy/save |

Estruturas de dados: `RoundAnalysis` (insights por round) e `MatchAnalysis`
(insights agregados de partida com propriedade `all_insights`).

Rastreamento de falhas de modulo: Usa `_module_failure_counts` com supressao de log
(primeiros 3, depois a cada 10) para prevenir inundacao de logs.

### `AnalysisService` -- Analise de Desempenho

Servico leve para recuperacao de desempenho e deteccao de drift:

- `analyze_latest_performance(player_name)`: Busca ultimo `PlayerMatchStats`
- `get_pro_comparison(player_name, pro_name)`: Estatisticas lado a lado
- `check_for_drift(player_name)`: Detecta drift de features usando ultimas 100
  partidas

### `CoachingDialogueEngine` -- Chat de Coaching Interativo

Dialogo de coaching multi-turno com augmentacao RAG e Experience Bank:

- **Ciclo de vida da sessao**: `start_session()` -> `respond()` (repetido) ->
  `clear_session()`
- **Classificacao de intent**: Roteamento baseado em keywords em 4 categorias
  (positioning, utility, economy, aim) mais fallback "general"
- **Augmentacao RAG**: Cada mensagem do usuario aciona recuperacao de
  `KnowledgeRetriever` e `ExperienceBank`
- **Janela de contexto deslizante**: Ultimas `MAX_CONTEXT_TURNS * 2` mensagens
- **Thread safety**: Estado mutavel protegido por `_state_lock` (threading.Lock)
- **Fallback offline**: Respostas baseadas em template com conhecimento RAG quando
  Ollama nao esta disponivel

### `LessonGenerator` -- Licoes Estruturadas de Demo

Gera licoes de coaching educativas a partir de analise de demos:

- `generate_lesson(demo_name, focus_area)`: Produz uma licao multi-secao
- Limiares nomeados: `_ADR_STRONG_THRESHOLD`, `_HS_WEAK_THRESHOLD`, etc.
- Dicas pro especificas por mapa: mirage, inferno, dust2, ancient, nuke
- `check_lesson_system_status()`: Funcao diagnostica para saude do LLM e DB

### `LLMService` -- Integracao Ollama

Encapsula a API REST do Ollama para inferencia LLM local:

- **Endpoints**: `/api/generate` (requisicao unica) e `/api/chat` (multi-turno)
- **Caching de disponibilidade**: TTL de 60 segundos em verificacoes
  `is_available()`
- **Selecao automatica de modelo**: Se o modelo configurado nao for encontrado,
  usa o primeiro modelo disponivel
- **Marcadores de erro**: Todas as respostas de erro comecam com prefixo `[LLM`

### `OllamaCoachWriter` -- Polimento em Linguagem Natural

Transforma dados de coaching estruturados em conselhos conversacionais via Ollama:

- `polish(title, message, focus_area, severity, map_name)`: Aprimora uma
  mensagem; retorna texto original se Ollama estiver desabilitado ou indisponivel
- Feature flag: `USE_OLLAMA_COACHING` controla a habilitacao

### `ProfileService` -- Integracao de Perfis Externos

Gerencia a sincronizacao de perfis Steam e FaceIT:

- `fetch_steam_stats(steam_id)`: Busca info do jogador e horas de CS2 com retry
  limitado (3 tentativas, backoff exponencial)
- `fetch_faceit_stats(nickname)`: Busca Elo FaceIT e nivel de habilidade
- `sync_all_external_data()`: Orquestra ambas as buscas e persiste em
  `PlayerProfile`
- Seguranca: Chaves de API carregadas de keyring/env via `get_credential()`

### `VisualizationService` -- Renderizacao de Graficos

Gera visualizacoes baseadas em matplotlib:

- `generate_performance_radar()`: Grafico radar polar usuario vs pro
- `plot_comparison_v2()`: Grafico radar comparativo retornado como buffer
  `io.BytesIO`

### `telemetry_client` -- Despacho de Telemetria de Partida

Envia estatisticas de partida para um servidor ML Coach central via httpx:

- Dependencia opcional: `httpx` importado com try/except
- Endpoint: `POST /api/ingest/telemetry` em `CS2_TELEMETRY_URL`

## Integracao

```
App Desktop (Qt)
    |
    +-- Telas / ViewModels
            |
            +-- CoachingService.generate_new_insights()
            |       +-- correction_engine (tradicional)
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

## Notas de Desenvolvimento

- **Padrao singleton**: A maioria dos servicos expoe uma funcao factory `get_*()`
  para acesso singleton thread-safe. Use estas em vez de construcao direta.
- **Protecao de timeout**: `CoachingService` envolve chamadas custosas em
  `_run_with_timeout()` para prevenir bloqueio da thread UI.
- **Degradacao graciosa**: Cada servico degrada de forma limpa quando dependencias
  externas estao indisponiveis.
- **Sem segredos hard-coded**: Todas as chaves de API usam `get_credential()`.
- **Logging estruturado**: Todos os servicos usam
  `get_logger("cs2analyzer.<modulo>")`.
- **Thread safety**: `CoachingDialogueEngine` e `CoachingService` protegem estado
  mutavel com locks explicitos.
