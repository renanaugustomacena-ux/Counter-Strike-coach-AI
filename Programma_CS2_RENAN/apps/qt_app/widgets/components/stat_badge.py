"""StatBadge component — large number + label below (scope.gg pattern).

Displays a prominent stat value with a descriptive label underneath.
Color-coded semantically: green for good, red for bad, default for neutral.
Optional trend indicator shows directional delta (up / down / flat) with
its own color so glance-value doesn't depend on reading the delta text.
"""

from typing import Literal, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

_TrendDir = Literal["up", "down", "flat"]

# Unicode arrows carry semantic meaning at any font size; safer than
# sprite icons which may not ship with the specific trend glyph set.
_TREND_GLYPH: dict[_TrendDir, str] = {
    "up": "▲",  # ▲
    "down": "▼",  # ▼
    "flat": "→",  # → (horizontal neutral)
}


class StatBadge(QWidget):
    """Large stat value with label — scope.gg-style metric display.

    Args:
        value: The stat value text (e.g. "1.15", "78%").
        label: Description below the value (e.g. "Rating", "KAST").
        sentiment: "positive", "negative", or "neutral" for color coding.
        trend: Optional directional indicator: "up" | "down" | "flat".
        delta_pct: Optional numeric delta rendered next to the trend arrow.
        parent: Parent widget.
    """

    def __init__(
        self,
        value: str = "",
        label: str = "",
        sentiment: str = "neutral",
        trend: Optional[_TrendDir] = None,
        delta_pct: Optional[float] = None,
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

        # Trend row (hidden unless a trend is set)
        trend_row = QHBoxLayout()
        trend_row.setContentsMargins(0, 0, 0, 0)
        trend_row.setSpacing(4)
        trend_row.setAlignment(Qt.AlignCenter)

        self._trend_arrow = QLabel("")
        self._trend_arrow.setFont(QFont("Roboto", tokens.font_size_caption, QFont.Bold))
        self._trend_delta = QLabel("")
        self._trend_delta.setFont(QFont("JetBrains Mono", tokens.font_size_caption, QFont.Medium))
        trend_row.addWidget(self._trend_arrow)
        trend_row.addWidget(self._trend_delta)
        layout.addLayout(trend_row)

        self.set_sentiment(sentiment)
        self.set_trend(trend, delta_pct)

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

    def set_trend(
        self,
        direction: Optional[_TrendDir],
        delta_pct: Optional[float] = None,
    ) -> None:
        """Set the trend arrow + optional delta.

        Pass ``direction=None`` to hide the row entirely. The arrow color
        follows semantic tokens: success for up, error for down, tertiary
        text for flat — so a red downward arrow reads as "worse" at a
        glance regardless of what the metric measures.
        """
        if direction is None:
            self._trend_arrow.setText("")
            self._trend_delta.setText("")
            self._trend_arrow.setVisible(False)
            self._trend_delta.setVisible(False)
            return

        tokens = get_tokens()
        color_map: dict[_TrendDir, str] = {
            "up": tokens.success,
            "down": tokens.error,
            "flat": tokens.text_tertiary,
        }
        color = color_map[direction]
        self._trend_arrow.setText(_TREND_GLYPH[direction])
        self._trend_arrow.setStyleSheet(f"color: {color}; background: transparent;")
        self._trend_arrow.setVisible(True)

        if delta_pct is None:
            self._trend_delta.setText("")
            self._trend_delta.setVisible(False)
        else:
            sign = "+" if delta_pct > 0 else ("" if delta_pct == 0 else "")
            self._trend_delta.setText(f"{sign}{delta_pct:.1f}%")
            self._trend_delta.setStyleSheet(f"color: {color}; background: transparent;")
            self._trend_delta.setVisible(True)
