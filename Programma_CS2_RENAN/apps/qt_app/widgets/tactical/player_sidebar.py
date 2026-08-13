"""Player sidebar — frame-13 roster cards with team header totals.

Each card: team dot + bold name + mono money, labeled HP (thresholded) and
AR (info) bars with values, weapon + secondary mono line, utility caption.
Dead players gray out into a DEAD card with kill-info captions when the
payload carries them. Selection = accent border (frame 13); the old bottom
detail card is gone — the roster cards now carry its data inline.
"""

from typing import Dict, List, Optional

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
from Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge import i18n
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography
from Programma_CS2_RENAN.core.playback_engine import InterpolatedPlayerState

# Inventory items that are utility, not guns — (match substrings, i18n key,
# fallback label), in fixed display order (frame 13: flash · smoke · HE · moly).
_UTILITY_KINDS = (
    (("flash",), "tactical.util_flash", "flash"),
    (("smoke",), "tactical.util_smoke", "smoke"),
    (("hegrenade", "he_grenade"), "tactical.util_he", "HE"),
    (("molotov", "incendiar", "incgrenade", "inc_grenade", "moly"), "tactical.util_moly", "moly"),
)
_NON_SECONDARY = ("knife", "c4", "defuse", "kit", "taser", "zeus", "bayonet", "karambit")


def _caption_font(*, bold: bool = False) -> QFont:
    """Caption-sized BODY font (size from tokens) without the caption role's
    all-uppercase treatment — roster metadata stays lowercase per frame 13.
    Mono captions now come from ``Typography.mono_caption``."""
    f = Typography.font("body", QFont.Bold if bold else None)
    f.setPointSize(get_tokens().font_size_caption)
    return f


def _is_utility(item: str) -> Optional[int]:
    """Index into _UTILITY_KINDS when ``item`` is a grenade, else None."""
    low = item.lower()
    for idx, (needles, _key, _fallback) in enumerate(_UTILITY_KINDS):
        if any(n in low for n in needles) or low == _fallback.lower():
            return idx
    return None


def _utility_caption(player: InterpolatedPlayerState) -> str:
    """Compose the frame-13 utility caption from the inventory list."""
    counts = [0] * len(_UTILITY_KINDS)
    for item in getattr(player, "inventory", None) or []:
        idx = _is_utility(str(item))
        if idx is not None:
            counts[idx] += 1
    parts = []
    # FIELD-GAP: InterpolatedPlayerState carries no has_defuser field today
    # (PlayerState does) — rendered only when a payload superset provides it.
    if getattr(player, "has_defuser", False):
        parts.append(i18n.get_text("tactical.defuser", "defuser"))
    for count, (_needles, key, fallback) in zip(counts, _UTILITY_KINDS):
        if count:
            parts.append(f"{count} {i18n.get_text(key, fallback)}")
    return " · ".join(parts)


def _weapon_line(player: InterpolatedPlayerState) -> str:
    """``primary + secondary`` from current weapon + inventory (frame 13)."""
    primary = (player.weapon or "").strip()
    secondary = ""
    for item in getattr(player, "inventory", None) or []:
        name = str(item).strip()
        low = name.lower()
        if not name or low == primary.lower():
            continue
        if _is_utility(name) is not None or any(n in low for n in _NON_SECONDARY):
            continue
        secondary = name
        break
    if primary and secondary:
        return f"{primary} + {secondary}"
    return primary or secondary


class _StatBar(QWidget):
    """Thin painted bar — no QSS reparse per frame (60fps-safe)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frac = 0.0
        self._color = QColor()
        self.setFixedHeight(10)

    def set_state(self, frac: float, color: QColor):
        frac = max(0.0, min(1.0, frac))
        if frac != self._frac or color != self._color:
            self._frac = frac
            self._color = QColor(color)
            self.update()

    def paintEvent(self, event):
        t = get_tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        radius = t.radius_sm / 2
        p.setBrush(QColor(t.surface_sunken))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), radius, radius)
        if self._frac > 0:
            p.setBrush(self._color)
            p.drawRoundedRect(
                QRectF(0, 0, self.width() * self._frac, self.height()), radius, radius
            )
        p.end()


class _PlayerItem(QFrame):
    """Single roster card (frame 13)."""

    clicked = Signal(object)  # Steam IDs exceed int32

    def __init__(self, player_id: int, team_color: str, parent=None):
        super().__init__(parent)
        self._player_id = player_id
        self._team_color = team_color
        self._style_bucket: Optional[tuple] = None
        self.setObjectName("roster_card")
        self.setCursor(Qt.PointingHandCursor)

        t = get_tokens()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(t.spacing_sm + 2, t.spacing_sm, t.spacing_sm + 2, t.spacing_sm)
        layout.setSpacing(t.spacing_xs)

        # Row 1: team dot · bold name · mono money / DEAD
        row1 = QHBoxLayout()
        row1.setSpacing(t.spacing_sm)
        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        row1.addWidget(self._dot)
        self._name_label = QLabel()
        self._name_label.setFont(Typography.font("body", QFont.Bold))
        row1.addWidget(self._name_label, 1)
        self._right_label = QLabel()
        self._right_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row1.addWidget(self._right_label)
        layout.addLayout(row1)

        # HP / AR rows: caption label + painted bar + value
        self._hp_label, self._hp_bar, self._hp_value = self._make_bar_row(layout, "HP")
        self._ar_label, self._ar_bar, self._ar_value = self._make_bar_row(layout, "AR")

        # Live K/D/A readout (restored pre-redesign line) — mono caption fed
        # from the InterpolatedPlayerState kills/deaths/assists fields.
        self._kda_label = QLabel()
        self._kda_label.setFont(Typography.mono_caption())
        layout.addWidget(self._kda_label)

        # Weapon (mono) + utility caption — reused as kill-info lines when dead
        self._weapon_label = QLabel()
        self._weapon_label.setFont(Typography.mono_caption())
        layout.addWidget(self._weapon_label)
        self._util_label = QLabel()
        self._util_label.setFont(_caption_font())
        layout.addWidget(self._util_label)

        # 60fps churn fix: update_data runs per interpolated frame — skip
        # QLabel.setText when the string is unchanged (per-card cache).
        self._last_texts: dict[QLabel, str] = {}

    def _set_text(self, label: QLabel, text: str) -> None:
        if self._last_texts.get(label) != text:
            self._last_texts[label] = text
            label.setText(text)

    def _make_bar_row(self, parent_layout, caption: str):
        t = get_tokens()
        row = QHBoxLayout()
        row.setSpacing(t.spacing_xs + 2)
        label = QLabel(caption)
        label.setFont(_caption_font())
        label.setFixedWidth(20)
        row.addWidget(label)
        bar = _StatBar()
        row.addWidget(bar, 1)
        value = QLabel()
        value.setFont(_caption_font())
        value.setFixedWidth(26)
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(value)
        parent_layout.addLayout(row)
        return label, bar, value

    # ── Style buckets (only re-applied when the state actually changes) ──

    def _apply_styles(self, *, alive: bool, selected: bool, has_defuser: bool):
        bucket = (alive, selected, has_defuser)
        if bucket == self._style_bucket:
            return
        self._style_bucket = bucket
        t = get_tokens()

        if selected:
            card = (
                f"QFrame#roster_card {{ background: {t.frost_bg}; "
                f"border: 1px solid {t.accent_primary}; border-radius: {t.radius_md}px; }}"
            )
        else:
            card = (
                f"QFrame#roster_card {{ background: {t.surface_raised}; "
                f"border: 1px solid {t.border_subtle}; border-radius: {t.radius_md}px; }}"
                f"QFrame#roster_card:hover {{ border: 1px solid {t.border_default}; }}"
            )
        self.setStyleSheet(card)

        dot_color = self._team_color if alive else t.text_disabled
        self._dot.setStyleSheet(
            f"background: {dot_color}; border-radius: 5px; border: none;"
        )
        name_color = t.text_primary if alive else t.text_disabled
        self._name_label.setStyleSheet(f"color: {name_color}; background: transparent;")
        if alive:
            self._right_label.setFont(Typography.mono_caption())
            self._right_label.setStyleSheet(
                f"color: {t.text_secondary}; background: transparent;"
            )
            self._weapon_label.setStyleSheet(
                f"color: {t.text_primary}; background: transparent;"
            )
            util_color = t.info if has_defuser else t.text_secondary
            self._util_label.setStyleSheet(f"color: {util_color}; background: transparent;")
            self._kda_label.setStyleSheet(
                f"color: {t.text_secondary}; background: transparent;"
            )
        else:
            self._right_label.setFont(_caption_font(bold=True))
            self._right_label.setStyleSheet(f"color: {t.error}; background: transparent;")
            self._weapon_label.setStyleSheet(
                f"color: {t.text_secondary}; background: transparent;"
            )
            self._util_label.setStyleSheet(f"color: {t.text_tertiary}; background: transparent;")
            self._kda_label.setStyleSheet(
                f"color: {t.text_tertiary}; background: transparent;"
            )
        for lbl in (self._hp_label, self._ar_label, self._hp_value, self._ar_value):
            lbl.setStyleSheet(f"color: {t.text_secondary}; background: transparent;")

    # ── Data ──

    def update_data(self, player: InterpolatedPlayerState, is_selected: bool):
        t = get_tokens()
        alive = bool(player.is_alive)
        has_defuser = bool(getattr(player, "has_defuser", False))
        self._apply_styles(alive=alive, selected=is_selected, has_defuser=has_defuser)

        self._set_text(self._name_label, player.name)

        hp = int(getattr(player, "hp", 0) or 0)
        self._set_text(self._hp_value, str(hp))
        # Pre-redesign thresholds preserved: > 60 healthy, >= 30 hurt, else critical.
        if hp > 60:
            hp_color = t.success
        elif hp >= 30:
            hp_color = t.warning
        else:
            hp_color = t.error
        self._hp_bar.set_state(hp / 100.0 if alive else 0.0, QColor(hp_color))

        kills = int(getattr(player, "kills", 0) or 0)
        deaths = int(getattr(player, "deaths", 0) or 0)
        assists = int(getattr(player, "assists", 0) or 0)
        self._set_text(self._kda_label, f"K {kills} · D {deaths} · A {assists}")

        if alive:
            self._set_text(self._right_label, f"${int(getattr(player, 'money', 0) or 0):,}")
            armor = int(getattr(player, "armor", 0) or 0)
            for w in (self._ar_label, self._ar_bar, self._ar_value):
                w.setVisible(True)
            self._set_text(self._ar_value, str(armor))
            self._ar_bar.set_state(armor / 100.0, QColor(t.info))
            self._set_text(self._weapon_label, _weapon_line(player))
            self._set_text(self._util_label, _utility_caption(player))
        else:
            self._set_text(self._right_label, i18n.get_text("tactical.dead", "DEAD"))
            self._set_text(self._hp_value, "0")
            for w in (self._ar_label, self._ar_bar, self._ar_value):
                w.setVisible(False)
            # FIELD-GAP: no kill-attribution fields exist on the frame payload
            # today — rendered only when a superset provides death_info.
            death = getattr(player, "death_info", None) or {}
            place = death.get("place")
            self._set_text(
                self._weapon_label,
                i18n.get_text("tactical.killed_at", "killed @ {place}").replace(
                    "{place}", str(place)
                )
                if place
                else "",
            )
            killer, weapon, tick = death.get("by"), death.get("weapon"), death.get("tick")
            if killer and weapon and tick is not None:
                by_line = (
                    i18n.get_text("tactical.killed_by", "by {killer} · {weapon} · tick {tick}")
                    .replace("{killer}", str(killer))
                    .replace("{weapon}", str(weapon))
                    .replace("{tick}", f"{int(tick):,}")
                )
            else:
                by_line = ""
            self._set_text(self._util_label, by_line)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._player_id)
        super().mousePressEvent(event)


class PlayerSidebar(QWidget):
    """Team sidebar: `CT · 4 ALIVE` + team money header over roster cards."""

    player_clicked = Signal(object)  # Steam IDs exceed int32

    def __init__(self, team_name: str = "TEAM", team_color: str | None = None, parent=None):
        super().__init__(parent)
        self._team_name = team_name
        # Default resolves at construction time so it theme-tracks; both
        # tactical viewer call sites pass an explicit token color.
        self._team_color = team_color or get_tokens().text_primary
        self._player_items: Dict[int, _PlayerItem] = {}

        t = get_tokens()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header — caption caps team label left, mono team money right.
        header_row = QHBoxLayout()
        header_row.setContentsMargins(
            t.spacing_md, t.spacing_md, t.spacing_md, t.spacing_sm
        )
        self._header_label = QLabel(team_name.upper())
        self._header_label.setFont(Typography.font("caption", QFont.Bold))
        self._header_label.setStyleSheet(
            f"color: {self._team_color}; background: transparent;"
        )
        header_row.addWidget(self._header_label)
        header_row.addStretch()
        self._money_label = QLabel()
        self._money_label.setFont(Typography.mono_caption())
        self._money_label.setStyleSheet(
            f"color: {self._team_color}; background: transparent;"
        )
        header_row.addWidget(self._money_label)
        layout.addLayout(header_row)

        # Scroll area for player list. Vertical scrolling only — the K/D/A
        # line made cards tall enough to overflow the fixed 200px column,
        # and a horizontal scrollbar would just clip card edges anyway.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(
            t.spacing_xs + 2, t.spacing_xs, t.spacing_xs + 2, t.spacing_xs
        )
        self._list_layout.setSpacing(t.spacing_sm)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, 1)

    def update_players(self, players: List[InterpolatedPlayerState], selected_id=None):
        active_ids = {p.player_id for p in players}

        # Evict stale
        for pid in list(self._player_items.keys()):
            if pid not in active_ids:
                item = self._player_items.pop(pid)
                self._list_layout.removeWidget(item)
                item.deleteLater()

        sorted_players = sorted(players, key=lambda x: (not x.is_alive, x.player_id))
        for p_data in sorted_players:
            is_selected = p_data.player_id == selected_id
            if p_data.player_id in self._player_items:
                item = self._player_items[p_data.player_id]
                item.update_data(p_data, is_selected)
            else:
                item = _PlayerItem(p_data.player_id, self._team_color)
                item.clicked.connect(self._on_item_clicked)
                item.update_data(p_data, is_selected)
                # Insert before stretch
                self._list_layout.insertWidget(self._list_layout.count() - 1, item)
                self._player_items[p_data.player_id] = item

        alive = sum(1 for p in players if p.is_alive)
        total_money = sum(int(getattr(p, "money", 0) or 0) for p in players)
        if players:
            alive_word = i18n.get_text("tactical.alive", "ALIVE")
            self._header_label.setText(f"{self._team_name.upper()} · {alive} {alive_word}")
            self._money_label.setText(f"${total_money:,}")
        else:
            self._header_label.setText(self._team_name.upper())
            self._money_label.setText("")

    def clear_all(self):
        for pid in list(self._player_items.keys()):
            item = self._player_items.pop(pid)
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._header_label.setText(self._team_name.upper())
        self._money_label.setText("")

    def _on_item_clicked(self, pid: int):
        self.player_clicked.emit(pid)
