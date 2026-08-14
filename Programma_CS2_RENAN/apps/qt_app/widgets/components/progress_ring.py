"""ProgressRing component — circular progress indicator using QPainter.

Replaces horizontal progress bars with a modern circular design.
Draws a background arc and a foreground arc proportional to the value.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QConicalGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography


class ProgressRing(QWidget):
    """Circular progress indicator with centered percentage text.

    Size presets (frames 20/33): ``SMALL`` inline chips, ``DEFAULT``
    generic, ``COACH`` belief ring, ``HERO`` full-width celebration.

    Args:
        value: Progress value between 0.0 and 1.0.
        size: Widget diameter in pixels (use the class presets).
        thickness: Arc stroke width in pixels (frame spec: 8).
        show_text: Whether to display percentage text in center.
        parent: Parent widget.
    """

    SMALL = 48
    DEFAULT = 64
    COACH = 80
    HERO = 128

    def __init__(
        self,
        value: float = 0.0,
        size: int = DEFAULT,
        thickness: int = 8,
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

        # Foreground arc (progress) — conical gradient from accent_primary
        # at the 12 o'clock start to accent_hover at the arc's end. Adds
        # a subtle vertical depth cue without a second pass.
        gradient = QConicalGradient(QPointF(rect.center()), 90.0)
        gradient.setColorAt(0.0, QColor(tokens.accent_primary))
        gradient.setColorAt(max(0.01, self._value), QColor(tokens.accent_hover))
        gradient.setColorAt(1.0, QColor(tokens.accent_primary))
        fg_pen = QPen(gradient, self._thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(fg_pen)
        # Start at 12 o'clock (90°), sweep counter-clockwise (frame 33
        # spec: "starts 12 o'clock CCW" — positive span in Qt's
        # mathematical angle convention; matches the conical gradient
        # which also runs CCW from its 90° start).
        start_angle = 90 * 16
        span_angle = int(self._value * 360 * 16)
        painter.drawArc(rect, start_angle, span_angle)

        # Center text — stat role family/weight, point size scaled to the
        # ring diameter (geometry math, not a design constant).
        if self._show_text:
            painter.setPen(QColor(tokens.text_primary))
            font = Typography.font("stat")
            font.setPointSize(max(9, side // 5))
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, f"{int(self._value * 100)}%")

        painter.end()
