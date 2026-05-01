"""Typography helper — single source of truth for font roles across qt_app.

Two ways to apply typography to a widget:

1. ``Typography.apply(widget, role)`` — preferred for QLabels. Roles that
   match a QLabel[variant="..."] rule in ``themes/base.qss.template``
   (display, h1, caption, mono, accent) flow through QSS. Other roles
   fall back to setFont().

2. ``Typography.font(role)`` — returns a QFont for non-QLabel widgets,
   QPainter calls, or QFontMetrics math.

Roles always read sizes from ``get_tokens()`` — never hardcode a number
elsewhere. This keeps theme changes consistent and the W3C tokens JSON
authoritative.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

_SANS = "Roboto"
_DISPLAY = "Space Grotesk"
_MONO = "JetBrains Mono"

# Roles whose visual treatment is fully described by a QSS rule under
# QLabel[variant="..."]. apply() routes these via setProperty() + polish().
_QSS_ROLES: frozenset[str] = frozenset({"display", "h1", "caption", "mono", "accent"})


class Typography:
    """Static helper — never instantiate."""

    @staticmethod
    def apply(widget: QWidget, role: str) -> None:
        """Apply a typography role to the widget.

        For QSS-backed roles (QLabel variants), sets the ``variant`` property
        and re-polishes so the rule takes effect immediately. For others,
        calls setFont() with the role's QFont.
        """
        if role in _QSS_ROLES:
            widget.setProperty("variant", role)
            style = widget.style()
            if style is not None:
                style.unpolish(widget)
                style.polish(widget)
            return
        widget.setFont(Typography.font(role))

    @staticmethod
    def font(role: str) -> QFont:
        """Return a QFont for the given role."""
        t = get_tokens()
        if role == "display":
            f = QFont(_DISPLAY, t.font_size_display, QFont.Black)
            f.setLetterSpacing(QFont.AbsoluteSpacing, -1.0)
            return f
        if role == "h1":
            f = QFont(_DISPLAY, t.font_size_h1, QFont.Bold)
            f.setLetterSpacing(QFont.AbsoluteSpacing, -0.5)
            return f
        if role == "title":
            return QFont(_SANS, t.font_size_title, QFont.DemiBold)
        if role == "subtitle":
            return QFont(_SANS, t.font_size_subtitle, QFont.Bold)
        if role == "body":
            return QFont(_SANS, t.font_size_body, QFont.Normal)
        if role == "caption":
            f = QFont(_SANS, t.font_size_caption, QFont.DemiBold)
            f.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
            f.setCapitalization(QFont.AllUppercase)
            return f
        if role == "mono":
            return QFont(_MONO, t.font_size_body, QFont.Normal)
        if role == "stat":
            return QFont(_DISPLAY, t.font_size_stat, QFont.Bold)
        return QFont(_SANS, t.font_size_body, QFont.Normal)
