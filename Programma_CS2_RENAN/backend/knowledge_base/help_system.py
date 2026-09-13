"""In-app knowledge base — the markdown guides under ``data/docs``.

Layout::

    data/docs/<topic>.md        English (the fallback for every language)
    data/docs/<lang>/<topic>.md localized copy (it, pt, ...)

A topic id is the file stem; its title is the first ``# `` heading. A
language sees its own copy of a topic when one exists and the English one
otherwise, so the topic set is identical in every language.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from Programma_CS2_RENAN.core.config import get_resource_path
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.help_system")

DEFAULT_LANGUAGE = "en"


def _read_topic(path: str, topic_id: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as exc:
        logger.warning("Help doc unreadable: %s (%s)", path, exc)
        return None
    title = topic_id.replace("_", " ").title()
    for line in raw.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    return {"title": title, "content": raw, "path": path}


class HelpSystem:
    """Reads the guides once per language and serves them by topic id."""

    def __init__(self, docs_dir: Optional[str] = None):
        self.docs_dir = docs_dir or get_resource_path(os.path.join("data", "docs"))
        self._by_lang: Dict[str, Dict[str, dict]] = {}
        self.refresh_index()

    def refresh_index(self) -> None:
        """Scan ``docs_dir`` (English) and every language sub-folder."""
        self._by_lang = {DEFAULT_LANGUAGE: {}}
        if not os.path.isdir(self.docs_dir):
            return
        for entry in sorted(os.listdir(self.docs_dir)):
            full = os.path.join(self.docs_dir, entry)
            if entry.endswith(".md") and os.path.isfile(full):
                topic = _read_topic(full, entry[:-3])
                if topic:
                    self._by_lang[DEFAULT_LANGUAGE][entry[:-3]] = topic
            elif os.path.isdir(full) and not entry.startswith("."):
                localized: Dict[str, dict] = {}
                for name in sorted(os.listdir(full)):
                    if name.endswith(".md"):
                        topic = _read_topic(os.path.join(full, name), name[:-3])
                        if topic:
                            localized[name[:-3]] = topic
                if localized:
                    self._by_lang[entry.lower()] = localized

    # ── lookup ──

    def available_languages(self) -> set:
        return set(self._by_lang)

    def _resolve(self, topic_id: str, lang: Optional[str]) -> Optional[dict]:
        code = (lang or DEFAULT_LANGUAGE).lower()
        localized = self._by_lang.get(code, {}).get(topic_id)
        return localized or self._by_lang.get(DEFAULT_LANGUAGE, {}).get(topic_id)

    def get_topic(self, topic_id: str, lang: Optional[str] = None) -> Optional[dict]:
        """Returns the topic dict for ``lang`` (English fallback) or None."""
        return self._resolve(topic_id, lang)

    def get_all_topics(self, lang: Optional[str] = None) -> List[dict]:
        """``[{id, title, content}]`` — the English topic set, localized where possible."""
        topics = []
        for topic_id in self._by_lang.get(DEFAULT_LANGUAGE, {}):
            data = self._resolve(topic_id, lang)
            if data:
                topics.append(
                    {"id": topic_id, "title": data["title"], "content": data.get("content", "")}
                )
        return topics

    def search_topics(self, query: str, lang: Optional[str] = None) -> List[dict]:
        """Simple text search across titles and content, most relevant first."""
        query = (query or "").lower()
        results = []
        for topic in self.get_all_topics(lang):
            score = 0
            if query in topic["title"].lower():
                score += 10
            if query in topic["content"].lower():
                score += 1
            if score > 0:
                results.append({"id": topic["id"], "title": topic["title"], "score": score})
        return sorted(results, key=lambda item: item["score"], reverse=True)


# Lazy singleton — avoids file I/O at import time (C-54)
_help_system = None


def get_help_system() -> HelpSystem:
    """Return the cached HelpSystem singleton (lazy-initialized)."""
    global _help_system
    if _help_system is None:
        _help_system = HelpSystem()
    return _help_system
