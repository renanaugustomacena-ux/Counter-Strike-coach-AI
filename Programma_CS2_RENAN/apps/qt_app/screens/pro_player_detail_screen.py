"""Pro Player Detail — drill-down screen for a single HLTV pro.

Composition:
    Title rail        ← Back        Nickname (Real name)        [team rank chip]
    Header card       Country flag · Team · Age · Time span chip
    Stats grid card   12-metric grid (Rating 2.0, KPR, DPR, ADR, KAST, HS%, Impact,
                      Opening duels, Opening kills, Clutch wins, Multikill %, Maps played)
    Recent matches    last-N panel sourced from detailed_stats_json["matches"] when present

Reached from ProComparisonScreen via "Details" buttons on the two combos.
The MainWindow registers this screen by name "pro_player_detail" and the
caller invokes window.switch_screen("pro_player_detail") after calling
detail.load_pro(hltv_id).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.viewmodels.pro_player_detail_vm import ProPlayerDetailViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_pro_player_detail")

# (db_field, display_name, format_kind, lower_is_better)
# format_kind: 'percent' formats as N.N%, 'int' as integer, default float to 2 dp.
_DETAIL_METRICS = [
    ("rating_2_0", "Rating 2.0", "float", False),
    ("kpr", "Kills / Round", "float", False),
    ("dpr", "Deaths / Round", "float", True),
    ("adr", "Damage / Round", "float", False),
    ("kast", "KAST", "percent", False),
    ("headshot_pct", "Headshot %", "percent", False),
    ("impact", "Impact", "float", False),
    ("opening_duel_win_pct", "Opening Duel Win %", "percent", False),
    ("opening_kill_ratio", "Opening Kill Ratio", "float", False),
    ("clutch_win_count", "Clutch Wins", "int", False),
    ("multikill_round_pct", "Multikill Round %", "percent", False),
    ("maps_played", "Maps Played", "int", False),
]


def _format_metric(value, kind: str) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if kind == "percent":
        return f"{v * 100:.1f}%" if v <= 1.5 else f"{v:.1f}%"
    if kind == "int":
        return f"{int(v)}"
    return f"{v:.2f}"


class ProPlayerDetailScreen(QWidget):
    """Single-pro drill-down. Loads on demand via load_pro(hltv_id)."""

    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._vm = ProPlayerDetailViewModel()
        self._vm.profile_loaded.connect(self._on_profile)
        self._vm.error_changed.connect(self._on_error)
        self._build_ui()
        # Empty until load_pro() is called.
        self._show_empty()

    # ── Public API ──

    def load_pro(self, hltv_id: int) -> None:
        """Trigger background fetch + show loading state."""
        self._show_loading()
        self._vm.load_pro(int(hltv_id))

    def on_enter(self) -> None:
        # No automatic re-fetch on re-enter — caller decides what pro
        # to load. Reusing the cached profile is the right default.
        pass

    def retranslate(self) -> None:
        self._title_label.setText("Pro Player")

    # ── UI ──

    def _build_ui(self) -> None:
        tokens = get_tokens()

        root = QVBoxLayout(self)
        root.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        root.setSpacing(tokens.spacing_md)

        # Title rail with Back button + status chip.
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)

        self._back_btn = make_button("← Back", variant="secondary", fixed_width=100)
        self._back_btn.setFixedHeight(32)
        self._back_btn.clicked.connect(self.back_requested.emit)
        title_row.addWidget(self._back_btn)

        self._title_label = QLabel("Pro Player")
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)

        self._rank_chip = StatusChip("—", severity="neutral")
        title_row.addWidget(self._rank_chip)
        root.addLayout(title_row)

        # Scrollable content area (header + stats + matches).
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(tokens.spacing_lg)

        # Header card (real name, country, team, age, time span).
        self._header_card = Card(title="—", subtitle="", depth="raised")
        header_body = self._header_card.content_layout
        self._header_real_name = QLabel("—")
        self._header_real_name.setFont(Typography.font("body"))
        self._header_real_name.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        header_body.addWidget(self._header_real_name)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(tokens.spacing_md)
        self._header_country = QLabel("Country: —")
        self._header_team = QLabel("Team: —")
        self._header_age = QLabel("Age: —")
        self._header_time_span = QLabel("Time span: —")
        for lbl in (
            self._header_country,
            self._header_team,
            self._header_age,
            self._header_time_span,
        ):
            lbl.setFont(Typography.font("caption"))
            lbl.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")
            meta_row.addWidget(lbl)
        meta_row.addStretch(1)
        header_body.addLayout(meta_row)
        self._content_layout.addWidget(self._header_card)

        # Stats grid card.
        self._stats_card = Card(title="Performance Stats", depth="raised")
        self._stats_grid = QGridLayout()
        self._stats_grid.setContentsMargins(0, 0, 0, 0)
        self._stats_grid.setHorizontalSpacing(tokens.spacing_lg)
        self._stats_grid.setVerticalSpacing(tokens.spacing_sm)
        self._stat_value_labels: dict[str, QLabel] = {}
        for i, (field, name, _kind, _lib) in enumerate(_DETAIL_METRICS):
            row = i // 2
            col = (i % 2) * 2
            name_lbl = QLabel(name)
            name_lbl.setFont(Typography.font("body"))
            name_lbl.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
            value_lbl = QLabel("—")
            value_lbl.setFont(Typography.font("body"))
            value_lbl.setStyleSheet(
                f"color: {tokens.text_primary}; background: transparent; " f"font-weight: 600;"
            )
            value_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._stats_grid.addWidget(name_lbl, row, col)
            self._stats_grid.addWidget(value_lbl, row, col + 1)
            self._stat_value_labels[field] = value_lbl
        self._stats_card.content_layout.addLayout(self._stats_grid)
        self._content_layout.addWidget(self._stats_card)

        # Recent matches panel (populated from detailed_stats_json["matches"]).
        self._matches_card = Card(title="Recent Matches", depth="raised")
        self._matches_container_layout = self._matches_card.content_layout
        self._matches_empty = EmptyState(
            icon_text="◌",
            title="No recent matches",
            description="HLTV match history not yet scraped for this player.",
        )
        self._matches_container_layout.addWidget(self._matches_empty)
        self._content_layout.addWidget(self._matches_card)

        # Loading / error overlay (uses EmptyState as a single
        # status-message surface that swaps in/out).
        self._status_state = EmptyState(
            icon_text="◌",
            title="Loading…",
            description="",
        )
        self._content_layout.addWidget(self._status_state)

        self._content_layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    # ── State helpers ──

    def _show_empty(self) -> None:
        self._header_card.setVisible(False)
        self._stats_card.setVisible(False)
        self._matches_card.setVisible(False)
        self._status_state.setVisible(True)
        self._status_state.set_title("No pro selected")
        self._status_state.set_description("Pick a pro from the comparison screen.")

    def _show_loading(self) -> None:
        self._header_card.setVisible(False)
        self._stats_card.setVisible(False)
        self._matches_card.setVisible(False)
        self._status_state.setVisible(True)
        self._status_state.set_title("Loading…")
        self._status_state.set_description("")

    def _on_error(self, msg: str) -> None:
        self._header_card.setVisible(False)
        self._stats_card.setVisible(False)
        self._matches_card.setVisible(False)
        self._status_state.setVisible(True)
        self._status_state.set_title("Failed to load")
        self._status_state.set_description(str(msg))

    def _on_profile(self, profile: dict) -> None:
        """Bind the loaded profile dict to the UI surfaces."""
        self._status_state.setVisible(False)
        self._header_card.setVisible(True)
        self._stats_card.setVisible(True)
        self._matches_card.setVisible(True)

        # Title rail.
        nickname = profile.get("nickname") or "—"
        real_name = profile.get("real_name") or ""
        title = nickname if not real_name else f"{nickname}  ({real_name})"
        self._header_card.set_title(title)
        # Real name secondary line if present.
        if real_name:
            self._header_real_name.setText(real_name)
            self._header_real_name.setVisible(True)
        else:
            self._header_real_name.setVisible(False)

        team_name = profile.get("team_name") or "—"
        team_rank = profile.get("team_rank")
        rank_label = f"#{team_rank}" if team_rank and team_rank < 999 else "Unranked"
        self._rank_chip.set_label(f"{team_name} · {rank_label}")
        self._rank_chip.set_severity("online" if team_rank and team_rank <= 30 else "neutral")

        country = profile.get("country") or "—"
        self._header_country.setText(f"Country: {country}")
        self._header_team.setText(f"Team: {team_name}")
        age = profile.get("age")
        self._header_age.setText(f"Age: {age}" if age else "Age: —")
        time_span = (profile.get("stat_card") or {}).get("time_span", "n/a")
        self._header_time_span.setText(f"Time span: {time_span}")

        # Stats grid.
        sc = profile.get("stat_card") or {}
        for field, _name, kind, _lib in _DETAIL_METRICS:
            lbl = self._stat_value_labels.get(field)
            if lbl is None:
                continue
            lbl.setText(_format_metric(sc.get(field), kind))

        # Recent matches list (last 10 from detailed_stats_json).
        self._populate_recent_matches(profile)

    def _populate_recent_matches(self, profile: dict) -> None:
        tokens = get_tokens()
        # Clear prior children except the empty-state placeholder.
        for i in reversed(range(self._matches_container_layout.count())):
            item = self._matches_container_layout.itemAt(i)
            widget = item.widget() if item is not None else None
            if widget is not None and widget is not self._matches_empty:
                widget.setParent(None)
                widget.deleteLater()

        matches = ((profile.get("detailed") or {}).get("matches")) or []
        if not matches:
            self._matches_empty.setVisible(True)
            return
        self._matches_empty.setVisible(False)

        for m in matches[:10]:
            row = QFrame()
            row.setStyleSheet(
                f"QFrame {{ "
                f"background-color: {tokens.surface_card}; "
                f"border: 1px solid {tokens.border_subtle}; "
                f"border-radius: 6px; "
                f"padding: 6px 10px; "
                f"}}"
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            date_lbl = QLabel(str(m.get("date", "—")))
            date_lbl.setFont(Typography.font("caption"))
            date_lbl.setStyleSheet(f"color: {tokens.text_tertiary}; background: transparent;")
            opp_lbl = QLabel(f"vs {m.get('opponent', '—')}  ·  {m.get('map', '—')}")
            opp_lbl.setFont(Typography.font("body"))
            opp_lbl.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
            rating = m.get("rating", 0.0)
            try:
                rating_str = f"R {float(rating):.2f}"
            except (TypeError, ValueError):
                rating_str = "R —"
            rating_lbl = QLabel(rating_str)
            rating_lbl.setFont(Typography.font("body"))
            rating_lbl.setStyleSheet(
                f"color: {tokens.text_secondary}; background: transparent; " f"font-weight: 600;"
            )
            rating_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row_layout.addWidget(date_lbl)
            row_layout.addSpacing(12)
            row_layout.addWidget(opp_lbl, 1)
            row_layout.addWidget(rating_lbl)

            self._matches_container_layout.addWidget(row)
