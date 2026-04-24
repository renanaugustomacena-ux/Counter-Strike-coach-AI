"""Horizontal step indicator — dots + connector bars.

Used by the first-run wizard (Frame 17–19) to show which step the user
is on without a dedicated title bar per page. Each dot is a 14px circle;
the connector is a 2px bar between dots. Active step = accent_primary;
completed steps = accent_pressed; upcoming steps = border_default.

No text labels — pairs with a bigger page title above. Set
``current_step`` via the setter or the property; emits ``step_changed``
when the value changes so callers can react without polling.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens


class Stepper(QWidget):
    """Horizontal dot-and-bar step indicator.

    Args:
        step_count: Number of steps in the flow.
        current_step: 0-indexed current step. Defaults to 0.
    """

    step_changed = Signal(int)

    _DOT_RADIUS = 7
    _BAR_THICKNESS = 2
    _BAR_LENGTH = 48
    _DOT_SPACING = 16  # padding between the dot edge and the bar

    def __init__(
        self,
        step_count: int = 4,
        current_step: int = 0,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        if step_count < 1:
            raise ValueError("step_count must be >= 1")
        self._step_count = step_count
        self._current_step = max(0, min(current_step, step_count - 1))
        # Width = sum of dot diameters + (n-1) * bar_length + padding
        w = step_count * (self._DOT_RADIUS * 2) + (step_count - 1) * self._BAR_LENGTH + 8
        self.setFixedSize(w, self._DOT_RADIUS * 2 + 8)

    # ── Public ──

    def _get_current(self) -> int:
        return self._current_step

    def _set_current(self, value: int) -> None:
        value = max(0, min(int(value), self._step_count - 1))
        if value == self._current_step:
            return
        self._current_step = value
        self.update()
        self.step_changed.emit(value)

    current_step = Property(int, _get_current, _set_current)

    @property
    def step_count(self) -> int:
        return self._step_count

    def advance(self) -> None:
        """Move to the next step if possible."""
        self._set_current(self._current_step + 1)

    def retreat(self) -> None:
        """Move to the previous step if possible."""
        self._set_current(self._current_step - 1)

    # ── Paint ──

    def paintEvent(self, event):  # noqa: D401
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cy = self.height() / 2
        x = 4  # left padding

        active = QColor(tokens.accent_primary)
        completed = QColor(tokens.accent_pressed)
        upcoming = QColor(tokens.border_default)

        for i in range(self._step_count):
            # Dot
            center_x = x + self._DOT_RADIUS
            if i < self._current_step:
                dot_color = completed
            elif i == self._current_step:
                dot_color = active
            else:
                dot_color = upcoming
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(dot_color))
            painter.drawEllipse(
                QRectF(
                    center_x - self._DOT_RADIUS,
                    cy - self._DOT_RADIUS,
                    self._DOT_RADIUS * 2,
                    self._DOT_RADIUS * 2,
                )
            )
            # Current step gets a subtle outer ring
            if i == self._current_step:
                ring = QColor(active)
                ring.setAlpha(60)
                painter.setPen(QPen(ring, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(
                    QRectF(
                        center_x - self._DOT_RADIUS - 4,
                        cy - self._DOT_RADIUS - 4,
                        (self._DOT_RADIUS + 4) * 2,
                        (self._DOT_RADIUS + 4) * 2,
                    )
                )
                painter.setPen(Qt.NoPen)

            x += self._DOT_RADIUS * 2

            # Connector bar (not after last dot)
            if i < self._step_count - 1:
                bar_color = completed if i < self._current_step else upcoming
                painter.setBrush(QBrush(bar_color))
                painter.drawRect(
                    QRectF(
                        x,
                        cy - self._BAR_THICKNESS / 2,
                        self._BAR_LENGTH,
                        self._BAR_THICKNESS,
                    )
                )
                x += self._BAR_LENGTH

        painter.end()
