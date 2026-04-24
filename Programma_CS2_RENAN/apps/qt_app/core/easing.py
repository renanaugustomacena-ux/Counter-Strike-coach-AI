"""Easing curves — Qt-native port of the Remotion easing library used in
`design/cs2/animations.jsx`.

`QEasingCurve` covers the common named curves; this module wraps them
behind short, typed aliases so call-sites don't need to remember the
`QEasingCurve.Type` enum name. Use with `QPropertyAnimation.setEasingCurve`.

    from Programma_CS2_RENAN.apps.qt_app.core.easing import Easing
    anim.setEasingCurve(Easing.OutBack)

For custom cubic bezier (exact parity with CSS / Remotion bezier control
points), use `Easing.cubic_bezier(x1, y1, x2, y2)`.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPointF


class Easing:
    """Named easing curves. Build on import; reuse freely."""

    # Named curves mirror the Remotion library used in the design assets.
    # See `design/cs2/animations.jsx`.
    Linear = QEasingCurve(QEasingCurve.Linear)
    InCubic = QEasingCurve(QEasingCurve.InCubic)
    OutCubic = QEasingCurve(QEasingCurve.OutCubic)
    InOutCubic = QEasingCurve(QEasingCurve.InOutCubic)
    InExpo = QEasingCurve(QEasingCurve.InExpo)
    OutExpo = QEasingCurve(QEasingCurve.OutExpo)
    InOutExpo = QEasingCurve(QEasingCurve.InOutExpo)
    InBack = QEasingCurve(QEasingCurve.InBack)
    OutBack = QEasingCurve(QEasingCurve.OutBack)
    InOutBack = QEasingCurve(QEasingCurve.InOutBack)
    InSine = QEasingCurve(QEasingCurve.InSine)
    OutSine = QEasingCurve(QEasingCurve.OutSine)
    InOutSine = QEasingCurve(QEasingCurve.InOutSine)

    @staticmethod
    def cubic_bezier(x1: float, y1: float, x2: float, y2: float) -> QEasingCurve:
        """Return a QEasingCurve using the CSS cubic-bezier control points.

        The curve passes through (0, 0) and (1, 1); the two intermediate
        control points are (x1, y1) and (x2, y2). Call this for curves
        that don't match one of the named presets (e.g. `cubic-bezier(0.65,
        0, 0.35, 1)` from the Remotion library).
        """
        curve = QEasingCurve(QEasingCurve.BezierSpline)
        # PySide6 6.x: takes three QPointF (c1, c2, endpoint).
        curve.addCubicBezierSegment(QPointF(x1, y1), QPointF(x2, y2), QPointF(1.0, 1.0))
        return curve
