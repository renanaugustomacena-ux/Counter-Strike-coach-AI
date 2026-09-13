"""Guides round (WP2) — the shipped guides describe the program that exists.

The old guides told users they MUST link a Steam ID and a FACEIT ID for
identity (nothing uses them for that), pointed at a Kivy ``main.py``, a
Playwright "Fix Dependencies" button and ``gemma3`` — none of which exist.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[1] / "data" / "docs"
TOPICS = ("getting_started", "features", "troubleshooting")
LANGS = ("it", "pt")
FORBIDDEN = (
    "FACEIT ID",
    "FaceIT ID",
    "MUST link",
    "main.py",
    "Kivy",
    "Playwright",
    "Fix Dependencies",
    "gemma3",
    "Test Path",
)


def _every_doc():
    for topic in TOPICS:
        yield DOCS / f"{topic}.md"
        for lang in LANGS:
            yield DOCS / lang / f"{topic}.md"


def _doc_id(path: Path) -> str:
    return f"{path.parent.name}/{path.name}"


def test_every_topic_exists_in_english_italian_and_portuguese():
    for path in _every_doc():
        assert path.is_file(), path


@pytest.mark.parametrize("path", list(_every_doc()), ids=_doc_id)
def test_docs_do_not_describe_features_that_do_not_exist(path):
    text = path.read_text(encoding="utf-8")
    for phrase in FORBIDDEN:
        assert phrase not in text, f"{path.name}: {phrase!r}"


@pytest.mark.parametrize("path", list(_every_doc()), ids=_doc_id)
def test_each_doc_starts_with_a_title_and_uses_sections(path):
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines and lines[0].startswith("# "), path
    assert any(ln.startswith("## ") for ln in lines), path


@pytest.mark.parametrize("topic", TOPICS)
def test_localized_docs_mirror_the_english_section_count(topic):
    def sections(path: Path) -> int:
        text = path.read_text(encoding="utf-8")
        return sum(1 for ln in text.splitlines() if ln.startswith("## "))

    english = sections(DOCS / f"{topic}.md")
    for lang in LANGS:
        assert sections(DOCS / lang / f"{topic}.md") == english, f"{lang}/{topic}"


def test_getting_started_names_the_nickname_as_the_identity():
    text = (DOCS / "getting_started.md").read_text(encoding="utf-8").lower()
    assert "in-game name" in text or "nickname" in text
    assert "steam id" not in text.split("## ")[1] if "## " in text else True
