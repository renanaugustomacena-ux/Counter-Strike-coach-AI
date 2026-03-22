"""ProgressRing component — circular progress indicator using QPainter.

Replaces horizontal progress bars with a modern circular design.
Draws a background arc and a foreground arc proportional to the value.
"""

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class ProgressRing(QWidget):
    """Circular progress indicator with centered percentage text.

    Args:
        value: Progress value between 0.0 and 1.0.
        size: Widget diameter in pixels.
        thickness: Arc stroke width in pixels.
        show_text: Whether to display percentage text in center.
        parent: Parent widget.
    """

    def __init__(
        self,
        value: float = 0.0,
        size: int = 64,
        thickness: int = 6,
        show_text: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._value = max(0.0, min(1.0, value))
        self._thickness = thickness
        self._show_text = show_text
        self.setFixedSize(size, size)

    def set_value(self, value: float):
        """Update the progress value (0.0 to 1.0)."""
        self._value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        margin = self._thickness / 2 + 1
        rect = QRectF(margin, margin, side - 2 * margin, side - 2 * margin)

        # Background arc (full circle)
        bg_color = QColor(tokens.border_default)
        bg_color.setAlphaF(0.3)
        bg_pen = QPen(bg_color, self._thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Foreground arc (progress)
        fg_color = QColor(tokens.accent_primary)
        fg_pen = QPen(fg_color, self._thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(fg_pen)
        # Start at 12 o'clock (90°), sweep counter-clockwise
        start_angle = 90 * 16
        span_angle = -int(self._value * 360 * 16)
        painter.drawArc(rect, start_angle, span_angle)

        # Center text
        if self._show_text:
            painter.setPen(QColor(tokens.text_primary))
            font_size = max(9, side // 5)
            painter.setFont(QFont("Roboto", font_size, QFont.Bold))
            painter.drawText(
                self.rect(), Qt.AlignCenter, f"{int(self._value * 100)}%"
            )

        painter.end()
