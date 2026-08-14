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

_SCREENS_DIR = Path(_PROJECT_ROOT) / "Programma_CS2_RENAN" / "apps" / "qt_app" / "screens"
_THEMES_DIR = Path(_PROJECT_ROOT) / "Programma_CS2_RENAN" / "apps" / "qt_app" / "themes"

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
    return sorted(p.stem for p in _SCREENS_DIR.glob("*_screen.py") if not p.name.startswith("_"))


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
        from Programma_CS2_RENAN.apps.qt_app.main_window import MainWindow

        _check(True, "MainWindow class imported successfully")

        for attr in _REQUIRED_MW_ATTRS:
            _check(
                hasattr(MainWindow, attr),
                f"MainWindow has '{attr}'",
            )

        # NAV_ITEMS now lives in widgets/components/nav_sidebar.py
        from Programma_CS2_RENAN.apps.qt_app.widgets.components.nav_sidebar import NAV_ITEMS

        _check(
            isinstance(NAV_ITEMS, list) and len(NAV_ITEMS) > 0,
            f"NAV_ITEMS is a non-empty list ({len(NAV_ITEMS)} entries)",
        )
        for i, item in enumerate(NAV_ITEMS):
            # (key, icon, i18n_key, shortcut) — shortcut added with the nav rework.
            is_4_tuple = isinstance(item, (list, tuple)) and len(item) == 4
            _check(is_4_tuple, f"NAV_ITEMS[{i}] is a 4-tuple: {item!r:.60}")
            shortcut = item[3] if is_4_tuple else None
            _check(
                isinstance(shortcut, str) and bool(shortcut.strip()),
                f"NAV_ITEMS[{i}] shortcut is a non-empty str: {shortcut!r}",
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

    # --- 4. Theme template — token render validation for all three themes ---
    # The per-theme *.qss files are gone: themes/base.qss.template is the sole
    # stylesheet source, rendered at runtime per theme via qss_generator.
    print("\n[Phase 4] Theme template (render validation)")
    _check(
        (_THEMES_DIR / "base.qss.template").is_file(),
        "themes/base.qss.template exists",
    )

    # Rendered QSS must contain actual selectors — at minimum a QWidget block.
    _QSS_SELECTOR_RE = re.compile(r"Q\w+\s*\{")

    try:
        from Programma_CS2_RENAN.apps.qt_app.core.design_tokens import get_tokens
        from Programma_CS2_RENAN.apps.qt_app.core.qss_generator import render_qss

        for theme_name in ("CS2", "CSGO", "CS1.6"):
            try:
                content = render_qss(get_tokens(theme_name))
                _check(
                    len(content) >= 200,
                    f"{theme_name}: rendered QSS length {len(content)} chars (>= 200)",
                )
                _check(
                    bool(_QSS_SELECTOR_RE.search(content)),
                    f"{theme_name}: rendered QSS contains selectors (QWidget {{...}})",
                )
            except Exception as e:
                errors.append(f"Theme render error: {theme_name} — {e}")
                print(f"  [FAIL] {theme_name}: {e}")
    except Exception as e:
        errors.append(f"Failed to import theme renderer: {e}")
        print(f"  [FAIL] Import design_tokens/qss_generator: {e}")

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
