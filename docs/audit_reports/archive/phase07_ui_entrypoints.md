# Deep Audit Report — Phase 7: Desktop App + Root Entry Points

> **STATUS: HISTORICAL — All FIXED items removed (2026-03-08)**
> Cross-referenced against DEFERRALS.md. Only ACCEPTED design decisions retained.

**Date:** 2026-02-27
**Files Audited:** 18 / 18
**Original Issues:** 42 (3 CRITICAL, 7 HIGH, 20 MEDIUM, 12 LOW)
**Remaining:** 9 (9 ACCEPTED)

---

## Accepted Design Decisions (9)

| F-Code | File | Severity | Description |
|--------|------|----------|-------------|
| F7-08 | `main.py:~1380` | LOW | `save_hardware_budget()` marked DEPRECATED in docstring but still callable from UI. Kept for backward compatibility |
| F7-10 | `console.py:~1050` | MEDIUM | `stderr_file` passed to subprocess; `finally` block closes handle while subprocess may still write. Subprocess owns the handle; OS closes on process exit |
| F7-12 | `goliath.py:21`, `console.py:18` | LOW | `sys.path` manipulation at module level in root-level entry points. Acceptable for CLI tools |
| F7-28 | `localization.py:66` | LOW | `os.path.expanduser("~")` evaluated at import time — always correct in desktop context |
| F7-30 | `console.py:~820` | LOW | Shows last 4 chars of API key. Accepted practice until keyring integration |
| F7-32 | `console.py:~1100` | LOW | `__pycache__` clear without confirmation prompt. Safe operation (caches regenerate) |
| F7-37 | `main.py:~950` | LOW | Notifications marked as read immediately on retrieval, even if UI hasn't displayed them |
| F7-38 | `ghost_pixel.py` | LOW | GhostPixel debug overlay importable in production — no functional risk |
| F7-39 | `layout.kv:126` | MEDIUM | Two full-resolution FitImage textures held in memory for crossfade transitions (~20MB acceptable trade-off) |

## Monitoring Items

None.
