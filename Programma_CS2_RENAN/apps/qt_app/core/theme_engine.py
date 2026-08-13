"""
Theme engine for Qt — renders token-driven QSS and manages CS2/CSGO/CS1.6 skins.

Every color flows from design_tokens.py (generated from
design/tokens/design-tokens.json) — the QSS template, the QPalette, and the
rating helpers all read the same DesignTokens instance. No second palette.
"""

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import (
    DesignTokens,
    get_tokens,
    set_active_theme,
)
from Programma_CS2_RENAN.apps.qt_app.core.qss_generator import invalidate_cache, render_qss
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.qt_theme_engine")

THEME_NAMES = ("CS2", "CSGO", "CS1.6")

RATING_GOOD = 1.10
RATING_BAD = 0.90

_THEMES_DIR = Path(__file__).parent.parent / "themes"
_ASSETS_DIR = Path(__file__).parent.parent.parent.parent / "PHOTO_GUI"
# P4 Neo-tactical noir display fonts live here; auto-scanned at register_fonts().
# See assets/fonts/README.txt for Space Grotesk + Inter variable-font sources.
_DISPLAY_FONTS_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "fonts"

_THEME_WALLPAPER_FOLDER = {
    "CS2": "cs2theme",
    "CSGO": "csgotheme",
    "CS1.6": "cs16theme",
}

_FONT_FILES = {
    "Roboto": "Roboto-Regular.ttf",
    "JetBrains Mono": "JetBrainsMono-Regular.ttf",
    "New Hope": "NewHope.ttf",
    "CS Regular": "cs_regular.ttf",
    "YUPIX": "YUPIX.otf",
}


def rating_color(rating: float) -> QColor:
    """HLTV rating → semantic token QColor (theme-tracking)."""
    tokens = get_tokens()
    if rating > RATING_GOOD:
        return QColor(tokens.success)
    if rating < RATING_BAD:
        return QColor(tokens.error)
    return QColor(tokens.warning)


def rating_label(rating: float) -> str:
    """WCAG 1.4.1 color-blind accessible text label for ratings."""
    if rating >= 1.20:
        return "Excellent"
    if rating > RATING_GOOD:
        return "Good"
    if rating >= RATING_BAD:
        return "Average"
    return "Below Avg"


class ThemeEngine(QObject):
    """Loads and applies QSS themes + QPalette colors + fonts + wallpapers."""

    # Emitted after a theme switch. Widgets can connect to update custom painting.
    theme_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active: str = "CS2"
        self._fonts_registered = False
        self._wallpaper_path: str = ""
        self._font_family: str = "Roboto"
        self._font_size: int = 13

    @property
    def active_theme(self) -> str:
        return self._active

    @property
    def tokens(self) -> DesignTokens:
        """Return the active theme's DesignTokens."""
        return get_tokens(self._active)

    @property
    def chart_bg(self) -> str:
        return self.tokens.chart_bg

    def apply_theme(self, name: str, app: Optional[QApplication] = None):
        """Switch to a named theme. Renders QSS from template and sets QPalette."""
        if name not in THEME_NAMES:
            return
        self._active = name
        set_active_theme(name)
        target = app or QApplication.instance()
        if target is None:
            return

        # Render QSS from the design-token template
        tokens = self.tokens
        qss = render_qss(tokens)

        # Append font rule AFTER QSS so it wins the cascade (same specificity, last wins)
        font_rule = (
            f'\nQWidget {{ font-family: "{self._font_family}", "Segoe UI", "Arial", sans-serif; '
            f"font-size: {self._font_size}px; }}\n"
        )
        target.setStyleSheet(qss + font_rule)

        # QPalette for widgets that don't honor QSS — same token source.
        p = QPalette()
        p.setColor(QPalette.Window, QColor(tokens.surface_base))
        p.setColor(QPalette.WindowText, QColor(tokens.text_primary))
        p.setColor(QPalette.Base, QColor(tokens.surface_sunken))
        p.setColor(QPalette.AlternateBase, QColor(tokens.surface_raised))
        p.setColor(QPalette.Text, QColor(tokens.text_primary))
        p.setColor(QPalette.BrightText, QColor(tokens.text_inverse))
        p.setColor(QPalette.Button, QColor(tokens.surface_raised))
        p.setColor(QPalette.ButtonText, QColor(tokens.text_primary))
        p.setColor(QPalette.Highlight, QColor(tokens.accent_primary))
        p.setColor(QPalette.HighlightedText, QColor(tokens.text_inverse))
        p.setColor(QPalette.ToolTipBase, QColor(tokens.surface_overlay))
        p.setColor(QPalette.ToolTipText, QColor(tokens.text_primary))
        p.setColor(QPalette.PlaceholderText, QColor(tokens.text_tertiary))
        p.setColor(QPalette.Link, QColor(tokens.accent_primary))

        target.setPalette(p)

        # Update wallpaper for the new theme
        self._update_wallpaper(name)

        # Notify widgets that the theme changed
        self.theme_changed.emit(name)

    # ── Font Management ──

    def set_font(self, family: str, size_pt: int):
        """Change the app font and re-apply stylesheet to propagate everywhere."""
        self._font_family = family
        self._font_size = size_pt
        invalidate_cache()  # Font rule is appended after QSS, so re-render
        self.apply_theme(self._active)

    def register_fonts(self):
        """Register all custom font files with Qt. Call once at startup.

        Two sources:
            1. ``PHOTO_GUI/`` — legacy display fonts (Roboto, JetBrains Mono,
               New Hope, CS Regular, YUPIX) shipped since P1.
            2. ``assets/fonts/`` — P4 Neo-tactical noir display stack
               (Space Grotesk, Inter variable). Auto-scanned; whatever
               .ttf / .otf files are present get registered. Missing files
               are silent at debug level because the QSS fallback chain
               (Roboto / system sans) renders correctly either way.
        """
        if self._fonts_registered:
            return
        for name, filename in _FONT_FILES.items():
            path = _ASSETS_DIR / filename
            if path.exists():
                font_id = QFontDatabase.addApplicationFont(str(path))
                if font_id < 0:
                    _logger.warning("Failed to load font %s from %s", name, path)
            else:
                _logger.warning("Font file not found: %s", path)

        if _DISPLAY_FONTS_DIR.is_dir():
            for font_path in sorted(_DISPLAY_FONTS_DIR.iterdir()):
                if font_path.suffix.lower() not in (".ttf", ".otf"):
                    continue
                font_id = QFontDatabase.addApplicationFont(str(font_path))
                if font_id < 0:
                    _logger.warning("Failed to load display font from %s", font_path)
                else:
                    _logger.debug("Registered display font %s", font_path.name)
        else:
            _logger.debug(
                "Display fonts dir missing: %s (Roboto fallback used)",
                _DISPLAY_FONTS_DIR,
            )

        self._fonts_registered = True

    # ── Wallpaper ──

    @property
    def wallpaper_path(self) -> str:
        """Current wallpaper image path (empty string if none)."""
        return self._wallpaper_path

    def _update_wallpaper(self, theme_name: str):
        """Resolve the wallpaper from the persisted user choice (flat default).

        The design atlas default is NO wallpaper — a flat ``surface_base``
        canvas. Only an explicit user choice (persisted BACKGROUND_IMAGE
        setting) brings one back:

        - unset / empty  → flat (``""``)
        - filename       → resolved inside the active theme's wallpaper
          folder; missing there (e.g. after a theme switch) → flat.
        """
        from Programma_CS2_RENAN.core.config import get_setting

        chosen = get_setting("BACKGROUND_IMAGE", None)
        if not chosen:
            self._wallpaper_path = ""
            return
        folder = _THEME_WALLPAPER_FOLDER.get(theme_name, "cs2theme")
        path = _ASSETS_DIR / folder / str(chosen)
        self._wallpaper_path = str(path) if path.is_file() else ""

    def get_available_wallpapers(self, theme_name: str | None = None) -> list[str]:
        """Return list of wallpaper filenames for a theme."""
        name = theme_name or self._active
        folder = _THEME_WALLPAPER_FOLDER.get(name, "cs2theme")
        theme_dir = _ASSETS_DIR / folder
        if not theme_dir.is_dir():
            return []
        return sorted(
            f for f in os.listdir(theme_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))
        )

    def resolve_wallpaper(self, filename: str) -> str:
        """Absolute path of a wallpaper file in the active theme ("" if absent)."""
        if not filename:
            return ""
        folder = _THEME_WALLPAPER_FOLDER.get(self._active, "cs2theme")
        path = _ASSETS_DIR / folder / filename
        return str(path) if path.is_file() else ""

    def set_wallpaper(self, filename: str):
        """Set a specific wallpaper by filename; ``""`` clears to flat."""
        if not filename:
            self._wallpaper_path = ""
            return
        resolved = self.resolve_wallpaper(filename)
        if resolved:
            self._wallpaper_path = resolved
