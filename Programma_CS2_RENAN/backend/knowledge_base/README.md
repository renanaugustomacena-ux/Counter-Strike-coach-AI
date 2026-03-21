> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Knowledge Base — In-App Help System

> **Authority:** Rule 3 (Frontend & UX)

## Introduction

The `knowledge_base` module provides a lightweight, read-only in-app documentation
system that serves user-facing help content inside the Macena CS2 Analyzer. It reads
Markdown files from the `data/docs/` resource directory, indexes them by filename,
and exposes a simple text-search API that the UI layers consume.

This module is **entirely separate** from the RAG/COPER knowledge system located in
`backend/knowledge/`. The two modules share no code, no data, and no runtime state.
Their names are similar but their responsibilities are disjoint:

| Module | Purpose | Technology |
|--------|---------|------------|
| `backend/knowledge/` | RAG coaching knowledge + Experience Bank + vector search | SBERT embeddings, FAISS, SQLite |
| `backend/knowledge_base/` | **In-app help documentation** (this module) | Markdown files, substring text search |

## File Inventory

| File | Lines | Purpose | Key Exports |
|------|-------|---------|-------------|
| `__init__.py` | 1 | Package marker | — |
| `help_system.py` | ~83 | Markdown documentation lookup, indexing, and search | `HelpSystem`, `get_help_system()` |

## Architecture & Concepts

### HelpSystem Class

`HelpSystem` is the sole class in this module. It performs three responsibilities:

1. **Index construction** — On instantiation (or when `refresh_index()` is called),
   it scans the docs directory, reads every `.md` file, extracts the first `# ` heading
   as the topic title, and stores the full content in an in-memory dictionary keyed by
   the filename stem (e.g., `getting_started.md` becomes topic ID `getting_started`).

2. **Topic retrieval** — `get_topic(topic_id)` returns a single topic dict with keys
   `title`, `content`, and `path`. `get_all_topics()` returns a list of all indexed
   topics for populating the sidebar menu.

3. **Text search** — `search_topics(query)` performs case-insensitive substring matching
   across both titles and content. Title matches receive a score of 10; content matches
   receive a score of 1. Results are returned sorted by descending relevance score.

### Singleton Pattern (C-54)

The module follows the **lazy singleton** pattern identified as C-54 in the codebase:

```python
# No file I/O at import time
_help_system = None

def get_help_system() -> HelpSystem:
    global _help_system
    if _help_system is None:
        _help_system = HelpSystem()
    return _help_system
```

This avoids disk reads during module import, which is critical because the help system
module may be imported by screens that are never actually visited during a session.

### Data Source: `data/docs/`

The Markdown files live under the `Programma_CS2_RENAN/data/docs/` resource directory,
resolved at runtime via `get_resource_path("data/docs")` from `core/config.py`. This
resolution is PyInstaller-aware: when running from a frozen bundle, it reads from the
`_MEIPASS` temporary extraction folder instead of the source tree.

Current documentation topics:

| File | Topic | Content Summary |
|------|-------|-----------------|
| `getting_started.md` | Getting Started | Setup wizard, demo paths, Steam/FACEIT linking, 10/10 rule, ingestion modes |
| `features.md` | Feature Guide | Dashboard, Skill Radar, RAP AI Coach, Tactical Viewer, Advanced Analytics |
| `troubleshooting.md` | Troubleshooting | Neural stall fixes, demo detection, UI launch issues, performance tuning |

### Fallback Topics

Both the Qt and Kivy help screens define hardcoded `_FALLBACK_TOPICS` lists that are
used when `help_system.py` fails to import or when `get_help_system()` raises an
exception. The fallback topics cover: Getting Started, Demo Analysis, AI Coach,
Steam Integration, Navigation, and Troubleshooting. This ensures the help screen
is never completely empty, even in degraded environments.

### Search Scoring

The search algorithm is intentionally simple (no stemming, no fuzzy matching, no
tokenization). Scores are assigned as follows:

| Match Location | Score |
|----------------|-------|
| Title contains query substring | +10 |
| Content contains query substring | +1 |

Results are sorted by total score descending. A topic that matches in both title and
content receives a combined score of 11.

## Integration

### Qt Help Screen (`apps/qt_app/screens/help_screen.py`)

The primary UI consumer. Implements a two-panel layout:

- **Left panel** (240px fixed): Search input (`QLineEdit`) + topic list (`QListWidget`)
- **Right panel** (flexible): Scrollable content viewer (`QLabel` inside `QScrollArea`)

The screen imports `get_help_system` with a try/except guard and sets
`_HELP_AVAILABLE = True/False`. On `on_enter()`, it attempts to load topics from the
help system and falls back to `_FALLBACK_TOPICS` on failure. Search is performed
client-side by filtering the already-loaded topic list.

### Kivy Help Screen (`apps/desktop_app/help_screen.py`)

The legacy Kivy consumer. Uses `MDScreen` with `MDListItem` widgets for the topic
sidebar and an `MDLabel` for content display. It follows the same import-guard and
fallback pattern as the Qt screen, but populates an empty list instead of fallback
topics when the help system is unavailable.

### Adding New Help Topics

To add a new documentation topic to the in-app help:

1. Create a new `.md` file in `Programma_CS2_RENAN/data/docs/` (e.g., `economy_tips.md`)
2. Start the file with a `# Title` heading — this becomes the topic title in the sidebar
3. Write the content in standard Markdown (the viewer renders plain text, not rich HTML)
4. Call `get_help_system().refresh_index()` if the app is already running, or restart

No code changes are required. The index is rebuilt dynamically from the filesystem.

## Development Notes

- **Thread safety:** `HelpSystem` is not thread-safe. It is designed for single-threaded
  UI access only. Both the Qt and Kivy screens call it from the main/UI thread.
- **No write operations:** The help system never modifies files on disk. It is strictly
  a read-only indexer.
- **Encoding:** All files are read as UTF-8 (`encoding="utf-8"`).
- **Error handling:** Individual file read failures are caught and printed to stderr
  (`print()`). This should be migrated to structured logging in a future pass.
- **Cache invalidation:** The cache is only rebuilt when `refresh_index()` is called
  explicitly. There is no file-watcher or auto-refresh mechanism.
- **Content rendering:** The Qt help screen displays content as plain text via
  `QLabel.setText()`. Markdown formatting (headers, lists, links) is not rendered —
  content appears as-is. A future enhancement could use `QTextBrowser` with
  `setMarkdown()` for rich rendering.
- **Search limitations:** Substring matching means searching for "demo" will match
  "demonstration" and "demographics". There is no word-boundary awareness.
- **PyInstaller compatibility:** The docs directory is resolved through
  `get_resource_path()`, ensuring it works both in development and in frozen builds.
  The `data/docs/` directory must be included in the PyInstaller spec file's `datas`
  list for the help system to function in distributed builds.
