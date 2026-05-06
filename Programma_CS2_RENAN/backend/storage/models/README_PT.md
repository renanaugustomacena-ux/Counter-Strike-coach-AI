# `backend/storage/models/` — Namespace reservado

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/storage/models/`
> **Status:** Reservado — atualmente vazio, mantido como pacote Python.

## Por que isto existe

Namespace reservado para **classes de dados específicas da camada de storage**: coisas como helpers de mapeamento de linhas, DTOs leves que mediam entre linhas do ORM SQLModel e consumidores downstream, ou tipos de resultado de query builders.

Este **não** é o lugar para as definições de tabelas do ORM SQLModel — essas vivem em `backend/storage/db_models.py`. Colocá-las aqui criaria uma confusa fonte-dupla-de-verdade para o modelo de dados.

## Inventário de arquivos

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote (vazio). |

## Quando adicionar código aqui

Adicione um módulo aqui quando:

- Você tem um DTO do lado de storage que não mapeia 1:1 com uma tabela de banco (por exemplo, um resultado de query achatado, uma projeção de join).
- O DTO é consumido por múltiplos módulos e merece um único lar.
- Você *não* está definindo uma nova tabela do ORM — essas vão em `db_models.py`.

## Fronteiras (mantenha limpas)

| Preocupação | Vive em |
|-------------|---------|
| Classes de tabela ORM (`SQLModel.table=True`) | `backend/storage/db_models.py` |
| Manager singletons (`get_db_manager()`, etc.) | `backend/storage/database.py` |
| Pool de engine SQLite por partida | `backend/storage/match_data_manager.py` |
| DTOs e tipos de resultado do lado de storage | `backend/storage/models/` (este diretório) |

## Não faça

- Não adicione novas classes de tabela ORM aqui. Elas devem ficar em `db_models.py`.
- Não importe deste pacote eagerly — pacotes vazios não devem aparecer na API pública.
- Não coloque checkpoints de modelos de machine learning aqui. Esses vivem em `Programma_CS2_RENAN/models/`.

## Relacionados

- Definições do ORM: `backend/storage/db_models.py`
- Visão geral da camada de storage: `backend/storage/README.md`
