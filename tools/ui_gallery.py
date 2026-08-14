"""Offscreen component-gallery renderer — frame 33/20 primitives per theme.

Composes every shared primitive with frame-realistic sample data on a
grid page per theme and grabs it to <out>/<THEME>/gallery.png (plus
gallery_chat.png for the ChatPanel + shared-primitive page). Sample
copy is dev-tool fixture data mirroring the design frames, not app UI —
screens pass their own i18n'd strings to these components.

Usage:
    python tools/ui_gallery.py --themes CS2,CS1.6 --out docs/ux-audit/renders-atlas
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "tools"))
os.chdir(_REPO)

import ui_screenshot  # noqa: E402 — bootstrap above must run first
from PySide6.QtWidgets import (  # noqa: E402
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens  # noqa: E402
from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine  # noqa: E402
from Programma_CS2_RENAN.apps.qt_app.core.typography import Typography  # noqa: E402
from Programma_CS2_RENAN.apps.qt_app.core.widgets_helpers import make_button  # noqa: E402
from Programma_CS2_RENAN.apps.qt_app.widgets.coaching import ChatPanel  # noqa: E402
from Programma_CS2_RENAN.apps.qt_app.widgets.components import (  # noqa: E402
    DbRecordCard,
    DriversList,
    EmptyState,
    MonoFooter,
    NumberedStep,
    ProBadge,
    ProgressRing,
    StatBadge,
    TipBox,
)
from Programma_CS2_RENAN.apps.qt_app.widgets.components.status_chip import StatusChip  # noqa: E402
from Programma_CS2_RENAN.apps.qt_app.widgets.skeleton import SkeletonCard  # noqa: E402
from Programma_CS2_RENAN.apps.qt_app.widgets.toast import ToastWidget  # noqa: E402


def _section(text: str) -> QLabel:
    label = QLabel(text)
    Typography.apply(label, "caption")
    return label


def _row(*widgets: QWidget) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    for widget in widgets:
        layout.addWidget(widget)
    layout.addStretch()
    return row


def _tile(widget: QWidget) -> QFrame:
    """Raised tile wrapper (frame 33 shows badges on raised panels)."""
    frame = QFrame()
    frame.setObjectName("surface_raised")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.addWidget(widget)
    return frame


def _page(width: int | None = None) -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    page.setObjectName("gallery_root")
    page.setStyleSheet(f"QWidget#gallery_root {{ background-color: {get_tokens().surface_base}; }}")
    if width:
        page.setFixedWidth(width)
    col = QVBoxLayout(page)
    col.setContentsMargins(32, 24, 32, 24)
    col.setSpacing(12)
    return page, col


def build_components_page() -> QWidget:
    """Frame 33/20 grid: controls, chips, badges, toasts, states, progress."""
    page, col = _page()

    disabled = make_button("Analyze", "primary")
    disabled.setEnabled(False)
    col.addWidget(_section(f"Controls · {get_tokens().theme_name}"))
    col.addWidget(
        _row(
            make_button("Analyze", "primary"),
            make_button("Analyze", "secondary"),
            make_button("Cancel", "ghost"),
            make_button("Delete", "danger"),
            disabled,
        )
    )

    col.addWidget(_section("StatusChip severities"))
    chips = [StatusChip(s.capitalize(), s) for s in ("online", "offline", "warning", "neutral")]
    col.addWidget(_row(*chips))

    col.addWidget(_section("StatBadge · rating_color(value)"))
    tiles = []
    ratings = [(1.28, "> 1.10 · GREEN"), (0.97, "0.90–1.10 · YELLOW"), (0.84, "< 0.90 · RED")]
    for value, caption in ratings:
        badge = StatBadge()
        badge.set_rating(value, caption)
        tiles.append(_tile(badge))
    col.addWidget(_row(*tiles))

    col.addWidget(_section("ProBadge · default / ct / t"))
    col.addWidget(_row(ProBadge(), ProBadge("CT-SIDE", side="ct"), ProBadge("T-SIDE", side="t")))

    col.addWidget(_section("Toast · 4 severities"))
    for sev, msg in [
        ("INFO", "Demo analysis complete — check Match History"),
        ("WARNING", "HLTV rate-limited — retry in 12 minutes"),
        ("ERROR", "Demo rejected — file smaller than 10 MB (DS-12)"),
        ("CRITICAL", "Teacher daemon crashed — restarted automatically"),
    ]:
        toast = ToastWidget(sev, msg)
        toast.setFixedWidth(440)
        col.addWidget(toast)

    col.addWidget(_section("EmptyState · icon well + CTA + ghost link"))
    empty = EmptyState(
        icon_text="📭",
        title="No matches found",
        description="Play some games and they'll appear here.\nOr analyze pro demos for reference.",
        cta_text="Select Demo Folder",
        link_text="Or read the Getting Started guide →",
    )
    col.addWidget(_tile(empty))

    col.addWidget(_section("ProgressRing · 48 / 64 / 80 / 128 px @ 73%"))
    sizes = (ProgressRing.SMALL, ProgressRing.DEFAULT, ProgressRing.COACH, ProgressRing.HERO)
    col.addWidget(_row(*[ProgressRing(0.73, size=s) for s in sizes]))

    col.addWidget(_section("Indeterminate bar + SkeletonCard"))
    busy = QProgressBar()
    busy.setObjectName("indeterminate")
    busy.setRange(0, 0)
    busy.setTextVisible(False)
    col.addWidget(busy)
    col.addWidget(SkeletonCard())
    return page


# ── T9/T10 gallery page — ChatPanel (frame 07) + shared primitives ──


def build_chat_page() -> QWidget:
    """ChatPanel per frame 07 + DriversList/TipBox/NumberedStep/DbRecordCard/MonoFooter."""
    page, col = _page(width=960)

    col.addWidget(_section("ChatPanel · frame 07"))
    chat = ChatPanel()
    chat.setMinimumHeight(660)
    chat.set_status(True, "ollama", "gemma4:e2b")
    chat.add_message(
        "coach",
        "Hey macena — analyzed your last 10 Mirage matches.\n"
        "Main pattern: over-peeking A-site jungle without util.",
    )
    chat.add_message("user", "How can I improve positioning?")
    chat.add_message(
        "coach",
        "Three patterns from your data vs ZywOo pro reference:\n"
        "① Hold jungle angle from stairs, not top · ② Delay peek 0.4s after flash "
        "· ③ Crouch-peek when HP < 60",
        meta="confidence 0.82 · 4 demos referenced · RAP-Pedagogy",
    )
    chat.add_message("user", "Analyze utility usage")
    chat.add_message(
        "coach", "Your HE avg 4.1s before engage vs pro 8.3s — throw earlier on execute plays."
    )
    chat.set_suggestions(
        [
            "How can I improve positioning?",
            "Analyze utility usage",
            "What should I focus on improving?",
        ]
    )
    col.addWidget(chat)

    col.addWidget(_section("DriversList · frame 06"))
    drivers = DriversList(
        [
            ("success", "Sample count · 47 personal demos analyzed"),
            ("success", "Data quality · 42 complete · 5 partial · 0 none"),
            ("warning", "Map coverage · 6 of 9 competitive maps seen"),
        ]
    )
    col.addWidget(_tile(drivers))

    col.addWidget(_section("TipBox · frame 17"))
    col.addWidget(
        TipBox(
            "Stored locally",
            "CS2_PLAYER_NAME lives in user_settings.json (chmod 0o600). "
            "Nothing uploaded anywhere. FE-04.",
        )
    )

    col.addWidget(_section("NumberedStep · frame 19"))
    ingest_desc = 'Click "Analyze Demos" — or leave the Scanner daemon running'
    for number, title, desc in [
        (1, "Set your in-game name", "Go to Settings → Quick Links → In-Game Name"),
        (2, "Point to your demo folder", "Home → Demo Analysis → Select Demo Folder"),
        (3, "Let the analyzer ingest your .dem files", ingest_desc),
    ]:
        col.addWidget(NumberedStep(number, title, desc))

    col.addWidget(_section("DbRecordCard · frame 17"))
    record = DbRecordCard(
        "Database record", 'SELECT * FROM PlayerProfile WHERE player_name = "macena"'
    )
    record.set_rows(
        [
            ("id", "42", None),
            ("player_name", "macena", None),
            ("created_at", "2025-11-12", None),
            ("matches_analyzed", "47", "success"),
            ("last_match", "2026-04-22", None),
        ]
    )
    record.setFixedWidth(380)
    col.addWidget(record)

    col.addWidget(_section("MonoFooter"))
    col.addWidget(
        MonoFooter(
            'profile_screen.py · save_user_setting("CS2_PLAYER_NAME", ...) · '
            "PlayerProfile insert on first save"
        )
    )
    return page


def _grab(app, page: QWidget, dest: Path) -> None:
    page.resize(page.sizeHint().expandedTo(page.minimumSizeHint()))
    page.show()
    ui_screenshot._settle(app)
    ui_screenshot._wait(app, 300)
    dest.parent.mkdir(parents=True, exist_ok=True)
    page.grab().save(str(dest), "PNG")
    page.close()
    print(f"wrote {dest}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--themes", default="CS2")
    ap.add_argument("--out", default="docs/ux-audit/renders-atlas")
    args = ap.parse_args()

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)

    for theme_name in (x.strip() for x in args.themes.split(",") if x.strip()):
        theme = ThemeEngine()
        theme.register_fonts()
        theme.apply_theme(theme_name, app)
        out_dir = Path(args.out) / theme_name.replace(".", "")
        _grab(app, build_components_page(), out_dir / "gallery.png")
        _grab(app, build_chat_page(), out_dir / "gallery_chat.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
