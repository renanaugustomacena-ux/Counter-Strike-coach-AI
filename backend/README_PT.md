# `backend/` (nível superior) — área de staging do storage

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Layout do filesystem no nível do repo
> **Status:** Área de staging; o pacote backend de fato vive em `Programma_CS2_RENAN/backend/`.

## Por que este diretório existe

`./backend/` (este diretório, na raiz do repo) **não** é o pacote backend da aplicação. É uma pequena área de staging do filesystem que armazena arquivos que precisam viver fora da árvore do pacote Python mas logicamente pertencem ao domínio backend — tipicamente shards SQLite por-partida e outros artefatos gerados de grande porte que não devem ser commitados sob `Programma_CS2_RENAN/`.

O código backend de fato — serviços, treinamento NN, ingestão, gerenciadores de storage, base de conhecimento, pipelines de processamento — vive em:

> `Programma_CS2_RENAN/backend/` ([README](../Programma_CS2_RENAN/backend/README.md))

Esse sub-pacote contém 14 módulos de domínio (`analysis/`, `coaching/`, `control/`, `data_sources/`, `ingestion/`, `knowledge/`, `knowledge_base/`, `nn/`, `onboarding/`, `processing/`, `progress/`, `reporting/`, `services/`, `storage/`).

## O que vive aqui

```
backend/
└── storage/          # Artefatos de runtime gerados (SQLite por-partida, backups)
```

`backend/storage/` é a raiz de dados em tempo de execução usada pelo `MatchDataManager` quando `PRO_DEMO_PATH` não está configurado ou indisponível. Os arquivos `match_{id}.db` por-partida pousam aqui e se acumulam ao longo do tempo. A limpeza é tratada por `Programma_CS2_RENAN/backend/storage/maintenance.py` e pela política de retenção do `BackupManager`.

## Não faça

- **Não** adicione arquivos-fonte Python aqui. Código backend novo vai em `Programma_CS2_RENAN/backend/<dominio>/`.
- **Não** trate isto como caminho de import. `from backend.foo import ...` não resolverá — a raiz do pacote é `Programma_CS2_RENAN`.
- **Não** commite o conteúdo de `backend/storage/`. Os arquivos `*.db` gerados estão no gitignore.

## Documentação relacionada

- Pacote backend da aplicação: `Programma_CS2_RENAN/backend/README.md`
- Especificidades da camada de storage: `Programma_CS2_RENAN/backend/storage/README.md`
- Arquitetura tri-database: `CLAUDE.md` e `REFERENCE.md`
