> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Sistema de Migração de Banco de Dados (Alembic)

> **Autoridade:** Regra 4 (Persistência de Dados), Regra 6 (Governança de Mudanças)
> **Skill:** `/db-review`

Sistema de migração de banco de dados usando Alembic para gerenciar a evolução do esquema SQLite no Macena CS2 Analyzer. Todas as mudanças de esquema no banco de dados monolítico (`database.db`) devem passar por migrações Alembic — nenhum DDL manual em produção.

## Estrutura do Diretório

```
alembic/
├── env.py                  # Configuração do ambiente Alembic
├── script.py.mako          # Template de script de migração
└── versions/               # Histórico de migrações (sequencial, imutável)
    ├── f769fbe67229_...    # Completude de campos de perfil (root)
    ├── 7a30a0ea024e_...    # Sincronização de esquema
    ├── 89850b6e0a49_...    # Estatísticas de jogadores profissionais
    ├── 8a93567a2798_...    # Vinculação de física pro
    ├── c8a2308770e5_...    # Triggers de retreinamento
    ├── 8c443d3d9523_...    # Suporte a daemon triplo
    ├── 609fed4b4dce_...    # Rastreamento de tarefa de ingestão
    ├── e3013f662fd4_...    # Sincronização de estado de coaching
    ├── 57a72f0df21e_...    # Heartbeat nullable
    ├── da7a6be5c0c7_...    # Notificações de serviço
    ├── 19fcff36ea0a_...    # Telemetria heartbeat
    ├── 3c6ecb5fe20e_...    # Colunas do plano fusion
    ├── a1b2c3d4e5f6_...    # Métricas de qualidade de dados
    ├── b2c3d4e5f6a7_...    # Enriquecimento de tick de jogador
    ├── c3d4e5f6a7b8_...    # Rótulo de estratégia de experiência de coaching
    ├── d4e5f6a7b8c9_...    # Colunas SteamID
    ├── e5f6a7b8c9d0_...    # Índice de stream POV
    ├── f6a7b8c9d0e1_...    # Remoção de connect_state
    └── a7b8c9d0e1f2_...    # Fonte de data da partida (head)
```

## Histórico de Migrações (19 Revisões)

Cadeia linear única, da mais antiga. Head atual: `a7b8c9d0e1f2`.

| Revisão | Descrição | Tabelas Afetadas |
|---------|-----------|------------------|
| `f769fbe67229` | Adição de campos de perfil faltantes (root) | `PlayerProfile`, `IngestionTask` (nova) |
| `7a30a0ea024e` | Sincronização de tabelas faltantes | `CalibrationSnapshot` (nova), `RoleThresholdRecord` (nova) |
| `89850b6e0a49` | Adição de estatísticas de jogadores profissionais | `ProTeam` (nova), `ProPlayer` (nova), `ProPlayerStatCard` (nova) |
| `8a93567a2798` | Vinculação de física pro às estatísticas | `PlayerMatchStats` (FK para `ProPlayer`) |
| `c8a2308770e5` | Suporte a trigger de retreinamento | `CoachState` |
| `8c443d3d9523` | Suporte a daemon triplo (Hunter/Digester/Teacher) | `CoachState` |
| `609fed4b4dce` | Adição de last_tick_processed à IngestionTask | `IngestionTask` |
| `e3013f662fd4` | Adição de sync e intervalo ao CoachState | `CoachState` |
| `57a72f0df21e` | Adição de heartbeat nullable ao CoachState | `CoachState` |
| `da7a6be5c0c7` | Adição de tabela de notificações de serviço | `ServiceNotification` (nova) |
| `19fcff36ea0a` | Adição de telemetria heartbeat ao CoachState | `CoachState` |
| `3c6ecb5fe20e` | Colunas do plano fusion (trade kills, detalhamento de utilitários, feedback COPER) | `PlayerMatchStats`, `CoachingExperience` |
| `a1b2c3d4e5f6` | Adição de qualidade de dados ao PlayerMatchStats | `PlayerMatchStats` |
| `b2c3d4e5f6a7` | Adição de colunas de enriquecimento ao PlayerTickState | `PlayerTickState` |
| `c3d4e5f6a7b8` | Adição de strategy_label ao CoachingExperience | `CoachingExperience` |
| `d4e5f6a7b8c9` | Adição de steamid a tick e match stats | `PlayerTickState`, `PlayerMatchStats` |
| `e5f6a7b8c9d0` | Adição de índice de stream POV ao PlayerTickState | `PlayerTickState` (somente índice) |
| `f6a7b8c9d0e1` | Remoção de connect_state do Ext_PlayerPlaystyle | `Ext_PlayerPlaystyle` |
| `a7b8c9d0e1f2` | Adição de marcador de proveniência match_date_source (head) | `PlayerMatchStats` |

## `env.py` — Configuração do Ambiente

O script de ambiente gerencia tanto o modo de migração offline quanto online:

- **Estabilização de caminhos** via `core.config.stabilize_paths()` — garante a resolução correta de `CORE_DB_DIR`
- **Import de modelos** — importa explicitamente 19 classes SQLModel de `Programma_CS2_RENAN/backend/storage/db_models.py` para diff autogenerate contra `SQLModel.metadata`
- **Backup pré-migração** — o modo online chama `db_backup.backup_monolith()` antes de executar migrações (não fatal em caso de falha)
- **URL do Banco** — `CS2_ALEMBIC_URL` (variável de ambiente, para DBs de verificação descartáveis) prevalece sobre `core.config.DATABASE_URL` (o monolítico `database.db`)

```python
# Resolução de URL + execução online (simplificada)
config.set_main_option("sqlalchemy.url", os.environ.get("CS2_ALEMBIC_URL", DATABASE_URL))
_pre_migration_backup()  # backup_monolith(), não fatal
connectable = engine_from_config(..., poolclass=pool.NullPool)
with connectable.connect() as connection:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

## Escopo e Limites

Alembic gerencia **apenas** o banco de dados monolítico (`database.db`). Os outros dois bancos na arquitetura tri-database são gerenciados separadamente:

| Banco de Dados | Gerenciador | Estratégia de Migração |
|----------------|-------------|----------------------|
| `database.db` (monolítico) | Alembic | Migrações versionadas sequenciais |
| `hltv_metadata.db` | `HLTVDatabaseManager` | Esquema via `SQLModel.metadata.create_all()` no primeiro uso |
| `match_data/<id>.db` (por partida) | `MatchDataManager` | Esquema criado por demo ingerida |

Trazer `hltv_metadata.db` para o Alembic é **trabalho em backlog** (TASKS.md #47, Programme Phase G7) — hoje seu esquema ainda evolui fora do Alembic.

## Uso

```bash
# Ativar o ambiente virtual do projeto primeiro (veja "Manual Setup" no README.md principal)

# Verificar status de migração atual
alembic current

# Atualizar para versão mais recente
alembic upgrade head

# Downgrade de uma revisão
alembic downgrade -1

# Gerar nova migração (após modificar db_models.py)
alembic revision --autogenerate -m "descrição_da_mudança"

# Visualizar histórico de migrações
alembic history --verbose
```

## Princípios de Migração

1. **Sequencial** — uma cadeia linear única, sem ramificações (head atual: `a7b8c9d0e1f2`)
2. **Reversível** — toda migração tem funções `upgrade()` e `downgrade()`
3. **Versionado** — migrações são commitadas no git e nunca modificadas após merge
4. **Testado** — executar `python tools/headless_validator.py` após qualquer mudança de esquema
5. **Atômico** — cada migração é uma única mudança lógica de esquema
6. **SQLite-aware** — usar `op.batch_alter_table()` para operações ALTER TABLE (limitação do SQLite)

## Notas de Desenvolvimento

- Sempre execute `alembic upgrade head` após baixar novas mudanças que incluem migrações
- Nunca delete ou reordene arquivos de migração em `versions/`
- O arquivo `alembic.ini` na raiz do projeto configura a URL do banco e logging
- SQLite não suporta nativamente todas as operações ALTER TABLE — o modo batch do Alembic lida com isso
- Após criar uma nova migração, verifique com `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`
- O `DatabaseGovernor` em `Programma_CS2_RENAN/backend/control/db_governor.py` executa auditorias periódicas de integridade (`PRAGMA quick_check`) nos bancos de dados ativos
- `env.py` importa explicitamente 19 classes SQLModel de `db_models.py` (que define 25 modelos `table=True`) para detecção autogenerate — adicionar uma tabela significa adicionar seu import lá

## Problemas Comuns

| Problema | Causa | Solução |
|----------|-------|---------|
| "Target database is not up to date" | Migrações pendentes | Executar `alembic upgrade head` |
| "Can't locate revision" | Tabela `alembic_version` corrompida | Verificar `alembic current`, corrigir manualmente |
| "No changes detected" | Mudanças no modelo não importadas | Verificar imports de `db_models.py` no `env.py` |
| Erros de batch mode | Falta de `render_as_batch=True` | Adicionar ao `context.configure()` no `env.py` |
