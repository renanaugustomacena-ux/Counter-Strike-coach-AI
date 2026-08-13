"""Horizontal step indicator — dots + connector bars (+ optional labels).

Used by the first-run wizard (Frame 18) to show which step the user is
on. Each dot is a 14px circle; the connector is a 2px bar between dots.
Active step = accent_primary; completed steps = accent_pressed;
upcoming steps = border_default.

Two modes:
    * Unlabeled (default, original API): plain dots + bars, no text.
    * Labeled (``labels=[...]``): frame-18 anatomy — completed dots
      carry a check glyph, current/upcoming dots carry their step
      number, and each dot gets a small caption underneath (current =
      accent, completed = secondary, upcoming = tertiary).

Set ``current_step`` via the setter or the property; emits
``step_changed`` when the value changes so callers can react without
polling.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography


class Stepper(QWidget):
    """Horizontal dot-and-bar step indicator.

    Args:
        step_count: Number of steps in the flow.
        current_step: 0-indexed current step. Defaults to 0.
        labels: Optional per-step captions rendered under the dots
            (frame 18). Must have exactly ``step_count`` entries.
    """

    step_changed = Signal(int)

    _DOT_RADIUS = 7
    _BAR_THICKNESS = 2
    _BAR_LENGTH = 48
    _DOT_SPACING = 16  # padding between the dot edge and the bar
    _LABEL_GAP = 4  # vertical gap between dots and labels
    _MIN_PITCH = 64  # labeled mode: minimum horizontal cell per step

    def __init__(
        self,
        step_count: int = 4,
        current_step: int = 0,
        labels: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        if step_count < 1:
            raise ValueError("step_count must be >= 1")
        if labels is not None and len(labels) != step_count:
            raise ValueError("labels must have exactly step_count entries")
        self._step_count = step_count
        self._current_step = max(0, min(current_step, step_count - 1))
        self._labels: list[str] = list(labels) if labels else []
        self._label_font = Typography.font("caption")
        self._update_geometry()

    def _update_geometry(self) -> None:
        if self._labels:
            fm = QFontMetrics(self._label_font)
            pitch = max(
                self._MIN_PITCH,
                max(fm.horizontalAdvance(text) for text in self._labels) + 12,
            )
            self._pitch = pitch
            w = pitch * self._step_count + 8
            h = self._DOT_RADIUS * 2 + 8 + self._LABEL_GAP + fm.height()
        else:
            self._pitch = 0
            # Width = sum of dot diameters + (n-1) * bar_length + padding
            w = (
                self._step_count * (self._DOT_RADIUS * 2)
                + (self._step_count - 1) * self._BAR_LENGTH
                + 8
            )
            h = self._DOT_RADIUS * 2 + 8
        self.setFixedSize(w, h)

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

    @property
    def labels(self) -> list[str]:
        return list(self._labels)

    def set_labels(self, labels: list[str] | None) -> None:
        """Replace (or clear) the per-step captions — used on retranslate."""
        if labels is not None and len(labels) != self._step_count:
            raise ValueError("labels must have exactly step_count entries")
        self._labels = list(labels) if labels else []
        self._update_geometry()
        self.update()

    def advance(self) -> None:
        """Move to the next step if possible."""
        self._set_current(self._current_step + 1)

    def retreat(self) -> None:
        """Move to the previous step if possible."""
        self._set_current(self._current_step - 1)

    # ── Paint ──

    def paintEvent(self, event):  # noqa: D401
        if self._labels:
            self._paint_labeled()
        else:
            self._paint_plain()

    def _paint_plain(self) -> None:
        """Original chrome-less mode — plain dots and bars."""
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

    def _paint_labeled(self) -> None:
        """Frame-18 mode — check/number glyphs in dots + captions below."""
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        active = QColor(tokens.accent_primary)
        completed = QColor(tokens.accent_pressed)
        upcoming = QColor(tokens.border_default)
        r = self._DOT_RADIUS
        cy = 4 + r
        fm = QFontMetrics(self._label_font)

        glyph_font = Typography.font("caption")
        glyph_font.setBold(True)

        centers = [4 + i * self._pitch + self._pitch / 2 for i in range(self._step_count)]

        # Connector bars first (under the dots)
        for i in range(self._step_count - 1):
            bar_color = completed if i < self._current_step else upcoming
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(bar_color))
            painter.drawRect(
                QRectF(
                    centers[i] + r,
                    cy - self._BAR_THICKNESS / 2,
                    centers[i + 1] - centers[i] - 2 * r,
                    self._BAR_THICKNESS,
                )
            )

        for i, cx in enumerate(centers):
            dot_rect = QRectF(cx - r, cy - r, r * 2, r * 2)
            painter.setFont(glyph_font)
            if i < self._current_step:
                # Completed — filled dot + check glyph
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(completed))
                painter.drawEllipse(dot_rect)
                painter.setPen(QPen(QColor(tokens.text_inverse)))
                painter.drawText(dot_rect, Qt.AlignCenter, "✓")
            elif i == self._current_step:
                # Current — accent fill + subtle ring + step number
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(active))
                painter.drawEllipse(dot_rect)
                ring = QColor(active)
                ring.setAlpha(60)
                painter.setPen(QPen(ring, 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(dot_rect.adjusted(-4, -4, 4, 4))
                painter.setPen(QPen(QColor(tokens.text_inverse)))
                painter.drawText(dot_rect, Qt.AlignCenter, str(i + 1))
            else:
                # Upcoming — outline dot + tertiary step number
                painter.setPen(QPen(upcoming, 1.5))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(dot_rect)
                painter.setPen(QPen(QColor(tokens.text_tertiary)))
                painter.drawText(dot_rect, Qt.AlignCenter, str(i + 1))

            # Caption under the dot
            if i == self._current_step:
                label_color = QColor(tokens.accent_primary)
            elif i < self._current_step:
                label_color = QColor(tokens.text_secondary)
            else:
                label_color = QColor(tokens.text_tertiary)
            painter.setFont(self._label_font)
            painter.setPen(QPen(label_color))
            label_rect = QRectF(
                cx - self._pitch / 2,
                cy + r + self._LABEL_GAP,
                self._pitch,
                fm.height(),
            )
            painter.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop, self._labels[i])

        painter.end()
