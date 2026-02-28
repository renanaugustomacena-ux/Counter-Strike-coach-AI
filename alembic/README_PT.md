> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Sistema de Migração de Banco de Dados (Alembic)

Sistema de migração de banco de dados usando Alembic para gerenciar a evolução do esquema SQLite.

## Visão Geral

Este diretório contém migrações Alembic para o banco de dados Macena CS2 Analyzer (`database.db`). Todas as mudanças de esquema devem passar por migrações — nenhum DDL manual em produção.

## Arquivos de Migração

O diretório `versions/` contém 13 arquivos de migração cobrindo:

- Campos de perfil e preferências do usuário
- Alinhamento de esquema com modelos
- Estatísticas de jogadores profissionais
- Suporte a daemon (Hunter, Digester, Teacher)
- Telemetria e observabilidade
- Colunas do plano fusion (temporal baseline, limiares de role, estado de coaching)

## Arquivos Principais

- `env.py` — Configuração do ambiente Alembic (conexão com banco SQLite em modo WAL)
- `alembic.ini` — Configuração Alembic (URL do banco, logging)
- `versions/` — Histórico de migrações (sequencial, imutável)

## Princípios de Migração

- **Idempotente** — Migrações podem ser executadas múltiplas vezes com segurança
- **Reversível** — Todas as migrações têm caminhos de upgrade e downgrade
- **Versionado** — Migrações são commitadas no git
- **Testado** — Migrações testadas em dados semelhantes a produção antes do deployment

## Uso

```bash
# Verificar status de migração atual
alembic current

# Atualizar para versão mais recente
alembic upgrade head

# Downgrade de uma revisão
alembic downgrade -1

# Gerar nova migração
alembic revision --autogenerate -m "descrição"
```

## Notas

- Banco de dados usa modo SQLite WAL para acesso concorrente
- Todas as migrações devem passar validação headless antes do commit
- Nunca pular migrações ou forçar mudanças de esquema
