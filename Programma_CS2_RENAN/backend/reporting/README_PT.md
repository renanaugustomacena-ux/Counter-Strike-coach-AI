# Reporting -- Motor Analitico para Dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Portugues](README_PT.md)**

> **Autoridade:** Regra 1 (Corretude), Regra 2 (Soberania do Backend)
> **Skill:** `/correctness-check`

## Introducao

Este modulo fornece a camada de calculo matematico e agregacao de dados para a
interface do dashboard. Calcula tendencias de jogadores, dados de radar de
habilidades, metricas de treinamento, historico de rating, estatisticas por mapa,
analise de pontos fortes/fracos, detalhamento de utilidades e decomposicao dos
componentes do rating HLTV 2.0. Todos os metodos sao consultas somente leitura sem
mutacoes.

**Distincao importante:** Este e `backend/reporting/`, que foca no calculo de dados
para o dashboard Qt. E separado do diretorio de nivel superior
`Programma_CS2_RENAN/reporting/`, que lida com geracao de PDF e arquivos de saida
de visualizacao.

## Inventario de Arquivos

| Arquivo | Linhas | Finalidade | Exports Principais |
|---------|--------|------------|--------------------|
| `__init__.py` | 0 | Marcador de pacote | -- |
| `analytics.py` | 353 | Motor matematico para dashboard | `AnalyticsEngine`, `analytics` (singleton) |

## Arquitetura e Conceitos

### `AnalyticsEngine` -- Provedor Central de Dados do Dashboard

A classe `AnalyticsEngine` e o ponto de entrada unico para toda a agregacao de dados
do dashboard. Possui uma referencia ao database manager (obtida via
`get_db_manager()`) e expoe sete metodos publicos, cada um retornando um formato de
dados especifico para um widget da interface.

#### `get_player_trends(player_name, limit=20)` -> DataFrame

Busca metricas de desempenho historico para o widget de grafico de tendencias:

- Consulta `PlayerMatchStats` onde `player_name` corresponde e `is_pro == False`
- Ordena por `processed_at DESC`, limita a `limit` registros (padrao 20)
- Converte resultados em um DataFrame pandas em ordem cronologica (invertido)
- Retorna um DataFrame vazio se nenhum dado existir

#### `get_skill_radar(player_name)` -> Dict

Calcula atributos de habilidade normalizados (0--100) para o widget do grafico radar:

| Eixo de Habilidade | Formula | Teto |
|--------------------|---------|------|
| **Aim** | `(accuracy * 100 * 0.5) + (HS% * 100 * 0.5)` | 100 |
| **Utility** | `(blind_enemies / 2.0 * 100 * 0.6) + (flash_assists / 1.0 * 100 * 0.4)` | 100 |
| **Positioning** | `min(100, (KAST / 0.75) * 100)` | 100 |
| **Map Sense** | `min(100, (ADR / 100.0) * 100)` | 100 |
| **Clutch** | `min(100, clutch_win_pct * 100)` | 100 |

Retorna dict vazio `{}` se os dados forem insuficientes.

#### `get_training_metrics()` -> Dict

Busca a telemetria de treinamento mais recente da tabela `CoachState` no contexto da
sessao knowledge. Retorna epoch, total_epochs, loss de treinamento/validacao e
confidence do belief.

#### `get_rating_history(player_name, limit=50)` -> List

Retorna uma lista ordenada cronologicamente de dicts
`{rating, match_date, demo_name}` para o widget de timeline de rating.
Filtra partidas pro (`is_pro == False`).

#### `get_per_map_stats(player_name)` -> Dict

Agrega desempenho por mapa em `{map_name: {rating, adr, kd, matches}}`:

- Extrai nomes de mapa de `demo_name` usando padrao regex
  `(de_\w+|cs_\w+|ar_\w+)`
- Agrupa partidas por mapa e calcula media de rating, ADR e K/D por mapa
- Mapas nao identificaveis sao agrupados sob `"unknown"`

#### `get_strength_weakness(player_name)` -> Dict

Calcula desvios Z-score em relacao a baseline profissional para metricas chave.
Z-score > 0.5 qualifica como ponto forte; Z-score < -0.5 qualifica como fraqueza.
Retorna os 5 maiores pontos fortes e as 5 maiores fraquezas.

#### `get_utility_breakdown(player_name)` -> Dict

Comparacao por tipo de utilidade entre medias do usuario e medias pro para 6 metricas:
`he_damage`, `molotov_damage`, `smokes_per_round`, `flash_blind_time`,
`flash_assists`, `unused_utility`. A baseline pro e consultada a partir de dados reais
do DB (`is_pro == True`). Se nao existirem dados pro, o dict pro e retornado vazio
(Regra Anti-Fabricacao).

#### `get_hltv2_breakdown(player_name)` -> Dict

Decompoe o rating HLTV 2.0 do jogador em seus cinco componentes: Kill, Survival,
KAST, Impact e Damage. Cada componente e normalizado em relacao as constantes de
baseline HLTV importadas de `rating.py`.

### Singleton a Nivel de Modulo

```python
analytics = AnalyticsEngine()
```

O modulo expoe um singleton pre-construido `analytics` para importacao direta pelos
ViewModels. Isso evita chamadas repetidas a `get_db_manager()` enquanto mantem a
classe testavel via instanciacao direta.

## Integracao

```
Dashboard UI (Qt MVVM)
    |
    +-- PerformanceViewModel
    |       +-- analytics.get_player_trends()    --> grafico de tendencias
    |       +-- analytics.get_skill_radar()      --> grafico radar
    |       +-- analytics.get_rating_history()   --> timeline de rating
    |       +-- analytics.get_per_map_stats()    --> detalhamento por mapa
    |
    +-- StrengthWeaknessWidget
    |       +-- analytics.get_strength_weakness() --> cards Z-score
    |
    +-- UtilityWidget
    |       +-- analytics.get_utility_breakdown() --> barras usuario vs pro
    |
    +-- TrainingStatusWidget
            +-- analytics.get_training_metrics()  --> display epoch/loss
```

### Dependencias

| Dependencia | Modulo | Finalidade |
|-------------|--------|------------|
| `get_db_manager()` | `backend/storage/database.py` | Acesso a sessoes do DB |
| `PlayerMatchStats` | `backend/storage/db_models.py` | Modelo ORM para dados de partida |
| `CoachState` | `backend/storage/db_models.py` | Modelo ORM para estado de treinamento |
| `get_pro_baseline()` | `backend/processing/baselines/pro_baseline.py` | Baseline pro para Z-scores |
| `calculate_deviations()` | `backend/processing/baselines/pro_baseline.py` | Calculo de Z-score |
| Baselines HLTV 2.0 | `backend/processing/feature_engineering/rating.py` | Decomposicao de rating |

## Notas de Desenvolvimento

- **Contrato somente leitura**: Todos os metodos usam
  `get_db_manager().get_session()` para leituras atomicas. Nenhum metodo altera o
  banco de dados.
- **Verificacao de null defensiva**: Cada metodo retorna um padrao seguro (dict vazio,
  lista vazia, DataFrame vazio) se os dados subjacentes estiverem ausentes ou
  insuficientes.
- **Todas as consultas usam SQLModel ORM**: Sem SQL cru.
- **A normalizacao do radar e baseada em heuristicas**: Os pesos sao parametros de
  ajuste, nao saidas de ML. Ajuste-os no corpo do metodo.
- **Baselines pro a partir de dados reais**: Nenhum valor fabricado como fallback.
- **Sem caching nesta classe**: Os ViewModels gerenciam o caching.
- **Logging**: Utiliza `get_logger("cs2analyzer.analytics")` para logging estruturado.
