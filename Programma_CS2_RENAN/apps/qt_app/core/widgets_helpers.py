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


def navigate_to(widget: QWidget, screen_name: str) -> None:
    """Switch the MainWindow to ``screen_name`` from any child widget.

    The standard screen `_navigate` copy: resolve the top-level window and
    call its ``switch_screen`` when present (no-op under tests/harness
    where the widget may be parentless).
    """
    win = widget.window()
    if win and hasattr(win, "switch_screen"):
        win.switch_screen(screen_name)
