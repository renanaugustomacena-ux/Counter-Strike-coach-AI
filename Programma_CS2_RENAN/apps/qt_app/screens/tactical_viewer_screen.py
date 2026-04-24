"""Tactical Viewer screen — 2D demo replay with playback controls."""

import logging
import os
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.qt_playback_engine import QtPlaybackEngine
from Programma_CS2_RENAN.apps.qt_app.core.web_bridge import MarqueeBridge
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.apps.qt_app.viewmodels.tactical_vm import (
    TacticalChronovisorVM,
    TacticalGhostVM,
    TacticalPlaybackVM,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.map_widget import TacticalMapWidget
from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.player_sidebar import PlayerSidebar
from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.timeline_widget import TimelineWidget
from Programma_CS2_RENAN.core.demo_frame import Team
from Programma_CS2_RENAN.core.playback_engine import InterpolatedFrame
from Programma_CS2_RENAN.observability.logger_setup import get_logger

logger = get_logger("cs2analyzer.qt_tactical_viewer")

# Path to the built web marquee app. Exists only after `pnpm build` has
# been run for web/tactical-viewer. If missing, we fall back to the
# Qt-native tactical viewer even when the toggle is ON so the screen
# never goes blank.
_WEB_DIST_INDEX = (
    Path(__file__).resolve().parent.parent / "web" / "tactical-viewer" / "dist" / "index.html"
)


class _DemoLoaderLogBridge(QObject):
    """Pipe `cs2analyzer.demo_loader` INFO lines into a Qt signal.

    `DemoLoader.load_demo` is a monolithic 500+ LoC function with no native
    progress callback — but it already emits informative INFO log lines
    ("Pass 1 - Extracting player positions", "Pass 2 - Linking grenades",
    "Resolving final game events", "Saving cache", etc). This bridge taps
    those records so the progress dialog can show live phase text instead
    of an opaque pulsing bar. The previous UX caused the user to cancel
    after 4 min of silence even though the parse had actually completed.

    Usage:
        bridge = _DemoLoaderLogBridge()
        bridge.phase_changed.connect(dialog.setLabelText)
        ...
        bridge.detach()
    """

    phase_changed = Signal(str)

    def __init__(self, parent: "QObject | None" = None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger("cs2analyzer.demo_loader")
        # Subclass Handler so we can emit Qt signals from a logging record.
        bridge = self

        class _Handler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                if record.levelno >= logging.INFO:
                    try:
                        bridge.phase_changed.emit(record.getMessage())
                    except RuntimeError:
                        # Bridge was deleted; ignore.
                        pass

        self._handler = _Handler(level=logging.INFO)
        self._logger.addHandler(self._handler)

    def detach(self) -> None:
        if self._handler is not None:
            self._logger.removeHandler(self._handler)
            self._handler = None


class TacticalViewerScreen(QWidget):
    """2D tactical replay viewer with playback, sidebars, and timeline."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # ViewModels
        self._playback_vm = TacticalPlaybackVM()
        self._ghost_vm = TacticalGhostVM()
        self._chronovisor_vm = TacticalChronovisorVM()

        # Playback engine
        self._engine = QtPlaybackEngine()
        self._playback_vm.set_engine(self._engine)
        self._playback_vm.frame_updated.connect(self._on_frame_update)

        # Chronovisor callbacks
        self._chronovisor_vm.navigate_to.connect(
            lambda tick, desc: self._playback_vm.seek_to_tick(tick)
        )

        # Data
        self._full_demo_data = {}
        self._game_events = []
        self._last_frame = None
        self._segments = {}

        # Worker reference — prevents GC of signal source
        self._current_worker = None
        self._progress_dialog = None
        self._log_bridge: "_DemoLoaderLogBridge | None" = None
        self._demo_cancelled: bool = False

        # Tick UI timer
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(100)
        self._tick_timer.timeout.connect(self._update_tick_ui)

        self._build_ui()

    def on_enter(self):
        self._tick_timer.start()
        self._timeline.set_seek_callback(self._on_seek)
        self._reposition_overlay()

    def on_leave(self):
        self._tick_timer.stop()

    def retranslate(self):
        """Update all translatable text when language changes."""
        self._title_label.setText(i18n.get_text("tactical_analyzer"))
        self._open_btn.setText(i18n.get_text("open_demo"))
        self._empty_overlay.setText(i18n.get_text("tactical_empty_state"))
        self._map_label.setText(i18n.get_text("select_map") + ":")
        self._round_label.setText(i18n.get_text("select_round") + ":")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_overlay()

    # ── WebEngine marquee host ──────────────────────────────────────────

    def _should_use_webengine(self) -> bool:
        """Pick the marquee path iff the toggle is ON *and* the build exists.

        We deliberately never leave the screen blank: if the user has
        flipped the toggle but forgot to run ``tools/build_web.py``, we
        log once and fall back to the Qt-native viewer. Opposite case
        (toggle off, dist present) is also fine — we just don't use it.
        """
        if not get_app_state().use_webengine_marquee:
            return False
        if not _WEB_DIST_INDEX.exists():
            logger.info(
                "use_webengine_marquee=True but %s missing — run "
                "tools/build_web.py to enable the WebEngine viewer; "
                "falling back to Qt-native for now",
                _WEB_DIST_INDEX,
            )
            return False
        return True

    def _build_webengine_host(self) -> QWidget:
        """Construct the QWebEngineView + QWebChannel + MarqueeBridge stack.

        Imports are lazy because QtWebEngine adds a heavy GPU-backed
        runtime — loading it at app import time slowed down Qt-native
        users for no reason. A single bridge instance is owned by this
        screen and wired to the playback ViewModel so the web side
        observes the same ticks the Qt-native map would.
        """
        from PySide6.QtCore import QUrl
        from PySide6.QtWebChannel import QWebChannel
        from PySide6.QtWebEngineWidgets import QWebEngineView

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        view = QWebEngineView(container)
        view.setContextMenuPolicy(Qt.NoContextMenu)
        layout.addWidget(view, 1)

        bridge = MarqueeBridge("bridge", parent=self)
        channel = QWebChannel(view.page())
        channel.registerObject("bridge", bridge)
        view.page().setWebChannel(channel)

        # Wire bridge → playback VM so web-side seek / ghost requests
        # drive the same engine the Qt-native path uses. This keeps
        # behaviour identical across modes.
        bridge.seek_requested.connect(self._on_seek)
        bridge.ghost_requested.connect(self._on_ghost_request_from_web)
        bridge.player_selected.connect(self._on_player_select)

        # Wire playback VM → bridge so the web app receives tick + frame
        # updates without any further plumbing. `_on_frame_update` is
        # the existing hook called on every interpolated frame; we tap
        # it by connecting an additional lambda that also forwards to
        # the bridge, preserving original Qt-native frame handling.
        self._playback_vm.frame_updated.connect(self._forward_frame_to_web)

        view.load(QUrl.fromLocalFile(str(_WEB_DIST_INDEX)))
        logger.info("WebEngine marquee loaded from %s", _WEB_DIST_INDEX)

        self._web_view = view
        self._web_bridge = bridge
        self._web_channel = channel
        return container

    def _on_ghost_request_from_web(self, tick: int) -> None:
        """Web asked for a ghost-AI overlay at a specific tick.

        Activate the GhostVM (cheap — idempotent), grab predictions for
        the current frame's players, normalize, and ship back via
        ``publish_ghost``. If the Ghost engine isn't available the
        bridge publishes an empty list so the web side can hide its
        overlay cleanly.
        """
        if self._web_bridge is None or self._last_frame is None:
            return
        from Programma_CS2_RENAN.core.spatial_engine import SpatialEngine

        self._ghost_vm.set_active(True)
        try:
            ghost_states = self._ghost_vm.predict_ghosts(self._last_frame.players)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("Ghost prediction failed: %s", exc)
            ghost_states = []
        map_name = getattr(self, "_current_map_for_web", None) or ""
        ghosts_payload = []
        for g in ghost_states:
            nx, ny = SpatialEngine.world_to_normalized(float(g.x), float(g.y), map_name)
            ghosts_payload.append(
                {
                    "id": int(getattr(g, "player_id", 0)),
                    "name": getattr(g, "name", ""),
                    "team": getattr(g.team, "name", str(g.team)),
                    "nx": nx,
                    "ny": ny,
                }
            )
        self._web_bridge.publish_ghost(ghosts_payload)

    def _forward_frame_to_web(self, frame) -> None:
        """Called on every interpolated frame; serialize the smallest
        payload the web app needs (players + nades + tick). Cheap JSON
        (no numpy arrays, no deep objects) so the bridge stays <200 us
        per frame even at 64 Hz.
        """
        if self._web_bridge is None:
            return
        try:
            players = [
                {
                    "id": int(p.player_id),
                    "name": getattr(p, "name", ""),
                    "team": getattr(p.team, "name", str(p.team)),
                    "x": float(p.x),
                    "y": float(p.y),
                    "is_alive": bool(getattr(p, "is_alive", True)),
                    "hp": int(getattr(p, "hp", 100)),
                }
                for p in (frame.players or [])
            ]
        except AttributeError:
            players = []
        payload = {
            "tick": int(getattr(frame, "tick", 0)),
            "players": players,
            "nades": [],  # rendered Qt-native for now; P4.0 full wires these too
        }
        self._web_bridge.publish_tick(payload["tick"])
        self._web_bridge.publish_frame(payload)

    def _reposition_overlay(self):
        """Center the empty-state overlay over the map widget.

        Guarded against pre-layout calls where parent width/height are 0 or
        below the minimum overlay footprint. Returning early leaves geometry
        untouched so the next resizeEvent re-triggers the math once the
        layout has resolved.
        """
        if not hasattr(self, "_empty_overlay"):
            return
        parent = self._empty_overlay.parentWidget()
        if not parent:
            return
        pw, ph = parent.width(), parent.height()
        # Skip if parent hasn't been laid out yet — setGeometry with negative
        # width/height silently hides the widget and never recovers without
        # another resizeEvent firing.
        if pw < 80 or ph < 80:
            return
        ow = min(500, max(200, pw - 40))
        oh = min(200, max(80, ph - 40))
        self._empty_overlay.setGeometry((pw - ow) // 2, (ph - oh) // 2, ow, oh)

    # ── UI Construction ──

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        header.setSpacing(12)
        self._title_label = QLabel(i18n.get_text("tactical_analyzer"))
        self._title_label.setObjectName("section_title")
        self._title_label.setFont(QFont("Roboto", 18, QFont.Bold))
        header.addWidget(self._title_label)
        header.addStretch()

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: #ff5555; font-size: 13px;")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        header.addWidget(self._error_label)

        self._open_btn = QPushButton(i18n.get_text("open_demo"))
        self._open_btn.setCursor(Qt.PointingHandCursor)
        self._open_btn.setFixedHeight(36)
        self._open_btn.clicked.connect(self._open_demo)
        header.addWidget(self._open_btn)
        root.addLayout(header)

        # Main area: CT sidebar + (Qt-native map OR WebEngine marquee) + T sidebar.
        # Decision is made at __init__ so a runtime toggle flip requires a
        # screen re-enter (restart-equivalent for this screen). Qt-native
        # path preserves every playback, ghost, chronovisor binding — the
        # marquee path treats the central map as the sole replacement.
        main_area = QHBoxLayout()
        main_area.setContentsMargins(0, 0, 0, 0)
        main_area.setSpacing(0)

        self._ct_sidebar = PlayerSidebar("CT", "#4d80ff")
        self._ct_sidebar.setFixedWidth(200)
        self._ct_sidebar.player_clicked.connect(self._on_player_select)
        main_area.addWidget(self._ct_sidebar)

        self._web_view = None
        self._web_bridge: MarqueeBridge | None = None
        self._web_channel = None  # type: ignore[assignment]
        if self._should_use_webengine():
            map_container = self._build_webengine_host()
            # In WebEngine mode the map_widget is still created (so the
            # rest of the screen code that touches it for frame updates
            # / player select doesn't crash), but it stays offscreen.
            self._map_widget = TacticalMapWidget()
            self._map_widget.selected_player_changed.connect(self._on_map_selection_changed)
            self._empty_overlay = QLabel("")
            self._empty_overlay.setParent(map_container)
            self._empty_overlay.setGeometry(0, 0, 0, 0)
            self._loading_overlay = QLabel("")
            self._loading_overlay.setParent(map_container)
            self._loading_overlay.hide()
        else:
            # Qt-native map: wrap in a container for the empty-state overlay
            map_container = QWidget()
            map_layout = QVBoxLayout(map_container)
            map_layout.setContentsMargins(0, 0, 0, 0)
            map_layout.setSpacing(0)

            self._map_widget = TacticalMapWidget()
            self._map_widget.selected_player_changed.connect(self._on_map_selection_changed)
            map_layout.addWidget(self._map_widget, 1)

            # Empty-state overlay
            self._empty_overlay = QLabel(i18n.get_text("tactical_empty_state"))
            self._empty_overlay.setAlignment(Qt.AlignCenter)
            self._empty_overlay.setFont(QFont("Roboto", 16))
            self._empty_overlay.setStyleSheet(
                "color: #707090; background: rgba(10, 10, 20, 180); "
                "border-radius: 12px; padding: 32px;"
            )
            self._empty_overlay.setParent(map_container)
            self._empty_overlay.setGeometry(0, 0, 0, 0)  # sized in resizeEvent

            # Loading overlay (UX-2: map switch indicator)
            self._loading_overlay = QLabel("Loading map...")
            self._loading_overlay.setAlignment(Qt.AlignCenter)
            self._loading_overlay.setFont(QFont("Roboto", 14))
            self._loading_overlay.setStyleSheet(
                "color: #e0e0e0; background: rgba(10, 10, 20, 200); "
                "border-radius: 12px; padding: 24px;"
            )
            self._loading_overlay.setParent(map_container)
            self._loading_overlay.hide()

        main_area.addWidget(map_container, 1)

        self._t_sidebar = PlayerSidebar("T", "#ff9933")
        self._t_sidebar.setFixedWidth(200)
        self._t_sidebar.player_clicked.connect(self._on_player_select)
        main_area.addWidget(self._t_sidebar)

        root.addLayout(main_area, 1)

        # Control panel
        control_panel = self._build_controls()
        root.addWidget(control_panel)

    def _build_controls(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("QFrame { background-color: #0f0f1a; border-top: 1px solid #2a2a3a; }")
        panel.setFixedHeight(130)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(4)

        # Row 1: selectors
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        self._map_combo = QComboBox()
        self._map_combo.setFixedWidth(140)
        self._map_combo.currentTextChanged.connect(self._on_map_changed)
        self._map_label = QLabel(i18n.get_text("select_map") + ":")
        row1.addWidget(self._map_label)
        row1.addWidget(self._map_combo)

        self._round_combo = QComboBox()
        self._round_combo.setFixedWidth(120)
        self._round_combo.currentTextChanged.connect(self._on_round_changed)
        self._round_label = QLabel(i18n.get_text("select_round") + ":")
        row1.addWidget(self._round_label)
        row1.addWidget(self._round_combo)

        self._tick_label = QLabel("Tick 0")
        self._tick_label.setObjectName("tick_counter")
        self._tick_label.setMinimumWidth(120)
        row1.addWidget(self._tick_label)

        row1.addStretch()

        self._ghost_check = QCheckBox("Ghost AI")
        self._ghost_check.setObjectName("ghost_toggle")
        self._ghost_check.toggled.connect(self._ghost_vm.set_active)
        row1.addWidget(self._ghost_check)

        layout.addLayout(row1)

        # Row 2: playback controls.
        # Unicode transport glyphs render via system font fallback; we keep
        # setObjectName("playback_control") so the tight-padding QSS rule
        # overrides the global QPushButton padding (otherwise 8px 20px on
        # a 40x40 fixed-size button clips the glyph to zero width — that
        # was the "blank buttons" bug the user reported post-P1).
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        prev_cm_btn = QPushButton("⏮")  # ⏮ Skip backward
        prev_cm_btn.setObjectName("playback_control")
        prev_cm_btn.setFixedSize(40, 40)
        prev_cm_btn.setCursor(Qt.PointingHandCursor)
        prev_cm_btn.setToolTip("Previous critical moment")
        prev_cm_btn.clicked.connect(self._jump_prev_cm)
        row2.addWidget(prev_cm_btn)

        self._play_btn = QPushButton("▶")  # ▶ Play
        self._play_btn.setObjectName("playback_control")
        self._play_btn.setFixedSize(48, 40)
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.setToolTip("Play / Pause")
        self._play_btn.clicked.connect(self._toggle_playback)
        row2.addWidget(self._play_btn)

        next_cm_btn = QPushButton("⏭")  # ⏭ Skip forward
        next_cm_btn.setObjectName("playback_control")
        next_cm_btn.setFixedSize(40, 40)
        next_cm_btn.setCursor(Qt.PointingHandCursor)
        next_cm_btn.setToolTip("Next critical moment")
        next_cm_btn.clicked.connect(self._jump_next_cm)
        row2.addWidget(next_cm_btn)

        row2.addSpacing(16)

        self._speed_buttons: list[QPushButton] = []
        # U+00D7 multiplication sign reads cleaner than ASCII 'x' in monospace
        for speed in [0.5, 1.0, 2.0, 4.0]:
            label = f"{speed:g}×"
            btn = QPushButton(label)
            btn.setObjectName("speed_button")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumWidth(54)
            btn.clicked.connect(lambda _checked=False, s=speed, b=btn: self._set_speed(s, b))
            if speed == 1.0:
                btn.setProperty("state", "active")
            self._speed_buttons.append(btn)
            row2.addWidget(btn)

        row2.addStretch()
        layout.addLayout(row2)

        # Timeline
        self._timeline = TimelineWidget()
        layout.addWidget(self._timeline)

        return panel

    # ── Demo Loading ──

    def _open_demo(self):
        from Programma_CS2_RENAN.core.config import get_setting

        start_dir = get_setting("DEFAULT_DEMO_PATH", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Demo File", start_dir, "Demo files (*.dem)"
        )
        if not path:
            return

        # FE-03 (AUDIT §9): Qt's filter `*.dem` is a UI hint, not enforcement.
        # Users can type any path manually (and some OS dialogs accept it).
        # Resolve symlinks, verify extension + size before handing a C
        # extension (demoparser2) an arbitrary file — a `.dem → /etc/shadow`
        # symlink would otherwise be read into the parser's exception text.
        try:
            resolved = os.path.realpath(path)
        except (OSError, ValueError) as exc:
            logger.warning("Demo path resolution failed for %s: %s", path, exc)
            self._show_error("Invalid demo path")
            return
        if not resolved.lower().endswith(".dem"):
            logger.warning("Demo path rejected — not a .dem file: %s", resolved)
            self._show_error("Selected file is not a .dem demo")
            return
        try:
            # DS-12: MIN_DEMO_SIZE=10MB is the ingestion invariant; enforce
            # it at UI load too so sub-threshold files fail fast with a
            # readable error instead of a cryptic parser crash.
            from Programma_CS2_RENAN.backend.data_sources.demo_format_adapter import MIN_DEMO_SIZE

            size = os.path.getsize(resolved)
        except OSError as exc:
            logger.warning("Demo path stat failed for %s: %s", resolved, exc)
            self._show_error("Unable to read selected file")
            return
        if size < MIN_DEMO_SIZE:
            logger.warning(
                "Demo path rejected — %d bytes below MIN_DEMO_SIZE (%d): %s",
                size,
                MIN_DEMO_SIZE,
                resolved,
            )
            self._show_error(
                f"File too small to be a valid CS2 demo "
                f"({size // 1024} KB < {MIN_DEMO_SIZE // 1024 // 1024} MB)"
            )
            return
        path = resolved

        logger.info("Loading demo: %s", path)
        self._play_btn.setText("...")
        self._play_btn.setEnabled(False)
        self._error_label.setVisible(False)

        # Show loading dialog with cancel button
        self._demo_cancelled = False
        demo_basename = os.path.basename(path)
        self._progress_dialog = QProgressDialog(
            f"Parsing {demo_basename}...\n\n"
            "Waiting for first phase (header + player positions)...\n"
            "Cached demos load instantly on subsequent opens.",
            "Cancel",
            0,
            0,  # Indeterminate (0, 0 = pulsing bar)
            self,
        )
        self._progress_dialog.setWindowTitle("Loading Demo")
        self._progress_dialog.setWindowModality(Qt.WindowModal)
        self._progress_dialog.setMinimumDuration(0)
        self._progress_dialog.canceled.connect(self._on_demo_cancel)
        self._progress_dialog.show()

        # Pipe demo_loader phase logs into the dialog so 4-minute parses
        # are not opaque. The alternative (previously shipped) was an
        # indeterminate spinner with no text updates — user cancelled
        # because they could not distinguish "still working" from "hung".
        self._log_bridge = _DemoLoaderLogBridge(self)
        self._log_bridge.phase_changed.connect(
            lambda msg: self._progress_dialog
            and self._progress_dialog.setLabelText(f"Parsing {demo_basename}...\n\n{msg}")
        )

        def _parse_demo(demo_path):
            from Programma_CS2_RENAN.ingestion.demo_loader import DemoLoader

            loader = DemoLoader()
            return loader.load_demo(demo_path)

        worker = Worker(_parse_demo, path)
        worker.signals.result.connect(self._on_demo_loaded)
        worker.signals.error.connect(self._on_demo_error)
        self._current_worker = worker  # Prevent GC of signal source
        QThreadPool.globalInstance().start(worker)

    def _on_demo_cancel(self):
        """User cancelled demo loading.

        The underlying `DemoLoader.load_demo` is a synchronous C-extension
        (demoparser2) call with no cooperative cancel hook — so cancelling
        here does NOT stop the parse; the worker thread keeps going until
        the parser returns. Previously we ALSO discarded the eventual
        result, which meant a 4-minute parse that finished 6 seconds after
        a cancel click was silently thrown away (observed in logs
        2026-04-24T11:54:03 → 11:54:09). That is worse than no cancel at
        all: user saw "loading finished, nothing happened" and lost the
        work. Now cancel only hides the dialog; the result, when it
        arrives, is still shown (and the cache write means re-opens are
        instant).
        """
        self._demo_cancelled = True
        self._progress_dialog = None
        self._play_btn.setEnabled(True)
        self._play_btn.setText("Play")
        logger.info(
            "Demo loading cancel requested — parse continues in background; "
            "result will be shown when it arrives"
        )

    def _on_demo_loaded(self, data: dict):
        self._current_worker = None
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None
        if self._log_bridge is not None:
            self._log_bridge.detach()
            self._log_bridge = None

        # If user cancelled mid-parse, surface the recovered result rather
        # than silently discarding a successful 4-minute parse (the
        # previous behaviour that caused the "loading finished, nothing
        # happened" bug report).
        if self._demo_cancelled:
            logger.info(
                "Demo parse finished after user cancel — surfacing result; "
                "cache has been written, re-open will be instant"
            )
            self._demo_cancelled = False

        # Surface the raw shape so a broken parse produces actionable logs
        # instead of a silent blank viewer.
        raw_keys = list(data.keys()) if isinstance(data, dict) else []
        logger.info(
            "Demo parse returned %s with %d top-level key(s): %s",
            type(data).__name__,
            len(raw_keys),
            raw_keys,
        )

        if not isinstance(data, dict):
            self._on_demo_error(f"Demo parser returned {type(data).__name__}, expected dict.")
            return

        # Filter out _-prefixed metadata keys (e.g., _map_tensors, _quality_flags)
        # and surface non-tuple-shaped entries as INFO so a cache-format drift
        # shows up in logs instead of silently emptying the viewer.
        map_data = {}
        rejected = []
        for k, v in data.items():
            if isinstance(v, tuple) and len(v) == 3:
                map_data[k] = v
            else:
                rejected.append((k, type(v).__name__))

        if rejected:
            logger.info("Filtered %d non-map key(s) from demo data: %s", len(rejected), rejected)

        if not map_data:
            self._on_demo_error(
                "No valid map data found in demo file. "
                f"Top-level keys present: {raw_keys}. "
                "Expected a dict of map_name -> (frames, events, segments) tuples."
            )
            return

        # Report per-map frame counts so a parse that produces zero frames
        # (which otherwise results in a blank map with no player dots)
        # is visible in the log.
        for map_name, (frames, events, segments) in map_data.items():
            logger.info(
                "Map %r: %d frames, %d events, %d segment(s)",
                map_name,
                len(frames) if frames is not None else 0,
                len(events) if events is not None else 0,
                len(segments) if segments is not None else 0,
            )

        self._full_demo_data = map_data
        self._play_btn.setEnabled(True)
        self._play_btn.setText("Play")
        self._error_label.setVisible(False)
        self._empty_overlay.setVisible(False)

        # Populate map combo
        self._map_combo.blockSignals(True)
        self._map_combo.clear()
        self._map_combo.addItems(list(map_data.keys()))
        self._map_combo.blockSignals(False)

        # Switch to first map
        if map_data:
            first_map = list(map_data.keys())[0]
            self._map_combo.setCurrentText(first_map)
            self._switch_map(first_map)

        logger.info("Demo loaded: %d map(s): %s", len(map_data), list(map_data.keys()))

    def _on_demo_error(self, error: str):
        self._current_worker = None
        if self._progress_dialog:
            self._progress_dialog.close()
            self._progress_dialog = None
        if self._log_bridge is not None:
            self._log_bridge.detach()
            self._log_bridge = None

        self._play_btn.setEnabled(True)
        self._play_btn.setText("Play")
        logger.error("Demo load failed: %s", error)
        self._show_error(error, modal=True)

    def _show_error(self, message: str, modal: bool = False) -> None:
        """Display an error message.

        ``modal=True`` raises a QMessageBox so demo-load failures cannot be
        missed by the user (the previous header-label-only path was too
        easy to overlook against a dark background). ``modal=False`` keeps
        the inline label for low-severity validation errors where the file
        dialog just returned an invalid pick.
        """
        self._error_label.setText(f"Error: {message}")
        self._error_label.setVisible(True)
        if modal:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Demo Load Failed")
            box.setText("The selected demo could not be loaded.")
            box.setInformativeText(message)
            box.setStandardButtons(QMessageBox.Ok)
            box.exec()

    # ── Map/Round Switching ──

    def _switch_map(self, map_name: str):
        if map_name not in self._full_demo_data:
            return

        # UX-2: Show loading overlay during map switch
        self._loading_overlay.setText(f"Loading {map_name}...")
        self._loading_overlay.setGeometry(self._map_widget.geometry())
        self._loading_overlay.show()
        self._loading_overlay.raise_()
        QApplication.processEvents()

        frames, events, segments = self._full_demo_data[map_name]
        self._game_events = events
        self._segments = segments
        # Track the map name so _forward_frame_to_web can normalize
        # world coordinates via SpatialEngine for the right radar.
        self._current_map_for_web = map_name

        # Clear sidebars
        self._ct_sidebar.clear_all()
        self._t_sidebar.clear_all()

        # Update map
        self._map_widget.set_map(map_name)

        # Publish map + segments + events to the web marquee (no-op
        # when WebEngine path is off).
        if self._web_bridge is not None:
            self._web_bridge.publish_map(map_name)
            self._web_bridge.publish_segments(dict(segments))
            event_payloads = []
            for ev in events or []:
                tick = int(getattr(ev, "tick", 0))
                event_payloads.append(
                    {
                        "tick": tick,
                        "kind": getattr(
                            getattr(ev, "event_type", None),
                            "name",
                            str(getattr(ev, "event_type", "")),
                        ),
                        "attacker": int(getattr(ev, "attacker_id", 0) or 0),
                        "victim": int(getattr(ev, "victim_id", 0) or 0),
                    }
                )
            self._web_bridge.publish_events(event_payloads)

        # Load frames
        self._playback_vm.load_frames(frames)

        # Update timeline
        self._timeline.max_tick = self._playback_vm.total_ticks
        self._timeline.set_events(events)

        # Round combo
        self._round_combo.blockSignals(True)
        self._round_combo.clear()
        self._round_combo.addItems(list(segments.keys()))
        self._round_combo.blockSignals(False)
        if segments:
            self._round_combo.setCurrentIndex(0)

        # Seek to start
        self._playback_vm.seek_to_tick(0)

        # Clear chronovisor
        self._chronovisor_vm.clear()

        # UX-2: Hide loading overlay
        self._loading_overlay.hide()

    def _on_map_changed(self, text: str):
        if text:
            self._switch_map(text)

    def _on_round_changed(self, text: str):
        if text in self._segments:
            self._on_seek(self._segments[text])

    # ── Frame Rendering ──

    def _on_frame_update(self, frame: InterpolatedFrame):
        self._last_frame = frame

        ghosts = self._ghost_vm.predict_ghosts(frame.players)
        self._map_widget.update_map(frame.players, frame.nades, ghosts, frame.tick)

        ct_players = [p for p in frame.players if p.team == Team.CT]
        t_players = [p for p in frame.players if p.team == Team.T]
        selected = self._map_widget.selected_player_id
        self._ct_sidebar.update_players(ct_players, selected)
        self._t_sidebar.update_players(t_players, selected)

    def _update_tick_ui(self):
        tick = self._playback_vm.get_current_tick()
        self._tick_label.setText(f"Tick {tick:,}")
        self._timeline.current_tick = tick
        playing = self._playback_vm.is_playing
        # U+23F8 is the pause glyph; U+25B6 the play glyph. The "state"
        # property drives the QSS accent-fill rule (#playback_control
        # [state="playing"]) so the button visually reflects the mode.
        self._play_btn.setText("⏸" if playing else "▶")
        self._play_btn.setProperty("state", "playing" if playing else "")
        self._play_btn.style().unpolish(self._play_btn)
        self._play_btn.style().polish(self._play_btn)

    # ── Playback Controls ──

    def _toggle_playback(self):
        self._playback_vm.toggle_playback()

    def _set_speed(self, speed: float, active_btn: QPushButton | None = None):
        self._playback_vm.set_speed(speed)
        # Sync visual active-state across the speed button row.
        for btn in getattr(self, "_speed_buttons", []):
            is_active = btn is active_btn
            btn.setProperty("state", "active" if is_active else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_seek(self, tick: int):
        self._playback_vm.seek_to_tick(tick)

    # ── Player Selection ──

    def _on_player_select(self, player_id: int):
        self._map_widget.selected_player_id = player_id

    def _on_map_selection_changed(self, player_id):
        if self._last_frame:
            ct = [p for p in self._last_frame.players if p.team == Team.CT]
            t = [p for p in self._last_frame.players if p.team == Team.T]
            self._ct_sidebar.update_players(ct, player_id)
            self._t_sidebar.update_players(t, player_id)

    # ── Chronovisor ──

    def _jump_next_cm(self):
        tick = self._playback_vm.get_current_tick()
        self._chronovisor_vm.jump_to_next(tick)

    def _jump_prev_cm(self):
        tick = self._playback_vm.get_current_tick()
        self._chronovisor_vm.jump_to_prev(tick)
