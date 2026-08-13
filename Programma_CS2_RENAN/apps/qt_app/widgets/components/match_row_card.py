"""MatchRowCard — wide horizontal row for the Match History list (frame 08).

Row anatomy:

    [ 1.34      PRO?   de_mirage | 2026-04-22 21:14
      Good             K/D: 1.26 | ADR: 82.3 | Kills: 24.0 Deaths: 19.0
                       KAST 78% · HS% 52 · clutch 2/3 · demo 312 MB      ]

Pro rows insert the player into the title (``de_mirage | ZywOo | …``) and
swap line 3 for the event line (``Vitality vs NAVI · ESL Pro League ·
16-11 CT``) when the payload carries event fields — otherwise they fall
back to the personal stat line. Every optional stat renders "—" when its
key is absent (the ViewModel documents the FIELD-GAPs).

Click anywhere on the row → ``clicked(demo_name)``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.match_utils import extract_map_name
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import rating_color, rating_label
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.components.pro_badge import ProBadge


def _fmt_match_datetime(value: Any) -> str:
    """``2026-04-22 21:14`` from a datetime or ISO string; "—" otherwise."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value or "—"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return "—"


def _pct(value: Any) -> str:
    """0..1 fraction → "78%"; absent → "—"."""
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.0f}%"
    except (TypeError, ValueError):
        return "—"


class MatchRowCard(QFrame):
    """Single-row match entry: rating block, PRO badge, three text lines."""

    clicked = Signal(str)  # demo_name

    def __init__(self, match: dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("dashboard_card")
        self.setProperty("depth", "raised")
        self.setCursor(Qt.PointingHandCursor)

        self._demo_name = str(match.get("demo_name", ""))
        is_pro = bool(match.get("is_pro", False))

        tokens = get_tokens()

        layout = QHBoxLayout(self)
        # The #dashboard_card QSS already pads spacing_lg on every side —
        # zero layout margins keep the row at frame-08 density (~84px).
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens.spacing_lg)

        # ── Rating block: stat-size number + label caption beneath ──
        rating_value = float(match.get("rating") or 0.0)
        color = rating_color(rating_value).name()

        rating_col = QVBoxLayout()
        rating_col.setContentsMargins(0, 0, 0, 0)
        rating_col.setSpacing(0)

        rating_number = QLabel(f"{rating_value:.2f}")
        rating_number.setFont(Typography.font("stat"))
        rating_number.setStyleSheet(f"color: {color}; background: transparent;")
        rating_number.setAlignment(Qt.AlignHCenter)
        rating_col.addWidget(rating_number)

        rating_tag = QLabel(rating_label(rating_value))
        rating_tag.setFont(Typography.font("body"))
        rating_tag.setStyleSheet(
            f"color: {color}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        rating_tag.setAlignment(Qt.AlignHCenter)
        rating_col.addWidget(rating_tag)

        rating_block = QWidget()
        rating_block.setLayout(rating_col)
        rating_block.setFixedWidth(84)
        layout.addWidget(rating_block, 0, Qt.AlignVCenter)

        # ── PRO badge (pro rows only) ──
        if is_pro:
            layout.addWidget(ProBadge(), 0, Qt.AlignVCenter)

        # ── Text column: title / stats / mono detail line ──
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        title = QLabel(self._title_text(match, is_pro))
        title.setFont(Typography.font("body", weight=700))
        title.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        text_col.addWidget(title)

        stats = QLabel(self._stats_text(match))
        stats.setFont(Typography.font("body"))
        stats.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        text_col.addWidget(stats)

        detail = QLabel(self._detail_text(match, is_pro))
        detail.setFont(Typography.font("mono"))
        detail.setStyleSheet(
            f"color: {tokens.info}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        text_col.addWidget(detail)

        layout.addLayout(text_col, 1)

    # ── Line composition ──

    @staticmethod
    def _title_text(match: dict[str, Any], is_pro: bool) -> str:
        map_name = extract_map_name(str(match.get("demo_name", "")))
        when = _fmt_match_datetime(match.get("match_date"))
        if is_pro:
            player = str(match.get("player_name") or "").strip()
            if player:
                return f"{map_name} | {player} | {when}"
        return f"{map_name} | {when}"

    @staticmethod
    def _stats_text(match: dict[str, Any]) -> str:
        kd = float(match.get("kd_ratio") or 0.0)
        adr = float(match.get("avg_adr") or 0.0)
        kills = float(match.get("avg_kills") or 0.0)
        deaths = float(match.get("avg_deaths") or 0.0)
        kd_word = i18n.get_text("stat_kd", "K/D")
        adr_word = i18n.get_text("stat_adr", "ADR")
        kills_word = i18n.get_text("history.kills", "Kills")
        deaths_word = i18n.get_text("history.deaths", "Deaths")
        return (
            f"{kd_word}: {kd:.2f} | {adr_word}: {adr:.1f} | "
            f"{kills_word}: {kills:.1f} {deaths_word}: {deaths:.1f}"
        )

    @staticmethod
    def _detail_text(match: dict[str, Any], is_pro: bool) -> str:
        if is_pro:
            event_bits = [
                str(match[key])
                for key in ("pro_teams", "pro_event", "pro_score")
                if match.get(key)
            ]
            if event_bits:
                return " · ".join(event_bits)
            # FIELD-GAP: no pro event columns in PlayerMatchStats — fall
            # through to the personal stat line, which pro rows also carry.

        kast_word = i18n.get_text("history.kast", "KAST")
        hs_word = i18n.get_text("history.hs_pct", "HS%")
        clutch_word = i18n.get_text("history.clutch", "clutch")
        demo_word = i18n.get_text("history.demo", "demo")

        kast = _pct(match.get("avg_kast"))
        hs = _pct(match.get("avg_hs")).rstrip("%")  # frame form: "HS% 52"

        won = match.get("clutches_won")
        total = match.get("clutches_total")
        if won is not None and total is not None:
            clutch = f"{int(won)}/{int(total)}"
        else:
            # FIELD-GAP: clutch counts absent — pct fallback from
            # clutch_win_pct, or "—" when that is missing too.
            clutch = _pct(match.get("clutch_win_pct"))

        size_mb = match.get("demo_size_mb")
        if size_mb is not None:
            demo = f"{float(size_mb):.0f} MB"
        else:
            demo = "—"  # FIELD-GAP: demo file size not recorded at ingest.

        return (
            f"{kast_word} {kast} · {hs_word} {hs} · "
            f"{clutch_word} {clutch} · {demo_word} {demo}"
        )

    # ── API ──

    def demo_name(self) -> str:
        return self._demo_name

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._demo_name:
            self.clicked.emit(self._demo_name)
        super().mousePressEvent(event)
