"""MapTile — per-map performance tile for the frame-12 grid.

Sunken rounded tile: bold map name, rating line tinted by
``theme_engine.rating_color`` with its accessibility label
(``Rating: 1.22 (Good)``), an ``ADR: n K/D: n`` line, an ``n matches``
caption, and a bottom 4px progress bar filled ``min(rating / 1.5, 1.0)``
in the rating color.

Fully QPainter-drawn so every color re-reads ``get_tokens()`` (and the
live-token rating helpers) on paint — the tile repaints correctly after
a theme switch with no restyle pass.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color, rating_label
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography

_FILL_CAP = 1.5  # rating that reads as a full bar
_BAR_H = 4.0


def _small_font() -> QFont:
    """Body family at caption size (lowercase metadata, sizes from tokens)."""
    font = Typography.font("body")
    font.setPointSize(get_tokens().font_size_caption)
    return font


class MapTile(QFrame):
    """Per-map performance tile (frame 12): name, rating, ADR/KD, matches, bar."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._map_name: str = ""
        self._rating: float = 0.0
        self._adr: float = 0.0
        self._kd: float = 0.0
        self._matches: int = 0
        # 4 text lines + paddings + the 4px bar: 112 made the matches
        # caption collide with the bar at current token font sizes.
        self.setMinimumSize(150, 132)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def set_data(
        self, map_name: str, rating: float, adr: float, kd: float, matches: int
    ) -> None:
        self._map_name = str(map_name)
        self._rating = float(rating)
        self._adr = float(adr)
        self._kd = float(kd)
        self._matches = int(matches)
        self.update()

    def _fill_frac(self) -> float:
        return min(max(self._rating, 0.0) / _FILL_CAP, 1.0)

    def paintEvent(self, event):  # noqa: ARG002 — Qt signature
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        tokens = get_tokens()

        # Sunken tile panel.
        panel = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QColor(tokens.border_default))
        painter.setBrush(QColor(tokens.surface_sunken))
        painter.drawRoundedRect(panel, tokens.radius_md, tokens.radius_md)

        pad = float(tokens.spacing_md)
        x = panel.left() + pad
        width = panel.width() - 2 * pad
        y = panel.top() + pad
        r_color = rating_color(self._rating)

        # Map name.
        name_font = Typography.font("subtitle")
        painter.setFont(name_font)
        painter.setPen(QColor(tokens.text_primary))
        name_h = QFontMetricsF(name_font).height()
        painter.drawText(QRectF(x, y, width, name_h), Qt.AlignLeft, self._map_name)
        y += name_h + 4.0

        # Rating line, rating-colored + accessible label.
        rating_font = Typography.font("body", QFont.Bold)
        painter.setFont(rating_font)
        painter.setPen(r_color)
        line_h = QFontMetricsF(rating_font).height()
        rating_word = i18n.get_text("map_tile_rating", "Rating")
        painter.drawText(
            QRectF(x, y, width, line_h), Qt.AlignLeft,
            f"{rating_word}: {self._rating:.2f} ({rating_label(self._rating)})",
        )
        y += line_h + 4.0

        # ADR / KD line.
        small = _small_font()
        painter.setFont(small)
        painter.setPen(QColor(tokens.text_secondary))
        small_h = QFontMetricsF(small).height()
        adr_word = i18n.get_text("stat_adr", "ADR")
        kd_word = i18n.get_text("stat_kd", "K/D")
        painter.drawText(
            QRectF(x, y, width, small_h), Qt.AlignLeft,
            f"{adr_word}: {self._adr:g} {kd_word}: {self._kd:.2f}",
        )
        y += small_h + 4.0

        # Matches caption.
        painter.setPen(QColor(tokens.text_tertiary))
        painter.drawText(
            QRectF(x, y, width, small_h), Qt.AlignLeft,
            f"{self._matches} {i18n.get_text('map_tile_matches', 'matches')}",
        )

        # Bottom 4px progress bar: track + rating-colored fill.
        bar_y = panel.bottom() - pad - _BAR_H
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(tokens.surface_base))
        painter.drawRoundedRect(QRectF(x, bar_y, width, _BAR_H), 2, 2)
        fill_w = width * self._fill_frac()
        if fill_w > 1:
            painter.setBrush(r_color)
            painter.drawRoundedRect(QRectF(x, bar_y, fill_w, _BAR_H), 2, 2)
