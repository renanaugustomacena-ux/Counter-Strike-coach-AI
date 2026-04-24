"""Animated integer counter — tweens 0 → target on reveal.

Large numbers on dashboard cards *should* feel earned, not dumped. The
standard Qt path (``label.setText(str(value))``) flashes the final
figure with zero story. This widget animates the transition via a
``Q_PROPERTY`` float backed by a ``QPropertyAnimation`` so the viewer's
eye is drawn to the metric as it settles.

Usage::

    counter = AnimatedCounter(target=1256, prefix="", suffix=" matches")
    layout.addWidget(counter)
    counter.start_animation()        # or counter.set_target(new_value)

Formatting:
    ``prefix`` + ``f"{value:,.0f}"`` + ``suffix`` — thousand-separated
    integer by default. Pass ``precision > 0`` to render a decimal.

Safety:
    Animates a scalar ``Q_PROPERTY`` — NOT a ``QGraphicsOpacityEffect`` —
    so the Linux mid-repaint pitfall documented in ``core/animation.py``
    cannot trigger.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QAbstractAnimation, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.easing import Easing


class AnimatedCounter(QLabel):
    """QLabel that animates its integer value on reveal / update."""

    finished = Signal()

    def __init__(
        self,
        target: float = 0.0,
        prefix: str = "",
        suffix: str = "",
        precision: int = 0,
        duration_ms: int = 900,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        tokens = get_tokens()
        self._value: float = 0.0
        self._target: float = float(target)
        self._prefix = prefix
        self._suffix = suffix
        self._precision = max(0, int(precision))
        self._duration = int(duration_ms)
        self._anim: QPropertyAnimation | None = None

        # Use the display stack + variant so QSS picks up tight tracking.
        self.setProperty("variant", "display")
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setFont(QFont("Space Grotesk", tokens.font_size_stat, QFont.Bold))
        self._render()

    # ── Animated Q_PROPERTY ──
    # Private getter/setter so QPropertyAnimation can address
    # `b"value"` below. The Property wiring uses ``float`` so tweens are
    # smooth even when the final target is an int.

    def _get_value(self) -> float:
        return self._value

    def _set_value(self, value: float) -> None:
        self._value = float(value)
        self._render()

    value = Property(float, _get_value, _set_value)

    # ── Public API ──

    def set_target(self, target: float, animate: bool = True) -> None:
        """Update the displayed target.

        When ``animate=True`` (default) the current displayed value
        tweens to the new target. Pass ``False`` to snap instantly —
        useful when a screen is invisible and the animation would be
        wasted.
        """
        self._target = float(target)
        if not animate:
            self._set_value(self._target)
            return
        self.start_animation()

    def set_format(
        self,
        prefix: str | None = None,
        suffix: str | None = None,
        precision: int | None = None,
    ) -> None:
        if prefix is not None:
            self._prefix = prefix
        if suffix is not None:
            self._suffix = suffix
        if precision is not None:
            self._precision = max(0, int(precision))
        self._render()

    def start_animation(self) -> None:
        """Tween current value → target. Cancels any in-flight animation."""
        if self._anim is not None:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setStartValue(float(self._value))
        self._anim.setEndValue(float(self._target))
        self._anim.setDuration(self._duration)
        self._anim.setEasingCurve(Easing.OutExpo)
        self._anim.finished.connect(self.finished)
        self._anim.start(QAbstractAnimation.DeleteWhenStopped)

    # ── Internal ──

    def _render(self) -> None:
        body = f"{self._value:,.{self._precision}f}"
        self.setText(f"{self._prefix}{body}{self._suffix}")
