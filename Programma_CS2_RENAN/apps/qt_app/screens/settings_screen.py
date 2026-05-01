"""Settings screen — tabbed layout: Appearance, Paths & Data, General."""

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.toggle_switch import ToggleSwitch
from Programma_CS2_RENAN.core.config import get_setting, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_settings")

_FONT_SIZES = {"Small": 11, "Medium": 13, "Large": 16}


class SettingsScreen(QWidget):
    """User-facing settings organized into 3 tabs."""

    def __init__(self, theme_engine: ThemeEngine, parent=None):
        super().__init__(parent)
        self._theme_engine = theme_engine

        # Toggle button group references (key → QPushButton)
        self._theme_buttons: dict = {}
        self._wallpaper_buttons: dict = {}
        self._font_size_buttons: dict = {}
        self._font_type_buttons: dict = {}
        self._language_buttons: dict = {}
        self._ingest_mode_buttons: dict = {}

        # Value display widgets
        self._default_path_label: QLabel | None = None
        self._pro_path_label: QLabel | None = None
        self._interval_input: QLineEdit | None = None

        # Ingestion state
        self._ingestion_worker = None
        self._start_btn: QPushButton | None = None
        self._stop_btn: QPushButton | None = None
        self._ingest_status_label: QLabel | None = None

        self._build_ui()

    # ── Lifecycle ──

    def on_enter(self):
        """Refresh all controls from current config when screen becomes visible."""
        self._default_path_label.setText(get_setting("DEFAULT_DEMO_PATH", "Not Set"))
        self._pro_path_label.setText(get_setting("PRO_DEMO_PATH", "Not Set"))
        self._interval_input.setText(str(get_setting("INGEST_INTERVAL_MINUTES", 30)))
        self._refresh_all_toggles()

    def retranslate(self):
        """Update all translatable text when language changes."""
        self._title_label.setText(i18n.get_text("settings"))
        # Tab labels
        self._tabs.setTabText(0, i18n.get_text("appearance"))
        self._tabs.setTabText(1, i18n.get_text("analysis_paths"))
        self._tabs.setTabText(2, i18n.get_text("language"))
        # Section cards
        self._theme_card.set_title(i18n.get_text("visual_theme"))
        self._wallpaper_card.set_title(i18n.get_text("wallpaper"))
        self._font_size_card.set_title(i18n.get_text("appearance"))
        self._font_type_card.set_title(i18n.get_text("font_type"))
        self._paths_card.set_title(i18n.get_text("analysis_paths"))
        self._ingestion_card.set_title(i18n.get_text("data_ingestion"))
        self._language_card.set_title(i18n.get_text("language"))
        # Inline labels
        self._font_size_label.setText(i18n.get_text("font_size") + ":")
        self._ingest_mode_label.setText(i18n.get_text("ingestion_mode") + ":")

    # ── UI Construction ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self._title_label = QLabel(i18n.get_text("settings"))
        Typography.apply(self._title_label, "h1")
        layout.addWidget(self._title_label)

        # Tab widget
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, 1)

        # Tab 1: Appearance
        app_scroll, self._appearance_layout = self._make_tab()
        self._tabs.addTab(app_scroll, i18n.get_text("appearance"))
        self._build_theme_section(self._appearance_layout)
        self._build_wallpaper_section(self._appearance_layout)
        self._build_font_size_section(self._appearance_layout)
        self._build_font_type_section(self._appearance_layout)
        self._appearance_layout.addStretch()

        # Tab 2: Paths & Data
        paths_scroll, self._paths_layout = self._make_tab()
        self._tabs.addTab(paths_scroll, i18n.get_text("analysis_paths"))
        self._build_paths_section(self._paths_layout)
        self._build_ingestion_section(self._paths_layout)
        self._paths_layout.addStretch()

        # Tab 3: General
        gen_scroll, self._general_layout = self._make_tab()
        self._tabs.addTab(gen_scroll, i18n.get_text("language"))
        self._build_language_section(self._general_layout)
        self._build_flagship_section(self._general_layout)
        self._general_layout.addStretch()

    def _make_tab(self) -> tuple[QScrollArea, QVBoxLayout]:
        """Create a scrollable container for a tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        scroll.setWidget(content)
        return scroll, content_layout

    # ── Section Builders ──

    def _build_theme_section(self, target: QVBoxLayout):
        self._theme_card = Card(title=i18n.get_text("visual_theme"))
        row = self._make_toggle_group(
            {"CS2": "CS2", "CSGO": "CS:GO", "CS1.6": "CS 1.6"},
            self._theme_buttons,
            self._on_theme_selected,
        )
        self._theme_card.layout().addLayout(row)
        target.addWidget(self._theme_card)

    def _build_wallpaper_section(self, target: QVBoxLayout):
        self._wallpaper_card = Card(title=i18n.get_text("wallpaper"))
        self._wallpaper_row = QHBoxLayout()
        self._wallpaper_row.setSpacing(8)
        self._rebuild_wallpaper_buttons()
        self._wallpaper_card.layout().addLayout(self._wallpaper_row)
        target.addWidget(self._wallpaper_card)

    def _rebuild_wallpaper_buttons(self):
        """Rebuild wallpaper toggle buttons for the current theme."""
        self._wallpaper_buttons.clear()
        while self._wallpaper_row.count() > 0:
            item = self._wallpaper_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if self._theme_engine is None:
            return
        wallpapers = self._theme_engine.get_available_wallpapers()
        current_path = self._theme_engine.wallpaper_path
        for filename in wallpapers:
            short = filename.rsplit(".", 1)[0]
            if "16_9" in short:
                prefix = "16:9"
            elif "vertical" in short:
                prefix = "Vert"
            elif "mini" in short:
                prefix = "Mini"
            else:
                prefix = short[:8]
            variant = ""
            base = short.rsplit(".", 1)[0]
            if base and base[-1].isalpha() and base[-2] == "_":
                variant = f" {base[-1]}"
            label = f"{prefix}{variant}"

            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setMinimumWidth(70)
            btn.clicked.connect(lambda _c, f=filename: self._on_wallpaper_selected(f))
            self._wallpaper_buttons[filename] = btn
            self._wallpaper_row.addWidget(btn)

        self._wallpaper_row.addStretch()
        self._update_wallpaper_toggles(current_path)

    def _update_wallpaper_toggles(self, current_path: str):
        """Highlight the active wallpaper button."""
        import os

        tokens = get_tokens()
        for filename, btn in self._wallpaper_buttons.items():
            is_active = current_path.endswith(os.sep + filename) or current_path.endswith(
                "/" + filename
            )
            if is_active:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {tokens.accent_primary}; "
                    f"color: {tokens.text_inverse}; border: none; border-radius: 8px; "
                    f"padding: 8px 12px; font-weight: bold; }}"
                    f"QPushButton:hover {{ background-color: {tokens.accent_hover}; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: transparent; "
                    f"color: {tokens.text_secondary}; "
                    f"border: 1px solid {tokens.border_subtle}; border-radius: 8px; "
                    f"padding: 8px 12px; }}"
                    f"QPushButton:hover {{ background-color: {tokens.accent_muted_15}; "
                    f"color: {tokens.text_primary}; }}"
                )

    def _build_paths_section(self, target: QVBoxLayout):
        self._paths_card = Card(title=i18n.get_text("analysis_paths"))
        tokens = get_tokens()

        # Demo path
        demo_row = QHBoxLayout()
        demo_row.setSpacing(8)
        lbl = QLabel("Demo Path:")
        lbl.setFixedWidth(90)
        lbl.setObjectName("section_subtitle")
        demo_row.addWidget(lbl)
        self._default_path_label = QLabel("Not Set")
        self._default_path_label.setWordWrap(True)
        demo_row.addWidget(self._default_path_label, 1)
        btn = QPushButton("Change")
        btn.setFixedWidth(80)
        btn.clicked.connect(lambda: self._on_path_change("default"))
        demo_row.addWidget(btn)
        self._paths_card.layout().addLayout(demo_row)

        # Pro path
        pro_row = QHBoxLayout()
        pro_row.setSpacing(8)
        lbl2 = QLabel("Pro Path:")
        lbl2.setFixedWidth(90)
        lbl2.setObjectName("section_subtitle")
        pro_row.addWidget(lbl2)
        self._pro_path_label = QLabel("Not Set")
        self._pro_path_label.setWordWrap(True)
        pro_row.addWidget(self._pro_path_label, 1)
        btn2 = QPushButton("Change")
        btn2.setFixedWidth(80)
        btn2.clicked.connect(lambda: self._on_path_change("pro"))
        pro_row.addWidget(btn2)
        self._paths_card.layout().addLayout(pro_row)

        target.addWidget(self._paths_card)

    def _build_font_size_section(self, target: QVBoxLayout):
        self._font_size_card = Card(title=i18n.get_text("appearance"))
        self._font_size_label = QLabel(i18n.get_text("font_size") + ":")
        self._font_size_label.setObjectName("section_subtitle")
        self._font_size_card.layout().addWidget(self._font_size_label)
        row = self._make_toggle_group(
            {"Small": "Small", "Medium": "Medium", "Large": "Large"},
            self._font_size_buttons,
            self._on_font_size_selected,
        )
        self._font_size_card.layout().addLayout(row)
        target.addWidget(self._font_size_card)

    def _build_ingestion_section(self, target: QVBoxLayout):
        self._ingestion_card = Card(title=i18n.get_text("data_ingestion"))
        tokens = get_tokens()

        # Mode toggle
        self._ingest_mode_label = QLabel(i18n.get_text("ingestion_mode") + ":")
        self._ingest_mode_label.setObjectName("section_subtitle")
        self._ingestion_card.layout().addWidget(self._ingest_mode_label)
        mode_row = self._make_toggle_group(
            {"manual": "Manual", "auto": "Auto"},
            self._ingest_mode_buttons,
            self._on_ingest_mode_selected,
        )
        self._ingestion_card.layout().addLayout(mode_row)

        # Interval
        interval_row = QHBoxLayout()
        interval_row.setSpacing(8)
        int_lbl = QLabel("Scan Interval (min):")
        int_lbl.setObjectName("section_subtitle")
        interval_row.addWidget(int_lbl)
        self._interval_input = QLineEdit()
        self._interval_input.setFixedWidth(80)
        self._interval_input.setPlaceholderText("30")
        interval_row.addWidget(self._interval_input)
        set_btn = QPushButton("Set")
        set_btn.setFixedWidth(60)
        set_btn.clicked.connect(self._on_interval_set)
        interval_row.addWidget(set_btn)
        self._interval_error = QLabel("")
        self._interval_error.setStyleSheet(
            f"color: {tokens.error}; background: transparent; "
            f"font-size: {tokens.font_size_caption}px;"
        )
        self._interval_error.setVisible(False)
        interval_row.addWidget(self._interval_error)
        interval_row.addStretch()
        self._ingestion_card.layout().addLayout(interval_row)

        # Start/Stop ingestion
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        self._start_btn = QPushButton("Start Ingestion")
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.setToolTip("Scan demo folders and ingest new demos")
        self._start_btn.clicked.connect(self._on_start_ingestion)
        action_row.addWidget(self._start_btn)
        self._ingest_status_label = QLabel("")
        self._ingest_status_label.setStyleSheet(f"color: {tokens.text_secondary}; font-size: 13px;")
        action_row.addWidget(self._ingest_status_label)
        action_row.addStretch()
        self._ingestion_card.layout().addLayout(action_row)

        target.addWidget(self._ingestion_card)

    def _build_font_type_section(self, target: QVBoxLayout):
        self._font_type_card = Card(title=i18n.get_text("font_type"))
        row1 = self._make_toggle_group(
            {"Roboto": "Roboto", "Arial": "Arial", "JetBrains Mono": "JetBrains"},
            self._font_type_buttons,
            self._on_font_type_selected,
        )
        self._font_type_card.layout().addLayout(row1)
        row2 = self._make_toggle_group(
            {"New Hope": "New Hope", "CS Regular": "CS Regular", "YUPIX": "YUPIX"},
            self._font_type_buttons,
            self._on_font_type_selected,
        )
        self._font_type_card.layout().addLayout(row2)
        target.addWidget(self._font_type_card)

    def _build_language_section(self, target: QVBoxLayout):
        self._language_card = Card(title=i18n.get_text("language"))
        row = self._make_toggle_group(
            {"en": "English", "it": "Italiano", "pt": "Portugues"},
            self._language_buttons,
            self._on_language_selected,
        )
        self._language_card.layout().addLayout(row)
        target.addWidget(self._language_card)

    def _build_flagship_section(self, target: QVBoxLayout):
        """P3 opt-in feature toggles (sounds, frameless window, pyqtgraph heatmap).

        Each row uses a ``ToggleSwitch`` primitive bound to an AppState
        setter; persistence is automatic via the settings config layer.
        Restart requirements are flagged in the description where the
        underlying chrome (main window frame) cannot hot-swap.
        """
        self._flagship_card = Card(
            title="Flagship Features",
            subtitle="Opt-in polish beyond the default UX. All default off.",
            depth="raised",
        )
        layout = self._flagship_card.layout()
        app_state = get_app_state()

        def _add_row(
            label_text: str,
            description: str,
            checked: bool,
            handler,
            note: str = "",
        ) -> ToggleSwitch:
            row = QHBoxLayout()
            row.setSpacing(12)

            text_col = QVBoxLayout()
            text_col.setSpacing(2)
            name_label = QLabel(label_text)
            name_label.setFont(QFont("Roboto", 13, QFont.DemiBold))
            name_label.setStyleSheet(
                f"color: {get_tokens().text_primary}; background: transparent;"
            )
            text_col.addWidget(name_label)

            desc_label = QLabel(description + (f"  ({note})" if note else ""))
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(
                f"color: {get_tokens().text_secondary}; font-size: 12px; "
                "background: transparent;"
            )
            text_col.addWidget(desc_label)
            row.addLayout(text_col, 1)

            toggle = ToggleSwitch(checked=checked)
            toggle.toggled.connect(handler)
            row.addWidget(toggle, 0, Qt.AlignVCenter)
            layout.addLayout(row)
            return toggle

        self._sounds_toggle = _add_row(
            "Micro-interaction sounds",
            "Subtle click / success / error feedback.",
            app_state.sounds_enabled,
            app_state.set_sounds_enabled,
            note="Requires WAVs under PHOTO_GUI/sounds/",
        )

        self._frameless_toggle = _add_row(
            "Frameless window",
            "Replaces the OS titlebar with a hand-rolled chrome (no GPL dep).",
            app_state.use_frameless_window,
            app_state.set_use_frameless_window,
            note="Restart to apply",
        )

        self._pyqtgraph_toggle = _add_row(
            "pyqtgraph heatmap",
            "Higher-fidelity match-detail heatmap via pyqtgraph if installed.",
            app_state.use_pyqtgraph_heatmap,
            app_state.set_use_pyqtgraph_heatmap,
            note="Falls back to QtCharts if pyqtgraph missing",
        )

        target.addWidget(self._flagship_card)

    # ── Toggle Button Helpers ──

    def _make_toggle_group(self, options: dict, button_dict: dict, callback) -> QHBoxLayout:
        """Create a horizontal row of exclusive toggle buttons."""
        row = QHBoxLayout()
        row.setSpacing(8)
        for key, label in options.items():
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda _checked, k=key: callback(k))
            button_dict[key] = btn
            row.addWidget(btn)
        row.addStretch()
        return row

    def _update_toggle_group(self, button_dict: dict, active_key: str):
        """Active button gets accent fill, rest get outlined style."""
        tokens = get_tokens()
        for key, btn in button_dict.items():
            if key == active_key:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {tokens.accent_primary}; "
                    f"color: {tokens.text_inverse}; border: none; border-radius: 8px; "
                    f"padding: 8px 20px; font-weight: bold; }}"
                    f"QPushButton:hover {{ background-color: {tokens.accent_hover}; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: transparent; "
                    f"color: {tokens.text_secondary}; "
                    f"border: 1px solid {tokens.border_subtle}; border-radius: 8px; "
                    f"padding: 8px 20px; }}"
                    f"QPushButton:hover {{ background-color: {tokens.accent_muted_15}; "
                    f"color: {tokens.text_primary}; }}"
                )

    def _refresh_all_toggles(self):
        """Re-read config and update all toggle groups."""
        self._update_toggle_group(self._theme_buttons, get_setting("ACTIVE_THEME", "CS2"))
        self._update_toggle_group(self._font_size_buttons, get_setting("FONT_SIZE", "Medium"))
        self._update_toggle_group(self._font_type_buttons, get_setting("FONT_TYPE", "Roboto"))
        self._update_toggle_group(self._language_buttons, get_setting("LANGUAGE", "en"))
        is_auto = get_setting("INGEST_MODE_AUTO", True)
        self._update_toggle_group(self._ingest_mode_buttons, "auto" if is_auto else "manual")

    # ── Action Handlers ──

    def _on_theme_selected(self, name: str):
        self._theme_engine.apply_theme(name, QApplication.instance())
        save_user_setting("ACTIVE_THEME", name)
        self._refresh_all_toggles()
        self._rebuild_wallpaper_buttons()
        win = self.window()
        if hasattr(win, "set_wallpaper"):
            win.set_wallpaper(self._theme_engine.wallpaper_path)
        logger.info("Theme changed to %s", name)

    def _on_path_change(self, target: str):
        config_key = "DEFAULT_DEMO_PATH" if target == "default" else "PRO_DEMO_PATH"
        current = get_setting(config_key, "")
        path = QFileDialog.getExistingDirectory(
            self,
            f"Select {'Demo' if target == 'default' else 'Pro Demo'} Folder",
            current,
        )
        if path:
            save_user_setting(config_key, path)
            label = self._default_path_label if target == "default" else self._pro_path_label
            label.setText(path)
            logger.info("%s path set to %s", config_key, path)

    def _on_font_size_selected(self, size: str):
        save_user_setting("FONT_SIZE", size)
        pt = _FONT_SIZES.get(size, 13)
        font_type = get_setting("FONT_TYPE", "Roboto")
        self._theme_engine.set_font(font_type, pt)
        self._update_toggle_group(self._font_size_buttons, size)
        logger.info("Font size changed to %s (%dpt)", size, pt)

    def _on_ingest_mode_selected(self, mode: str):
        save_user_setting("INGEST_MODE_AUTO", mode == "auto")
        self._update_toggle_group(self._ingest_mode_buttons, mode)
        logger.info("Ingestion mode set to %s", mode)

    def _on_interval_set(self):
        text = self._interval_input.text().strip()
        try:
            val = max(1, int(text))
        except (ValueError, TypeError):
            self._interval_error.setText("Enter a valid number (1-999)")
            self._interval_error.setVisible(True)
            return
        self._interval_error.setVisible(False)
        save_user_setting("INGEST_INTERVAL_MINUTES", val)
        self._interval_input.setText(str(val))
        logger.info("Ingest interval set to %d min", val)

    def _on_font_type_selected(self, font_name: str):
        save_user_setting("FONT_TYPE", font_name)
        pt = _FONT_SIZES.get(get_setting("FONT_SIZE", "Medium"), 13)
        self._theme_engine.set_font(font_name, pt)
        self._update_toggle_group(self._font_type_buttons, font_name)
        logger.info("Font type changed to %s", font_name)

    def _on_language_selected(self, lang_code: str):
        save_user_setting("LANGUAGE", lang_code)
        i18n.set_language(lang_code)
        self._update_toggle_group(self._language_buttons, lang_code)
        logger.info("Language changed to %s", lang_code)

    def _on_wallpaper_selected(self, filename: str):
        self._theme_engine.set_wallpaper(filename)
        self._update_wallpaper_toggles(self._theme_engine.wallpaper_path)
        win = self.window()
        if hasattr(win, "set_wallpaper"):
            win.set_wallpaper(self._theme_engine.wallpaper_path)
        logger.info("Wallpaper changed to %s", filename)

    def _on_start_ingestion(self):
        if self._ingestion_worker is not None:
            return  # Already running
        tokens = get_tokens()
        pro_path = get_setting("PRO_DEMO_PATH", "")
        demo_path = get_setting("DEFAULT_DEMO_PATH", "")
        if not pro_path and not demo_path:
            self._ingest_status_label.setText("Set a demo path first")
            self._ingest_status_label.setStyleSheet(f"color: {tokens.error}; font-size: 13px;")
            return

        self._start_btn.setEnabled(False)
        self._start_btn.setText("Ingesting...")
        self._ingest_status_label.setText("Scanning for demos...")
        self._ingest_status_label.setStyleSheet(f"color: {tokens.warning}; font-size: 13px;")

        def _run_ingestion():
            from Programma_CS2_RENAN.run_ingestion import process_new_demos

            results = []
            if pro_path:
                results.append(("pro", process_new_demos(is_pro=True)))
            if demo_path:
                results.append(("user", process_new_demos(is_pro=False)))
            return results

        worker = Worker(_run_ingestion)
        worker.signals.result.connect(self._on_ingestion_done)
        worker.signals.error.connect(self._on_ingestion_error)
        self._ingestion_worker = worker
        QThreadPool.globalInstance().start(worker)

    def _on_ingestion_done(self, results):
        self._ingestion_worker = None
        self._start_btn.setEnabled(True)
        self._start_btn.setText("Start Ingestion")
        tokens = get_tokens()
        self._ingest_status_label.setText("Ingestion complete")
        self._ingest_status_label.setStyleSheet(f"color: {tokens.success}; font-size: 13px;")
        logger.info("Ingestion completed: %s", results)

    def _on_ingestion_error(self, error):
        self._ingestion_worker = None
        self._start_btn.setEnabled(True)
        self._start_btn.setText("Start Ingestion")
        tokens = get_tokens()
        self._ingest_status_label.setText(f"Error: {error}")
        self._ingest_status_label.setStyleSheet(f"color: {tokens.error}; font-size: 13px;")
        logger.error("Ingestion failed: %s", error)
