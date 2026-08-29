"""
Main window — QMainWindow with collapsible navigation sidebar and QStackedWidget.

Replaces the Kivy ScreenManager + layout.kv root FloatLayout.
"""

from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.widgets.components.nav_sidebar import NAV_ITEMS, NavSidebar
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_main_window")


class _CustomTitleBar(QFrame):
    """Hand-rolled frameless titlebar — drag zone + Min/Max/Close.

    Only instantiated when ``AppState.use_frameless_window`` is True. The
    three buttons live in a compact 40px strip; the remainder of the bar
    acts as the drag handle (we track the press offset so the window
    moves 1:1 with the cursor without jumping on the first delta).

    No native snap-to-edge — that's an OS window-manager feature that
    only fires on native frames. We surface this caveat in the settings
    row copy so the user knows what they're giving up.
    """

    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.setObjectName("custom_titlebar")
        self.setFixedHeight(36)
        self._window = parent
        self._drag_offset: QPoint | None = None

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 0, 0)
        row.setSpacing(0)

        self._title = QLabel(parent.windowTitle())
        self._title.setObjectName("custom_titlebar_title")
        row.addWidget(self._title)
        row.addStretch()

        for glyph, tooltip, handler in (
            ("−", "Minimize", parent.showMinimized),
            ("□", "Maximize / Restore", self._toggle_maximize),
            ("✕", "Close", parent.close),
        ):
            btn = QPushButton(glyph)
            btn.setObjectName("custom_titlebar_button")
            btn.setFixedSize(44, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.clicked.connect(handler)
            row.addWidget(btn)

    def _toggle_maximize(self) -> None:
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._window.isMaximized():
            self._drag_offset = (
                event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class _BackgroundWidget(QWidget):
    """Paints a wallpaper image + tactical-grid motif behind children.

    Two layers, both composited via QPainter.setOpacity:

        1. Wallpaper pixmap (existing since P1) — center-cropped,
           ``self._opacity`` (0.25).
        2. Tactical-grid motif SVG (P4 addition) — tiled at
           ``self._motif_opacity`` (0.025) across the full viewport. SVG
           is rendered once into a 64×64 QPixmap and then painted with
           QPainter.drawTiledPixmap so the cost stays O(viewport) even
           as the tile count scales.
    """

    _MOTIF_PATH = (
        Path(__file__).resolve().parent.parent.parent.parent
        / "design"
        / "assets"
        / "motifs"
        / "tactical-grid.svg"
    )

    # Q6-SLIDESHOW: rotation cadence + crossfade length. The fade runs on a
    # QVariantAnimation repaint loop (no QGraphicsEffect — Linux ban).
    _SLIDESHOW_INTERVAL_MS = 120_000
    _SLIDESHOW_FADE_MS = 900

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._scaled_cache: QPixmap | None = None
        # P2 (UX audit): wallpaper opacity lowered 0.25 -> 0.15 so decorative
        # imagery never competes with content on sparse screens (empty
        # performance/match-detail, wizard). Panel'd screens already rely on
        # frosted cards; this rescues the screens without a content panel.
        self._opacity: float = 0.15
        self._motif_tile: QPixmap | None = self._render_motif_tile()
        # Keep the motif barely perceptible — it's a subconscious
        # texture cue, not a decoration. Tweak via settings later.
        self._motif_opacity: float = 0.05
        # Slideshow state (Q6) — inert until set_slideshow() arms it.
        self._slideshow_paths: list[str] = []
        self._slideshow_idx: int = 0
        self._slideshow_timer: QTimer | None = None
        self._fade_anim: QVariantAnimation | None = None
        self._fade_t: float = 1.0  # 1.0 = incoming fully shown
        self._old_scaled: QPixmap | None = None

    @classmethod
    def _render_motif_tile(cls) -> QPixmap | None:
        """Render the tactical-grid SVG into a 64×64 pixmap once per process."""
        if not cls._MOTIF_PATH.exists():
            return None
        try:
            from PySide6.QtSvg import QSvgRenderer
        except ImportError:  # pragma: no cover — QtSvg ships with Essentials
            return None
        renderer = QSvgRenderer(str(cls._MOTIF_PATH))
        if not renderer.isValid():
            return None
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()
        return pm

    def set_image(self, path: str):
        self.stop_slideshow()
        self._set_pixmap_from_path(path)

    def _set_pixmap_from_path(self, path: str):
        if path and __import__("os").path.exists(path):
            self._pixmap = QPixmap(path)
        else:
            self._pixmap = None
        self._scaled_cache = None
        self.update()

    # ── Slideshow (Q6) ──

    def set_slideshow(self, paths: list[str]):
        """Rotate through ``paths`` with a crossfade every 2 minutes.

        An empty/degenerate list degrades to the flat default. A single
        image shows statically (no pointless self-fades).
        """
        import os

        real = [p for p in paths if p and os.path.exists(p)]
        self.stop_slideshow()
        if not real:
            self._set_pixmap_from_path("")
            return
        self._slideshow_paths = real
        self._slideshow_idx = 0
        self._set_pixmap_from_path(real[0])
        if len(real) < 2:
            return
        self._slideshow_timer = QTimer(self)
        self._slideshow_timer.setInterval(self._SLIDESHOW_INTERVAL_MS)
        self._slideshow_timer.timeout.connect(self._advance_slideshow)
        self._slideshow_timer.start()

    def stop_slideshow(self):
        if self._slideshow_timer is not None:
            self._slideshow_timer.stop()
            self._slideshow_timer.deleteLater()
            self._slideshow_timer = None
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
        self._slideshow_paths = []
        self._old_scaled = None
        self._fade_t = 1.0

    def _advance_slideshow(self):
        import os

        if not self._slideshow_paths:
            return
        self._slideshow_idx = (self._slideshow_idx + 1) % len(self._slideshow_paths)
        next_path = self._slideshow_paths[self._slideshow_idx]
        # The harness (and users who disable animations) get a hard cut.
        if os.environ.get("MACENA_UI_ANIMATIONS") == "0":
            self._set_pixmap_from_path(next_path)
            return
        # Keep the outgoing frame for the crossfade, then swap the source.
        self._old_scaled = self._scaled_cache
        self._set_pixmap_from_path(next_path)
        if self._fade_anim is not None:
            self._fade_anim.stop()
        anim = QVariantAnimation(self)
        anim.setDuration(self._SLIDESHOW_FADE_MS)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        def _tick(value):
            self._fade_t = float(value)
            self.update()

        def _done():
            self._old_scaled = None
            self._fade_t = 1.0
            self._fade_anim = None
            self.update()

        anim.valueChanged.connect(_tick)
        anim.finished.connect(_done)
        self._fade_anim = anim
        self._fade_t = 0.0
        anim.start()

    def resizeEvent(self, event):
        self._scaled_cache = None  # Invalidate cache on resize
        self._old_scaled = None  # A mid-fade resize drops the outgoing frame
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        fading = self._old_scaled is not None and self._fade_t < 1.0
        if fading:
            painter.setOpacity(self._opacity * (1.0 - self._fade_t))
            painter.drawPixmap(0, 0, self._old_scaled)
        if self._pixmap and not self._pixmap.isNull():
            if self._scaled_cache is None or self._scaled_cache.size() != self.size():
                scaled = self._pixmap.scaled(
                    self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                # Center-crop the scaled image
                x = (scaled.width() - self.width()) // 2
                y = (scaled.height() - self.height()) // 2
                self._scaled_cache = scaled.copy(x, y, self.width(), self.height())
            painter.setOpacity(self._opacity * (self._fade_t if fading else 1.0))
            painter.drawPixmap(0, 0, self._scaled_cache)
        if self._motif_tile is not None:
            painter.setOpacity(self._motif_opacity)
            painter.drawTiledPixmap(self.rect(), self._motif_tile)
        painter.end()
        super().paintEvent(event)


class MainWindow(QMainWindow):
    """Root application window with collapsible sidebar navigation."""

    screen_changed = Signal(str)

    def __init__(self):
        super().__init__()
        from importlib.metadata import PackageNotFoundError, version

        try:
            _v = version("macena-cs2-analyzer")
        except PackageNotFoundError:
            _v = "1.0.0"
        self.setWindowTitle(f"Macena CS2 Analyzer v{_v}")
        self.setMinimumSize(1280, 720)
        # Frame-05 canvas: the atlas is designed at 1440x900; open there by
        # default instead of the 1280x720 minimum.
        self.resize(1440, 900)

        # Flagship P3 toggle: if enabled, strip the native frame and
        # provide a hand-rolled titlebar above the sidebar + content.
        # We read the toggle once at construction — runtime flip requires
        # restart, surfaced in the settings description copy.
        self._frameless_mode = get_app_state().use_frameless_window
        if self._frameless_mode:
            self.setWindowFlag(Qt.FramelessWindowHint, True)

        # Central container
        central = QWidget()
        self.setCentralWidget(central)
        if self._frameless_mode:
            outer = QVBoxLayout(central)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.setSpacing(0)
            self._titlebar = _CustomTitleBar(self)
            outer.addWidget(self._titlebar)
            body = QWidget()
            outer.addWidget(body, 1)
            root_layout = QHBoxLayout(body)
        else:
            self._titlebar = None
            root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ──
        self._nav_sidebar = NavSidebar()
        self._nav_sidebar.nav_clicked.connect(self.switch_screen)
        root_layout.addWidget(self._nav_sidebar)

        # ── Content area with background image ──
        content_wrapper = QWidget()
        overlay = QStackedLayout(content_wrapper)
        overlay.setStackingMode(QStackedLayout.StackAll)

        # Layer 0: background wallpaper (painted behind everything)
        self._bg_widget = _BackgroundWidget()
        overlay.addWidget(self._bg_widget)

        # Layer 1: actual screen stack (on top, transparent background)
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("QStackedWidget { background: transparent; }")
        overlay.addWidget(self._stack)

        # Screen stack is the topmost interactive layer
        overlay.setCurrentWidget(self._stack)

        root_layout.addWidget(content_wrapper, 1)

        # Toast notifications — floating child of content_wrapper, NOT in the
        # QStackedLayout.  Hides itself when empty so it never blocks events.
        from Programma_CS2_RENAN.apps.qt_app.widgets.toast import ToastContainer

        self._toast_container = ToastContainer(content_wrapper)
        self._content_wrapper = content_wrapper
        content_wrapper.installEventFilter(self)

        # Screen registry
        self._screens: dict[str, int] = {}

        # Connect notification toasts (get_app_state already imported at module top)
        get_app_state().notification_received.connect(self._show_toast)

        # Connect i18n changes
        i18n.language_changed.connect(self._refresh_nav_labels)

        # Keyboard shortcuts for sidebar nav items — NAV_ITEMS is the single
        # source of truth (same table drives the buttons and their tooltips).
        for screen, _icon, _i18n_key, keys in NAV_ITEMS:
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.activated.connect(lambda s=screen: self.switch_screen(s))

    # ── System tray (Q6) ──

    def attach_tray(self, tray) -> None:
        """Adopt the tray icon; arms close-to-tray in closeEvent."""
        self._tray = tray

    def closeEvent(self, event):
        """Close button minimizes to the tray when armed (Q6).

        Two guards: a tray must be attached and the CLOSE_TO_TRAY setting
        on (default). The tray's Quit action calls QApplication.quit()
        directly — that path never enters closeEvent. Hiding keeps the
        backend alive: the scanner daemon goes on ingesting demos while
        the window is away.
        """
        from Programma_CS2_RENAN.core.config import get_setting

        tray = getattr(self, "_tray", None)
        if tray is not None and get_setting("CLOSE_TO_TRAY", True):
            event.ignore()
            self.hide()
            if not getattr(self, "_tray_balloon_shown", False):
                self._tray_balloon_shown = True
                tray.showMessage(
                    i18n.get_text("tray_bg_title", "Still running"),
                    i18n.get_text(
                        "tray_bg_body",
                        "Macena keeps coaching in the background — "
                        "right-click the tray icon to quit.",
                    ),
                )
            return
        if tray is not None:
            # Tray mode disables quit-on-last-window; an unarmed close must
            # still exit the app rather than strand a windowless process.
            from PySide6.QtWidgets import QApplication

            QApplication.instance().quit()
        super().closeEvent(event)

    def set_wallpaper(self, path: str):
        """Set the background wallpaper image path."""
        self._bg_widget.set_image(path)

    def set_wallpaper_slideshow(self, paths: list[str]):
        """Arm the rotating wallpaper slideshow (Q6)."""
        self._bg_widget.set_slideshow(paths)

    def apply_wallpaper_state(self, theme) -> None:
        """Push the ThemeEngine's current wallpaper choice to the canvas.

        Single seam for all three wallpaper triggers (boot, theme switch,
        settings pick) — branches static path vs the slideshow sentinel so
        no caller re-implements the mode logic.
        """
        if getattr(theme, "wallpaper_is_slideshow", False):
            self.set_wallpaper_slideshow(theme.slideshow_paths())
        else:
            self.set_wallpaper(theme.wallpaper_path)

    def register_screen(self, name: str, widget: QWidget):
        """Add a screen widget to the stack.

        Coach registers like every other screen since the frames-06/07
        redesign — the QDockWidget pathway (and its DOCK-01 float-restore
        contract) was removed with it.
        """
        idx = self._stack.addWidget(widget)
        self._screens[name] = idx

    def _sound(self):
        """Lazy singleton SoundManager (R4 MED: it was never instantiated,
        so the SOUNDS_ENABLED settings toggle had no effect at all)."""
        mgr = getattr(self, "_sound_manager", None)
        if mgr is None:
            try:
                from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
                from Programma_CS2_RENAN.apps.qt_app.core.sound import SoundManager

                mgr = SoundManager(get_app_state(), self)
            except Exception:
                logger.exception("SoundManager init failed — sounds disabled")

                class _NullSound:
                    def play(self, _name):
                        return None

                mgr = _NullSound()
            self._sound_manager = mgr
        return mgr

    def switch_screen(self, name: str):
        """Navigate to a named screen."""
        self._sound().play("click")
        if name not in self._screens:
            logger.warning("switch_screen: unknown screen '%s'", name)
            return

        new_idx = self._screens[name]
        old_idx = self._stack.currentIndex()

        # Update sidebar active state
        self._nav_sidebar.set_active(name)

        if old_idx == new_idx:
            # Same screen — just notify
            widget = self._stack.currentWidget()
            if hasattr(widget, "on_enter"):
                widget.on_enter()
            return

        # Notify old screen it's leaving
        old_widget = self._stack.widget(old_idx)
        if old_widget is not None and hasattr(old_widget, "on_leave"):
            old_widget.on_leave()

        new_widget = self._stack.widget(new_idx)

        # Switch screen (fade animation disabled — QGraphicsOpacityEffect causes
        # QPainter errors on Linux when applied during widget layout/repaint)
        self._stack.setCurrentIndex(new_idx)

        # Notify the screen
        if hasattr(new_widget, "on_enter"):
            new_widget.on_enter()

        self.screen_changed.emit(name)

    def _show_toast(self, severity: str, message: str):
        """Display a toast notification from the backend."""
        self._toast_container.add_toast(severity, message)

    def _refresh_nav_labels(self, _lang: str):
        """Update sidebar labels and screen content when language changes."""
        self._nav_sidebar.retranslate()
        # Notify all screens
        for i in range(self._stack.count()):
            widget = self._stack.widget(i)
            if hasattr(widget, "retranslate"):
                widget.retranslate()

    def eventFilter(self, obj, event):
        """Reposition toast overlay when content area resizes."""
        if obj is self._content_wrapper and event.type() == QEvent.Type.Resize:
            if self._toast_container.isVisible():
                self._toast_container.refit()
        return super().eventFilter(obj, event)
