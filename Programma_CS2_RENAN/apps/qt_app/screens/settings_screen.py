"""Settings screen — tabbed layout: Appearance, Paths & Data, General."""

from PySide6.QtCore import QRectF, Qt, QThreadPool
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import (
    WALLPAPER_SLIDESHOW,
    ThemeEngine,
    normalize_font_family,
)
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import navigate_to
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.apps.qt_app.widgets.components.card import Card
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mono_footer import MonoFooter
from Programma_CS2_RENAN.apps.qt_app.widgets.components.toggle_switch import ToggleSwitch
from Programma_CS2_RENAN.core.config import SETTINGS_PATH, get_setting, save_user_setting
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_settings")

_FONT_SIZES = {"Small": 11, "Medium": 13, "Large": 16}

# Theme-card metadata (frame 16): display name + tagline i18n key/fallback.
_THEME_CARD_META = {
    "CS2": ("CS2", "theme_tagline_cs2", "modern · tactical orange"),
    "CSGO": ("CS:GO", "theme_tagline_csgo", "muted · military steel"),
    "CS1.6": ("CS 1.6", "theme_tagline_cs16", "retro · terminal green"),
}

# Swatch strip inside each theme card — 5 representative token fields.
_SWATCH_FIELDS = ("surface_base", "surface_raised", "accent_primary", "text_primary", "info")

# Quick Links (frame 16): key → (i18n key, fallback).
_QUICK_LINK_LABELS = {
    "ingame": ("quick_link_ingame", "In-Game Name"),
    "steam": ("quick_link_steam", "Steam Config"),
    "faceit": ("quick_link_faceit", "FaceIt Config"),
    "reset_wizard": ("quick_link_reset_wizard", "Reset Wizard"),
    "wipe": ("wipe_local_data", "Wipe local data"),
}


def _repolish(widget: QWidget) -> None:
    """Re-evaluate QSS dynamic-property selectors after a property change."""
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)


class _ThemeCard(QFrame):
    """Clickable theme card — 5 palette swatches + accent name + tagline.

    Swatches and the name color come from THAT theme's token set
    (``get_tokens(theme_key)``) so every card previews its own palette
    regardless of the active theme. Selection renders via the QSS
    ``QFrame#theme_card[selected="true"]`` accent-border rule.
    """

    def __init__(self, theme_key: str, display_name: str, on_select, parent=None):
        super().__init__(parent)
        self.setObjectName("theme_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self._theme_key = theme_key
        self._on_select = on_select
        theme_tokens = get_tokens(theme_key)
        tokens = get_tokens()

        row = QHBoxLayout(self)
        row.setContentsMargins(
            tokens.spacing_md, tokens.spacing_md, tokens.spacing_lg, tokens.spacing_md
        )
        row.setSpacing(tokens.spacing_md)

        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(3)
        for field in _SWATCH_FIELDS:
            swatch = QFrame()
            swatch.setFixedSize(10, 28)
            swatch.setStyleSheet(
                f"background-color: {getattr(theme_tokens, field)}; "
                f"border: none; border-radius: 2px;"
            )
            swatch_row.addWidget(swatch)
        row.addLayout(swatch_row)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        name_label = QLabel(display_name)
        name_label.setFont(Typography.font("body", QFont.Bold))
        name_label.setStyleSheet(f"color: {theme_tokens.accent_primary}; background: transparent;")
        text_col.addWidget(name_label)

        self.tagline_label = QLabel("")
        self.tagline_label.setObjectName("theme_card_tagline")
        text_col.addWidget(self.tagline_label)
        row.addLayout(text_col)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        _repolish(self)

    def mousePressEvent(self, event):  # noqa: D401
        if event.button() == Qt.LeftButton:
            self._on_select(self._theme_key)
        super().mousePressEvent(event)


class _WallpaperCard(QFrame):
    """Wallpaper preview card — paints the owning theme's surface gradient.

    Wallpaper image files can be large or absent from the repo, so the
    preview is a token gradient (accent → surface) rather than a
    thumbnail — matching the frame-16 look while staying asset-free.
    """

    def __init__(self, filename: str, label: str, caption: str, on_select, parent=None):
        super().__init__(parent)
        self.setObjectName("wallpaper_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setFixedSize(150, 80)
        self._filename = filename
        self._on_select = on_select
        tokens = get_tokens()

        col = QVBoxLayout(self)
        col.setContentsMargins(8, 8, 8, 8)
        col.setSpacing(2)
        col.addStretch()
        name_label = QLabel(label)
        name_label.setAlignment(Qt.AlignHCenter)
        name_label.setFont(Typography.font("body", QFont.Bold))
        name_label.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        col.addWidget(name_label)
        if caption:
            caption_label = QLabel(caption)
            caption_label.setAlignment(Qt.AlignHCenter)
            caption_label.setStyleSheet(
                f"color: {tokens.text_secondary}; "
                f"font-size: {tokens.font_size_caption}px; background: transparent;"
            )
            col.addWidget(caption_label)
        col.addStretch()

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        _repolish(self)

    def paintEvent(self, event):  # noqa: D401
        tokens = get_tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(rect.bottomLeft(), rect.topRight())
        gradient.setColorAt(0.0, QColor(tokens.accent_primary))
        gradient.setColorAt(0.45, QColor(tokens.accent_pressed))
        gradient.setColorAt(1.0, QColor(tokens.surface_base))
        path = QPainterPath()
        path.addRoundedRect(rect, tokens.radius_md, tokens.radius_md)
        painter.fillPath(path, gradient)
        painter.end()
        super().paintEvent(event)  # QSS border (selected accent ring) on top

    def mousePressEvent(self, event):  # noqa: D401
        if event.button() == Qt.LeftButton:
            self._on_select(self._filename)
        super().mousePressEvent(event)


class _WallpaperSlideshowCard(QFrame):
    """Dashed 'Slideshow' card (Q6) — rotates all wallpapers of the theme.

    Shares the ``wallpaper_none_card`` QSS identity so the dashed styling
    (and its selected ring) applies without a template change.
    """

    def __init__(self, on_select, parent=None):
        super().__init__(parent)
        self.setObjectName("wallpaper_none_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setFixedSize(150, 80)
        self._on_select = on_select
        tokens = get_tokens()

        col = QVBoxLayout(self)
        col.setContentsMargins(8, 8, 8, 8)
        col.setSpacing(2)
        self.text_label = QLabel(i18n.get_text("wallpaper_slideshow", "Slideshow"))
        self.text_label.setObjectName("wallpaper_none_text")
        self.text_label.setAlignment(Qt.AlignCenter)
        col.addWidget(self.text_label)
        caption = QLabel(i18n.get_text("wallpaper_slideshow_caption", "rotates every 2 min"))
        caption.setAlignment(Qt.AlignCenter)
        caption.setStyleSheet(
            f"color: {tokens.text_secondary}; "
            f"font-size: {tokens.font_size_caption}px; background: transparent;"
        )
        col.addWidget(caption)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        _repolish(self)

    def mousePressEvent(self, event):  # noqa: D401
        if event.button() == Qt.LeftButton:
            self._on_select(WALLPAPER_SLIDESHOW)
        super().mousePressEvent(event)


class _WallpaperNoneCard(QFrame):
    """Dashed 'No wallpaper' card — the flat ``surface_base`` default."""

    def __init__(self, on_select, parent=None):
        super().__init__(parent)
        self.setObjectName("wallpaper_none_card")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setFixedSize(150, 80)
        self._on_select = on_select

        col = QVBoxLayout(self)
        col.setContentsMargins(8, 8, 8, 8)
        self.text_label = QLabel(i18n.get_text("no_wallpaper", "No wallpaper"))
        self.text_label.setObjectName("wallpaper_none_text")
        self.text_label.setAlignment(Qt.AlignCenter)
        col.addWidget(self.text_label)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        _repolish(self)

    def mousePressEvent(self, event):  # noqa: D401
        if event.button() == Qt.LeftButton:
            self._on_select("")
        super().mousePressEvent(event)


class SettingsScreen(QWidget):
    """User-facing settings organized into 3 tabs."""

    def __init__(self, theme_engine: ThemeEngine, parent=None):
        super().__init__(parent)
        self._theme_engine = theme_engine

        # Theme/wallpaper card references (key → clickable card)
        self._theme_cards: dict = {}
        self._wallpaper_cards: dict = {}
        # Toggle button group references (key → QPushButton)
        self._font_size_buttons: dict = {}
        self._font_type_buttons: dict = {}
        self._language_buttons: dict = {}
        self._ingest_mode_buttons: dict = {}
        self._close_behavior_buttons: dict = {}  # Q6-TRAY

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
        # One connection covers theme AND font changes: set_font() re-runs
        # apply_theme(), which re-emits theme_changed.
        self._theme_engine.theme_changed.connect(self._on_theme_changed)

    # ── Lifecycle ──

    def on_enter(self):
        """Refresh all controls from current config when screen becomes visible."""
        self._default_path_label.setText(get_setting("DEFAULT_DEMO_PATH", "Not Set"))
        self._pro_path_label.setText(get_setting("PRO_DEMO_PATH", "Not Set"))
        self._interval_input.setText(str(get_setting("INGEST_INTERVAL_MINUTES", 30)))
        self._refresh_all_toggles()
        self._refresh_live_preview()

    def retranslate(self):
        """Update all translatable text when language changes."""
        self._title_label.setText(i18n.get_text("settings"))
        # Tab labels
        self._tabs.setTabText(0, i18n.get_text("appearance"))
        self._tabs.setTabText(1, i18n.get_text("analysis_paths"))
        self._tabs.setTabText(2, i18n.get_text("language"))
        # Section cards
        self._theme_card.set_title(i18n.get_text("visual_theme"))
        self._theme_card.set_subtitle(
            i18n.get_text(
                "visual_theme_desc",
                "Choose the color palette used across the entire app. "
                "Tokens live in design_tokens.py.",
            )
        )
        self._wallpaper_card.set_title(i18n.get_text("wallpaper"))
        self._wallpaper_card.set_subtitle(
            i18n.get_text("wallpaper_desc", "Background image shown behind the app surface.")
        )
        self._font_size_card.set_title(i18n.get_text("appearance"))
        self._live_preview_card.set_title(i18n.get_text("live_preview", "Live Preview"))
        self._quick_links_card.set_title(i18n.get_text("quick_links", "Quick Links"))
        self._paths_card.set_title(i18n.get_text("analysis_paths"))
        self._ingestion_card.set_title(i18n.get_text("data_ingestion"))
        self._language_card.set_title(i18n.get_text("language"))
        # Inline labels
        self._font_size_label.setText(i18n.get_text("font_size") + ":")
        self._interface_font_label.setText(i18n.get_text("interface_font", "Interface font") + ":")
        self._ingest_mode_label.setText(i18n.get_text("ingestion_mode") + ":")
        # Theme card taglines
        for key, card in self._theme_cards.items():
            _, tagline_key, tagline_fallback = _THEME_CARD_META[key]
            card.tagline_label.setText(i18n.get_text(tagline_key, tagline_fallback))
        # Wallpaper "None" card (file cards are filenames — not translated)
        none_card = self._wallpaper_cards.get("")
        if none_card is not None:
            none_card.text_label.setText(i18n.get_text("no_wallpaper", "No wallpaper"))
        # Quick links
        for key, btn in self._quick_link_buttons.items():
            btn.setText(i18n.get_text(*_QUICK_LINK_LABELS[key]))
        # Live preview copy
        self._refresh_live_preview()

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

        # Tab 1: Appearance (frame 16 — theme cards, wallpaper cards,
        # font pills + live preview side by side, quick links)
        app_scroll, self._appearance_layout = self._make_tab()
        self._tabs.addTab(app_scroll, i18n.get_text("appearance"))
        self._build_theme_section(self._appearance_layout)
        self._build_wallpaper_section(self._appearance_layout)
        fonts_row = QHBoxLayout()
        fonts_row.setSpacing(16)
        self._build_font_section(fonts_row)
        self._build_live_preview_section(fonts_row)
        self._appearance_layout.addLayout(fonts_row)
        self._build_quick_links_section(self._appearance_layout)
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

        # Frame 16 footer — the REAL persistence target composed from
        # core.config (save_user_setting writes atomically then chmods
        # 0o600 on POSIX — FE-04).
        layout.addWidget(MonoFooter(f"settings saved to {SETTINGS_PATH} · chmod 0o600 (FE-04)"))

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
        self._theme_card = Card(
            title=i18n.get_text("visual_theme"),
            subtitle=i18n.get_text(
                "visual_theme_desc",
                "Choose the color palette used across the entire app. "
                "Tokens live in design_tokens.py.",
            ),
        )
        row = QHBoxLayout()
        row.setSpacing(12)
        for key, (display, tagline_key, tagline_fallback) in _THEME_CARD_META.items():
            card = _ThemeCard(key, display, self._on_theme_selected)
            card.tagline_label.setText(i18n.get_text(tagline_key, tagline_fallback))
            self._theme_cards[key] = card
            row.addWidget(card)
        row.addStretch()
        self._theme_card.layout().addLayout(row)
        target.addWidget(self._theme_card)

    def _update_theme_cards(self, active_key: str):
        for key, card in self._theme_cards.items():
            card.set_selected(key == active_key)

    def _build_wallpaper_section(self, target: QVBoxLayout):
        self._wallpaper_card = Card(
            title=i18n.get_text("wallpaper"),
            subtitle=i18n.get_text(
                "wallpaper_desc", "Background image shown behind the app surface."
            ),
        )
        # Grid, not a single row: CS2 alone ships 12 wallpapers under
        # PHOTO_GUI/, and an unwrapped fixed-width row would force the
        # scroll content wider than the viewport (pushing the Live
        # Preview column off-screen).
        self._wallpaper_grid = QGridLayout()
        self._wallpaper_grid.setSpacing(12)
        self._rebuild_wallpaper_cards()
        self._wallpaper_card.layout().addLayout(self._wallpaper_grid)
        target.addWidget(self._wallpaper_card)

    _WALLPAPERS_PER_ROW = 6

    def _rebuild_wallpaper_cards(self):
        """Rebuild wallpaper cards for the current theme.

        One gradient-preview card per available wallpaper file of the
        active theme (PHOTO_GUI/<theme folder>/), painted from that
        theme's surface tokens — image thumbnails are deliberately not
        loaded; only the header is read for the dimensions caption.
        The dashed "No wallpaper" card (the flat design default) closes
        the grid, per frame 16.
        """
        self._wallpaper_cards.clear()
        while self._wallpaper_grid.count() > 0:
            item = self._wallpaper_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if self._theme_engine is None:
            return
        wallpapers = self._theme_engine.get_available_wallpapers()
        current_path = self._theme_engine.wallpaper_path
        display = _THEME_CARD_META.get(self._theme_engine.active_theme, ("", "", ""))[0]

        cards = []
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
            label = f"{display} {prefix}{variant}".strip()

            caption = ""
            resolved = self._theme_engine.resolve_wallpaper(filename)
            if resolved:
                from PySide6.QtGui import QImageReader

                size = QImageReader(resolved).size()  # header-only read
                if size.isValid():
                    caption = f"{size.width()}×{size.height()}"

            card = _WallpaperCard(filename, label, caption, self._on_wallpaper_selected)
            self._wallpaper_cards[filename] = card
            cards.append(card)

        # Dashed "Slideshow" card (Q6) — keyed by the persisted sentinel.
        # Only offered when the theme has 2+ wallpapers to rotate.
        if len(wallpapers) >= 2:
            slideshow_card = _WallpaperSlideshowCard(self._on_wallpaper_selected)
            self._wallpaper_cards[WALLPAPER_SLIDESHOW] = slideshow_card
            cards.append(slideshow_card)

        # Dashed "No wallpaper" card — flat surface is the design default.
        # Keyed by "" in _wallpaper_cards (the persisted empty value).
        none_card = _WallpaperNoneCard(self._on_wallpaper_selected)
        self._wallpaper_cards[""] = none_card
        cards.append(none_card)

        for idx, card in enumerate(cards):
            row, col = divmod(idx, self._WALLPAPERS_PER_ROW)
            self._wallpaper_grid.addWidget(card, row, col)
        # Left-align partial rows by letting a stretch column absorb slack.
        self._wallpaper_grid.setColumnStretch(self._WALLPAPERS_PER_ROW, 1)

        self._update_wallpaper_toggles(current_path)

    def _update_wallpaper_toggles(self, current_path: str):
        """Highlight the active wallpaper card."""
        import os

        for filename, card in self._wallpaper_cards.items():
            if filename == "":
                # "None" choice — active exactly when no wallpaper is set
                is_active = current_path == ""
            elif filename == WALLPAPER_SLIDESHOW:
                is_active = current_path == WALLPAPER_SLIDESHOW
            else:
                is_active = current_path.endswith(os.sep + filename) or current_path.endswith(
                    "/" + filename
                )
            card.set_selected(is_active)

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

    def _build_font_section(self, target: QHBoxLayout):
        """Frame 16 'Appearance' card — font size + interface font pills."""
        self._font_size_card = Card(title=i18n.get_text("appearance"))
        self._font_size_label = QLabel(i18n.get_text("font_size") + ":")
        self._font_size_label.setObjectName("section_subtitle")
        self._font_size_card.layout().addWidget(self._font_size_label)
        row = self._make_toggle_group(
            {name: f"{name} ({px}px)" for name, px in _FONT_SIZES.items()},
            self._font_size_buttons,
            self._on_font_size_selected,
        )
        self._font_size_card.layout().addLayout(row)

        self._interface_font_label = QLabel(i18n.get_text("interface_font", "Interface font") + ":")
        self._interface_font_label.setObjectName("section_subtitle")
        self._font_size_card.layout().addWidget(self._interface_font_label)
        row1 = self._make_toggle_group(
            {"Roboto": "Roboto", "Arial": "Arial", "JetBrains Mono": "JetBrains"},
            self._font_type_buttons,
            self._on_font_type_selected,
        )
        self._font_size_card.layout().addLayout(row1)
        # Q6-FONTS: keys are the EMBEDDED family names Qt actually matches
        # ("NewHope", "Counter-Strike") — the old pretty-label keys resolved
        # to nothing and silently fell back to Segoe UI. Labels stay pretty.
        row2 = self._make_toggle_group(
            {"NewHope": "New Hope", "Counter-Strike": "CS Regular", "YUPIX": "YUPIX"},
            self._font_type_buttons,
            self._on_font_type_selected,
        )
        self._font_size_card.layout().addLayout(row2)

        # Q6-TRAY: close-button behavior (persisted CLOSE_TO_TRAY bool).
        self._close_behavior_label = QLabel(i18n.get_text("close_behavior", "Close button") + ":")
        self._close_behavior_label.setObjectName("section_subtitle")
        self._font_size_card.layout().addWidget(self._close_behavior_label)
        row3 = self._make_toggle_group(
            {
                "tray": i18n.get_text("close_to_tray", "Minimize to tray"),
                "exit": i18n.get_text("close_exit", "Exit the app"),
            },
            self._close_behavior_buttons,
            self._on_close_behavior_selected,
        )
        self._font_size_card.layout().addLayout(row3)
        self._font_size_card.layout().addStretch()
        target.addWidget(self._font_size_card, 1)

    def _build_live_preview_section(self, target: QHBoxLayout):
        """Frame 16 'Live Preview' card — sample text + accent/mono facts.

        The sample labels carry no hard-coded font: they inherit the
        app-wide ``QWidget`` font rule, so a font-size or family pill
        click restyles them immediately. Token-dependent lines refresh
        via ``theme_changed``.
        """
        self._live_preview_card = Card(title=i18n.get_text("live_preview", "Live Preview"))

        sample = QFrame()
        sample.setObjectName("live_preview_sample")
        sample_layout = QVBoxLayout(sample)
        tokens = get_tokens()
        sample_layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_md, tokens.spacing_lg, tokens.spacing_md
        )
        sample_layout.setSpacing(tokens.spacing_xs)

        self._sample_title = QLabel(i18n.get_text("sample_card", "Sample Card"))
        self._sample_title.setStyleSheet("font-weight: 700; background: transparent;")
        sample_layout.addWidget(self._sample_title)

        self._sample_body = QLabel("")
        self._sample_body.setWordWrap(True)
        self._sample_body.setStyleSheet("background: transparent;")
        sample_layout.addWidget(self._sample_body)

        accent_row = QHBoxLayout()
        accent_row.setSpacing(6)
        self._accent_dot = QLabel("●")
        accent_row.addWidget(self._accent_dot)
        self._accent_line = QLabel("")
        Typography.apply(self._accent_line, "mono")
        accent_row.addWidget(self._accent_line)
        accent_row.addStretch()
        sample_layout.addLayout(accent_row)

        self._mono_line = QLabel(
            i18n.get_text("mono_stack_note", "mono: JetBrains Mono · fallback Roboto")
        )
        Typography.apply(self._mono_line, "mono")
        sample_layout.addWidget(self._mono_line)

        self._live_preview_card.layout().addWidget(sample)
        self._live_preview_card.layout().addStretch()
        target.addWidget(self._live_preview_card, 1)

    def _refresh_live_preview(self):
        """Re-render token-dependent preview lines (theme or font change)."""
        tokens = get_tokens()
        size_name = get_setting("FONT_SIZE", "Medium")
        body = i18n.get_text(
            "sample_body", "This is how body text appears in the {size} size."
        ).replace("{size}", i18n.get_text(f"size_{size_name.lower()}", size_name))
        self._sample_body.setText(body)
        self._accent_dot.setStyleSheet(f"color: {tokens.accent_primary}; background: transparent;")
        self._accent_line.setText(
            f"{i18n.get_text('accent_primary_label', 'Accent primary')} = "
            f"{tokens.accent_primary}"
        )

    def _on_theme_changed(self, _name: str):
        """Track theme/font swaps triggered from anywhere (incl. this screen)."""
        self._refresh_live_preview()

    def _build_quick_links_section(self, target: QVBoxLayout):
        """Frame 16 'Quick Links' — secondary nav shortcuts + danger wipe."""
        self._quick_links_card = Card(title=i18n.get_text("quick_links", "Quick Links"))
        row = QHBoxLayout()
        row.setSpacing(12)
        self._quick_link_buttons: dict[str, QPushButton] = {}

        def _add_link(key: str, variant: str, handler) -> None:
            btn = QPushButton(i18n.get_text(*_QUICK_LINK_LABELS[key]))
            btn.setProperty("variant", variant)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setMinimumWidth(120)
            btn.clicked.connect(handler)
            self._quick_link_buttons[key] = btn
            row.addWidget(btn)

        _add_link("ingame", "secondary", lambda: self._navigate("profile"))
        _add_link("steam", "secondary", lambda: self._navigate("steam_config"))
        _add_link("faceit", "secondary", lambda: self._navigate("faceit_config"))
        _add_link("reset_wizard", "secondary", self._on_reset_wizard)
        _add_link("wipe", "danger", self._on_wipe_local_data)
        row.addStretch()
        self._quick_links_card.layout().addLayout(row)
        target.addWidget(self._quick_links_card)

    def _navigate(self, screen_name: str):
        navigate_to(self, screen_name)

    def _on_reset_wizard(self):
        """Re-arm the first-run wizard and jump straight into it."""
        save_user_setting("SETUP_COMPLETED", False)
        logger.info("Setup wizard re-armed (SETUP_COMPLETED=False)")
        self._navigate("wizard")

    def _on_wipe_local_data(self):
        """Two-step confirm, then surface the CLI-only wipe path.

        # FIELD-GAP: no wipe backend is wired to the UI — the safe wipe
        # lives in tools/wipe_for_reingest_safe.py (CLI only). The UI
        # must not invoke destructive backend paths directly, so after
        # the double confirmation we point the user at the tool.
        """
        first = QMessageBox.warning(
            self,
            i18n.get_text("wipe_confirm_title", "Wipe local data?"),
            i18n.get_text(
                "wipe_confirm_body",
                "This would delete every analyzed match, model checkpoint "
                "and knowledge entry on this machine.",
            ),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if first != QMessageBox.Yes:
            return
        second = QMessageBox.warning(
            self,
            i18n.get_text("wipe_confirm_title_2", "Are you absolutely sure?"),
            i18n.get_text("wipe_confirm_body_2", "This action cannot be undone. Continue?"),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if second != QMessageBox.Yes:
            return
        get_app_state().notification_received.emit(
            "info",
            i18n.get_text(
                "wipe_not_available",
                "Not available from the UI yet — run tools/wipe_for_reingest_safe.py",
            ),
        )

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
            name_label.setFont(Typography.font("body", QFont.DemiBold))
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
            note="Falls back to the built-in chart if pyqtgraph missing",
        )

        self._marquee_toggle = _add_row(
            i18n.get_text("flag_webengine_marquee", "WebEngine marquee"),
            i18n.get_text(
                "flag_webengine_marquee_desc",
                "Render marquee screens with the web front-end when a dist build exists.",
            ),
            app_state.use_webengine_marquee,
            app_state.set_use_webengine_marquee,
            note=i18n.get_text("restart_required", "Restart to apply"),
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
                # P4 (UX audit): the selected pill gets a lighter accent_hover
                # ring on top of the accent fill so the active state reads
                # strongly even when the theme accent is muted (CSGO's slate).
                # Border kept at 1px in BOTH states so the content box doesn't
                # reflow by 1px when toggled.
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {tokens.accent_primary}; "
                    f"color: {tokens.text_inverse}; "
                    f"border: 1px solid {tokens.accent_hover}; border-radius: 8px; "
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
        self._update_theme_cards(get_setting("ACTIVE_THEME", "CS2"))
        self._update_toggle_group(self._font_size_buttons, get_setting("FONT_SIZE", "Medium"))
        self._update_toggle_group(
            self._font_type_buttons, normalize_font_family(get_setting("FONT_TYPE", "Roboto"))
        )
        self._update_toggle_group(self._language_buttons, get_setting("LANGUAGE", "en"))
        is_auto = get_setting("INGEST_MODE_AUTO", True)
        self._update_toggle_group(self._ingest_mode_buttons, "auto" if is_auto else "manual")
        to_tray = get_setting("CLOSE_TO_TRAY", True)
        self._update_toggle_group(self._close_behavior_buttons, "tray" if to_tray else "exit")

    # ── Action Handlers ──

    def _on_theme_selected(self, name: str):
        self._theme_engine.apply_theme(name, QApplication.instance())
        save_user_setting("ACTIVE_THEME", name)
        self._refresh_all_toggles()
        self._rebuild_wallpaper_cards()
        win = self.window()
        if hasattr(win, "apply_wallpaper_state"):
            win.apply_wallpaper_state(self._theme_engine)
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
        font_type = normalize_font_family(get_setting("FONT_TYPE", "Roboto"))
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

    def _on_close_behavior_selected(self, key: str):
        save_user_setting("CLOSE_TO_TRAY", key == "tray")
        self._update_toggle_group(self._close_behavior_buttons, key)
        logger.info("Close behavior set to %s", key)

    def _on_language_selected(self, lang_code: str):
        save_user_setting("LANGUAGE", lang_code)
        i18n.set_language(lang_code)
        self._update_toggle_group(self._language_buttons, lang_code)
        logger.info("Language changed to %s", lang_code)

    def _on_wallpaper_selected(self, filename: str):
        self._theme_engine.set_wallpaper(filename)
        save_user_setting("BACKGROUND_IMAGE", filename)
        self._update_wallpaper_toggles(self._theme_engine.wallpaper_path)
        win = self.window()
        if hasattr(win, "apply_wallpaper_state"):
            win.apply_wallpaper_state(self._theme_engine)
        logger.info("Wallpaper changed to %s", filename or "<none>")

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
