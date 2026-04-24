> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

# Analysis — Motores de Teoria dos Jogos e Estatistica

**Autoridade:** Implementacao Phase 6 Game Theory + modulos fundamentais Phase 1B.
**Nivel de habilidade:** Avancado — Inferencia bayesiana, teoria da informacao, busca adversarial, classificacao neural.

---

## Visao Geral

Este diretorio contem 11 motores analiticos que formam a camada de inteligencia tatica do sistema de coaching CS2. Eles transformam dados brutos de demo (posicoes tick, eventos de kill, snapshots economicos, lancamentos de utility) em insights de coaching acionaveis atraves de teoria dos jogos, modelagem probabilistica e analise estatistica.

Cada modulo segue o padrao factory function para acesso singleton thread-safe. Todos os motores sao orquestrados por `backend/services/coaching_service.py` e expostos a UI atraves do analysis orchestrator.

---

## Inventario de Arquivos

| Arquivo | Classes Principais | Factory Function | Proposito |
|---------|-------------------|------------------|-----------|
| `belief_model.py` | `DeathProbabilityEstimator`, `BeliefState`, `AdaptiveBeliefCalibrator` | `get_death_estimator()` | Probabilidade de morte bayesiana com calibracao online |
| `win_probability.py` | `WinProbabilityPredictor`, `WinProbabilityNN`, `GameState` | `get_win_predictor()` | Predicao neural de vitoria do round a partir do estado do jogo |
| `blind_spots.py` | `BlindSpotDetector`, `BlindSpot` | `get_blind_spot_detector()` | Decisoes subotimas recorrentes vs. game tree |
| `engagement_range.py` | `EngagementRangeAnalyzer`, `NamedPositionRegistry`, `EngagementProfile` | `get_engagement_range_analyzer()` | Perfil de distancias de kill e anotacao de callouts |
| `entropy_analysis.py` | `EntropyAnalyzer`, `UtilityImpact` | `get_entropy_analyzer()` | Entropia de Shannon para eficacia de utility |
| `deception_index.py` | `DeceptionAnalyzer`, `DeceptionMetrics` | `get_deception_analyzer()` | Quantificacao de engano tatico |
| `game_tree.py` | `ExpectiminimaxSearch`, `OpponentModel`, `GameNode` | `get_game_tree_search()` | Arvore de decisao adversarial com nos chance |
| `role_classifier.py` | `RoleClassifier`, `RoleProfile` | `get_role_classifier()` | Classificacao neural + heuristica de 5 funcoes |
| `utility_economy.py` | `UtilityAnalyzer`, `EconomyOptimizer`, `EconomyDecision` | `get_utility_analyzer()`, `get_economy_optimizer()` | Eficiencia de granadas e otimizacao de buy round |
| `momentum.py` | `MomentumTracker`, `MomentumState` | `get_momentum_tracker()` | Momentum de round com deteccao de tilt |
| `movement_quality.py` | `MovementQualityAnalyzer` | `get_movement_quality_analyzer()` | Detector de erros de posicionamento (paper MLMove, 4 padroes) |
| `__init__.py` | _(re-exporta todos os simbolos publicos)_ | _(todas as factory functions)_ | Superficie da API do pacote |

---

## Descricoes dos Modulos

### 1. Modelos Probabilisticos

#### belief_model.py — Avaliacao Bayesiana de Morte

Estima `P(death | belief, HP, armor, weapon_class)` usando uma atualizacao bayesiana logistica. O dataclass `BeliefState` captura a assimetria informacional: inimigos visiveis, contagem de inimigos inferidos, idade da informacao e exposicao posicional. A ameaca decai exponencialmente via `THREAT_DECAY_LAMBDA` (padrao 0.1, calibravel).

O `AdaptiveBeliefCalibrator` estende a calibracao com tres pipelines:
- **Priors por faixa de HP** a partir de taxas historicas de morte por round (agrupadas em full/damaged/critical).
- **Multiplicadores de letalidade de armas** a partir de razoes de kill por classe de arma, normalizados para rifle = 1.0.
- **Lambda de decay da ameaca** ajustado via minimos quadrados log-linearizados em bins de information-age.

Todos os valores calibrados sao limitados por safety bounds e persistidos como linhas `CalibrationSnapshot` para observabilidade. A funcao auxiliar `extract_death_events_from_db()` extrai dados de calibracao de `RoundStats` com um limite de `MAX_CALIBRATION_SAMPLES = 5000`.

#### win_probability.py — Predicao Neural de Vitoria

Uma rede neural feedforward de 12 features (64 -> 32 -> 1 com sigmoid) prediz a probabilidade de vitoria do round em tempo real. O dataclass `GameState` captura economia, contagem de jogadores, utility, controle de mapa, tempo, estado da bomba e lado. Normalizacao de features: economia / 16000, jogadores / 5, tempo / 115, utility / 5.

O pos-processamento heuristico sobrescreve a saida neural para casos deterministicos (0 vivos = 0%, 0 inimigos = 100%) e aplica clamps de vantagem de jogadores e ajustes para bomba plantada. A validacao de checkpoint (regra A-12) impede o carregamento cruzado do modelo trainer de 9 dimensoes no predictor de 12 dimensoes.

---

### 2. Analise Tatica

#### blind_spots.py — Deteccao de Fraquezas Estrategicas

Compara as acoes do jogador com as recomendacoes otimas do `ExpectiminimaxSearch` ao longo dos rounds historicos. Classifica os estados de jogo em situacoes legiveis (ex.: "1v3 clutch", "post-plant advantage", "eco round") e agrega as discrepancias por frequencia e impacto na probabilidade de vitoria.

O metodo `generate_training_plan()` produz um plano de coaching em linguagem natural focando nos top-N blind spots de maior impacto, com recomendacoes especificas de pratica por tipo de acao (push, hold, rotate, use_utility).

#### engagement_range.py — Perfilamento de Distancias de Kill

Calcula distancias euclidianas de kill a partir de posicoes 3D e as classifica em quatro faixas: close (<500u), medium (500-1500u), long (1500-3000u), extreme (>3000u). O `EngagementProfile` e comparado com baselines pro especificas por funcao (AWPer, Entry, Support, Lurker, IGL, Flex) com um limiar de desvio de 15%.

Inclui `NamedPositionRegistry` com 60+ posicoes de callout hardcoded em 9 mapas competitivos (Mirage, Inferno, Dust2, Anubis, Nuke, Ancient, Overpass, Vertigo, Train). Suporta extensao JSON para callouts da comunidade. Os eventos de kill sao anotados com a posicao nomeada mais proxima para output legivel.

#### entropy_analysis.py — Avaliacao de Utility baseada em Teoria da Informacao

Mede a entropia de Shannon `H = -sum(p * log2(p))` das distribuicoes posicionais inimigas antes e depois dos lancamentos de utility. As posicoes sao discretizadas em uma grade 32x32 (configuravel). O delta de entropia quantifica o ganho informacional de cada lancamento, normalizado em relacao aos maximos teoricos por tipo de utility (smoke: 2.5 bits, molotov: 2.0, flash: 1.8, HE: 1.5).

A thread safety e mantida via `_buffer_lock` protegendo o buffer de grade pre-alocado. O metodo `rank_utility_usage()` ordena os lancamentos por eficacia para output de coaching.

#### deception_index.py — Quantificacao de Engano Tatico

Calcula um indice de engano composto a partir de tres sub-metricas:
- **Taxa de fake flash** (peso 0.25): fracao de flashbangs que nao cegam inimigos dentro de 128 ticks (~2s). Detectado via `searchsorted` vetorizado sobre ticks de eventos blind.
- **Taxa de rotation feint** (peso 0.40): reversoes significativas de direcao (>108 graus) nos caminhos de movimento amostrados, normalizadas pela extensao do mapa.
- **Pontuacao de sound deception** (peso 0.35): razao de crouch inversa como proxy para geracao deliberada de ruido vs. movimento silencioso.

O metodo `compare_to_baseline()` produz output de coaching em linguagem natural comparando as metricas do jogador com baselines pro.

---

### 3. Otimizacao de Decisoes

#### game_tree.py — Busca Expectiminimax

Modela a estrategia de round CS2 como uma arvore alternada max/min/chance com quatro acoes taticas: push, hold, rotate, use_utility. Os nos folha sao avaliados pelo `WinProbabilityPredictor` (carregado de forma lazy para evitar imports circulares).

O `OpponentModel` adapta as distribuicoes de acoes usando:
- Priors por faixa economica (eco/force/full_buy).
- Ajustes por lado (T push mais, CT hold mais).
- Modificadores de vantagem de jogadores e pressao temporal.
- Blending EMA com perfis aprendidos quando 10+ rounds de dados estao disponiveis.

Funcionalidades de performance: transposition table (`_TT_MAX_SIZE = 10000`), hashing deterministico de estado, orcamento de nos configuravel (`DEFAULT_NODE_BUDGET = 1000`). O metodo `suggest_strategy()` retorna recomendacoes em linguagem natural com probabilidade de vitoria e nivel de confianca.

#### role_classifier.py — Classificacao Neural de 5 Funcoes

Arquitetura de classificador duplo combinando scoring heuristico ponderado com uma opiniao secundaria neural:
- **Heuristico**: calcula pontuacoes de afinidade por funcao a partir de estatisticas (AWP kill ratio, entry rate, assist rate, survival rate, solo kills) contra limiares aprendidos do `RoleThresholdStore`.
- **Neural**: head softmax de 5 classes carregado de checkpoint (`load_role_head()`), com normalizacao de features usando estatisticas de treinamento.
- **Consensus**: concordancia aumenta a confianca (+0.1), neural sobrescreve o heuristico apenas com margem suficiente (+0.1).

O guard cold-start retorna FLEX com 0% de confianca quando o `RoleThresholdStore` nao tem dados aprendidos. A classificacao em nivel de equipe (`classify_team()`) impoe restricoes de composicao (maximo 1 AWPer). O metodo `audit_team_balance()` detecta fraquezas estruturais (Entry faltando, Lurkers duplicados, etc.).

Dicas de coaching especificas por funcao sao recuperadas via RAG (`KnowledgeRetriever`) com fallback para `_FALLBACK_TIPS` estaticos.

---

### 4. Economia e Recursos

#### utility_economy.py — Eficiencia de Granadas e Decisoes de Compra

`UtilityAnalyzer` pontua cada tipo de utility contra baselines pro: molotov (35 dmg/lancamento), HE (25 dmg/lancamento), flash (1.2 inimigos/flash), smoke (0.9 taxa de uso). Gera recomendacoes por tipo quando a eficacia < 50% e calcula o impacto economico em dolares.

`EconomyOptimizer` recomenda decisoes de compra (full-buy, force-buy, half-buy, eco, pistol) baseando-se em dinheiro atual, numero do round, lado, diferencial de placar e loss bonus. Suporta formatos MR12 (padrao CS2) e MR13 (legacy) via mapeamento `HALF_ROUND` configuravel. Trata casos especiais para pistol rounds e rounds criticos na troca de lado.

#### momentum.py — Rastreamento de Momentum Psicologico

Modela o momentum como um multiplicador com decaimento temporal (limitado [0.7, 1.4]) dirigido por sequencias de vitorias/derrotas. Sequencias de vitorias adicionam +0.05 por round; sequencias de derrotas subtraem -0.04 (assimetrico para refletir a vantagem economica do CS2). O momentum decai exponencialmente entre rounds pulados (`decay_rate = 0.15`) e reseta na troca de lado (round 13 MR12, round 16 MR13).

A deteccao de tilt e acionada quando o multiplicador < 0.85 (~3 derrotas consecutivas). A funcao auxiliar `predict_performance_adjustment()` escala os ratings base do jogador pelo multiplicador de momentum. A funcao `from_round_stats()` constroi uma timeline completa de momentum a partir de registros `RoundStats`.

---

## Fluxo de Integracao

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
    |                                |   Plano de Treinamento
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
    +--> EconomyOptimizer ----------+    UI / Relatorios
    |                                |
    +--> ExpectiminimaxSearch ------+
              |
              v
         OpponentModel
```

---

## Exports das Factory Functions

Todas as factory functions sao re-exportadas de `__init__.py`:

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

## Algoritmos Chave

| Algoritmo | Modulo | Descricao |
|-----------|--------|-----------|
| Atualizacao logistica bayesiana | `belief_model.py` | Prior log-odds + termos likelihood ponderados -> posterior sigmoid |
| Decaimento exponencial da ameaca | `belief_model.py` | `P(threat) = visible + inferred * exp(-lambda * age) * 0.5` |
| Ajuste lambda por minimos quadrados | `belief_model.py` | Log-linearizacao death rate vs. info age, `polyfit` grau 1 |
| MLP com inicializacao Xavier | `win_probability.py` | 12 -> 64 -> 32 -> 1 sigmoid, ReLU + Dropout |
| Entropia de Shannon em grade | `entropy_analysis.py` | `H = -sum(p * log2(p))` sobre discretizacao espacial 32x32 |
| Deteccao de flash vetorizada | `deception_index.py` | `searchsorted` em ticks blind ordenados para matching O(F log B) |
| Expectiminimax + TT | `game_tree.py` | Arvore max/min/chance com memoizacao em transposition table |
| Blending EMA do oponente | `game_tree.py` | `(1 - alpha) * base + alpha * learned`, alpha limitado a 0.7 |
| Consensus de classificador duplo | `role_classifier.py` | Heuristico + neural com regras de fusao boost/margem |
| Decaimento exponencial de momentum | `momentum.py` | `multiplier = 1.0 +/- streak_delta * exp(-decay * gap)` |

---

## Notas de Desenvolvimento

1. **Thread safety.** `DeathProbabilityEstimator` usa double-checked locking para seu singleton. `EntropyAnalyzer` protege seu buffer de grade compartilhado com `_buffer_lock`. Os demais modulos sao instanciados por-request via factory functions.

2. **Imports lazy.** `ExpectiminimaxSearch` carrega `WinProbabilityPredictor` de forma lazy para quebrar cadeias de import circular. `BlindSpotDetector` importa `ExpectiminimaxSearch` no momento do `__init__` (nivel de funcao).

3. **Pipeline de calibracao.** `AdaptiveBeliefCalibrator.auto_calibrate()` e chamado pelo daemon Teacher periodicamente. Os snapshots de calibracao sao persistidos como linhas DB `CalibrationSnapshot` para rollback e observabilidade.

4. **Comportamento cold-start.** `RoleClassifier` retorna FLEX/0% confianca quando `RoleThresholdStore` nao tem dados aprendidos. `OpponentModel` recai sobre `_DEFAULT_OPPONENT_PROBS` ate que 10+ rounds sejam observados.

5. **Isolamento de checkpoint.** `WinProbabilityNN` (predictor 12-dim) e `WinProbabilityTrainerNN` (trainer 9-dim) sao arquiteturas separadas. A regra A-12 valida a dimensao de input antes do `load_state_dict` para prevenir corrupcao silenciosa.

6. **Posicoes nomeadas.** O `NamedPositionRegistry` inclui 60+ callouts em 9 mapas. Posicoes adicionais podem ser carregadas de JSON sem alteracoes no codigo via `load_from_json()`.

7. **Safety bounds.** Todos os parametros calibrados sao limitados: priors [0.05, 0.95], letalidade de armas [0.1, 3.0], lambda de decay [0.01, 1.0], momentum [0.7, 1.4]. Isso previne valores patologicos de corromper analises a jusante.

8. **Logging estruturado.** Cada modulo usa `get_logger("cs2analyzer.analysis.<modulo>")` com suporte a correlation ID para rastrear chamadas de analise atraves da pipeline de coaching.

---

## Dependencias

- **PyTorch** — `WinProbabilityNN`, head neural de funcoes, operacoes com tensores.
- **NumPy** — Calculo de entropia em grade, deteccao de flash vetorizada, analise estatistica.
- **pandas** — DataFrames de calibracao, dados de round para analise de engano.
- **SQLModel** — Persistencia de `CalibrationSnapshot`, queries em `RoundStats`.
- **Biblioteca padrao** — `math`, `threading`, `dataclasses`, `json`, `pathlib`, `enum`, `collections`.
