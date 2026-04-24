"""Animation framework — lightweight helpers built on QPropertyAnimation.

Provides fade, slide, pulse, stagger-reveal, and collapse-width effects
for screen transitions, skeleton loaders, sidebar animations, and micro-
interactions. Default duration: 200 ms (industry-standard scope.gg / FACEIT
pattern). Easing defaults come from `core.easing.Easing`.

SAFETY NOTE — QGraphicsOpacityEffect:
    Applying `QGraphicsOpacityEffect` to a widget that is mid-repaint (most
    commonly during a stacked-widget screen transition) causes QPainter
    errors on Linux — see `main_window.py:171`. The helpers in this module
    that mutate geometry (`slide_in`, `slide_out`, `reveal_stagger`,
    `collapse_width`) are safe in that context because they do NOT attach
    a graphics effect. Prefer them over `fade_in`/`fade_out`/`cross_fade`
    whenever a widget may repaint concurrently.
"""

from typing import Iterable, Literal

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QSequentialAnimationGroup,
    QTimer,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.easing import Easing


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

    # ── Geometry animations (safe on mid-repaint widgets) ─────────────

    @staticmethod
    def slide_in(
        widget: QWidget,
        direction: Literal["left", "right", "up", "down"] = "right",
        distance_px: int = 24,
        duration: int = 220,
        easing: QEasingCurve | None = None,
    ) -> QPropertyAnimation:
        """Slide a widget from an offset back to its resting geometry.

        Animates `geometry` (not opacity) so it is safe to call on widgets
        that may repaint concurrently — e.g. toasts sliding in from the
        right edge while the underlying screen renders.

        The widget must already have its final geometry set (via layout or
        `setGeometry`). `distance_px` is how far offset the start position
        is from the resting position along `direction`.
        """
        widget.setVisible(True)
        end = widget.geometry()
        dx, dy = 0, 0
        if direction == "right":
            dx = distance_px
        elif direction == "left":
            dx = -distance_px
        elif direction == "down":
            dy = distance_px
        elif direction == "up":
            dy = -distance_px
        start = QRect(end.x() + dx, end.y() + dy, end.width(), end.height())
        widget.setGeometry(start)

        anim = QPropertyAnimation(widget, b"geometry", widget)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(easing or Easing.OutCubic)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        return anim

    @staticmethod
    def slide_out(
        widget: QWidget,
        direction: Literal["left", "right", "up", "down"] = "right",
        distance_px: int = 24,
        duration: int = 180,
        easing: QEasingCurve | None = None,
        hide_on_finish: bool = True,
    ) -> QPropertyAnimation:
        """Slide a widget away from its resting geometry along `direction`.

        Safe on mid-repaint widgets (animates `geometry`, not opacity).
        Optionally hides the widget once the animation finishes.
        """
        start = widget.geometry()
        dx, dy = 0, 0
        if direction == "right":
            dx = distance_px
        elif direction == "left":
            dx = -distance_px
        elif direction == "down":
            dy = distance_px
        elif direction == "up":
            dy = -distance_px
        end = QRect(start.x() + dx, start.y() + dy, start.width(), start.height())

        anim = QPropertyAnimation(widget, b"geometry", widget)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(easing or Easing.InCubic)
        if hide_on_finish:
            anim.finished.connect(lambda: widget.setVisible(False))
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        return anim

    @staticmethod
    def reveal_stagger(
        widgets: Iterable[QWidget],
        delay_ms: int = 40,
        duration: int = 220,
        distance_px: int = 16,
        direction: Literal["left", "right", "up", "down"] = "up",
    ) -> list[QPropertyAnimation]:
        """Reveal a sequence of widgets with a staggered slide-in.

        Each widget starts `distance_px` offset in `direction` from its
        resting position, then slides back at `delay_ms` intervals. Used
        by bento grids, card lists, and skeleton rows.
        """
        anims: list[QPropertyAnimation] = []
        for i, w in enumerate(widgets):
            QTimer.singleShot(
                i * delay_ms,
                lambda widget=w: Animator.slide_in(
                    widget, direction=direction, distance_px=distance_px, duration=duration
                ),
            )
        return anims

    @staticmethod
    def collapse_width(
        widget: QWidget,
        to_width: int,
        duration: int = 200,
        easing: QEasingCurve | None = None,
    ) -> QPropertyAnimation:
        """Animate `minimumWidth` → `to_width` for sidebar collapse / expand.

        Qt's `QWidget.minimumWidth` is a property, but not a Q_PROPERTY
        animatable directly. We animate via `geometry` on the widget's
        current height; layout engines that track min-width may need
        `widget.setFixedWidth(to_width)` called before/after to settle.
        For a plain sidebar pattern this is fine.
        """
        start = widget.geometry()
        end = QRect(start.x(), start.y(), to_width, start.height())
        anim = QPropertyAnimation(widget, b"geometry", widget)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(easing or Easing.OutCubic)
        anim.start(QAbstractAnimation.DeleteWhenStopped)
        return anim
