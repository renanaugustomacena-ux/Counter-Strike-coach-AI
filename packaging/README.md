# Packaging — Build & Distribution

> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

> **Authority:** Rule 7 (CI/CD & Release Engineering)

This directory contains everything needed to build the Macena CS2 Analyzer into a distributable Windows application.

## File Inventory

| File | Purpose |
|------|---------|
| `cs2_analyzer_win.spec` | PyInstaller specification (172 lines) |
| `windows_installer.iss` | Inno Setup script for the Windows installer EXE (78 lines) |
| `BUILD_CHECKLIST.md` | Pre-release verification protocol (75 lines) |

## Quick Build

```bat
REM Prerequisites (Windows): venv_win created by scripts\Setup_Macena_CS2.ps1, PyInstaller installed
call venv_win\Scripts\activate

REM 1. Validate (must pass before building)
python tools/headless_validator.py

REM 2. Build
python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN

REM 3. Output
dir dist\Macena_CS2_Analyzer
```

## `cs2_analyzer_win.spec` — PyInstaller Configuration

### Entry Point

```python
# Primary entry point (Qt6 frontend)
a = Analysis(['Programma_CS2_RENAN/apps/qt_app/app.py'], ...)
```

### Bundled Data (15 entries + factory models)

The spec bundles all required runtime files (missing paths are filtered out gracefully for CI):

| Category | Files | Purpose |
|----------|-------|---------|
| Theme assets | `PHOTO_GUI/` (fonts, backgrounds) | Visual themes |
| Map config | `data/map_config.json` | Spatial data |
| Datasets | `data/dataset.csv`, `data/external/` | Reference statistics |
| Integrity | `core/integrity_manifest.json` | RASP source manifest |
| Knowledge | `backend/knowledge/tactical_knowledge.json` | RAG coaching data |
| Migrations | `alembic/` (repo root) | Database schema upgrades |
| Translations | `assets/i18n/` | Localization |
| Help docs | `data/docs/` | In-app help |
| Qt themes | `apps/qt_app/themes/` | QSS stylesheets |
| Fonts | `assets/fonts/` | Design-atlas type stack |
| Map zones | `assets/map_zones/` | Named-zone overlays for the tactical map |
| HLTV seed | `backend/storage/hltv_metadata.db` | Copied to the user's db folder on first boot (absent in CI: filtered) |
| Coach book | `backend/knowledge/book/` | Per-map knowledge read by `init_knowledge_base` |
| Alembic config | `alembic.ini` (repo root → bundle root) | Beside `alembic/` for `db_migrate` |
| Factory models | `models/global/*.pt` + `*.pt.meta.json` (globbed at build) | What `load_nn` falls back to before a local training run — see `models/global/README.txt` |

### Hidden Imports (35 explicit + auto-collection)

Critical packages that PyInstaller can't detect automatically:
- **Qt:** PySide6 (QtCore, QtGui, QtWidgets)
- **ML:** torch, torch.nn, torch.optim
- **Database:** sqlmodel, sqlalchemy (incl. sqlite dialect), alembic
- **Parsing:** demoparser2, pandas, numpy
- **Project modules:** 21 internal modules with deferred imports (app_state, jepa_model, coaching_service, etc.)
- Plus `collect_submodules("Programma_CS2_RENAN")` auto-discovers the rest of the package.

### Excluded Packages

```python
excludes = ['pytest', 'coverage', 'pre_commit', 'black', 'isort',
            'IPython', 'notebook', 'jupyterlab',
            'shap', 'playwright',
            'kivy', 'kivymd',      # migrated to Qt
            'ncps', 'hflayers',    # RAP optional deps, not needed at runtime
            'Programma_CS2_RENAN.tests']   # never in the bundle (WP4c)
```

### Bundle Sizes

| Variant | Size | Notes |
|---------|------|-------|
| CPU-only PyTorch | ~1.5 GB | Default, works everywhere |
| GPU (CUDA) PyTorch | ~2.5 GB | Auto-detected at runtime |

## `windows_installer.iss` — Inno Setup

Creates a Windows setup executable (`dist/Macena_CS2_Installer_<version>.exe`) with:
- **Version:** `AppVersion={#AppVersion}` from `version.iss`, generated from `pyproject.toml` by `tools/gen_version_iss.py` (never edited by hand)
- **Install path:** `Program Files\Macena_CS2_Analyzer` — 64-bit only (`ArchitecturesInstallIn64BitMode=x64compatible`); per-machine by default, per-user on request (`PrivilegesRequiredOverridesAllowed=dialog`)
- **User data:** never beside the exe — `%LOCALAPPDATA%\MacenaCS2Analyzer` or the folder chosen in the setup wizard (D-52); the uninstaller asks before removing it and keeps it by default
- **Languages:** English, Italian, Brazilian Portuguese
- **Compression:** LZMA (solid compression)
- **Shortcuts:** Start Menu group + optional Desktop icon; `UninstallDisplayIcon` set
- **MSVC runtime:** `vc_redist.x64.exe` is optional (`#ifexist`): when placed in `packaging/` it is installed silently if missing
- **Post-install:** Optionally launches the application; no `.dem` file association

Requires [Inno Setup](https://jrsoftware.org/isinfo.php) to compile.

## `BUILD_CHECKLIST.md` — Release Protocol

Step-by-step verification before distribution:

1. **Pre-build:** All 14 pre-commit hooks pass, test coverage >= 50%, validator exits 0
2. **Version sync:** `pyproject.toml` version matches `packaging/version.iss` (`python tools/gen_version_iss.py`)
3. **Factory models:** the `.pt` + `.pt.meta.json` pairs to ship sit in `Programma_CS2_RENAN/models/global/`
4. **Build:** `scripts\build_production.bat` (or PyInstaller with `--noconfirm`)
5. **Post-build:** packaged selftest passes (`--selftest`, scratch `LOCALAPPDATA`, dist write-denied), exe launches, maps load, charts render, `audit_binaries.py` passes
6. **Optional:** Compile the Inno Setup installer for distribution

## Build Drivers & CI

Three paths consume the spec — all end at `dist/Macena_CS2_Analyzer/`:

| Driver | Invocation | Notes |
|--------|------------|-------|
| Direct | `python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN` | Quick Build above |
| Batch pipeline | `scripts/build_production.bat` → `python -m PyInstaller … packaging/cs2_analyzer_win.spec` | Pre-flight checks (Qt/storage/torch/PyInstaller imports, factory-model notice), alembic migration, RASP manifest, `version.iss`, PyInstaller, binary audit, packaged selftest (scratch `LOCALAPPDATA`, dist write-denied via `icacls`), optional Inno Setup (`scripts/build_exe.bat` delegates here too) |
| CI dist stage | `build-distribution` job in `.github/workflows/build.yml` | Pushes to `main` only |

The CI dist stage (reworked 2026-08-14) runs on `windows-latest` and:

- pins **Python 3.12** — `requirements-lock-cpu.txt` was frozen on Python 3.12.10, and the lock is installed on the interpreter it was frozen for
- installs the locked CPU dependency set (`requirements-lock-cpu.txt`) plus a pinned `pyinstaller==6.17.0` (deliberately absent from the runtime lock)
- sets `PYTHONUTF8=1` at job level (a git-sdist dependency's `setup.py` dies under the runner's cp1252 default)
- uses one native command per step, so a failed install can no longer be masked by a later command's exit code
- validates 10 critical data files before building, then runs PyInstaller on this spec
- gates the result with `tools/audit_binaries.py`, runs the packaged selftest (`Macena_CS2_Analyzer.exe --selftest` with `LOCALAPPDATA` in `RUNNER_TEMP`; the JSON report is printed from `selftest_report.json` because a windowed exe has no stdout) and only then uploads `dist/` as the `cs2-analyzer-windows` artifact (30-day retention)

> `tools/build_pipeline.py` (the older 5-stage "industrial" pipeline) now looks for the spec under `packaging/` first; the maintained drivers are the three above.

## Development Notes

- The `.spec` file handles missing paths gracefully (for CI environments)
- `collect_submodules("Programma_CS2_RENAN")` auto-discovers project modules
- GPU detection happens at runtime via `backend/nn/config.py:get_device()`
- **matplotlib is REQUIRED** at runtime (for visualization_service.py)
- **sentence_transformers is REQUIRED** (for SBERT embeddings in RAG)
- **ncps/hflayers are NOT needed at runtime** (RAP model is experimental)
- Version numbers: `pyproject.toml` is the source; `packaging/version.iss` is generated from it (`python tools/gen_version_iss.py`) and `windows_installer.iss` includes it
