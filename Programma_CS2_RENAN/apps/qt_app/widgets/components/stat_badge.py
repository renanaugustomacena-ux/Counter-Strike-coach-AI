"""StatBadge component — large number + label below (scope.gg pattern).

Displays a prominent stat value with a descriptive label underneath.
Color-coded semantically: green for good, red for bad, default for neutral.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class StatBadge(QWidget):
    """Large stat value with label — scope.gg-style metric display.

    Args:
        value: The stat value text (e.g. "1.15", "78%").
        label: Description below the value (e.g. "Rating", "KAST").
        sentiment: "positive", "negative", or "neutral" for color coding.
        parent: Parent widget.
    """

    def __init__(
        self,
        value: str = "",
        label: str = "",
        sentiment: str = "neutral",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        tokens = get_tokens()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing_sm, tokens.spacing_sm, tokens.spacing_sm, tokens.spacing_sm
        )
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        # Value label (large)
        self._value_label = QLabel(value)
        self._value_label.setAlignment(Qt.AlignCenter)
        self._value_label.setFont(QFont("Roboto", tokens.font_size_stat, QFont.Bold))
        layout.addWidget(self._value_label)

        # Description label (small)
        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setFont(QFont("Roboto", tokens.font_size_caption))
        self._label.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        layout.addWidget(self._label)

        self.set_sentiment(sentiment)

    def set_value(self, text: str):
        """Update the stat value."""
        self._value_label.setText(text)

    def set_label(self, text: str):
        """Update the description label."""
        self._label.setText(text)

    def set_sentiment(self, sentiment: str):
        """Update color coding: 'positive', 'negative', or 'neutral'."""
        tokens = get_tokens()
        color_map = {
            "positive": tokens.success,
            "negative": tokens.error,
            "neutral": tokens.text_primary,
        }
        color = color_map.get(sentiment, tokens.text_primary)
        self._value_label.setStyleSheet(f"color: {color}; background: transparent;")
