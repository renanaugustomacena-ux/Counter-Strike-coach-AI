> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Coaching -- Pipeline de Coaching Multi-Modo

> **Autoridade:** `backend/coaching/`
> **Skill:** `/ml-check`, `/api-contract-review`
> **Modulo proprietario:** `backend/services/coaching_service.py`

## Visao Geral

O pacote coaching e a camada de inteligencia que transforma dados de analise brutos em
feedback acionavel para o jogador. Implementa uma **pipeline de coaching com quatro modos**
onde cada modo oferece um compromisso diferente entre conselhos baseados em conhecimento e
previsoes de rede neural. O modo padrao e **COPER** ("Context Optimized with Prompt, Experience,
and Replay"), que combina um Experience Bank, recuperacao de conhecimento RAG e dados de
referencia de jogadores profissionais para produzir saida de coaching fundamentada em
evidencias reais de partida.

Todos os modos de coaching sao consumidos por um unico ponto de entrada --
`backend/services/coaching_service.py` -- que seleciona o modo ativo com base nas flags
de funcionalidade `USE_COPER_COACHING`, `USE_HYBRID_COACHING` e `USE_RAG_COACHING`
(a flag separada `USE_JEPA_MODEL` controla o adaptador de insight JEPA, nao a selecao
de modo).

## Os Quatro Modos de Coaching

| # | Modo | Flag | Descricao |
|---|------|------|-----------|
| 1 | **COPER** | `USE_COPER_COACHING=True` (padrao) | Recuperacao semantica Experience Bank + conhecimento RAG + Referencias Pro. Requer nome do mapa + dados de tick. |
| 2 | **Hybrid** | `USE_HYBRID_COACHING=True` (padrao False) | Z-scores de desvio do baseline sintetizados com contexto RAG. Requer estatisticas do jogador. |
| 3 | **Traditional + RAG** | `USE_RAG_COACHING=True` (padrao False) | Motor de correcao aprimorado com recuperacao de conhecimento tatico. Sem inferencia ML. |
| 4 | **Traditional** | _(nenhuma — sempre disponivel)_ | Motor de correcao puro baseado em desvio. Zero dependencias externas; fallback definitivo. |

### Fluxo de Fallback do Coaching

Quando um modo de maior fidelidade nao esta disponivel (modelo ausente,
base de conhecimento vazia, etc.), a pipeline degrada de forma controlada atraves da
seguinte cadeia:

```
COPER (Experience Bank + RAG + Pro)
   |  [erro/timeout, ou dados de mapa/tick ausentes]
   v
Hybrid (baseline Z + RAG)
   |  [desabilitado, estatisticas do jogador ausentes, ou erro]
   v
Traditional + RAG (motor de correcao + recuperacao de conhecimento)
   |  [USE_RAG_COACHING desabilitado]
   v
Correcoes heuristicas Traditional (correction_engine.py — terminal)
```

Cada transicao e registrada no nivel WARNING com uma mensagem contendo a razao da
degradacao, para que o operador sempre saiba qual modo esta ativo.

Nota: a cadeia acima e uma *escada de prioridade*. No momento da falha, um
erro/timeout do COPER cai para Hybrid somente quando `USE_HYBRID_COACHING` esta habilitado
e as estatisticas do jogador estao disponiveis — caso contrario, cai diretamente para
Traditional; uma falha do Hybrid sempre cai para Traditional. O nivel Traditional + RAG e
escolhido somente no momento do dispatch quando nem COPER nem Hybrid estao selecionados e
`USE_RAG_COACHING` esta habilitado.

## Inventario de Arquivos

| Arquivo | Exportacao Primaria | Proposito |
|---------|--------------------|-----------|
| `__init__.py` | API do Pacote | Re-exporta `HybridCoachingEngine`, `generate_corrections`, `ExplanationGenerator`, `PlayerCardAssimilator`, `get_pro_baseline_for_coach` |
| `hybrid_engine.py` | `HybridCoachingEngine` | Orquestrador modo Hybrid: desvios Z-score do baseline + recuperacao de conhecimento RAG + pontuacao de confianca |
| `correction_engine.py` | `generate_corrections()` | Classifica desvios Z-score pre-calculados nas top-3 correcoes ponderadas (escalonamento de confianca e importancia) |
| `nn_refinement.py` | `apply_nn_refinement()` | Escalonamento de pesos de correcao — multiplica desvios Z-score por pesos por-feature. NAO executa inferencia NN (nome historico) |
| `longitudinal_engine.py` | `generate_longitudinal_coaching()` | Rastreia tendencias de desempenho ao longo do tempo usando integracao de decaimento temporal de baseline para conselhos de melhoria a longo prazo |
| `explainability.py` | `ExplanationGenerator` | Geracao narrativa baseada em template por eixo de habilidade, mais classificacao de severidade de insight |
| `pro_bridge.py` | `PlayerCardAssimilator` | Assimila stat cards de jogadores profissionais em baselines formato coach e arquetipos |
| `token_resolver.py` | `PlayerTokenResolver` | Recupera "Player Tokens" estaticos dos pro (stat cards) de `hltv_metadata.db` e compara estatisticas de partida com eles |
| `jepa_insight_adapter.py` | `JEPAInsightAdapter` | Converte saídas sigmoid do coaching-head JEPA em objetos `InsightCandidate`. Mapeia os primeiros 10 das 25 dimensões para 5 eixos táticos. Gating por maturidade; ativado pela flag `USE_JEPA_MODEL` (padrão `False`). Conforme NO-WALLHACK — consome apenas dados POV do jogador. |

## Descricoes dos Modulos

### hybrid_engine.py -- HybridCoachingEngine

O `HybridCoachingEngine` e o orquestrador primario para o modo Hybrid de coaching.
Sua pipeline: calcula os desvios Z-score das `player_stats` em relacao ao baseline
pro (opcionalmente um baseline contextual do stat card de um pro especifico), recupera
conhecimento relevante do indice RAG e sintetiza insights unificados a partir dos desvios
e do contexto de conhecimento. Contribuicoes neurais entram na cadeia de insights atraves
do `JEPAInsightAdapter` quando a flag `USE_JEPA_MODEL` esta habilitada (26-HYB-01). A
confianca do insight combina |Z| com contagens de uso de conhecimento; baselines de
fallback obsoletos marcam cada insight com um aviso de baseline degradado (F4-02).

### correction_engine.py -- generate_corrections()

Funcao stateless que recebe desvios Z-score *pre-calculados* (a comparacao com o baseline
acontece a montante) mais `rounds_played`. Cada desvio e escalonado por um fator de
confianca (`rounds_played / 300`, limitado a 1.0) e um peso de importancia por-feature
(substituivel pela configuracao `COACH_WEIGHT_OVERRIDES`); as top-3 correcoes ordenadas
por `|weighted_z| * importance` sao retornadas como dicionarios (`feature`, `weighted_z`,
`importance`). Severidade e narrativas legiveis sao adicionadas a jusante por
`coaching_service.py` usando `ExplanationGenerator`. Este modulo e o fallback final
quando todos os modos de coaching de maior fidelidade nao estao disponiveis.

### nn_refinement.py -- apply_nn_refinement()

Etapa de escalonamento de pesos de correcao (DA-03: o nome historico e enganoso). Recebe
correcoes heuristicas de `correction_engine.py` e multiplica cada `weighted_z` por
`(1 + feature_weight)` de um dicionario de ajustes fornecido. Isto e pura aritmetica —
nenhuma rede neural e carregada, nenhuma inferencia de modelo ocorre, nenhuma pontuacao
de confianca e calculada. O dicionario de ajustes *pode* originar da saida de um modelo
NN a montante, mas este modulo e uma multiplicacao escalar. Chamado condicionalmente por
`correction_engine.py` somente quando `nn_adjustments` nao esta vazio — o caminho de
servico atual nunca passa ajustes, portanto esta etapa esta dormente em producao.

### longitudinal_engine.py -- generate_longitudinal_coaching()

Gera conselhos de coaching baseados em tendencias de desempenho ao longo de multiplas
partidas ou sessoes. Usa o decaimento temporal de baseline de
`backend/processing/baselines/pro_baseline.py` (`TemporalBaselineDecay`) para pesar o desempenho recente mais
do que dados antigos. Produz indicadores de direcao de tendencia
(melhorando/piorando/estavel) para cada metrica rastreada e adapta os conselhos de
acordo.

### explainability.py -- ExplanationGenerator

Geracao narrativa baseada em template: `generate_narrative()` renderiza templates
por-eixo (`SkillAxes` MECHANICS / POSITIONING / UTILITY / TIMING / DECISION) com
contexto dinamico (localizacao, arma, magnitude do delta). Deltas abaixo do limiar de
silencio (|delta| < 0.2) nao produzem feedback — "o silencio e uma acao valida" — e um
filtro de nivel de habilidade simplifica a saida para iniciantes.
`classify_insight_severity()` mapeia |delta| para High / Medium / Low. Usado por
`coaching_service.py` para transformar Z-scores de correcao em mensagens de coaching
legiveis.

### pro_bridge.py -- PlayerCardAssimilator

Preenche a lacuna entre as estatisticas de jogadores profissionais (de
`hltv_metadata.db`) e a pipeline de coaching. O `PlayerCardAssimilator` traduz um
`ProPlayerStatCard` no formato baseline do coach em escalas por-round (KPR/DPR — P3-02),
com normalizacao defensiva de valores em forma percentual legado (V-2), e classifica o
arquetipo do pro via `get_player_archetype()` (Star Fragger / Support Anchor / Sniper
Specialist / All-Rounder). O helper `get_pro_baseline_for_coach()` fornece um dicionario
de baseline contextual pronto para uso, utilizado por `hybrid_engine.py` quando uma
referencia pro e selecionada.

### token_resolver.py -- PlayerTokenResolver

Recupera "Player Tokens" estaticos dos pro para o AI Coach: `get_player_token()` busca
um profissional por nickname exato em `hltv_metadata.db` (`ProPlayer` + ultimo
`ProPlayerStatCard`) e monta um dicionario token estruturado (identidade, metricas core,
baselines taticos, estatisticas detalhadas granulares, metadados).
`compare_performance_to_token()` retorna um "Correction Delta" (deltas de rating / ADR /
KAST / HS mais uma flag de underperformance) para avaliacao especializada contra o token.
O fuzzy name matching reside em outro lugar (`nickname_resolver.py`, usado por
`backend/services/player_lookup.py`), nao neste modulo.

## Integracao com a Camada de Servicos

```
coaching_service.py
    |
    +-- seleciona modo de coaching (COPER / Hybrid / Traditional+RAG / Traditional)
    |
    +-- chama hybrid_engine.py (modo Hybrid)
    |       |-- desvios Z-score do baseline (baselines contextuais pro_bridge.py)
    |       +-- recuperacao RAG (knowledge/)
    |
    +-- chama correction_engine.py (modos Traditional e fallbacks de erro)
    |       +-- nn_refinement.py (somente se nn_adjustments passados -- dormente hoje)
    |
    +-- chama longitudinal_engine.py (tendencias de compute_trend())
    |
    +-- chama explainability.py (narrativas + severidade para correcoes)
    |
    +-- salva linhas CoachingInsight no banco de dados (consumidas pela UI)
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

- **PyTorch** -- Inferencia do modelo adaptador de insight JEPA em `jepa_insight_adapter.py`
- **sentence-transformers** -- Geracao de embeddings para recuperacao RAG e Experience Bank
- **SQLModel** -- Acesso ao banco de dados (conhecimento tatico, insights de coaching, stat cards pro)
