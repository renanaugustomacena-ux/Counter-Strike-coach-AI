"""Typography helper — single source of truth for font roles across qt_app.

Two ways to apply typography to a widget:

1. ``Typography.apply(widget, role)`` — preferred for QLabels. Roles that
   match a QLabel[variant="..."] rule in ``themes/base.qss.template``
   (display, h1, caption, mono, accent) flow through QSS. Other roles
   fall back to setFont().

2. ``Typography.font(role, weight=None)`` — returns a QFont for
   non-QLabel widgets, QPainter calls, or QFontMetrics math. The
   optional ``weight`` overrides the role's default weight.

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
    def font(role: str, weight: int | None = None) -> QFont:
        """Return a QFont for the given role.

        Args:
            role: Typography role name (display, h1, title, subtitle,
                body, caption, mono, stat). Unknown roles fall back to
                the body treatment.
            weight: Optional weight override (e.g. ``QFont.Bold``)
                applied on top of the role's default weight — for
                painters and widgets that need the role's family/size
                but a heavier or lighter stroke.
        """
        t = get_tokens()
        if role == "display":
            f = QFont(_DISPLAY, t.font_size_display, QFont.Black)
            f.setLetterSpacing(QFont.AbsoluteSpacing, -1.0)
        elif role == "h1":
            f = QFont(_DISPLAY, t.font_size_h1, QFont.Bold)
            f.setLetterSpacing(QFont.AbsoluteSpacing, -0.5)
        elif role == "title":
            f = QFont(_SANS, t.font_size_title, QFont.DemiBold)
        elif role == "subtitle":
            f = QFont(_SANS, t.font_size_subtitle, QFont.Bold)
        elif role == "caption":
            f = QFont(_SANS, t.font_size_caption, QFont.DemiBold)
            f.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
            f.setCapitalization(QFont.AllUppercase)
        elif role == "mono":
            f = QFont(_MONO, t.font_size_body, QFont.Normal)
        elif role == "stat":
            f = QFont(_DISPLAY, t.font_size_stat, QFont.Bold)
        else:  # "body" and unknown roles
            f = QFont(_SANS, t.font_size_body, QFont.Normal)
        if weight is not None:
            f.setWeight(QFont.Weight(weight))
        return f

    @classmethod
    def mono_caption(cls, bold: bool = False) -> QFont:
        """Mono family at caption size — painted chart/table captions.

        The shared replacement for the per-module ``_caption_font`` copies:
        no uppercase treatment (unlike the ``caption`` role), size read from
        tokens so theme switches keep tracking. ``bold=True`` uses DemiBold.
        """
        f = cls.font("mono")
        f.setPointSize(get_tokens().font_size_caption)
        if bold:
            f.setWeight(QFont.DemiBold)
        return f
