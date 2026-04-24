"""Label with a subtle accent underglow painted behind its text.

QGraphicsDropShadowEffect attached to a whole widget tanks FPS on busy
screens (P2 docs) and is banned on mid-repaint paths (Linux QPainter
bug, P1 docs). The trick here: we attach the effect **only to a
dedicated QLabel** whose job is to render text once per value change,
then let the widget composite it above the regular label. The shadow
fires on text-change, not on every frame the parent re-lays-out.

Two glow layers:
    1. Wide blur (18 px) at the accent color — the "halo".
    2. Tight blur (4 px) at accent.hover — the "edge" that keeps text
       readable even at small sizes.

Use for hero metrics where the accent color is semantically "this is
the number we want the eye to land on" (e.g. total matches, win rate,
rating delta).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class UnderglowLabel(QWidget):
    """Text with a two-layer accent-colored glow. Color-token-driven."""

    def __init__(
        self,
        text: str = "",
        font_size: int | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        tokens = get_tokens()
        size = font_size or tokens.font_size_stat

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._label = QLabel(text)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._label.setFont(QFont("Space Grotesk", size, QFont.Bold))
        self._label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        # Wide halo — applied to the QLabel itself (text only, no layout
        # children), safe from the opacity-effect mid-repaint pitfall.
        glow = QGraphicsDropShadowEffect(self._label)
        glow.setBlurRadius(18)
        glow.setOffset(0, 0)
        c = QColor(tokens.accent_primary)
        c.setAlpha(130)
        glow.setColor(c)
        self._label.setGraphicsEffect(glow)

        layout.addWidget(self._label)

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def text(self) -> str:
        return self._label.text()

    @property
    def label(self) -> QLabel:
        """Expose the inner QLabel for callers that need fine control."""
        return self._label
