# Services -- Camada de Orquestracao de Servicos da Aplicacao

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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

A maioria dos servicos usa injecao de dependencia para acesso ao `DatabaseManager`
(via singleton `get_db_manager()`). Servicos que nao possuem dependencia de banco de
dados (`LLMService`, `OllamaCoachWriter`, `VisualizationService`,
`telemetry_client`) operam de forma autonoma. Todos os servicos usam logging
estruturado (via `get_logger("cs2analyzer.<modulo>")`).

## Inventario de Arquivos

| Arquivo | Linhas | Finalidade | Exports Principais |
|---------|--------|------------|--------------------|
| `__init__.py` | 0 | Marcador de pacote | -- |
| `coaching_service.py` | ~1068 | Orquestrador principal de coaching (4 modos) | `CoachingService` |
| `analysis_orchestrator.py` | ~1149 | Coordenacao de analise Phase 6 (11 motores) | `AnalysisOrchestrator`, `MatchAnalysis`, `RoundAnalysis` |
| `analysis_service.py` | 91 | Analise de desempenho e deteccao de drift | `AnalysisService`, `get_analysis_service()` |
| `coaching_dialogue.py` | ~2014 | Chat de coaching interativo multi-turno com tool-calling no DB | `CoachingDialogueEngine`, `get_dialogue_engine()` |
| `lesson_generator.py` | 383 | Geracao estruturada de licoes a partir de demos | `LessonGenerator`, `check_lesson_system_status()` |
| `llm_service.py` | ~484 | Wrapper do provedor Ollama LLM (incl. tool calling) | `LLMService`, `get_llm_service()`, `check_ollama_status()` |
| `ollama_writer.py` | 108 | Polimento em linguagem natural para insights | `OllamaCoachWriter`, `get_ollama_writer()` |
| `player_lookup.py` | ~557 | Deteccao de nomes de jogadores e recuperacao de dados HLTV para chat | `PlayerLookupService` |
| `profile_service.py` | 165 | Integracao de perfis Steam/FaceIT | `ProfileService` |
| `telemetry_client.py` | 64 | Despacho de telemetria de partida para servidor ML | `send_match_telemetry()` |
| `visualization_service.py` | 136 | Graficos radar e graficos comparativos | `VisualizationService`, `get_visualization_service()` |

## Arquitetura e Conceitos

### `CoachingService` -- Orquestrador Principal de Coaching

O motor de coaching central com uma cadeia de fallback de 4 modos priorizada (P9-03):

1. **COPER** (padrao, `USE_COPER_COACHING=True`): Coaching context-aware usando
   Experience Bank + RAG + Referencias Pro. Requer `map_name` e `tick_data`.
2. **Hybrid** (`USE_HYBRID_COACHING=True`): Desvios Z-score da baseline pro
   sintetizados com recuperacao de conhecimento RAG. Requer `player_stats`.
   Contribuicoes da rede neural chegam a cadeia de insights atraves do modulo
   `jepa_insight_adapter`, nao atraves deste motor (F-0028, fechado 2026-08-21).
3. **Traditional + RAG** (`USE_RAG_COACHING=True`): Motor de correcao aprimorado com
   recuperacao de conhecimento tatico.
4. **Traditional** (sempre disponivel): Motor de correcao puro baseado em desvios.
   Fidelidade minima, zero dependencias externas. Fallback terminal.

Transicoes de fallback: Falha COPER -> Hybrid (se habilitado) -> Traditional.

Pipelines pos-coaching (nao bloqueantes):
- Analise Avancada Phase 6 (momentum, decepcao, entropia, teoria dos jogos)
- Geracao de insights JEPA (F1.2, controlada por `USE_JEPA_MODEL`, padrao off;
  o adapter agora recusa checkpoints apenas pretrain via uma guarda sidecar
  `head_trained`, F-0029 fechado 2026-08-21)
- Coaching Longitudinal de Tendencias (deteccao de regressao/melhoria via
  `compute_trend()`)
- Polimento em linguagem natural via Ollama (via `OllamaCoachWriter`)
- Narrativas de explicabilidade (via `ExplanationGenerator`)

Metodo chave: `generate_new_insights(player_name, demo_name, deviations,
rounds_played, map_name, player_stats, tick_data)`.

Protecao de timeout: Toda geracao de coaching passa por `_run_with_timeout()` com
padrao de 30 segundos (`_COACHING_TIMEOUT`) para prevenir travamentos da UI quando
o download do SBERT, a busca FAISS ou o polimento Ollama travam.

### `AnalysisOrchestrator` -- Coordenacao de Analise Phase 6

Instancia 10 motores de analise eagerly (o analisador de qualidade de movimento e
importado lazy no momento da analise) e executa uma suite de 11 passos (Game Tree
e Blind Spots compartilham um passo) produzindo objetos `CoachingInsight` para
armazenamento no banco de dados:

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
| 10 | Death Probability Estimator | `tick_data` | Estimativa bayesiana de risco de morte |
| 11 | Movement Quality Analyzer | `tick_data` | Deteccao de erros de posicionamento |

O passo de utilidades agora deriva contagens de lancamento de `RoundStats` (F-0031,
fechado 2026-08-21). Os passos strategy, win-probability e economy permanecem
inativos porque nenhum produtor upstream popula `game_states` (veja
`docs/OPEN_ISSUES.md` R9).

Estruturas de dados: `RoundAnalysis` (insights por round) e `MatchAnalysis`
(insights agregados de partida com propriedade `all_insights`).

Rastreamento de falhas de modulo: Usa `_module_failure_counts` com supressao de log
(primeiros 3, depois a cada 10) para prevenir inundacao de logs por falhas
persistentes de motores.

### `AnalysisService` -- Analise de Desempenho

Servico leve para recuperacao de desempenho e deteccao de drift:

- `analyze_latest_performance(player_name)`: Busca ultimo `PlayerMatchStats`
- `get_pro_comparison(player_name, pro_name)`: Estatisticas lado a lado
  usuario vs pro
- `check_for_drift(player_name)`: Detecta drift de features usando as ultimas 100
  partidas via `detect_feature_drift()` do modulo de validacao

### `CoachingDialogueEngine` -- Chat de Coaching Interativo

Dialogo de coaching multi-turno com augmentacao RAG e Experience Bank:

- **Ciclo de vida da sessao**: `start_session()` -> `respond()` /
  `respond_stream()` (repetido) -> `clear_session()`
- **Classificacao de intent**: Roteamento baseado em keywords em 7 categorias
  (positioning, utility, economy, aim, player_query, round_query, match_query)
  mais fallback "general"
- **Tool-calling no banco de dados (DP-03)**: Quando o modelo Ollama ativo
  suporta function calling, as respostas passam por uma fase de tools (maximo 4
  rounds de tools) com quatro tools de DB -- `list_matches`,
  `get_match_overview`, `get_round_details`, `lookup_player` -- ancorando
  respostas em dados reais de demos analisadas; modelos sem suporte a tools
  recorrem ao caminho de chat simples
- **Augmentacao RAG**: Cada mensagem do usuario aciona recuperacao de
  `KnowledgeRetriever` e `ExperienceBank`, injetada como contexto no prompt LLM
- **Janela de contexto deslizante**: Ultimas `MAX_CONTEXT_TURNS * 2` mensagens
  (padrao 12)
- **Top-k RAG**: `RETRIEVAL_TOP_K = 3` resultados de recuperacao
  knowledge/experience
- **Timeouts** (sobreescriveis via env): `_DIALOGUE_TIMEOUT` 180 s,
  `_OPENING_TIMEOUT` 90 s, `_FALLBACK_RETRY_TIMEOUT` 90 s,
  `_STREAM_STALL_TIMEOUT` 30 s
- **Thread safety**: Todo estado mutavel protegido por `_state_lock`
  (threading.Lock)
- **Fallback offline**: Respostas baseadas em template com conhecimento RAG quando
  Ollama nao esta disponivel

Singleton: `get_dialogue_engine()` com double-checked locking.

### `LessonGenerator` -- Licoes Estruturadas de Demo

Gera licoes de coaching educativas a partir de analise de demos:

- `generate_lesson(demo_name, focus_area)`: Produz uma licao multi-secao com
  visao geral, pontos fortes, melhorias, dicas pro e narrativa LLM opcional
- Limiares nomeados: `_ADR_STRONG_THRESHOLD`, `_HS_WEAK_THRESHOLD`,
  `_DEATH_RATIO_WARNING`, etc. -- sem numeros magicos
- Dicas pro especificas por mapa: mirage, inferno, dust2, ancient, nuke
- `check_lesson_system_status()`: Funcao diagnostica para saude do LLM e DB

### `LLMService` -- Integracao Ollama

Encapsula a API REST do Ollama para inferencia LLM local:

- **Escada de resolucao de modelo** (avaliada na construcao e em
  `refresh_model()`): env `OLLAMA_MODEL` -> configuracao do usuario
  `LLM_COACH_MODEL` -> hard default `"gemma4:e2b"`
- **Endpoints**: `/api/generate` (requisicao unica), `/api/chat` (multi-turno),
  streaming via `chat_stream()`, listagem de modelos via `list_models()`
  (`/api/tags`)
- **Tool calling (DP-03)**: `chat_tools()` envia requisicoes de function-calling
  Ollama; um HTTP 400 coloca em cache `tools_supported=False` (exposto via a
  propriedade `tools_supported`) para o modelo atual para que turnos posteriores
  pulem a fase de tools
- **`refresh_model()`** (D-03): Re-resolve o modelo a partir da escada de
  configuracoes para que a escolha de modelo na CoachScreen tenha efeito sem
  reiniciar o servico
- **Caching de disponibilidade**: TTL de 60 segundos em verificacoes
  `is_available()`
- **Selecao automatica de modelo**: Se o modelo configurado nao for encontrado,
  usa o primeiro modelo disponivel (preferindo a mesma familia)
- **Marcadores de erro**: Todas as respostas de erro comecam com prefixo `[LLM`
  para facil deteccao a jusante
- Metodos especializados: `generate_lesson()`, `explain_round_decision()`,
  `generate_pro_tip()`

### `OllamaCoachWriter` -- Polimento em Linguagem Natural

Transforma dados de coaching estruturados em conselhos conversacionais via Ollama:

- `polish(title, message, focus_area, severity, map_name)`: Aprimora uma
  mensagem de coaching; retorna texto original inalterado se Ollama estiver
  desabilitado ou indisponivel
- Feature flag: `USE_OLLAMA_COACHING` controla a habilitacao
- Inicializacao lazy do servico LLM para evitar chamadas HTTP no momento do
  import

### `PlayerLookupService` -- Deteccao de Jogadores no Chat

Detecta mencoes de nomes de jogadores em mensagens de coaching chat e recupera
dados factuais estruturados dos bancos de dados HLTV e monolith:

- `detect_player_mentions(message)`: Tokeniza a mensagem do usuario, filtra
  stop words e faz exact-match de tokens contra um conjunto de apelidos em cache
  (TTL 60 s, de `ProPlayer` em `hltv_metadata.db` com fallback em
  `PlayerMatchStats`); recorre a fuzzy matching (`SequenceMatcher`, limiar
  `_CHAT_FUZZY_THRESHOLD=0.75`) apenas quando nao e encontrado match exato
- `lookup_player(name)`: Monta uma dataclass `ProPlayerProfile` a partir de
  `ProPlayer`, `ProPlayerStatCard`, `ProTeam` e linhas `PlayerMatchStats`
  derivadas de demos. Marca perfis construidos a partir da sentinela
  DEFAULT_STATS (CHAT-06) com `is_default_stats=True` para que o renderizador
  possa mostrar "stats ainda nao coletadas" em vez de numeros fabricados
- `format_player_context(profile)`: Renderiza o perfil em um bloco de texto
  `VERIFIED PLAYER DATA` injetado no prompt LLM por `CoachingDialogueEngine`
- Cross-database: le `hltv_metadata.db` via `get_hltv_db_manager()` e
  `database.db` via `get_db_manager()`

### `ProfileService` -- Integracao de Perfis Externos

Gerencia a sincronizacao de perfis Steam e FaceIT:

- `fetch_steam_stats(steam_id)`: Busca info do jogador e horas de CS2 com retry
  limitado (3 tentativas, backoff exponencial)
- `fetch_faceit_stats(nickname)`: Busca Elo FaceIT e nivel de habilidade
- `sync_all_external_data()`: Orquestra ambas as buscas e persiste em
  `PlayerProfile` no banco de dados
- Seguranca: Chaves de API carregadas de keyring/env via `get_credential()`,
  nunca hard-coded (F5-22)
- Guarda (AC-28-01): Pula o salvamento do perfil quando ambas as buscas falham

### `VisualizationService` -- Renderizacao de Graficos

Gera visualizacoes baseadas em matplotlib:

- `generate_performance_radar(user_stats, pro_stats, output_path)`: Grafico radar
  polar comparando usuario vs pro, salvo em arquivo
- `plot_comparison_v2(p1_name, p2_name, p1_stats, p2_stats)`: Grafico radar
  comparativo retornado como buffer `io.BytesIO` para embedding no Qt

### `telemetry_client` -- Despacho de Telemetria de Partida

Envia estatisticas de partida para um servidor ML Coach central via httpx:

- Dependencia opcional: `httpx` importado com try/except; degrada de forma
  transparente
- Endpoint: `POST /api/ingest/telemetry` em `CS2_TELEMETRY_URL`
- Sem dados de teste fabricados (Regra Anti-Fabricacao)

## Integracao

```
App Desktop (Qt)
    |
    +-- Telas / ViewModels
            |
            +-- CoachingService.generate_new_insights()
            |       +-- correction_engine (tradicional)
            |       +-- experience_bank (sintese COPER: Experience Bank + RAG)
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

## Notas de Desenvolvimento

- **Padrao singleton**: A maioria dos servicos expoe uma funcao factory `get_*()`
  para acesso singleton thread-safe. Use estas em vez de construcao direta.
- **Protecao de timeout**: `CoachingService` envolve chamadas custosas em
  `_run_with_timeout()` para prevenir bloqueio da thread UI.
- **Degradacao graciosa**: Cada servico degrada de forma limpa quando dependencias
  externas (Ollama, Steam API, FaceIT API) estao indisponiveis.
- **Sem segredos hard-coded**: Todas as chaves de API usam `get_credential()` de
  `core/config.py`, carregadas do keyring do SO ou de variaveis de ambiente.
- **Logging estruturado**: Todos os servicos usam
  `get_logger("cs2analyzer.<modulo>")` com saida JSON estruturada e IDs de
  correlacao.
- **Thread safety**: `CoachingDialogueEngine` e `CoachingService` protegem estado
  mutavel com locks explicitos. Singletons usam padrao double-checked locking.
