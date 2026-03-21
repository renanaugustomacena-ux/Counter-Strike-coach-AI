# Camada de Armazenamento de Banco de Dados

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

**Autoridade:** `Programma_CS2_RENAN/backend/storage/`
Camada de persistência tri-database que alimenta toda operação de dados no Macena CS2 Analyzer.

## Introdução

Este pacote implementa toda a camada de persistência de dados utilizando SQLite em
modo WAL, ORM SQLModel/SQLAlchemy e uma arquitetura de armazenamento em três
camadas. Cada tick de jogador, estatística de partida, insight de coaching e perfil
de jogador profissional passa por estes módulos antes de chegar ao pipeline de
treinamento da rede neural ou à interface do usuário. O design prioriza durabilidade
dos dados, acesso concorrente pelos daemons e portabilidade entre máquinas.

## Inventário de Arquivos

| Arquivo | Propósito |
|---------|-----------|
| `db_models.py` | 20 classes de tabela SQLModel cobrindo todo o modelo de dados |
| `database.py` | `DatabaseManager` (monólito) + `HLTVDatabaseManager` + singletons |
| `match_data_manager.py` | Partições SQLite por-partida (Tier 3) com cache de engine LRU |
| `backup_manager.py` | Backup a quente via `VACUUM INTO`, política de retenção (7 diários + 4 semanais) |
| `db_backup.py` | Wrapper da SQLite Online Backup API + arquivamento tar.gz para dados de partida |
| `db_migrate.py` | Executor de migrações Alembic para upgrades automáticos de schema na inicialização |
| `maintenance.py` | Poda de metadados: remove dados de tick antigos preservando estatísticas agregadas |
| `state_manager.py` | `StateManager` DAO para a linha singleton `CoachState` |
| `stat_aggregator.py` | `StatCardAggregator`: saída do spider para `ProPlayer`/`ProPlayerStatCard` |
| `storage_manager.py` | `StorageManager`: caminhos de arquivos demo, controle de cota, deduplicação |
| `remote_file_server.py` | Servidor cloud pessoal FastAPI para acesso cross-machine de demos |

## Arquitetura Tri-Database

O sistema divide os dados em três bancos SQLite distintos para eliminar a contenção
de lock de escrita entre daemons e manter a profundidade B-tree rasa por partida.

```
+-------------------------------+
|      database.db (Monólito)   |
|  17 tabelas: dados de treino, |
|  estatísticas de jogador,     |
|  ticks, estado de coaching,   |
|  base de conhecimento         |
+---------------+---------------+
                |
                |  Processo separado / sem link FK
                v
+-------------------------------+
|    hltv_metadata.db (HLTV)    |
|  3 tabelas: ProTeam,          |
|  ProPlayer, ProPlayerStatCard |
+-------------------------------+

+-------------------------------+
|  match_data/{id}.db (Tier 3)  |
|  Telemetria por-partida:      |
|  MatchTickState,              |
|  MatchEventState,             |
|  MatchMetadata                |
+-------------------------------+
   Um arquivo por partida (~1.7M linhas cada)
```

### PRAGMAs de Conexão (aplicadas em cada checkout)

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous  = NORMAL;
PRAGMA busy_timeout = 30000;
```

Pool de engine: `pool_size=1, max_overflow=4` para segurança single-writer do SQLite.

## Classes Principais

### DatabaseManager (`database.py`)

Gerencia o monólito `database.db`. Fornece:

- `create_db_and_tables()` -- inicialização do schema (filtrado a `_MONOLITH_TABLES`)
- `get_session()` -- context manager com auto-commit/rollback e `expire_all()` em caso de falha
- `upsert()` -- upsert atômico; usa `INSERT ... ON CONFLICT` do SQLite para `PlayerMatchStats`
- `delete_match_cascade()` -- ordem de exclusão FK-safe (filhos primeiro, depois pai)
- `detect_orphans()` -- encontra arquivos DB por-partida sem um `MatchResult` correspondente

Acesso singleton: **sempre** use `get_db_manager()` (double-checked locking).

### HLTVDatabaseManager (`database.py`)

Manager dedicado para `hltv_metadata.db`, isolado para evitar contenção WAL com os
daemons do session engine. Inclui `_reconcile_stale_schema()` que descarta e recria
tabelas cujas colunas divergiram da definição do modelo.

Acesso singleton: `get_hltv_db_manager()`.

### MatchDataManager (`match_data_manager.py`)

Cria e gerencia arquivos SQLite individuais sob `config.MATCH_DATA_PATH`.
Cada partida recebe `match_{id}.db` contendo `MatchTickState`, `MatchEventState`
e `MatchMetadata`. Funcionalidades:

- Cache de engine LRU (`OrderedDict`, máximo 50 entradas) para prevenir esgotamento de file handles
- Auto-migração via `_ensure_match_schema()` (passos incrementais `ALTER TABLE`)
- Filtro `tables=` no `create_all()` para impedir vazamento de tabelas do monólito nos DBs de partida
- Utilitário de migração `migrate_match_data()` para relocar dados em drives externos

### StateManager (`state_manager.py`)

DAO thread-safe para a linha singleton `CoachState` (constraint CHECK `id = 1`).
Rastreia status dos daemons, progresso do treinamento, heartbeat e limites de
recursos. Funcionalidades:

- Enum `DaemonName` previne bugs causados por erros de digitação em atualizações de status
- Escalação de telemetria (SM-02): loga como WARNING até 5 falhas consecutivas, depois ERROR
- Auto-poda de notificações (SM-03): cap em 500, remove entradas com mais de 30 dias

### BackupManager (`backup_manager.py`)

Backup a quente usando `VACUUM INTO` (não-bloqueante em modo WAL). Política de
retenção: mantém o mais recente + 7 diários + 4 semanais. Cada backup é verificado
com `PRAGMA quick_check` antes da aceitação.

### StorageManager (`storage_manager.py`)

Gerenciador de sistema de arquivos para arquivos demo. Cuida dos caminhos de demos
de usuário e pro, controle de cota, deduplicação contra `IngestionTask` e
`PlayerMatchStats`, e proteção contra path-traversal (P2-03).

## Destaques do Modelo de Dados (db_models.py)

O módulo define 20 classes de tabela SQLModel organizadas em grupos lógicos:

- **Telemetria de jogador:** `PlayerMatchStats`, `PlayerTickState`, `RoundStats`
- **Framework de coaching:** `CoachState`, `CoachingInsight`, `CoachingExperience` (COPER)
- **Base de conhecimento:** `TacticalKnowledge` (RAG, embeddings 384-dim)
- **Dados pro:** `ProTeam`, `ProPlayer`, `ProPlayerStatCard`
- **Estrutura de partida:** `MatchResult`, `MapVeto`
- **Dados externos:** `Ext_TeamRoundStats`, `Ext_PlayerPlaystyle`
- **Controle de pipeline:** `IngestionTask`, `ServiceNotification`
- **Observabilidade:** `DataLineage`, `DataQualityMetric`, `CalibrationSnapshot`
- **Ajuste de ML:** `RoleThresholdRecord`

Proteções de tamanho de campos JSON são aplicadas via validadores Pydantic:
`MAX_GAME_STATE_JSON_BYTES = 16 KB`, `MAX_AUX_JSON_BYTES = 8 KB`.

## Pontos de Integração

```
session_engine.py ──> get_db_manager()   ──> database.db
                  ──> get_state_manager() ──> CoachState (linha singleton)

hltv_sync_service ──> get_hltv_db_manager() ──> hltv_metadata.db

pipeline de ingestão ──> get_match_data_manager() ──> match_data/{id}.db
                     ──> get_db_manager()          ──> PlayerMatchStats, RoundStats
```

## Notas de Desenvolvimento

- **Nunca instancie managers diretamente.** Use os singletons `get_db_manager()`,
  `get_hltv_db_manager()`, `get_match_data_manager()` e `get_state_manager()`.
- **Chame `reset_match_data_manager()` após alterações em `PRO_DEMO_PATH`** para invalidar
  o pool de engines em cache e utilizar o novo caminho.
- **O banco HLTV NÃO tem NADA a ver com arquivos demo.** Ele faz scraping de estatísticas
  de jogadores profissionais do hltv.org. A ingestão de demos é um pipeline inteiramente
  separado.
- **Regras de cascade FK:** `ON DELETE CASCADE` para dados dependentes (stat cards, map vetoes);
  `ON DELETE SET NULL` para dados que devem sobreviver à exclusão do pai (ticks, experiências).
- **Relocação de dados de partida:** migração única de `backend/storage/match_data/` para
  `PRO_DEMO_PATH/match_data/` executada automaticamente na primeira inicialização após
  a mudança de caminho.
