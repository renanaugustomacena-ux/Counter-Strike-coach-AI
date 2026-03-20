# Knowledge Base — In-App Help System

> **Authority:** Rule 3 (Frontend & UX)

This module provides a lightweight in-app documentation system for user-facing help content. It is entirely separate from the RAG/COPER knowledge system in `backend/knowledge/`.

## Distinction from `backend/knowledge/`

| Module | Purpose | Technology |
|--------|---------|------------|
| `knowledge/` | RAG coaching knowledge + Experience Bank + vector search | SBERT embeddings, FAISS, SQLite |
| `knowledge_base/` | **In-app help documentation** (this module) | Markdown files, text search |

## File Inventory

| File | Lines | Purpose | Key Classes |
|------|-------|---------|-------------|
| `help_system.py` | ~80 | Markdown documentation lookup | `HelpSystem` |

## `HelpSystem` — How It Works

```python
# Lazy singleton access (C-54 pattern: no I/O at import time)
help_sys = get_help_system()

# Get all available topics
topics = help_sys.get_all_topics()
# → [{"id": "getting_started", "title": "Getting Started", "content": "..."}, ...]

# Get a specific topic
topic = help_sys.get_topic("getting_started")

# Search topics by keyword
results = help_sys.search_topics("demo")
```

### Data Source

Reads Markdown files from `Programma_CS2_RENAN/data/docs/`:

| File | Topic |
|------|-------|
| `getting_started.md` | Initial setup, demo folders, Steam/FaceIT linking, 10/10 rule |
| `features.md` | Coaching features and analytics capabilities |
| `troubleshooting.md` | Common issues and solutions |

### Key Behaviors

- **Lazy initialization:** First call to `get_help_system()` reads files; subsequent calls return cached instance
- **Index by filename:** Topic ID = filename without `.md` extension
- **Text search:** Simple substring matching across title + content
- **Read-only:** Never writes to disk

## Integration

- `apps/qt_app/screens/help_screen.py` — Two-pane help browser with topic list and content viewer
- `apps/desktop_app/help_screen.py` — Kivy help screen (legacy)

## Development Notes

- To add a new help topic: create a `.md` file in `data/docs/` and call `help_sys.refresh_index()`
- Topic titles are derived from the first `#` heading in each Markdown file
- Search is case-insensitive substring matching — no stemming or fuzzy matching
- Keep help content concise and user-focused — this is not developer documentation
