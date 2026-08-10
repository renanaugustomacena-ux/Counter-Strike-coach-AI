> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Build and Setup Scripts

> **Authority:** Rule 7 (CI/CD & Release Engineering)

Build and setup scripts for creating production-ready executables of the Macena CS2 Analyzer desktop application. These scripts automate the PyInstaller build process for Windows distribution.

## File Inventory

| File | Purpose | Platform |
|------|---------|----------|
| `build_exe.bat` | Legacy development build — inline PyInstaller invocation (broken: targets the removed Kivy entry point) | Windows |
| `build_production.bat` | Production build automation — validation, migration, manifest, build, audit, installer | Windows |
| `Setup_Macena_CS2.ps1` | PowerShell setup — creates `venv_win`, installs CPU torch + requirements, initializes the database, installs Playwright Chromium | Windows |
| `reaggregate.sh` | Re-aggregation pipeline — repopulates round stats, enriches match stats, mines coaching experiences, rebuilds knowledge base + FAISS indexes | Linux/macOS (bash) |

## Build Architecture

The build process uses PyInstaller to bundle the entire Python application, its dependencies, and all runtime assets into a standalone Windows executable. No Python installation is required on the target machine.

```
Source Code + Dependencies + Assets
        │
        ▼
    PyInstaller (packaging/cs2_analyzer_win.spec, driven by build_production.bat)
        │
        ├── Analysis phase (detect imports, collect data files)
        ├── Bundle phase (create archive)
        └── Output phase (generate executable)
        │
        ▼
    dist/Macena_CS2_Analyzer/
        ├── Macena_CS2_Analyzer.exe   # Main executable
        ├── _internal/                # Bundled Python + deps
        └── (runtime assets)          # Maps, fonts, themes, knowledge base
```

## `build_exe.bat` — Legacy Development Build (broken)

Kept for historical reference. It creates a directory-mode bundle via an inline PyInstaller invocation from `venv_win`:

1. **Cleans** old build artifacts (`dist/`, `build/` directories)
2. **Runs PyInstaller** with:
   - `--noconsole` — no terminal window (GUI application)
   - `--name Macena` — executable named `Macena.exe`
   - `--icon` — uses `Programma_CS2_RENAN/PHOTO_GUI/icon.ico`
   - `--add-data` for `PHOTO_GUI/`, `apps/`, `data/`
   - `--collect-all kivymd --collect-all kivy`

> **Note:** the script targets `Programma_CS2_RENAN/main.py`, the old Kivy entry point, which **no longer exists** (the app migrated to Qt with entry point `apps/qt_app/app.py`). Running it today fails; use `packaging/cs2_analyzer_win.spec` instead.

## `build_production.bat` — Production Build Automation

The full Windows release pipeline (uses `venv_win`; run `Setup_Macena_CS2.ps1` first):

1. **Pre-flight** — verifies `venv_win`, `Programma_CS2_RENAN/tools/sync_integrity_manifest.py`, `tools/audit_binaries.py`, `packaging/cs2_analyzer_win.spec`, and core deps (keyring, kivymd, sqlmodel, alembic) are present
2. **Cleanup** — removes `build/` and `dist/`
3. **Schema sync** — `alembic upgrade head` (aborts on failure)
4. **Integrity manifest (RASP)** — regenerates `integrity_manifest.json` via `sync_integrity_manifest.py`
5. **Build** — `python Programma_CS2_RENAN/tools/build_tools.py build` (advanced build debugger; writes `build_debug.log` / `build_report.json`)
6. **Binary audit** — `python tools/audit_binaries.py` (aborts if the security audit fails)
7. **Installer (optional)** — compiles `packaging/windows_installer.iss` with Inno Setup 6 if `ISCC.exe` is found, producing `dist\Macena_CS2_Installer.exe`

## Relationship with `packaging/`

`build_exe.bat` is the **legacy** approach; the build definition now lives in `packaging/cs2_analyzer_win.spec` (Qt/PySide6 entry point), which `build_production.bat` drives:

| Aspect | `build_exe.bat` (legacy) | `packaging/` spec (primary) |
|--------|---------------------|----------------------|
| Entry point | `main.py` (Kivy — removed) | `apps/qt_app/app.py` (Qt) |
| UI framework | Kivy + KivyMD | PySide6/Qt |
| Spec file | Inline in .bat | `cs2_analyzer_win.spec` |
| Hidden imports | Auto-detected | 35 explicit entries + `collect_submodules` |
| Installer | None | Inno Setup (`Macena_CS2_Installer.exe`) |

## Usage

```bat
REM One-time environment setup (creates venv_win)
powershell -ExecutionPolicy Bypass -File scripts\Setup_Macena_CS2.ps1

REM Production build (validation + build + audit + installer)
scripts\build_production.bat
```

```bash
# Data re-aggregation pipeline (Linux/macOS, venv activated)
bash scripts/reaggregate.sh
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
