"""iOS-style toggle switch — 48x26 pill with a sliding knob.

QCheckBox gets styled by QSS but the box indicator stays rectangular,
which reads as "preference list checkbox" rather than "feature flag on/
off". The flagship P3 settings panel surfaces three toggle-gated
features (sounds, frameless, pyqtgraph heatmap) — each deserves a
distinct affordance that reads as a switch.

Animates the knob position via geometry (NOT an opacity effect) so the
Linux QPainter/mid-repaint crash documented in ``core/animation.py``
cannot be triggered.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.easing import Easing

# Track: 48px wide, 26px tall. Knob: 20x20 with 3px inset on each side.
_TRACK_W = 48
_TRACK_H = 26
_KNOB_SIZE = 20
_KNOB_INSET = 3
_KNOB_X_OFF = _KNOB_INSET
_KNOB_X_ON = _TRACK_W - _KNOB_SIZE - _KNOB_INSET


class ToggleSwitch(QWidget):
    """Animated binary toggle with ``toggled(bool)`` signal.

    Usage::

        sw = ToggleSwitch(checked=False)
        sw.toggled.connect(app_state.set_sounds_enabled)

    The widget is keyboard accessible: Space and Enter flip the state
    when it has focus. Clicks / taps flip immediately.
    """

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(_TRACK_W, _TRACK_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

        self._checked = bool(checked)
        # Knob x-coordinate is the animated @Property.
        self._knob_x: float = _KNOB_X_ON if self._checked else _KNOB_X_OFF

    # ── Public API ──

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        value = bool(value)
        if value == self._checked:
            return
        self._checked = value
        self._animate_to(value)
        self.toggled.emit(value)

    # ── Animated knob position ──

    def _get_knob_x(self) -> float:
        return self._knob_x

    def _set_knob_x(self, value: float) -> None:
        self._knob_x = value
        self.update()

    # @Property bound to QPropertyAnimation; pyqtProperty isn't needed on
    # PySide6 since QPropertyAnimation accepts any named Q_PROPERTY.
    knob_x = Property(float, _get_knob_x, _set_knob_x)

    def _animate_to(self, on: bool) -> None:
        from PySide6.QtCore import QAbstractAnimation, QPropertyAnimation

        target = _KNOB_X_ON if on else _KNOB_X_OFF
        anim = QPropertyAnimation(self, b"knob_x", self)
        anim.setDuration(220)
        anim.setStartValue(self._knob_x)
        anim.setEndValue(float(target))
        anim.setEasingCurve(Easing.OutBack)
        anim.start(QAbstractAnimation.DeleteWhenStopped)

    # ── Input ──

    def mousePressEvent(self, event):  # noqa: D401
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):  # noqa: D401
        if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.setChecked(not self._checked)
            return
        super().keyPressEvent(event)

    # ── Paint ──

    def paintEvent(self, event):  # noqa: D401
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Track
        track_rect = QRectF(0, 0, _TRACK_W, _TRACK_H)
        track_path = QPainterPath()
        track_path.addRoundedRect(track_rect, _TRACK_H / 2, _TRACK_H / 2)

        if self._checked:
            track_color = QColor(tokens.accent_primary)
            track_border = QColor(tokens.accent_pressed)
        else:
            track_color = QColor(tokens.surface_sunken)
            track_border = QColor(tokens.border_default)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawPath(track_path)

        # 1px inset border for a subtle depth cue
        painter.setPen(track_border)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, _TRACK_W - 1, _TRACK_H - 1),
            _TRACK_H / 2 - 0.5,
            _TRACK_H / 2 - 0.5,
        )

        # Focus ring when keyboard focused
        if self.hasFocus():
            painter.setPen(QColor(tokens.accent_primary))
            painter.drawRoundedRect(
                QRect(-2, -2, _TRACK_W + 4, _TRACK_H + 4),
                _TRACK_H / 2 + 2,
                _TRACK_H / 2 + 2,
            )
            painter.setPen(Qt.NoPen)

        # Knob
        knob_rect = QRectF(self._knob_x, _KNOB_INSET, _KNOB_SIZE, _KNOB_SIZE)
        knob_color = QColor(tokens.text_inverse)
        painter.setBrush(QBrush(knob_color))
        painter.drawEllipse(knob_rect)
        painter.end()
