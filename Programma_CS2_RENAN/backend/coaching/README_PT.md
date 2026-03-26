> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching -- Pipeline de Coaching Multi-Modo

> **Autoridade:** `backend/coaching/`
> **Skill:** `/ml-check`, `/api-contract-review`
> **Modulo proprietario:** `backend/services/coaching_service.py`

## Visao Geral

O pacote coaching e a camada de inteligencia que transforma dados de analise brutos em
feedback acionavel para o jogador. Implementa uma **pipeline de coaching com quatro modos**
onde cada modo oferece um compromisso diferente entre conselhos baseados em conhecimento e
previsoes de rede neural. O modo padrao e **COPER** (Contextual Observation Pattern
Experience Retrieval), que combina um Experience Bank, recuperacao de conhecimento RAG e
dados de referencia de jogadores profissionais para produzir saida de coaching
fundamentada em evidencias reais de partida.

Todos os modos de coaching sao consumidos por um unico ponto de entrada --
`backend/services/coaching_service.py` -- que seleciona o modo ativo com base nas flags
de funcionalidade `USE_COPER_COACHING`, `USE_HYBRID_COACHING`, `USE_RAG_COACHING` e
`USE_JEPA_MODEL` / `USE_RAP_MODEL` em `core/config.py`.

## Os Quatro Modos de Coaching

| # | Modo | Flag | Descricao |
|---|------|------|-----------|
| 1 | **COPER** | `USE_COPER_COACHING=True` (padrao) | Recuperacao semantica Experience Bank + conhecimento RAG + Referencias Pro. Nenhum modelo ML necessario. |
| 2 | **Hybrid** | `USE_HYBRID_COACHING=True` | Previsoes de rede neural sintetizadas com contexto RAG para saida mesclada. |
| 3 | **RAG** | `USE_RAG_COACHING=True` | Recuperacao pura de conhecimento de padroes de demos pro indexados. Sem inferencia ML. |
| 4 | **Neural** | `USE_JEPA_MODEL=True` ou `USE_RAP_MODEL=True` | Previsoes ML puras sem aumento de conhecimento. Requer um checkpoint de modelo treinado. |

### Fluxo de Fallback do Coaching

Quando um modo de maior fidelidade nao esta disponivel (checkpoint de modelo ausente,
base de conhecimento vazia, etc.), a pipeline degrada de forma controlada atraves da
seguinte cadeia:

```
Neural (ML puro)
   |  [checkpoint de modelo ausente ou erro de inferencia]
   v
Hybrid (ML + RAG)
   |  [indice RAG vazio ou ML indisponivel]
   v
COPER (Experience Bank + RAG + Pro)
   |  [experience bank vazio]
   v
RAG (apenas recuperacao de conhecimento)
   |  [indice de conhecimento vazio]
   v
Correcoes heuristicas (fallback correction_engine.py)
```

Cada transicao e registrada no nivel WARNING com uma mensagem JSON estruturada
contendo a razao da degradacao, para que o operador sempre saiba qual modo esta ativo.

## Inventario de Arquivos

| Arquivo | Exportacao Primaria | Proposito |
|---------|--------------------|-----------|
| `__init__.py` | API do Pacote | Re-exporta `HybridCoachingEngine`, `generate_corrections`, `ExplanationGenerator`, `PlayerCardAssimilator`, `get_pro_baseline_for_coach` |
| `hybrid_engine.py` | `HybridCoachingEngine` | Orquestrador central que sintetiza previsoes ML com recuperacao de conhecimento RAG para insights de coaching equilibrados |
| `correction_engine.py` | `generate_corrections()` | Gera correcoes taticas comparando desvios de desempenho do jogador contra baselines profissionais |
| `nn_refinement.py` | `apply_nn_refinement()` | Camada de refinamento de rede neural que aprimora correcoes heuristicas com pontuacao de confianca de modelos treinados |
| `longitudinal_engine.py` | `generate_longitudinal_coaching()` | Rastreia tendencias de desempenho ao longo do tempo usando integracao de decaimento temporal de baseline para conselhos de melhoria a longo prazo |
| `explainability.py` | `ExplanationGenerator` | Converte tensores de previsao ML opacos em explicacoes legiveis por humanos com cadeias de atribuicao causal |
| `pro_bridge.py` | `PlayerCardAssimilator` | Conecta stat cards de jogadores profissionais a insights de coaching via comparacao baseada em funcao (entry fragger, AWPer, etc.) |
| `token_resolver.py` | `PlayerTokenResolver` | Canonicaliza nomes de jogadores usando fuzzy matching, normalizacao leet-speak e resolucao de alias |

## Descricoes dos Modulos

### hybrid_engine.py -- HybridCoachingEngine

O `HybridCoachingEngine` e o orquestrador primario para o modo Hybrid de coaching.
Aceita um vetor de caracteristicas de 25 dimensoes (veja `METADATA_DIM` em
`nn/config.py`), executa inferencia ML atraves do modelo ativo (JEPA ou RAP), recupera
conhecimento relevante do indice RAG e funde ambos os sinais em uma resposta de coaching
unificada. O motor aplica uma estrategia de fusao ponderada por confianca: previsoes ML
de alta confianca dominam, enquanto as de baixa confianca cedem ao conhecimento RAG.

### correction_engine.py -- generate_corrections()

Funcao stateless que recebe um snapshot de desempenho do round do jogador e o compara
com o baseline profissional (fornecido por `pro_bridge.py`). Desvios que excedem limites
configuraveis produzem entradas de correcao com severidade (info/warning/critical), uma
descricao legivel e a metrica especifica que acionou a correcao. Este modulo e o fallback
final quando todos os modos de coaching de maior fidelidade nao estao disponiveis.

### nn_refinement.py -- apply_nn_refinement()

Camada de pos-processamento que recebe correcoes heuristicas de `correction_engine.py`
e as refina usando uma rede neural treinada. Cada correcao recebe uma pontuacao de
confianca (0.0--1.0). Correcoes abaixo do limiar de confianca sao suprimidas para
reduzir ruido. A etapa de refinamento e opcional e so e ativada quando um checkpoint
de modelo treinado esta disponivel.

### longitudinal_engine.py -- generate_longitudinal_coaching()

Gera conselhos de coaching baseados em tendencias de desempenho ao longo de multiplas
partidas ou sessoes. Usa o decaimento temporal de baseline de
`backend/processing/baselines/pro_baseline.py` (`TemporalBaselineDecay`) para pesar o desempenho recente mais
do que dados antigos. Produz indicadores de direcao de tendencia
(melhorando/piorando/estavel) para cada metrica rastreada e adapta os conselhos de
acordo.

### explainability.py -- ExplanationGenerator

Implementa explicabilidade do modelo decompondo previsoes de rede neural em explicacoes
legiveis. Usa atribuicao de caracteristicas (qual das 25 dimensoes de entrada contribuiu
mais para a previsao) e cadeias de raciocinio causal para explicar *por que* o modelo
recomenda uma acao especifica. Fundamental para construir a confianca do jogador nos
conselhos de coaching orientados por ML.

### pro_bridge.py -- PlayerCardAssimilator

Preenche a lacuna entre as estatisticas de jogadores profissionais (de
`hltv_metadata.db`) e a pipeline de coaching. O `PlayerCardAssimilator` carrega stat
cards de jogadores pro e realiza comparacoes baseadas em funcao: se o usuario joga como
entry fragger, suas estatisticas sao comparadas com as de entry fraggers profissionais.
O helper `get_pro_baseline_for_coach()` fornece um dicionario de baseline pronto para
uso pelo motor de correcao.

### token_resolver.py -- PlayerTokenResolver

Resolve referencias ambiguas de nomes de jogadores para identidades canonicas. Lida com
desafios comuns na nomenclatura CS2: substituicoes leet-speak (ex. "s1mple" vs "simple"),
prefixos de clan tag, homoglifos Unicode e correspondencias parciais de nomes. Usa fuzzy
string matching com limiares de similaridade configuraveis. Essencial para corresponder
nomes fornecidos pelo usuario a entradas no banco de dados de jogadores profissionais.

## Integracao com a Camada de Servicos

```
coaching_service.py
    |
    +-- seleciona modo de coaching (COPER / Hybrid / RAG / Neural)
    |
    +-- chama hybrid_engine.py (modo Hybrid)
    |       |-- inferencia ML (modelo JEPA ou RAP)
    |       +-- recuperacao RAG (knowledge/)
    |
    +-- chama correction_engine.py (todos os modos)
    |       +-- pro_bridge.py (baseline profissional)
    |
    +-- chama nn_refinement.py (se modelo disponivel)
    |
    +-- chama longitudinal_engine.py (se dados historicos presentes)
    |
    +-- chama explainability.py (se previsoes ML usadas)
    |
    +-- retorna CoachingResponse para a camada UI
```

O orquestrador `coaching_service.py` tambem injeta contexto de baseline temporal de
`backend/processing/baselines/pro_baseline.py` (`TemporalBaselineDecay`), garantindo que os conselhos de coaching
considerem como o nivel de habilidade do jogador evoluiu nas sessoes recentes.

## Notas de Desenvolvimento

- **Disciplina de flags:** Nunca ignore as flags de funcionalidade. O modo de coaching e
  selecionado exclusivamente atraves das flags de `core/config.py`. Hard-codar um modo
  causa falhas nos testes.
- **Contrato 25-dim:** Qualquer modulo que toque o vetor de caracteristicas deve respeitar
  `METADATA_DIM=25`. Veja a tabela de Contrato Dimensional no `CLAUDE.md` do projeto raiz.
- **Logging estruturado:** Todos os modulos usam
  `get_logger("cs2analyzer.coaching.<modulo>")`. Transicoes de fallback sao registradas
  no nivel WARNING com correlation IDs.
- **Thread safety:** A pipeline de coaching pode ser invocada pela thread Teacher do
  Quad-Daemon. Todo estado compartilhado deve ser acessado atraves de acessores
  thread-safe, nunca globais em nivel de modulo.
- **Testes:** Os testes residem em `Programma_CS2_RENAN/tests/`. Use as fixtures
  `mock_db_manager` e `torch_no_grad` para testes de coaching.

## Dependencias

- **PyTorch** -- Inferencia de rede neural para modos Hybrid e Neural
- **sentence-transformers** -- Geracao de embeddings para recuperacao RAG e Experience Bank
- **SQLModel** -- Persistencia do Experience Bank
- **scikit-learn** -- Metricas de similaridade para resolucao de tokens (opcional)
