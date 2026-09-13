"""Guides round (WP2) — markdown renders as styled rich text, never as raw markers.

Two of the three in-app guides were dumped into a plain ``QLabel`` with
``#``, ``**`` and fences visible. ``MarkdownArticle`` converts the small
markdown subset the guides use into Qt rich text styled from the design
tokens (no hardcoded hex, no QGraphicsEffect).
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

MD = """# Title

Intro with **bold**, *em* and `code`.

## Section

- one
- two
    - nested

1. first
2. second

```bash
python -m x
```

> note

[link](https://example.com)
"""


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_render_markdown_html_covers_the_docs_subset():
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.markdown_article import (
        render_markdown_html,
    )

    html = render_markdown_html(MD)
    for fragment in (
        "<h1>Title</h1>",
        "<h2>Section</h2>",
        "<strong>bold</strong>",
        "<em>em</em>",
        "<code>code</code>",
        "<li>one</li>",
        "<li>first</li>",
        "python -m x",
        "<blockquote>",
        'href="https://example.com"',
    ):
        assert fragment in html, fragment
    assert html.count("<ul>") == 2, "the 4-space bullet is a nested list"
    assert "<ol>" in html and "<pre" in html


def test_render_escapes_html_and_keeps_code_literal():
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.markdown_article import (
        render_markdown_html,
    )

    html = render_markdown_html("a < b & c > d\n\n`<tag>` and **x**")
    assert "&lt; b &amp; c &gt;" in html
    assert "<tag>" not in html and "&lt;tag&gt;" in html
    assert "<strong>x</strong>" in html


def test_widget_renders_without_raw_markers(qapp):
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.markdown_article import MarkdownArticle

    article = MarkdownArticle()
    article.set_markdown(MD)
    plain = article.toPlainText()
    assert "Title" in plain and "nested" in plain and "python -m x" in plain
    for marker in ("#", "**", "`", "> note", "[link]"):
        assert marker not in plain, marker
    assert "Title" in article.document().toHtml()


def test_widget_height_follows_the_document(qapp):
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.markdown_article import MarkdownArticle

    short = MarkdownArticle()
    short.setFixedWidth(600)
    short.show()
    short.set_markdown("# One line")
    qapp.processEvents()

    long = MarkdownArticle()
    long.setFixedWidth(600)
    long.show()
    long.set_markdown("\n\n".join(f"## Heading {i}\n\nparagraph {i}" for i in range(12)))
    qapp.processEvents()

    assert short.height() > 10
    assert long.height() > short.height() * 4
    assert long.verticalScrollBar().maximum() == 0, "the article never scrolls itself"


def test_css_is_built_from_design_tokens():
    from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
    from Programma_CS2_RENAN.apps.qt_app.widgets.components.markdown_article import (
        build_article_css,
    )

    tokens = get_tokens()
    css = build_article_css(tokens)
    assert tokens.text_primary in css
    assert tokens.accent_primary in css
    assert tokens.surface_sunken in css
    assert "JetBrains Mono" in css
    assert f"{tokens.font_size_h1}px" in css and f"{tokens.font_size_body}px" in css
