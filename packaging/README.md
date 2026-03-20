# Packaging — Build & Distribution

> **Authority:** Rule 7 (CI/CD & Release Engineering)

This directory contains everything needed to build the Macena CS2 Analyzer into a distributable Windows application.

## File Inventory

| File | Purpose |
|------|---------|
| `cs2_analyzer_win.spec` | PyInstaller specification (168 lines) |
| `windows_installer.iss` | Inno Setup script for MSI installer (42 lines) |
| `BUILD_CHECKLIST.md` | Pre-release verification protocol (76 lines) |

## Quick Build

```bash
# Prerequisites: Python 3.10+, venv activated, all deps installed
source /home/renan/.venvs/cs2analyzer/bin/activate

# 1. Validate (must pass before building)
python tools/headless_validator.py

# 2. Build
python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN

# 3. Output
ls dist/Macena_CS2_Analyzer/
```

## `cs2_analyzer_win.spec` — PyInstaller Configuration

### Entry Point

```python
# Primary entry point (Qt6 frontend)
a = Analysis(['Programma_CS2_RENAN/apps/qt_app/app.py'], ...)
```

### Bundled Data (43 entries)

The spec bundles all required runtime files:

| Category | Files | Purpose |
|----------|-------|---------|
| Theme assets | `PHOTO_GUI/` (fonts, backgrounds) | Visual themes |
| Map config | `map_config.json`, `map_tensors.json` | Spatial data |
| External data | `data/external/*.csv` | Reference statistics |
| Knowledge | `data/knowledge/`, `tactical_knowledge.json` | RAG coaching data |
| Migrations | `alembic/` | Database schema upgrades |
| Translations | `assets/i18n/` | Localization |
| Help docs | `data/docs/` | In-app help |
| Qt themes | `apps/qt_app/themes/` | QSS stylesheets |

### Hidden Imports (92 total)

Critical packages that PyInstaller can't detect automatically:
- **Qt:** PySide6 (QtCore, QtGui, QtWidgets, QtCharts)
- **ML:** torch, torch.nn, torch.optim
- **Database:** sqlmodel, sqlalchemy, alembic
- **Parsing:** demoparser2, pandas, numpy
- **Project modules:** 30+ internal modules (app_state, jepa_model, coaching_service, etc.)

### Excluded Packages

```python
excludes = ['pytest', 'coverage', 'pre_commit', 'black', 'isort',
            'IPython', 'notebook', 'jupyterlab', 'kivy', 'kivymd',
            'shap', 'playwright']
```

### Bundle Sizes

| Variant | Size | Notes |
|---------|------|-------|
| CPU-only PyTorch | ~1.5 GB | Default, works everywhere |
| GPU (CUDA) PyTorch | ~2.5 GB | Auto-detected at runtime |

## `windows_installer.iss` — Inno Setup

Creates a Windows MSI installer with:
- **Install path:** `Program Files\Macena_CS2_Analyzer`
- **Languages:** English, Italian, Brazilian Portuguese
- **Compression:** LZMA (solid compression)
- **Shortcuts:** Start Menu group + optional Desktop icon
- **Post-install:** Auto-launches the application

Requires [Inno Setup](https://jrsoftware.org/isinfo.php) to compile.

## `BUILD_CHECKLIST.md` — Release Protocol

Step-by-step verification before distribution:

1. **Pre-build:** All 13 pre-commit hooks pass, test coverage >= 30%, validator exits 0
2. **Version sync:** `pyproject.toml` version matches `windows_installer.iss` AppVersion
3. **Build:** PyInstaller with `--noconfirm`
4. **Post-build:** Exe launches, UI renders, maps load, charts render, `audit_binaries.py` passes
5. **Optional:** Compile Inno Setup installer for MSI distribution

## Development Notes

- The `.spec` file handles missing paths gracefully (for CI environments)
- `collect_submodules("Programma_CS2_RENAN")` auto-discovers project modules
- GPU detection happens at runtime via `backend/nn/config.py:get_device()`
- **matplotlib is REQUIRED** at runtime (for visualization_service.py)
- **sentence_transformers is REQUIRED** (for SBERT embeddings in RAG)
- **ncps/hflayers are NOT needed at runtime** (RAP model is experimental)
- The CI/CD pipeline (`/.github/workflows/build.yml`) automates this on pushes to main
- Version numbers: check both `pyproject.toml` and `windows_installer.iss` before releasing
