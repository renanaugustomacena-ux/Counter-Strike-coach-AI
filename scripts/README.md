> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Build and Setup Scripts

> **Authority:** Rule 7 (CI/CD & Release Engineering)

Build and setup scripts for creating production-ready executables of the Macena CS2 Analyzer desktop application. These scripts automate the PyInstaller build process for Windows distribution.

## File Inventory

| File | Purpose | Platform |
|------|---------|----------|
| `build_exe.bat` | Compatibility wrapper — delegates to `build_production.bat` (the old inline Kivy invocation was replaced) | Windows |
| `build_production.bat` | Production build automation — validation, migration, manifest, build, audit, installer | Windows |
| `Setup_Macena_CS2.ps1` | PowerShell setup — re-roots itself to the repository root, creates `venv_win`, installs CPU torch + requirements, initializes the database, installs Playwright Chromium | Windows |
| `reaggregate.sh` | Re-aggregation pipeline — repopulates round stats, enriches match stats, mines coaching experiences, rebuilds knowledge base + FAISS indexes | Linux (bash) — runs on the separate data/training machine |

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

## `build_exe.bat` — Compatibility Wrapper

Formerly an inline PyInstaller invocation targeting the removed Kivy entry point (`Programma_CS2_RENAN/main.py`). It was replaced (not deleted, so older instructions that invoke it keep working): the script now prints a notice and delegates to `build_production.bat`, forwarding all arguments, so it produces the current PySide6 build from `packaging/cs2_analyzer_win.spec`.

## `build_production.bat` — Production Build Automation

The full Windows release pipeline (uses `venv_win`; run `Setup_Macena_CS2.ps1` first):

1. **Pre-flight** — verifies `venv_win`, `Programma_CS2_RENAN/tools/sync_integrity_manifest.py`, `tools/audit_binaries.py`, `packaging/cs2_analyzer_win.spec`, and core deps (keyring, kivymd, sqlmodel, alembic) are present
2. **Cleanup** — removes `build/` and `dist/`
3. **Schema sync** — `alembic upgrade head` (aborts on failure)
4. **Integrity manifest (RASP)** — regenerates `integrity_manifest.json` via `sync_integrity_manifest.py`
5. **Build** — `python Programma_CS2_RENAN/tools/build_tools.py build` (format/import checks, pytest, `alembic upgrade head`, PyInstaller via `packaging/cs2_analyzer_win.spec`, SHA-256 `build_manifest.json` in `dist/`)
6. **Binary audit** — `python tools/audit_binaries.py` (aborts if the security audit fails)
7. **Installer (optional)** — compiles `packaging/windows_installer.iss` with Inno Setup 6 if `ISCC.exe` is found, producing `dist\Macena_CS2_Installer.exe`

## Relationship with `packaging/`

The build definition lives in `packaging/cs2_analyzer_win.spec` (Qt/PySide6 entry point `apps/qt_app/app.py`, 35 explicit hidden imports + `collect_submodules`). Both batch scripts converge on it:

- `build_production.bat` runs the full pipeline and builds the spec via `Programma_CS2_RENAN/tools/build_tools.py build`
- `build_exe.bat` simply delegates to `build_production.bat`
- The optional installer is compiled from `packaging/windows_installer.iss` (Inno Setup, `Macena_CS2_Installer.exe`)

The CI dist stage (`build-distribution` job in `.github/workflows/build.yml`) builds the same spec on `windows-latest` (pushes to `main` only) with Python 3.12, `requirements-lock-cpu.txt`, and a pinned `pyinstaller==6.17.0`.

## Usage

```bat
REM One-time environment setup (creates venv_win)
powershell -ExecutionPolicy Bypass -File scripts\Setup_Macena_CS2.ps1

REM Production build (validation + build + audit + installer)
scripts\build_production.bat
```

```bash
# Data re-aggregation pipeline (separate Linux machine, venv activated)
bash scripts/reaggregate.sh
```

> **Note:** `reaggregate.sh` runs on the separate Linux machine that hosts the `.dem` corpus (`PRO_DEMO_PATH` in `user_settings.json`) — like full-scale AI training, this data-heavy workload does not run on the Windows development box. Expected runtime: 30-90 minutes depending on demo count.

`Setup_Macena_CS2.ps1` can be invoked from any directory (it changes to the repository root first) and prints the launch command on completion: `.\venv_win\Scripts\python.exe -m Programma_CS2_RENAN.apps.qt_app.app`.

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
| Missing module errors | PyInstaller can't detect dynamic imports | Add to `hiddenimports` in `packaging/cs2_analyzer_win.spec` |
| Asset not found at runtime | Data files not bundled | Add the missing path to `datas` in the spec |
| Executable crashes on launch | Missing DLLs or runtime files | Check PyInstaller warnings during build |
| Build too large (>3 GB) | GPU PyTorch included | Use CPU-only torch for distribution |

## Development Notes

- Always run `python tools/headless_validator.py` before building
- The production build is approximately 1.5 GB (CPU-only PyTorch; see `packaging/BUILD_CHECKLIST.md`)
- GPU support is auto-detected at runtime via `backend/nn/config.py:get_device()`
- All build paths (both `.bat` scripts and CI) use `packaging/cs2_analyzer_win.spec`
