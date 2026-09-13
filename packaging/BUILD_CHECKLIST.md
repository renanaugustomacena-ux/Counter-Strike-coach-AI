# Build Checklist — Macena CS2 Analyzer

## Prerequisites

- [ ] Python 3.10+ with venv activated
- [ ] `pip install -r requirements.txt` clean (exit 0)
- [ ] `pip install pyinstaller` (not in requirements.txt — build-only dep)
- [ ] `python tools/headless_validator.py` exits 0

## Pre-Build Verification

- [ ] All 13 pre-commit hooks pass: `pre-commit run --all-files`
- [ ] Test suite passes: `pytest --cov=Programma_CS2_RENAN --cov-fail-under=30`
- [ ] No `print()` in production code (headless validator Phase 12 checks this)
- [ ] `integrity_manifest.json` is current (regenerate if files changed)

## Version Synchronization

Before every release build, verify version consistency:

- [ ] `pyproject.toml` → `[project].version`
- [ ] `packaging/version.iss` → `#define AppVersion` (generated: `python tools/gen_version_iss.py`;
      `windows_installer.iss` includes it, never edit the version by hand)
- Both must match. Current: **1.0.0**

## Factory Models

- [ ] Place the checkpoints to ship in `Programma_CS2_RENAN/models/global/` — each `.pt` WITH its
      `.pt.meta.json` sidecar (`jepa_v2_encoder.pt` for the current neural core; see the README.txt there)
- [ ] Everything matching `*.pt*` in that folder is bundled; the build script warns when it is empty

## Build Command

```bat
scripts\build_production.bat
```

The script activates `venv_win` (or `.venv`), checks the Qt/storage/torch/PyInstaller imports,
migrates the schema, regenerates the integrity manifest and `version.iss`, runs PyInstaller on
`packaging/cs2_analyzer_win.spec`, audits the binaries, runs the packaged selftest and compiles
the installer when Inno Setup is present. Manual equivalent of the build step:

```bash
python -m PyInstaller --noconfirm packaging/cs2_analyzer_win.spec --log-level WARN
```

Output: `dist/Macena_CS2_Analyzer/` (onedir: the exe plus `_internal/`)

## PyTorch CPU-Only Variant (Smaller Build)

To reduce build size (~500MB savings), install CPU-only torch before building:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

The code auto-detects CPU via `backend/nn/config.py:get_device()` — no code changes needed.

## Expected Bundle Size

| Variant | Approximate Size |
|---------|-----------------|
| CPU-only torch | ~1.5 GB |
| GPU (CUDA) torch | ~2.5 GB |

## Post-Build Verification

- [ ] `dist/Macena_CS2_Analyzer/Macena_CS2_Analyzer.exe` exists
- [ ] Packaged selftest: `Macena_CS2_Analyzer.exe --selftest` with `LOCALAPPDATA` pointing at a
      scratch folder and the dist folder write-denied (the build script does both); read
      `<LOCALAPPDATA>\MacenaCS2Analyzer\selftest_report.json` — `"ok": true`, the factory models
      listed, `alembic_ini_ok`, no file created beside the exe
- [ ] Launch exe — verify no crash on startup; the setup wizard opens on a fresh profile
- [ ] Verify map_config.json accessible (map images load)
- [ ] Verify `_internal/alembic/` and `_internal/alembic.ini` present in the bundle
- [ ] Verify PHOTO_GUI/ assets present (fonts, themes, backgrounds)
- [ ] Verify matplotlib charts render (Performance screen → skill radar)
- [ ] Run `python tools/audit_binaries.py` on the dist folder

## Windows Installer (Optional)

Requires [Inno Setup](https://jrsoftware.org/isinfo.php):

```bash
iscc packaging/windows_installer.iss
```

## Known Constraints

- FlareSolverr requires Docker — not bundled, must be run separately
- Playwright requires browser install — not bundled for frozen builds
- HLTV scraping excluded from frozen build (Playwright dep)
- SentenceTransformer model downloads on first run (~80MB)
- matplotlib is included in the bundle (~30MB) — required for chart rendering
