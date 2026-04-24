"""BeliefThreatGauge — radial arc visualising the Belief-state threat level.

The backend publishes a threat multiplier (0.7–1.4) per tick; no
competitor has this data surface, so we give it a distinctive shape: a
270° arc starting at 7-o'clock, filling clockwise, with a conical
gradient that shifts orange→cyan→red as the multiplier climbs past
1.0. A small decay-curve polyline underneath the readout hints that
the value is temporally decayed from last-observed information.

The widget is fully Q_PROPERTY-animated — set ``threat_multiplier`` and
the arc tweens via ``QPropertyAnimation``. Size is fixed at 160×180 to
drop cleanly into a raised Card's content layout.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Property, QAbstractAnimation, QPointF, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QConicalGradient, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.easing import Easing

# Arc geometry: 270° arc starts at 7-o'clock (225° in Qt's coordinate
# system, 0°=3-o'clock, counter-clockwise positive) and sweeps clockwise
# back around. Qt's drawArc uses 1/16th degree units.
_ARC_START_DEG = 225.0
_ARC_SWEEP_DEG = -270.0  # negative = clockwise


class BeliefThreatGauge(QWidget):
    """Radial threat gauge with animated fill and decay-curve hint.

    ``threat_multiplier`` in [0.7, 1.4] maps to [0.0, 1.0] fill. Values
    under 0.85 are read as "safe"; 0.85–1.10 as "contested"; above
    1.10 as "hot". Color follows semantic tokens at each band.
    """

    def __init__(
        self,
        threat: float = 1.0,
        label: str = "Threat",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setFixedSize(160, 180)
        self._threat: float = float(threat)
        self._display_fill: float = self._threat_to_fill(self._threat)
        self._label = label
        self._anim: Optional[QPropertyAnimation] = None

    # ── Animated Q_PROPERTY ─────────────────────────────────────────────

    def _get_fill(self) -> float:
        return self._display_fill

    def _set_fill(self, value: float) -> None:
        self._display_fill = max(0.0, min(1.0, float(value)))
        self.update()

    fill = Property(float, _get_fill, _set_fill)

    # ── Public API ──────────────────────────────────────────────────────

    def set_threat(self, threat: float, animate: bool = True) -> None:
        """Update the threat multiplier. Animates the fill arc by default."""
        self._threat = float(threat)
        target = self._threat_to_fill(self._threat)
        if not animate:
            self._set_fill(target)
            return
        if self._anim is not None:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"fill", self)
        self._anim.setStartValue(self._display_fill)
        self._anim.setEndValue(target)
        self._anim.setDuration(420)
        self._anim.setEasingCurve(Easing.OutExpo)
        self._anim.start(QAbstractAnimation.DeleteWhenStopped)

    def set_label(self, text: str) -> None:
        self._label = text
        self.update()

    # ── Paint ───────────────────────────────────────────────────────────

    def paintEvent(self, event):  # noqa: D401
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Arc framing rect — leave headroom for the readout below.
        side = min(self.width(), self.height() - 28)
        margin = 8
        rect = QRectF(
            (self.width() - side) / 2 + margin,
            margin,
            side - 2 * margin,
            side - 2 * margin,
        )

        # Background arc — dim rail against which the fill sweeps.
        bg_color = QColor(tokens.border_default)
        bg_color.setAlphaF(0.5)
        bg_pen = QPen(bg_color, 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, int(_ARC_START_DEG * 16), int(_ARC_SWEEP_DEG * 16))

        # Fill arc — conical gradient that reads as safe → contested → hot.
        gradient = QConicalGradient(QPointF(rect.center()), _ARC_START_DEG)
        gradient.setColorAt(0.0, QColor(tokens.success))
        gradient.setColorAt(0.5, QColor(tokens.accent_primary))
        gradient.setColorAt(1.0, QColor(tokens.error))
        fill_pen = QPen(QBrush(gradient), 10, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(fill_pen)
        sweep = _ARC_SWEEP_DEG * self._display_fill
        painter.drawArc(rect, int(_ARC_START_DEG * 16), int(sweep * 16))

        # Decay hint — a thin polyline INSIDE the arc hinting the
        # value is temporally decayed (not live ground truth).
        painter.setPen(QPen(QColor(tokens.text_tertiary), 1.2))
        painter.setBrush(Qt.NoBrush)
        inset = rect.adjusted(14, 14, -14, -14)
        path = QPainterPath()
        start = inset.bottomLeft() + QPointF(0, -6)
        path.moveTo(start)
        for i in range(1, 9):
            t = i / 8.0
            x = inset.left() + inset.width() * t
            y = inset.bottom() - 6 - (1 - t) * 20 * (1 - self._display_fill)
            path.lineTo(QPointF(x, y))
        painter.drawPath(path)

        # Multiplier readout — large display number + caption.
        painter.setPen(QColor(tokens.text_primary))
        painter.setFont(QFont("Space Grotesk", tokens.font_size_h1, QFont.Bold))
        readout_rect = QRectF(0, rect.top() + rect.height() * 0.38, self.width(), 36)
        painter.drawText(readout_rect, Qt.AlignCenter, f"{self._threat:.2f}")

        painter.setPen(QColor(tokens.text_secondary))
        painter.setFont(QFont("JetBrains Mono", tokens.font_size_caption, QFont.Medium))
        caption_rect = QRectF(0, readout_rect.bottom() - 2, self.width(), 18)
        painter.drawText(caption_rect, Qt.AlignCenter, self._band_label())

        # Footer label at the bottom of the widget.
        painter.setPen(QColor(tokens.text_secondary))
        painter.setFont(QFont("Inter", tokens.font_size_caption, QFont.Medium))
        footer_rect = QRectF(0, self.height() - 24, self.width(), 20)
        painter.drawText(footer_rect, Qt.AlignCenter, self._label.upper())
        painter.end()

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _threat_to_fill(threat: float) -> float:
        """Map threat multiplier [0.7..1.4] to fill [0..1], clamped."""
        lo, hi = 0.7, 1.4
        t = (threat - lo) / (hi - lo)
        return max(0.0, min(1.0, t))

    def _band_label(self) -> str:
        if self._threat < 0.85:
            return "SAFE"
        if self._threat < 1.10:
            return "CONTESTED"
        return "HOT"
