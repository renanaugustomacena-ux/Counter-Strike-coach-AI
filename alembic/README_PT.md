> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Sistema de Migração de Banco de Dados (Alembic)

> **Autoridade:** Regra 5 (Persistência de Dados), Regra 6 (Governança de Mudanças)
> **Skill:** `/db-review`

Sistema de migração de banco de dados usando Alembic para gerenciar a evolução do esquema SQLite no Macena CS2 Analyzer. Todas as mudanças de esquema no banco de dados monolítico (`database.db`) devem passar por migrações Alembic — nenhum DDL manual em produção.

## Estrutura do Diretório

```
alembic/
├── env.py                  # Configuração do ambiente Alembic
├── script.py.mako          # Template de script de migração
└── versions/               # Histórico de migrações (sequencial, imutável)
    ├── 19fcff36ea0a_...    # Telemetria heartbeat
    ├── 3c6ecb5fe20e_...    # Colunas do plano fusion
    ├── 57a72f0df21e_...    # Heartbeat nullable
    ├── 609fed4b4dce_...    # Rastreamento de tarefa de ingestão
    ├── 7a30a0ea024e_...    # Sincronização de esquema
    ├── 89850b6e0a49_...    # Estatísticas de jogadores profissionais
    ├── 8a93567a2798_...    # Vinculação de física pro
    ├── 8c443d3d9523_...    # Suporte a daemon triplo
    ├── a1b2c3d4e5f6_...    # Métricas de qualidade de dados
    ├── b2c3d4e5f6a7_...    # Enriquecimento de tick de jogador
    ├── c8a2308770e5_...    # Triggers de retreinamento
    ├── da7a6be5c0c7_...    # Notificações de serviço
    ├── e3013f662fd4_...    # Sincronização de estado de coaching
    └── f769fbe67229_...    # Completude de campos de perfil
```

## Histórico de Migrações (14 Revisões)

| Revisão | Descrição | Tabelas Afetadas |
|---------|-----------|------------------|
| `f769fbe67229` | Adição de campos de perfil faltantes | `UserProfile` |
| `e3013f662fd4` | Adição de sync e intervalo ao CoachState | `CoachState` |
| `da7a6be5c0c7` | Adição de tabela de notificações de serviço | `ServiceNotification` (nova) |
| `c8a2308770e5` | Suporte a trigger de retreinamento | `TrainingState` |
| `b2c3d4e5f6a7` | Colunas de enriquecimento em PlayerTickState | `PlayerTickState` |
| `a1b2c3d4e5f6` | Qualidade de dados em PlayerMatchStats | `PlayerMatchStats` |
| `8c443d3d9523` | Suporte a daemon triplo (Hunter/Digester/Teacher) | `DaemonState` (nova) |
| `8a93567a2798` | Vinculação de física pro às estatísticas | `ProPlayer`, `ProPlayerStatCard` |
| `89850b6e0a49` | Adição de estatísticas de jogadores profissionais | `ProPlayer` (nova), `ProPlayerStatCard` (nova) |
| `7a30a0ea024e` | Sincronização de tabelas faltantes | Múltiplas |
| `609fed4b4dce` | Adição de last_tick_processed à IngestionTask | `IngestionTask` |
| `57a72f0df21e` | Adição de heartbeat nullable ao CoachState | `CoachState` |
| `3c6ecb5fe20e` | Colunas do plano fusion (baseline temporal, limiares de role) | `CoachState` |
| `19fcff36ea0a` | Adição de telemetria heartbeat ao CoachState | `CoachState` |

## `env.py` — Configuração do Ambiente

O script de ambiente gerencia tanto o modo de migração offline quanto online:

- **Estabilização de caminhos** via `core.config.stabilize_paths()` — garante a resolução correta de `CORE_DB_DIR`
- **Import de modelos** — importa todas as classes SQLModel de `backend/storage/db_models.py` para autogenerate
- **Imposição do modo WAL** — toda conexão define `PRAGMA journal_mode=WAL` antes de executar migrações
- **URL do Banco** — resolvida de `core.config.DATABASE_URL` (sempre aponta para o monolítico `database.db`)

```python
# Configuração de conexão (simplificada)
connectable = create_engine(config.DATABASE_URL)
with connectable.connect() as connection:
    connection.execute(text("PRAGMA journal_mode=WAL"))
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

## Escopo e Limites

Alembic gerencia **apenas** o banco de dados monolítico (`database.db`). Os outros dois bancos na arquitetura tri-database são gerenciados separadamente:

| Banco de Dados | Gerenciador | Estratégia de Migração |
|----------------|-------------|----------------------|
| `database.db` (monolítico) | Alembic | Migrações versionadas sequenciais |
| `hltv_metadata.db` | `HLTVDatabaseManager` | Esquema criado no primeiro uso |
| `match_data/<id>.db` (por partida) | `MatchDataManager` | Esquema criado por demo ingerida |

## Uso

```bash
# Ativar o ambiente virtual primeiro
source /home/renan/.venvs/cs2analyzer/bin/activate

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

1. **Idempotente** — migrações usam `batch_alter_table` para compatibilidade SQLite e podem ser reexecutadas
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
- O `DatabaseGovernor` em `backend/control/db_governor.py` audita o estado das migrações a cada inicialização
- Todas as 61+ classes SQLModel em `db_models.py` são importadas pelo `env.py` para detecção do autogenerate

## Problemas Comuns

| Problema | Causa | Solução |
|----------|-------|---------|
| "Target database is not up to date" | Migrações pendentes | Executar `alembic upgrade head` |
| "Can't locate revision" | Tabela `alembic_version` corrompida | Verificar `alembic current`, corrigir manualmente |
| "No changes detected" | Mudanças no modelo não importadas | Verificar imports de `db_models.py` no `env.py` |
| Erros de batch mode | Falta de `render_as_batch=True` | Adicionar ao `context.configure()` no `env.py` |
