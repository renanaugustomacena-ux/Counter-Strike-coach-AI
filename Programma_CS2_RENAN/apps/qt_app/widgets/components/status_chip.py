"""StatusChip — pill-shaped status indicator.

Replaces the ad-hoc ``<span style="color:X">●</span> Coach: Idle`` rich-text
patterns scattered across screens with a structured component that respects
the design-token palette.

Severity ↦ visual treatment:
    online    success token (green-ish)
    offline   error token (red)
    warning   warning token (yellow/orange)
    neutral   tertiary text (gray)

Usage:
    chip = StatusChip("Online", severity="online")
    chip.set_label("Connected")
    chip.set_severity("warning")
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens

Severity = Literal["online", "offline", "warning", "neutral"]


class StatusChip(QFrame):
    """Compact dot + label chip."""

    def __init__(
        self,
        label: str = "",
        severity: Severity = "neutral",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("status_chip")
        self._severity: Severity = severity

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 10, 3)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        layout.addWidget(self._dot)

        self._label = QLabel(label)
        layout.addWidget(self._label)

        self.refresh_styling()

    def set_label(self, text: str) -> None:
        self._label.setText(text)

    def set_severity(self, severity: Severity) -> None:
        self._severity = severity
        self.refresh_styling()

    def severity(self) -> Severity:
        return self._severity

    def refresh_styling(self) -> None:
        """Re-read tokens and restyle. Call after a theme change."""
        t = get_tokens()
        dot_color = {
            "online": t.success,
            "offline": t.error,
            "warning": t.warning,
            "neutral": t.text_tertiary,
        }[self._severity]
        text_color = t.text_secondary
        self.setStyleSheet(
            f"QFrame#status_chip {{ "
            f"background-color: transparent; "
            f"border-radius: {t.radius_sm}px; "
            f"}}"
        )
        self._dot.setStyleSheet(
            f"color: {dot_color}; background: transparent; font-size: 10px;"
        )
        self._label.setStyleSheet(
            f"color: {text_color}; background: transparent; "
            f"font-size: {t.font_size_body}px;"
        )
