"""MarkdownArticle — token-styled rich-text renderer for the in-app guides.

The Help screen used to drop two of its three guides into a plain ``QLabel``
with ``#``, ``**`` and code fences visible. This widget converts the small
markdown subset the guides use (ATX headings, paragraphs, nested bullet and
numbered lists, fenced and inline code, blockquotes, bold, italic, links)
into Qt rich text and styles it from the live design tokens — no hardcoded
hex, no QGraphicsEffect, re-styled on every theme switch.

The converter is deliberately in-house: the ``markdown`` package on the dev
machine is not a shipped dependency, and ``QTextDocument.setMarkdown`` does
not honour ``setDefaultStyleSheet`` the way HTML does.
"""

from __future__ import annotations

import html
import math
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy, QTextBrowser

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import get_theme_relay
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

_MONO = "'JetBrains Mono', 'Fira Code', Consolas, monospace"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_EM_RE = re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def build_article_css(tokens) -> str:
    """Qt rich-text stylesheet for the article body, every value a token."""
    return "\n".join(
        [
            f"h1 {{ color: {tokens.text_primary}; font-size: {tokens.font_size_h1}px; "
            f"font-weight: 700; margin-top: 0px; margin-bottom: {tokens.spacing_sm}px; }}",
            f"h2 {{ color: {tokens.text_primary}; font-size: {tokens.font_size_title}px; "
            f"font-weight: 700; margin-top: {tokens.spacing_lg}px; "
            f"margin-bottom: {tokens.spacing_xs}px; }}",
            f"h3 {{ color: {tokens.accent_primary}; font-size: {tokens.font_size_subtitle}px; "
            f"font-weight: 700; margin-top: {tokens.spacing_md}px; "
            f"margin-bottom: {tokens.spacing_xs}px; }}",
            f"p {{ color: {tokens.text_secondary}; font-size: {tokens.font_size_body}px; "
            f"margin-top: {tokens.spacing_xs}px; margin-bottom: {tokens.spacing_sm}px; }}",
            f"li {{ color: {tokens.text_secondary}; font-size: {tokens.font_size_body}px; "
            f"margin-bottom: 2px; }}",
            f"strong {{ color: {tokens.text_primary}; font-weight: 700; }}",
            f"em {{ color: {tokens.text_secondary}; font-style: italic; }}",
            f"code {{ font-family: {_MONO}; color: {tokens.accent_primary}; "
            f"background-color: {tokens.surface_sunken}; }}",
            f"pre {{ font-family: {_MONO}; color: {tokens.text_primary}; "
            f"background-color: {tokens.surface_sunken}; font-size: {tokens.font_size_body}px; "
            f"margin-top: {tokens.spacing_sm}px; margin-bottom: {tokens.spacing_sm}px; }}",
            f"blockquote {{ color: {tokens.text_tertiary}; font-style: italic; "
            f"margin-left: {tokens.spacing_lg}px; }}",
            f"a {{ color: {tokens.info}; text-decoration: none; }}",
        ]
    )


def _inline(text: str) -> str:
    """Escape, then bold / italic / code / links. Code spans stay literal."""
    escaped = html.escape(text, quote=False)
    spans: list[str] = []

    def _hold(match: re.Match) -> str:
        spans.append(f"<code>{match.group(1)}</code>")
        return f"\x00{len(spans) - 1}\x00"

    escaped = _CODE_SPAN_RE.sub(_hold, escaped)
    escaped = _LINK_RE.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', escaped)
    escaped = _BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    escaped = _EM_RE.sub(r"<em>\1</em>", escaped)
    for index, span in enumerate(spans):
        escaped = escaped.replace(f"\x00{index}\x00", span)
    return escaped


def render_markdown_html(markdown: str) -> str:
    """Convert the guides' markdown subset to Qt-friendly HTML."""
    out: list[str] = []
    paragraph: list[str] = []
    lists: list[tuple[int, str]] = []  # (indent, "ul" | "ol")
    code: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{_inline(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_lists(down_to: int = -1) -> None:
        while lists and lists[-1][0] > down_to:
            out.append(f"</{lists.pop()[1]}>")

    for raw in (markdown or "").splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if in_code:
            if stripped.startswith("```"):
                out.append("<pre>" + html.escape("\n".join(code), quote=False) + "</pre>")
                code.clear()
                in_code = False
            else:
                code.append(raw.rstrip("\n"))
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            close_lists()
            in_code = True
            continue

        if not stripped:
            flush_paragraph()
            close_lists()
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            flush_paragraph()
            close_lists()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            close_lists()
            out.append(f"<blockquote>{_inline(stripped.lstrip('> '))}</blockquote>")
            continue

        item = _LIST_RE.match(line)
        if item:
            flush_paragraph()
            indent = len(item.group(1).replace("\t", "    "))
            kind = "ol" if item.group(2)[0].isdigit() else "ul"
            if lists and indent < lists[-1][0]:
                close_lists(indent)
            if lists and lists[-1][0] == indent and lists[-1][1] != kind:
                out.append(f"</{lists.pop()[1]}>")
            if not lists or indent > lists[-1][0]:
                lists.append((indent, kind))
                out.append(f"<{kind}>")
            out.append(f"<li>{_inline(item.group(3))}</li>")
            continue

        if lists and line.startswith((" ", "\t")):
            # Wrapped continuation of the previous list item.
            out[-1] = out[-1][: -len("</li>")] + " " + _inline(stripped) + "</li>"
            continue

        if lists:
            close_lists()
        paragraph.append(stripped)

    if in_code and code:
        out.append("<pre>" + html.escape("\n".join(code), quote=False) + "</pre>")
    flush_paragraph()
    close_lists()
    return "\n".join(out)


class MarkdownArticle(QTextBrowser):
    """Read-only article body that grows to its content and follows the theme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("markdown_article")
        self._markdown = ""
        self._fitting = False
        self.setReadOnly(True)
        self.setOpenExternalLinks(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.viewport().setAutoFillBackground(False)
        # Structural only — every colour lives in the document stylesheet.
        self.setStyleSheet(
            "QTextBrowser#markdown_article { background: transparent; border: none; }"
        )
        self.setFont(Typography.font("body"))
        self.document().setDocumentMargin(0)
        self.document().documentLayout().documentSizeChanged.connect(self._fit_height)
        get_theme_relay().theme_changed.connect(self.apply_tokens)
        self.apply_tokens()

    @property
    def markdown_text(self) -> str:
        return self._markdown

    def set_markdown(self, text: str) -> None:
        self._markdown = text or ""
        self._render()

    def apply_tokens(self, *_args) -> None:
        """Rebuild the stylesheet from the live tokens and re-render."""
        self.document().setDefaultStyleSheet(build_article_css(get_tokens()))
        self._render()

    # ── internals ──

    def _render(self) -> None:
        self.setHtml(render_markdown_html(self._markdown))
        self._fit_height()

    def _fit_height(self, *_args) -> None:
        if self._fitting:
            return
        self._fitting = True
        try:
            height = int(math.ceil(self.document().size().height())) + 2 * self.frameWidth() + 2
            self.setFixedHeight(max(height, 1))
        finally:
            self._fitting = False
