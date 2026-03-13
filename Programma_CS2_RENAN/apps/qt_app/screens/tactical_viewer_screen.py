"""Tactical Viewer screen — 2D demo replay with playback controls."""

from PySide6.QtCore import QRunnable, QThreadPool, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.qt_playback_engine import QtPlaybackEngine
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


class _LoadWorkerSignals(Signal):
    pass


class _LoadWorker(QRunnable):
    """Background worker for demo parsing."""

    class Signals(QWidget):
        result = Signal(object)
        error = Signal(str)

        def __init__(self):
            super().__init__()
            self.setVisible(False)

    def __init__(self, path: str):
        super().__init__()
        self._path = path
        self.signals = _LoadWorker.Signals()

    @Slot()
    def run(self):
        try:
            from Programma_CS2_RENAN.ingestion.demo_loader import DemoLoader

            loader = DemoLoader()
            data = loader.load_demo(self._path)
            self.signals.result.emit(data)
        except Exception as e:
            self.signals.error.emit(str(e))


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

        # Tick UI timer
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(100)
        self._tick_timer.timeout.connect(self._update_tick_ui)

        self._build_ui()

    def on_enter(self):
        self._tick_timer.start()
        self._timeline.set_seek_callback(self._on_seek)

    def on_leave(self):
        self._tick_timer.stop()

    # ── UI Construction ──

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        header.setSpacing(12)
        title = QLabel("Tactical Analyzer")
        title.setObjectName("section_title")
        title.setFont(QFont("Roboto", 18, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        open_btn = QPushButton("Open Demo")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.setFixedHeight(36)
        open_btn.clicked.connect(self._open_demo)
        header.addWidget(open_btn)
        root.addLayout(header)

        # Main area: CT sidebar + map + T sidebar
        main_area = QHBoxLayout()
        main_area.setContentsMargins(0, 0, 0, 0)
        main_area.setSpacing(0)

        self._ct_sidebar = PlayerSidebar("CT", "#4d80ff")
        self._ct_sidebar.setFixedWidth(200)
        self._ct_sidebar.player_clicked.connect(self._on_player_select)
        main_area.addWidget(self._ct_sidebar)

        self._map_widget = TacticalMapWidget()
        self._map_widget.selected_player_changed.connect(self._on_map_selection_changed)
        main_area.addWidget(self._map_widget, 1)

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
        panel.setStyleSheet(
            "QFrame { background-color: #0f0f1a; border-top: 1px solid #2a2a3a; }"
        )
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
        row1.addWidget(QLabel("Map:"))
        row1.addWidget(self._map_combo)

        self._round_combo = QComboBox()
        self._round_combo.setFixedWidth(120)
        self._round_combo.currentTextChanged.connect(self._on_round_changed)
        row1.addWidget(QLabel("Round:"))
        row1.addWidget(self._round_combo)

        self._tick_label = QLabel("Tick: 0")
        self._tick_label.setStyleSheet("color: #a0a0b0; font-size: 12px;")
        self._tick_label.setFixedWidth(100)
        row1.addWidget(self._tick_label)

        row1.addStretch()

        self._ghost_check = QCheckBox("Ghost AI")
        self._ghost_check.setStyleSheet("color: #a0a0b0;")
        self._ghost_check.toggled.connect(self._ghost_vm.set_active)
        row1.addWidget(self._ghost_check)

        layout.addLayout(row1)

        # Row 2: playback controls
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        prev_cm_btn = QPushButton("\u23ee")
        prev_cm_btn.setFixedSize(36, 36)
        prev_cm_btn.setCursor(Qt.PointingHandCursor)
        prev_cm_btn.setToolTip("Previous critical moment")
        prev_cm_btn.clicked.connect(self._jump_prev_cm)
        row2.addWidget(prev_cm_btn)

        self._play_btn = QPushButton("\u25b6")
        self._play_btn.setFixedSize(40, 36)
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.clicked.connect(self._toggle_playback)
        row2.addWidget(self._play_btn)

        next_cm_btn = QPushButton("\u23ed")
        next_cm_btn.setFixedSize(36, 36)
        next_cm_btn.setCursor(Qt.PointingHandCursor)
        next_cm_btn.setToolTip("Next critical moment")
        next_cm_btn.clicked.connect(self._jump_next_cm)
        row2.addWidget(next_cm_btn)

        row2.addSpacing(16)

        for speed in [0.5, 1.0, 2.0, 4.0]:
            btn = QPushButton(f"{speed}x")
            btn.setFixedWidth(50)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, s=speed: self._set_speed(s))
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

        logger.info("Loading demo: %s", path)
        self._play_btn.setText("\u231b")
        self._play_btn.setEnabled(False)

        worker = _LoadWorker(path)
        worker.signals.result.connect(self._on_demo_loaded)
        worker.signals.error.connect(self._on_demo_error)
        QThreadPool.globalInstance().start(worker)

    def _on_demo_loaded(self, data: dict):
        self._full_demo_data = data
        self._play_btn.setEnabled(True)
        self._play_btn.setText("\u25b6")

        # Populate map combo
        self._map_combo.blockSignals(True)
        self._map_combo.clear()
        self._map_combo.addItems(list(data.keys()))
        self._map_combo.blockSignals(False)

        # Switch to first map
        if data:
            first_map = list(data.keys())[0]
            self._map_combo.setCurrentText(first_map)
            self._switch_map(first_map)

        logger.info("Demo loaded: %d map(s)", len(data))

    def _on_demo_error(self, error: str):
        self._play_btn.setEnabled(True)
        self._play_btn.setText("\u25b6")
        logger.error("Demo load failed: %s", error)

    # ── Map/Round Switching ──

    def _switch_map(self, map_name: str):
        if map_name not in self._full_demo_data:
            return

        frames, events, segments = self._full_demo_data[map_name]
        self._game_events = events
        self._segments = segments

        # Clear sidebars
        self._ct_sidebar.clear_all()
        self._t_sidebar.clear_all()

        # Update map
        self._map_widget.set_map(map_name)

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
        self._tick_label.setText(f"Tick: {tick}")
        self._timeline.current_tick = tick
        self._play_btn.setText("\u23f8" if self._playback_vm.is_playing else "\u25b6")

    # ── Playback Controls ──

    def _toggle_playback(self):
        self._playback_vm.toggle_playback()

    def _set_speed(self, speed: float):
        self._playback_vm.set_speed(speed)

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
