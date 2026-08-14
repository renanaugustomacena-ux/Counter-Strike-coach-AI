"""ProBadge — mono bold caption pill for pro-sourced rows (frame 33 tags).

Default look: accent outline + accent text (``QLabel#pro_badge`` in
``themes/base.qss.template``). Side variants recolor the pill per the
frame-33 tag row:

    badge.set_side("ct")   # cyan  — tokens.info
    badge.set_side("t")    # orange — tokens.chart_line_secondary
    badge.set_side(None)   # back to the accent default

All colors flow from the QSS template (token-substituted); this class
only owns the object name, the ``side`` property, and re-polishing.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget


class ProBadge(QLabel):
    """Pill-shaped mono badge — "PRO" by default, side-colorable.

    Args:
        text: Badge caption (caller passes localized/composed text;
            the conventional default is the untranslatable mark "PRO").
        side: Optional side variant — ``"ct"`` | ``"t"`` | ``None``.
        parent: Parent widget.
    """

    def __init__(
        self,
        text: str = "PRO",
        side: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(text, parent)
        self.setObjectName("pro_badge")
        self.setAlignment(Qt.AlignCenter)
        # Pill hugs its caption — never stretches to fill a layout cell.
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if side is not None:
            self.set_side(side)

    def set_side(self, side: str | None) -> None:
        """Apply a side variant ("ct" / "t") or reset to the accent default."""
        self.setProperty("side", side if side in ("ct", "t") else None)
        style = self.style()
        if style is not None:
            style.unpolish(self)
            style.polish(self)

    def side(self) -> str | None:
        """Return the current side variant (None = accent default)."""
        value = self.property("side")
        return value if value in ("ct", "t") else None
