"""SVG icon provider — renders symbols from `design/assets/icons/sprite.svg`.

The sprite is the authoritative icon set maintained in the design folder.
This provider gives us the same static-method API as the prior
`QPainterPath`-based `IconProvider` (in `core/icons.py`), so call-sites
like `IconProvider.home(...)` keep working after the flag-flip in
`icons.py`. Migration surface is narrow (two files: `nav_sidebar.py`,
`icon_widget.py`); every other screen goes through `IconWidget`.

Color injection: the sprite declares `stroke="currentColor"` on every
symbol. We render the symbol into a QPixmap with `QSvgRenderer`, then
use `QPainter` composition modes to tint the pixmap with the requested
color. Results are cached by `(symbol_id, size, color)` so repeated
paints don't re-render the SVG.

Each public method matches the name + signature of its `IconProvider`
counterpart so they are interchangeable under the `USE_SVG_ICONS` flag.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.qt_svg_icons")

_SCRIPT_PATH = Path(__file__).resolve()
# core/svg_icon_provider.py -> apps/qt_app/core -> apps/qt_app -> apps -> Programma_CS2_RENAN -> project root
_PROJECT_ROOT = _SCRIPT_PATH.parents[4]
_SPRITE_PATH = _PROJECT_ROOT / "design" / "assets" / "icons" / "sprite.svg"


def _sprite_raw() -> Optional[str]:
    """Read the raw sprite SVG text once; warn on miss."""
    if not _SPRITE_PATH.exists():
        _logger.warning(
            "SVG sprite not found at %s — falling back to QPainterPath icons",
            _SPRITE_PATH,
        )
        return None
    try:
        return _SPRITE_PATH.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover
        _logger.warning("SVG sprite read failed: %s", exc)
        return None


_SPRITE_TEXT: Optional[str] = _sprite_raw()

# Match <symbol id="..."> ... </symbol> — non-greedy so nested defs don't overshoot
_SYMBOL_RE = re.compile(
    r'<symbol\s+id="(?P<id>[^"]+)"[^>]*viewBox="(?P<vb>[^"]+)"(?P<attrs>[^>]*)>(?P<body>.*?)</symbol>',
    re.DOTALL,
)


def _build_symbol_svgs(raw: str) -> dict[str, str]:
    """Extract each <symbol> and wrap it as a self-contained SVG document.

    Each returned SVG has the symbol's viewBox, inherits `currentColor`
    on stroke (the sprite already uses `stroke="currentColor"`), and is
    ready for `QSvgRenderer`.
    """
    out: dict[str, str] = {}
    for match in _SYMBOL_RE.finditer(raw):
        symbol_id = match.group("id")
        viewbox = match.group("vb")
        attrs = match.group("attrs").strip()
        body = match.group("body").strip()
        # Wrap as a standalone <svg>. Preserve the symbol's attrs (fill,
        # stroke, stroke-width, linecap, linejoin).
        out[symbol_id] = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" ' f"{attrs}>{body}</svg>"
        )
    return out


_SYMBOL_SVGS: dict[str, str] = _build_symbol_svgs(_SPRITE_TEXT) if _SPRITE_TEXT else {}


def _render_symbol(symbol_id: str, size: int, color: str) -> QPixmap:
    """Render a sprite symbol into a QPixmap of the given size and color.

    Strategy: substitute `currentColor` in the symbol body with the
    requested color so `QSvgRenderer` draws directly in the target tone.
    This avoids a second compose pass for every render.
    """
    svg = _SYMBOL_SVGS.get(symbol_id)
    if svg is None:
        _logger.debug("Sprite symbol %r missing; returning blank pixmap", symbol_id)
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        return pm

    tinted = svg.replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(tinted.encode("utf-8")))

    # Render at 2x internal size for supersampling on HiDPI; downscale after.
    scale = 2
    img = QImage(size * scale, size * scale, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size * scale, size * scale))
    painter.end()
    return QPixmap.fromImage(img.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class SvgIconProvider:
    """Sprite-backed QIcon factory. Mirrors the `IconProvider` API.

    Public method names match the prior `QPainterPath` provider so the
    `USE_SVG_ICONS` flag in `core/icons.py` can swap implementations
    transparently.
    """

    # Per (symbol_id, size, color) cache — sprite is static so this is
    # effectively permanent for the app lifetime.
    _cache: dict[tuple[str, int, str], QIcon] = {}

    @classmethod
    def _icon(cls, symbol_id: str, size: int, color: str) -> QIcon:
        key = (symbol_id, size, color)
        cached = cls._cache.get(key)
        if cached is not None:
            return cached
        pm = _render_symbol(symbol_id, size, color)
        icon = QIcon(pm)
        cls._cache[key] = icon
        return icon

    # ── Nav / chrome ──

    @staticmethod
    def home(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-home", size, color)

    @staticmethod
    def brain(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-brain", size, color)

    @staticmethod
    def list_icon(size: int = 24, color: str = "#ffffff") -> QIcon:
        # Sprite uses `i-history` as the list/history glyph
        return SvgIconProvider._icon("i-history", size, color)

    @staticmethod
    def chart(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-chart", size, color)

    @staticmethod
    def crosshair(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-crosshair", size, color)

    @staticmethod
    def gear(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-gear", size, color)

    @staticmethod
    def help_circle(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-help", size, color)

    @staticmethod
    def user(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-user", size, color)

    # ── Game icons (new — not in QPainterPath fallback) ──

    @staticmethod
    def bomb(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-bomb", size, color)

    @staticmethod
    def defuser(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-defuser", size, color)

    @staticmethod
    def smoke(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-smoke", size, color)

    @staticmethod
    def flash(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-flash", size, color)

    @staticmethod
    def molotov(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-molotov", size, color)

    @staticmethod
    def he(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-he", size, color)

    @staticmethod
    def rifle(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-rifle", size, color)

    @staticmethod
    def awp(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-awp", size, color)

    @staticmethod
    def pistol(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-pistol", size, color)

    @staticmethod
    def knife(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-knife", size, color)

    # ── Status glyphs ──

    @staticmethod
    def check(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-check", size, color)

    @staticmethod
    def warn(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-warn", size, color)

    @staticmethod
    def bolt(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-bolt", size, color)

    @staticmethod
    def db(size: int = 24, color: str = "#ffffff") -> QIcon:
        return SvgIconProvider._icon("i-db", size, color)


def sprite_is_available() -> bool:
    """True if the sprite loaded and parsed at import time.

    Used by `core/icons.py` to decide whether to flip to SVG. If the
    sprite is missing or unparseable, we stay on QPainterPath so the app
    never ships with broken nav icons.
    """
    return bool(_SYMBOL_SVGS)
