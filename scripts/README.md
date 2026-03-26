> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Build and Setup Scripts

> **Authority:** Rule 7 (CI/CD & Release Engineering)

Build and setup scripts for creating production-ready executables of the Macena CS2 Analyzer desktop application. These scripts automate the PyInstaller build process for Windows distribution.

## File Inventory

| File | Purpose | Platform |
|------|---------|----------|
| `build_exe.bat` | Development build — creates standalone executable | Windows |
| `build_production.bat` | Production build — optimized and stripped | Windows |
| `Setup_Macena_CS2.ps1` | PowerShell setup script for environment configuration | Windows |

## Build Architecture

The build process uses PyInstaller to bundle the entire Python application, its dependencies, and all runtime assets into a standalone Windows executable. No Python installation is required on the target machine.

```
Source Code + Dependencies + Assets
        │
        ▼
    PyInstaller (build_exe.bat)
        │
        ├── Analysis phase (detect imports, collect data files)
        ├── Bundle phase (create archive)
        └── Output phase (generate executable)
        │
        ▼
    dist/Macena/
        ├── Macena.exe          # Main executable
        ├── _internal/          # Bundled Python + deps
        └── (runtime assets)    # Maps, fonts, themes, knowledge base
```

## `build_exe.bat` — Development Build

This script creates a directory-mode bundle (not a single file) for easier debugging:

### What It Does

1. **Cleans** old build artifacts (`dist/`, `build/` directories)
2. **Runs PyInstaller** with the following configuration:
   - `--noconsole` — no terminal window (GUI application)
   - `--name Macena` — executable named `Macena.exe`
   - `--icon` — uses `Programma_CS2_RENAN/PHOTO_GUI/icon.ico`
3. **Bundles runtime data:**
   - `PHOTO_GUI/` — fonts, backgrounds, theme images
   - `apps/` — application screens and layouts
   - `data/` — knowledge base, external CSVs, map configs
4. **Collects** all KivyMD and Kivy assets automatically

### Entry Point

```python
# The build starts from the legacy Kivy entry point
Programma_CS2_RENAN/main.py
```

### Output

```
dist/Macena/
├── Macena.exe
└── _internal/
    ├── PHOTO_GUI/
    ├── apps/
    ├── data/
    └── (Python runtime + all dependencies)
```

## `build_production.bat` — Production Build

Extends the development build with production optimizations:

| Optimization | Flag | Effect |
|-------------|------|--------|
| Python optimization | `-OO` | Removes docstrings and assert statements |
| Debug stripping | (PyInstaller internal) | Removes debug symbols |
| Size minimization | Exclude dev packages | Removes pytest, coverage, IPython, etc. |
| Integrity validation | Post-build check | Verifies executable can launch |

## Relationship with `packaging/`

These scripts are the **legacy** build approach. The primary build system has moved to `packaging/cs2_analyzer_win.spec`, which uses the Qt (PySide6) entry point instead of Kivy:

| Aspect | `scripts/` (legacy) | `packaging/` (primary) |
|--------|---------------------|----------------------|
| Entry point | `main.py` (Kivy) | `apps/qt_app/app.py` (Qt) |
| UI framework | Kivy + KivyMD | PySide6/Qt |
| Spec file | Inline in .bat | `cs2_analyzer_win.spec` |
| Hidden imports | Auto-detected | 92 explicit entries |
| Installer | None | Inno Setup (MSI) |

## Usage

```bat
REM Development build
scripts\build_exe.bat

REM Production build (optimized)
scripts\build_production.bat
```

## Prerequisites

- Python 3.10+ with virtual environment activated
- PyInstaller installed (`pip install pyinstaller`)
- All project dependencies installed
- Windows environment (batch scripts)

## Build Artifacts

| Directory | Contents | Git-tracked |
|-----------|----------|-------------|
| `dist/` | Final executable and bundled files | No (.gitignore) |
| `build/` | Intermediate build artifacts | No (.gitignore) |

For a clean build, delete both directories before rebuilding.

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| Missing module errors | PyInstaller can't detect dynamic imports | Add to `--hidden-import` flags |
| Asset not found at runtime | Data files not bundled | Add `--add-data` for the missing path |
| Executable crashes on launch | Missing DLLs or runtime files | Check PyInstaller warnings during build |
| Build too large (>3 GB) | GPU PyTorch included | Use CPU-only torch for distribution |

## Development Notes

- Always run `python tools/headless_validator.py` before building
- The production build is approximately 1.5 GB (CPU-only PyTorch)
- GPU support is auto-detected at runtime via `backend/nn/config.py:get_device()`
- For the primary Qt-based build, use `packaging/cs2_analyzer_win.spec` instead
