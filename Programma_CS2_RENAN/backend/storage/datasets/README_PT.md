# `backend/storage/datasets/` — Namespace reservado

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** `Programma_CS2_RENAN/backend/storage/datasets/`
> **Status:** Reservado — atualmente vazio, mantido como pacote Python.

## Por que isto existe

Este pacote é um namespace reservado para **wrappers de dataset** que apresentam múltiplos bancos SQLite por partida como uma interface unificada e amigável a iteradores para treinamento de ML. No HEAD atual ele contém apenas `__init__.py` — os wrappers ainda não chegaram.

O caminho atual de acesso a dados para treinamento passa diretamente por:

- `backend/storage/match_data_manager.py` — `MatchDataManager` (arquivos de DB por partida)
- `backend/storage/database.py` — `DatabaseManager` (monólito `database.db`)

Abstrações futuras de dataset (por exemplo, um `RAPTickDataset` que envolve consultas a `MatchTickState` com batching, sharding e cache para `torch.utils.data.DataLoader`) viverão aqui.

## Inventário de arquivos

| Arquivo | Finalidade |
|---------|------------|
| `__init__.py` | Marcador de pacote (vazio). |

## Quando adicionar código aqui

Adicione um módulo aqui quando:

- Você precisar de um wrapper `Dataset` / `IterableDataset` ao redor de shards SQLite por partida.
- O wrapper for grande o suficiente para merecer arquivo próprio (não deixe `match_data_manager.py` crescer indefinidamente).
- A abstração for genérica entre múltiplos consumidores (treinamento, avaliação, detecção de drift).

Mantenha a lógica de storage manager — pools de engine, PRAGMAs de conexão, migrations de schema — dentro do próprio `match_data_manager.py`.

## Não faça

- Não coloque pesos de modelos de ML aqui (esses vão para `Programma_CS2_RENAN/models/`).
- Não duplique helpers de query de `match_data_manager.py`.
- Não quebre o contrato do pacote — `__init__.py` deve permanecer importável mesmo quando vazio.

## Relacionados

- Match data manager: `backend/storage/match_data_manager.py`
- Visão geral da camada de storage: `backend/storage/README.md`
- Busca de dados de treinamento: `backend/nn/training_orchestrator.py:_fetch_batches()`
