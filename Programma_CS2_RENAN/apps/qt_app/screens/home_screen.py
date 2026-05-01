"""Home / Dashboard screen — premium analytics surface.

Composition:
    Title rail            Dashboard                              [● Status chip]
    Hero pair (50/50)     [Last Match]                           [Focus This Week]
    Recent matches strip  RECENT MATCHES — horizontal MatchMiniCards
    Utility row (3-col)   [Ingest] · [Training, hidden if idle] · [Tactical]

Cold-start branch (no user matches yet) replaces the hero pair + recent
strip with a single onboarding hero card, so the user never sees raw
"Not set" / empty placeholders. The utility row stays visible — Analyze
buttons remain reachable.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.apps.qt_app.viewmodels.focus_insight_vm import (
    FocusInsightViewModel,
)
from Programma_CS2_RENAN.apps.qt_app.viewmodels.match_history_vm import (
    MatchHistoryViewModel,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.focus_insight import (
    FocusInsightCard,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.last_match_hero import (
    LastMatchHeroCard,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.match_mini_card import (
    MatchMiniCard,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip
from Programma_CS2_RENAN.core.config import get_setting, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_home")


class HomeScreen(QWidget):
    """Dashboard with hero pair, recent matches, and utility cards."""

    # Wired in app.py to MatchDetailScreen.load_demo + window.switch_screen.
    match_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._connected = False
        self._ingestion_worker = None
        self._user_matches: list[dict[str, Any]] = []

        self._match_history_vm = MatchHistoryViewModel(self)
        self._focus_insight_vm = FocusInsightViewModel(self)

        self._build_ui()

        self._match_history_vm.matches_changed.connect(self._on_matches_changed)
        self._focus_insight_vm.insight_changed.connect(self._on_insight_changed)

    # ── Lifecycle ──

    def on_enter(self):
        """Refresh paths and connect signals when shown."""
        self._refresh_path_display()
        if not self._connected:
            state = get_app_state()
            state.service_active_changed.connect(self._on_service_active)
            state.coach_status_changed.connect(self._on_coach_status)
            state.parsing_progress_changed.connect(self._on_parsing_progress)
            state.training_changed.connect(self._on_training)
            state.total_matches_changed.connect(self._on_total_matches)
            self._connected = True

        prev = get_app_state().cached_state
        if "service_active" in prev:
            self._on_service_active(prev["service_active"])
        if prev.get("total_matches", 0) > 0:
            self._on_total_matches(prev["total_matches"])

        # Kick off async loads — both VMs marshal results back via signals.
        self._match_history_vm.load_matches()
        self._focus_insight_vm.load()

    # ── UI Construction ──

    def _build_ui(self):
        tokens = get_tokens()
        root = QVBoxLayout(self)
        root.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_lg
        )
        root.setSpacing(tokens.spacing_lg)

        # ── Title rail ──
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(tokens.spacing_md)

        self._title_label = QLabel(i18n.get_text("dashboard"))
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)

        self._service_chip = StatusChip("Service: Idle", severity="neutral")
        title_row.addWidget(self._service_chip)
        self._matches_chip = StatusChip("0 matches", severity="neutral")
        title_row.addWidget(self._matches_chip)

        root.addLayout(title_row)

        # ── Scrollable content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(tokens.spacing_lg)

        # ── Hero / onboarding stack (swaps based on data presence) ──
        self._hero_section = QWidget()
        self._hero_stack = QStackedLayout(self._hero_section)
        self._hero_stack.setContentsMargins(0, 0, 0, 0)

        # Page A: hero pair + recent strip
        hero_page = QWidget()
        hero_layout = QVBoxLayout(hero_page)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setSpacing(tokens.spacing_lg)

        hero_pair = QHBoxLayout()
        hero_pair.setContentsMargins(0, 0, 0, 0)
        hero_pair.setSpacing(tokens.spacing_lg)
        self._last_match_card = LastMatchHeroCard()
        self._last_match_card.analyze_clicked.connect(self._on_start_analysis)
        self._last_match_card.detail_clicked.connect(self._on_match_detail)
        hero_pair.addWidget(self._last_match_card, 1)

        self._focus_card = FocusInsightCard()
        self._focus_card.open_clicked.connect(self._on_focus_open)
        hero_pair.addWidget(self._focus_card, 1)
        hero_layout.addLayout(hero_pair)

        hero_layout.addWidget(self._build_recent_strip())

        self._hero_stack.addWidget(hero_page)

        # Page B: onboarding hero (cold start)
        self._onboarding_card = self._build_onboarding_card()
        self._hero_stack.addWidget(self._onboarding_card)

        content_layout.addWidget(self._hero_section)

        # ── Utility row (3-col): Ingest · Training (toggleable) · Tactical ──
        # Training is hidden by default; stretch is rebalanced in
        # ``_on_training`` so the slot doesn't leave a gap when idle.
        self._utility_row = QHBoxLayout()
        self._utility_row.setContentsMargins(0, 0, 0, 0)
        self._utility_row.setSpacing(tokens.spacing_lg)

        self._ingest_card = self._build_ingest_card()
        self._utility_row.addWidget(self._ingest_card, 3)

        self._training_card = self._build_training_card()
        self._utility_row.addWidget(self._training_card, 0)

        self._tactical_card = self._build_tactical_card()
        self._utility_row.addWidget(self._tactical_card, 1)

        content_layout.addLayout(self._utility_row)
        content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._show_onboarding(True)  # default until matches load

    def _build_recent_strip(self) -> QWidget:
        tokens = get_tokens()
        container = QFrame()
        container.setObjectName("dashboard_card")
        container.setProperty("depth", "flat")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_md, tokens.spacing_lg, tokens.spacing_md
        )
        layout.setSpacing(tokens.spacing_sm)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        caption = QLabel("RECENT MATCHES")
        Typography.apply(caption, "caption")
        caption.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        header_row.addWidget(caption)
        header_row.addStretch(1)
        view_all = make_button("View all →", variant="ghost")
        view_all.setFixedHeight(28)
        view_all.clicked.connect(lambda: self._navigate("match_history"))
        header_row.addWidget(view_all)
        layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(146)

        strip = QWidget()
        self._strip_layout = QHBoxLayout(strip)
        self._strip_layout.setContentsMargins(0, 0, 0, 0)
        self._strip_layout.setSpacing(tokens.spacing_md)
        self._strip_layout.addStretch(1)

        scroll.setWidget(strip)
        layout.addWidget(scroll)
        return container

    def _build_onboarding_card(self) -> QWidget:
        empty = EmptyState(
            icon_text="◎",
            title="Welcome to Macena CS2 Analyzer",
            description=(
                "Point the analyzer at a folder of .dem files to start "
                "building your personal coaching baseline. Once a few "
                "matches are processed, your last-match performance, "
                "focus area, and recent trend show up here."
            ),
            cta_text="Choose demo folder",
            secondary_cta_text="View match history",
        )
        empty.action_clicked.connect(self._pick_demo_folder)
        empty.secondary_action_clicked.connect(lambda: self._navigate("match_history"))
        return empty

    # ── Ingest card ──

    def _build_ingest_card(self) -> Card:
        tokens = get_tokens()
        card = Card(title="Ingest", depth="raised")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = card.content_layout
        layout.setSpacing(tokens.spacing_md)

        # Personal demos row
        self._personal_row, self._personal_path_label, self._personal_btn = (
            self._build_ingest_row(
                kind_caption="PERSONAL",
                button_text="Analyze",
                on_click=self._on_start_analysis,
                pick_action=self._pick_demo_folder,
            )
        )
        layout.addLayout(self._personal_row)

        # Personal status / progress
        self._parsing_bar = QProgressBar()
        self._parsing_bar.setRange(0, 100)
        self._parsing_bar.setValue(0)
        self._parsing_bar.setVisible(False)
        self._parsing_bar.setFixedHeight(6)
        layout.addWidget(self._parsing_bar)

        self._analyze_status = QLabel("")
        self._analyze_status.setFont(Typography.font("caption"))
        self._analyze_status.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent;"
        )
        layout.addWidget(self._analyze_status)

        # Pro demos row
        self._pro_row, self._pro_path_label, self._pro_btn = self._build_ingest_row(
            kind_caption="PRO BASELINE",
            button_text="Analyze pro",
            on_click=self._on_start_pro_analysis,
            pick_action=self._pick_pro_folder,
        )
        layout.addLayout(self._pro_row)

        self._pro_analyze_status = QLabel("")
        self._pro_analyze_status.setFont(Typography.font("caption"))
        self._pro_analyze_status.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent;"
        )
        layout.addWidget(self._pro_analyze_status)

        return card

    def _build_ingest_row(
        self,
        kind_caption: str,
        button_text: str,
        on_click,
        pick_action,
    ):
        tokens = get_tokens()
        row = QVBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)

        cap = QLabel(kind_caption)
        Typography.apply(cap, "caption")
        cap.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent;"
        )
        row.addWidget(cap)

        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.setSpacing(tokens.spacing_sm)

        path_label = QLabel("Not configured")
        path_label.setFont(Typography.font("mono"))
        path_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        path_label.setWordWrap(False)
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_row.addWidget(path_label, 1)

        change_btn = make_button("Change", variant="ghost")
        change_btn.setFixedHeight(26)
        change_btn.clicked.connect(pick_action)
        path_row.addWidget(change_btn)

        analyze_btn = make_button(button_text, variant="primary", fixed_width=120)
        analyze_btn.setFixedHeight(30)
        analyze_btn.clicked.connect(on_click)
        path_row.addWidget(analyze_btn)

        row.addLayout(path_row)
        return row, path_label, analyze_btn

    # ── Training card ──

    def _build_training_card(self) -> Card:
        tokens = get_tokens()
        card = Card(title="Training", depth="raised")
        card.setVisible(False)  # hidden until training is active
        layout = card.content_layout
        layout.setSpacing(tokens.spacing_xs)

        self._epoch_label = QLabel("Epoch — / —")
        self._epoch_label.setFont(Typography.font("title"))
        self._epoch_label.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        layout.addWidget(self._epoch_label)

        self._train_progress_bar = QProgressBar()
        self._train_progress_bar.setRange(0, 100)
        self._train_progress_bar.setValue(0)
        self._train_progress_bar.setFixedHeight(6)
        self._train_progress_bar.setTextVisible(False)
        layout.addWidget(self._train_progress_bar)

        self._train_loss_label = QLabel("Loss —")
        self._train_loss_label.setFont(Typography.font("mono"))
        self._train_loss_label.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        layout.addWidget(self._train_loss_label)

        self._eta_label = QLabel("ETA —")
        self._eta_label.setFont(Typography.font("mono"))
        self._eta_label.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent;"
        )
        layout.addWidget(self._eta_label)

        layout.addStretch(1)
        return card

    # ── Tactical card ──

    def _build_tactical_card(self) -> Card:
        tokens = get_tokens()
        card = Card(title="Tactical", depth="raised")
        layout = card.content_layout
        layout.setSpacing(tokens.spacing_md)

        desc = QLabel(
            i18n.get_text(
                "tactical_desc",
                "Replay any match in 2D with ghost-AI overlay, or compare "
                "your stats side-by-side with pros.",
            )
        )
        desc.setFont(Typography.font("body"))
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {tokens.text_secondary}; background: transparent;"
        )
        layout.addWidget(desc)

        layout.addStretch(1)

        button_col = QVBoxLayout()
        button_col.setSpacing(tokens.spacing_sm)
        viewer_btn = make_button("Open viewer", variant="primary")
        viewer_btn.setFixedHeight(30)
        viewer_btn.clicked.connect(lambda: self._navigate("tactical_viewer"))
        button_col.addWidget(viewer_btn)

        compare_btn = make_button("Compare pros", variant="secondary")
        compare_btn.setFixedHeight(30)
        compare_btn.clicked.connect(lambda: self._navigate("pro_comparison"))
        button_col.addWidget(compare_btn)

        layout.addLayout(button_col)
        return card

    # ── State helpers ──

    def _show_onboarding(self, show: bool) -> None:
        self._hero_stack.setCurrentIndex(1 if show else 0)

    def _refresh_path_display(self) -> None:
        demo_path = get_setting("DEFAULT_DEMO_PATH", "")
        pro_path = get_setting("PRO_DEMO_PATH", "")
        self._personal_path_label.setText(demo_path or "Not configured")
        self._pro_path_label.setText(pro_path or "Not configured")

    # ── i18n ──

    def retranslate(self) -> None:
        self._title_label.setText(i18n.get_text("dashboard"))
        # Card titles are static English right now; the pieces below
        # belong to i18n keys that already exist or will be added.
        # The new dashboard intentionally avoids dense translatable
        # copy — every translatable string flows through i18n.get_text
        # with a sensible English default so missing keys don't break.

    # ── Match history → dashboard data ──

    def _on_matches_changed(self, matches: list[dict[str, Any]]):
        # Filter to the current user's matches (drop pro-baseline rows).
        user_matches = [m for m in matches if not m.get("is_pro")]
        self._user_matches = user_matches

        if not user_matches:
            self._show_onboarding(True)
            self._matches_chip.set_label("0 matches")
            self._matches_chip.set_severity("neutral")
            return

        self._show_onboarding(False)

        last_match = user_matches[0]
        history_ratings = [
            float(m.get("rating") or 0.0)
            for m in reversed(user_matches[:10])
            if m.get("rating") is not None
        ]
        self._last_match_card.set_state(last_match, history_ratings)

        self._populate_recent_strip(user_matches[:6])
        self._matches_chip.set_label(f"{len(user_matches)} matches")
        self._matches_chip.set_severity("online")

    def _populate_recent_strip(self, matches: list[dict[str, Any]]) -> None:
        # Clear existing cards (leave the trailing stretch in place).
        while self._strip_layout.count() > 1:
            item = self._strip_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        # Insert new cards before the trailing stretch.
        for match in matches:
            card = MatchMiniCard(match)
            card.clicked.connect(self._on_match_detail)
            self._strip_layout.insertWidget(self._strip_layout.count() - 1, card)

    # ── Focus insight ──

    def _on_insight_changed(self, payload: dict) -> None:
        area = payload.get("area", "")
        body = payload.get("body", "")
        navigate_to = payload.get("navigate_to", "")
        if area:
            self._focus_card.set_insight(area, body, navigate_to)
        else:
            self._focus_card.set_empty()

    def _on_focus_open(self, screen_name: str) -> None:
        if screen_name:
            self._navigate(screen_name)

    # ── Navigation ──

    def _navigate(self, screen_name: str) -> None:
        win = self.window()
        if win and hasattr(win, "switch_screen"):
            win.switch_screen(screen_name)

    def _on_match_detail(self, demo_name: str) -> None:
        if demo_name:
            self.match_selected.emit(demo_name)

    # ── Folder pickers ──

    def _pick_demo_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Demo Folder")
        if folder:
            save_user_setting("DEFAULT_DEMO_PATH", folder)
            self._personal_path_label.setText(folder)
            logger.info("Demo folder set: %s", folder)

    def _pick_pro_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Pro Demo Folder")
        if folder:
            save_user_setting("PRO_DEMO_PATH", folder)
            self._pro_path_label.setText(folder)
            logger.info("Pro demo folder set: %s", folder)

    # ── Analysis flows ──

    def _on_start_analysis(self) -> None:
        if self._ingestion_worker is not None:
            return
        demo_path = get_setting("DEFAULT_DEMO_PATH", "")
        if not demo_path:
            tokens = get_tokens()
            self._analyze_status.setText("Set a demo folder first")
            self._analyze_status.setStyleSheet(
                f"color: {tokens.error}; background: transparent; "
                f"font-size: {tokens.font_size_caption}px;"
            )
            return
        self._set_analyze_busy(True, "Scanning for demos…", is_pro=False)

        def _run():
            from Programma_CS2_RENAN.run_ingestion import process_new_demos

            process_new_demos(is_pro=False)

        worker = Worker(_run)
        worker.signals.result.connect(lambda _: self._on_analysis_done(is_pro=False))
        worker.signals.error.connect(
            lambda err: self._on_analysis_error(err, is_pro=False)
        )
        self._ingestion_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_start_pro_analysis(self) -> None:
        if self._ingestion_worker is not None:
            return
        pro_path = get_setting("PRO_DEMO_PATH", "")
        if not pro_path:
            tokens = get_tokens()
            self._pro_analyze_status.setText("Set a pro demo folder first")
            self._pro_analyze_status.setStyleSheet(
                f"color: {tokens.error}; background: transparent; "
                f"font-size: {tokens.font_size_caption}px;"
            )
            return
        self._set_analyze_busy(True, "Scanning pro demos…", is_pro=True)

        def _run():
            from Programma_CS2_RENAN.run_ingestion import process_new_demos

            process_new_demos(is_pro=True)

        worker = Worker(_run)
        worker.signals.result.connect(lambda _: self._on_analysis_done(is_pro=True))
        worker.signals.error.connect(
            lambda err: self._on_analysis_error(err, is_pro=True)
        )
        self._ingestion_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _set_analyze_busy(self, busy: bool, message: str, is_pro: bool) -> None:
        tokens = get_tokens()
        self._personal_btn.setEnabled(not busy)
        self._pro_btn.setEnabled(not busy)
        if busy:
            target = self._pro_btn if is_pro else self._personal_btn
            target.setText("Analyzing…")
            status = self._pro_analyze_status if is_pro else self._analyze_status
            status.setText(message)
            status.setStyleSheet(
                f"color: {tokens.warning}; background: transparent; "
                f"font-size: {tokens.font_size_caption}px;"
            )

    def _on_analysis_done(self, is_pro: bool) -> None:
        self._ingestion_worker = None
        tokens = get_tokens()
        self._personal_btn.setEnabled(True)
        self._pro_btn.setEnabled(True)
        if is_pro:
            self._pro_btn.setText("Analyze pro")
            status = self._pro_analyze_status
        else:
            self._personal_btn.setText("Analyze")
            status = self._analyze_status
        status.setText("Analysis complete")
        status.setStyleSheet(
            f"color: {tokens.success}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        get_app_state().notification_received.emit(
            "INFO",
            (
                "Pro demo analysis complete"
                if is_pro
                else "Demo analysis complete — check Match History for results"
            ),
        )
        # Re-fetch matches so the dashboard updates with newly analyzed data.
        self._match_history_vm.load_matches()
        self._focus_insight_vm.load()

    def _on_analysis_error(self, error: Any, is_pro: bool) -> None:
        self._ingestion_worker = None
        tokens = get_tokens()
        self._personal_btn.setEnabled(True)
        self._pro_btn.setEnabled(True)
        if is_pro:
            self._pro_btn.setText("Analyze pro")
            status = self._pro_analyze_status
        else:
            self._personal_btn.setText("Analyze")
            status = self._analyze_status
        status.setText(f"Error: {error}")
        status.setStyleSheet(
            f"color: {tokens.error}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        logger.error(
            "Home %s analysis failed: %s", "pro" if is_pro else "personal", error
        )
        get_app_state().notification_received.emit(
            "ERROR",
            f"{'Pro analysis' if is_pro else 'Demo analysis'} failed: {error}",
        )

    # ── Signal slots ──

    def _on_service_active(self, active: bool) -> None:
        self._service_chip.set_label("Service: Online" if active else "Service: Offline")
        self._service_chip.set_severity("online" if active else "offline")

    def _on_coach_status(self, status: str) -> None:
        # Coach status is folded into the service chip when transient.
        # Idle/Online stays as-is; anything else swaps in the live state.
        if not status or status.strip().lower() == "idle":
            return
        self._service_chip.set_label(f"Coach: {status}")
        self._service_chip.set_severity("warning")

    def _on_parsing_progress(self, progress: float) -> None:
        if 0 < progress < 100:
            self._parsing_bar.setValue(int(progress))
            self._parsing_bar.setVisible(True)
        else:
            self._parsing_bar.setVisible(False)

    def _on_training(self, data: dict) -> None:
        epoch = int(data.get("current_epoch", 0))
        total = int(data.get("total_epochs", 0))
        active = total > 0
        self._training_card.setVisible(active)
        # Rebalance utility row: when training is hidden the slot's
        # stretch goes to 0 so Ingest absorbs its share; when active,
        # restore 2:1:1 (Ingest : Training : Tactical).
        self._utility_row.setStretchFactor(self._ingest_card, 2 if active else 3)
        self._utility_row.setStretchFactor(self._training_card, 1 if active else 0)
        self._utility_row.setStretchFactor(self._tactical_card, 1)
        if not active:
            return
        self._epoch_label.setText(f"Epoch {epoch} / {total}")
        pct = int((epoch / total) * 100) if total > 0 else 0
        self._train_progress_bar.setValue(max(0, min(100, pct)))
        train_loss = float(data.get("train_loss", 0.0))
        val_loss = float(data.get("val_loss", 0.0))
        self._train_loss_label.setText(
            f"Loss {train_loss:.4f}  ·  Val {val_loss:.4f}"
        )
        self._eta_label.setText(f"ETA {self._format_eta(data.get('eta_seconds', 0))}")

    def _on_total_matches(self, count: int) -> None:
        self._matches_chip.set_label(f"{count} matches")
        if count > 0:
            self._matches_chip.set_severity("online")

    @staticmethod
    def _format_eta(seconds: float) -> str:
        if seconds <= 0:
            return "—"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m"
        return f"{m}m {s}s"
