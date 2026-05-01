"""FilterChip — toggleable pill chip used for list filters.

Companion to ``StatusChip`` (read-only status indicator). Tracks
checked/unchecked state and emits ``toggled(bool)`` on click. Optional
trailing count badge so a filter chip can read "Mirage  ·  12".

Usage:
    chip = FilterChip("All", checked=True, count=47)
    chip.toggled.connect(lambda checked: ...)
    chip.set_count(12)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography


class FilterChip(QFrame):
    """Pill chip with checked/unchecked toggle + optional count badge."""

    toggled = Signal(bool)  # checked state after toggle

    def __init__(
        self,
        label: str = "",
        checked: bool = False,
        count: int | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("filter_chip")
        self.setCursor(Qt.PointingHandCursor)
        # Lock vertical size — without this, the chip stretches to fill
        # any leftover vertical space when its host's stretchy children
        # (lists, empty states) consume less than the available height.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setFixedHeight(28)
        self._checked: bool = bool(checked)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setFont(Typography.font("body"))
        layout.addWidget(self._label)

        self._count_label = QLabel("")
        self._count_label.setFont(Typography.font("mono"))
        layout.addWidget(self._count_label)

        self.set_count(count)
        self.refresh_styling()

    # ── Public API ──

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool) -> None:
        if checked == self._checked:
            return
        self._checked = bool(checked)
        self.refresh_styling()

    def set_label(self, text: str) -> None:
        self._label.setText(text)

    def set_count(self, count: int | None) -> None:
        if count is None:
            self._count_label.setText("")
            self._count_label.setVisible(False)
        else:
            self._count_label.setText(f"·  {count}")
            self._count_label.setVisible(True)

    def refresh_styling(self) -> None:
        """Re-read tokens and repaint. Call after a theme change."""
        t = get_tokens()
        if self._checked:
            bg = t.accent_muted_25
            border = t.accent_primary
            text_color = t.accent_primary
            count_color = t.accent_primary
        else:
            bg = "transparent"
            border = t.border_default
            text_color = t.text_secondary
            count_color = t.text_tertiary
        self.setStyleSheet(
            f"QFrame#filter_chip {{ "
            f"background-color: {bg}; "
            f"border: 1px solid {border}; "
            f"border-radius: 14px; "
            f"}}"
            f"QFrame#filter_chip:hover {{ "
            f"border: 1px solid {t.accent_primary}; "
            f"}}"
        )
        self._label.setStyleSheet(
            f"color: {text_color}; background: transparent;"
        )
        self._count_label.setStyleSheet(
            f"color: {count_color}; background: transparent;"
        )

    # ── Internals ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self.refresh_styling()
            self.toggled.emit(self._checked)
        super().mousePressEvent(event)
