# CI/CD Pipeline Guide

## Pipeline Architecture

**File:** `.github/workflows/build.yml`

The Macena CI Pipeline runs 6 jobs across 2 platforms:

| Job | Runner | Depends On | Blocking? |
|-----|--------|------------|-----------|
| `lint` | ubuntu-latest | — | Yes |
| `test` | ubuntu + windows (matrix) | lint | Yes |
| `integration` | ubuntu + windows (matrix) | test | Yes |
| `security` | ubuntu-latest | lint | Yes |
| `type-check` | ubuntu-latest | lint | No (informational) |
| `build-distribution` | windows-latest | integration + security | Yes (main only) |

### Visual Flow

```
                  ┌─ test (Ubuntu) ─────┐   ┌─ integration (Ubuntu) ────┐
lint ─────────────┤                     ├───┤                           ├──── build-distribution
                  └─ test (Windows) ────┘   └─ integration (Windows) ───┘      (Windows, main only)
         │                                                                          │
         ├── security ──────────────────────────────────────────────────────────────┘
         └── type-check (non-blocking)
```

---

## Workflow Triggers

| Event | Branches | Jobs Run |
|-------|----------|----------|
| Push | `main`, `develop`, `feature/**`, `fix/**` | All (build-distribution only on main) |
| Pull request | `main`, `develop` | All except build-distribution |

**Concurrency:** Only one pipeline runs per branch at a time. New pushes cancel in-progress runs.

---

## Cross-Platform Dependencies

### Linux (Ubuntu)
```bash
# System packages (SDL2 for Kivy)
sudo apt-get install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libgl1-mesa-glx

# Python packages (CPU-only PyTorch for CI speed)
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

### Windows
```powershell
# Uses the reproducible lock file
pip install -r requirements-ci.txt
```

**Why different?** `requirements-lock.txt` (referenced by `requirements-ci.txt`) contains Windows-specific packages (`kivy-deps.angle`, `pywin32`, etc.) that cannot install on Linux. Linux uses the platform-agnostic `requirements.txt` with version ranges.

---

## Environment Variables

These environment variables are set on CI runners:

| Variable | Value | Purpose |
|----------|-------|---------|
| `CI` | `'true'` | Bypasses venv guards in tools |
| `VIRTUAL_ENV` | `'ci'` | Signals managed environment |
| `KIVY_NO_ARGS` | `'1'` | Prevents Kivy from parsing CLI args |

---

## Local Validation (Before Push)

### 1. Verify YAML syntax
```bash
pip install yamllint
yamllint .github/workflows/build.yml
```

### 2. Run the headless validator
```bash
# Linux
source ~/.venvs/cs2analyzer/bin/activate
python tools/headless_validator.py

# Windows (PowerShell)
.\.venvs\cs2analyzer\Scripts\Activate
python tools\headless_validator.py
```

### 3. Run portability checks
```bash
python tools/portability_test.py
```

### 4. Run pre-commit hooks
```bash
pre-commit run --all-files
```

---

## Security Gates

### Bandit (SAST)
- Scans `Programma_CS2_RENAN/` for security issues
- Severity: MEDIUM+ with MEDIUM+ confidence
- Excludes: `tests/`, `external_analysis/`
- Generates JSON report artifact

### detect-secrets
- Scans for hardcoded credentials, API keys, tokens
- Fails the pipeline if any secrets are detected
- Excludes: `tests/`, `external_analysis/`

### Supply Chain
- All GitHub Actions are **SHA-pinned** (not tag-referenced)
- Prevents tag-swapping attacks on the Actions marketplace

---

## Build Distribution

Runs **only on main branch** after all quality gates pass.

1. Installs Windows dependencies from lock file
2. Validates critical data files exist (layouts, configs, knowledge base)
3. Builds executable via PyInstaller (`packaging/cs2_analyzer_win.spec`)
4. Runs post-build integrity audit
5. Uploads `cs2-analyzer-windows` artifact (30-day retention)

### Download Artifact
1. Go to GitHub Actions tab
2. Click the latest successful main branch run
3. Scroll to "Artifacts" section
4. Download `cs2-analyzer-windows`

---

## Troubleshooting

### Pipeline doesn't trigger
- Verify GitHub Actions is enabled: Settings > Actions > Allow all actions
- Check branch pattern matches: `main`, `develop`, `feature/**`, `fix/**`

### Tests pass locally but fail on CI
- **Path separators:** Use `pathlib.Path` instead of hardcoded `/` or `\`
- **Missing dependencies:** Check both `requirements.txt` (Linux) and `requirements-lock.txt` (Windows)
- **Venv guards:** Tools need `and not os.environ.get("CI")` in their venv check

### Build artifact missing
- Only generated on `main` branch pushes
- Check the `build-distribution` job logs for PyInstaller errors
- Verify `packaging/cs2_analyzer_win.spec` exists

### Actions minutes
- **Public repos:** Unlimited
- **Private repos:** 2,000 min/month free (Linux), 500 min/month free (Windows, 2x multiplier)
- Monitor: Settings > Billing > Actions minutes

---

## Cost Analysis

| Item | Cost (Public Repo) |
|------|--------------------|
| GitHub Actions execution | $0 |
| Artifact storage (30 days) | $0 |
| **Total Monthly** | **$0** |
