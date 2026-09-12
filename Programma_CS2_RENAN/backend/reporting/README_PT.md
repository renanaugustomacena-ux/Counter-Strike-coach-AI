# Reporting -- Motor Analitico para Dashboard

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

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
`Programma_CS2_RENAN/reporting/`, que gera relatorios de partida em Markdown e
arquivos de imagem de heatmap/visualizacao.

## Inventario de Arquivos

| Arquivo | Linhas | Finalidade | Exports Principais |
|---------|--------|------------|--------------------|
| `__init__.py` | 0 | Marcador de pacote | -- |
| `analytics.py` | 418 | Motor matematico para dashboard | `AnalyticsEngine`, `analytics` (singleton) |

## Arquitetura e Conceitos

### `AnalyticsEngine` -- Provedor Central de Dados do Dashboard

A classe `AnalyticsEngine` e o ponto de entrada unico para toda a agregacao de dados
do dashboard. Possui uma referencia ao database manager (obtida via
`get_db_manager()`) e expoe oito metodos publicos, cada um retornando um formato de
dados especifico para um widget da interface.

Consultas com escopo de jogador compartilham um helper `_player_filter()`: se o
jogador tem pelo menos uma partida pessoal (`is_pro == False`), os resultados sao
restritos a essas linhas; caso contrario, o filtro recorre a TODAS as linhas
(incluindo partidas pro) para que a tela de Performance mostre uma visao geral pro
em vez de um estado vazio. `get_skill_radar()` e a excecao -- filtra apenas por
`player_name`.

#### `get_player_trends(player_name, limit=20)` -> DataFrame

Busca metricas de desempenho historico para o widget de grafico de tendencias:

- Consulta `PlayerMatchStats` atraves do fallback `_player_filter()` descrito acima
- Ordena por `processed_at DESC`, limita a `limit` registros (padrao 20)
- Converte resultados em um DataFrame pandas em ordem cronologica (invertido)
- Retorna um DataFrame vazio se nenhum dado existir

#### `get_skill_radar(player_name)` -> Dict

Calcula atributos de habilidade normalizados (0--100) para o widget do grafico radar:

| Eixo de Habilidade | Formula | Teto |
|--------------------|---------|------|
| **Aim** | `(accuracy * 100 * 0.5) + (HS% * 100 * 0.5)` | nao limitado |
| **Utility** | `min(100, blind_enemies / 2.0 * 100) * 0.6 + min(100, flash_assists / 1.0 * 100) * 0.4` | 100 |
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
`{rating, match_date, demo_name, kd_ratio, avg_adr, avg_kast}` para o widget de
timeline de rating, usando o fallback `_player_filter()`. Os campos estatisticos
extras alimentam o contexto de percentis pro em `performance_vm.py` (fix R4 HIGH,
2026-07-16).

#### `get_per_map_stats(player_name)` -> Dict

Agrega desempenho por mapa em `{map_name: {rating, adr, kd, matches}}`:

- Extrai nomes de mapa de `demo_name` usando padrao regex
  `(de_\w+|cs_\w+|ar_\w+)`
- Recorre a uma lista de nomes de mapas conhecidos (mirage, inferno, dust2, ...)
  para nomes de arquivo de demo como `furia-vs-navi-m1-mirage.dem`, normalizados
  para `de_<nome>`
- Agrupa partidas por mapa e calcula media de rating, ADR e K/D por mapa
- Mapas nao identificaveis sao agrupados sob `"unknown"`

#### `get_strength_weakness(player_name)` -> Dict

Calcula desvios Z-score em relacao a baseline profissional para metricas chave:

- Busca medias do jogador para rating, K/D, ADR, KAST, HS%, precisao, clutch% e
  opening duel%
- Chama `calculate_deviations()` de `pro_baseline.py` para obter Z-scores
- Z-score > 0.5 qualifica como ponto forte; Z-score < -0.5 qualifica como fraqueza
- Retorna os 5 maiores pontos fortes e as 5 maiores fraquezas, ordenados por
  magnitude

#### `get_utility_breakdown(player_name)` -> Dict

Comparacao por tipo de utilidade entre medias do usuario e medias pro para 6 metricas:
`he_damage`, `molotov_damage`, `smokes_per_round`, `flash_blind_time`,
`flash_assists`, `unused_utility`. A baseline pro e consultada a partir de dados reais
do DB (`is_pro == True`) e carrega um marcador `"_provenance": "db"`. Se nao
existirem dados pro, o dict pro e retornado vazio (Regra Anti-Fabricacao).

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
    +-- PerformanceViewModel (performance_vm.py)
    |       +-- analytics.get_rating_history()     --> timeline de rating
    |       +-- analytics.get_per_map_stats()      --> detalhamento por mapa
    |       +-- analytics.get_strength_weakness()  --> cards Z-score
    |       +-- analytics.get_utility_breakdown()  --> barras usuario vs pro
    |
    +-- MatchDetailViewModel (match_detail_vm.py)
            +-- analytics.get_hltv2_breakdown()    --> componentes HLTV 2.0
```

`get_player_trends()`, `get_skill_radar()` e `get_training_metrics()` atualmente
nao possuem consumidores conectados na UI.

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
  banco de dados. Isso e garantido pelo design, nao por guardas no codigo.
- **Verificacao de null defensiva**: Cada metodo retorna um padrao seguro (dict vazio,
  lista vazia, DataFrame vazio) se os dados subjacentes estiverem ausentes ou
  insuficientes.
- **Todas as consultas usam SQLModel ORM**: Sem SQL cru. Isso garante type safety e
  compatibilidade com a configuracao SQLite WAL.
- **A normalizacao do radar e baseada em heuristicas**: Os pesos (0.5/0.5 para Aim,
  0.6/0.4 para Utility, etc.) sao parametros de ajuste, nao saidas de ML. Ajuste-os
  no corpo do metodo conforme o modelo de coaching evolui.
- **Baselines pro a partir de dados reais**: `get_utility_breakdown()` e
  `get_strength_weakness()` usam ambos dados pro reais do banco de dados. Nenhum
  valor fabricado como fallback (Regra Anti-Fabricacao).
- **Sem caching nesta classe**: Os ViewModels gerenciam o caching e a invalidacao.
  `AnalyticsEngine` recalcula a cada chamada.
- **Logging**: Utiliza `get_logger("cs2analyzer.analytics")` para logging estruturado
  de erros. Todos os caminhos de erro registram a excecao e retornam padroes seguros.
- **O limite padrao de 20 partidas** para `get_player_trends()` previne leituras
  excessivas do DB enquanto fornece linhas de tendencia significativas.
