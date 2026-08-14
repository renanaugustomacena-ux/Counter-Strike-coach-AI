"""MiniLinkCard — small navigation card: bold "Title →" + caption.

Frame anatomy (17 "Related" row / 19 "RELATED" row): a sunken clickable
card with a bold title carrying a trailing arrow glyph and a one-line
secondary caption. Emits ``clicked`` on left press; the caller wires
navigation (``switch_screen`` / topic switch).

QSS anatomy (token-substituted in ``base.qss.template``):
    QFrame#mini_link_card          sunken surface, subtle border, accent on hover
    QLabel#mini_link_title         bold primary title
    QLabel#mini_link_caption       secondary caption
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class MiniLinkCard(QFrame):
    """Clickable mini navigation card with a bold title and a caption."""

    clicked = Signal()

    def __init__(self, title: str = "", caption: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("mini_link_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        tokens = get_tokens()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing_md, tokens.spacing_md, tokens.spacing_md, tokens.spacing_md
        )
        layout.setSpacing(tokens.spacing_xs)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("mini_link_title")
        layout.addWidget(self._title_label)

        self._caption_label = QLabel(caption)
        self._caption_label.setObjectName("mini_link_caption")
        self._caption_label.setWordWrap(True)
        layout.addWidget(self._caption_label)

    def set_title(self, text: str) -> None:
        self._title_label.setText(text)

    def set_caption(self, text: str) -> None:
        self._caption_label.setText(text)

    def mousePressEvent(self, event):  # noqa: D401
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
