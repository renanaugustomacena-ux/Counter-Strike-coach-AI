# `backend/` (nivel superior) — area de staging do storage

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Layout do filesystem no nivel do repo
> **Status:** Area de staging; o pacote backend de fato vive em `Programma_CS2_RENAN/backend/`.

## Por que este diretorio existe

`./backend/` (este diretorio, na raiz do repo) **nao** e o pacote backend da aplicacao. E uma pequena area de staging do filesystem que espelha o layout do dominio backend fora da arvore do pacote Python — hoje contem apenas um scaffold Alembic legado sob `storage/`.

O codigo backend de fato — servicos, treinamento NN, ingestao, gerenciadores de storage, base de conhecimento, pipelines de processamento — vive em:

> `Programma_CS2_RENAN/backend/` ([README](../Programma_CS2_RENAN/backend/README.md))

Esse sub-pacote contem 14 modulos de dominio (`analysis/`, `coaching/`, `control/`, `data_sources/`, `ingestion/`, `knowledge/`, `knowledge_base/`, `nn/`, `onboarding/`, `processing/`, `progress/`, `reporting/`, `services/`, `storage/`).

## O que vive aqui

```
backend/
└── storage/
    └── migrations/   # Scaffold Alembic legado (2 revisoes iniciais) — NAO e a cadeia ativa
```

`backend/storage/` contem apenas um scaffold Alembic vestigial ([README](storage/README.md)). A cadeia de migracoes **ativa** vive no diretorio `alembic/` na raiz do repo (19 revisoes), configurada pelo `alembic.ini` na raiz. Os bancos de dados de runtime **nao** vivem aqui: o monolito `database.db` e `hltv_metadata.db` sao criados sob `Programma_CS2_RENAN/backend/storage/`, e os shards por-partida vao para `PRO_DEMO_PATH/match_data/` (com fallback para `Programma_CS2_RENAN/backend/storage/match_data/`).

## Nao faca

- **Nao** adicione arquivos-fonte Python aqui. Codigo backend novo vai em `Programma_CS2_RENAN/backend/<dominio>/`.
- **Nao** trate isto como caminho de import. `from backend.foo import ...` nao resolvera — a raiz do pacote e `Programma_CS2_RENAN`.
- **Nao** adicione novas migracoes aqui. Novas alteracoes de schema passam pela cadeia `alembic/versions/` na raiz.

## Documentacao relacionada

- Pacote backend da aplicacao: `Programma_CS2_RENAN/backend/README.md`
- Especificidades da camada de storage: `Programma_CS2_RENAN/backend/storage/README.md`
- Cadeia de migracoes ativa: `alembic/README.md` (raiz do repo)
- Arquitetura tri-database: `REFERENCE.md`
