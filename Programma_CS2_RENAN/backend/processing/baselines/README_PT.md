# Baselines Profissionais & Deteccao de Meta-Drift

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/backend/processing/baselines/`

## Introducao

Este pacote estabelece o quadro de referencia profissional contra o qual cada
metrica de desempenho do usuario e avaliada. Ele responde a pergunta *"como
este jogador se compara aos pros?"* mantendo baselines gaussianas (media +
desvio padrao) derivadas de estatisticas HLTV reais, detectando quando o meta
competitivo muda o suficiente para invalidar essas baselines, resolvendo
nicknames de demo in-game para identidades HLTV canonicas, e aprendendo
limiares de classificacao de papeis a partir de dados empiricos ao inves de
constantes hardcoded.

O pacote e deliberadamente **read-heavy / write-rare**: baselines e limiares
sao calculados uma vez (durante a sincronizacao HLTV ou apos a ingestao de
demos) e entao consumidos milhares de vezes pela pipeline de coaching.

## Inventario de Arquivos

| Arquivo | Finalidade | Exports Principais |
|---------|-----------|-------------------|
| `pro_baseline.py` | Baselines gaussianas de registros `ProPlayerStatCard` HLTV | `get_pro_baseline()`, `calculate_deviations()`, `get_pro_positions()`, `TemporalBaselineDecay` |
| `role_thresholds.py` | Limiares de classificacao de papeis aprendidos (com gestao cold-start) | `RoleThresholdStore`, `LearnedThreshold`, `get_role_threshold_store()` |
| `meta_drift.py` | Detecta drift estatistico e espacial nos padroes de jogo pro | `MetaDriftEngine` |
| `nickname_resolver.py` | Resolucao fuzzy de nomes de jogadores de demo para IDs HLTV | `NicknameResolver` |
| `pro_player_linker.py` | Backfill + linking por-ingestao de `PlayerMatchStats.pro_player_id` para `ProPlayer.hltv_id` | `ProPlayerLinker` |
| `__init__.py` | Marcador de pacote vazio | -- |

## Arquitetura & Conceitos

### Fusao de Baseline em Quatro Camadas (`pro_baseline.py`)

`get_pro_baseline()` estratifica todas as fontes disponiveis (prioridade
ascendente -- camadas posteriores sobrescrevem as anteriores), nao uma
cascata first-wins:

1. **Defaults hardcoded** -- `HARD_DEFAULT_BASELINE` fornece 16 distribuicoes
   de metricas calibradas manualmente para que o coach ainda funcione em
   uma instalacao nova.
2. **CSV** -- `data/external/all_Time_best_Players_Stats.csv` para dados
   historicos amplos. Mapeia dinamicamente colunas CSV via `_CSV_COLUMN_MAP`.
3. **Demo stats** -- Dados de partida reais de demos pro ingeridas via
   `_load_pro_from_demo_stats()` (fornece `accuracy` e campos derivados de
   demo).
4. **HLTV** -- Linhas `ProPlayerStatCard` de `hltv_metadata.db` agregadas
   por jogador, depois media/desvio padrao globais. Suporta filtragem
   opcional por `map_name` (Task 2.18.1) para coaching especifico por mapa;
   fornece opening duels, clutch stats e impact (maior N).

Uma chave `_provenance` registra a cadeia de fontes usadas. Quando apenas
`hard_default` esta disponivel a baseline e logada como degradada.

Protecoes:
- `P-PB-01`: Razao K/D ignorada quando DPR < 0.01 (evita razoes infladas).
- `P-PB-02`: Sobrevivencia aproximada como `max(0, min(1, 1 - dpr))` pois
  o HLTV nao expoe uma metrica de sobrevivencia dedicada.
- `P-PB-03`: O mapeamento de colunas CSV e dinamico, nao hardcoded para tres
  colunas.
- `std = 0.0` e permitido; a jusante `calculate_deviations()` pula o Z-score
  para aquela metrica ao inves de dividir por zero.

### Decaimento Temporal de Baseline (`TemporalBaselineDecay`)

O CS2 profissional evolui: estatisticas recentes devem ter mais peso do que
dados de seis meses atras. `TemporalBaselineDecay` envolve o legado
`get_pro_baseline()` com ponderacao temporal exponencial:

- **Meia-vida:** 90 dias (configuravel via `HALF_LIFE_DAYS`).
- **Peso minimo:** 0.1 (`MIN_WEIGHT`) -- dados antigos sao sub-ponderados,
  nunca descartados completamente.
- **Deteccao de meta-shift:** `detect_meta_shift()` compara duas epocas de
  baseline e sinaliza metricas que mudaram mais de 5%
  (`META_SHIFT_THRESHOLD`).

A baseline temporal e fundida com a baseline legada para garantir que nenhuma
metrica fique ausente.

### Vigilancia Meta-Drift (`meta_drift.py`)

`MetaDriftEngine` combina dois sinais de drift:

| Sinal | Peso | Fonte |
|-------|------|-------|
| Drift estatistico (variacao media Rating 2.0) | 0.4 | `hltv_metadata.db` via `ProPlayerStatCard` |
| Drift espacial (variacao do centroide de posicoes) | 0.6 | `database.db` via `PlayerTickState` |

- O drift espacial usa `P-MD-01`: dimensoes reais do mapa de `spatial_data`
  quando disponiveis, com fallback para a dispersao de dados observada.
- Limiar de drift: 10% da extensao do mapa ou 500 unidades mundo, o que for
  maior.
- Coeficiente final em `[0.0, 1.0]` alimenta
  `get_meta_confidence_adjustment()` que retorna um multiplicador de
  confianca de coaching em `[0.5, 1.0]`.

### Aprendizado de Limiares de Papel (`role_thresholds.py`)

`RoleThresholdStore` segue o **Principio Anti-Mock**: cada limiar comeca
como `None` e e populado exclusivamente a partir de dados reais.

- **Deteccao de cold-start:** `is_cold_start()` retorna `True` ate que pelo
  menos 3 limiares tenham `>= MIN_SAMPLES_FOR_VALIDITY` (30) jogadores
  unicos.
- **Validacao de consistencia:** `validate_consistency()` verifica intervalo
  `[0, 1]` antes de cada persistencia (`P-RT-03`).
- **Aprendizado por percentil:** `learn_from_pro_data()` calcula o 75o
  percentil para cada estatistica de papel (`P-RT-01`), contando jogadores
  unicos e nao pontos de dados totais (`P-RT-02`).
- **Singleton thread-safe:** `get_role_threshold_store()` usa double-checked
  locking (`P3-06`).
- **Persistencia em banco de dados:** `persist_to_db()` / `load_from_db()`
  usam o modelo `RoleThresholdRecord` para recuperacao entre reinicializacoes.

### Resolucao de Nickname (`nickname_resolver.py`)

Conecta nomes de jogadores de demo (ex. `"Spirit donk"`, `"s1mple-G2-"`)
a `ProPlayer.hltv_id` atraves de uma pipeline de tres estagios:

1. **Match exato** -- query SQL case-insensitive.
2. **Match de substring** -- verifica se algum nickname conhecido esta
   contido no nome de demo limpo.
3. **Match fuzzy** -- `SequenceMatcher` com `FUZZY_THRESHOLD = 0.8`.

Nota de complexidade (`F2-41`): lookup substring + fuzzy e `O(n)` por query,
aceitavel para < 1000 pros registrados.

## Pontos de Integracao

| Consumidor | Uso |
|------------|-----|
| `CoachingService` | Chama `get_pro_baseline()` e `calculate_deviations()` para gerar relatorios Z-score |
| Daemon `Teacher` | Chama `MetaDriftEngine.calculate_drift_coefficient()` apos o retreinamento |
| `AnalysisOrchestrator` | Usa `TemporalBaselineDecay.get_temporal_baseline()` para comparacoes ponderadas por recencia |
| `RoleClassifier` | Le `get_role_threshold_store()` para limiares aprendidos |
| `NicknameResolver` | Chamado durante a ingestao de demo para marcar jogadores pro |
| `role_features.py` | Chama `MetaDriftEngine.get_meta_confidence_adjustment()` para assinaturas adaptativas |

## Fontes de Dados

- **`hltv_metadata.db`** -- Tabelas `ProPlayer`, `ProPlayerStatCard`,
  `ProTeam` populadas pela pipeline de scraping HLTV.
- **`database.db`** -- `PlayerMatchStats`, `PlayerTickState` para analise
  de drift espacial e recuperacao de posicoes pro.
- **Bancos de dados por-partida** -- `match_data/<id>.db` para
  `get_pro_positions()`.
- **Fallback CSV** -- `data/external/all_Time_best_Players_Stats.csv`.

## Notas de Desenvolvimento

- Todas as funcoes de baseline sao **leitores puros** -- nunca mutam o banco
  de dados. Apenas `RoleThresholdStore.persist_to_db()` escreve.
- O logging estruturado usa `get_logger("cs2analyzer.<module>")`.
- O dicionario `HARD_DEFAULT_BASELINE` e o ultimo recurso e deve ser
  atualizado periodicamente para refletir as medias pro atuais.
- `get_pro_positions()` limita a saida via amostragem uniforme para
  restringir a memoria.
- `R4-20-01`: As queries ao banco de dados usam `.limit()` e
  `.yield_per(500)` para prevenir consumo de memoria ilimitado.
