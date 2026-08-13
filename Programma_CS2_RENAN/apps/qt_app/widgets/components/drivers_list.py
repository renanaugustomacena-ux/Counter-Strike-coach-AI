"""DriversList — severity-squared driver rows (frame 06 "Drivers:").

Each row = an 8px semantic-colored square + body text, e.g.
``(success, "Sample count · 47 personal demos analyzed")``.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import severity_color

# The vocabulary this widget colors via theme_engine.severity_color;
# anything else (including "") keeps the tertiary neutral square.
_KNOWN_SEVERITIES = frozenset({"success", "warning", "error", "info"})


class DriversList(QWidget):
    """Vertical list of (severity, text) driver rows.

    Severity ∈ {"success", "warning", "error", "info"} — anything else
    falls back to tertiary text color.
    """

    def __init__(self, rows: list[tuple[str, str]] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(get_tokens().spacing_sm)
        if rows:
            self.set_rows(rows)

    def set_rows(self, rows: list[tuple[str, str]]) -> None:
        """Replace all rows with (severity, text) tuples."""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        tokens = get_tokens()
        for severity, text in rows:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(tokens.spacing_sm)

            color = (
                severity_color(severity).name()
                if severity in _KNOWN_SEVERITIES
                else tokens.text_tertiary
            )
            square = QFrame()
            square.setObjectName("drivers_square")
            square.setFixedSize(8, 8)
            square.setStyleSheet(
                f"background-color: {color}; "
                f"border-radius: 1px;"
            )
            row_layout.addWidget(square, alignment=Qt.AlignVCenter)

            label = QLabel(text)
            label.setObjectName("drivers_text")
            label.setWordWrap(True)
            row_layout.addWidget(label, 1)
            self._layout.addWidget(row)
