> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Scaffold de Migracao Legado

Este diretorio contem um **scaffold Alembic legado** de uma primeira iteracao da camada de persistencia de dados. E mantido apenas como referencia historica — a cadeia de migracoes **ativa** para a aplicacao vive no diretorio `alembic/` na raiz do repo (19 revisoes, configurada pelo `alembic.ini` na raiz).

## Visao Geral Tecnica

O scaffold utiliza SQLAlchemy/SQLModel como camada ORM e Alembic para evolucao do schema, espelhando a abordagem que o projeto ainda utiliza hoje. Contem as duas primeiras revisoes de schema ja escritas para a camada de estatisticas de match; o desenvolvimento posterior reiniciou a cadeia na raiz do repo, onde todas as revisoes subsequentes vivem.

## Componentes Principais

### Migracoes Alembic
O subdiretorio **`migrations/`** contem o scaffold:
- **`env.py`**: O ponto de entrada do ambiente Alembic (importa todos os modelos de `Programma_CS2_RENAN.backend.storage.db_models` e aponta para `SQLModel.metadata`).
- **`script.py.mako`**: Um arquivo de template usado pelo Alembic para gerar novos scripts de migracao.
- **`README`**: Um aviso de deprecacao (R2-01) que marca esta cadeia como legada e aponta para o diretorio `alembic/` na raiz.
- **`versions/`**: Os dois scripts de migracao iniciais.
    - **`b609a11e13cc_baseline_schema.py`**: Estabelece as tabelas iniciais (`matchresult`, `mapveto`) e estende `proplayerstatcard`.
    - **`5d5764ef9f26_add_rating_components.py`**: Adiciona as colunas de componentes do Rating 2.0 (kpr, dpr, ...) a `playermatchstats`.

## Estrutura do Diretorio

```text
backend/storage/
├── migrations/             # Scaffold Alembic legado
│   ├── env.py              # Configuracao do ambiente
│   ├── script.py.mako      # Template de script de migracao
│   ├── README              # Aviso de deprecacao R2-01
│   └── versions/           # Duas revisoes de schema iniciais
├── README.md               # Documentacao em ingles
├── README_IT.md            # Versao em italiano
└── README_PT.md            # Esta documentacao
```

## Uso

**Nao** execute migracoes a partir deste diretorio — nao ha um `alembic.ini` aqui, e a cadeia esta superada. Todos os comandos de migracao sao executados a partir da raiz do projeto contra o diretorio `alembic/` na raiz:

### Aplicando Migracoes
```bash
alembic upgrade head
```

### Criando uma Nova Migracao
Quando as classes SQLModel em `Programma_CS2_RENAN/backend/storage/db_models.py` forem atualizadas:
```bash
alembic revision --autogenerate -m "descricao das mudancas"
```

### Rollbacks
```bash
alembic downgrade -1
```

A URL do banco de dados e configurada no `alembic.ini` na raiz (monolito SQLite `Programma_CS2_RENAN/backend/storage/database.db`); a variavel de ambiente `CS2_ALEMBIC_URL` pode sobrescreve-la para bancos de dados de verificacao temporarios. Consulte `alembic/README.md` na raiz do repo para o historico completo das migracoes.
