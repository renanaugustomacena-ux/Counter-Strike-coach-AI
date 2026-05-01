"""HeroStatsStrip — horizontal row of "display-number + caption" stat blocks.

Used at the top of MatchDetail's Overview tab and similar contexts where
a few key numbers should anchor the page. Each block renders:

    1.34       <- display font, color = sentiment-driven
    RATING     <- caption, uppercase, letter-spaced

Sentiments: ``positive`` (success token), ``negative`` (error), ``neutral``
(text_primary), or ``accent`` (accent_primary).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

Sentiment = Literal["positive", "negative", "neutral", "accent"]


@dataclass(frozen=True)
class HeroStat:
    value: str
    label: str
    sentiment: Sentiment = "neutral"


class HeroStatsStrip(QWidget):
    """Renders a list of HeroStat dataclasses as a horizontal block row."""

    def __init__(
        self,
        stats: Iterable[HeroStat] = (),
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        tokens = get_tokens()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens.spacing_xxl)

        self._layout = layout
        self._stats: list[HeroStat] = []
        self.set_stats(list(stats))

    def set_stats(self, stats: list[HeroStat]) -> None:
        # Clear existing
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._stats = list(stats)

        for stat in self._stats:
            self._layout.addWidget(self._build_block(stat))
        self._layout.addStretch(1)

    @staticmethod
    def _build_block(stat: HeroStat) -> QWidget:
        tokens = get_tokens()

        block = QWidget()
        col = QVBoxLayout(block)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)

        value = QLabel(stat.value)
        value.setFont(Typography.font("display"))
        value.setAlignment(Qt.AlignLeft | Qt.AlignBaseline)
        value.setStyleSheet(
            f"color: {_sentiment_color(stat.sentiment)}; background: transparent;"
        )
        col.addWidget(value)

        caption = QLabel(stat.label.upper())
        Typography.apply(caption, "caption")
        caption.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        col.addWidget(caption)

        return block


def _sentiment_color(sentiment: Sentiment) -> str:
    t = get_tokens()
    if sentiment == "positive":
        return t.success
    if sentiment == "negative":
        return t.error
    if sentiment == "accent":
        return t.accent_primary
    return t.text_primary
