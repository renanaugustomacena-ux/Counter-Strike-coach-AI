"""QPainter-based 2D tactical map — renders players, grenades, and ghosts."""

import json
import math
import os
from collections import deque
from typing import List, Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QWidget

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.apps.qt_app.widgets.tactical._paint_utils import with_alpha
from Programma_CS2_RENAN.core.config import get_resource_path
from Programma_CS2_RENAN.core.demo_frame import NadeType, Team
from Programma_CS2_RENAN.core.playback_engine import InterpolatedPlayerState
from Programma_CS2_RENAN.core.spatial_engine import SpatialEngine
from Programma_CS2_RENAN.core.tick_rate import DEFAULT_TICK_RATE
from Programma_CS2_RENAN.observability.logger_setup import get_logger

_logger = get_logger("cs2analyzer.qt_tactical_map")

TICK_RATE = DEFAULT_TICK_RATE
PLAYER_RADIUS = 8
HITBOX_MULTIPLIER = 2.5

GRENADE_RADII = {
    NadeType.HE: 350,
    NadeType.MOLOTOV: 180,
    NadeType.SMOKE: 144,
    NadeType.FLASH: 1000,
}

# Grenade type → semantic palette key (resolved in _palette per paint).
_NADE_PALETTE_KEYS = {
    NadeType.HE: "he",
    NadeType.MOLOTOV: "molotov",
    NadeType.SMOKE: "smoke",
    NadeType.FLASH: "flash",
}


# Trails keep the last N interpolated positions per player (frame 13 spec).
TRAIL_MAX_POINTS = 40
# 35% alpha for trail polylines (frame-13 movement-history treatment).
_TRAIL_ALPHA = 89


def _caption_font(*, bold: bool = False) -> QFont:
    """Caption-sized BODY font for painted annotations — size read from
    tokens. Mono captions come from ``Typography.mono_caption``."""
    f = Typography.font("body", QFont.Bold if bold else None)
    f.setPointSize(get_tokens().font_size_caption)
    return f


def load_map_zones(map_name: str) -> list[dict]:
    """Load named-zone rects for ``map_name`` from ``assets/map_zones/``.

    Schema: ``{"map": ..., "zones": [{"name", "x", "y", "w", "h", "label",
    "major"?}]}`` with coordinates normalized 0-1 in radar space. Returns
    a validated list; unknown maps / missing files / malformed entries
    degrade to ``[]`` so the viewer never breaks on a map without zones.

    Pure function (no Qt) so tests can exercise normalization directly.
    """
    clean = (map_name or "").lower().strip()
    clean = clean.replace(".dem", "").replace(".vpk", "").replace("maps/", "")
    if not clean:
        return []
    candidates = [clean] if clean.startswith("de_") else [clean, f"de_{clean}"]
    for candidate in candidates:
        path = get_resource_path(os.path.join("assets", "map_zones", f"{candidate}.json"))
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            _logger.warning("Map zones unreadable for %r (%s): %s", map_name, path, exc)
            return []
        zones: list[dict] = []
        for raw in data.get("zones", []) if isinstance(data, dict) else []:
            try:
                x, y = float(raw["x"]), float(raw["y"])
                w, h = float(raw["w"]), float(raw["h"])
            except (KeyError, TypeError, ValueError):
                continue
            if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                continue
            zones.append(
                {
                    "x": x,
                    "y": y,
                    "w": min(w, 1.0 - x),
                    "h": min(h, 1.0 - y),
                    "label": str(raw.get("label", raw.get("name", ""))),
                    "major": bool(raw.get("major", False)),
                }
            )
        return zones
    return []


class TacticalMapWidget(QWidget):
    """2D tactical map with player/grenade rendering via QPainter."""

    selected_player_changed = Signal(object)  # int or None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._map_name = "de_dust2"
        self._map_pixmap: Optional[QPixmap] = None
        self._scaled_pixmap: Optional[QPixmap] = None
        self._cached_map_size: int = 0
        self._players: List[InterpolatedPlayerState] = []
        self._ghosts: List[InterpolatedPlayerState] = []
        self._nades: List = []
        self._current_tick = 0
        self._selected_player_id: Optional[int] = None
        # Frame-13 layers: named zones (from assets/map_zones), score box,
        # C4 marker, and per-player movement trails.
        self._zones: list[dict] = load_map_zones(self._map_name)
        self._score_info: Optional[dict] = None
        self._score_layout: Optional[dict] = None
        self._bomb: Optional[dict] = None
        self._trails: dict[int, tuple[bool, deque]] = {}
        self._trails_enabled = True
        # Frame-14 Ghost Mode overlay (paths/divergences/legend), or None.
        self._ghost_overlay: Optional[dict] = None

        self._name_font = _caption_font(bold=True)  # lowercase, frame-13 style
        self._name_fm = QFontMetrics(self._name_font)
        self._pal = self._palette()

        self.setMinimumSize(200, 200)
        self.setMouseTracking(False)

    def _palette(self) -> dict[str, QColor]:
        """Token-derived paint palette, refreshed each paintEvent.

        Reading get_tokens() per paint keeps the map theme-tracking
        (CS2 / CSGO / CS1.6). Baked alphas mirror the retired module
        constants (dead 128, selected 204).
        """
        t = get_tokens()
        return {
            "ct": QColor(t.chart_line_primary),
            "t": QColor(t.chart_line_secondary),
            "dead": with_alpha(QColor(t.text_disabled), 128),
            "selected": with_alpha(QColor(t.accent_primary), 204),
            "he": QColor(t.warning),
            "molotov": QColor(t.error),
            "smoke": QColor(t.text_secondary),
            "flash": QColor(t.info),
            "text": QColor(t.text_primary),
            "muted": QColor(t.text_secondary),
            "well": QColor(t.surface_sunken),
            "hp_high": QColor(t.success),
            "hp_low": QColor(t.error),
            "zone": with_alpha(QColor(t.chart_axis), 170),
            "zone_label": with_alpha(QColor(t.text_tertiary), 200),
            "bomb": QColor(t.warning),
            "bomb_text": QColor(t.text_inverse),
            "accent": QColor(t.accent_primary),
            "overlay_bg": with_alpha(QColor(t.surface_base), 178),
        }

    # ── Public API ──

    def set_map(self, map_name: str):
        self._map_name = map_name
        self._zones = load_map_zones(map_name)
        self._trails.clear()
        self._load_map_image()
        self.update()

    def set_score_info(self, info: Optional[dict]):
        """Score-box overlay data (frame 13): ``{"t_label", "t_score",
        "ct_score", "ct_label", "caption"}`` — absent values pre-composed
        by the screen as em-dashes. ``None`` hides the box."""
        if self._score_info != info:
            self._score_info = info or None
            # Segment layout (strings/fonts/offsets) is recomputed HERE, on
            # score change only — not per paintEvent, where the old code
            # built ~15 QFontMetrics at 60fps while playing.
            self._score_layout = self._compose_score_layout(self._score_info)
            self.update()

    @staticmethod
    def _compose_score_layout(info: "Optional[dict]") -> "Optional[dict]":
        """Precomputed score-box layout: per-segment (text, palette key,
        font, x offset) plus box metrics. Colors stay palette KEYS so
        paintEvent keeps theme-tracking through ``self._pal``."""
        if not info:
            return None
        t = get_tokens()
        bold_body = Typography.font("body", QFont.Bold)
        score_font = Typography.font("subtitle")
        cap_font = _caption_font()
        bold_fm = QFontMetrics(bold_body)
        score_fm = QFontMetrics(score_font)
        cap_fm = QFontMetrics(cap_font)

        segments = [
            (str(info.get("t_label", "")), "t", bold_body),
            (f'  {info.get("t_score", "—")}', "text", score_font),
            (" — ", "muted", bold_body),
            (f'{info.get("ct_score", "—")}  ', "text", score_font),
            (str(info.get("ct_label", "")), "ct", bold_body),
        ]
        placed: list[tuple[str, str, QFont, float]] = []
        dx = 0.0
        for text, key, font in segments:
            placed.append((text, key, font, dx))
            dx += (score_fm if font is score_font else bold_fm).horizontalAdvance(text)
        caption = str(info.get("caption", ""))
        cap_h = cap_fm.height() if caption else 0
        pad = t.spacing_md
        line1_h = max(bold_fm.height(), score_fm.height())
        return {
            "segments": placed,
            "ascent": score_fm.ascent(),
            "caption": caption,
            "cap_font": cap_font,
            "cap_ascent": cap_fm.ascent(),
            "box_w": max(dx, cap_fm.horizontalAdvance(caption)) + 2 * pad,
            "box_h": pad + line1_h + (t.spacing_xs + cap_h if caption else 0) + pad,
            "pad": pad,
            "gap": t.spacing_xs,
        }

    def set_bomb(self, bomb: Optional[dict]):
        """C4 marker: ``{"x", "y"}`` world coords (``None`` hides it)."""
        if self._bomb != bomb:
            self._bomb = bomb or None
            self.update()

    def set_trails_enabled(self, enabled: bool):
        """Toggle movement-trail polylines (driven by the CM-marks toggle)."""
        if self._trails_enabled != bool(enabled):
            self._trails_enabled = bool(enabled)
            self.update()

    def clear_trails(self):
        """Drop trail history — called on seek / round or map change."""
        if self._trails:
            self._trails.clear()
            self.update()

    def set_ghost_overlay(self, payload: Optional[dict]):
        """Frame-14 Ghost Mode overlay. Keys (all optional, normalized 0-1
        radar coords): ``you_path``/``ghost_path`` point lists, ``you_label``
        / ``ghost_label``, ``you_died``, ``divergence_points`` ([{x, y,
        label}]), ``smokes`` ([{x, y, label}]), ``legend`` ({title, you,
        ghost, divergence}). ``None`` disables the overlay."""
        self._ghost_overlay = payload or None
        self.update()

    def update_map(
        self,
        players: List[InterpolatedPlayerState],
        nades: List = None,
        ghosts: List = None,
        tick: int = 0,
    ):
        self._players = players
        self._nades = nades or []
        self._ghosts = ghosts or []
        self._current_tick = tick
        for p in players or []:
            if not getattr(p, "is_alive", True):
                continue
            entry = self._trails.get(p.player_id)
            if entry is None:
                is_ct = (
                    p.team == Team.CT
                    if isinstance(p.team, Team)
                    else "CT" in str(p.team).upper()
                )
                entry = (is_ct, deque(maxlen=TRAIL_MAX_POINTS))
                self._trails[p.player_id] = entry
            points = entry[1]
            pos = (float(p.x), float(p.y))
            if not points or points[-1] != pos:
                points.append(pos)
        self.update()

    @property
    def selected_player_id(self) -> Optional[int]:
        return self._selected_player_id

    @selected_player_id.setter
    def selected_player_id(self, value):
        if self._selected_player_id != value:
            self._selected_player_id = value
            self.selected_player_changed.emit(value)
            self.update()

    # ── Map Loading ──

    def resizeEvent(self, event):
        self._scaled_pixmap = None  # Invalidate cache on resize
        super().resizeEvent(event)

    def _load_map_image(self):
        """Load map radar image as QPixmap — no Kivy dependency."""
        self._scaled_pixmap = None  # Invalidate cache on map change
        clean = self._map_name.lower().strip()
        clean = clean.replace(".dem", "").replace(".vpk", "").replace("maps/", "")

        maps_dir = get_resource_path(os.path.join("PHOTO_GUI", "maps"))

        # Try exact name, then with de_ prefix
        for candidate in [clean, f"de_{clean}"]:
            path = os.path.join(maps_dir, f"{candidate}.png")
            if os.path.exists(path):
                self._map_pixmap = QPixmap(path)
                return

        # Partial match
        if os.path.isdir(maps_dir):
            for fname in os.listdir(maps_dir):
                if clean in fname and fname.endswith(".png"):
                    self._map_pixmap = QPixmap(os.path.join(maps_dir, fname))
                    return

        # No radar found. paintEvent draws a dark fallback rect with the
        # map name — without this warning the failure was silent, which
        # produced the "blank viewer" symptom reported by the user.
        _logger.warning(
            "Map radar image not found for %r (searched %s); "
            "viewer will render fallback rect only",
            self._map_name,
            maps_dir,
        )
        self._map_pixmap = None

    # ── Coordinate Transform ──

    def _map_geometry(self):
        """Return (map_size, offset_x, offset_y) for centered square map."""
        ms = min(self.width(), self.height())
        ox = (self.width() - ms) / 2
        oy = (self.height() - ms) / 2
        return ms, ox, oy

    def _world_to_screen(self, x: float, y: float) -> tuple:
        nx, ny = SpatialEngine.world_to_normalized(x, y, self._map_name)
        ms, ox, oy = self._map_geometry()
        # Qt top-left origin matches radar image origin — no Y inversion
        return (nx * ms + ox, ny * ms + oy)

    # ── Paint ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        ms, ox, oy = self._map_geometry()

        # Refresh the token palette once per paint (cheap dict of QColors)
        # so every layer below theme-tracks.
        self._pal = self._palette()

        # Layer 1: Map image (cached rescale — only recomputed on resize/map change)
        if self._map_pixmap and not self._map_pixmap.isNull():
            ms_int = int(ms)
            if self._scaled_pixmap is None or self._cached_map_size != ms_int:
                self._scaled_pixmap = self._map_pixmap.scaled(
                    ms_int, ms_int, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self._cached_map_size = ms_int
            painter.drawPixmap(int(ox), int(oy), self._scaled_pixmap)
        else:
            painter.fillRect(QRectF(ox, oy, ms, ms), self._pal["well"])
            if not self._zones:
                # The named-zone outlines are the map sketch when present;
                # only a zone-less map needs the identifying fallback text.
                painter.setPen(self._pal["muted"])
                painter.drawText(
                    QRectF(ox, oy, ms, ms),
                    Qt.AlignCenter,
                    f"Map: {self._map_name}",
                )

        # Layer 1.5: named-zone outlines + labels — UNDER everything dynamic
        if self._zones:
            self._draw_zones(painter, ms, ox, oy)

        # Layer 1.75: movement trails (under grenades and players)
        if self._trails_enabled and self._trails:
            self._draw_trails(painter)

        # Layer 2: Grenades
        for nade in self._nades:
            self._draw_nade(painter, nade)

        # Layer 2.5: planted C4 marker
        if self._bomb is not None:
            self._draw_bomb(painter)

        # Layer 3: Ghosts
        for ghost in self._ghosts:
            self._draw_player(painter, ghost, is_ghost=True)

        # Layer 4: Players
        for player in self._players:
            self._draw_player(painter, player)

        # Layer 4.5: Ghost Mode dual-path overlay (frame 14)
        if self._ghost_overlay:
            self._draw_ghost_overlay(painter, ms, ox, oy)

        # Layer 5: score box overlay (topmost)
        if self._score_info:
            self._draw_score_box(painter)

        painter.end()

    # ── Zone / trail / bomb / score layers (frame 13) ──

    def _draw_zones(self, p: QPainter, ms: float, ox: float, oy: float):
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(self._pal["zone"], 1))
        for zone in self._zones:
            p.drawRect(
                QRectF(ox + zone["x"] * ms, oy + zone["y"] * ms, zone["w"] * ms, zone["h"] * ms)
            )
        # Build the two label fonts once per paint — not once per zone.
        major_font = Typography.font("title")
        minor_font = _caption_font()
        p.setPen(self._pal["zone_label"])
        for zone in self._zones:
            if not zone["label"]:
                continue
            p.setFont(major_font if zone["major"] else minor_font)
            p.drawText(
                QRectF(ox + zone["x"] * ms, oy + zone["y"] * ms, zone["w"] * ms, zone["h"] * ms),
                Qt.AlignCenter,
                zone["label"],
            )

    def _draw_trails(self, p: QPainter):
        p.setBrush(Qt.NoBrush)
        for is_ct, points in self._trails.values():
            if len(points) < 2:
                continue
            color = with_alpha(self._pal["ct" if is_ct else "t"], _TRAIL_ALPHA)
            p.setPen(QPen(color, 1))
            polyline = QPolygonF([QPointF(*self._world_to_screen(x, y)) for x, y in points])
            p.drawPolyline(polyline)

    def _draw_bomb(self, p: QPainter):
        try:
            sx, sy = self._world_to_screen(float(self._bomb["x"]), float(self._bomb["y"]))
        except (KeyError, TypeError, ValueError):
            return
        center = QPointF(sx, sy)
        p.setPen(Qt.NoPen)
        p.setBrush(self._pal["bomb"])
        p.drawEllipse(center, 11, 11)
        p.setPen(self._pal["bomb_text"])
        p.setFont(Typography.mono_caption(bold=True))
        p.drawText(QRectF(sx - 11, sy - 11, 22, 22), Qt.AlignCenter, "C4")
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(with_alpha(self._pal["accent"], 180), 1.5))
        p.drawEllipse(center, 18, 18)

    def _score_box_anchor_right(self) -> bool:
        """Score box pins top-left (frame 13) unless Ghost Mode's legend
        occupies that corner (frame 14) — then it pins top-right."""
        return self._ghost_overlay is not None

    # ── Ghost Mode overlay (frame 14) ──

    def _norm_point(self, nx: float, ny: float, ms: float, ox: float, oy: float) -> QPointF:
        return QPointF(ox + float(nx) * ms, oy + float(ny) * ms)

    def _draw_ghost_overlay(self, p: QPainter, ms: float, ox: float, oy: float):
        ov = self._ghost_overlay
        t = get_tokens()
        # Frame 14 draws the ghost in purple; no purple token exists, so the
        # ghost channel uses the in-system analog `info` per token discipline.
        info = QColor(t.info)
        accent = QColor(self._pal["accent"])
        label_font = _caption_font(bold=True)
        p.setFont(label_font)
        fm = QFontMetrics(label_font)

        def points_of(key):
            return [
                self._norm_point(pt[0], pt[1], ms, ox, oy)
                for pt in (ov.get(key) or [])
                if isinstance(pt, (tuple, list)) and len(pt) >= 2
            ]

        def endpoint(center: QPointF, color: QColor, label: str):
            p.setPen(QPen(self._pal["text"], 2))
            p.setBrush(color)
            p.drawEllipse(center, 9, 9)
            if label:
                p.setPen(color)
                tw = fm.horizontalAdvance(label)
                p.drawText(QPointF(center.x() - tw / 2, center.y() - 14), label)

        # Ghost smokes (dashed muted circles + caption)
        for smoke in ov.get("smokes") or []:
            try:
                center = self._norm_point(smoke["x"], smoke["y"], ms, ox, oy)
            except (KeyError, TypeError, ValueError):
                continue
            pen = QPen(with_alpha(self._pal["smoke"], 120), 1)
            pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.setBrush(with_alpha(self._pal["smoke"], 46))
            p.drawEllipse(center, 30, 30)
            label = str(smoke.get("label", ""))
            if label:
                p.setPen(self._pal["muted"])
                p.setFont(_caption_font())
                p.drawText(
                    QRectF(center.x() - 60, center.y() - 8, 120, 16), Qt.AlignCenter, label
                )
                p.setFont(label_font)

        # Ghost (pro) path — dashed 2px info
        ghost_pts = points_of("ghost_path")
        if len(ghost_pts) >= 2:
            pen = QPen(info, 2)
            pen.setStyle(Qt.CustomDashLine)
            pen.setDashPattern([4.0, 3.0])
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPolygonF(ghost_pts))
        if ghost_pts:
            endpoint(ghost_pts[-1], info, str(ov.get("ghost_label", "")))

        # Your path — solid 3px accent
        you_pts = points_of("you_path")
        if len(you_pts) >= 2:
            p.setPen(QPen(accent, 3))
            p.setBrush(Qt.NoBrush)
            p.drawPolyline(QPolygonF(you_pts))
        if you_pts:
            endpoint(you_pts[-1], accent, str(ov.get("you_label", "")))
            if ov.get("you_died"):
                end = you_pts[-1]
                p.setPen(QPen(QColor(t.error), 2))
                p.drawLine(QPointF(end.x() - 6, end.y() - 6), QPointF(end.x() + 6, end.y() + 6))
                p.drawLine(QPointF(end.x() - 6, end.y() + 6), QPointF(end.x() + 6, end.y() - 6))

        # Divergence points — dashed accent rings + captions
        div_pen = QPen(accent, 1.5)
        div_pen.setStyle(Qt.CustomDashLine)
        div_pen.setDashPattern([3.0, 2.0])
        cap_font = _caption_font()
        cap_fm = QFontMetrics(cap_font)
        for point in ov.get("divergence_points") or []:
            try:
                center = self._norm_point(point["x"], point["y"], ms, ox, oy)
            except (KeyError, TypeError, ValueError):
                continue
            p.setPen(div_pen)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(center, 14, 14)
            label = str(point.get("label", ""))
            if label:
                p.setFont(cap_font)
                p.setPen(accent)
                tw = cap_fm.horizontalAdvance(label)
                p.drawText(QPointF(center.x() - tw / 2, center.y() + 14 + cap_fm.ascent() + 2), label)
                p.setFont(label_font)

        # Legend chip strip (top-left)
        legend = ov.get("legend") or {}
        if legend:
            self._draw_ghost_legend(p, legend, info, accent)

    def _draw_ghost_legend(self, p: QPainter, legend: dict, info: QColor, accent: QColor):
        t = get_tokens()
        pad = t.spacing_md
        title_font = _caption_font(bold=True)
        row_font = _caption_font()
        title_fm = QFontMetrics(title_font)
        row_fm = QFontMetrics(row_font)
        rows = [
            ("you", legend.get("you", "")),
            ("ghost", legend.get("ghost", "")),
            ("divergence", legend.get("divergence", "")),
        ]
        title = str(legend.get("title", ""))
        sample_w = 20 + t.spacing_sm
        box_w = (
            max(
                title_fm.horizontalAdvance(title),
                max((row_fm.horizontalAdvance(str(text)) for _k, text in rows), default=0)
                + sample_w,
            )
            + 2 * pad
        )
        row_h = row_fm.height() + t.spacing_xs
        box_h = pad + title_fm.height() + t.spacing_xs + len(rows) * row_h + pad - t.spacing_xs
        x = y = t.spacing_lg

        p.setPen(Qt.NoPen)
        p.setBrush(self._pal["overlay_bg"])
        p.drawRoundedRect(QRectF(x, y, box_w, box_h), t.radius_sm, t.radius_sm)

        p.setFont(title_font)
        p.setPen(self._pal["text"])
        baseline = y + pad + title_fm.ascent()
        p.drawText(QPointF(x + pad, baseline), title)

        p.setFont(row_font)
        row_y = y + pad + title_fm.height() + t.spacing_xs
        for kind, text in rows:
            mid = row_y + row_fm.height() / 2
            if kind == "you":
                p.setPen(QPen(accent, 3))
                p.drawLine(QPointF(x + pad, mid), QPointF(x + pad + 20, mid))
            elif kind == "ghost":
                pen = QPen(info, 3)
                pen.setStyle(Qt.CustomDashLine)
                pen.setDashPattern([2.0, 1.5])
                p.setPen(pen)
                p.drawLine(QPointF(x + pad, mid), QPointF(x + pad + 20, mid))
            else:
                pen = QPen(accent, 1.5)
                pen.setStyle(Qt.DashLine)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(QPointF(x + pad + 10, mid), 5, 5)
            p.setPen(self._pal["text"])
            p.drawText(QPointF(x + pad + sample_w, row_y + row_fm.ascent()), str(text))
            row_y += row_h

    def _draw_score_box(self, p: QPainter):
        lay = self._score_layout
        if not lay:
            return
        t = get_tokens()
        x = (
            self.width() - t.spacing_lg - lay["box_w"]
            if self._score_box_anchor_right()
            else t.spacing_lg
        )
        y = t.spacing_lg

        p.setPen(Qt.NoPen)
        p.setBrush(self._pal["overlay_bg"])
        p.drawRoundedRect(QRectF(x, y, lay["box_w"], lay["box_h"]), t.radius_sm, t.radius_sm)

        baseline = y + lay["pad"] + lay["ascent"]
        for text, key, font, dx in lay["segments"]:
            p.setFont(font)
            p.setPen(self._pal[key])
            p.drawText(QPointF(x + lay["pad"] + dx, baseline), text)
        if lay["caption"]:
            p.setFont(lay["cap_font"])
            p.setPen(self._pal["muted"])
            p.drawText(
                QPointF(x + lay["pad"], baseline + lay["gap"] + lay["cap_ascent"]),
                lay["caption"],
            )

    # ── Player Drawing ──

    def _draw_player(self, p: QPainter, player: InterpolatedPlayerState, is_ghost=False):
        px, py = self._world_to_screen(player.x, player.y)

        is_ct = (
            player.team == Team.CT
            if isinstance(player.team, Team)
            else "CT" in str(player.team).upper()
        )

        if not player.is_alive:
            color = QColor(self._pal["dead"])
        elif is_ct:
            color = QColor(self._pal["ct"])
        else:
            color = QColor(self._pal["t"])

        if is_ghost or getattr(player, "is_ghost", False):
            color.setAlpha(77)

        r = PLAYER_RADIUS

        # Selection highlight
        if player.player_id == self._selected_player_id:
            p.setPen(Qt.NoPen)
            p.setBrush(self._pal["selected"])
            p.drawEllipse(QPointF(px, py), r + 4, r + 4)

        # Player circle
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(px, py), r, r)

        # FoV cone (alive only)
        if player.is_alive:
            p.save()
            p.translate(px, py)
            p.rotate(90 - player.yaw)

            cone_color = QColor(color)
            cone_color.setAlpha(77)
            p.setPen(Qt.NoPen)
            p.setBrush(cone_color)

            # Triangle pointing up (-Y in Qt = north on map)
            cone = QPolygonF(
                [
                    QPointF(0, 0),
                    QPointF(-15, -30),
                    QPointF(15, -30),
                ]
            )
            p.drawPolygon(cone)
            p.restore()

        # Player name (above) — selected player only, in team color
        # (frame 13 labels exactly one dot; naming all ten is unreadable
        # over the radar).
        if player.player_id == self._selected_player_id and not is_ghost:
            p.setPen(self._pal["t" if not is_ct else "ct"])
            p.setFont(self._name_font)
            tw = self._name_fm.horizontalAdvance(player.name)
            p.drawText(int(px - tw / 2), int(py - r - 4), player.name)

        # Health bar (below)
        if player.is_alive:
            bar_w = r * 2
            bar_h = 2
            bar_x = px - r
            bar_y = py + r + 2
            p.fillRect(QRectF(bar_x, bar_y, bar_w, bar_h), with_alpha(self._pal["well"], 128))
            hp_key = "hp_high" if player.hp > 50 else "hp_low"
            hp_color = with_alpha(self._pal[hp_key], 204)
            p.fillRect(QRectF(bar_x, bar_y, bar_w * (player.hp / 100.0), bar_h), hp_color)

    # ── Grenade Drawing ──

    def _draw_nade(self, p: QPainter, nade):
        start_vis = nade.throw_tick or nade.starting_tick
        end_vis = nade.ending_tick + (5 * TICK_RATE)
        if not (start_vis <= self._current_tick <= end_vis):
            return

        # Interpolate position if in flight
        nx, ny = nade.x, nade.y
        if (
            nade.throw_tick
            and nade.throw_tick <= self._current_tick < nade.starting_tick
            and len(nade.trajectory) >= 2
        ):
            duration = nade.starting_tick - nade.throw_tick
            t = 1.0 if duration == 0 else (self._current_tick - nade.throw_tick) / duration
            p1, p2 = nade.trajectory[0], nade.trajectory[1]
            nx = p1[0] + (p2[0] - p1[0]) * t
            ny = p1[1] + (p2[1] - p1[1]) * t

        sx, sy = self._world_to_screen(nx, ny)

        # Trajectory
        if nade.throw_tick and self._current_tick >= nade.throw_tick:
            self._draw_trajectory(p, nade)

        # Detonation radius overlay
        if nade.starting_tick <= self._current_tick <= nade.ending_tick:
            self._draw_detonation_overlay(p, nade, sx, sy)

        # Active effect
        if nade.starting_tick <= self._current_tick <= nade.ending_tick:
            if nade.nade_type == NadeType.SMOKE:
                age = (self._current_tick - nade.starting_tick) / float(TICK_RATE)
                size = min(85, 20 + age * 18) if age > 0 else 60
                p.setPen(Qt.NoPen)
                p.setBrush(with_alpha(self._pal["smoke"], 89))
                p.drawEllipse(QPointF(sx, sy), size / 2, size / 2)
                p.setBrush(with_alpha(self._pal["text"], 26))
                p.drawEllipse(QPointF(sx, sy), size * 0.4, size * 0.4)
            elif nade.nade_type == NadeType.MOLOTOV:
                pulse = 0.5 + 0.15 * math.sin(self._current_tick / TICK_RATE * 8)
                p.setPen(Qt.NoPen)
                p.setBrush(with_alpha(self._pal["molotov"], int(pulse * 255)))
                p.drawEllipse(QPointF(sx, sy), 25, 25)
                p.setBrush(with_alpha(self._pal["he"], int((0.2 + pulse * 0.2) * 255)))
                p.drawEllipse(QPointF(sx, sy), 15, 15)

            # Duration progress arc
            total_ticks = nade.ending_tick - nade.starting_tick
            if total_ticks > 0:
                progress = 1.0 - ((self._current_tick - nade.starting_tick) / total_ticks)
                if progress > 0:
                    p.setPen(QPen(with_alpha(self._pal["text"], 153), 2))
                    p.setBrush(Qt.NoBrush)
                    span = int(progress * 360 * 16)
                    p.drawArc(QRectF(sx - 10, sy - 10, 20, 20), 90 * 16, span)

        # Central dot
        p.setPen(Qt.NoPen)
        p.setBrush(self._pal["text"])
        p.drawEllipse(QPointF(sx, sy), 3, 3)

    def _draw_detonation_overlay(self, p: QPainter, nade, sx, sy):
        radius_units = GRENADE_RADII.get(nade.nade_type)
        if radius_units is None:
            return

        color = self._pal[_NADE_PALETTE_KEYS.get(nade.nade_type, "text")]
        origin_px, _ = self._world_to_screen(nade.x, nade.y)
        edge_px, _ = self._world_to_screen(nade.x + radius_units, nade.y)
        pixel_radius = abs(edge_px - origin_px)
        if pixel_radius < 2:
            return

        base_alpha = 25 if nade.nade_type == NadeType.FLASH else 38

        # Radius fill
        fill = QColor(color)
        fill.setAlpha(base_alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(fill)
        p.drawEllipse(QPointF(sx, sy), pixel_radius, pixel_radius)

        # Border ring
        border = QColor(color)
        border.setAlpha(base_alpha + 38)
        p.setPen(QPen(border, 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(sx, sy), pixel_radius, pixel_radius)

        # Flash inner zone (300 units)
        if nade.nade_type == NadeType.FLASH:
            inner_edge, _ = self._world_to_screen(nade.x + 300, nade.y)
            inner_r = abs(inner_edge - origin_px)
            if inner_r > 2:
                inner_fill = QColor(color)
                inner_fill.setAlpha(51)
                p.setPen(Qt.NoPen)
                p.setBrush(inner_fill)
                p.drawEllipse(QPointF(sx, sy), inner_r, inner_r)

    def _draw_trajectory(self, p: QPainter, nade):
        if not nade.trajectory or len(nade.trajectory) < 2:
            return

        fade_start = nade.starting_tick + (3 * TICK_RATE)
        base_alpha = 0.5
        if self._current_tick > fade_start:
            base_alpha = max(0, 0.5 - (self._current_tick - fade_start) / (2 * float(TICK_RATE)))
        if base_alpha <= 0:
            return

        base = self._pal[_NADE_PALETTE_KEYS.get(nade.nade_type, "he")]

        min_z = min(pt[2] for pt in nade.trajectory)
        max_z = max(pt[2] for pt in nade.trajectory)
        z_range = max(1.0, max_z - min_z)

        last_sx, last_sy = None, None
        apex_idx = 0
        cur_max_z = float("-inf")

        for i, (wx, wy, wz) in enumerate(nade.trajectory):
            sx, sy = self._world_to_screen(wx, wy)
            if wz > cur_max_z:
                cur_max_z = wz
                apex_idx = i

            if i > 0 and last_sx is not None:
                rel_h = (wz - min_z) / z_range
                seg_width = 1.0 + rel_h * 2.5
                seg_alpha = int(base_alpha * (0.6 + rel_h * 0.4) * 255)
                p.setPen(QPen(with_alpha(base, seg_alpha), seg_width))
                p.drawLine(QPointF(last_sx, last_sy), QPointF(sx, sy))

            last_sx, last_sy = sx, sy

        # Apex marker
        if apex_idx < len(nade.trajectory):
            ax, ay, _ = nade.trajectory[apex_idx]
            apx, apy = self._world_to_screen(ax, ay)
            p.setPen(Qt.NoPen)
            p.setBrush(with_alpha(self._pal["text"], int(base_alpha * 0.8 * 255)))
            p.drawEllipse(QPointF(apx, apy), 3, 3)

    # ── Mouse Handling ──

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)

        mx = event.position().x()
        my = event.position().y()

        for player in self._players:
            px, py = self._world_to_screen(player.x, player.y)
            if math.hypot(mx - px, my - py) < PLAYER_RADIUS * HITBOX_MULTIPLIER:
                new_id = player.player_id if self._selected_player_id != player.player_id else None
                self.selected_player_id = new_id
                return

        self.selected_player_id = None
