"""
Animation framework — lightweight helpers built on QPropertyAnimation.

Provides fade, slide, and pulse effects for screen transitions, skeleton
loaders, and micro-interactions. All durations follow the 200ms industry
standard (scope.gg / FACEIT pattern).
"""

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QSequentialAnimationGroup,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


def _ensure_opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
    """Attach a QGraphicsOpacityEffect if not already present."""
    effect = widget.graphicsEffect()
    if not isinstance(effect, QGraphicsOpacityEffect):
        effect = QGraphicsOpacityEffect(widget)
        effect.setOpacity(1.0)
        widget.setGraphicsEffect(effect)
    return effect


class Animator:
    """Reusable animation helpers — all durations in milliseconds."""

    @staticmethod
    def fade_in(widget: QWidget, duration: int = 200) -> QPropertyAnimation:
        """Fade widget from 0 to 1 opacity."""
        effect = _ensure_opacity_effect(widget)
        effect.setOpacity(0.0)
        widget.setVisible(True)

        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        return anim

    @staticmethod
    def fade_out(
        widget: QWidget, duration: int = 150, hide_on_finish: bool = False
    ) -> QPropertyAnimation:
        """Fade widget from current opacity to 0."""
        effect = _ensure_opacity_effect(widget)

        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration)
        anim.setStartValue(effect.opacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        if hide_on_finish:
            anim.finished.connect(lambda: widget.setVisible(False))
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        return anim

    @staticmethod
    def pulse(
        widget: QWidget,
        low: float = 0.3,
        high: float = 0.8,
        duration: int = 1200,
    ) -> QSequentialAnimationGroup:
        """Pulsing opacity loop for skeleton loaders (breathing effect).

        Returns the animation group so callers can stop() it when loading finishes.
        """
        effect = _ensure_opacity_effect(widget)
        effect.setOpacity(low)

        group = QSequentialAnimationGroup(widget)

        fade_up = QPropertyAnimation(effect, b"opacity")
        fade_up.setDuration(duration // 2)
        fade_up.setStartValue(low)
        fade_up.setEndValue(high)
        fade_up.setEasingCurve(QEasingCurve.InOutSine)

        fade_down = QPropertyAnimation(effect, b"opacity")
        fade_down.setDuration(duration // 2)
        fade_down.setStartValue(high)
        fade_down.setEndValue(low)
        fade_down.setEasingCurve(QEasingCurve.InOutSine)

        group.addAnimation(fade_up)
        group.addAnimation(fade_down)
        group.setLoopCount(-1)  # Infinite loop
        group.start()
        return group

    @staticmethod
    def cross_fade(
        old_widget: QWidget,
        new_widget: QWidget,
        duration: int = 200,
    ) -> None:
        """Cross-fade from one widget to another (for screen transitions).

        Fades out old_widget, then fades in new_widget.
        """
        # Ensure new widget starts invisible
        new_effect = _ensure_opacity_effect(new_widget)
        new_effect.setOpacity(0.0)
        new_widget.setVisible(True)

        # Fade out old, then fade in new
        old_effect = _ensure_opacity_effect(old_widget)
        fade_out = QPropertyAnimation(old_effect, b"opacity", old_widget)
        fade_out.setDuration(duration // 2)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InCubic)

        def _on_fade_out_done():
            Animator.fade_in(new_widget, duration // 2)

        fade_out.finished.connect(_on_fade_out_done)
        fade_out.start(QAbstractAnimation.DeleteWhenStopped)
