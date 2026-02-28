> **[English](README.md)** | **[Italiano](README_IT.md)** | **[Português](README_PT.md)**

# Build and Setup Scripts

Build and setup scripts for creating production-ready executables and development environment setup.

## Build Scripts

- `build_exe.bat` — PyInstaller executable build script for Windows
- `build_production.bat` — Production build script with optimizations

## Build Process

The build scripts use PyInstaller to create a standalone executable of the Macena CS2 Analyzer desktop application.

### build_exe.bat

- Creates a single-file executable (`--onefile`) or directory bundle
- Includes all necessary dependencies (Kivy, KivyMD, PyTorch, ncps, hflayers)
- Bundles assets (maps, images, fonts) from `apps/desktop_app/assets/`
- Configures icon and executable metadata
- Output: `dist/MacenaCS2Analyzer.exe`

### build_production.bat

- Extends `build_exe.bat` with production optimizations
- Enables Python optimization flags (`-OO`)
- Strips debug symbols and bytecode
- Minimizes executable size
- Validates build integrity

## Usage

```bat
# Development build
scripts\build_exe.bat

# Production build (optimized)
scripts\build_production.bat
```

## Requirements

- PyInstaller installed (`pip install pyinstaller`)
- All project dependencies installed
- Windows environment (batch scripts)

## Notes

Build artifacts are generated in the `dist/` and `build/` directories. Clean build: delete these directories before rebuilding.
