"""
Headless dry-run of the Qt app structure.

Verifies that the Qt entry point, MainWindow, all screens, and theme files
are importable and structurally sound — without requiring a display server.

Screen modules are auto-discovered from the filesystem (not hardcoded).
MainWindow is validated against its required public interface.
Theme files are checked for actual QSS content, not just file size.
"""

import importlib
import os
import re
import sys
from pathlib import Path

# --- Venv Guard ---
if sys.prefix == sys.base_prefix and not os.environ.get("CI"):
    print("ERROR: Not in venv. Run: source ~/.venvs/cs2analyzer/bin/activate", file=sys.stderr)
    sys.exit(2)

# Path setup — anchored to __file__, not CWD
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_SCREENS_DIR = (
    Path(_PROJECT_ROOT) / "Programma_CS2_RENAN" / "apps" / "qt_app" / "screens"
)
_THEMES_DIR = (
    Path(_PROJECT_ROOT) / "Programma_CS2_RENAN" / "apps" / "qt_app" / "themes"
)

# MainWindow must expose these attributes/methods.
_REQUIRED_MW_ATTRS = [
    "register_screen",
    "switch_screen",
    "screen_changed",
    "set_wallpaper",
]

errors: list[str] = []


def _check(condition: bool, msg: str) -> None:
    if not condition:
        errors.append(msg)
        print(f"  [FAIL] {msg}")
    else:
        print(f"  [PASS] {msg}")


def _discover_screen_modules() -> list[str]:
    """Auto-discover *_screen.py modules from the screens directory."""
    if not _SCREENS_DIR.is_dir():
        return []
    return sorted(
        p.stem
        for p in _SCREENS_DIR.glob("*_screen.py")
        if not p.name.startswith("_")
    )


def main():
    print("=" * 60)
    print("       MACENA QT APP — BOOT STRUCTURE VALIDATOR")
    print("=" * 60)

    # --- 1. Qt app entry point ---
    print("\n[Phase 1] Qt app entry point")
    try:
        from Programma_CS2_RENAN.apps.qt_app import app as qt_app_module

        _check(
            hasattr(qt_app_module, "main") and callable(qt_app_module.main),
            "qt_app.app.main() exists and is callable",
        )
    except Exception as e:
        errors.append(f"Failed to import qt_app.app: {e}")
        print(f"  [FAIL] Import qt_app.app: {e}")

    # --- 2. MainWindow class + public interface ---
    print("\n[Phase 2] MainWindow class")
    try:
        from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow, NAV_ITEMS

        _check(True, "MainWindow class imported successfully")

        for attr in _REQUIRED_MW_ATTRS:
            _check(
                hasattr(MainWindow, attr),
                f"MainWindow has '{attr}'",
            )

        # NAV_ITEMS must be a non-empty list of 3-tuples
        _check(
            isinstance(NAV_ITEMS, list) and len(NAV_ITEMS) > 0,
            f"NAV_ITEMS is a non-empty list ({len(NAV_ITEMS)} entries)",
        )
        for i, item in enumerate(NAV_ITEMS):
            _check(
                isinstance(item, (list, tuple)) and len(item) == 3,
                f"NAV_ITEMS[{i}] is a 3-tuple: {item!r:.60}",
            )

    except Exception as e:
        errors.append(f"Failed to import MainWindow: {e}")
        print(f"  [FAIL] Import MainWindow: {e}")

    # --- 3. Auto-discovered screen modules ---
    print("\n[Phase 3] Screen modules (auto-discovered)")
    discovered = _discover_screen_modules()
    _check(len(discovered) > 0, f"Discovered {len(discovered)} screen modules on disk")

    imported_count = 0
    for mod_name in discovered:
        full = f"Programma_CS2_RENAN.apps.qt_app.screens.{mod_name}"
        try:
            importlib.import_module(full)
            imported_count += 1
        except Exception as e:
            errors.append(f"Screen import failed: {full} — {e}")
            print(f"  [FAIL] {full}: {e}")

    _check(
        imported_count == len(discovered),
        f"All {len(discovered)} screen modules imported ({imported_count}/{len(discovered)})",
    )

    # --- 4. Theme files — actual QSS content validation ---
    print("\n[Phase 4] Theme files (content validation)")
    qss_files = sorted(_THEMES_DIR.glob("*.qss")) if _THEMES_DIR.is_dir() else []
    _check(len(qss_files) >= 3, f"Found {len(qss_files)} .qss theme files (need >= 3)")

    # QSS must contain actual selectors — at minimum a QWidget block.
    _QSS_SELECTOR_RE = re.compile(r"Q\w+\s*\{")

    for qss_path in qss_files:
        name = qss_path.name
        try:
            content = qss_path.read_text(encoding="utf-8")
            _check(
                len(content) >= 200,
                f"{name}: length {len(content)} chars (>= 200)",
            )
            _check(
                bool(_QSS_SELECTOR_RE.search(content)),
                f"{name}: contains QSS selectors (QWidget {{...}})",
            )
        except Exception as e:
            errors.append(f"Theme read error: {name} — {e}")
            print(f"  [FAIL] {name}: {e}")

    # --- Summary ---
    print("\n" + "=" * 60)
    if errors:
        print(f"VERDICT: FAIL — {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("VERDICT: PASS — Qt app structure validated")
    print("=" * 60)


if __name__ == "__main__":
    main()
