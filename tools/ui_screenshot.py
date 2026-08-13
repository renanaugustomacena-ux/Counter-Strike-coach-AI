"""Offscreen UI screenshot harness — renders real screens with fixture data.

Boots ONLY the presentation layer (ThemeEngine + MainWindow + screens).
Never starts backend services, the Session Engine daemon, SBERT downloads,
or AppState polling — safe to run on any machine, including CI.

Usage:
    python tools/ui_screenshot.py --screens home,match_history --themes CS2 \
        --out docs/ux-audit/renders-atlas

Output: <out>/<THEME>/<screen>.png (window-sized grabs, default 1440x900).
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

ALL_SCREENS = [
    "home",
    "coach",
    "match_history",
    "match_detail",
    "performance",
    "tactical_viewer",
    "pro_comparison",
    "pro_player_detail",
    "settings",
    "profile",
    "user_profile",
    "steam_config",
    "faceit_config",
    "wizard",
    "help",
]


def _settle(app, rounds: int = 20, wait_ms: int = 100) -> None:
    """Let queued signals deliver and background workers finish.

    Screens kick off Worker DB loads in on_enter(); their results arrive as
    queued signals. Fixtures must be injected AFTER those land so the fixture
    state wins deterministically.
    """
    from PySide6.QtCore import QThreadPool

    pool = QThreadPool.globalInstance()
    for _ in range(rounds):
        app.processEvents()
        if pool.waitForDone(wait_ms):
            break
    app.processEvents()


def _wait(app, ms: int) -> None:
    """Spin the event loop for ``ms`` wall-clock milliseconds.

    In-flight UI animations (e.g. the 200 ms list fade-in) must reach their
    end state before grabbing, or screenshots capture half-faded content.
    """
    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    QCoreApplication.processEvents()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--screens", default=",".join(ALL_SCREENS))
    ap.add_argument("--themes", default="CS2")
    ap.add_argument("--out", default="docs/ux-audit/renders-atlas")
    ap.add_argument(
        "--no-fixtures",
        action="store_true",
        help="Render natural (DB / cold-start) state instead of fixture data",
    )
    ap.add_argument(
        "--collapse-nav",
        action="store_true",
        help="Collapse the nav sidebar to its 60px icon rail before grabbing",
    )
    ap.add_argument("--size", default="1440x900")
    args = ap.parse_args()
    width, height = (int(x) for x in args.size.lower().split("x"))

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)

    import ui_fixtures
    from Programma_CS2_RENAN.apps.qt_app import app as qt_app_module
    from Programma_CS2_RENAN.apps.qt_app.core.theme_engine import ThemeEngine
    from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

    wanted = [s.strip() for s in args.screens.split(",") if s.strip()]
    exit_code = 0

    for theme_name in (t.strip() for t in args.themes.split(",") if t.strip()):
        theme = ThemeEngine()
        theme.register_fonts()
        theme.apply_theme(theme_name, app)

        window = MainWindow()
        window.set_wallpaper("")  # flat surface per the design atlas
        screens = qt_app_module._create_screens(theme)
        for name, widget in screens.items():
            window.register_screen(name, widget)
        window.resize(width, height)
        window.show()
        app.processEvents()
        if args.collapse_nav:
            window._nav_sidebar.toggle_collapse()
            _wait(app, 400)  # let the 200 ms width animation reach 60px

        out_dir = Path(args.out) / theme_name.replace(".", "")
        out_dir.mkdir(parents=True, exist_ok=True)

        for name in wanted:
            if name not in screens:
                print(f"skip unknown screen: {name}", file=sys.stderr)
                exit_code = 2
                continue
            window.switch_screen(name)
            _settle(app)
            if not args.no_fixtures:
                ui_fixtures.inject(name, screens[name])
            _wait(app, 400)  # let list fade-ins and property animations finish
            dest = out_dir / f"{name}.png"
            if not window.grab().save(str(dest), "PNG"):
                print(f"FAILED to save {dest}", file=sys.stderr)
                exit_code = 1
                continue
            print(f"wrote {dest}")

        window.close()
        app.processEvents()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
