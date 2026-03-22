"""Card component — themed container with title, optional subtitle, and content area.

Replaces the ad-hoc _make_card() helpers duplicated across 4 screens.
Uses the dashboard_card QSS object name for theme-consistent styling.
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class Card(QFrame):
    """Standard card with title, optional subtitle, and content area.

    Args:
        title: Card title text.
        subtitle: Optional description below the title.
        parent: Parent widget.
    """

    def __init__(self, title: str = "", subtitle: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        tokens = get_tokens()

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(tokens.spacing_sm)

        # Title
        self._title_label = QLabel(title)
        self._title_label.setFont(QFont("Roboto", tokens.font_size_subtitle, QFont.Bold))
        self._title_label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        if title:
            self._layout.addWidget(self._title_label)
        else:
            self._title_label.setVisible(False)

        # Subtitle
        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setStyleSheet(
            f"color: {tokens.text_secondary}; font-size: {tokens.font_size_body}px; "
            f"background: transparent;"
        )
        if subtitle:
            self._layout.addWidget(self._subtitle_label)
        else:
            self._subtitle_label.setVisible(False)

    @property
    def title_label(self) -> QLabel:
        """Access the title QLabel for retranslation or updates."""
        return self._title_label

    @property
    def content_layout(self) -> QVBoxLayout:
        """The layout where child widgets should be added."""
        return self._layout

    def set_title(self, text: str):
        """Update the card title."""
        self._title_label.setText(text)
        self._title_label.setVisible(bool(text))

    def set_subtitle(self, text: str):
        """Update the card subtitle."""
        self._subtitle_label.setText(text)
        self._subtitle_label.setVisible(bool(text))
