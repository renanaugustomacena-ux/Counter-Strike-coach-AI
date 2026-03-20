> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge Base — Sistema de Ajuda In-App

> **Autoridade:** Regra 3 (Frontend & UX)

Este modulo fornece um sistema de documentacao in-app leve para conteudo de ajuda voltado ao usuario. Totalmente separado do sistema de conhecimento RAG/COPER em `backend/knowledge/`.

## Distincao

| Modulo | Finalidade | Tecnologia |
|--------|-----------|------------|
| `knowledge/` | Conhecimento RAG para coaching + Experience Bank + busca vetorial | SBERT embeddings, FAISS, SQLite |
| `knowledge_base/` | Documentacao de ajuda in-app (este modulo) | Arquivos Markdown, busca textual |

## Arquivo: help_system.py (~80 linhas)

Classe HelpSystem — singleton lazy:
- get_all_topics() → lista de topicos de ajuda
- get_topic(id) → topico individual
- search_topics(keyword) → resultados filtrados

Fonte de dados: arquivos Markdown de `data/docs/` (getting_started.md, features.md, troubleshooting.md)

## Comportamentos Principais

- Inicializacao lazy, armazenada em cache apos a primeira chamada
- ID do topico = nome do arquivo sem extensao .md
- Busca textual: correspondencia de substring case-insensitive
- Somente leitura: nunca escreve em disco

## Notas de Desenvolvimento

- Para adicionar um novo topico de ajuda: crie um arquivo .md em `data/docs/`
- Mantenha o conteudo de ajuda conciso e focado no usuario
