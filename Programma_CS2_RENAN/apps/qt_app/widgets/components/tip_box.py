"""TipBox — dashed info-outline note (frames 17/18 "Stored locally" / tips).

QSS anatomy (all token-substituted in ``base.qss.template``):
    QFrame#tip_box          1px dashed ${info} border, transparent bg
    QLabel#tip_box_title    bold ${info} title
    QLabel#tip_box_body     secondary body text
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class TipBox(QFrame):
    """Dashed-border callout with a bold info title and secondary body."""

    def __init__(self, title: str = "", body: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("tip_box")
        tokens = get_tokens()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_md, tokens.spacing_lg, tokens.spacing_md
        )
        layout.setSpacing(tokens.spacing_xs)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("tip_box_title")
        layout.addWidget(self._title_label)

        self._body_label = QLabel(body)
        self._body_label.setObjectName("tip_box_body")
        self._body_label.setWordWrap(True)
        layout.addWidget(self._body_label)

    def set_title(self, text: str) -> None:
        self._title_label.setText(text)

    def set_body(self, text: str) -> None:
        self._body_label.setText(text)
