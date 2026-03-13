"""Settings screen — theme, paths, appearance, ingestion, font, language."""

from PySide6.QtCore import Qt
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
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
from Programma_CS2_RENAN.core.config import get_setting, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_settings")

_FONT_SIZES = {"Small": 11, "Medium": 13, "Large": 16}


class SettingsScreen(QWidget):
    """User-facing settings: theme, paths, appearance, ingestion, font, language."""

    def __init__(self, theme_engine: ThemeEngine, parent=None):
        super().__init__(parent)
        self._theme_engine = theme_engine

        # Toggle button group references (key → QPushButton)
        self._theme_buttons: dict = {}
        self._font_size_buttons: dict = {}
        self._font_type_buttons: dict = {}
        self._language_buttons: dict = {}
        self._ingest_mode_buttons: dict = {}

        # Value display widgets
        self._default_path_label: QLabel | None = None
        self._pro_path_label: QLabel | None = None
        self._interval_input: QLineEdit | None = None

        self._build_ui()

    # ── Lifecycle ──

    def on_enter(self):
        """Refresh all controls from current config when screen becomes visible."""
        self._default_path_label.setText(get_setting("DEFAULT_DEMO_PATH", "Not Set"))
        self._pro_path_label.setText(get_setting("PRO_DEMO_PATH", "Not Set"))
        self._interval_input.setText(str(get_setting("INGEST_INTERVAL_MINUTES", 30)))
        self._refresh_all_toggles()

    # ── UI Construction ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("Settings")
        title.setObjectName("section_title")
        title.setFont(QFont("Roboto", 20, QFont.Bold))
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(16)

        self._build_theme_section()
        self._build_paths_section()
        self._build_font_size_section()
        self._build_ingestion_section()
        self._build_font_type_section()
        self._build_language_section()

        self._content_layout.addStretch()
        scroll.setWidget(self._content)
        layout.addWidget(scroll, 1)

    def _section(self, title: str) -> QFrame:
        """Create a titled dashboard card and add it to content layout."""
        card = QFrame()
        card.setObjectName("dashboard_card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        lbl = QLabel(title)
        lbl.setFont(QFont("Roboto", 14, QFont.Bold))
        lbl.setStyleSheet("color: #dcdcdc;")
        card_layout.addWidget(lbl)

        self._content_layout.addWidget(card)
        return card

    # ── Section Builders ──

    def _build_theme_section(self):
        card = self._section("Theme")
        row = self._make_toggle_group(
            {"CS2": "CS2", "CSGO": "CS:GO", "CS1.6": "CS 1.6"},
            self._theme_buttons,
            self._on_theme_selected,
        )
        card.layout().addLayout(row)

    def _build_paths_section(self):
        card = self._section("Analysis Paths")

        # Demo path
        demo_row = QHBoxLayout()
        demo_row.setSpacing(8)
        lbl = QLabel("Demo Path:")
        lbl.setFixedWidth(90)
        lbl.setStyleSheet("color: #a0a0b0;")
        demo_row.addWidget(lbl)
        self._default_path_label = QLabel("Not Set")
        self._default_path_label.setStyleSheet("color: #dcdcdc;")
        self._default_path_label.setWordWrap(True)
        demo_row.addWidget(self._default_path_label, 1)
        btn = QPushButton("Change")
        btn.setFixedWidth(80)
        btn.clicked.connect(lambda: self._on_path_change("default"))
        demo_row.addWidget(btn)
        card.layout().addLayout(demo_row)

        # Pro path
        pro_row = QHBoxLayout()
        pro_row.setSpacing(8)
        lbl2 = QLabel("Pro Path:")
        lbl2.setFixedWidth(90)
        lbl2.setStyleSheet("color: #a0a0b0;")
        pro_row.addWidget(lbl2)
        self._pro_path_label = QLabel("Not Set")
        self._pro_path_label.setStyleSheet("color: #dcdcdc;")
        self._pro_path_label.setWordWrap(True)
        pro_row.addWidget(self._pro_path_label, 1)
        btn2 = QPushButton("Change")
        btn2.setFixedWidth(80)
        btn2.clicked.connect(lambda: self._on_path_change("pro"))
        pro_row.addWidget(btn2)
        card.layout().addLayout(pro_row)

    def _build_font_size_section(self):
        card = self._section("Appearance")
        lbl = QLabel("Font Size:")
        lbl.setStyleSheet("color: #a0a0b0;")
        card.layout().addWidget(lbl)
        row = self._make_toggle_group(
            {"Small": "Small", "Medium": "Medium", "Large": "Large"},
            self._font_size_buttons,
            self._on_font_size_selected,
        )
        card.layout().addLayout(row)

    def _build_ingestion_section(self):
        card = self._section("Data Ingestion")

        # Mode toggle
        mode_lbl = QLabel("Ingestion Mode:")
        mode_lbl.setStyleSheet("color: #a0a0b0;")
        card.layout().addWidget(mode_lbl)
        mode_row = self._make_toggle_group(
            {"manual": "Manual", "auto": "Auto"},
            self._ingest_mode_buttons,
            self._on_ingest_mode_selected,
        )
        card.layout().addLayout(mode_row)

        # Interval
        interval_row = QHBoxLayout()
        interval_row.setSpacing(8)
        int_lbl = QLabel("Scan Interval (min):")
        int_lbl.setStyleSheet("color: #a0a0b0;")
        interval_row.addWidget(int_lbl)
        self._interval_input = QLineEdit()
        self._interval_input.setFixedWidth(80)
        self._interval_input.setPlaceholderText("30")
        interval_row.addWidget(self._interval_input)
        set_btn = QPushButton("Set")
        set_btn.setFixedWidth(60)
        set_btn.clicked.connect(self._on_interval_set)
        interval_row.addWidget(set_btn)
        interval_row.addStretch()
        card.layout().addLayout(interval_row)

        # Start/Stop — disabled until session engine exists (Phase 2)
        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        start_btn = QPushButton("Start Ingestion")
        start_btn.setEnabled(False)
        start_btn.setToolTip("Requires session engine (Phase 2)")
        action_row.addWidget(start_btn)
        stop_btn = QPushButton("Stop Ingestion")
        stop_btn.setEnabled(False)
        stop_btn.setToolTip("Requires session engine (Phase 2)")
        action_row.addWidget(stop_btn)
        action_row.addStretch()
        card.layout().addLayout(action_row)

    def _build_font_type_section(self):
        card = self._section("Font Type")
        row1 = self._make_toggle_group(
            {"Roboto": "Roboto", "Arial": "Arial", "JetBrains Mono": "JetBrains"},
            self._font_type_buttons,
            self._on_font_type_selected,
        )
        card.layout().addLayout(row1)
        row2 = self._make_toggle_group(
            {"New Hope": "New Hope", "CS Regular": "CS Regular", "YUPIX": "YUPIX"},
            self._font_type_buttons,
            self._on_font_type_selected,
        )
        card.layout().addLayout(row2)

    def _build_language_section(self):
        card = self._section("Language")
        row = self._make_toggle_group(
            {"en": "English", "it": "Italiano", "pt": "Portugues"},
            self._language_buttons,
            self._on_language_selected,
        )
        card.layout().addLayout(row)

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
        accent = self._theme_engine.get_color("accent_primary").name()
        for key, btn in button_dict.items():
            if key == active_key:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {accent}; color: white; "
                    f"border: none; border-radius: 8px; padding: 8px 20px; font-weight: bold; }}"
                    f"QPushButton:hover {{ background-color: {accent}; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background-color: transparent; color: #a0a0b0; "
                    "border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; "
                    "padding: 8px 20px; }"
                    "QPushButton:hover { background-color: rgba(255,255,255,0.05); "
                    "color: #dcdcdc; }"
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
        # Update wallpaper in MainWindow
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
            logger.warning("Invalid interval input: %s", text)
            return
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
