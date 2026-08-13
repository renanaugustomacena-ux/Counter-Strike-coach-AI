"""Shared QPainter helpers for the tactical widgets (map + timeline)."""

from __future__ import annotations

from PySide6.QtGui import QColor


def with_alpha(color: QColor, alpha: int) -> QColor:
    """Return a copy of ``color`` with the given 0-255 alpha."""
    c = QColor(color)
    c.setAlpha(alpha)
    return c
