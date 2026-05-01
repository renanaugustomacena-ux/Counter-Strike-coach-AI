"""Pro Player Comparison — side-by-side stats, Pro vs Pro or Me vs Pro.

Composition:
    Title rail   Pro Comparison              [● N pros loaded]
    Mode chips   [Pro vs Pro] [Me vs Pro]
    Selectors    Player A: [combo]  Player B: [combo]   [Compare]
    Body         Header card (names + optional banner)
                 Stats card (3-column grid: metric / A / B with delta-tinted values)
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.viewmodels.pro_comparison_vm import (
    COMPARISON_METRICS,
    ProComparisonViewModel,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.filter_chip import FilterChip
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_pro_comparison")


def _format_value(field: str, value: float) -> str:
    if not value:
        return "—"
    if field in {"maps_played", "clutch_win_count"}:
        return f"{int(value)}"
    if field in {"kast", "headshot_pct", "opening_duel_win_pct", "multikill_round_pct"}:
        return f"{value * 100:.1f}%"
    return f"{value:.2f}"


class ProComparisonScreen(QWidget):
    """Compare two pros, or yourself against a pro."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._vm = ProComparisonViewModel()
        self._vm.players_loaded.connect(self._on_players_loaded)
        self._vm.comparison_ready.connect(self._on_comparison)
        self._vm.error_changed.connect(self._on_error)

        self._mode = "pro_vs_pro"
        self._players: list[dict] = []
        self._build_ui()

    def on_enter(self) -> None:
        self._vm.load_pro_list()

    def retranslate(self) -> None:
        self._title_label.setText("Pro Comparison")

    # ── UI Construction ──

    def _build_ui(self) -> None:
        tokens = get_tokens()

        root = QVBoxLayout(self)
        root.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        root.setSpacing(tokens.spacing_md)

        # Title rail
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        self._title_label = QLabel("Pro Comparison")
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)
        self._count_chip = StatusChip("Loading pros…", severity="neutral")
        title_row.addWidget(self._count_chip)
        root.addLayout(title_row)

        # Mode chips
        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 0, 0, 0)
        mode_row.setSpacing(tokens.spacing_sm)

        self._chip_p_vs_p = FilterChip("Pro vs Pro", checked=True)
        self._chip_p_vs_p.toggled.connect(lambda _c: self._set_mode("pro_vs_pro"))
        mode_row.addWidget(self._chip_p_vs_p)

        self._chip_m_vs_p = FilterChip("Me vs Pro", checked=False)
        self._chip_m_vs_p.toggled.connect(lambda _c: self._set_mode("me_vs_pro"))
        mode_row.addWidget(self._chip_m_vs_p)

        mode_row.addStretch(1)
        root.addLayout(mode_row)

        # Selector card
        selector_card = Card(title="Players", depth="raised")
        sel_body = selector_card.content_layout
        sel_body.setSpacing(tokens.spacing_md)

        sel_row = QHBoxLayout()
        sel_row.setContentsMargins(0, 0, 0, 0)
        sel_row.setSpacing(tokens.spacing_md)

        self._label_a = QLabel("Player A")
        self._label_a.setFont(Typography.font("body"))
        self._label_a.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        sel_row.addWidget(self._label_a)

        self._combo_a = QComboBox()
        self._combo_a.setMinimumWidth(220)
        self._combo_a.setEditable(True)
        self._combo_a.setInsertPolicy(QComboBox.NoInsert)
        sel_row.addWidget(self._combo_a)

        self._label_b = QLabel("Player B")
        self._label_b.setFont(Typography.font("body"))
        self._label_b.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        sel_row.addWidget(self._label_b)

        self._combo_b = QComboBox()
        self._combo_b.setMinimumWidth(220)
        self._combo_b.setEditable(True)
        self._combo_b.setInsertPolicy(QComboBox.NoInsert)
        sel_row.addWidget(self._combo_b)

        self._compare_btn = make_button("Compare", variant="primary", fixed_width=120)
        self._compare_btn.setFixedHeight(36)
        self._compare_btn.clicked.connect(self._on_compare)
        sel_row.addWidget(self._compare_btn)

        sel_row.addStretch(1)
        sel_body.addLayout(sel_row)
        root.addWidget(selector_card)

        # Body stack: empty / loading / error / results
        self._body_stack = QStackedWidget()
        root.addWidget(self._body_stack, 1)

        self._empty_state = EmptyState(
            icon_text="◌",
            title="Pick two players to compare",
            description=(
                "Choose pros above (or switch to 'Me vs Pro') and click "
                "Compare to see a side-by-side breakdown."
            ),
        )
        self._body_stack.addWidget(self._empty_state)

        self._error_state = EmptyState(
            icon_text="◎",
            title="Comparison failed",
            description="",
        )
        self._body_stack.addWidget(self._error_state)

        # Results — scrollable card column
        self._results_scroll = QScrollArea()
        self._results_scroll.setWidgetResizable(True)
        self._results_scroll.setFrameShape(QFrame.NoFrame)
        self._results = QWidget()
        self._results_layout = QVBoxLayout(self._results)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(tokens.spacing_lg)
        self._results_layout.addStretch(1)
        self._results_scroll.setWidget(self._results)
        self._body_stack.addWidget(self._results_scroll)

        self._page_empty = 0
        self._page_error = 1
        self._page_results = 2

    # ── Mode switching ──

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        self._chip_p_vs_p.set_checked(mode == "pro_vs_pro")
        self._chip_m_vs_p.set_checked(mode == "me_vs_pro")
        if mode == "pro_vs_pro":
            self._label_a.setText("Player A")
            self._label_a.setVisible(True)
            self._combo_a.setVisible(True)
            self._label_b.setText("Player B")
        else:
            self._label_a.setVisible(False)
            self._combo_a.setVisible(False)
            self._label_b.setText("Compare against")

        self._body_stack.setCurrentIndex(self._page_empty)

    # ── Data flow ──

    def _on_players_loaded(self, players: list) -> None:
        self._players = players
        self._combo_a.clear()
        self._combo_b.clear()
        for p in players:
            rank = p.get("team_rank", 0)
            rank_prefix = f"#{rank} " if rank and rank < 999 else ""
            label = f"{p['nickname']} ({rank_prefix}{p['team']})"
            self._combo_a.addItem(label, p["hltv_id"])
            self._combo_b.addItem(label, p["hltv_id"])
        if len(players) >= 2:
            self._combo_b.setCurrentIndex(1)

        self._count_chip.set_label(f"{len(players)} pros loaded")
        self._count_chip.set_severity("online" if players else "neutral")

    def _on_compare(self) -> None:
        self._body_stack.setCurrentIndex(self._page_empty)
        self._empty_state.set_title("Comparing…")
        self._empty_state.set_description("")

        if self._mode == "pro_vs_pro":
            id_a = self._combo_a.currentData()
            id_b = self._combo_b.currentData()
            if id_a is not None and id_b is not None:
                self._vm.compare_pros(id_a, id_b)
        else:
            id_b = self._combo_b.currentData()
            if id_b is not None:
                self._vm.compare_user_vs_pro(id_b)

    def _on_comparison(
        self, stats_a: dict, stats_b: dict, name_a: str, name_b: str
    ) -> None:
        tokens = get_tokens()
        self._clear_results()
        no_data_a = not stats_a or all((v or 0) == 0 for v in stats_a.values())

        # Header card with both names — use highlighted depth so it
        # reads as the focal element.
        header_card = Card(title=f"{name_a}  vs  {name_b}", depth="highlighted")
        if no_data_a and self._mode == "me_vs_pro":
            banner = QLabel(
                "You don't have personal match data yet. "
                "Import and analyze your demos to populate your side."
            )
            banner.setWordWrap(True)
            banner.setFont(Typography.font("body"))
            banner.setStyleSheet(
                f"color: {tokens.accent_primary}; "
                f"background: {tokens.accent_muted_15}; "
                f"border: 1px solid {tokens.accent_muted_30}; "
                f"border-radius: {tokens.radius_md}px; "
                f"padding: {tokens.spacing_md}px;"
            )
            header_card.content_layout.addWidget(banner)
        self._results_layout.insertWidget(
            self._results_layout.count() - 1, header_card
        )

        # Stats card with grid
        grid_card = Card(title="Statistics", depth="raised")
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(tokens.spacing_xs)

        # Column headers
        grid.addWidget(self._grid_header_label("Metric"), 0, 0)
        grid.addWidget(self._grid_header_label(name_a), 0, 1)
        grid.addWidget(self._grid_header_label(name_b), 0, 2)
        grid.addWidget(self._grid_header_label("Δ"), 0, 3)

        for row_idx, (field, display_name, lower_is_better) in enumerate(
            COMPARISON_METRICS, start=1
        ):
            val_a = float(stats_a.get(field, 0.0) or 0)
            val_b = float(stats_b.get(field, 0.0) or 0)
            fmt_a = _format_value(field, val_a)
            fmt_b = _format_value(field, val_b)

            # Color by who's better
            color_a, color_b = tokens.text_primary, tokens.text_primary
            delta_color = tokens.text_tertiary
            delta_text = "—"
            if val_a and val_b and val_a != val_b:
                threshold = max(abs(val_a), abs(val_b)) * 0.05
                diff = val_a - val_b
                if lower_is_better:
                    diff = -diff
                if diff > threshold:
                    color_a, color_b = tokens.success, tokens.error
                    delta_color = tokens.success
                    delta_text = "▲"
                elif diff < -threshold:
                    color_a, color_b = tokens.error, tokens.success
                    delta_color = tokens.error
                    delta_text = "▼"

            metric = QLabel(display_name)
            metric.setFont(Typography.font("body"))
            metric.setStyleSheet(
                f"color: {tokens.text_secondary}; background: transparent;"
            )
            grid.addWidget(metric, row_idx, 0)

            grid.addWidget(self._stat_cell(fmt_a, color_a), row_idx, 1)
            grid.addWidget(self._stat_cell(fmt_b, color_b), row_idx, 2)
            grid.addWidget(
                self._stat_cell(delta_text, delta_color, mono=False),
                row_idx,
                3,
            )

        grid_card.content_layout.addWidget(grid_widget)
        self._results_layout.insertWidget(
            self._results_layout.count() - 1, grid_card
        )

        self._body_stack.setCurrentIndex(self._page_results)

    def _on_error(self, msg: str) -> None:
        self._error_state.set_title("Comparison failed")
        self._error_state.set_description(str(msg))
        self._body_stack.setCurrentIndex(self._page_error)

    # ── Helpers ──

    def _grid_header_label(self, text: str) -> QLabel:
        tokens = get_tokens()
        lbl = QLabel(text.upper())
        Typography.apply(lbl, "caption")
        lbl.setAlignment(Qt.AlignCenter if text != "Metric" else Qt.AlignLeft)
        lbl.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent; "
            f"padding: {tokens.spacing_xs}px 0;"
        )
        return lbl

    def _stat_cell(self, text: str, color: str, mono: bool = True) -> QLabel:
        tokens = get_tokens()
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(Typography.font("mono") if mono else Typography.font("body"))
        lbl.setStyleSheet(
            f"color: {color}; background: transparent; "
            f"padding: {tokens.spacing_xs}px {tokens.spacing_md}px;"
        )
        return lbl

    def _clear_results(self) -> None:
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            w = item.widget() if item is not None else None
            if w is not None:
                w.setParent(None)
                w.deleteLater()
