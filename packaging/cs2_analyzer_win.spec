# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Macena CS2 Analyzer — Windows build (PySide6/Qt frontend).

Usage:
    python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN

Output:  dist/Macena_CS2_Analyzer/
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# --- Paths ---
PROJECT_ROOT = Path(SPECPATH).parent.resolve()
APP_DIR = PROJECT_ROOT / "Programma_CS2_RENAN"

block_cipher = None

# --- Data files ---
# Each tuple: (source_glob_or_file, dest_dir_inside_bundle)
datas = [
    # Assets (fonts, themes, map images)
    (str(APP_DIR / "PHOTO_GUI"), "Programma_CS2_RENAN/PHOTO_GUI"),
    # Config / data files
    (str(APP_DIR / "data" / "map_config.json"), "Programma_CS2_RENAN/data"),
(str(APP_DIR / "data" / "dataset.csv"), "Programma_CS2_RENAN/data"),
    (str(APP_DIR / "data" / "external"), "Programma_CS2_RENAN/data/external"),
    (str(APP_DIR / "core" / "integrity_manifest.json"), "Programma_CS2_RENAN/core"),
    # Knowledge base
    (str(APP_DIR / "backend" / "knowledge" / "tactical_knowledge.json"), "Programma_CS2_RENAN/backend/knowledge"),
    # Help docs
    (str(APP_DIR / "data" / "docs"), "Programma_CS2_RENAN/data/docs"),
    # Alembic migrations (root-level alembic/ directory)
    (str(PROJECT_ROOT / "alembic"), "alembic"),
    # Qt theme stylesheets
    (str(APP_DIR / "apps" / "qt_app" / "themes"), "Programma_CS2_RENAN/apps/qt_app/themes"),
    # i18n translations
    (str(APP_DIR / "assets" / "i18n"), "Programma_CS2_RENAN/assets/i18n"),
    # Design-atlas type stack (Inter, Space Grotesk, JetBrains Mono weights).
    # Q6-FONTS: was missing — the packaged app shipped only PHOTO_GUI fonts,
    # so every mono/display QSS rule silently fell back to Consolas/Roboto.
    (str(APP_DIR / "assets" / "fonts"), "Programma_CS2_RENAN/assets/fonts"),
    # Tactical map named-zone overlays (map_widget.load_map_zones)
    (str(APP_DIR / "assets" / "map_zones"), "Programma_CS2_RENAN/assets/map_zones"),
    # WP4c (D-32): HLTV metadata seed, copied to the user's db folder on first
    # boot (database.seed_hltv_metadata_if_absent). Absent in CI: filtered below.
    (str(APP_DIR / "backend" / "storage" / "hltv_metadata.db"), "Programma_CS2_RENAN/backend/storage"),
    # Coach book (init_knowledge_base reads book/index.json beside its module)
    (str(APP_DIR / "backend" / "knowledge" / "book"), "Programma_CS2_RENAN/backend/knowledge/book"),
    # Alembic config at the bundle root, beside alembic/ (db_migrate._alembic_paths)
    (str(PROJECT_ROOT / "alembic.ini"), "."),
    # SVG icon sprite: svg_icon_provider resolves design/assets/icons/sprite.svg
    # from the project root (= _MEIPASS when frozen); the first packaged run
    # fell back to QPainterPath icons because it was not bundled (WP4c).
    (str(PROJECT_ROOT / "design" / "assets" / "icons" / "sprite.svg"), "design/assets/icons"),
]

# Filter out non-existent paths (graceful handling for CI)
datas = [(src, dst) for src, dst in datas if os.path.exists(src)]

# Factory models (WP4c, D-32): whatever the operator places in models/global/
# ships — checkpoints AND their .pt.meta.json sidecars (load_nn refuses a
# checkpoint without one). See Programma_CS2_RENAN/models/global/README.txt.
datas += [
    (str(path), "Programma_CS2_RENAN/models/global")
    for path in sorted((APP_DIR / "models" / "global").glob("*.pt*"))
]

# --- Hidden imports ---
# Modules imported lazily (inside functions) that PyInstaller cannot detect
hiddenimports = [
    # Qt frontend
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    # ML
    "torch",
    "torch.nn",
    "torch.optim",
    # DB
    "sqlmodel",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "alembic",
    # Parsing
    "demoparser2",
    "pandas",
    "numpy",
    # Project submodules with deferred imports
    "Programma_CS2_RENAN.apps.qt_app.core.app_state",
    "Programma_CS2_RENAN.apps.qt_app.core.theme_engine",
    "Programma_CS2_RENAN.apps.qt_app.core.i18n_bridge",
    "Programma_CS2_RENAN.backend.nn.factory",
    "Programma_CS2_RENAN.backend.nn.jepa_model",
    "Programma_CS2_RENAN.backend.nn.training_orchestrator",
    "Programma_CS2_RENAN.backend.nn.coach_manager",
    "Programma_CS2_RENAN.backend.analysis.belief_model",
    "Programma_CS2_RENAN.backend.analysis.game_tree",
    "Programma_CS2_RENAN.backend.coaching.hybrid_engine",
    "Programma_CS2_RENAN.backend.knowledge.rag_knowledge",
    "Programma_CS2_RENAN.backend.knowledge.experience_bank",
    "Programma_CS2_RENAN.backend.services.coaching_service",
    "Programma_CS2_RENAN.backend.storage.state_manager",
    "Programma_CS2_RENAN.backend.storage.database",
    "Programma_CS2_RENAN.backend.control.console",
    "Programma_CS2_RENAN.core.session_engine",
    "Programma_CS2_RENAN.core.localization",
    "Programma_CS2_RENAN.core.config",
    "Programma_CS2_RENAN.observability.rasp",
    "Programma_CS2_RENAN.observability.logger_setup",
]

# Collect all Programma_CS2_RENAN submodules — except the test suite (WP4c):
# it would drag pytest and every test fixture into the bundle.
try:
    hiddenimports += [
        name
        for name in collect_submodules("Programma_CS2_RENAN")
        if not name.startswith("Programma_CS2_RENAN.tests")
    ]
except Exception:
    pass

# --- Analysis ---
a = Analysis(
    [str(APP_DIR / "apps" / "qt_app" / "app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test-only and dev-only modules
        "pytest",
        "coverage",
        "pre_commit",
        "black",
        "isort",
        "Programma_CS2_RENAN.tests",
        # NOTE (P10-02): matplotlib is REQUIRED at runtime by widgets.py, visualizer.py,
        # visualization_service.py, and embedding_projector.py. Do NOT exclude it.
        "IPython",
        "notebook",
        "jupyterlab",
        # Exclude optional heavy deps not needed for runtime
        # NOTE: sentence_transformers is REQUIRED for Experience Bank SBERT — do NOT exclude
        "shap",
        "playwright",
        # Kivy/KivyMD (migrated to Qt)
        "kivy",
        "kivymd",
        # RAP optional deps (not needed at runtime)
        "ncps",
        "hflayers",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Macena_CS2_Analyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed app (no console)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Macena_CS2_Analyzer",
)
