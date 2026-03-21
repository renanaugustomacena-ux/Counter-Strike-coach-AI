# Feature Engineering -- Extracao de Features Unificada

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/backend/processing/feature_engineering/`

## Introducao

Este pacote e a **unica fonte de verdade** para o vetor de features de 25
dimensoes (`METADATA_DIM = 25`) consumido por toda rede neural do projeto
(RAP Coach, JEPA, AdvancedCoachNN). Toda a logica de extracao, normalizacao
e codificacao de features reside aqui -- nenhum outro modulo e autorizado a
construir vetores de features independentemente.

O contrato fundamental: treinamento e inferencia DEVEM produzir vetores de
features identicos para dados de entrada identicos. Qualquer divergencia
causa corrupcao silenciosa do modelo conhecida como *Inference-Training Skew*.

## Inventario de Arquivos

| Arquivo | Finalidade | Exports Principais |
|---------|-----------|-------------------|
| `vectorizer.py` | Extracao e validacao do vetor de features 25-dim | `FeatureExtractor`, `FEATURE_NAMES`, `METADATA_DIM`, `DataQualityError`, `WEAPON_CLASS_MAP` |
| `base_features.py` | Limiares heuristicos configuraveis + agregacao a nivel de partida | `HeuristicConfig`, `extract_match_stats()`, `load_learned_heuristics()`, `save_heuristic_config()` |
| `rating.py` | Formula unificada HLTV 2.0 rating (componentes + regressao) | `compute_hltv2_rating()`, `compute_impact_rating()`, `compute_survival_rating()`, `compute_hltv2_rating_regression()` |
| `kast.py` | Calculo KAST (Kill/Assist/Survive/Trade) | `calculate_kast_for_round()`, `calculate_kast_percentage()`, `estimate_kast_from_stats()` |
| `role_features.py` | Features especificas por papel e classificacao | `classify_role()`, `extract_role_features()`, `get_role_coaching_focus()`, `get_adaptive_signatures()`, `ROLE_SIGNATURES`, `PlayerRole` |
| `__init__.py` | Dispatcher lazy-import (previne deadlocks de import-lock) | Reexporta todos os nomes publicos dos submodulos |

## O Vetor de Features de 25 Dimensoes

Cada tick de cada jogador e codificado em exatamente 25 valores float32. A
ordem e fixa e imposta pela assercao compile-time
`len(FEATURE_NAMES) == METADATA_DIM` (invariante `P-X-01`).

| Idx | Nome | Normalizacao | Intervalo | Categoria |
|-----|------|-------------|-----------|-----------|
| 0 | `health` | /100 | [0, 1] | Vitais |
| 1 | `armor` | /100 | [0, 1] | Vitais |
| 2 | `has_helmet` | binario | {0, 1} | Vitais |
| 3 | `has_defuser` | binario | {0, 1} | Vitais |
| 4 | `equipment_value` | /10000 | [0, 1] | Economia |
| 5 | `is_crouching` | binario | {0, 1} | Postura |
| 6 | `is_scoped` | binario | {0, 1} | Postura |
| 7 | `is_blinded` | binario | {0, 1} | Postura |
| 8 | `enemies_visible` | /5, clamped | [0, 1] | Consciencia |
| 9 | `pos_x` | /4096, clipped | [-1, 1] | Posicao |
| 10 | `pos_y` | /4096, clipped | [-1, 1] | Posicao |
| 11 | `pos_z` | /1024, clipped | [-1, 1] | Posicao |
| 12 | `view_yaw_sin` | sin(yaw_rad) | [-1, 1] | Angulo de Visao |
| 13 | `view_yaw_cos` | cos(yaw_rad) | [-1, 1] | Angulo de Visao |
| 14 | `view_pitch` | /90 | [-1, 1] | Angulo de Visao |
| 15 | `z_penalty` | `compute_z_penalty()` | [0, 1] | Espacial |
| 16 | `kast_estimate` | razao KAST | [0, 1] | Desempenho |
| 17 | `map_id` | hash md5 -> [0, 1] | [0, 1] | Contexto |
| 18 | `round_phase` | 0/0.33/0.66/1.0 | [0, 1] | Economia |
| 19 | `weapon_class` | categorico 0-1 | [0, 1] | Equipamento |
| 20 | `time_in_round` | /115, clamped | [0, 1] | Contexto |
| 21 | `bomb_planted` | binario | {0, 1} | Contexto |
| 22 | `teammates_alive` | /4 | [0, 1] | Contexto |
| 23 | `enemies_alive` | /5 | [0, 1] | Contexto |
| 24 | `team_economy` | /16000 | [0, 1] | Economia |

### Decisoes de Design

- **O angulo yaw usa codificacao sin/cos** (indices 12-13) para evitar a
  descontinuidade +/-180 graus que confundiria modelos gradient-based.
- **A identidade do mapa usa `hashlib.md5`** (indice 17), nao `hash()` do
  Python, para reprodutibilidade deterministica entre sessoes.
- **As features de contexto 20-24** sao lidas primeiro de `tick_data`
  (enriquecidos durante a ingestao), com fallback para um dict `context`
  (DemoFrame na inferencia), eliminando o skew treinamento/inferencia.
- **Weapon class** (indice 19) mapeia cerca de 70 nomes de armas CS2 (nomes
  internos + nomes display demoparser2) em 6 categorias via
  `WEAPON_CLASS_MAP`.

## Arquitetura & Conceitos

### FeatureExtractor (`vectorizer.py`)

A interface principal. Configuracao a nivel de classe via `HeuristicConfig`
habilita hot-swap runtime dos limites de normalizacao (Task 6.3).

Metodos chave:
- `extract(tick_data, map_name, context, _config_override)` -- tick unico.
- `extract_batch(tick_data_list, map_name, contexts)` -- batch com snapshot
  de config (`R4-14-03`) para consistencia thread-safe.
- `validate_feature_parity(vec, label)` -- assegura que a ultima dimensao
  seja igual a `METADATA_DIM` nos limites de treinamento e inferencia
  (`P-SR-01`).
- `get_feature_names()` -- delega para a tupla `FEATURE_NAMES`.

Mecanismos de seguranca:
- `P-VEC-01`: Warning quando `map_name` ausente (z_penalty default 0.0).
- `P-VEC-02`: Deteccao NaN/Inf com logging ERROR e clamp para defaults.
- `P-VEC-03`: Parametro `_config_override` para consistencia de batch.
- `P3-A`: Quality gate de batch -- `DataQualityError` levantado quando >5%
  dos vetores no batch continham NaN/Inf antes do clamping.
- `H-12`: Armas desconhecidas logadas em WARNING na primeira ocorrencia,
  depois DEBUG.

### HeuristicConfig (`base_features.py`)

Um `@dataclass` encapsulando todos os limites de normalizacao e constantes
de limiar. Serializavel para/de JSON via `to_dict()` / `from_dict()`. Chaves
desconhecidas sao ignoradas silenciosamente para compatibilidade futura.

`extract_match_stats()` agrega DataFrames por-round em estatisticas a nivel
de partida, calculando o rating HLTV 2.0 unificado atraves das funcoes de
`rating.py` para prevenir Inference-Training Skew.

### HLTV 2.0 Rating (`rating.py`)

Duas implementacoes coexistem por design (`F2-40`):

1. **`compute_hltv2_rating()`** -- media por componente, cada termo
   independentemente interpretavel. Usado para analise de desvios de coaching.
2. **`compute_hltv2_rating_regression()`** -- coeficientes de regressao que
   correspondem aos valores publicados HLTV (R^2=0.995). Usado para
   validacao de display UI. Inclui uma guarda runtime contra confusao
   razao/percentual kast.

As duas funcoes divergem deliberadamente -- NAO as reconcilie.

### Calculo KAST (`kast.py`)

Tres granularidades:
- `calculate_kast_for_round()` -- por-round a nivel de eventos (verificacao
  K/A/S/T com janela de trade e tick rate configuraveis).
- `calculate_kast_percentage()` -- agregado multi-round.
- `estimate_kast_from_stats()` -- aproximacao estatistica quando eventos
  por-round nao estao disponiveis (usa heuristica de overlap de assist 0.8
  e estimativa de probabilidade de trade 30%).

### Role Features (`role_features.py`)

- `ROLE_SIGNATURES` -- perfis centroide estaticos para Entry, AWPer, Support,
  Lurker e IGL baseados em analise dos top-20 jogadores HLTV.
- `classify_role()` -- delega para `RoleClassifier` (limiares aprendidos +
  consenso neural), fallback para heuristica de distancia euclidiana em
  cold start.
- `get_adaptive_signatures()` -- amplia as bandas de tolerancia via
  `MetaDriftEngine.get_meta_confidence_adjustment()` quando meta drift > 0.3.
- `get_role_coaching_focus()` -- retorna chaves de estatisticas prioritarias
  por papel.

### Lazy Imports (`__init__.py`)

Usa `__getattr__` para adiar imports de submodulos ate o primeiro acesso a
atributo. Isso previne deadlocks `_ModuleLock` quando threads daemon (workers
de ingestao) importam submodulos enquanto a thread UI Kivy detem o lock de
import.

## Pontos de Integracao

| Consumidor | Uso |
|------------|-----|
| `backend/nn/rap_coach/trainer.py` | `FeatureExtractor.extract_batch()` para dados de treinamento |
| `backend/nn/jepa_trainer.py` | `FeatureExtractor.extract_batch()` com `validate_feature_parity()` |
| `backend/services/coaching_service.py` | `FeatureExtractor.extract()` para inferencia ao vivo |
| `backend/services/analysis_orchestrator.py` | `extract_match_stats()` para analise a nivel de partida |
| `backend/processing/baselines/role_thresholds.py` | `classify_role()` para validacao de limiares |
| `core/session_engine.py` | `FeatureExtractor.configure()` na inicializacao |

## Notas de Desenvolvimento

- **Nunca adicione uma feature** sem atualizar `FEATURE_NAMES`,
  `METADATA_DIM`, a docstring de `extract()` e todas as assercoes
  `input_dim` dos modelos.
- **Nunca inclua `round_won`** como feature de treinamento -- e um label
  de resultado (invariante `P-RSB-03`).
- **Sempre chame `extract()` com `map_name`** durante o treinamento --
  z_penalty quebra sem ele (`P-VEC-01`).
- Use `_config_override` em `extract()` para processamento batch (`P-VEC-03`).
- O logging estruturado usa `get_logger("cs2analyzer.vectorizer")`.
- Dependencias: NumPy, Pandas, hashlib (stdlib), math (stdlib).
