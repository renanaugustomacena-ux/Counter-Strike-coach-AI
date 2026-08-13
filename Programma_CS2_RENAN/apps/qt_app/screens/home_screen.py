"""Home / Dashboard screen — frame 05 composition.

Composition (top→bottom):
    Title rail            Dashboard
    Status strip card     [● Coach: Idle] [● Service: Online] [● Matches: 47]
    Hero pair (50/50)     [Last Match]         [Focus This Week]
    Recent matches strip  RECENT MATCHES — horizontal MatchMiniCards
    Demo Analysis         path chip · Select/Analyze · status caption
    Pro Demo Ingestion    path chip · Select/Analyze · status caption
    Connectivity          [Profile] [Steam Config] [FaceIt Config]
    Tactical Analysis     [Open Tactical Viewer] [Compare Pro Players]
    Training Status       highlighted card, visible only while training

The hero pair + recent strip are richer than frame 05 and kept per
Locked Decision 9. Cold-start branch (no user matches yet) replaces the
hero pair + recent strip with a single onboarding hero card, so the user
never sees raw "Not set" / empty placeholders. The frame card stack
stays visible — Analyze buttons remain reachable.
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
from Programma_CS2_RENAN.apps.qt_app.viewmodels.focus_insight_vm import FocusInsightViewModel
from Programma_CS2_RENAN.apps.qt_app.viewmodels.match_history_vm import MatchHistoryViewModel
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.empty_state import EmptyState
from Programma_CS2_RENAN.apps.qt_app.widgets.components.focus_insight import FocusInsightCard
from Programma_CS2_RENAN.apps.qt_app.widgets.components.last_match_hero import LastMatchHeroCard
from Programma_CS2_RENAN.apps.qt_app.widgets.components.match_mini_card import MatchMiniCard
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mono_footer import MonoFooter
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip
from Programma_CS2_RENAN.core.config import get_setting, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_home")


class HomeScreen(QWidget):
    """Dashboard per frame 05 — status strip, hero pair, five-card stack."""

    # Wired in app.py to MatchDetailScreen.load_demo + window.switch_screen.
    match_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._connected = False
        self._ingestion_worker = None
        self._user_matches: list[dict[str, Any]] = []
        # Tracks whether _on_matches_changed has populated the matches chip;
        # gates _on_total_matches from clobbering the row-derived count.
        self._matches_chip_populated = False
        # Last-known dynamic state, kept so retranslate() can recompose
        # every composed label without waiting for the next signal.
        self._coach_status_raw = ""
        self._service_state: bool | None = None
        self._matches_count: int | None = None
        self._pro_demos_count: int | None = None
        self._training_data: dict[str, Any] = {}

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
        root.setSpacing(tokens.spacing_md)

        # ── Title rail ──
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(tokens.spacing_md)

        self._title_label = QLabel(i18n.get_text("dashboard"))
        Typography.apply(self._title_label, "h1")
        title_row.addWidget(self._title_label)
        title_row.addStretch(1)
        root.addLayout(title_row)

        # ── Status strip card (frame 05: Coach / Service / Matches) ──
        root.addWidget(self._build_status_strip())

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

        # ── Frame-05 card stack ──
        self._demo_card = self._build_demo_analysis_card()
        content_layout.addWidget(self._demo_card)

        self._pro_card = self._build_pro_ingestion_card()
        content_layout.addWidget(self._pro_card)

        self._connectivity_card = self._build_connectivity_card()
        content_layout.addWidget(self._connectivity_card)

        self._tactical_card = self._build_tactical_card()
        content_layout.addWidget(self._tactical_card)

        self._training_card = self._build_training_card()
        content_layout.addWidget(self._training_card)

        content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._show_onboarding(True)  # default until matches load

    def _build_status_strip(self) -> QWidget:
        tokens = get_tokens()
        strip = QFrame()
        strip.setObjectName("dashboard_card")
        strip.setProperty("depth", "flat")
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_xs, tokens.spacing_lg, tokens.spacing_xs
        )
        layout.setSpacing(tokens.spacing_xxl)

        self._coach_chip = StatusChip(self._coach_chip_text(), severity="neutral")
        layout.addWidget(self._coach_chip)

        self._service_chip = StatusChip(self._service_chip_text(), severity="neutral")
        layout.addWidget(self._service_chip)

        # Placeholder until matches_changed or total_matches signal arrives.
        # Hardcoding "0" misled users when pro rows existed but no personal
        # demos had been ingested yet.
        self._matches_chip = StatusChip("…", severity="neutral")
        layout.addWidget(self._matches_chip)

        layout.addStretch(1)
        return strip

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
        caption.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
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

    # ── Frame-05 card builders ──

    def _build_path_row(self) -> tuple[QHBoxLayout, QLabel, QLabel]:
        """`Path:` caption + mono path chip on a sunken rounded frame."""
        tokens = get_tokens()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_sm)

        cap = QLabel(f"{i18n.get_text('home.path', 'Path')}:")
        cap.setFont(Typography.font("body"))
        cap.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        row.addWidget(cap)

        chip = QFrame()
        chip.setObjectName("path_chip")
        chip.setStyleSheet(
            f"QFrame#path_chip {{ "
            f"background-color: {tokens.surface_sunken}; "
            f"border-radius: {tokens.radius_sm}px; "
            f"}}"
        )
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(tokens.spacing_sm, 2, tokens.spacing_sm, 2)
        chip_layout.setSpacing(0)

        path_label = QLabel(i18n.get_text("home.not_configured", "Not configured"))
        Typography.apply(path_label, "mono")
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        chip_layout.addWidget(path_label)

        row.addWidget(chip)
        row.addStretch(1)
        return row, path_label, cap

    def _build_action_row(
        self,
        select_cb,
        analyze_text: str,
        analyze_cb,
    ) -> tuple[QHBoxLayout, Any, Any, QLabel]:
        """[Select Demo Folder] [Analyze …] + mono status caption."""
        tokens = get_tokens()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_md)

        select_btn = make_button(
            i18n.get_text("select_demo_folder", "Select Demo Folder"), variant="secondary"
        )
        select_btn.setFixedHeight(32)
        select_btn.clicked.connect(select_cb)
        row.addWidget(select_btn)

        analyze_btn = make_button(analyze_text, variant="primary")
        analyze_btn.setFixedHeight(32)
        analyze_btn.clicked.connect(analyze_cb)
        row.addWidget(analyze_btn)

        status = QLabel("")
        status.setFont(Typography.font("mono"))
        status.setStyleSheet(
            f"color: {tokens.text_tertiary}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        row.addWidget(status)
        row.addStretch(1)
        return row, select_btn, analyze_btn, status

    def _build_demo_analysis_card(self) -> Card:
        tokens = get_tokens()
        card = Card(
            title=i18n.get_text("demo_analysis", "Demo Analysis"),
            subtitle=i18n.get_text(
                "home.demo_analysis_desc",
                "Analyze .dem files from your configured folder and feed "
                "them to the coaching pipeline.",
            ),
            depth="raised",
        )
        layout = card.content_layout
        layout.setSpacing(tokens.spacing_md)

        path_row, self._personal_path_label, self._personal_path_cap = self._build_path_row()
        layout.addLayout(path_row)

        (
            action_row,
            self._personal_select_btn,
            self._personal_btn,
            self._analyze_status,
        ) = self._build_action_row(
            select_cb=self._pick_demo_folder,
            analyze_text=i18n.get_text("home.analyze_demos", "Analyze Demos"),
            analyze_cb=self._on_start_analysis,
        )
        layout.addLayout(action_row)

        self._parsing_bar = QProgressBar()
        self._parsing_bar.setRange(0, 100)
        self._parsing_bar.setValue(0)
        self._parsing_bar.setVisible(False)
        self._parsing_bar.setFixedHeight(6)
        self._parsing_bar.setTextVisible(False)
        layout.addWidget(self._parsing_bar)

        return card

    def _build_pro_ingestion_card(self) -> Card:
        tokens = get_tokens()
        card = Card(
            title=i18n.get_text("pro_demo_ingestion", "Pro Demo Ingestion"),
            subtitle=i18n.get_text(
                "home.pro_ingestion_desc",
                "Ingest pro player demos to build the reference baseline "
                "for the JEPA model and chat coach.",
            ),
            depth="raised",
        )
        layout = card.content_layout
        layout.setSpacing(tokens.spacing_md)

        path_row, self._pro_path_label, self._pro_path_cap = self._build_path_row()
        layout.addLayout(path_row)

        (
            action_row,
            self._pro_select_btn,
            self._pro_btn,
            self._pro_analyze_status,
        ) = self._build_action_row(
            select_cb=self._pick_pro_folder,
            analyze_text=i18n.get_text("home.analyze_pro_demos", "Analyze Pro Demos"),
            analyze_cb=self._on_start_pro_analysis,
        )
        layout.addLayout(action_row)

        return card

    def _build_connectivity_card(self) -> Card:
        tokens = get_tokens()
        card = Card(
            title=i18n.get_text("home.connectivity", "Connectivity"),
            depth="raised",
        )
        layout = card.content_layout
        layout.setSpacing(tokens.spacing_md)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_md)

        self._profile_btn = make_button(
            i18n.get_text("home.btn_profile", "Profile"), variant="secondary"
        )
        self._profile_btn.setFixedHeight(32)
        self._profile_btn.clicked.connect(lambda: self._navigate("profile"))
        row.addWidget(self._profile_btn)

        self._steam_btn = make_button(
            i18n.get_text("steam_config", "Steam Config"), variant="secondary"
        )
        self._steam_btn.setFixedHeight(32)
        self._steam_btn.clicked.connect(lambda: self._navigate("steam_config"))
        row.addWidget(self._steam_btn)

        self._faceit_btn = make_button(
            i18n.get_text("faceit_config", "FaceIt Config"), variant="secondary"
        )
        self._faceit_btn.setFixedHeight(32)
        self._faceit_btn.clicked.connect(lambda: self._navigate("faceit_config"))
        row.addWidget(self._faceit_btn)

        row.addStretch(1)
        layout.addLayout(row)
        return card

    def _build_tactical_card(self) -> Card:
        tokens = get_tokens()
        card = Card(
            title=i18n.get_text("home.tactical_analysis", "Tactical Analysis"),
            subtitle=i18n.get_text(
                "home.tactical_desc",
                "Open the 2D tactical viewer for round-by-round replay, "
                "or compare any pro player's stats.",
            ),
            depth="raised",
        )
        layout = card.content_layout
        layout.setSpacing(tokens.spacing_md)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(tokens.spacing_md)

        self._viewer_btn = make_button(
            i18n.get_text("open_tactical_viewer", "Open Tactical Viewer"), variant="secondary"
        )
        self._viewer_btn.setFixedHeight(32)
        self._viewer_btn.clicked.connect(lambda: self._navigate("tactical_viewer"))
        row.addWidget(self._viewer_btn)

        self._compare_btn = make_button(
            i18n.get_text("home.compare_pro_players", "Compare Pro Players"), variant="secondary"
        )
        self._compare_btn.setFixedHeight(32)
        self._compare_btn.clicked.connect(lambda: self._navigate("pro_comparison"))
        row.addWidget(self._compare_btn)

        row.addStretch(1)
        layout.addLayout(row)
        return card

    # ── Training card ──

    def _build_training_card(self) -> Card:
        tokens = get_tokens()
        card = Card(
            title=i18n.get_text("training_status", "Training Status"),
            depth="highlighted",
        )
        card.setVisible(False)  # hidden until training is active
        layout = card.content_layout
        layout.setSpacing(tokens.spacing_sm)

        self._epoch_label = QLabel(f"{i18n.get_text('home.epoch', 'Epoch')}: — / —")
        self._epoch_label.setFont(Typography.font("body"))
        self._epoch_label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        layout.addWidget(self._epoch_label)

        self._train_progress_bar = QProgressBar()
        self._train_progress_bar.setRange(0, 100)
        self._train_progress_bar.setValue(0)
        self._train_progress_bar.setFixedHeight(6)
        self._train_progress_bar.setTextVisible(False)
        layout.addWidget(self._train_progress_bar)

        loss_row = QHBoxLayout()
        loss_row.setContentsMargins(0, 0, 0, 0)
        loss_row.setSpacing(tokens.spacing_xxl)

        self._train_loss_label = QLabel(f"{i18n.get_text('home.train_loss', 'Train Loss')}: —")
        self._train_loss_label.setFont(Typography.font("body"))
        self._train_loss_label.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        loss_row.addWidget(self._train_loss_label)

        self._val_loss_label = QLabel(f"{i18n.get_text('home.val_loss', 'Val Loss')}: —")
        self._val_loss_label.setFont(Typography.font("body"))
        self._val_loss_label.setStyleSheet(
            f"color: {tokens.text_primary}; background: transparent;"
        )
        loss_row.addWidget(self._val_loss_label)

        self._eta_label = QLabel(f"{i18n.get_text('home.eta', 'ETA')}: —")
        self._eta_label.setFont(Typography.font("body"))
        self._eta_label.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
        loss_row.addWidget(self._eta_label)

        loss_row.addStretch(1)
        layout.addLayout(loss_row)

        # Static source annotation; batch progress appended defensively in
        # _on_training when the payload carries batch fields.
        self._training_footer = MonoFooter(self._training_footer_text())
        layout.addWidget(self._training_footer)

        return card

    # ── State helpers ──

    def _show_onboarding(self, show: bool) -> None:
        self._hero_stack.setCurrentIndex(1 if show else 0)

    def _refresh_path_display(self) -> None:
        demo_path = get_setting("DEFAULT_DEMO_PATH", "")
        pro_path = get_setting("PRO_DEMO_PATH", "")
        not_configured = i18n.get_text("home.not_configured", "Not configured")
        self._personal_path_label.setText(demo_path or not_configured)
        self._pro_path_label.setText(pro_path or not_configured)

    # ── Composed label helpers (single source for build + retranslate) ──

    def _coach_chip_text(self) -> str:
        prefix = i18n.get_text("home.chip_coach", "Coach")
        status = self._coach_status_raw.strip()
        if not status or status.lower() == "idle":
            status = i18n.get_text("home.coach_idle", "Idle")
        return f"{prefix}: {status}"

    def _service_chip_text(self) -> str:
        prefix = i18n.get_text("home.chip_service", "Service")
        if self._service_state is None:
            return f"{prefix}: —"
        if self._service_state:
            return f"{prefix}: {i18n.get_text('home.service_online', 'Online')}"
        return f"{prefix}: {i18n.get_text('home.service_offline', 'Offline')}"

    def _matches_chip_text(self) -> str:
        prefix = i18n.get_text("home.chip_matches", "Matches")
        if self._matches_count is None:
            return "…"
        return f"{prefix}: {self._matches_count}"

    def _personal_status_text(self) -> str:
        if self._matches_count is None:
            return ""
        ready = i18n.get_text("home.status_ready", "Ready")
        analyzed = i18n.get_text("home.analyzed", "analyzed")
        pending = i18n.get_text("home.pending", "pending")
        # FIELD-GAP: no signal carries a pending-demos count (the folder scan
        # lives inside run_ingestion) — render "—" until one exists.
        return f"{ready} — {self._matches_count} {analyzed} · — {pending}"

    def _pro_status_text(self) -> str:
        if self._pro_demos_count is None:
            return ""
        indexed = i18n.get_text("home.indexed", "indexed")
        last_sync = i18n.get_text("home.last_sync", "last sync")
        # FIELD-GAP: no last-sync timestamp signal for the pro corpus —
        # render "—" until the ingestion service exposes one.
        return f"{self._pro_demos_count} {indexed} · {last_sync} —"

    def _training_footer_text(self) -> str:
        static = i18n.get_text("home.training_footer", "teacher daemon · jepa_train.py")
        batch = self._training_data.get("batch")
        total_batches = self._training_data.get("total_batches")
        if batch is not None and total_batches is not None:
            return f"{static} · batch {batch}/{total_batches}"
        return static

    # ── i18n ──

    def retranslate(self) -> None:
        self._title_label.setText(i18n.get_text("dashboard"))
        # Status strip
        self._coach_chip.set_label(self._coach_chip_text())
        self._service_chip.set_label(self._service_chip_text())
        self._matches_chip.set_label(self._matches_chip_text())
        # Demo Analysis card
        self._demo_card.set_title(i18n.get_text("demo_analysis", "Demo Analysis"))
        self._demo_card.set_subtitle(
            i18n.get_text(
                "home.demo_analysis_desc",
                "Analyze .dem files from your configured folder and feed "
                "them to the coaching pipeline.",
            )
        )
        self._personal_path_cap.setText(f"{i18n.get_text('home.path', 'Path')}:")
        self._personal_select_btn.setText(i18n.get_text("select_demo_folder", "Select Demo Folder"))
        self._personal_btn.setText(i18n.get_text("home.analyze_demos", "Analyze Demos"))
        # Pro ingestion card
        self._pro_card.set_title(i18n.get_text("pro_demo_ingestion", "Pro Demo Ingestion"))
        self._pro_card.set_subtitle(
            i18n.get_text(
                "home.pro_ingestion_desc",
                "Ingest pro player demos to build the reference baseline "
                "for the JEPA model and chat coach.",
            )
        )
        self._pro_path_cap.setText(f"{i18n.get_text('home.path', 'Path')}:")
        self._pro_select_btn.setText(i18n.get_text("select_demo_folder", "Select Demo Folder"))
        self._pro_btn.setText(i18n.get_text("home.analyze_pro_demos", "Analyze Pro Demos"))
        # Connectivity card
        self._connectivity_card.set_title(i18n.get_text("home.connectivity", "Connectivity"))
        self._profile_btn.setText(i18n.get_text("home.btn_profile", "Profile"))
        self._steam_btn.setText(i18n.get_text("steam_config", "Steam Config"))
        self._faceit_btn.setText(i18n.get_text("faceit_config", "FaceIt Config"))
        # Tactical card
        self._tactical_card.set_title(i18n.get_text("home.tactical_analysis", "Tactical Analysis"))
        self._tactical_card.set_subtitle(
            i18n.get_text(
                "home.tactical_desc",
                "Open the 2D tactical viewer for round-by-round replay, "
                "or compare any pro player's stats.",
            )
        )
        self._viewer_btn.setText(i18n.get_text("open_tactical_viewer", "Open Tactical Viewer"))
        self._compare_btn.setText(
            i18n.get_text("home.compare_pro_players", "Compare Pro Players")
        )
        # Training card
        self._training_card.set_title(i18n.get_text("training_status", "Training Status"))
        self._training_footer.setText(self._training_footer_text())
        if self._training_data:
            self._apply_training_labels(self._training_data)
        # Paths + status captions (recomposed from stored state)
        self._refresh_path_display()
        if self._ingestion_worker is None:
            if self._matches_count is not None:
                self._analyze_status.setText(self._personal_status_text())
            if self._pro_demos_count is not None:
                self._pro_analyze_status.setText(self._pro_status_text())

    # ── Match history → dashboard data ──

    def _on_matches_changed(self, matches: list[dict[str, Any]]):
        # Filter to the current user's matches (drop pro-baseline rows).
        user_matches = [m for m in matches if not m.get("is_pro")]
        self._user_matches = user_matches

        # Distinct pro demos = unique demo_name across is_pro rows.
        # PlayerMatchStats stores one row per (demo, player), so the row count
        # would inflate by the number of players analyzed per demo (~10×).
        # FIELD-GAP: no corpus-size signal exists for the pro library — the
        # distinct count over the loaded rows (≤50) is the available proxy.
        pro_demos = {m["demo_name"] for m in matches if m.get("is_pro") and m.get("demo_name")}
        self._update_matches_chip(len(user_matches), len(pro_demos))

        if not user_matches:
            self._show_onboarding(True)
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

    def _update_matches_chip(self, user_n: int, pro_demos_n: int) -> None:
        self._matches_count = user_n
        self._pro_demos_count = pro_demos_n
        self._matches_chip.set_label(self._matches_chip_text())
        self._matches_chip.set_severity("online" if user_n > 0 else "neutral")
        self._matches_chip_populated = True
        # Refresh the card status captions — skip while an analysis worker
        # is running so busy/progress text isn't clobbered mid-flight.
        if self._ingestion_worker is None:
            tokens = get_tokens()
            for label, text in (
                (self._analyze_status, self._personal_status_text()),
                (self._pro_analyze_status, self._pro_status_text()),
            ):
                label.setText(text)
                label.setStyleSheet(
                    f"color: {tokens.text_tertiary}; background: transparent; "
                    f"font-size: {tokens.font_size_caption}px;"
                )

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
        folder = QFileDialog.getExistingDirectory(
            self, i18n.get_text("select_demo_folder", "Select Demo Folder")
        )
        if folder:
            save_user_setting("DEFAULT_DEMO_PATH", folder)
            self._personal_path_label.setText(folder)
            logger.info("Demo folder set: %s", folder)

    def _pick_pro_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, i18n.get_text("select_demo_folder", "Select Demo Folder")
        )
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
            self._analyze_status.setText(
                i18n.get_text("home.set_folder_first", "Set a demo folder first")
            )
            self._analyze_status.setStyleSheet(
                f"color: {tokens.error}; background: transparent; "
                f"font-size: {tokens.font_size_caption}px;"
            )
            return
        self._set_analyze_busy(
            True, i18n.get_text("home.scanning", "Scanning for demos…"), is_pro=False
        )

        def _run():
            from Programma_CS2_RENAN.run_ingestion import process_new_demos

            process_new_demos(is_pro=False)

        worker = Worker(_run)
        worker.signals.result.connect(lambda _: self._on_analysis_done(is_pro=False))
        worker.signals.error.connect(lambda err: self._on_analysis_error(err, is_pro=False))
        self._ingestion_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_start_pro_analysis(self) -> None:
        if self._ingestion_worker is not None:
            return
        pro_path = get_setting("PRO_DEMO_PATH", "")
        if not pro_path:
            tokens = get_tokens()
            self._pro_analyze_status.setText(
                i18n.get_text("home.set_pro_folder_first", "Set a pro demo folder first")
            )
            self._pro_analyze_status.setStyleSheet(
                f"color: {tokens.error}; background: transparent; "
                f"font-size: {tokens.font_size_caption}px;"
            )
            return
        self._set_analyze_busy(
            True, i18n.get_text("home.scanning_pro", "Scanning pro demos…"), is_pro=True
        )

        def _run():
            from Programma_CS2_RENAN.run_ingestion import process_new_demos

            process_new_demos(is_pro=True)

        worker = Worker(_run)
        worker.signals.result.connect(lambda _: self._on_analysis_done(is_pro=True))
        worker.signals.error.connect(lambda err: self._on_analysis_error(err, is_pro=True))
        self._ingestion_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _set_analyze_busy(self, busy: bool, message: str, is_pro: bool) -> None:
        tokens = get_tokens()
        self._personal_btn.setEnabled(not busy)
        self._pro_btn.setEnabled(not busy)
        if busy:
            target = self._pro_btn if is_pro else self._personal_btn
            target.setText(i18n.get_text("home.analyzing", "Analyzing…"))
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
            self._pro_btn.setText(i18n.get_text("home.analyze_pro_demos", "Analyze Pro Demos"))
            status = self._pro_analyze_status
        else:
            self._personal_btn.setText(i18n.get_text("home.analyze_demos", "Analyze Demos"))
            status = self._analyze_status
        status.setText(i18n.get_text("home.analysis_complete", "Analysis complete"))
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
            self._pro_btn.setText(i18n.get_text("home.analyze_pro_demos", "Analyze Pro Demos"))
            status = self._pro_analyze_status
        else:
            self._personal_btn.setText(i18n.get_text("home.analyze_demos", "Analyze Demos"))
            status = self._analyze_status
        status.setText(f"{i18n.get_text('home.error_prefix', 'Error')}: {error}")
        status.setStyleSheet(
            f"color: {tokens.error}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        logger.error("Home %s analysis failed: %s", "pro" if is_pro else "personal", error)
        get_app_state().notification_received.emit(
            "ERROR",
            f"{'Pro analysis' if is_pro else 'Demo analysis'} failed: {error}",
        )

    # ── Signal slots ──

    def _on_service_active(self, active: bool) -> None:
        self._service_state = bool(active)
        self._service_chip.set_label(self._service_chip_text())
        self._service_chip.set_severity("online" if active else "offline")

    def _on_coach_status(self, status: str) -> None:
        # Dedicated Coach chip (frame 05) — no longer folded into the
        # service chip. Must actively reset to Idle/neutral so a transient
        # "Analyzing" doesn't stick after the coach goes idle again.
        self._coach_status_raw = status or ""
        idle = not status or status.strip().lower() == "idle"
        self._coach_chip.set_label(self._coach_chip_text())
        self._coach_chip.set_severity("neutral" if idle else "warning")

    def _on_parsing_progress(self, progress: float) -> None:
        if 0 < progress < 100:
            self._parsing_bar.setValue(int(progress))
            self._parsing_bar.setVisible(True)
        else:
            self._parsing_bar.setVisible(False)

    def _on_training(self, data: dict) -> None:
        total = int(data.get("total_epochs", 0))
        active = total > 0
        self._training_card.setVisible(active)
        if not active:
            self._training_data = {}
            return
        self._training_data = dict(data)
        self._apply_training_labels(data)

    def _apply_training_labels(self, data: dict) -> None:
        epoch = int(data.get("current_epoch", 0))
        total = int(data.get("total_epochs", 0))
        self._epoch_label.setText(f"{i18n.get_text('home.epoch', 'Epoch')}: {epoch} / {total}")
        pct = int((epoch / total) * 100) if total > 0 else 0
        self._train_progress_bar.setValue(max(0, min(100, pct)))
        train_loss = float(data.get("train_loss", 0.0))
        val_loss = float(data.get("val_loss", 0.0))
        self._train_loss_label.setText(
            f"{i18n.get_text('home.train_loss', 'Train Loss')}: {train_loss:.4f}"
        )
        self._val_loss_label.setText(
            f"{i18n.get_text('home.val_loss', 'Val Loss')}: {val_loss:.4f}"
        )
        self._eta_label.setText(
            f"{i18n.get_text('home.eta', 'ETA')}: {self._format_eta(data.get('eta_seconds', 0))}"
        )
        self._training_footer.setText(self._training_footer_text())

    def _on_total_matches(self, count: int) -> None:
        # AppState reports DISTINCT demo_name across PlayerMatchStats — demos,
        # not rows. If _on_matches_changed already populated the chip from the
        # row payload, leave that richer (personal-only) count alone.
        if self._matches_chip_populated:
            return
        self._matches_count = int(count)
        self._matches_chip.set_label(self._matches_chip_text())
        if count > 0:
            self._matches_chip.set_severity("neutral")

    @staticmethod
    def _format_eta(seconds: float) -> str:
        if seconds <= 0:
            return "—"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m"
        return f"{m}m {s}s"
