"""Pro Player Comparison Screen — side-by-side stats for Pro vs Pro or User vs Pro."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.viewmodels.pro_comparison_vm import (
    COMPARISON_METRICS,
    ProComparisonViewModel,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_pro_comparison")


class ProComparisonScreen(QWidget):
    """Compare two pro players or yourself against a pro player."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm = ProComparisonViewModel()
        self._vm.players_loaded.connect(self._on_players_loaded)
        self._vm.comparison_ready.connect(self._on_comparison)
        self._vm.error_changed.connect(self._on_error)

        self._mode = "pro_vs_pro"  # or "me_vs_pro"
        self._players = []

        self._build_ui()

    def on_enter(self):
        self._vm.load_pro_list()

    def retranslate(self):
        self._title.setText("Pro Player Comparison")

    # ── UI Construction ──

    def _build_ui(self):
        tokens = get_tokens()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Title
        self._title = QLabel("Pro Player Comparison")
        self._title.setFont(QFont("Roboto", 20, QFont.Bold))
        layout.addWidget(self._title)

        # Mode selector
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)

        self._btn_pro_vs_pro = QPushButton("Pro vs Pro")
        self._btn_pro_vs_pro.setCheckable(True)
        self._btn_pro_vs_pro.setChecked(True)
        self._btn_pro_vs_pro.setCursor(Qt.PointingHandCursor)
        self._btn_pro_vs_pro.clicked.connect(lambda: self._set_mode("pro_vs_pro"))
        mode_row.addWidget(self._btn_pro_vs_pro)

        self._btn_me_vs_pro = QPushButton("Me vs Pro")
        self._btn_me_vs_pro.setCheckable(True)
        self._btn_me_vs_pro.setCursor(Qt.PointingHandCursor)
        self._btn_me_vs_pro.clicked.connect(lambda: self._set_mode("me_vs_pro"))
        mode_row.addWidget(self._btn_me_vs_pro)

        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Player selectors
        selector_card = Card(title="Select Players")
        sel_layout = selector_card.layout()

        sel_row = QHBoxLayout()
        sel_row.setSpacing(12)

        # Player A
        self._label_a = QLabel("Player A:")
        self._label_a.setFont(QFont("Roboto", 12))
        sel_row.addWidget(self._label_a)

        self._combo_a = QComboBox()
        self._combo_a.setMinimumWidth(200)
        self._combo_a.setEditable(True)
        self._combo_a.setInsertPolicy(QComboBox.NoInsert)
        sel_row.addWidget(self._combo_a)

        # Player B
        self._label_b = QLabel("Player B:")
        self._label_b.setFont(QFont("Roboto", 12))
        sel_row.addWidget(self._label_b)

        self._combo_b = QComboBox()
        self._combo_b.setMinimumWidth(200)
        self._combo_b.setEditable(True)
        self._combo_b.setInsertPolicy(QComboBox.NoInsert)
        sel_row.addWidget(self._combo_b)

        # Compare button
        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setFixedHeight(36)
        self._compare_btn.setMinimumWidth(120)
        self._compare_btn.setCursor(Qt.PointingHandCursor)
        self._compare_btn.clicked.connect(self._on_compare)
        sel_row.addWidget(self._compare_btn)

        sel_row.addStretch()
        sel_layout.addLayout(sel_row)
        layout.addWidget(selector_card)

        # Status / error
        self._status = QLabel("")
        self._status.setStyleSheet("color: #a0a0b0; font-size: 13px;")
        self._status.setVisible(False)
        layout.addWidget(self._status)

        # Results area (scrollable)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._results = QWidget()
        self._results_layout = QVBoxLayout(self._results)
        self._results_layout.setSpacing(8)
        self._results_layout.addStretch()
        self._scroll.setWidget(self._results)
        self._scroll.setVisible(False)
        layout.addWidget(self._scroll, 1)

    # ── Mode switching ──

    def _set_mode(self, mode: str):
        self._mode = mode
        self._btn_pro_vs_pro.setChecked(mode == "pro_vs_pro")
        self._btn_me_vs_pro.setChecked(mode == "me_vs_pro")

        if mode == "pro_vs_pro":
            self._label_a.setText("Player A:")
            self._combo_a.setVisible(True)
            self._label_b.setText("Player B:")
        else:
            self._label_a.setVisible(False)
            self._combo_a.setVisible(False)
            self._label_b.setText("Compare against:")

        # Clear results
        self._scroll.setVisible(False)
        self._status.setVisible(False)

    # ── Events ──

    def _on_players_loaded(self, players: list):
        self._players = players
        self._combo_a.clear()
        self._combo_b.clear()
        for p in players:
            rank = p.get("team_rank", 0)
            rank_prefix = f"#{rank} " if rank and rank < 999 else ""
            label = f"{p['nickname']} ({rank_prefix}{p['team']})"
            self._combo_a.addItem(label, p["hltv_id"])
            self._combo_b.addItem(label, p["hltv_id"])

        # Pre-select different players
        if len(players) >= 2:
            self._combo_b.setCurrentIndex(1)

        self._status.setText(f"{len(players)} pro players loaded")
        self._status.setVisible(True)

    def _on_compare(self):
        if self._mode == "pro_vs_pro":
            id_a = self._combo_a.currentData()
            id_b = self._combo_b.currentData()
            if id_a is not None and id_b is not None:
                self._status.setText("Comparing...")
                self._status.setVisible(True)
                self._vm.compare_pros(id_a, id_b)
        else:
            id_b = self._combo_b.currentData()
            if id_b is not None:
                self._status.setText("Comparing...")
                self._status.setVisible(True)
                self._vm.compare_user_vs_pro(id_b)

    def _on_comparison(self, stats_a: dict, stats_b: dict, name_a: str, name_b: str):
        self._status.setVisible(False)
        self._scroll.setVisible(True)
        self._clear_results()

        tokens = get_tokens()
        no_data_a = not stats_a or all(v == 0 for v in stats_a.values())

        # Header
        header_card = Card(title=f"{name_a}  vs  {name_b}")
        if no_data_a and self._mode == "me_vs_pro":
            info = QLabel("You don't have personal match data yet. "
                          "Import and analyze your demos to see your stats here.")
            info.setWordWrap(True)
            info.setStyleSheet("color: #d96600; font-size: 12px; font-style: italic;")
            header_card.layout().addWidget(info)
        self._results_layout.insertWidget(0, header_card)

        # Stats grid
        grid_card = Card(title="Statistics")
        grid = QGridLayout()
        grid.setSpacing(6)

        # Column headers
        grid.addWidget(self._header_label("Metric"), 0, 0)
        grid.addWidget(self._header_label(name_a), 0, 1)
        grid.addWidget(self._header_label(name_b), 0, 2)

        for row_idx, (field, display_name, lower_is_better) in enumerate(COMPARISON_METRICS, start=1):
            val_a = stats_a.get(field, 0.0)
            val_b = stats_b.get(field, 0.0)

            # Metric name
            name_lbl = QLabel(display_name)
            name_lbl.setFont(QFont("Roboto", 11))
            name_lbl.setStyleSheet("color: #c0c0c0;")
            grid.addWidget(name_lbl, row_idx, 0)

            # Format values
            if field == "maps_played" or field == "clutch_win_count":
                fmt_a = f"{int(val_a)}" if val_a else "—"
                fmt_b = f"{int(val_b)}" if val_b else "—"
            elif field in ("kast", "headshot_pct", "opening_duel_win_pct", "multikill_round_pct"):
                fmt_a = f"{val_a * 100:.1f}%" if val_a else "—"
                fmt_b = f"{val_b * 100:.1f}%" if val_b else "—"
            else:
                fmt_a = f"{val_a:.2f}" if val_a else "—"
                fmt_b = f"{val_b:.2f}" if val_b else "—"

            # Color: who's better?
            color_a, color_b = "#c0c0c0", "#c0c0c0"
            if val_a and val_b and val_a != val_b:
                threshold = max(abs(val_a), abs(val_b)) * 0.05
                diff = val_a - val_b
                if lower_is_better:
                    diff = -diff
                if diff > threshold:
                    color_a, color_b = "#4caf50", "#ff5555"
                elif diff < -threshold:
                    color_a, color_b = "#ff5555", "#4caf50"

            lbl_a = QLabel(fmt_a)
            lbl_a.setFont(QFont("Roboto", 11, QFont.Bold))
            lbl_a.setStyleSheet(f"color: {color_a};")
            lbl_a.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl_a, row_idx, 1)

            lbl_b = QLabel(fmt_b)
            lbl_b.setFont(QFont("Roboto", 11, QFont.Bold))
            lbl_b.setStyleSheet(f"color: {color_b};")
            lbl_b.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl_b, row_idx, 2)

        grid_card.layout().addLayout(grid)
        self._results_layout.insertWidget(1, grid_card)

    def _on_error(self, msg: str):
        self._status.setText(f"Error: {msg}")
        self._status.setStyleSheet("color: #ff5555; font-size: 13px;")
        self._status.setVisible(True)

    # ── Helpers ──

    def _header_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Roboto", 12, QFont.Bold))
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    def _clear_results(self):
        while self._results_layout.count() > 1:
            item = self._results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setVisible(False)
                w.setParent(None)
