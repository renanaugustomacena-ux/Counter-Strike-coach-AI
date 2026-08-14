"""Tactical Viewer screen — 2D demo replay with playback controls."""

import logging
import os
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPolygonF
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.app_state import get_app_state
from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.qt_playback_engine import QtPlaybackEngine
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.core.web_bridge import MarqueeBridge
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button
from Programma_CS2_RENAN.apps.qt_app.core.worker import Worker
from Programma_CS2_RENAN.apps.qt_app.viewmodels.tactical_vm import (
    TacticalChronovisorVM,
    TacticalGhostVM,
    TacticalPlaybackVM,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.mono_footer import MonoFooter
from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.map_widget import TacticalMapWidget
from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.player_sidebar import PlayerSidebar
from Programma_CS2_RENAN.apps.qt_app.widgets.tactical.timeline_widget import (
    GLYPH_LEGEND,
    TimelineWidget,
)
from Programma_CS2_RENAN.core.demo_frame import Team
from Programma_CS2_RENAN.core.playback_engine import InterpolatedFrame
from Programma_CS2_RENAN.core.tick_rate import DEFAULT_TICK_RATE
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


def _caption_font(*, bold: bool = False) -> "QFont":
    """Caption-sized BODY font (size from tokens) without the caption role's
    uppercase treatment — ghost-panel metadata stays lowercase per frame 14.
    Mono captions now come from ``Typography.mono_caption``."""
    f = Typography.font("body", QFont.Bold if bold else None)
    f.setPointSize(get_tokens().font_size_caption)
    return f


# Fixed metric order of the frame-14 divergence grid.
_DIVERGENCE_METRICS = (
    ("entry_timing", "tactical.entry_timing", "Entry timing"),
    ("peek_angle", "tactical.peek_angle", "Peek angle"),
    ("flash_support", "tactical.flash_support", "Flash support"),
    ("crouch_ratio", "tactical.crouch_ratio", "Crouch ratio"),
    ("crosshair_placement", "tactical.crosshair_placement", "Crosshair placement"),
    ("outcome", "tactical.outcome", "Outcome"),
)


def _divergence_rows(ghost_payload: "dict | None") -> list[tuple[str, str, str]]:
    """Adapter: ghost payload → 6 ``(label, value, verdict)`` rows.

    Reads ONLY the ``divergence`` dict the payload actually carries; every
    absent metric renders as an em-dash with a neutral verdict (Locked
    Decision 8 — no backend model changes this pass).
    FIELD-GAP: TacticalGhostVM exposes none of these metrics today; the
    shape mirrors what a divergence-capable VM payload WOULD provide
    (per-metric ``{"value", "verdict"}`` dicts or bare scalars).
    """
    divergence = (ghost_payload or {}).get("divergence")
    if not isinstance(divergence, dict):
        divergence = {}
    rows: list[tuple[str, str, str]] = []
    for field, key, fallback in _DIVERGENCE_METRICS:
        raw = divergence.get(field)
        if isinstance(raw, dict):
            value = str(raw.get("value") or "—")
            verdict = str(raw.get("verdict") or "neutral")
        elif raw not in (None, ""):
            value, verdict = str(raw), "neutral"
        else:
            value, verdict = "—", "neutral"
        rows.append((i18n.get_text(key, fallback), value, verdict))
    return rows


class _GhostPanel(QWidget):
    """Frame-14 left panel: YOU card, GHOST card, divergence analysis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        tokens = get_tokens()
        self.setFixedWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing_lg, tokens.spacing_lg, tokens.spacing_md, tokens.spacing_lg
        )
        layout.setSpacing(tokens.spacing_sm)

        def card() -> tuple[QFrame, QVBoxLayout]:
            frame = QFrame()
            frame.setObjectName("ghost_card")
            box = QVBoxLayout(frame)
            box.setContentsMargins(
                tokens.spacing_md, tokens.spacing_md, tokens.spacing_md, tokens.spacing_md
            )
            box.setSpacing(tokens.spacing_xs)
            return frame, box

        def caption_label(color: str) -> QLabel:
            label = QLabel()
            label.setFont(_caption_font())
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {color}; background: transparent;")
            return label

        # YOU section — caption-size bold WITHOUT the caption role's
        # uppercase/letterspacing (frame 14 keeps names lowercase and the
        # 240px panel can't spare the tracking).
        self._you_header = QLabel()
        self._you_header.setFont(_caption_font(bold=True))
        self._you_header.setStyleSheet(
            f"color: {tokens.chart_line_secondary}; background: transparent;"
        )
        layout.addWidget(self._you_header)
        you_card, you_box = card()
        you_card.setStyleSheet(
            f"QFrame#ghost_card {{ background: {tokens.surface_raised}; "
            f"border: 1px solid {tokens.border_subtle}; border-radius: {tokens.radius_md}px; }}"
        )
        self._you_title = QLabel()
        self._you_title.setFont(Typography.font("body", QFont.Bold))
        self._you_title.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        you_box.addWidget(self._you_title)
        self._you_path = caption_label(tokens.text_secondary)
        you_box.addWidget(self._you_path)
        self._you_decision = caption_label(tokens.text_secondary)
        you_box.addWidget(self._you_decision)
        layout.addWidget(you_card)

        # GHOST section — frame purple has no token; `info` is the approved
        # in-system analog for the ghost channel.
        self._ghost_header = QLabel()
        self._ghost_header.setFont(_caption_font(bold=True))
        self._ghost_header.setStyleSheet(f"color: {tokens.info}; background: transparent;")
        layout.addWidget(self._ghost_header)
        ghost_card, ghost_box = card()
        ghost_card.setStyleSheet(
            f"QFrame#ghost_card {{ background: {tokens.surface_raised}; "
            f"border: 1px solid {tokens.info}; border-radius: {tokens.radius_md}px; }}"
        )
        self._ghost_title = QLabel()
        self._ghost_title.setFont(Typography.font("body", QFont.Bold))
        self._ghost_title.setStyleSheet(f"color: {tokens.text_primary}; background: transparent;")
        ghost_box.addWidget(self._ghost_title)
        self._ghost_path = caption_label(tokens.text_secondary)
        ghost_box.addWidget(self._ghost_path)
        self._ghost_decision = caption_label(tokens.info)
        ghost_box.addWidget(self._ghost_decision)
        layout.addWidget(ghost_card)

        # DIVERGENCE ANALYSIS
        div_card, div_box = card()
        div_card.setStyleSheet(
            f"QFrame#ghost_card {{ background: {tokens.surface_raised}; "
            f"border: 1px solid {tokens.border_subtle}; border-radius: {tokens.radius_md}px; }}"
        )
        self._div_header = QLabel()
        self._div_header.setFont(_caption_font(bold=True))
        self._div_header.setStyleSheet(f"color: {tokens.accent_primary}; background: transparent;")
        div_box.addWidget(self._div_header)
        self._div_grid = QGridLayout()
        self._div_grid.setHorizontalSpacing(tokens.spacing_sm)
        self._div_grid.setVerticalSpacing(tokens.spacing_xs + 1)
        self._div_grid.setColumnStretch(0, 0)
        self._div_grid.setColumnStretch(1, 1)
        div_box.addLayout(self._div_grid)
        div_box.addSpacing(tokens.spacing_sm)
        self._causal_caption = caption_label(tokens.text_tertiary)
        div_box.addWidget(self._causal_caption)
        self._causal_stat = QLabel()
        self._causal_stat.setFont(Typography.font("subtitle"))
        self._causal_stat.setStyleSheet(f"color: {tokens.accent_primary}; background: transparent;")
        div_box.addWidget(self._causal_stat)
        self._causal_bar = QProgressBar()
        self._causal_bar.setRange(0, 100)
        self._causal_bar.setFixedHeight(6)
        self._causal_bar.setTextVisible(False)
        self._causal_bar.setStyleSheet(
            f"QProgressBar {{ background-color: {tokens.surface_sunken}; border: none; "
            f"border-radius: {tokens.radius_sm // 2}px; }}"
            f"QProgressBar::chunk {{ background-color: {tokens.accent_primary}; "
            f"border-radius: {tokens.radius_sm // 2}px; }}"
        )
        div_box.addWidget(self._causal_bar)
        layout.addWidget(div_card)
        layout.addStretch()

    def set_payload(self, payload: dict) -> None:
        tokens = get_tokens()
        you = payload.get("you") if isinstance(payload.get("you"), dict) else {}
        ghost = payload.get("ghost") if isinstance(payload.get("ghost"), dict) else {}

        player = payload.get("player") or "—"
        self._you_header.setText(f"{i18n.get_text('tactical.you', 'YOU')} · {player}")
        side, map_name = you.get("side") or "—", payload.get("map") or you.get("map") or "—"
        self._you_title.setText(
            i18n.get_text("tactical.side_map", "{side} side · {map}")
            .replace("{side}", str(side))
            .replace("{map}", str(map_name))
        )
        path_tpl = i18n.get_text("tactical.path", "Path: {path}")
        decision_tpl = i18n.get_text("tactical.decision_time", "Decision time: {d}")
        self._you_path.setText(path_tpl.replace("{path}", str(you.get("path") or "—")))
        self._you_decision.setText(decision_tpl.replace("{d}", str(you.get("decision") or "—")))

        pro, team = payload.get("pro") or "—", payload.get("team")
        ghost_name = f"{pro} ({team})" if team else str(pro)
        self._ghost_header.setText(f"{i18n.get_text('tactical.ghost', 'GHOST')} · {ghost_name}")
        self._ghost_title.setText(str(ghost.get("context") or "—"))
        self._ghost_path.setText(path_tpl.replace("{path}", str(ghost.get("path") or "—")))
        self._ghost_decision.setText(decision_tpl.replace("{d}", str(ghost.get("decision") or "—")))

        self._div_header.setText(
            i18n.get_text("tactical.divergence_analysis", "DIVERGENCE ANALYSIS")
        )
        while self._div_grid.count():
            item = self._div_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        verdict_colors = {
            "good": tokens.success,
            "bad": tokens.error,
            "warn": tokens.warning,
        }
        for row, (label, value, verdict) in enumerate(_divergence_rows(payload)):
            name = QLabel(label)
            name.setFont(_caption_font())
            name.setWordWrap(True)
            name.setStyleSheet(f"color: {tokens.text_secondary}; background: transparent;")
            self._div_grid.addWidget(name, row, 0)
            val = QLabel(value)
            val.setFont(Typography.mono_caption(bold=True))
            val.setWordWrap(True)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            color = verdict_colors.get(verdict, tokens.text_primary)
            val.setStyleSheet(f"color: {color}; background: transparent;")
            self._div_grid.addWidget(val, row, 1)

        self._causal_caption.setText(
            i18n.get_text("tactical.causal_score", "Causal score (RAPPedagogy)")
        )
        causal = payload.get("causal") if isinstance(payload.get("causal"), dict) else {}
        score, factor = causal.get("top_score"), causal.get("top_factor")
        if isinstance(score, (int, float)):
            self._causal_stat.setText(f"{score:.2f} {factor}" if factor else f"{score:.2f}")
            self._causal_bar.setValue(int(max(0.0, min(1.0, float(score))) * 100))
        else:
            # FIELD-GAP: no causal attribution source on the VM yet.
            self._causal_stat.setText("—")
            self._causal_bar.setValue(0)


class _TransportIconButton(QPushButton):
    """Prev/next critical-moment button with a QPainter-drawn skip glyph.

    The previous unicode glyphs (U+23EE / U+23ED) render as tofu boxes on
    the offscreen platform's fallback fonts — a painted bar + triangle is
    font-independent. Keeps objectName "playback_control" so the QSS
    hover/pressed treatment still applies to the button chrome.
    """

    def __init__(self, kind: str, parent=None):
        super().__init__("", parent)
        self._kind = kind  # "prev" | "next"

    def paintEvent(self, event):
        super().paintEvent(event)
        tokens = get_tokens()
        color = QColor(tokens.text_primary if self.isEnabled() else tokens.text_disabled)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        cx, cy = self.width() / 2, self.height() / 2
        half_h = 6.0
        if self._kind == "prev":
            p.drawRect(int(cx - 6), int(cy - half_h), 2, int(half_h * 2))
            triangle = [
                QPointF(cx + 6, cy - half_h),
                QPointF(cx + 6, cy + half_h),
                QPointF(cx - 2, cy),
            ]
        else:
            p.drawRect(int(cx + 4), int(cy - half_h), 2, int(half_h * 2))
            triangle = [
                QPointF(cx - 6, cy - half_h),
                QPointF(cx - 6, cy + half_h),
                QPointF(cx + 2, cy),
            ]
        p.drawPolygon(QPolygonF(triangle))
        p.end()


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

        # Chronovisor callbacks (through _on_seek so trails reset on jumps)
        self._chronovisor_vm.navigate_to.connect(lambda tick, desc: self._on_seek(tick))
        # R4 MED: enable the CM transport only when a scan found moments.
        self._chronovisor_vm.scan_complete.connect(self._on_cm_scan_complete)

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

        # Ghost Mode (frame 14) — active only when the toggle is on AND a
        # ghost payload is present (Locked Decision 8: defensive rendering).
        self._ghost_payload: dict | None = None
        self._ghost_mode_on = False
        self._demo_tick_rate = DEFAULT_TICK_RATE

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
        # Recompose the tick counter in the new language (the 100ms timer
        # only rewrites it while the screen is active).
        self._tick_label.setText(
            f"{i18n.get_text('tactical.tick', 'Tick')}: "
            f"{self._playback_vm.get_current_tick():,}"
        )
        self._ghost_check.setText(i18n.get_text("tactical.ghost_ai", "Ghost AI"))
        self._cm_marks_check.setText(i18n.get_text("tactical.cm_marks", "CM marks"))
        self._ghost_combo_label.setText(i18n.get_text("tactical.ghost_combo_label", "Ghost:"))
        self._align_label.setText(i18n.get_text("tactical.align_method", "Align method:"))
        self._refresh_glyph_legend()
        self._update_chronovisor_footer()
        self._update_header_meta()
        if self._ghost_mode_on:
            # Recompose every ghost-owned string in the active language.
            self._ghost_mode_on = False
            self._update_ghost_mode()

    def _refresh_glyph_legend(self) -> None:
        """Compose the `★ critical · ◆ clutch · ● play` caption from the
        timeline's kind mapping, each glyph tinted to its paint color."""
        t = get_tokens()
        color_by_kind = {"star": t.warning, "diamond": t.info, "circle": t.success}
        parts = [
            f'<span style="color: {color_by_kind[kind]};">{glyph}</span> '
            f"{i18n.get_text(f'tactical.glyph_{label}', label)}"
            for kind, glyph, label in GLYPH_LEGEND
        ]
        self._glyph_legend.setText(
            f'<span style="color: {t.text_secondary};">{" &nbsp;·&nbsp; ".join(parts)}</span>'
        )

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
        tokens = get_tokens()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(
            tokens.spacing_md, tokens.spacing_sm, tokens.spacing_md, tokens.spacing_sm
        )
        header.setSpacing(tokens.spacing_md)
        self._title_label = QLabel(i18n.get_text("tactical_analyzer"))
        Typography.apply(self._title_label, "h1")
        header.addWidget(self._title_label)

        # Mono meta line: `{demo} · round {n} · tick {t}` (frame 13)
        self._header_meta = QLabel("—")
        Typography.apply(self._header_meta, "mono")
        header.addWidget(self._header_meta)
        header.addStretch()

        self._error_label = QLabel()
        self._error_label.setFont(Typography.font("body"))
        self._error_label.setStyleSheet(f"color: {tokens.error}; background: transparent;")
        self._error_label.setWordWrap(True)
        self._error_label.setVisible(False)
        header.addWidget(self._error_label)

        self._open_btn = make_button(i18n.get_text("open_demo"), variant="primary", fixed_width=140)
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

        # Side semantics per the design constraints: CT = chart_line_primary
        # (cyan), T = chart_line_secondary (orange) — same hues the map dots use.
        self._ct_sidebar = PlayerSidebar("CT", tokens.chart_line_primary)
        self._ct_sidebar.setFixedWidth(200)
        self._ct_sidebar.player_clicked.connect(self._on_player_select)
        main_area.addWidget(self._ct_sidebar)

        # Ghost Mode swaps the left roster for the YOU/GHOST/divergence panel.
        self._ghost_panel = _GhostPanel()
        self._ghost_panel.setVisible(False)
        main_area.addWidget(self._ghost_panel)

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
            self._empty_overlay.setFont(Typography.font("title"))
            self._empty_overlay.setStyleSheet(
                f"color: {tokens.text_secondary}; "
                f"background: {tokens.surface_raised_rgba}; "
                f"border-radius: {tokens.radius_lg}px; "
                f"padding: {tokens.spacing_xxl}px;"
            )
            self._empty_overlay.setParent(map_container)
            self._empty_overlay.setGeometry(0, 0, 0, 0)  # sized in resizeEvent

            # Loading overlay (UX-2: map switch indicator)
            self._loading_overlay = QLabel("Loading map...")
            self._loading_overlay.setAlignment(Qt.AlignCenter)
            self._loading_overlay.setFont(Typography.font("subtitle"))
            self._loading_overlay.setStyleSheet(
                f"color: {tokens.text_primary}; "
                f"background: {tokens.surface_raised_rgba}; "
                f"border-radius: {tokens.radius_lg}px; "
                f"padding: {tokens.spacing_xl}px;"
            )
            self._loading_overlay.setParent(map_container)
            self._loading_overlay.hide()

        main_area.addWidget(map_container, 1)

        self._t_sidebar = PlayerSidebar("T", tokens.chart_line_secondary)
        self._t_sidebar.setFixedWidth(200)
        self._t_sidebar.player_clicked.connect(self._on_player_select)
        main_area.addWidget(self._t_sidebar)

        root.addLayout(main_area, 1)

        # Control panel
        control_panel = self._build_controls()
        root.addWidget(control_panel)

    def _build_controls(self) -> QFrame:
        tokens = get_tokens()
        panel = QFrame()
        panel.setObjectName("tactical_controls")
        panel.setStyleSheet(
            f"QFrame#tactical_controls {{ "
            f"background-color: {tokens.surface_sidebar}; "
            f"border-top: 1px solid {tokens.border_subtle}; "
            f"}}"
        )
        panel.setFixedHeight(164)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(
            tokens.spacing_md, tokens.spacing_xs, tokens.spacing_md, tokens.spacing_xs
        )
        layout.setSpacing(tokens.spacing_xs)

        # Row 1: selectors
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        # Standard selectors live in their own container so Ghost Mode can
        # swap the row for its ghost/align selectors without relayout churn.
        self._std_selector_row = QWidget()
        std_row = QHBoxLayout(self._std_selector_row)
        std_row.setContentsMargins(0, 0, 0, 0)
        std_row.setSpacing(12)

        self._map_combo = QComboBox()
        self._map_combo.setFixedWidth(140)
        self._map_combo.currentTextChanged.connect(self._on_map_changed)
        self._map_label = QLabel(i18n.get_text("select_map") + ":")
        std_row.addWidget(self._map_label)
        std_row.addWidget(self._map_combo)

        self._round_combo = QComboBox()
        self._round_combo.setFixedWidth(120)
        self._round_combo.currentTextChanged.connect(self._on_round_changed)
        self._round_label = QLabel(i18n.get_text("select_round") + ":")
        std_row.addWidget(self._round_label)
        std_row.addWidget(self._round_combo)

        self._tick_label = QLabel(f"{i18n.get_text('tactical.tick', 'Tick')}: 0")
        self._tick_label.setObjectName("tick_counter")
        self._tick_label.setMinimumWidth(120)
        std_row.addWidget(self._tick_label)
        row1.addWidget(self._std_selector_row)

        # Ghost Mode selector row (frame 14) — swapped in for the standard
        # selectors while the mode is active.
        self._ghost_selector_row = QWidget()
        ghost_row = QHBoxLayout(self._ghost_selector_row)
        ghost_row.setContentsMargins(0, 0, 0, 0)
        ghost_row.setSpacing(12)
        self._ghost_combo_label = QLabel(i18n.get_text("tactical.ghost_combo_label", "Ghost:"))
        ghost_row.addWidget(self._ghost_combo_label)
        self._ghost_combo = QComboBox()
        self._ghost_combo.setFixedWidth(200)
        # FIELD-GAP: no ghost-library source exists yet — the selector shows
        # the active overlay's identity and stays disabled.
        self._ghost_combo.setEnabled(False)
        self._ghost_combo.setToolTip(
            i18n.get_text("tactical.ghost_source_gap", "Ghost library source not connected yet")
        )
        ghost_row.addWidget(self._ghost_combo)
        self._align_label = QLabel(i18n.get_text("tactical.align_method", "Align method:"))
        ghost_row.addWidget(self._align_label)
        self._align_combo = QComboBox()
        self._align_combo.setFixedWidth(140)
        self._align_combo.addItem(i18n.get_text("tactical.align_round_time", "round time"))
        ghost_row.addWidget(self._align_combo)
        self._ghost_selector_row.setVisible(False)
        row1.addWidget(self._ghost_selector_row)

        row1.addStretch()

        self._ghost_check = QCheckBox(i18n.get_text("tactical.ghost_ai", "Ghost AI"))
        self._ghost_check.setObjectName("ghost_toggle")
        self._ghost_check.toggled.connect(self._ghost_vm.set_active)
        self._ghost_check.toggled.connect(self._update_ghost_mode)
        row1.addWidget(self._ghost_check)

        # CM marks — toggles the map movement trails (frame 13).
        self._cm_marks_check = QCheckBox(i18n.get_text("tactical.cm_marks", "CM marks"))
        self._cm_marks_check.setObjectName("ghost_toggle")
        self._cm_marks_check.setChecked(True)
        self._cm_marks_check.toggled.connect(self._map_widget.set_trails_enabled)
        row1.addWidget(self._cm_marks_check)

        layout.addLayout(row1)

        # Row 2: playback controls.
        # setObjectName("playback_control") keeps the tight-padding QSS rule
        # that overrides the global QPushButton padding (otherwise 8px 20px
        # on a fixed-size button clips the content — the "blank buttons"
        # bug reported post-P1).
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        # R4 MED: CM transport starts DISABLED — the old buttons took
        # clicks and did nothing while _critical_moments was empty (nothing
        # ever called scan_match). They enable when a scan finds moments.
        prev_cm_btn = _TransportIconButton("prev")
        prev_cm_btn.setObjectName("playback_control")
        prev_cm_btn.setFixedSize(40, 40)
        prev_cm_btn.setCursor(Qt.PointingHandCursor)
        prev_cm_btn.setToolTip("Previous critical moment (no scan yet)")
        prev_cm_btn.setEnabled(False)
        prev_cm_btn.clicked.connect(self._jump_prev_cm)
        row2.addWidget(prev_cm_btn)
        self._prev_cm_btn = prev_cm_btn

        # Frame 13 labels the play control with text, not a glyph — and the
        # old ▶/⏸ pair was half-tofu offscreen (U+23F8 has no fallback).
        self._play_btn = QPushButton(i18n.get_text("tactical.play", "Play"))
        self._play_btn.setObjectName("playback_control")
        self._play_btn.setFixedSize(72, 40)
        self._play_btn.setCursor(Qt.PointingHandCursor)
        self._play_btn.setToolTip("Play / Pause")
        self._play_btn.clicked.connect(self._toggle_playback)
        row2.addWidget(self._play_btn)

        next_cm_btn = _TransportIconButton("next")
        next_cm_btn.setObjectName("playback_control")
        next_cm_btn.setFixedSize(40, 40)
        next_cm_btn.setCursor(Qt.PointingHandCursor)
        next_cm_btn.setToolTip("Next critical moment (no scan yet)")
        next_cm_btn.setEnabled(False)
        next_cm_btn.clicked.connect(self._jump_next_cm)
        row2.addWidget(next_cm_btn)
        self._next_cm_btn = next_cm_btn

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

        row2.addSpacing(16)
        # Ghost sync offset (frame 14) — mono, info-colored, shown only when
        # the ghost payload carries a known offset.
        self._sync_offset_label = QLabel()
        Typography.apply(self._sync_offset_label, "mono")
        self._sync_offset_label.setStyleSheet(f"color: {tokens.info};")
        self._sync_offset_label.setVisible(False)
        row2.addWidget(self._sync_offset_label)

        row2.addStretch()
        layout.addLayout(row2)

        # Glyph legend (29.5) — caption row under the transport bar naming
        # the timeline's kind-differentiated moment glyphs (★/◆/●).
        self._glyph_legend = QLabel()
        self._glyph_legend.setTextFormat(Qt.RichText)
        self._glyph_legend.setFont(_caption_font())
        self._glyph_legend.setStyleSheet("background: transparent;")
        self._refresh_glyph_legend()
        layout.addWidget(self._glyph_legend)

        # Timeline
        self._timeline = TimelineWidget()
        layout.addWidget(self._timeline)

        # Ghost Mode dual progress (frame 14): YOU (accent) / GHOST (info)
        # thin bars synced to playback, swapped in for the timeline.
        self._dual_progress = QWidget()
        dual_box = QVBoxLayout(self._dual_progress)
        dual_box.setContentsMargins(0, tokens.spacing_xs, 0, tokens.spacing_xs)
        dual_box.setSpacing(tokens.spacing_xs + 2)

        def dual_row(caption_key: str, fallback: str, color: str) -> QProgressBar:
            row = QHBoxLayout()
            row.setSpacing(tokens.spacing_sm)
            label = QLabel(i18n.get_text(caption_key, fallback))
            label.setFont(_caption_font(bold=True))
            label.setStyleSheet(f"color: {color}; background: transparent;")
            label.setFixedWidth(52)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(label)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setFixedHeight(10)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar {{ background-color: {tokens.surface_sunken}; border: none; "
                f"border-radius: {tokens.radius_sm}px; }}"
                f"QProgressBar::chunk {{ background-color: {color}; "
                f"border-radius: {tokens.radius_sm}px; }}"
            )
            row.addWidget(bar, 1)
            dual_box.addLayout(row)
            return bar

        self._you_progress = dual_row("tactical.you", "YOU", tokens.accent_primary)
        self._ghost_progress = dual_row("tactical.ghost", "GHOST", tokens.info)
        self._dual_progress.setVisible(False)
        layout.addWidget(self._dual_progress)

        # Footer strip: chronovisor summary left, demo meta right (frame 13).
        footer_row = QHBoxLayout()
        footer_row.setSpacing(tokens.spacing_md)
        self._footer_left = MonoFooter()
        self._footer_left.setWordWrap(False)
        footer_row.addWidget(self._footer_left)
        footer_row.addStretch()
        self._footer_right = MonoFooter()
        self._footer_right.setWordWrap(False)
        self._footer_right.setVisible(False)
        footer_row.addWidget(self._footer_right)
        layout.addLayout(footer_row)
        self._cm_count = 0
        self._demo_meta: dict | None = None
        self._update_chronovisor_footer()

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
        # Chronovisor scan resolves the DB match_id from this stem after load;
        # playback resolves the real tick rate from the full path's header.
        self._loaded_demo_stem = os.path.splitext(demo_basename)[0]
        self._loaded_demo_path = path
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
        # R4 MED: detach any bridge left over from a cancelled load first —
        # the old code overwrote self._log_bridge, so the first parse's
        # completion detached the NEW bridge (killing the second load's
        # progress text) while the first handler stayed attached to the
        # demo_loader logger forever, feeding a dead QProgressDialog.
        if self._log_bridge is not None:
            self._log_bridge.detach()
            self._log_bridge = None
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

        # R4 MED: kick off the critical-moment scan for the loaded demo —
        # nothing ever called scan_match before, so the CM transport was a
        # permanent no-op. Best-effort: stays disabled if unresolvable.
        self._start_chronovisor_scan()

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

        # Update map (also reloads its zone layer and drops trail history)
        self._map_widget.set_map(map_name)
        self._map_widget.set_score_info(None)
        self._map_widget.set_bomb(None)

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

        # Load frames with the demo's REAL tick rate (26-TICK: the old
        # default-64 path made 128-tick demos play at half speed).
        self._demo_tick_rate = self._resolve_demo_tick_rate()
        self._playback_vm.load_frames(frames, tick_rate=self._demo_tick_rate)

        # Update timeline (round-boundary dividers from the segment map)
        self._timeline.max_tick = self._playback_vm.total_ticks
        self._timeline.set_events(events)
        self._timeline.set_round_marks(list((segments or {}).values()))
        self._timeline.set_critical_moments([])
        self._update_header_meta()

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

        # FIELD-GAP: InterpolatedFrame carries no scoreboard/bomb fields
        # today — the score strip and C4 marker render only when a payload
        # superset provides them (em-dash / hidden otherwise).
        self._map_widget.set_score_info(self._compose_score(getattr(frame, "score", None)))
        bomb = getattr(frame, "bomb", None)
        self._map_widget.set_bomb(bomb if isinstance(bomb, dict) else None)

        ct_players = [p for p in frame.players if p.team == Team.CT]
        t_players = [p for p in frame.players if p.team == Team.T]
        selected = self._map_widget.selected_player_id
        self._ct_sidebar.update_players(ct_players, selected)
        self._t_sidebar.update_players(t_players, selected)

    def _compose_score(self, score) -> "dict | None":
        """Frame payload score fields → score-box display dict ("—" absent)."""
        if not isinstance(score, dict):
            return None

        def fmt(value):
            return "—" if value in (None, "") else str(value)

        t_name = str(score.get("t_name") or "").upper()
        caption_parts = []
        if score.get("round_no") is not None:
            caption_parts.append(
                f"{i18n.get_text('tactical.meta_round', 'round')} {score['round_no']}"
            )
        if score.get("time_remaining"):
            remaining = i18n.get_text("tactical.remaining", "remaining")
            caption_parts.append(f"{score['time_remaining']} {remaining}")
        if score.get("bomb_planted"):
            caption_parts.append(i18n.get_text("tactical.bomb_planted", "bomb planted"))
        if score.get("ghost_note"):
            caption_parts.append(str(score["ghost_note"]))
        return {
            "t_label": f"T · {t_name}" if t_name else "T",
            "t_score": fmt(score.get("t_score")),
            "ct_score": fmt(score.get("ct_score")),
            "ct_label": "CT",
            "caption": " · ".join(caption_parts),
        }

    def _update_header_meta(self):
        """Compose `{demo} · round {n} · tick {t}` (frame 13)."""
        if self._ghost_mode_on:
            return  # Ghost Mode owns the meta line (`ghost overlay: …`)
        parts = [getattr(self, "_loaded_demo_stem", None) or "—"]
        digits = "".join(ch for ch in self._round_combo.currentText() if ch.isdigit())
        if digits:
            parts.append(f"{i18n.get_text('tactical.meta_round', 'round')} {int(digits)}")
        tick = self._playback_vm.get_current_tick()
        parts.append(f"{i18n.get_text('tactical.meta_tick', 'tick')} {tick:,}")
        text = " · ".join(parts)
        if text != self._header_meta.text():
            self._header_meta.setText(text)

    def _update_chronovisor_footer(self):
        template = i18n.get_text(
            "tactical.footer_chronovisor",
            "ChronovisorScanner · 3 scales (micro/standard/macro) · "
            "{n} critical moments detected this round",
        )
        self._footer_left.setText(template.replace("{n}", str(self._cm_count)))

    def set_demo_meta(self, meta: "dict | None") -> None:
        """Right footer: `{source} · {size} MB · {parser}` from whatever the
        loader can provide. FIELD-GAP: DemoLoader returns no such metadata
        today — the footer stays hidden until a payload supplies it."""
        self._demo_meta = meta if isinstance(meta, dict) else None
        parts = []
        if self._demo_meta:
            if self._demo_meta.get("source"):
                parts.append(str(self._demo_meta["source"]))
            if self._demo_meta.get("size_mb") is not None:
                parts.append(f"{self._demo_meta['size_mb']} MB")
            if self._demo_meta.get("parser"):
                parts.append(str(self._demo_meta["parser"]))
        self._footer_right.setText(" · ".join(parts))
        self._footer_right.setVisible(bool(parts))

    # ── Ghost Mode (frame 14) ──

    def set_ghost_payload(self, payload: "dict | None") -> None:
        """Attach (or clear) the ghost-overlay payload.

        FIELD-GAP: TacticalGhostVM only predicts per-tick positions today —
        it has no signal carrying paths/divergence/causal data. This public
        slot is the seam a divergence-capable VM (or the fixture) feeds;
        every field is optional and renders defensively (Locked Decision 8).
        """
        self._ghost_payload = payload if isinstance(payload, dict) else None
        self._update_ghost_mode()

    def _update_ghost_mode(self, _checked: bool = False) -> None:
        active = self._ghost_check.isChecked() and bool(self._ghost_payload)
        if active == self._ghost_mode_on:
            if active:  # payload may have changed while active
                self._ghost_panel.set_payload(self._ghost_payload)
                self._map_widget.set_ghost_overlay(self._compose_ghost_overlay())
            return
        self._ghost_mode_on = active
        payload = self._ghost_payload or {}
        tokens = get_tokens()

        if active:
            suffix = i18n.get_text("tactical.ghost_mode_suffix", " — Ghost Mode")
            self._title_label.setText(i18n.get_text("tactical_analyzer") + suffix)
            overlay_tpl = i18n.get_text(
                "tactical.ghost_overlay", "ghost overlay: {pro} · same round on {map}"
            )
            self._header_meta.setText(
                overlay_tpl.replace("{pro}", str(payload.get("pro") or "—")).replace(
                    "{map}", str(payload.get("map") or "—")
                )
            )
            self._header_meta.setStyleSheet(f"color: {tokens.info};")
            self._ghost_panel.set_payload(payload)
            # Stale trail history has no meaning under the overlay comparison.
            self._map_widget.clear_trails()
            self._map_widget.set_ghost_overlay(self._compose_ghost_overlay())
            ghost_id = " · ".join(
                str(part)
                for part in (payload.get("pro"), payload.get("team"), payload.get("map"))
                if part
            )
            self._ghost_combo.clear()
            if ghost_id:
                self._ghost_combo.addItem(ghost_id)
            offset = payload.get("sync_offset_s")
            if isinstance(offset, (int, float)):
                offset_tpl = i18n.get_text("tactical.sync_offset", "ghost sync offset: {offset}")
                self._sync_offset_label.setText(offset_tpl.replace("{offset}", f"{offset:+.1f}s"))
                self._sync_offset_label.setVisible(True)
            else:
                self._sync_offset_label.setVisible(False)  # FIELD-GAP: offset unknown
            self._footer_left.setText(self._causal_footer_text(payload))
        else:
            self._title_label.setText(i18n.get_text("tactical_analyzer"))
            self._header_meta.setStyleSheet("")
            self._update_header_meta()
            self._map_widget.set_ghost_overlay(None)
            self._sync_offset_label.setVisible(False)
            self._update_chronovisor_footer()

        self._ct_sidebar.setVisible(not active)
        self._t_sidebar.setVisible(not active)
        self._ghost_panel.setVisible(active)
        self._std_selector_row.setVisible(not active)
        self._ghost_selector_row.setVisible(active)
        self._timeline.setVisible(not active)
        self._glyph_legend.setVisible(not active)
        self._dual_progress.setVisible(active)
        if active:
            self._update_dual_progress()

    def _compose_ghost_overlay(self) -> "dict | None":
        payload = self._ghost_payload or {}
        if not payload:
            return None
        you = payload.get("you") if isinstance(payload.get("you"), dict) else {}
        return {
            "you_path": payload.get("you_path") or [],
            "ghost_path": payload.get("ghost_path") or [],
            "you_label": payload.get("you_label") or i18n.get_text("tactical.map_you", "you"),
            "ghost_label": payload.get("ghost_label")
            or i18n.get_text("tactical.map_ghost", "ghost"),
            "you_died": bool(you.get("died")),
            "divergence_points": payload.get("divergence_points") or [],
            "smokes": payload.get("smokes") or [],
            "legend": {
                "title": i18n.get_text("tactical.legend_title", "Ghost Mode Legend"),
                "you": i18n.get_text("tactical.legend_you", "your path"),
                "ghost": i18n.get_text("tactical.legend_ghost", "ghost (pro) path"),
                "divergence": i18n.get_text("tactical.legend_divergence", "divergence point"),
            },
        }

    @staticmethod
    def _causal_footer_text(payload: dict) -> str:
        """Frame-14 footer from whatever causal components exist — absent
        components are dropped, not dashed (mono debug line)."""
        causal = payload.get("causal") if isinstance(payload.get("causal"), dict) else {}
        parts = ["RAPPedagogy.CausalAttributor"]
        for key in ("positioning", "utility", "aim", "aggression", "rotation"):
            value = causal.get(key)
            if isinstance(value, (int, float)):
                parts.append(f"{key} {value:.2f}")
        return " · ".join(parts)

    def _update_dual_progress(self) -> None:
        total = max(1, self._playback_vm.total_ticks)
        tick = self._playback_vm.get_current_tick()
        you = max(0.0, min(1.0, tick / total))
        offset = (self._ghost_payload or {}).get("sync_offset_s")
        offset_ticks = (
            float(offset) * self._demo_tick_rate if isinstance(offset, (int, float)) else 0.0
        )
        ghost = max(0.0, min(1.0, (tick + offset_ticks) / total))
        self._you_progress.setValue(int(you * 1000))
        self._ghost_progress.setValue(int(ghost * 1000))

    def _update_tick_ui(self):
        tick = self._playback_vm.get_current_tick()
        self._tick_label.setText(f"{i18n.get_text('tactical.tick', 'Tick')}: {tick:,}")
        self._timeline.current_tick = tick
        self._update_header_meta()
        if self._ghost_mode_on:
            self._update_dual_progress()
        playing = self._playback_vm.is_playing
        # The "state" property drives the QSS accent-fill rule
        # (#playback_control[state="playing"]) so the button reflects the mode.
        label = (
            i18n.get_text("tactical.pause", "Pause")
            if playing
            else i18n.get_text("tactical.play", "Play")
        )
        if self._play_btn.text() != label:
            self._play_btn.setText(label)
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
        # A jump invalidates continuous movement history (frame-13 trails).
        self._map_widget.clear_trails()

    def open_moment(self, demo_name: str, tick: int) -> None:
        """Deep-link entry: seek to ``tick`` when ``demo_name`` is the demo
        already loaded in this viewer.

        Wired by the app orchestrator to ``MatchDetailScreen.moment_selected``
        ("Open in Tactical Viewer" on Highlights moment cards); the wirer
        switches to this screen afterwards either way. Names are compared by
        stem so ``foo.dem`` and ``foo`` match the stored ``_loaded_demo_stem``.
        """
        wanted = os.path.splitext(os.path.basename(str(demo_name or "")))[0]
        loaded = getattr(self, "_loaded_demo_stem", None)
        if self._full_demo_data and wanted and loaded == wanted:
            self._on_seek(int(tick))
            return
        # FIELD-GAP: cross-demo auto-load — the viewer's only load path is
        # the modal file-picker flow (_open_demo); resolving a demo_name back
        # to a .dem path and loading it headlessly isn't wired yet.
        logger.info(
            "open_moment: demo %r not loaded (loaded=%r) — seek to tick %s skipped",
            demo_name,
            loaded,
            tick,
        )
        win = self.window()
        if win is not None and hasattr(win, "_show_toast"):
            win._show_toast(
                "INFO",
                i18n.get_text(
                    "tactical.open_moment_missing",
                    "Open demo {demo} here first to jump to this moment",
                ).replace("{demo}", str(demo_name)),
            )

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

    def _resolve_demo_tick_rate(self) -> int:
        """Per-demo tick rate from the loaded demo's header (fallback 64, loud)."""
        path = getattr(self, "_loaded_demo_path", None)
        if path:
            try:
                from Programma_CS2_RENAN.run_ingestion import _parse_demo_header_meta

                _map, rate = _parse_demo_header_meta(str(path))
                if 32 <= int(rate) <= 256:
                    return int(rate)
            except Exception as exc:  # noqa: BLE001 — playback must not die on header quirks
                logger.warning("Header tick-rate resolution failed for %r: %s", path, exc)
        logger.warning(
            "Falling back to %s tick/s for playback (no resolvable header)", DEFAULT_TICK_RATE
        )
        return DEFAULT_TICK_RATE

    def _on_cm_scan_complete(self, cms, count: int) -> None:
        """Enable/disable the CM transport based on real scan results."""
        has_moments = bool(count)
        for btn, label in (
            (getattr(self, "_prev_cm_btn", None), "Previous critical moment"),
            (getattr(self, "_next_cm_btn", None), "Next critical moment"),
        ):
            if btn is None:
                continue
            btn.setEnabled(has_moments)
            btn.setToolTip(f"{label} ({count} found)" if has_moments else f"{label} (none found)")
        # Frame 13: star markers on the timeline + chronovisor footer count.
        self._timeline.set_critical_moments(cms or [])
        self._cm_count = int(count or 0)
        self._update_chronovisor_footer()

    def _start_chronovisor_scan(self) -> None:
        """Best-effort CM scan for the demo just loaded (R4 MED wiring).

        scan_match needs the DB match_id; a demo opened from an arbitrary
        file may not be ingested, in which case the transport simply stays
        disabled. Resolution failures must never break the viewer.
        """
        stem = getattr(self, "_loaded_demo_stem", None)
        if not stem:
            return
        try:
            from sqlmodel import select

            from Programma_CS2_RENAN.backend.storage.database import get_db_manager
            from Programma_CS2_RENAN.backend.storage.db_models import PlayerTickState

            with get_db_manager().get_session() as session:
                match_id = session.exec(
                    select(PlayerTickState.match_id)
                    .where(PlayerTickState.demo_name == stem)
                    .limit(1)
                ).first()
            if match_id is None:
                logger.info(
                    "Chronovisor: demo %r not found in DB — CM scan skipped "
                    "(transport stays disabled)",
                    stem,
                )
                return
            self._chronovisor_vm.scan_match(int(match_id))
        except Exception as exc:
            logger.warning("Chronovisor scan wiring failed for %r: %s", stem, exc)

    def _jump_next_cm(self):
        tick = self._playback_vm.get_current_tick()
        self._chronovisor_vm.jump_to_next(tick)

    def _jump_prev_cm(self):
        tick = self._playback_vm.get_current_tick()
        self._chronovisor_vm.jump_to_prev(tick)
