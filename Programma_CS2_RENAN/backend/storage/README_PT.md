# Camada de Armazenamento de Banco de Dados

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

## Visão Geral

Camada de persistência baseada em SQLite com modo WAL, ORM SQLModel, gerenciamento de backup e arquitetura dual-storage (monólito `database.db` + arquivos SQLite por-partida).

## Componentes Principais

### `db_models.py`
61+ classes SQLModel definindo o modelo de dados completo:
- **Estatísticas de Jogador**: `PlayerMatchStats`, `PlayerTickState`, `RoundStats`
- **Coaching**: `CoachState`, `CoachingInsight`, `CoachingExperience`
- **Conhecimento**: `TacticalKnowledge`, `ExperienceRecord`
- **Dados Pro**: `ProPlayer`, `MatchResult`, `TeamComposition`
- **Análise**: `MomentumState`, `BeliefSnapshot`, `RoleThresholdRecord`
- **Sistema**: `DemoFileRecord`, `TrainingMetrics`, `IntegrityManifest`

### `database.py`
- **`DatabaseManager`** — Gerenciador de conexões SQLite com modo WAL
- **`get_db_manager()`** — Padrão factory singleton
- **`init_database()`** — Inicialização de schema e migração

### `match_data_manager.py`
- **`MatchDataManager`** — Gerenciamento de banco de dados SQLite por-partida
- **`get_match_data_manager()`** — Factory singleton com integração config
- **`migrate_match_data()`** — Migração única para caminho de armazenamento externo
- DBs de partidas armazenados em `config.MATCH_DATA_PATH` (padrão: `PRO_DEMO_PATH/match_data/`)

### `backup_manager.py`
- **`BackupManager`** — Orquestra backup de DB monólito e todos os DBs de partidas
- Política de rotação, verificação de integridade

### Módulos de Suporte
- **`db_backup.py`** — Utilitários de backup com resolução de caminho do config
- **`db_migrate.py`** — Utilitários de migração Alembic
- **`maintenance.py`** — VACUUM, ANALYZE, verificações de integridade
- **`state_manager.py`** — Persistência CoachState
- **`stat_aggregator.py`** — Agregação RoundStats → PlayerMatchStats

## Padrões Críticos

- **Sempre use modo WAL** — `PRAGMA journal_mode=WAL` para acesso concorrente
- **Nunca hardcode o caminho match_data** — Use `config.MATCH_DATA_PATH` ou `get_match_data_manager()`
- **Chame `reset_match_data_manager()` após mudanças de caminho** — Invalida cache singleton

## Migração

Relocalização de match data implementada na sessão 2026-02-22. Localização antiga: `backend/storage/match_data/`. Nova localização: `PRO_DEMO_PATH/match_data/` (disco externo).
