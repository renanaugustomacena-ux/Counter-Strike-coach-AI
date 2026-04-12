"""SectionHeader component — title row with optional subtitle and action widget.

Standardizes the recurring pattern of a bold section title with a right-aligned
action button or label.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class SectionHeader(QWidget):
    """Section title row with optional subtitle and right-side action widget.

    Args:
        title: Section title text.
        subtitle: Optional description below the title.
        parent: Parent widget.
    """

    def __init__(
        self,
        title: str = "",
        subtitle: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        tokens = get_tokens()

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, tokens.spacing_sm)
        row.setSpacing(tokens.spacing_md)

        # Left: title + subtitle stacked
        left = QVBoxLayout()
        left.setSpacing(2)

        self._title_label = QLabel(title)
        self._title_label.setFont(QFont("Roboto", tokens.font_size_title, QFont.Bold))
        self._title_label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        left.addWidget(self._title_label)

        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setFont(QFont("Roboto", tokens.font_size_body))
        self._subtitle_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        if subtitle:
            left.addWidget(self._subtitle_label)
        else:
            self._subtitle_label.setVisible(False)

        row.addLayout(left, 1)

        # Right: placeholder for action widget
        self._action_widget: QWidget | None = None

    def set_title(self, text: str):
        """Update the section title."""
        self._title_label.setText(text)

    def set_subtitle(self, text: str):
        """Update the section subtitle."""
        self._subtitle_label.setText(text)
        self._subtitle_label.setVisible(bool(text))

    def set_action_widget(self, widget: QWidget):
        """Set a right-aligned action widget (button, label, etc.)."""
        if self._action_widget is not None:
            self.layout().removeWidget(self._action_widget)
            self._action_widget.setParent(None)
        self._action_widget = widget
        self.layout().addWidget(widget, 0, Qt.AlignRight | Qt.AlignVCenter)
