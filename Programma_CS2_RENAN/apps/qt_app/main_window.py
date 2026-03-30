"""
Main window — QMainWindow with collapsible navigation sidebar and QStackedWidget.

Replaces the Kivy ScreenManager + layout.kv root FloatLayout.
"""

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedLayout, QStackedWidget, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.animation import Animator
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.widgets.components.nav_sidebar import NavSidebar
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_main_window")


class _BackgroundWidget(QWidget):
    """Paints a wallpaper image behind its children with configurable opacity."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._scaled_cache: QPixmap | None = None
        self._opacity: float = 0.25

    def set_image(self, path: str):
        if path and __import__("os").path.exists(path):
            self._pixmap = QPixmap(path)
        else:
            self._pixmap = None
        self._scaled_cache = None
        self.update()

    def resizeEvent(self, event):
        self._scaled_cache = None  # Invalidate cache on resize
        super().resizeEvent(event)

    def paintEvent(self, event):
        if self._pixmap and not self._pixmap.isNull():
            if self._scaled_cache is None or self._scaled_cache.size() != self.size():
                scaled = self._pixmap.scaled(
                    self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                # Center-crop the scaled image
                x = (scaled.width() - self.width()) // 2
                y = (scaled.height() - self.height()) // 2
                self._scaled_cache = scaled.copy(x, y, self.width(), self.height())
            painter = QPainter(self)
            painter.setOpacity(self._opacity)
            painter.drawPixmap(0, 0, self._scaled_cache)
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

        # Central container
        central = QWidget()
        self.setCentralWidget(central)
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

        # Connect notification toasts
        from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state

        get_app_state().notification_received.connect(self._show_toast)

        # Connect i18n changes
        i18n.language_changed.connect(self._refresh_nav_labels)

        # Keyboard shortcuts for sidebar nav items
        _nav_shortcuts = [
            ("Ctrl+1", "home"),
            ("Ctrl+2", "coach"),
            ("Ctrl+3", "match_history"),
            ("Ctrl+4", "performance"),
            ("Ctrl+5", "tactical_viewer"),
            ("Ctrl+,", "settings"),
            ("F1", "help"),
        ]
        for keys, screen in _nav_shortcuts:
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.activated.connect(lambda s=screen: self.switch_screen(s))

    def set_wallpaper(self, path: str):
        """Set the background wallpaper image path."""
        self._bg_widget.set_image(path)

    def register_screen(self, name: str, widget: QWidget):
        """Add a screen widget to the stack."""
        idx = self._stack.addWidget(widget)
        self._screens[name] = idx

    def switch_screen(self, name: str):
        """Navigate to a named screen with a fade transition."""
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

        # Switch screen — skip fade animation if widget hasn't been painted yet
        # (avoids QPainter errors when QGraphicsOpacityEffect is applied too early)
        self._stack.setCurrentIndex(new_idx)
        if new_widget.isVisible() and old_idx >= 0:
            Animator.fade_in(new_widget, duration=200)

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
                self._toast_container._refit()
        return super().eventFilter(obj, event)
