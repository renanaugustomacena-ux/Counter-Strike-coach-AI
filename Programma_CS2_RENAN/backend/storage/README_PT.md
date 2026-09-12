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
| `db_models.py` | 25 classes de tabela SQLModel cobrindo todo o modelo de dados |
| `database.py` | `DatabaseManager` (monólito) + `HLTVDatabaseManager` + singletons |
| `match_data_manager.py` | Partições SQLite por-partida (Tier 3) com cache de engine LRU |
| `backup_manager.py` | Backup a quente via SQLite Online Backup API, retencao (7 diarios incluindo o mais recente + 4 semanais) |
| `db_backup.py` | Wrapper da SQLite Online Backup API + arquivamento tar.gz para dados de partida |
| `db_migrate.py` | Executor de migrações Alembic para upgrades automáticos de schema na inicialização |
| `maintenance.py` | Poda de metadados: remove dados de tick antigos preservando estatísticas agregadas |
| `state_manager.py` | `StateManager` DAO para a linha singleton `CoachState` |
| `stat_aggregator.py` | `StatCardAggregator`: saída do spider para `ProPlayer`/`ProPlayerStatCard` |
| `storage_manager.py` | `StorageManager`: caminhos de arquivos demo, controle de cota, deduplicacao |
| `remote_file_server.py` | Servidor cloud pessoal FastAPI para acesso cross-machine de demos |
| `datasets/`, `models/` | Pacotes placeholder com apenas README (`__init__.py` vazio, sem codigo) |
| `remote_telemetry/` | Apenas JSON de telemetria de exemplo (sem codigo) |

## Arquitetura Tri-Database

O sistema divide os dados em três bancos SQLite distintos para eliminar a contenção
de lock de escrita entre daemons e manter a profundidade B-tree rasa por partida.

```
+-------------------------------+
|      database.db (Monólito)   |
|  18 tabelas: dados de treino, |
|  estatísticas de jogador,     |
|  ticks, estado de coaching,   |
|  base de conhecimento         |
+---------------+---------------+
                |
                |  Processo separado / sem link FK
                v
+-------------------------------+
|    hltv_metadata.db (HLTV)    |
|  7 tabelas: ProTeam, ProPlayer|
|  ProPlayerStatCard, ProEvent, |
|  ProTournament, ProHead2Head, |
|  ProMapRecord                 |
+-------------------------------+

+--------------------------------------+
|  match_data/match_{id}.db (Tier 3)   |
|  Telemetria por-partida:             |
|  MatchTickState,                     |
|  MatchEventState,                    |
|  MatchMetadata                       |
+--------------------------------------+
   Um arquivo por partida
```

### PRAGMAs de Conexão (aplicadas em cada checkout)

```sql
PRAGMA journal_mode     = WAL;
PRAGMA synchronous      = NORMAL;
PRAGMA busy_timeout     = 30000;
PRAGMA foreign_keys     = ON;      -- DB-06: FKs são decorativas sem isto
PRAGMA wal_autocheckpoint = 512;   -- DB-07: cadência de checkpoint ~2 MB
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

Manager dedicado para `hltv_metadata.db`, isolado para evitar contencao WAL com os
daemons do session engine. Inclui `_reconcile_stale_schema()` que reconcilia tabelas
cujo conjunto de colunas divergiu da definicao do modelo: drift aditivo (o modelo tem
novas colunas, todas as colunas DB existentes ainda estao no modelo) e tratado via
`ALTER TABLE ADD COLUMN` no local (linhas preservadas); drift nao-aditivo (colunas
tipadas/renomeadas/removidas) renomeia a tabela para `<nome>_stale_<ts>` (dados
preservados para recuperacao manual) e a recria do zero. Tabelas orfas ausentes de
`_HLTV_TABLES` sao eliminadas, mas snapshots `*_stale_*` nunca sao tocados.
`hltv_metadata.db` NAO esta sob Alembic ainda -- seu schema evolui apenas via
`create_all()` mais esta reconciliacao (item backlog #47 em `TASKS.md` rastreia a
migracao para Alembic, diferida para a Fase G7).

Acesso singleton: `get_hltv_db_manager()`.

### MatchDataManager (`match_data_manager.py`)

Cria e gerencia arquivos SQLite individuais sob `config.MATCH_DATA_PATH`.
Cada partida recebe `match_{id}.db` contendo `MatchTickState`, `MatchEventState`
e `MatchMetadata`. Funcionalidades:

- Cache de engine LRU (`OrderedDict`, máximo 50 entradas) para prevenir esgotamento de file handles
- Auto-migração via `_ensure_match_schema()` (passos incrementais `ALTER TABLE`)
- Filtro `tables=` no `create_all()` para impedir vazamento de tabelas do monólito nos DBs de partida
- Utilitario de migracao `migrate_match_data()` para relocar dados em drives externos
  (apenas chamada explicita -- nada a invoca implicitamente)

### StateManager (`state_manager.py`)

DAO thread-safe para a linha singleton `CoachState` (constraint CHECK `id = 1`).
Rastreia status dos daemons, progresso do treinamento, heartbeat e limites de
recursos. Funcionalidades:

- Enum `DaemonName` previne bugs causados por erros de digitação em atualizações de status
- Escalação de telemetria (SM-02): loga como WARNING até 5 falhas consecutivas, depois ERROR
- Auto-poda de notificações (SM-03): cap em 500, remove entradas com mais de 30 dias

### BackupManager (`backup_manager.py`)

Backup a quente usando a Online Backup API do SQLite (`sqlite3.Connection.backup()` em
`backup_manager.py:119`), WAL-safe e nao-bloqueante. Politica de
retencao: mantem 7 backups diarios (o mais recente e sempre mantido) + 4 semanais.
Cada backup e verificado com `PRAGMA quick_check` antes da aceitacao. Protecao de
tamanho (ST-BK-01, 2026-08-03): recusa fazer backup de um banco de dados maior que
50 GiB (override via `CS2_BACKUP_MAX_DB_BYTES`) ou quando o espaco livre e inferior
a 1.2x o tamanho do banco de dados -- o monolito pode ter centenas de GB.

### StorageManager (`storage_manager.py`)

Gerenciador de sistema de arquivos para arquivos demo. Cuida dos caminhos de demos
de usuário e pro, controle de cota, deduplicação contra `IngestionTask` e
`PlayerMatchStats`, e proteção contra path-traversal (P2-03).

## Destaques do Modelo de Dados (db_models.py)

O módulo define 25 classes de tabela SQLModel organizadas em grupos lógicos:

- **Telemetria de jogador:** `PlayerMatchStats`, `PlayerTickState`, `RoundStats`, `PlayerProfile`
- **Framework de coaching:** `CoachState`, `CoachingInsight`, `CoachingExperience` (COPER)
- **Base de conhecimento:** `TacticalKnowledge` (RAG, embeddings 384-dim)
- **Dados pro:** `ProTeam`, `ProPlayer`, `ProPlayerStatCard`, `ProEvent`, `ProTournament`, `ProHead2Head`, `ProMapRecord`
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
- **A relocacao de dados de partida e apenas explicita.** Nada reloca os shards
  automaticamente: `warn_if_shards_in_legacy_location()` apenas loga um warning quando
  shards permanecem no antigo diretorio in-project. Chame `migrate_match_data()` voce
  mesmo quando a relocacao for intencional (a antiga migracao implicita "unica" foi
  removida em 2026-07-26 apos ter movido o corpus de shards de producao como efeito
  colateral da construcao do singleton).
