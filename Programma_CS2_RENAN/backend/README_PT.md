> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Backend -- Camada Central de Logica de Negocios

| Autoridade | Nivel de Competencia |
|------------|---------------------|
| Macena CS2 Analyzer | Domain-Driven Design, AI Coaching Pipeline |

---

## Visao Geral

O pacote `backend/` e a camada central de logica de negocios do Macena CS2 Analyzer.
Esta organizado em **14 sub-pacotes** seguindo principios de domain-driven design,
onde cada sub-pacote e dono do seu dominio, invariantes de dados e modos de falha.

O backend implementa o **pipeline completo de coaching com IA** de ponta a ponta:

1. **Parsing bruto de demo** -- arquivos `.dem` sao decodificados em dados estruturados de tick/eventos.
2. **Feature engineering** -- dados no nivel de tick sao projetados em um vetor feature unificado de 25 dimensoes.
3. **Inferencia de redes neurais** -- modelos treinados (JEPA, RAP Coach, AdvancedCoachNN) avaliam e classificam o comportamento dos jogadores.
4. **Saida de coaching** -- resultados da analise sao transformados em conselhos de coaching acionaveis em linguagem natural.

Nenhuma logica de UI reside aqui. O backend expoe suas funcionalidades atraves de uma **camada de servicos**
(`services/`) que e consumida tanto pela UI primaria PySide6/Qt quanto pela UI legacy Kivy.

---

## Inventario de Sub-Pacotes

| # | Sub-Pacote | Arquivos | Proposito | Pontos de Entrada Chave |
|---|------------|----------|-----------|------------------------|
| 1 | `analysis/` | 12 | Motores de teoria dos jogos: belief model, rastreamento de momentum, win probability, analise de entropia, indice de engano, deteccao de pontos cegos | `belief_model.py`, `win_probability.py`, `momentum.py` |
| 2 | `coaching/` | 8 | Pipeline de coaching em 4 modos: COPER baseado em experiencia, Hybrid (NN + regras), RAG retrieval-augmented, refinamento puro NN | `hybrid_engine.py`, `correction_engine.py`, `pro_bridge.py` |
| 3 | `control/` | 5 | Gerenciamento do ciclo de vida de daemons, governanca de fila de ingestion, controle de training ML, limites de recursos de database | `ingest_manager.py`, `ml_controller.py`, `db_governor.py` |
| 4 | `data_sources/` | 15 | Integracao de dados externos: demo parser (demoparser2), scraper de estatisticas pro HLTV (FlareSolverr/Docker), Steam API, FACEIT API | `demo_parser.py`, `hltv/`, `steam_api.py`, `faceit_api.py` |
| 5 | `ingestion/` | 4 | Monitoramento runtime de arquivos para novas demos, migracao CSV de formatos legacy, governanca de recursos do OS | `watcher.py`, `resource_manager.py`, `csv_migrator.py` |
| 6 | `knowledge/` | 8 | Knowledge base RAG com indice vetorial FAISS, banco de experiencias COPER, mineracao de demos pro, grafo de conhecimento tatico | `rag_knowledge.py`, `experience_bank.py`, `vector_index.py` |
| 7 | `knowledge_base/` | 2 | Sistema de ajuda in-app: tooltips contextuais, glossario, guias passo a passo para a interface | `help_system.py` |
| 8 | `nn/` | 52 | Arquiteturas de redes neurais (6 tipos de modelo), pipeline de training, inferencia, EMA, early stopping, data quality, RAP Coach, JEPA | `jepa_model.py`, `rap_coach/`, `train.py`, `config.py` |
| 9 | `onboarding/` | 2 | Fluxo de progressao de novos usuarios: avaliacao de habilidades, solicitacoes de coleta de demos, calibracao inicial | `new_user_flow.py` |
| 10 | `processing/` | 33 | Feature engineering (vetor 25-dim), computacao de baselines, baselines pro, geracao de heatmap, validacao, enriquecimento de ticks | `feature_engineering/vectorizer.py`, `baselines/`, `validation/` |
| 11 | `progress/` | 3 | Rastreamento longitudinal de training: tendencias de sessao, metricas de melhoria, analise de curva de habilidade | `longitudinal.py`, `trend_analysis.py` |
| 12 | `reporting/` | 2 | Camada de consultas analiticas para telas da UI: estatisticas agregadas de partidas, resumos de tendencias, detalhamento de desempenho | `analytics.py` |
| 13 | `services/` | 12 | Camada de orquestracao de servicos: coaching service, analysis orchestrator, dialogue engine, integracao LLM, gerenciamento de perfil, telemetria | `coaching_service.py`, `analysis_orchestrator.py`, `llm_service.py` |
| 14 | `storage/` | 14 | Persistencia tri-database (SQLite WAL): database manager, ORM SQLModel, backup, match data manager, state manager, telemetria remota | `database.py`, `db_models.py`, `match_data_manager.py` |

---

## Diagrama de Fluxo de Dados

O backend processa dados atraves de quatro estagios conceituais, mapeando para o
Quad-Daemon Engine (`core/session_engine.py`):

```
 WATCH          LEARN           THINK            SPEAK
 (Ingestao)     (Processamento) (Analise)        (Coaching)

 Arquivos .dem   Dados de tick   Teoria dos jogos   Linguagem natural
 Estatisticas    Vetor 25-dim    Inferencia NN      Saida de coaching
 HLTV            Baselines       Belief model       Conselhos corretivos
 Steam API       Validacao       Win probability    Comparacoes pro

 data_sources/   processing/     analysis/        coaching/
 ingestion/      knowledge/      nn/              services/
 control/        storage/        progress/        reporting/
```

**Fluxo detalhado:**

```
[Arquivo Demo (.dem)]
       |
       v
  data_sources/demo_parser.py       -- Parsing do demo binario bruto
       |
       v
  processing/feature_engineering/   -- Extracao do vetor feature 25-dim
       |
       v
  storage/match_data_manager.py     -- Persistencia no database SQLite por partida
       |
       v
  nn/ (JEPA / RAP Coach)            -- Inferencia de rede neural
       |
       v
  analysis/ (11 modulos de teoria)  -- Scoring de padroes, deteccao de pontos cegos
       |
       v
  coaching/ (fallback em 4 niveis)  -- Geracao de conselhos de coaching
       |
       v
  services/coaching_service.py      -- Exposicao para a camada de UI
```

---

## Padroes Arquiteturais Chave

### Fallback de Coaching em 4 Niveis

O pipeline de coaching tenta estrategias progressivamente mais simples ate que uma funcione:

| Prioridade | Modo | Fonte | Condicao |
|------------|------|-------|----------|
| 1 | **COPER** | Experience Bank + Referencias Pro | Dados historicos suficientes |
| 2 | **Hybrid** | Predicoes NN + Correcoes baseadas em regras | Maturidade do modelo >= LEARNING |
| 3 | **RAG** | Geracao retrieval-augmented via FAISS | Knowledge base populada |
| 4 | **Base NN** | Saida pura da rede neural | Sempre disponivel (fallback) |

### Gating de Maturidade em 3 Estagios

Os modelos e a qualidade do coaching evoluem atraves de tres estagios:

| Estagio | Nome | Comportamento |
|---------|------|---------------|
| 0 | **CALIBRATING** | Apenas coleta de dados, nenhuma saida de coaching |
| 1 | **LEARNING** | Coaching basico, limiares de confianca baixos |
| 2 | **MATURE** | Coaching completo, comparacoes pro habilitadas |

### Decaimento Temporal de Baseline

As baselines de habilidade dos jogadores usam ponderacao com decaimento exponencial
para que o desempenho recente tenha mais peso do que dados antigos.
Controlado por `baselines/meta_drift.py`.

### Vetor Feature Unificado de 25 Dimensoes

Todos os modelos consomem o mesmo vetor de 25 elementos produzido pelo `FeatureExtractor`
(`processing/feature_engineering/vectorizer.py`). Esta e a **unica fonte de verdade**
para definicoes de features. Desalinhamentos dimensionais causam corrupcao silenciosa no training.
A asercao em tempo de compilacao impoe `len(FEATURE_NAMES) == METADATA_DIM == 25`.

### SQLite Modo WAL

Todos os tres databases (Monolith, HLTV, Per-match) aplicam Write-Ahead Logging
no checkout de conexao via `@event.listens_for` do SQLAlchemy. Isso permite
leitores concorrentes sem bloquear escritores.

---

## Regras de Dependencia entre Sub-Pacotes

```
Nivel 0 (Fundacao):       storage/
Nivel 1 (Dados):          data_sources/  ingestion/  knowledge/  knowledge_base/
Nivel 2 (Processamento):  processing/  progress/
Nivel 3 (Inteligencia):   analysis/  nn/
Nivel 4 (Coaching):       coaching/  onboarding/
Nivel 5 (Orquestracao):   services/  reporting/  control/
```

**Regras rigidas:**

- Camadas inferiores NUNCA importam de camadas superiores.
- `storage/` tem ZERO logica de dominio -- e pura persistencia.
- `services/` e a UNICA camada consumida pelos pacotes de UI (`apps/`).
- `nn/` pode ler de `processing/` e `storage/`, mas nunca de `coaching/`.
- `coaching/` pode invocar `nn/` para inferencia, mas nunca dispara training.
- `control/` gerencia o ciclo de vida dos daemons e pode acessar qualquer camada para orquestracao.
- `data_sources/hltv/` faz scraping APENAS de estatisticas de jogadores profissionais. NAO busca demos.

---

## Invariantes Criticos

| ID | Regra | Consequencia se Violado |
|----|-------|------------------------|
| P-X-01 | `len(FEATURE_NAMES) == METADATA_DIM == 25` | Corrupcao silenciosa do modelo |
| P-RSB-03 | `round_won` excluido das features de training | Label leakage destroi a validade do modelo |
| NN-MEM-01 | Hopfield contornado ate >= 2 passagens de training | Explosao NaN na memoria RAP |
| P-VEC-02 | NaN/Inf nas features dispara ERROR + clamp | Propagacao de lixo pela pipeline |
| P3-A | > 5% NaN/Inf no batch levanta `DataQualityError` | O training run aborta de forma limpa |
| DS-12 | `MIN_DEMO_SIZE = 10 MB` | Rejeita arquivos demo corrompidos/truncados |
| NN-16 | EMA `apply_shadow()` deve usar `.clone()` nos tensores | O target encoder compartilha pesos silenciosamente |
| NN-JM-04 | Target encoder `requires_grad=False` durante EMA | Gradient leakage corrompe JEPA |

---

## Notas de Desenvolvimento

### Padroes de Import

- Dependencias opcionais (`ncps`, `hflayers`) usam `try/except` no import e
  levantam excecoes na instanciacao. Verificar `_RAP_DEPS_AVAILABLE` antes de usar RAP Coach.
- Guardas contra import circular: `config` <-> `logger_setup` usa ligacao pos-import;
  `vectorizer.py` e `session_engine.py` usam imports lazy/no nivel de funcao.

### Configuracao

- Ordem de resolucao: Defaults -> `user_settings.json` -> OS keyring/env.
- Em threads daemon, usar `get_setting()` / `get_credential()` (thread-safe).
  Variaveis globais no nivel de modulo sao snapshot-at-import e podem estar desatualizadas.

### Testes

- Framework: `pytest`, 99 arquivos de teste em `Programma_CS2_RENAN/tests/` (+1 top-level).
- Testes de integracao requerem `CS2_INTEGRATION_TESTS=1`.
- Fixtures chave: `in_memory_db`, `seeded_db_session`, `mock_db_manager`, `torch_no_grad`.

### Hooks Pre-Commit

13 hooks devem passar antes de qualquer commit: headless-validator, dead-code-detector,
integrity-manifest, dev-health, trailing-whitespace, end-of-file-fixer,
check-yaml, check-json, large-files (1 MB), merge-conflict, detect-private-key,
black (100 colunas, py3.12), isort (profile=black).

### Validacao Pos-Tarefa

Apos qualquer alteracao, executar:

```bash
python tools/headless_validator.py   # deve sair com 0
```
