"""Shared widget factories — keeps screen code declarative.

The QSS template (``themes/base.qss.template``) already defines visual
treatments for ``QPushButton[variant="primary|secondary|ghost|danger"]``;
this helper just wires the property and conventional ergonomics
(pointing-hand cursor, optional fixed width) so screens don't repeat
the same five lines for every button.
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QWidget

ButtonVariant = Literal["primary", "secondary", "ghost", "danger"]


def make_button(
    text: str,
    variant: ButtonVariant = "secondary",
    fixed_width: int | None = None,
    parent: QWidget | None = None,
) -> QPushButton:
    """Create a themed QPushButton.

    Args:
        text: Button label.
        variant: Visual treatment — primary (CTA), secondary (default
            outlined), ghost (text-only with hover bg), danger (destructive).
        fixed_width: Optional pixel width — useful in tight rows.
        parent: Optional parent widget.
    """
    btn = QPushButton(text, parent)
    btn.setProperty("variant", variant)
    btn.setCursor(Qt.PointingHandCursor)
    if fixed_width is not None:
        btn.setFixedWidth(fixed_width)
    style = btn.style()
    if style is not None:
        style.unpolish(btn)
        style.polish(btn)
    return btn
