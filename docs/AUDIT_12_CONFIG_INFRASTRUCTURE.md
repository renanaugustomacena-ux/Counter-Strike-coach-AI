# Audit Report 12 — Configuration, CI/CD & Infrastructure

**Scope:** Config files, CI/CD, infrastructure scripts — 62 files | **Date:** 2026-03-10
**Open findings:** 0 HIGH | 14 MEDIUM | 18 LOW

---

## MEDIUM Findings

| ID | File | Finding |
|---|---|---|
| 1 | pyproject.toml | `disallow_untyped_defs = false` — mypy won't flag untyped functions |
| 5 | alembic.ini | Hardcoded relative DB path (env.py overrides at runtime) |
| 6 | .pre-commit-config.yaml | No security linter (bandit) at pre-commit stage |
| 7 | .pre-commit-config.yaml | headless-validator only at pre-push — broken code can accumulate |
| 11 | requirements.txt | Wide version ranges (torch <3.0, numpy <3.0) — incompatible major versions possible |
| 13 | requirements-lock.txt | Windows-only lock file with pywin32/kivy-deps — fails on Linux |
| 14 | requirements-lock.txt | Phantom PDF deps (pdfminer, pdfplumber, PyMuPDF, pypdf) despite documented removal |
| 17 | build.yml | `\|\| true` on Bandit medium scan — all medium findings silently ignored |
| 18 | build.yml | Secret detection is simple grep — misses API keys, tokens |
| 19 | build.yml | `pip install` without hash verification — supply chain risk |
| 24 | console.py | `_cmd_svc_spawn` opens stderr_file, intentionally never closes — FD leak |
| 25 | console.py | `_cmd_maint_clear_cache` walks PROJECT_ROOT with shutil.rmtree — dangerous if misconfigured |
| 26 | console.py | `import threading` at line 1288 instead of top-level |
| 35 | schema.py | `run_fix("sequences")` deletes sqlite_sequence without backup/confirmation |
| 36 | schema.py | `fetchall()` loads all rows into memory — unbounded for large tables |
| 39 | run_full_training_cycle.py | `manager._assign_dataset_splits()` calls private method |
| 41 | generate_zh_pdfs.py | Hardcoded absolute paths — not portable |
| 44 | training_progress.json | Epoch counter resets 50+ times — repeated training restarts |
| 45 | training_progress.json | All val_loss entries Infinity for first ~540 entries |

## LOW Findings

| ID | File | Finding |
|---|---|---|
| 2 | pyproject.toml | Coverage fail_under = 30 — very low threshold |
| 3 | pyproject.toml | Uses legacy/private setuptools build backend |
| 4 | pytest.ini | `--disable-warnings` suppresses all warnings including deprecation |
| 8 | .pre-commit-config.yaml | Hook versions may not be latest |
| 9 | docker-compose.yml | FlareSolverr v3.4.6 — check for CVEs |
| 10 | docker-compose.yml | No resource limits on container |
| 12 | requirements.txt | Comment says PDF deps removed but lock file still has them |
| 15 | requirements-lock.txt | torch locked to CUDA 12.1 |
| 16 | bindep.txt | Only Windows entries — no Linux binary deps listed |
| 20 | build.yml | All jobs on windows-latest — may not match production Linux |
| 21 | gemini-dispatch.yml | Edge case: empty body falls through (mitigated by auth check) |
| 22 | gemini-invoke.yml | Gemini CLI action not pinned to SHA |
| 27 | console.py | Logger named "MacenaConsole" not "cs2analyzer.console" |
| 28 | console.py | `dispatch_interactive` splits on spaces — can't handle paths with spaces |
| 29 | console.py | `_throttle_factor` private attribute access for display |
| 30 | console.py | `renderer._dirty` accessed from outside class |
| 31 | goliath.py | Logger named "Goliath" not "cs2analyzer.goliath" |
| 32 | goliath.py | `_cleanup_children` silently swallows all exceptions |
| 37 | schema.py | No logging — all output via print() |
| 38 | schema.py | Comment typo "Ignorning" |
| 40 | run_full_training_cycle.py | f-strings in logging calls |
| 42 | generate_zh_pdfs.py | `<html lang="it">` but file is for Chinese PDFs |
| 43 | integrity_manifest.json | Manifest over a month old — hashes may not match |
| 46 | Build_Health_Report.json | "STALE" daemon status could confuse automated tools |
| 47 | .claude/settings.local.json | Stale Windows permission patterns for Linux environment |

## Cross-Cutting

1. **Logger Naming** — console.py and goliath.py use custom names instead of `cs2analyzer.<module>`.
2. **Requirements Drift** — Lock file has phantom PDF deps and is Windows-only.
3. **Security Scanning Gaps** — No pre-commit security linter; CI Bandit silently ignores medium findings.
