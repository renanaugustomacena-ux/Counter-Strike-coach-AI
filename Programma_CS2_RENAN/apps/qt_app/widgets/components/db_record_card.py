"""DbRecordCard — raised card showing a DB row (frame 17 right panel).

Anatomy: bold title + mono SQL caption + key/value mono grid. A row's
value can carry a semantic token name ("success", "info", …) to tint
it — e.g. matches_analyzed rendered green.
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography


class DbRecordCard(QFrame):
    """Database-record card: title, SQL caption, key/value mono grid."""

    def __init__(self, title: str = "", sql: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dashboard_card")  # inherit raised-card chrome
        tokens = get_tokens()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        layout.setSpacing(tokens.spacing_sm)

        self._title_label = QLabel(title)
        self._title_label.setFont(Typography.font("body", QFont.Bold))
        layout.addWidget(self._title_label)

        self._sql_label = QLabel(sql)
        self._sql_label.setObjectName("db_record_sql")
        self._sql_label.setWordWrap(True)
        layout.addWidget(self._sql_label)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, tokens.spacing_xs, 0, 0)
        self._grid.setHorizontalSpacing(tokens.spacing_xl)
        self._grid.setVerticalSpacing(tokens.spacing_xs)
        self._grid.setColumnStretch(1, 1)
        layout.addWidget(self._grid_host)
        layout.addStretch()

    def set_rows(self, rows: list[tuple[str, str, str | None]]) -> None:
        """Replace the grid with (key, value, token_name | None) rows."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        tokens = get_tokens()
        for row_idx, (key, value, token_name) in enumerate(rows):
            key_label = QLabel(key)
            key_label.setObjectName("db_record_key")
            self._grid.addWidget(key_label, row_idx, 0)

            value_label = QLabel(value)
            value_label.setObjectName("db_record_value")
            color = getattr(tokens, token_name, None) if token_name else None
            if color:
                # Color-only inline override; QSS keeps family/size/weight.
                value_label.setStyleSheet(f"color: {color}; background: transparent;")
            self._grid.addWidget(value_label, row_idx, 1)
