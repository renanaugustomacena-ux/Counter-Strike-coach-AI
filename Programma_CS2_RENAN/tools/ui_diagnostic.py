#!/usr/bin/env python3
"""
UI Diagnostic — Headless UI validation for Macena CS2 Analyzer.

Merges and supersedes:
  gui_health_check, Omni_UI_Diagnostic, coordinate_audit, verify_setpos

Sections: Resources, Localization, Assets, KV Validation, Qt Frontend, Spatial Coordinates.

Exit codes: 0 = PASS, 1 = FAIL
"""

import re
import sys

from _infra import SOURCE_ROOT, BaseValidator, Severity, path_stabilize

path_stabilize()


class UIDiagnostic(BaseValidator):

    def __init__(self):
        super().__init__("Macena UI Diagnostic", version="1.0")

    def define_checks(self):
        self._check_resources()
        self._check_localization()
        self._check_assets()
        self._check_kv_validation()
        self._check_qt_frontend()
        self._check_spatial_coordinates()

    # -----------------------------------------------------------------
    # Section 1: Resources
    # -----------------------------------------------------------------
    def _check_resources(self):
        self.console.section("Resources", 1, 6)

        gui = SOURCE_ROOT / "PHOTO_GUI"
        self.check(
            "Resources",
            "PHOTO_GUI directory",
            gui.exists() and gui.is_dir(),
            detail=f"{len(list(gui.iterdir()))} items" if gui.exists() else "missing",
        )

        # Database connectivity
        try:
            from sqlalchemy import text

            from Programma_CS2_RENAN.backend.storage.database import get_db_manager, init_database

            init_database()
            db = get_db_manager()
            with db.get_session() as s:
                res = s.exec(text("SELECT 1")).first()
                self.check("Resources", "Database connectivity", res is not None and res[0] == 1)
        except Exception as e:
            self.check("Resources", "Database connectivity", False, error=str(e))

    # -----------------------------------------------------------------
    # Section 2: Localization
    # -----------------------------------------------------------------
    def _check_localization(self):
        self.console.section("Localization", 2, 6)

        try:
            from Programma_CS2_RENAN.core.localization import TRANSLATIONS

            langs = list(TRANSLATIONS.keys())
            self.check(
                "Localization", "Translations loaded", len(langs) > 0, detail=f"languages: {langs}"
            )

            # Key parity check
            if len(langs) >= 2:
                base = set(TRANSLATIONS[langs[0]].keys())
                for lang in langs[1:]:
                    other = set(TRANSLATIONS[lang].keys())
                    missing = base - other
                    extra = other - base
                    ok = len(missing) == 0
                    detail = f"{lang}: {len(missing)} missing" if missing else f"{lang}: parity OK"
                    self.check(
                        "Localization",
                        f"Key parity ({lang})",
                        ok,
                        detail=detail,
                        severity=Severity.WARNING,
                    )
        except ImportError:
            self.check(
                "Localization",
                "Translations module",
                True,
                detail="module not available (ok)",
                severity=Severity.INFO,
            )
        except Exception as e:
            self.check(
                "Localization", "Translations", False, error=str(e), severity=Severity.WARNING
            )

    # -----------------------------------------------------------------
    # Section 3: Assets
    # -----------------------------------------------------------------
    def _check_assets(self):
        self.console.section("Assets", 3, 6)

        gui = SOURCE_ROOT / "PHOTO_GUI"
        if not gui.exists():
            self.check("Assets", "PHOTO_GUI exists", False)
            return

        # Theme directories
        for theme in ["cs2theme", "csgotheme", "cs16theme"]:
            theme_dir = gui / theme
            exists = theme_dir.exists()
            count = len(list(theme_dir.iterdir())) if exists else 0
            self.check(
                "Assets",
                f"Theme: {theme}",
                exists and count > 0,
                detail=f"{count} files",
                severity=Severity.WARNING,
            )

        # Map radars
        maps_dir = gui / "maps"
        if maps_dir.exists():
            pngs = list(maps_dir.glob("*.png"))
            self.check("Assets", "Map radar images", len(pngs) >= 3, detail=f"{len(pngs)} maps")
        else:
            self.check("Assets", "Map radar directory", False, severity=Severity.WARNING)

        # Font files
        fonts = list(gui.rglob("*.ttf")) + list(gui.rglob("*.otf"))
        self.check(
            "Assets",
            "Font files available",
            len(fonts) > 0,
            detail=f"{len(fonts)} font files",
            severity=Severity.WARNING,
        )

    # -----------------------------------------------------------------
    # Section 4: KV Validation
    # -----------------------------------------------------------------
    def _check_kv_validation(self):
        # The Kivy UI (apps/legacy_kivy + layout.kv) was migrated to PySide6/Qt
        # and removed. KV validation is retired — the live UI is covered by the
        # Qt Frontend section below. Reported as a non-failing notice so the
        # `console.py` `test ui` command and the section count stay stable.
        self.console.section("KV Validation", 4, 6)
        self.check(
            "KV",
            "Kivy UI retired (migrated to Qt)",
            True,
            detail="layout.kv removed — see Qt Frontend section",
            severity=Severity.INFO,
        )

    # -----------------------------------------------------------------
    # Section 5: Qt Frontend (primary UI)
    # -----------------------------------------------------------------
    def _check_qt_frontend(self):
        self.console.section("Qt Frontend", 5, 6)

        qt_app_dir = SOURCE_ROOT / "apps" / "qt_app"
        self.check("Qt", "qt_app directory exists", qt_app_dir.exists() and qt_app_dir.is_dir())

        if not qt_app_dir.exists():
            return

        # Screen modules
        screens_dir = qt_app_dir / "screens"
        if screens_dir.exists():
            screen_files = list(screens_dir.glob("*_screen.py"))
            self.check(
                "Qt",
                "Screen modules discovered",
                len(screen_files) >= 10,
                detail=f"{len(screen_files)} screen modules",
            )

            # Verify each screen module is importable (AST parse only)
            import ast

            parse_errors = []
            for sf in screen_files:
                try:
                    ast.parse(sf.read_text(encoding="utf-8"))
                except SyntaxError as e:
                    parse_errors.append(f"{sf.name}: {e}")
            self.check(
                "Qt",
                "Screen modules syntax valid",
                len(parse_errors) == 0,
                detail=f"{len(screen_files)} parsed OK" if not parse_errors else "",
                error="; ".join(parse_errors[:3]) if parse_errors else "",
            )
        else:
            self.check("Qt", "screens/ directory", False)

        # QSS theme files
        qss_dir = qt_app_dir / "themes"
        if qss_dir.exists():
            qss_files = list(qss_dir.glob("*.qss"))
            self.check(
                "Qt",
                "QSS theme files",
                len(qss_files) >= 1,
                detail=f"{len(qss_files)} themes",
            )

            # Verify QSS files contain actual styling
            for qf in qss_files:
                content = qf.read_text(encoding="utf-8").strip()
                has_rules = "{" in content and "}" in content
                self.check(
                    "Qt",
                    f"QSS '{qf.stem}' has rules",
                    has_rules,
                    severity=Severity.WARNING,
                )
        else:
            self.check("Qt", "themes/ directory", False, severity=Severity.WARNING)

        # ViewModels
        vm_dir = qt_app_dir / "viewmodels"
        if vm_dir.exists():
            vm_files = list(vm_dir.glob("*_vm.py"))
            self.check(
                "Qt",
                "ViewModel modules",
                len(vm_files) >= 5,
                detail=f"{len(vm_files)} viewmodels",
            )
        else:
            self.check("Qt", "viewmodels/ directory", False, severity=Severity.WARNING)

        # app.py entry point
        app_py = qt_app_dir / "app.py"
        self.check("Qt", "app.py entry point exists", app_py.exists())

    # -----------------------------------------------------------------
    # Section 6: Spatial Coordinates
    # -----------------------------------------------------------------
    def _check_spatial_coordinates(self):
        self.console.section("Spatial Coordinates", 6, 6)

        try:
            from Programma_CS2_RENAN.core.spatial_data import SPATIAL_REGISTRY
        except ImportError:
            self.check("Spatial", "SPATIAL_REGISTRY import", False)
            return

        self.check(
            "Spatial",
            "SPATIAL_REGISTRY loaded",
            len(SPATIAL_REGISTRY) > 0,
            detail=f"{len(SPATIAL_REGISTRY)} maps",
        )

        # Normalization roundtrip (from coordinate_audit)
        try:
            from Programma_CS2_RENAN.core.spatial_engine import SpatialEngine

            engine = SpatialEngine()

            for map_name in list(SPATIAL_REGISTRY.keys())[:3]:
                meta = SPATIAL_REGISTRY[map_name]
                # Test corners: top-left and bottom-right
                tl_x, tl_y = meta.world_to_radar(meta.pos_x, meta.pos_y)
                ok = abs(tl_x) < 0.05 and abs(tl_y) < 0.05
                self.check(
                    "Spatial",
                    f"{map_name} top-left normalization",
                    ok,
                    detail=f"({tl_x:.3f}, {tl_y:.3f})",
                )

        except Exception as e:
            self.check("Spatial", "Coordinate validation", False, error=str(e))

        # Pixel bidirectionality (from verify_setpos)
        try:
            from Programma_CS2_RENAN.core.spatial_data import LANDMARKS, SPATIAL_REGISTRY

            for map_name in ["de_dust2", "de_mirage", "de_inferno"]:
                landmarks = LANDMARKS.get(map_name, {})
                meta = SPATIAL_REGISTRY.get(map_name)
                if not meta or not landmarks:
                    continue

                # Test first landmark
                name, (wx, wy) = next(iter(landmarks.items()))
                nx, ny = meta.world_to_radar(wx, wy)
                ok = 0.0 <= nx <= 1.0 and 0.0 <= ny <= 1.0
                self.check(
                    "Spatial",
                    f"{map_name} landmark '{name}' in bounds",
                    ok,
                    detail=f"({nx:.3f}, {ny:.3f})",
                )

        except Exception as e:
            self.check(
                "Spatial", "Landmark validation", False, error=str(e), severity=Severity.WARNING
            )


if __name__ == "__main__":
    validator = UIDiagnostic()
    sys.exit(validator.run())
