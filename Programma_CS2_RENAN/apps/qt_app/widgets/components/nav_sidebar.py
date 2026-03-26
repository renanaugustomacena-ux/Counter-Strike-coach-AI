"""NavSidebar — collapsible navigation sidebar with active indicator.

Replaces inline sidebar construction in MainWindow. Features:
- Smooth collapse/expand animation (220px ↔ 60px, 200ms)
- 3px accent bar on active item (via QSS)
- Hamburger toggle button
"""

from importlib.metadata import PackageNotFoundError, version

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QSpacerItem, QVBoxLayout, QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.icons import IconProvider

# ── Navigation definition ──
# (screen_key, icon_func, i18n_key)
NAV_ITEMS = [
    ("home", IconProvider.home, "dashboard"),
    ("coach", IconProvider.brain, "rap_coach_dashboard"),
    ("match_history", IconProvider.list_icon, "match_history_title"),
    ("performance", IconProvider.chart, "advanced_analytics"),
    ("tactical_viewer", IconProvider.crosshair, "tactical_analyzer"),
    ("settings", IconProvider.gear, "settings"),
    ("help", IconProvider.help_circle, "help_center"),
]

_EXPANDED_WIDTH = 220
_COLLAPSED_WIDTH = 60


class _NavButton(QPushButton):
    """Checkable sidebar button with vector icon and label for collapse support."""

    def __init__(self, icon_func, label: str, key: str):
        super().__init__()
        self._icon_func = icon_func
        self._label = label
        self.screen_key = key
        self.setObjectName("nav_button")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setIconSize(QSize(20, 20))
        self._collapsed = False
        self._refresh_icon()
        self._update_text()

    def _refresh_icon(self):
        tokens = get_tokens()
        color = tokens.accent_primary if self.isChecked() else tokens.text_secondary
        self.setIcon(self._icon_func(size=20, color=color))

    def _update_text(self):
        self.setText("" if self._collapsed else f"  {self._label}")

    def set_collapsed(self, collapsed: bool):
        """Toggle between icon-only and icon+label display."""
        self._collapsed = collapsed
        self._update_text()

    def update_label(self, label: str):
        """Update the translatable label text."""
        self._label = label
        self._update_text()


class NavSidebar(QWidget):
    """Collapsible navigation sidebar with active indicator and smooth animation.

    Emits ``nav_clicked(screen_key)`` when a navigation button is pressed.
    """

    nav_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("nav_sidebar")
        self._is_collapsed = False
        self._anim_group: QParallelAnimationGroup | None = None
        self.setFixedWidth(_EXPANDED_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)

        # Toggle button (hamburger — top right)
        self._toggle_btn = QPushButton("\u2261")  # ≡ hamburger
        self._toggle_btn.setObjectName("nav_toggle")
        self._toggle_btn.setFixedSize(36, 36)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self.toggle_collapse)
        layout.addWidget(self._toggle_btn, alignment=Qt.AlignRight)

        # App title
        self._title = QLabel("MACENA CS2")
        self._title.setObjectName("accent_label")
        self._title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title)
        layout.addSpacing(16)

        # Nav buttons
        self._buttons: dict[str, _NavButton] = {}
        for key, icon, i18n_key in NAV_ITEMS:
            btn = _NavButton(icon, i18n.get_text(i18n_key), key)
            btn.clicked.connect(self._on_clicked)
            layout.addWidget(btn)
            self._buttons[key] = btn

        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Version label at bottom
        try:
            _v = version("macena-cs2-analyzer")
        except PackageNotFoundError:
            _v = "dev"
        self._version_label = QLabel(f"v{_v}")
        self._version_label.setObjectName("section_subtitle")
        self._version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._version_label)

    # ── Public API ──

    def set_active(self, key: str):
        """Update the checked state of nav buttons to highlight ``key``."""
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)
            btn._refresh_icon()

    def retranslate(self):
        """Update button labels when language changes."""
        for key, _icon, i18n_key in NAV_ITEMS:
            if key in self._buttons:
                btn = self._buttons[key]
                btn.update_label(i18n.get_text(i18n_key))
                btn.set_collapsed(self._is_collapsed)

    def toggle_collapse(self):
        """Animate between expanded (220px) and collapsed (60px) states."""
        self._is_collapsed = not self._is_collapsed
        target = _COLLAPSED_WIDTH if self._is_collapsed else _EXPANDED_WIDTH

        # Animate min/max width together for smooth resize
        anim_min = QPropertyAnimation(self, b"minimumWidth")
        anim_min.setDuration(200)
        anim_min.setEndValue(target)
        anim_min.setEasingCurve(QEasingCurve.OutCubic)

        anim_max = QPropertyAnimation(self, b"maximumWidth")
        anim_max.setDuration(200)
        anim_max.setEndValue(target)
        anim_max.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_group = QParallelAnimationGroup(self)
        self._anim_group.addAnimation(anim_min)
        self._anim_group.addAnimation(anim_max)
        self._anim_group.finished.connect(self._on_anim_finished)
        self._anim_group.start()

        # Update content immediately
        for btn in self._buttons.values():
            btn.set_collapsed(self._is_collapsed)
        self._title.setVisible(not self._is_collapsed)
        self._version_label.setVisible(not self._is_collapsed)

    @property
    def is_collapsed(self) -> bool:
        """Whether the sidebar is currently collapsed."""
        return self._is_collapsed

    # ── Internal ──

    def _on_anim_finished(self):
        target = _COLLAPSED_WIDTH if self._is_collapsed else _EXPANDED_WIDTH
        self.setFixedWidth(target)

    def _on_clicked(self):
        btn = self.sender()
        if isinstance(btn, _NavButton):
            self.nav_clicked.emit(btn.screen_key)
