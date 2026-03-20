> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge Base — Sistema di Aiuto In-App

> **Autorità:** Regola 3 (Frontend & UX)

Questo modulo fornisce un sistema di documentazione in-app leggero per contenuti di aiuto rivolti all'utente. Completamente separato dal sistema di conoscenza RAG/COPER in `backend/knowledge/`.

## Distinzione

| Modulo | Scopo | Tecnologia |
|--------|-------|------------|
| `knowledge/` | Conoscenza RAG per coaching + Experience Bank + ricerca vettoriale | SBERT embeddings, FAISS, SQLite |
| `knowledge_base/` | Documentazione di aiuto in-app (questo modulo) | File Markdown, ricerca testuale |

## File: help_system.py (~80 righe)

Classe HelpSystem — singleton lazy:
- get_all_topics() → lista degli argomenti di aiuto
- get_topic(id) → singolo argomento
- search_topics(keyword) → risultati filtrati

Fonte dati: file Markdown da `data/docs/` (getting_started.md, features.md, troubleshooting.md)

## Comportamenti Chiave

- Inizializzazione lazy, memorizzata in cache dopo la prima chiamata
- ID argomento = nome file senza estensione .md
- Ricerca testuale: corrispondenza sottostringa case-insensitive
- Sola lettura: non scrive mai su disco

## Note di Sviluppo

- Per aggiungere un nuovo argomento di aiuto: creare un file .md in `data/docs/`
- Mantenere i contenuti di aiuto concisi e orientati all'utente
