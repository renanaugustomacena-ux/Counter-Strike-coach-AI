"""NumberedStep — accent-circled step row (frame 19 Getting Started).

Anatomy: filled accent circle with the step number (text_inverse bold)
+ bold title + secondary description beneath.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography


class NumberedStep(QWidget):
    """One numbered step: (n) + bold title + secondary description."""

    def __init__(
        self,
        number: int,
        title: str,
        description: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        tokens = get_tokens()

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_md)

        self._circle = QLabel(str(number))
        self._circle.setObjectName("numbered_step_circle")
        self._circle.setFixedSize(tokens.spacing_xl, tokens.spacing_xl)  # 24px round
        self._circle.setAlignment(Qt.AlignCenter)
        row.addWidget(self._circle, alignment=Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        self._title_label = QLabel(title)
        self._title_label.setFont(Typography.font("body", QFont.Bold))
        text_col.addWidget(self._title_label)

        self._desc_label = QLabel(description)
        self._desc_label.setObjectName("numbered_step_desc")
        self._desc_label.setWordWrap(True)
        if description:
            text_col.addWidget(self._desc_label)
        else:
            self._desc_label.setVisible(False)
        row.addLayout(text_col, 1)

    def set_title(self, text: str) -> None:
        self._title_label.setText(text)

    def set_description(self, text: str) -> None:
        self._desc_label.setText(text)
        self._desc_label.setVisible(bool(text))
