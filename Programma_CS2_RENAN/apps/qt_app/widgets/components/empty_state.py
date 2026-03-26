"""EmptyState component — centered message with optional CTA button.

Replaces bare "No data found" text labels with a structured empty state
that guides the user toward the next action.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class EmptyState(QWidget):
    """Centered empty state with icon area, title, description, and CTA.

    Args:
        icon_text: Large emoji or unicode character displayed at top.
        title: Main message (e.g. "No matches found").
        description: Secondary explanation text.
        cta_text: Button label. If empty, no button is shown.
        parent: Parent widget.
    """

    action_clicked = Signal()

    def __init__(
        self,
        icon_text: str = "",
        title: str = "",
        description: str = "",
        cta_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        tokens = get_tokens()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(tokens.spacing_md)
        layout.setContentsMargins(
            tokens.spacing_xxl,
            tokens.spacing_xxxl,
            tokens.spacing_xxl,
            tokens.spacing_xxxl,
        )

        # Icon area
        self._icon_label = QLabel(icon_text)
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFont(QFont("Roboto", 48))
        self._icon_label.setStyleSheet("background: transparent;")
        if icon_text:
            layout.addWidget(self._icon_label)
        else:
            self._icon_label.setVisible(False)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setFont(QFont("Roboto", tokens.font_size_title, QFont.Bold))
        self._title_label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        self._title_label.setWordWrap(True)
        layout.addWidget(self._title_label)

        # Description
        self._desc_label = QLabel(description)
        self._desc_label.setAlignment(Qt.AlignCenter)
        self._desc_label.setFont(QFont("Roboto", tokens.font_size_body))
        self._desc_label.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        self._desc_label.setWordWrap(True)
        if description:
            layout.addWidget(self._desc_label)
        else:
            self._desc_label.setVisible(False)

        # CTA button
        self._cta_button = QPushButton(cta_text)
        self._cta_button.setObjectName("accent_button")
        self._cta_button.setCursor(Qt.PointingHandCursor)
        self._cta_button.setFixedHeight(36)
        self._cta_button.clicked.connect(self.action_clicked.emit)
        if cta_text:
            layout.addWidget(self._cta_button, alignment=Qt.AlignCenter)
        else:
            self._cta_button.setVisible(False)

    def set_title(self, text: str):
        """Update the title text."""
        self._title_label.setText(text)

    def set_description(self, text: str):
        """Update the description text."""
        self._desc_label.setText(text)
        self._desc_label.setVisible(bool(text))

    def set_cta_text(self, text: str):
        """Update the CTA button text."""
        self._cta_button.setText(text)
        self._cta_button.setVisible(bool(text))
